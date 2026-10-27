"""Artes holográficas reutilizáveis (2D, vista de cima ou de lado), feitas com as primitivas do Holo.

Peças genéricas: placa (área de jogo projetada), avatar (pessoa vista de cima), bola, veículo de cima,
foguete de lado, explosão, poeira em parallax, aberração cromática e varredura.
Todas recebem um tempo `t` para animar detalhes (anéis girando, pulsos, cintilação).
"""
import math

import numpy as np

from .holo import AMARELO, AZUL, BRANCO, CIANO, LARANJA, MAGENTA, VERDE, VERMELHO, clareia


def _rot(pts, ang, c=(0, 0)):
    ca, sa = math.cos(ang), math.sin(ang)
    P = np.asarray(pts, float)
    return np.c_[c[0] + P[:, 0] * ca - P[:, 1] * sa, c[1] + P[:, 0] * sa + P[:, 1] * ca]


def _elipse(c, rx, ry, ang=0.0, n=36):
    k = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return _rot(np.c_[rx * np.cos(k), ry * np.sin(k)], ang, c)


def _cap(c, comp, raio, ang, n=10):
    """Cápsula (retângulo de pontas redondas) centrada em c, comprimento ao longo de ang."""
    meio = comp / 2 - raio
    pts = [(meio + raio * math.cos(a), raio * math.sin(a)) for a in np.linspace(-math.pi / 2, math.pi / 2, n)]
    pts += [(-meio + raio * math.cos(a), raio * math.sin(a)) for a in np.linspace(math.pi / 2, 3 * math.pi / 2, n)]
    return _rot(pts, ang, c)


# ------------------------------------------------------------------ ambiente

def poeira(h, t, cor=CIANO, n=70, semente=1, alfa=0.5):
    """Partículas de 'poeira de luz' flutuando, em três profundidades (parallax com a câmera)."""
    rng = np.random.default_rng(semente)
    ctx = h.ctx
    cx, cy = h.cam.centro
    for k in range(n):
        prof = (k % 3 + 1) / 3
        u, v = rng.random(), rng.random()
        vel = rng.uniform(4, 14)
        x = (u * h.w - cx * h.cam.escala * 0.2 * prof + math.sin(t * 0.3 + k) * 20) % h.w
        y = (v * h.h + t * vel * prof - (-cy) * h.cam.escala * 0.2 * prof) % h.h
        a = alfa * prof * (0.5 + 0.5 * math.sin(t * 2 + k * 1.7))
        ctx.set_source_rgba(*cor, a)
        ctx.arc(x, y, 0.8 + 1.6 * prof, 0, 2 * math.pi)
        ctx.fill()


def placa(h, x0, y0, x1, y1, t, cor=CIANO, rotulo=None, faixas=None):
    """Plataforma holográfica retangular: borda brilhante, faixas, colchetes nos cantos, medidas."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    h.forma(pts, cor, 0.5, 2, 0.025)
    if faixas:
        passo = faixas
        y = y0
        k = 0
        while y < y1 - 1e-6:
            if k % 2 == 0:
                yb = min(y + passo, y1)
                h.forma([(x0, y), (x1, y), (x1, yb), (x0, yb)], cor, 0.25, 0.1, 0.05, gradiente=False)
            y += passo
            k += 1
    L = min(x1 - x0, y1 - y0) * 0.08
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1)):
        h.linha([(cx, cy + sy * L), (cx, cy), (cx + sx * L, cy)], clareia(cor, 0.3), 4, 0.9)
    # varredura: uma linha clara que percorre a placa
    ys = y0 + ((t * 0.35) % 1.0) * (y1 - y0)
    h.linha([(x0, ys), (x1, ys)], cor, 2, 0.25, halo=True)
    if rotulo:
        h.texto(rotulo, ((x0 + x1) / 2, y0 - 0.45), 18, cor, 0.7)


def medida(h, a, b, texto, cor=CIANO, desloca=0.6):
    """Cota técnica entre dois pontos (linha com batentes + texto)."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    nx, ny = -math.sin(ang) * desloca, math.cos(ang) * desloca
    A, B = (a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny)
    h.linha([A, B], cor, 1.2, 0.45, halo=False)
    for p in (A, B):
        h.linha([(p[0] - ny * 0.3, p[1] + nx * 0.3), (p[0] + ny * 0.3, p[1] - nx * 0.3)], cor, 1.2, 0.45, halo=False)
    h.texto(texto, ((A[0] + B[0]) / 2 + nx * 0.6, (A[1] + B[1]) / 2 + ny * 0.6), 15, cor, 0.6)


# ------------------------------------------------------------------ personagens

# Esqueleto em coordenadas locais (+x = frente). Mesma topologia nas duas poses -> dá para interpolar.
_EM_PE = {"cab": (0.04, 0), "oe": (0, 0.25), "od": (0, -0.25), "ce": (0.1, 0.36), "cd": (0.1, -0.36),
          "me": (0.24, 0.33), "md": (0.24, -0.33), "qe": (-0.02, 0.1), "qd": (-0.02, -0.1),
          "pe": (0.0, 0.13), "pd": (0.0, -0.13), "ta": (0, 0.25), "tb": (0, -0.25), "tr": 0.12}
_MERGULHO = {"cab": (0.62, 0), "oe": (0.38, 0.2), "od": (0.38, -0.2), "ce": (0.72, 0.26), "cd": (0.72, -0.26),
             "me": (1.05, 0.2), "md": (1.05, -0.2), "qe": (-0.38, 0.11), "qd": (-0.38, -0.11),
             "pe": (-0.95, 0.2), "pd": (-0.95, -0.2), "ta": (-0.4, 0), "tb": (0.4, 0), "tr": 0.19}


def _pose(k, passo, bracos):
    P = {}
    for nome, a in _EM_PE.items():
        b = _MERGULHO[nome]
        if nome == "tr":
            P[nome] = a + (b - a) * k
        else:
            P[nome] = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
    if passo is not None and k < 0.5:  # pés e braços alternam na corrida
        for lado, fase in (("e", 0.0), ("d", math.pi)):
            s = math.sin(passo * 2 * math.pi + fase)
            x, y = P["p" + lado]
            P["p" + lado] = (x + 0.26 * s, y)
            x, y = P["m" + lado]
            P["m" + lado] = (x - 0.1 * s, y)
    if bracos and k < 0.5:  # braços abertos (goleiro esperando)
        for lado, sinal in (("e", 1), ("d", -1)):
            P["c" + lado] = (0.12, sinal * (0.36 + 0.12 * bracos))
            P["m" + lado] = (0.22 - 0.05 * bracos, sinal * (0.33 + 0.3 * bracos))
    return P


def avatar(h, c, ang, cor, t, rotulo=None, alfa=1.0, bracos=0.0, mergulho=0.0, base=True, detalhe=True,
           corpo_ang=None, passo=None, escala=1.35, lado_mergulho=1):
    """Pessoa vista de cima, desenhada como esqueleto holográfico.

    ang: para onde olha/corre (rad, 0 = +x).  corpo_ang: para onde os ombros apontam (a finta).
    bracos 0-1: abre os braços.  mergulho 0-1: deita o corpo para o lado `lado_mergulho` (+1 = +x).
    passo: fase da corrida (None = parado). Espessuras acompanham o zoom (detalhe nítido de perto)."""
    e = escala
    k = suave(mergulho)
    frente = ang if corpo_ang is None else corpo_ang
    alvo_ang = 0.0 if lado_mergulho > 0 else math.pi
    giro = frente + (_ang_dif(alvo_ang, frente)) * k
    P = _pose(k, passo, bracos)
    W = lambda nome: _rot([(P[nome][0] * e, P[nome][1] * e)], giro, c)[0]
    lw = max(1.6, h.px(0.035 * e))        # espessura base em px, proporcional ao zoom
    claro = clareia(cor, 0.25)
    h.ponto_luz(c, h.px(0.9 * e), cor, (0.14 if passo is None else 0.07) * alfa)
    if base and k < 0.5 and passo is None:
        r = 0.6 * e
        h.circulo(c, r, cor, 0.25 * alfa, lw * 0.4, 0.02)
        for i in range(4):
            a0 = t * 1.6 + i * math.pi / 2
            h.linha([(c[0] + (r + 0.1 * e) * math.cos(u), c[1] + (r + 0.1 * e) * math.sin(u))
                     for u in np.linspace(a0, a0 + 0.9, 8)], cor, lw * 0.6, 0.5 * alfa, halo=False)
        ponta = _rot([(r + 0.34 * e, 0), (r + 0.14 * e, 0.14 * e), (r + 0.14 * e, -0.14 * e)], ang, c)
        h.forma(ponta, cor, 0.8 * alfa, lw * 0.4, 0.4)
    # pernas e pés
    for l in "ed":
        h.linha([W("q" + l), W("p" + l)], cor, lw * 1.3, 0.7 * alfa)
        h.forma(_elipse(W("p" + l), 0.11 * e, 0.055 * e, giro), cor, 0.9 * alfa, lw * 0.45, 0.2, oclusor=True)
    # tronco
    ta, tb = W("ta"), W("tb")
    comp = math.hypot(tb[0] - ta[0], tb[1] - ta[1]) + 2 * P["tr"] * e
    meio = ((ta[0] + tb[0]) / 2, (ta[1] + tb[1]) / 2)
    ang_t = math.atan2(tb[1] - ta[1], tb[0] - ta[0])
    h.forma(_cap(meio, comp, P["tr"] * e, ang_t), cor, alfa, lw * 0.75, 0.14, oclusor=True)
    if detalhe and e * h.cam.escala > 90:   # gola e número só aparecem de perto
        h.linha([W("oe"), W("od")], cor, lw * 0.35, 0.5 * alfa, halo=False)
    # braços: ombro -> cotovelo -> mão
    for l in "ed":
        h.linha([W("o" + l), W("c" + l), W("m" + l)], cor, lw * 1.0, 0.95 * alfa)
        rm = (0.065 + 0.035 * k + 0.02 * bracos) * e
        h.circulo(W("m" + l), rm, claro, alfa, lw * 0.45, 0.35, oclusor=True)
    # cabeça: contorno + 'cabelo' na nuca (mostra para onde está virada)
    cb = W("cab")
    h.circulo(cb, 0.14 * e, claro, alfa, lw * 0.6, 0.1, oclusor=True)
    nuca = [(cb[0] + 0.13 * e * math.cos(giro + u), cb[1] + 0.13 * e * math.sin(giro + u))
            for u in np.linspace(math.pi * 0.55, math.pi * 1.45, 12)]
    h.linha(nuca, cor, lw * 1.1, alfa, halo=False)
    if rotulo:
        h.texto(rotulo, (c[0], c[1] + 1.0 * e), max(14, h.px(0.16 * e)), claro, 0.9 * alfa)


def _ang_dif(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def suave(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def bola(h, c, t, alfa=1.0, rastro=None, cor=BRANCO, raio=0.16):
    if rastro is not None and len(rastro) > 1:
        h.rastro(rastro, cor, 6, 0.9 * alfa)
        for i, p in enumerate(rastro[::3]):  # faíscas no rastro
            h.ponto_luz((p[0] + 0.08 * math.sin(i * 3.1 + t * 9), p[1]), 3, CIANO, 0.5 * alfa * i / max(len(rastro) / 3, 1))
    h.ponto_luz(c, 26, cor, 0.55 * alfa)
    h.circulo(c, raio, cor, alfa, 2, 0.5)
    for i in range(5):  # malha de gomos girando
        a = t * 6 + i * 2 * math.pi / 5
        p = (c[0] + raio * 0.55 * math.cos(a), c[1] + raio * 0.55 * math.sin(a))
        h.linha([c, p], cor, 1, 0.6 * alfa, halo=False)


def veiculo_topo(h, c, ang, comp, larg, cor, t, alfa=1.0, farois=True, re=False, base=False):
    """Carro visto de cima: carroceria, para-brisa, faróis com cone de luz, lanternas."""
    caixa = _cap(c, comp, larg / 2 * 0.9, ang, n=6)
    h.forma(caixa, cor, alfa, 2.4, 0.2)
    cab = _rot([(-0.1 * comp, -larg * 0.36), (0.18 * comp, -larg * 0.33), (0.18 * comp, larg * 0.33),
                (-0.1 * comp, larg * 0.36)], ang, c)
    h.forma(cab, clareia(cor, 0.3), 0.8 * alfa, 1.4, 0.25)
    if farois:
        for lado in (-1, 1):
            f = _rot([(comp * 0.47, lado * larg * 0.3)], ang, c)[0]
            h.ponto_luz(f, 7, BRANCO, alfa)
            h.cone(f, ang, 0.5, comp * 0.9, clareia(cor, 0.6), 0.18 * alfa)
    for lado in (-1, 1):
        r = _rot([(-comp * 0.48, lado * larg * 0.3)], ang, c)[0]
        h.ponto_luz(r, 8 if re else 6, BRANCO if re else VERMELHO, alfa)


def foguete_lado(h, c, ang, escala, cor, t, alfa=1.0, motor=0.0):
    """Foguete de perfil: casco, janela, aletas, chama pulsante. ang = inclinação (rad, 0 = de pé)."""
    corpo = [(0, 5.0), (0.8, 3.6), (0.8, 0.6), (1.3, 0), (-1.3, 0), (-0.8, 0.6), (-0.8, 3.6)]
    rot = lambda pts: _rot(np.asarray(pts) * escala, -ang, c)
    if motor > 0.05:
        f = 0.85 + 0.15 * math.sin(t * 40 + c[0] * 3)
        comp = (1.2 + 4.5 * motor * f)
        h.forma(rot([(-0.6, 0), (0.6, 0), (0, -comp)]), LARANJA, alfa, 2, 0.45)
        h.forma(rot([(-0.3, 0), (0.3, 0), (0, -comp * 0.6)]), AMARELO, alfa, 1.5, 0.6)
        h.ponto_luz(rot([(0, -0.4)])[0], 18 * motor + 6, LARANJA, alfa)
    h.forma(rot(corpo), cor, alfa, 2.4, 0.22)
    h.linha(rot([(-0.8, 1.6), (0.8, 1.6)]), cor, 1.2, 0.5 * alfa, halo=False)
    h.circulo(rot([(0, 2.7)])[0], 0.35 * escala, clareia(cor, 0.5), alfa, 1.6, 0.4)


def explosao(h, c, idade, semente=0, escala=1.0, alfa=1.0):
    if idade < 0:
        return
    if idade < 1.0:
        k = idade
        h.ponto_luz(c, (30 + 90 * k) * escala, LARANJA, (1 - k) * 0.9 * alfa)
        h.ponto_luz(c, (12 + 30 * k) * escala, AMARELO, (1 - k) * alfa)
        if alfa > 0.5:
            h.pulso(c, idade, VERMELHO, 2.5 * escala, 0.7, 5)
            h.particulas(c, idade, LARANJA, n=22, alcance=3 * escala, dur=1.0, semente=semente,
                         gravidade=1.5 * escala)
    # marca permanente no chão
    h.linha([(c[0] - 0.25 * escala, c[1] - 0.25 * escala), (c[0] + 0.25 * escala, c[1] + 0.25 * escala)],
            VERMELHO, 2, 0.5 * alfa)
    h.linha([(c[0] - 0.25 * escala, c[1] + 0.25 * escala), (c[0] + 0.25 * escala, c[1] - 0.25 * escala)],
            VERMELHO, 2, 0.5 * alfa)


# ------------------------------------------------------------------ pós-processamento

def cromatica(sup, desloca=2):
    """Aberração cromática leve (vermelho e azul levemente separados), cara de projeção."""
    sup.flush()
    w, hh, est = sup.get_width(), sup.get_height(), sup.get_stride()
    buf = np.ndarray((hh, est // 4, 4), np.uint8, sup.get_data())[:, :w, :]
    b = buf[:, :, 0].copy()
    r = buf[:, :, 2].copy()
    buf[:, desloca:, 2] = np.maximum(r[:, desloca:], r[:, :-desloca] // 2)
    buf[:, :-desloca, 0] = np.maximum(b[:, :-desloca], b[:, desloca:] // 2)
    sup.mark_dirty()


def varredura(h, t, alfa=0.08):
    ctx = h.ctx
    ctx.set_source_rgba(0, 0, 0, alfa)
    for y in range(0, h.h, 3):
        ctx.rectangle(0, y, h.w, 1)
    ctx.fill()
    if (t * 7) % 1 < 0.04:  # cintilação rara do holograma
        ctx.set_source_rgba(0.25, 0.92, 1.0, 0.04)
        ctx.paint()
