"""Rig do personagem (vista 3/4 caminhando). Coordenadas = pixels da arte original (1958x2000)."""
import json, math, os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from motor import Esqueleto, Cadeia, Peca, Personagem, Camera, suave

DIR = os.path.join(os.path.dirname(__file__), "..", "..", "personagem", "caminhando")

# ------------------------------------------------------------------ esqueleto
def esqueleto():
    e = Esqueleto()
    e.add("root", None, (960, 1050), (960, 960))
    e.add("espinha", "root", (960, 960), (975, 700))
    e.add("peito", "espinha", (975, 700), (980, 470))
    e.add("pescoco", "peito", (960, 455), (955, 400))
    e.add("cabeca", "pescoco", (955, 400), (955, 100))
    e.add("cabelo_e", "cabeca", (850, 300), (842, 408))
    e.add("cabelo_d", "cabeca", (1120, 300), (1152, 400))
    # braço de trás (o que oferece a mão, à esquerda na tela)
    e.add("bl_sup", "peito", (815, 500), (700, 700))
    e.add("bl_ant", "bl_sup", (700, 700), (615, 930))
    e.add("bl_mao", "bl_ant", (615, 930), (420, 992))
    # braço da frente (pendurado, à direita na tela)
    e.add("br_sup", "peito", (1170, 490), (1255, 750))
    e.add("br_ant", "br_sup", (1255, 750), (1318, 1022))
    e.add("br_mao", "br_ant", (1318, 1030), (1345, 1215))
    # pernas
    e.add("lb_coxa", "root", (880, 1100), (862, 1440))
    e.add("lb_canela", "lb_coxa", (862, 1440), (815, 1775))
    e.add("lb_pe", "lb_canela", (815, 1775), (560, 1845))
    e.add("lf_coxa", "root", (1080, 1100), (1185, 1450))
    e.add("lf_canela", "lf_coxa", (1185, 1450), (1272, 1750))
    e.add("lf_pe", "lf_canela", (1272, 1760), (1160, 1895))
    # tecidos (cadeias com física)
    e.add("cf1", "root", (1160, 800), (1215, 1000))
    e.add("cf2", "cf1", (1215, 1000), (1275, 1200))
    e.add("cf3", "cf2", (1275, 1200), (1295, 1400))
    e.add("cb1", "root", (1015, 900), (1012, 1080))
    e.add("cb2", "cb1", (1012, 1080), (1018, 1262))
    e.add("fa1", "root", (850, 1100), (835, 1340))
    return e

PECAS = {   # nome: (ossos que influenciam, espaçamento da malha, juntas p/ refino)
    "braco_longe": (["peito", "bl_sup", "bl_ant", "bl_mao"], 30, [(815, 500), (700, 700), (615, 930)]),
    "perna_tras": (["lb_canela", "lb_pe"], 30, [(815, 1775)]),
    "perna_frente": (["lf_canela", "lf_pe"], 30, [(1272, 1760)]),
    "tunica": (["root", "espinha", "peito", "pescoco"], 46, [(960, 960), (975, 700)]),
    "cauda_faixa": (["root", "cf1", "cf2", "cf3"], 34, [(1215, 1000), (1275, 1200)]),
    "braco_perto": (["peito", "br_sup", "br_ant", "br_mao"], 30, [(1170, 490), (1255, 750), (1318, 1030)]),
    "faixa": (["espinha", "peito", "root", "fa1"], 40, [(975, 700), (960, 960)]),
    "cinto": (["root", "espinha", "cb1", "cb2"], 28, [(1015, 900), (1012, 1080)]),
    "cabeca": (["cabeca", "pescoco", "cabelo_e", "cabelo_d"], 36, [(955, 400), (850, 300), (1120, 300)]),
}

# ------------------------------------------------------------------ deformadores (antes do skinning)
def onda_barra(V, P):
    """Barra da túnica balança com a caminhada (estilo 'warp deformer' do Live2D)."""
    amp = P.get("barra_amp", 0.0); ph = P.get("barra_fase", 0.0)
    k = suave(1150, 1780, V[:, 1])
    dx = amp * k * np.sin(ph - V[:, 0] / 140.0) + P.get("barra_vento", 0.0) * k
    dy = 0.25 * amp * k * np.cos(ph * 2 - V[:, 0] / 120.0)
    return np.c_[dx, dy]

def construir(esp_scale=1.0):
    info = json.load(open(os.path.join(DIR, "partes.json")))
    esq = esqueleto()
    pecas = {}
    for n in info["ordem"]:
        ossos, esp, juntas = PECAS[n]
        deform = [onda_barra] if n == "tunica" else []
        pecas[n] = Peca(n, os.path.join(DIR, n + ".png"), info["partes"][n]["bbox"], ossos, esq, int(esp * esp_scale), juntas, deform)
    ch = Personagem(esq, pecas, info["ordem"])
    ch.cadeias = [
        Cadeia(esq, ["cf1", "cf2", "cf3"], rigidez=520, amort=0.92, grav=700),
        Cadeia(esq, ["cb1", "cb2"], rigidez=650, amort=0.92, grav=700),
        Cadeia(esq, ["fa1"], rigidez=760, amort=0.93, grav=500),
        Cadeia(esq, ["cabelo_e"], rigidez=900, amort=0.93, grav=500),
        Cadeia(esq, ["cabelo_d"], rigidez=900, amort=0.93, grav=500),
    ]
    esq.fk()
    # rosto procedural (piscar + visemas), preso ao osso da cabeça
    pele = _amostra_pele(info)
    ch.depois["cabeca"] = [lambda buf, o, cam, e, P: _rosto(buf, o, cam, e, P, pele)]
    return ch

def _amostra_pele(info):
    from PIL import Image
    im = np.array(Image.open(os.path.join(DIR, "cabeca.png")).convert("RGBA"))
    x0, y0 = info["partes"]["cabeca"]["bbox"][:2]
    reg = im[215 - y0:238 - y0, 905 - x0:925 - x0, :3].reshape(-1, 3)
    c = np.median(reg, 0)
    return (int(c[2]), int(c[1]), int(c[0]))   # BGR

CONTORNO = (28, 18, 40)          # BGR do traço escuro do desenho
OLHOS = [((902, 188), 24, 19), ((990, 186), 26, 19)]
BOCA = (952, 283)

def _pt(e, cam, off, pts):
    M = e["cabeca"].skin
    p = np.c_[np.asarray(pts, float), np.ones(len(pts))] @ M.T
    q = cam(p[:, :2]) - np.array(off)
    return np.round(q * 16).astype(np.int32)

def _rosto(buf, off, cam, e, P, pele):
    ss = cam.ss; s = cam.s * ss
    # --- olhos: pálpebra (pele) cobre de cima para baixo
    aberto = P.get("olho", 1.0)
    if aberto < 0.97:
        for (c, rx, ry) in OLHOS:
            ylid = c[1] - ry + (1 - aberto) * 2 * ry
            ang = np.linspace(math.pi, 2 * math.pi, 14)
            top = [(c[0] + (rx + 5) * math.cos(a), c[1] + (ry + 5) * math.sin(a)) for a in ang]
            base = [(c[0] + rx + 5, ylid), (c[0], ylid + 3 * (1 - aberto) + 2), (c[0] - rx - 5, ylid)]
            poly = top + base
            cv2.fillPoly(buf, [_pt(e, cam, off, poly)], (*pele, 255), cv2.LINE_AA, 4)
            ln = [(c[0] - rx, ylid + 1), (c[0] - rx / 2, ylid + 5 * (1 - aberto) + 3), (c[0], ylid + 6 * (1 - aberto) + 3),
                  (c[0] + rx / 2, ylid + 5 * (1 - aberto) + 3), (c[0] + rx, ylid + 1)]
            cv2.polylines(buf, [_pt(e, cam, off, ln)], False, (*CONTORNO, 255), max(1, int(3.2 * s)), cv2.LINE_AA, 4)
    # --- boca: abertura (0..1) e largura (0.7..1.4)
    a = P.get("boca", 0.0); l = P.get("boca_larg", 1.0)
    if a > 0.06:
        cx, cy = BOCA; rx = 30 * l; ry = 3 + 24 * a
        ang = np.linspace(0, 2 * math.pi, 28, endpoint=False)
        # formato de "D" invertido: lábio superior reto, inferior curvo
        pts = [(cx + rx * math.cos(t), cy - 2 + (ry * math.sin(t) if math.sin(t) > 0 else 0.35 * ry * math.sin(t))) for t in ang]
        cv2.fillPoly(buf, [_pt(e, cam, off, pts)], (*CONTORNO, 255), cv2.LINE_AA, 4)
        inn = [(cx + (rx - 4) * math.cos(t), cy - 2 + ((ry - 4) * math.sin(t) if math.sin(t) > 0 else 0.35 * (ry - 3) * math.sin(t))) for t in ang]
        cv2.fillPoly(buf, [_pt(e, cam, off, inn)], (38, 36, 112), cv2.LINE_AA, 4)
        if a > 0.25:   # dentes superiores
            dentes = [(cx - rx * 0.78, cy - 3), (cx + rx * 0.78, cy - 3), (cx + rx * 0.7, cy + 3 + 5 * a), (cx - rx * 0.7, cy + 3 + 5 * a)]
            cv2.fillPoly(buf, [_pt(e, cam, off, dentes)], (232, 238, 245, 255), cv2.LINE_AA, 4)
        if a > 0.4:    # língua
            ln = [(cx + (rx * 0.6) * math.cos(t), cy + ry * 0.55 + (ry * 0.28) * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
            cv2.fillPoly(buf, [_pt(e, cam, off, ln)], (90, 80, 200), cv2.LINE_AA, 4)


# ------------------------------------------------------------------ animação: caminhada + fala
def pose(ch, t, fase=0.0, vel=1.0, falando=0.0, gesto=0.0, vento=0.0):
    """Ajusta ossos/parâmetros no tempo t (s). fase: ângulo acumulado do ciclo de passos (rad); vel: 0 (parado) .. 1 (andando);
    falando: 0..1 (balanço da cabeça); gesto: 0..1 (braço de trás levanta, palma aberta)."""
    e = ch.esq; P = ch.params
    e.zerar()
    w = fase; v = vel
    resp = 2 * math.pi * 0.28 * t
    bob = 15 * v * (1 - math.cos(2 * w)) / 2
    e["root"].pos = np.array([0.0, -bob + 6 + 2.0 * math.sin(resp)])
    e["root"].rot = 0.018 * v * math.sin(w)
    e["espinha"].rot = -0.03 * v * math.sin(w + 0.3)
    e["peito"].rot = 0.012 * v * math.sin(w + 0.9) + 0.01 * math.sin(resp)
    e["peito"].esc = 1.0 + 0.006 * math.sin(resp)
    e["pescoco"].rot = -0.35 * (e["root"].rot + e["espinha"].rot + e["peito"].rot)
    e["cabeca"].rot = 0.025 * v * math.sin(w + 0.9) + falando * (0.03 * math.sin(2 * math.pi * 1.7 * t) + 0.015 * math.sin(2 * math.pi * 0.6 * t)) - 0.01
    ga = gesto
    e["bl_sup"].rot = -0.04 - 0.17 * v * math.cos(w) - 0.25 * ga + 0.02 * math.sin(resp)
    e["bl_ant"].rot = 0.05 * v * math.sin(w + 0.8) + 0.10 + 0.95 * ga
    e["bl_mao"].rot = 0.12 * v * math.sin(w + 1.3) - 0.15 * ga + 0.05 * ga * math.sin(2 * math.pi * 1.3 * t)
    e["br_sup"].rot = 0.02 + 0.14 * v * math.cos(w) + 0.015 * math.sin(resp + 1)
    e["br_ant"].rot = 0.05 + 0.08 * v * math.sin(w + 0.7) + 0.05 * v * (1 + math.cos(w))
    e["br_mao"].rot = 0.10 * v * math.sin(w + 1.5)
    e.fk()
    # pernas por IK (pés "plantados" no mundo, independentes do balanço do corpo)
    A = 190.0; LIFT = 62.0 * v
    sw = math.sin(w)
    sx = 85.0 * (1 - v)       # parado: pés lado a lado
    lb = (1043 - A * v * math.cos(w) - sx, 1778 - LIFT * max(0.0, -sw) ** 0.8)
    lf = (1043 + A * v * math.cos(w) + sx, 1752 - LIFT * max(0.0, sw) ** 0.8)
    e.ik2("lb_coxa", "lb_canela", lb, dobra=-1)
    e.ik2("lf_coxa", "lf_canela", lf, dobra=-1)
    e.fk()
    for nome, tilt in (("lb", v * (0.28 * math.cos(w) - 0.10 * max(0, -sw))), ("lf", v * (-0.28 * math.cos(w) - 0.10 * max(0, sw)))):
        pe = e[nome + "_pe"]; pai = e[nome + "_canela"]
        pe.rot = tilt - e.rot_total(pai)
    e.fk()
    # tecidos
    P["barra_amp"] = 4 + v * (7 + 5 * abs(sw)); P["barra_fase"] = w; P["barra_vento"] = 6 * v * math.cos(w)
    for c in ch.cadeias:
        c.passo(1 / 30, sub=4, vento=vento + 50 * v * math.cos(w + 0.4))
    e.fk()


def piscar(t, intervalo=3.4):
    """0..1 abertura dos olhos; pisca a cada ~3.4 s, dura ~0.17 s."""
    ph = (t % intervalo)
    d = 0.17
    if ph < d:
        x = ph / d
        return abs(2 * x - 1) ** 1.5 if x < 1 else 1.0
    return 1.0
