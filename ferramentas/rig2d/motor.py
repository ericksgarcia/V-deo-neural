"""Motor de rig 2D por malhas (estilo Spine / Live2D / Moho), em Python puro (numpy + OpenCV + scipy).

Recursos:
  - malhas triangulares geradas do alfa de cada peça (contorno + pontos internos + anéis de refino nas juntas);
  - skinning com pesos por difusão de calor (como o "automatic weights" do Blender / Pinocchio), até 4 ossos por vértice;
  - esqueleto hierárquico (FK), IK de 2 ossos, escala e translação por osso;
  - física secundária (cadeias verlet com mola de volta à pose) para cabelo, faixa, cinto;
  - deformadores livres (função de vértices, ex.: onda da barra da túnica, respiração) aplicados antes do skinning;
  - decalques vetoriais presos à cabeça (piscar, boca com visemas);
  - renderizador de triângulos com texturas (afim por triângulo) com supersampling.
"""
import math, json, os
import numpy as np, cv2
from PIL import Image
from scipy.spatial import Delaunay, cKDTree
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import spsolve

I3 = np.eye(3)

def _T(x, y):
    m = np.eye(3); m[0, 2] = x; m[1, 2] = y; return m

def _R(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])

def _S(k):
    m = np.eye(3); m[0, 0] = m[1, 1] = k; return m

def cruz(a, b):
    return a[0] * b[1] - a[1] * b[0]

def suave(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ esqueleto
class Osso:
    def __init__(s, nome, pai, cabeca, ponta):
        s.nome, s.pai = nome, pai
        s.h = np.array(cabeca, float); s.t = np.array(ponta, float)
        d = s.t - s.h
        s.comp = float(np.hypot(*d)); s.ang = math.atan2(d[1], d[0])
        s.rot = 0.0; s.pos = np.zeros(2); s.esc = 1.0
        s.skin = I3.copy()

class Esqueleto:
    def __init__(s):
        s.ossos = []; s.idx = {}

    def add(s, nome, pai, cabeca, ponta):
        o = Osso(nome, s.ossos[s.idx[pai]] if pai else None, cabeca, ponta)
        s.idx[nome] = len(s.ossos); s.ossos.append(o); return o

    def __getitem__(s, n): return s.ossos[s.idx[n]]

    def zerar(s):
        for o in s.ossos: o.rot = 0.0; o.pos = np.zeros(2); o.esc = 1.0

    def fk(s):
        for o in s.ossos:
            P = o.pai.skin if o.pai else I3
            o.skin = P @ _T(*(o.h + o.pos)) @ _R(o.rot) @ _S(o.esc) @ _T(*(-o.h))

    def matrizes(s): return np.stack([o.skin for o in s.ossos])

    def rot_total(s, o): return math.atan2(o.skin[1, 0], o.skin[0, 0])

    def ik2(s, a, b, alvo, dobra=1):
        """IK analítico de 2 ossos: a (sup) e b (inf, filho de a). 'alvo' em coordenadas do mundo. Devolve ponto alcançado."""
        a, b = s[a] if isinstance(a, str) else a, s[b] if isinstance(b, str) else b
        P = a.pai.skin if a.pai else I3
        H = (P @ np.array([*(a.h + a.pos), 1.0]))[:2]
        la = float(np.hypot(*(b.h - a.h))); lb = b.comp
        d = np.asarray(alvo, float) - H
        dist = float(np.clip(np.hypot(*d), abs(la - lb) + 1e-3, la + lb - 1e-3))
        dir_t = math.atan2(d[1], d[0])
        cosA = (la * la + dist * dist - lb * lb) / (2 * la * dist)
        A = math.acos(np.clip(cosA, -1, 1))
        ang_a = dir_t - dobra * A
        rot_par = math.atan2(P[1, 0], P[0, 0])
        a.rot = ang_a - a.ang - rot_par
        K = H + la * np.array([math.cos(ang_a), math.sin(ang_a)])
        E = H + dist * np.array([math.cos(dir_t), math.sin(dir_t)])
        ang_b = math.atan2(*(E - K)[::-1])
        b.rot = ang_b - b.ang - (rot_par + a.rot)
        return E


# ------------------------------------------------------------------ física secundária
class Cadeia:
    """Cadeia de ossos simulada (verlet) presa ao pai do primeiro osso, com mola de volta à pose rígida."""
    def __init__(s, esq, nomes, rigidez=700.0, amort=0.93, grav=500.0, vento=0.0):
        s.esq, s.ossos = esq, [esq[n] for n in nomes]
        s.rest = np.array([s.ossos[0].h] + [o.t for o in s.ossos])
        s.L = np.hypot(*(np.diff(s.rest, axis=0)).T)
        s.k, s.amort, s.g, s.vento = rigidez, amort, grav, vento
        s.P = None; s.Pp = None

    def _ideal(s):
        pai = s.ossos[0].pai
        M = pai.skin if pai else I3
        pts = np.c_[s.rest, np.ones(len(s.rest))] @ M.T
        return pts[:, :2]

    def passo(s, dt=1 / 30, sub=4, vento=0.0):
        Q = s._ideal()
        if s.P is None: s.P = Q.copy(); s.Pp = Q.copy()
        h = dt / sub
        for _ in range(sub):
            Q = s._ideal()
            acc = np.zeros_like(s.P); acc[:, 1] += s.g; acc[:, 0] += vento + s.vento
            acc += s.k * (Q - s.P)
            nxt = s.P + (s.P - s.Pp) * s.amort + acc * h * h
            nxt[0] = Q[0]
            for _it in range(4):
                nxt[0] = Q[0]
                for i in range(len(s.L)):
                    d = nxt[i + 1] - nxt[i]; n = np.hypot(*d) + 1e-9
                    nxt[i + 1] = nxt[i] + d / n * s.L[i]
            s.Pp, s.P = s.P, nxt
        # converte posições em rotações locais
        pai = s.ossos[0].pai
        prev_total = math.atan2(pai.skin[1, 0], pai.skin[0, 0]) if pai else 0.0
        for i, o in enumerate(s.ossos):
            d = s.P[i + 1] - s.P[i]
            total = math.atan2(d[1], d[0]) - o.ang
            o.rot = (total - prev_total + math.pi) % (2 * math.pi) - math.pi
            o.pos = np.zeros(2)
            prev_total += o.rot
        return s.P


# ------------------------------------------------------------------ malha
def gerar_malha(alfa, off, esp=36, juntas=()):
    """alfa: crop uint8; off=(x0,y0) do crop na imagem global. Devolve (verts_global, tris)."""
    m = (alfa > 40).astype(np.uint8)
    md = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    cnts, _ = cv2.findContours(md, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    pts = []
    for c in cnts:
        if len(c) < 24: continue
        ap = cv2.approxPolyDP(c.astype(np.float32), 1.6, True)[:, 0, :].astype(float)
        n = len(ap)
        for i in range(n):
            a, b = ap[i], ap[(i + 1) % n]
            k = max(1, int(math.ceil(np.hypot(*(b - a)) / esp)))
            for j in range(k): pts.append(a + (b - a) * j / k)
    pts = np.array(pts)
    dt = cv2.distanceTransform(md, cv2.DIST_L2, 3)
    h, w = m.shape
    inner = []
    dy = esp * math.sqrt(3) / 2
    row = 0
    for y in np.arange(esp * 0.5, h, dy):
        for x in np.arange(esp * 0.5 + (esp / 2 if row % 2 else 0), w, esp):
            if dt[int(y), int(x)] >= esp * 0.55: inner.append((x, y))
        row += 1
    for (jx, jy) in juntas:
        jx, jy = jx - off[0], jy - off[1]
        for r, na in ((esp * 0.55, 8), (esp * 1.1, 12)):
            for k in range(na):
                a = 2 * math.pi * k / na
                x, y = jx + r * math.cos(a), jy + r * math.sin(a)
                if 0 <= x < w and 0 <= y < h and dt[int(y), int(x)] >= esp * 0.3: inner.append((x, y))
        if 0 <= jx < w and 0 <= jy < h and dt[int(jy), int(jx)] >= 2: inner.append((jx, jy))
    allp = list(pts)
    tree = cKDTree(pts) if len(pts) else None
    for p in inner:
        if tree is not None and tree.query(p)[0] < esp * 0.4: continue
        allp.append(np.array(p))
    allp = np.array(allp)
    # dedupe
    keep = []; tr = cKDTree(allp); used = np.zeros(len(allp), bool)
    for i in range(len(allp)):
        if used[i]: continue
        keep.append(i)
        for j in tr.query_ball_point(allp[i], esp * 0.25): used[j] = True
    allp = allp[keep]
    tri = Delaunay(allp).simplices
    ok = []
    for t in tri:
        p = allp[t]; c = p.mean(0)
        ar = abs(cruz(p[1] - p[0], p[2] - p[0])) / 2
        if ar < 2: continue
        cx, cy = int(np.clip(c[0], 0, w - 1)), int(np.clip(c[1], 0, h - 1))
        if md[cy, cx]: ok.append(t)
    tri = np.array(ok)
    used = np.unique(tri); remap = -np.ones(len(allp), int); remap[used] = np.arange(len(used))
    V = allp[used] + np.array(off, float)
    return V, remap[tri]


def pesos_calor(V, tris, ossos, esp):
    """Pesos de skinning por difusão de calor (Pinocchio). ossos: lista de Osso permitidos. Devolve (idx(n,4), w(n,4))."""
    n = len(V); nb = len(ossos)
    # laplaciano cotangente
    I, J, W = [], [], []
    mass = np.zeros(n)
    for t in tris:
        p = V[t]
        mass[t] += abs(cruz(p[1] - p[0], p[2] - p[0])) / 6
        for k in range(3):
            i, j, o = t[k], t[(k + 1) % 3], t[(k + 2) % 3]
            u, v = V[i] - V[o], V[j] - V[o]
            cot = np.dot(u, v) / (abs(cruz(u, v)) + 1e-9)
            w = max(0.5 * cot, 1e-3)
            I += [i, j]; J += [j, i]; W += [w, w]
    Wm = coo_matrix((W, (I, J)), shape=(n, n)).tocsr()
    D = diags(np.asarray(Wm.sum(1)).ravel())
    L = D - Wm
    # distância ao segmento de cada osso
    dist = np.zeros((n, nb))
    for j, o in enumerate(ossos):
        a, b = o.h, o.t; ab = b - a; l2 = max(ab @ ab, 1e-9)
        t = np.clip(((V - a) @ ab) / l2, 0, 1)
        dist[:, j] = np.hypot(*(V - (a + t[:, None] * ab)).T)
    near = dist.argmin(1)
    Wt = np.zeros((n, nb))
    for j in range(nb):
        d = np.maximum(dist[:, j], esp * 0.3) / esp
        H = np.where(near == j, 1.0 / (d * d), 0.0)
        Mh = diags(mass * H * (1.0 / (esp * esp)) * 40)
        rhs = Mh @ (near == j).astype(float)
        w = spsolve((L + Mh + diags(np.full(n, 1e-8))).tocsc(), rhs)
        Wt[:, j] = np.clip(w, 0, None)
    Wt = Wt / np.maximum(Wt.sum(1, keepdims=True), 1e-9)
    k = min(4, nb)
    idx = np.argsort(-Wt, 1)[:, :k]
    w = np.take_along_axis(Wt, idx, 1)
    w = w / np.maximum(w.sum(1, keepdims=True), 1e-9)
    if k < 4:
        idx = np.pad(idx, ((0, 0), (0, 4 - k))); w = np.pad(w, ((0, 0), (0, 4 - k)))
    return idx, w


class Peca:
    def __init__(s, nome, png, bbox, ossos_perm, esq, esp=36, juntas=(), deformadores=()):
        s.nome = nome
        im = np.array(Image.open(png).convert("RGBA"))
        s.off = (bbox[0], bbox[1])
        a = im[..., 3:].astype(np.float32) / 255
        pre = np.dstack([im[..., :3] * a, im[..., 3:]]).astype(np.uint8)   # premultiplicado
        s.tex = pre[..., [2, 1, 0, 3]].copy()                            # BGRA
        s.V, s.tris = gerar_malha(im[..., 3], s.off, esp, juntas)
        s.uv = (s.V - np.array(s.off)).astype(np.float32)
        s.osso_idx = [esq.idx[n] for n in ossos_perm]
        perm = [esq.ossos[i] for i in s.osso_idx]
        idx, w = pesos_calor(s.V, s.tris, perm, esp)
        s.bi = np.array(s.osso_idx)[idx]; s.bw = w
        s.deformadores = list(deformadores)
        s.visivel = True; s.opac = 1.0

    def vertices(s, mats, params):
        V = s.V.copy()
        for f in s.deformadores: V = V + f(s.V, params)
        P = np.c_[V, np.ones(len(V))]
        out = np.zeros((len(V), 2))
        for k in range(4):
            M = mats[s.bi[:, k]]                       # (n,3,3)
            out += s.bw[:, k:k + 1] * np.einsum("nij,nj->ni", M, P)[:, :2]
        return out


# ------------------------------------------------------------------ renderização
class Camera:
    def __init__(s, escala, tx, ty, ss=2):
        s.s, s.tx, s.ty, s.ss = escala, tx, ty, ss
    def __call__(s, P):
        return (np.asarray(P) * s.s + np.array([s.tx, s.ty])) * s.ss


def _rasteriza_peca(peca, VS, W, H):
    """Desenha a malha deformada num buffer BGRA premultiplicado. Devolve (buf, x0, y0) ou None."""
    x0 = int(max(0, math.floor(VS[:, 0].min()) - 2)); y0 = int(max(0, math.floor(VS[:, 1].min()) - 2))
    x1 = int(min(W, math.ceil(VS[:, 0].max()) + 3)); y1 = int(min(H, math.ceil(VS[:, 1].max()) + 3))
    if x1 <= x0 or y1 <= y0: return None
    buf = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    D = (VS - np.array([x0, y0])).astype(np.float32)
    for t in peca.tris:
        d = D[t]
        bx0 = max(0, int(math.floor(d[:, 0].min())) - 1); by0 = max(0, int(math.floor(d[:, 1].min())) - 1)
        bx1 = min(buf.shape[1], int(math.ceil(d[:, 0].max())) + 2); by1 = min(buf.shape[0], int(math.ceil(d[:, 1].max())) + 2)
        w, h = bx1 - bx0, by1 - by0
        if w <= 0 or h <= 0: continue
        dl = d - np.array([bx0, by0], np.float32)
        A = cv2.getAffineTransform(peca.uv[t], dl)
        warped = cv2.warpAffine(peca.tex, A, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        mask = np.zeros((h, w), np.uint8)
        q = np.round(dl * 16).astype(np.int32)
        cv2.fillConvexPoly(mask, q, 255, cv2.LINE_8, 4)
        cv2.polylines(mask, [q], True, 255, 1, cv2.LINE_8, 4)
        sub = buf[by0:by1, bx0:bx1]
        sel = mask > 0
        sub[sel] = warped[sel]
    return buf, x0, y0


def compor_sobre(canvas, buf, x0, y0, opac=1.0):
    """canvas: float32 BGRA premultiplicado (H,W,4). Composição 'over'."""
    h, w = buf.shape[:2]
    reg = canvas[y0:y0 + h, x0:x0 + w]
    src = buf.astype(np.float32) / 255.0 * opac
    reg[:] = src + reg * (1.0 - src[..., 3:4])


class Personagem:
    def __init__(s, esq, pecas, ordem):
        s.esq, s.pecas, s.ordem = esq, pecas, ordem
        s.cadeias = []; s.params = {}; s.decalques = []   # decalques: f(canvas, cam, esq, params, rasterizar_ponto)
        s.depois = {}                                         # nome da peça -> [funções desenhando por cima dela]

    def render(s, cam, W, H):
        s.esq.fk()
        mats = s.esq.matrizes()
        canvas = np.zeros((H * cam.ss, W * cam.ss, 4), np.float32)
        for n in s.ordem:
            p = s.pecas[n]
            if not p.visivel: continue
            V = p.vertices(mats, s.params)
            VS = cam(V)
            r = _rasteriza_peca(p, VS, W * cam.ss, H * cam.ss)
            if r is None: continue
            buf, x0, y0 = r
            for f in s.depois.get(n, []): f(buf, (x0, y0), cam, s.esq, s.params)
            compor_sobre(canvas, buf, x0, y0, p.opac)
        out = cv2.resize(canvas, (W, H), interpolation=cv2.INTER_AREA) if cam.ss > 1 else canvas
        return out   # float BGRA premultiplicado 0..1 (x255)
