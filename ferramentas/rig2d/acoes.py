"""Biblioteca de ações do herói (vista 3/4) + montagem da máquina de estados.

Convenção de ângulos: rad, local ao pai, positivo = sentido horário na tela (y para baixo).
Braço de trás (bl_*) = o que oferece a mão (esquerda da tela). Braço da frente (br_*) = pendurado.
"""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from animacao import (Clipe, ClipeChaves, Pose, Parametro, Seguidor, Camada, Maquina, SUAVE, SOBRA, ANTECIPA, ANTECIPA_SOBRA, SAI, ENTRA, Facil,
                      com_antecipacao)

MASCARA_CIMA = ["peito", "pescoco", "cabeca", "bl_sup", "bl_ant", "bl_mao", "br_sup", "br_ant", "br_mao"]
MASCARA_BRACO = ["bl_sup", "bl_ant", "bl_mao"]


# ------------------------------------------------------------------ locomoção procedural (andar ↔ parado)
class ClipeAndar(Clipe):
    """Ciclo de caminhada com velocidade contínua 'vel' (0 parado … 1 andando). Pés por IK; respiração sempre ligada."""
    def __init__(s, periodo=1.0):
        s.periodo = periodo; s.fase = 0.0; s.t = 0.0; s.vel = 0.0; s.fal = 0.0

    def reset(s): pass          # a fase é contínua entre transições

    def passo(s, dt, ent):
        s.t = ent.get("t", s.t + dt)
        alvo = ent.get("vel", 0.0)
        s.vel += (alvo - s.vel) * min(1.0, dt * 5.0)                # aceleração suave (ease)
        s.fase += 2 * math.pi / s.periodo * dt * s.vel
        s.fal = ent.get("falando", 0.0)

    def pose(s):
        t, w, v, fal = s.t, s.fase, s.vel, s.fal
        P = Pose(); R = P.rot
        resp = 2 * math.pi * 0.28 * t
        bob = 15 * v * (1 - math.cos(2 * w)) / 2
        P.pos["root"] = (0.0, -bob + 6 + 2.0 * math.sin(resp))
        R["root"] = 0.018 * v * math.sin(w)
        R["espinha"] = -0.03 * v * math.sin(w + 0.3)
        R["peito"] = 0.012 * v * math.sin(w + 0.9) + 0.01 * math.sin(resp)
        P.esc["peito"] = 1.0 + 0.006 * math.sin(resp)
        R["pescoco"] = -0.35 * (R["root"] + R["espinha"] + R["peito"])
        R["cabeca"] = 0.025 * v * math.sin(w + 0.9) + fal * (0.03 * math.sin(2 * math.pi * 1.7 * t) + 0.015 * math.sin(2 * math.pi * 0.6 * t)) - 0.01
        R["bl_sup"] = -0.04 - 0.17 * v * math.cos(w) + 0.02 * math.sin(resp)
        R["bl_ant"] = 0.05 * v * math.sin(w + 0.8) + 0.10
        R["bl_mao"] = 0.12 * v * math.sin(w + 1.3)
        R["br_sup"] = 0.02 + 0.14 * v * math.cos(w) + 0.015 * math.sin(resp + 1)
        R["br_ant"] = 0.05 + 0.08 * v * math.sin(w + 0.7) + 0.05 * v * (1 + math.cos(w))
        R["br_mao"] = 0.10 * v * math.sin(w + 1.5)
        A = 190.0; LIFT = 62.0 * v; sw = math.sin(w); sx = 85.0 * (1 - v)
        P.pes["lb"] = (1043 - A * v * math.cos(w) - sx, 1778 - LIFT * max(0.0, -sw) ** 0.8)
        P.pes["lf"] = (1043 + A * v * math.cos(w) + sx, 1752 - LIFT * max(0.0, sw) ** 0.8)
        P.tilt["lb"] = v * (0.28 * math.cos(w) - 0.10 * max(0, -sw))
        P.tilt["lf"] = v * (-0.28 * math.cos(w) - 0.10 * max(0, sw))
        P.par["barra_amp"] = 4 + v * (7 + 5 * abs(sw)); P.par["barra_fase"] = w; P.par["barra_vento"] = 6 * v * math.cos(w)
        P.par["vento"] = 50 * v * math.cos(w + 0.4)
        return P


# ------------------------------------------------------------------ ações de tronco/braço (camada "cima")
def _ciclo(keys, **kw): return ClipeChaves(keys, loop=True, **kw)

def acenar(n=3):
    """Levanta o braço (com antecipação), balança a mão n vezes e abaixa com sobra. Termina sozinho."""
    ks = {0.0: {"bl_sup": -0.04, "bl_ant": 0.10, "bl_mao": 0.0, "peito": 0.0, "cabeca": 0.0}}
    ks[0.20] = {"bl_sup": -0.22, "bl_ant": 0.0, "_f": SUAVE}                         # antecipação (recua)
    ks[0.75] = {"bl_sup": 2.25, "bl_ant": -0.12, "bl_mao": 0.0, "peito": -0.02, "cabeca": 0.04, "_f": SOBRA}
    t = 0.75
    for i in range(n):
        ks[t + 0.22] = {"bl_ant": -0.65, "bl_mao": -0.30, "_f": SUAVE}
        ks[t + 0.44] = {"bl_ant": 0.30, "bl_mao": 0.30, "_f": SUAVE}
        t += 0.44
    ks[t + 0.25] = {"bl_ant": -0.15, "bl_mao": 0.0, "_f": SUAVE}
    ks[t + 0.85] = {"bl_sup": -0.04, "bl_ant": 0.10, "bl_mao": 0.0, "peito": 0.0, "cabeca": 0.0, "_f": SUAVE}
    return ClipeChaves(ks, loop=False)

def apontar(dur=2.2):
    """Estica o braço à frente e aponta; segura com leve vida; volta."""
    return ClipeChaves({
        0.0: {"bl_sup": -0.04, "bl_ant": 0.10, "bl_mao": 0.0, "peito": 0.0, "cabeca": 0.0},
        0.22: {"bl_sup": -0.16, "bl_ant": 0.05, "peito": 0.03, "_f": SUAVE},
        0.65: {"bl_sup": 1.20, "bl_ant": -0.10, "bl_mao": 0.0, "peito": -0.05, "cabeca": -0.07, "_f": ANTECIPA_SOBRA},
        dur - 0.7: {"bl_sup": 1.24, "bl_ant": -0.08, "bl_mao": 0.0, "peito": -0.055, "cabeca": -0.07, "_f": SUAVE},
        dur: {"bl_sup": -0.04, "bl_ant": 0.10, "bl_mao": 0.0, "peito": 0.0, "cabeca": 0.0, "_f": SUAVE},
    }, loop=False)

def oferecer(dur=3.0):
    """Palma aberta oferecida (o gesto do desenho original); balança de leve enquanto segura."""
    return ClipeChaves({
        0.0: {"bl_sup": -0.04, "bl_ant": 0.10, "bl_mao": 0.0},
        0.5: {"bl_sup": -0.29, "bl_ant": 1.05, "bl_mao": -0.15, "_f": SOBRA},
        dur - 0.6: {"bl_sup": -0.27, "bl_ant": 1.02, "bl_mao": -0.12, "_f": SUAVE},
        dur: {"bl_sup": -0.04, "bl_ant": 0.10, "bl_mao": 0.0, "_f": SUAVE},
    }, loop=False, ruido={"bl_mao": (0.05, 1.3), "bl_ant": (0.02, 0.7)})

def reverencia(dur=2.4):
    """Inclina o tronco e a cabeça para frente e volta (reverência / agradecimento)."""
    return ClipeChaves({
        0.0: {"espinha": 0.0, "peito": 0.0, "cabeca": 0.0, "br_sup": 0.02},
        0.20: {"espinha": -0.02, "peito": -0.02, "cabeca": 0.03, "_f": SUAVE},
        0.85: {"espinha": -0.20, "peito": -0.14, "cabeca": -0.14, "br_sup": 0.08, "_f": ANTECIPA},
        dur - 0.9: {"espinha": -0.21, "peito": -0.14, "cabeca": -0.14, "br_sup": 0.08, "_f": SUAVE},
        dur: {"espinha": 0.0, "peito": 0.0, "cabeca": 0.0, "br_sup": 0.02, "_f": SOBRA},
    }, loop=False)

def surpresa(dur=2.0):
    """Recuo rápido do tronco, cabeça para trás, braço sobe um pouco (susto/assombro), depois relaxa."""
    return ClipeChaves({
        0.0: {"espinha": 0.0, "peito": 0.0, "cabeca": 0.0, "bl_sup": -0.04, "bl_ant": 0.10},
        0.10: {"espinha": -0.03, "peito": -0.02, "_f": SUAVE},
        0.32: {"espinha": 0.06, "peito": 0.06, "cabeca": 0.08, "bl_sup": 0.45, "bl_ant": 0.45, "_f": SOBRA},
        dur - 0.8: {"espinha": 0.05, "peito": 0.05, "cabeca": 0.07, "bl_sup": 0.40, "bl_ant": 0.40, "_f": SUAVE},
        dur: {"espinha": 0.0, "peito": 0.0, "cabeca": 0.0, "bl_sup": -0.04, "bl_ant": 0.10, "_f": SUAVE},
    }, loop=False)

def gesticular():
    """Fala com a mão: balanço contínuo e orgânico do braço que oferece (loop, sem fim)."""
    return ClipeChaves({
        0.0: {"bl_sup": -0.30, "bl_ant": 0.95, "bl_mao": -0.15},
        0.9: {"bl_sup": -0.20, "bl_ant": 1.15, "bl_mao": 0.05, "_f": SUAVE},
        1.7: {"bl_sup": -0.34, "bl_ant": 0.80, "bl_mao": -0.2, "_f": SUAVE},
        2.6: {"bl_sup": -0.30, "bl_ant": 0.95, "bl_mao": -0.15, "_f": SUAVE},
    }, loop=True)

ACOES = {"acenar": acenar, "apontar": apontar, "oferecer": oferecer, "reverencia": reverencia, "surpresa": surpresa, "gesticular": gesticular}


# ------------------------------------------------------------------ parâmetros estilo Live2D / Inochi2D
PARAMETROS = [
    # cabeça: 'virar' também aciona o deformador de malha do rosto (heroi.virar_cabeca)
    Parametro("virar", {-1.0: {"cabeca": 0.05, "pescoco": 0.02}, 0.0: {}, 1.0: {"cabeca": -0.05, "pescoco": -0.02}}),
    Parametro("inclinar", {-1.0: {"cabeca": -0.14}, 0.0: {}, 1.0: {"cabeca": 0.14}}),
    # olhar 2D (x: esquerda/direita, y: baixo/cima): mistura virar + inclinar + pescoço
    Parametro("olhar_x", {(-1.0, 0.0): {"@virar": -0.8}, (0.0, 0.0): {}, (1.0, 0.0): {"@virar": 0.8},
                         (-1.0, -1.0): {"@virar": -0.8, "cabeca": 0.06}, (0.0, -1.0): {"cabeca": 0.06}, (1.0, -1.0): {"@virar": 0.8, "cabeca": 0.06},
                         (-1.0, 1.0): {"@virar": -0.8, "cabeca": -0.07}, (0.0, 1.0): {"cabeca": -0.07}, (1.0, 1.0): {"@virar": 0.8, "cabeca": -0.07}},
              nome_y="olhar_y"),
    Parametro("respirar_fundo", {0.0: {}, 1.0: {"peito": -0.02, "espinha": 0.01, "bl_sup": -0.03, "br_sup": 0.02}}),
]


MOCAP = os.path.join(os.path.dirname(__file__), "mocap")
OSSOS_CIMA_BVH = ["bl_sup", "bl_ant", "bl_mao", "cabeca", "peito", "espinha"]


def criar_maquina(mocap=True):
    from heroi import esqueleto
    from bvh import ClipeBVH
    base_est = {"andar": ClipeAndar()}
    estados = {n: f() for n, f in ACOES.items()}
    if mocap and os.path.isdir(MOCAP):
        esq = esqueleto()
        for n in ("acenar", "apontar", "pensar"):          # braço/tronco por mocap retargetado, na camada de cima
            estados[n + "_bvh"] = ClipeBVH(os.path.join(MOCAP, n + ".bvh"), esq, ossos=OSSOS_CIMA_BVH, pes=False, loop=False)
        pular = ClipeBVH(os.path.join(MOCAP, "pular.bvh"), esq, loop=False, ao_terminar="andar")   # corpo todo: pés/quadril por IK
        base_est["pular_bvh"] = pular
    base = Camada("base", base_est, "andar")
    cima = Camada("cima", estados, None, mascara=MASCARA_CIMA)
    seg = Seguidor({"cabeca": (3.2, 0.55), "bl_ant": (3.8, 0.6), "bl_mao": (4.5, 0.5), "br_ant": (3.8, 0.6), "br_mao": (4.5, 0.5)})
    return Maquina([base, cima], PARAMETROS, seg)


def nova_acao(m, nome, **kw):
    """Dispara uma ação (recria o clipe com os parâmetros dados, ex.: acenar(n=4))."""
    c = m.camadas["cima"]
    if kw: c.estados[nome] = ACOES[nome](**kw)
    else: c.estados[nome] = ACOES[nome]()
    c.nome_atual = None
    m.ir("cima", nome, 0.25)
