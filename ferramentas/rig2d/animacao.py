"""Camada de animação do rig 2D (independente do personagem).

Reúne o melhor de cada referência, reimplementado do zero (sem copiar código de terceiros):
  - Curvas Bézier de easing por segmento, antecipação e "sobra" (Harmony / Spine / Moho)     -> `Facil`, `ClipeChaves`
  - Parâmetros 1D/2D que acionam várias deformações juntas (Live2D / Inochi2D / Moho smart bones) -> `Parametro`
  - Máquina de estados com camadas, máscara de ossos e transições com mistura (Rive, Spine tracks) -> `Maquina`
  - Follow-through por mola de 2ª ordem nos ossos distais (overlap do Harmony)                 -> `Seguidor`
  - Clipes vindos de mocap BVH retargetado (AnimatedDrawings)                                  -> `bvh.py`
Um clipe devolve uma `Pose` (ângulos locais por osso, alvos de pés, parâmetros). Quem aplica no esqueleto é `heroi.aplicar`.
"""
import math
import numpy as np


# ------------------------------------------------------------------ easing (Bézier cúbica estilo CSS)
class Facil:
    """Curva Bézier cúbica (x1,y1,x2,y2). y fora de [0,1] dá antecipação (y<0) ou sobra/overshoot (y>1)."""
    def __init__(s, x1, y1, x2, y2):
        s.p = (x1, y1, x2, y2)

    def _bez(s, a, b, t):
        u = 1 - t
        return 3 * u * u * t * a + 3 * u * t * t * b + t ** 3

    def __call__(s, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        x1, y1, x2, y2 = s.p
        t = x
        for _ in range(8):                               # Newton
            f = s._bez(x1, x2, t) - x
            d = 3 * (1 - t) ** 2 * x1 + 6 * (1 - t) * t * (x2 - x1) + 3 * t * t * (1 - x2)
            if abs(d) < 1e-6: break
            t -= f / d
        lo, hi = 0.0, 1.0
        t = min(max(t, 0.0), 1.0)
        for _ in range(20):                               # refino por bisseção
            f = s._bez(x1, x2, t) - x
            if abs(f) < 1e-6: break
            if f > 0: hi = t
            else: lo = t
            t = (lo + hi) / 2
        return s._bez(y1, y2, t)


LINEAR = Facil(0, 0, 1, 1)
SUAVE = Facil(0.42, 0, 0.58, 1)          # entra e sai devagar
ENTRA = Facil(0.42, 0, 1, 1)
SAI = Facil(0, 0, 0.58, 1)
SOBRA = Facil(0.34, 1.45, 0.64, 1)       # passa um pouco do alvo e volta (follow-through)
ANTECIPA = Facil(0.5, -0.45, 0.35, 1.0)  # recua antes de ir (antecipação)
ANTECIPA_SOBRA = Facil(0.5, -0.45, 0.3, 1.45)


# ------------------------------------------------------------------ pose
class Pose:
    """rot: ângulo local por osso (rad); pos: deslocamento (dx,dy) por osso; esc: escala por osso;
    pes: alvo de cada pé no mundo (x,y) p/ IK; tilt: ângulo mundial do pé; par: parâmetros (olho, boca, virar, vento…)."""
    def __init__(s):
        s.rot = {}; s.pos = {}; s.esc = {}; s.pes = {}; s.tilt = {}; s.par = {}

    def copia(s):
        p = Pose()
        p.rot = dict(s.rot); p.pos = dict(s.pos); p.esc = dict(s.esc); p.pes = dict(s.pes); p.tilt = dict(s.tilt); p.par = dict(s.par)
        return p


def _lerp(a, b, w): return a + (b - a) * w


def misturar(A, B, w, mascara=None, manter=False):
    """Mistura A→B com peso w (0..1). Canal ausente em um lado: rot/pos/esc contam como neutro; alvos de pé usam o lado que existe.
    mascara: conjunto de ossos afetados (None = todos)."""
    P = A.copia()
    def ok(k): return mascara is None or k in mascara
    for k in set(A.rot) | set(B.rot):
        if ok(k) and not (manter and k not in B.rot): P.rot[k] = _lerp(A.rot.get(k, 0.0), B.rot.get(k, 0.0), w)
    for k in set(A.pos) | set(B.pos):
        if ok(k) and not (manter and k not in B.pos):
            a = np.asarray(A.pos.get(k, (0.0, 0.0))); b = np.asarray(B.pos.get(k, (0.0, 0.0)))
            P.pos[k] = tuple(_lerp(a, b, w))
    for k in set(A.esc) | set(B.esc):
        if ok(k) and not (manter and k not in B.esc): P.esc[k] = _lerp(A.esc.get(k, 1.0), B.esc.get(k, 1.0), w)
    for dic, nome in ((P.pes, "pes"), (P.tilt, "tilt")):
        a, b = getattr(A, nome), getattr(B, nome)
        for k in set(a) | set(b):
            if mascara is not None and not any(o.startswith(k) for o in mascara): continue
            if k in a and k in b: dic[k] = tuple(_lerp(np.asarray(a[k]), np.asarray(b[k]), w)) if nome == "pes" else _lerp(a[k], b[k], w)
            else: dic[k] = (b if k in b else a)[k]
    for k in set(A.par) | set(B.par):
        if not (manter and k not in B.par): P.par[k] = _lerp(A.par.get(k, 0.0), B.par.get(k, 0.0), w)
    return P


# ------------------------------------------------------------------ clipes
class Clipe:
    """Interface: passo(dt, entradas) avança; pose() devolve Pose. loop/dur definem o fim (ao_terminar = nome do próximo estado)."""
    loop = True; dur = None; ao_terminar = None
    def reset(s): s.t = 0.0
    def passo(s, dt, entradas): s.t += dt
    def terminou(s): return (not s.loop) and s.dur is not None and s.t >= s.dur
    def pose(s): return Pose()


class ClipeChaves(Clipe):
    """Clipe por quadros-chave por canal. keys = {tempo: {canal: valor}}; canal = nome de osso (rot) ou '@param'.
    O segmento que CHEGA numa chave usa o easing dessa chave (campo especial '_f': Facil). Antecipação/sobra vêm do easing."""
    def __init__(s, keys, loop=False, ao_terminar=None, facil=SUAVE, ruido=None):
        s.keys = sorted(keys.items()); s.dur = s.keys[-1][0]; s.loop = loop; s.ao_terminar = ao_terminar
        s.facil = facil; s.t = 0.0
        s.tracks = {}
        for tt, d in s.keys:
            for c, v in d.items():
                if c == "_f": continue
                s.tracks.setdefault(c, []).append((tt, v, d.get("_f", facil)))
        s.ruido = ruido or {}     # {osso: (amplitude, hz)} respiração/vida parada ("moving hold")

    def pose(s):
        P = Pose()
        t = (s.t % s.dur) if (s.loop and s.dur) else min(s.t, s.dur)
        for c, tr in s.tracks.items():
            v = tr[0][1]
            if t >= tr[-1][0]: v = tr[-1][1]
            else:
                for (t0, v0, _), (t1, v1, f) in zip(tr, tr[1:]):
                    if t0 <= t <= t1:
                        v = _lerp(v0, v1, f((t - t0) / (t1 - t0))) if t1 > t0 else v1; break
                    if t < t0: v = v0; break
            if c.startswith("@"): P.par[c[1:]] = v
            else: P.rot[c] = v
        for o, (a, hz) in s.ruido.items():
            P.rot[o] = P.rot.get(o, 0.0) + a * math.sin(2 * math.pi * hz * s.t + hash(o) % 7)
        return P


def com_antecipacao(keys, osso, quantidade=0.08, tempo=0.18):
    """Insere uma chave de antecipação (recuo oposto ao movimento) antes da primeira mudança de um osso. Princípio nº1 da animação."""
    ts = sorted(keys)
    if len(ts) < 2: return keys
    v0 = keys[ts[0]].get(osso, 0.0); v1 = next((keys[t][osso] for t in ts[1:] if osso in keys[t]), v0)
    k = dict(keys); alvo = ts[0] + tempo
    d = dict(k.get(alvo, {})); d[osso] = v0 - math.copysign(quantidade, v1 - v0); k[alvo] = d
    return k


# ------------------------------------------------------------------ parâmetros (Live2D / Inochi2D)
class Parametro:
    """Um eixo (ou dois) que dirige várias deformações. pontos: {valor: {canal: delta}} (1D); a interpolação é linear entre pontos.
    Parametro2D usa duas entradas e interpolação bilinear. Os deltas SOMAM na pose (aditivo), como no Inochi2D."""
    def __init__(s, nome, pontos, nome_y=None):
        s.nome, s.nome_y, s.pontos = nome, nome_y, pontos

    @staticmethod
    def _pesos(vals, x):
        vals = sorted(vals)
        x = min(max(x, vals[0]), vals[-1])
        for a, b in zip(vals, vals[1:]):
            if a <= x <= b:
                w = 0.0 if b == a else (x - a) / (b - a)
                return {a: 1 - w, b: w}
        return {vals[0]: 1.0}

    def aplicar(s, pose):
        if s.nome_y is None:
            wx = s._pesos([k for k in s.pontos], pose.par.get(s.nome, 0.0))
            pares = [(k, w) for k, w in wx.items()]
        else:
            xs = sorted({k[0] for k in s.pontos}); ys = sorted({k[1] for k in s.pontos})
            wx = s._pesos(xs, pose.par.get(s.nome, 0.0)); wy = s._pesos(ys, pose.par.get(s.nome_y, 0.0))
            pares = [((a, b), wa * wb) for a, wa in wx.items() for b, wb in wy.items()]
        for k, w in pares:
            if w <= 1e-6: continue
            for c, d in s.pontos.get(k, {}).items():
                if c.startswith("@"): pose.par[c[1:]] = pose.par.get(c[1:], 0.0) + w * d
                else: pose.rot[c] = pose.rot.get(c, 0.0) + w * d


# ------------------------------------------------------------------ follow-through
class Seguidor:
    """Mola de 2ª ordem por osso: o ângulo final persegue o ângulo da pose com atraso e uma sobra leve (overlap)."""
    def __init__(s, config):          # {osso: (freq_hz, amortecimento)}
        s.cfg = config; s.x = {}; s.v = {}

    def aplicar(s, pose, dt):
        for o, (hz, z) in s.cfg.items():
            alvo = pose.rot.get(o, 0.0)
            if o not in s.x: s.x[o] = alvo; s.v[o] = 0.0
            w = 2 * math.pi * hz
            n = max(1, int(dt / (1 / 240) + 0.5)); h = dt / n
            for _ in range(n):
                a = w * w * (alvo - s.x[o]) - 2 * z * w * s.v[o]
                s.v[o] += a * h; s.x[o] += s.v[o] * h
            pose.rot[o] = s.x[o]


# ------------------------------------------------------------------ máquina de estados com camadas (Rive)
class _Nulo(Clipe):
    pass


class Camada:
    def __init__(s, nome, estados, inicial=None, mascara=None):
        s.nome, s.estados, s.mascara = nome, estados, (set(mascara) if mascara else None)
        s.atual = estados.get(inicial) if inicial else None
        s.nome_atual = inicial
        s.ant = None; s.tt = 1.0; s.dur_t = 0.0; s.facil = SUAVE
        if s.atual: s.atual.reset()

    def ir(s, nome, dur=0.35, facil=SUAVE):
        if nome == s.nome_atual: return
        s.ant = s.atual; s.atual = s.estados.get(nome) if nome else None
        if s.atual: s.atual.reset()
        s.nome_atual = nome; s.tt = 0.0; s.dur_t = max(dur, 1e-3); s.facil = facil

    def passo(s, dt, entradas):
        if s.ant: s.ant.passo(dt, entradas)
        if s.atual: s.atual.passo(dt, entradas)
        if s.tt < 1.0: s.tt = min(1.0, s.tt + dt / s.dur_t)
        if s.tt >= 1.0: s.ant = None

    def saida(s):
        """Devolve (Pose, peso). Peso 0 = camada sem efeito."""
        e = s.facil(s.tt) if s.tt < 1.0 else 1.0
        pa = s.atual.pose() if s.atual else None
        pp = s.ant.pose() if s.ant else None
        if pp is None and s.tt < 1.0 and not s.ant:     # veio do vazio
            return (pa, e) if pa else (None, 0.0)
        if s.tt >= 1.0: return (pa, 1.0) if pa else (None, 0.0)
        if pa and pp: return misturar(pp, pa, e), 1.0
        if pa: return pa, e
        if pp: return pp, 1.0 - e
        return None, 0.0


class Maquina:
    """Camada 'base' (corpo todo: andar/parado/mocap) + camadas extras com máscara (ex.: 'cima' = braços/cabeça).
    entradas: valores numéricos que os clipes leem (ex.: 'vel'). `regras` = [(camada, de, para, cond(entradas), dur)] — transições automáticas."""
    def __init__(s, camadas, parametros=(), seguidor=None, regras=()):
        s.camadas = {c.nome: c for c in camadas}; s.ordem = [c.nome for c in camadas]
        s.parametros = list(parametros); s.seg = seguidor; s.regras = list(regras)
        s.entradas = {}; s.t = 0.0; s.par_extra = {}

    def ir(s, camada, estado, dur=0.35, facil=SUAVE): s.camadas[camada].ir(estado, dur, facil)

    def passo(s, dt=1 / 30):
        s.t += dt
        s.entradas["t"] = s.t
        for c in s.camadas.values():
            c.passo(dt, s.entradas)
            if c.atual and c.atual.terminou() and c.atual.ao_terminar is not None:
                c.ir(c.atual.ao_terminar or None, 0.4)
            elif c.atual and c.atual.terminou() and c.atual.ao_terminar is None and not c.atual.loop:
                c.ir(None, 0.4)
        for (cam, de, para, cond, dur) in s.regras:
            c = s.camadas[cam]
            if (de is None or c.nome_atual == de) and cond(s.entradas): c.ir(para, dur)
        base = s.camadas[s.ordem[0]].saida()[0] or Pose()
        P = base.copia()
        for n in s.ordem[1:]:
            c = s.camadas[n]; pose, w = c.saida()
            if pose is None or w <= 1e-4: continue
            P = misturar(P, pose, w, c.mascara, manter=True)
        P.par.update(s.par_extra)            # parâmetros dirigidos de fora (olhar, virar, fala…)
        for p in s.parametros: p.aplicar(P)
        if s.seg: s.seg.aplicar(P, dt)
        return P
