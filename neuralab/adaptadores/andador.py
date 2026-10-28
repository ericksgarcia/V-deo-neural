"""Adaptador do robô andador, vista de lado em estilo holograma (mundo = metros da simulação).

Mundo: x ao longo da pista (0 = largada, META = chegada), y para cima (y = 0 é o chão).
"""
import math

import numpy as np

from ..desafios.andador import COXA, CANELA, META, QUADRIL_ABAIXO, Andador as DesafioAndador
from ..desafios.foguete import FALHA, SUCESSO
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D, clareia
from .populacao import AdaptadorPopulacao


def robo(h, x, y, th, a, k, toca, cor, alfa=1.0, nitido=True, t=0.0):
    """Esqueleto neon: tronco, cabeça, duas pernas (a de trás mais fraca) e brilho nos pés que tocam o chão."""
    c, s = math.cos(th), math.sin(th)
    quadril = (x - QUADRIL_ABAIXO * s, y - QUADRIL_ABAIXO * c)
    ombro = (x + 0.42 * s, y + 0.42 * c)
    lw = max(1.6, h.px(0.045)) if nitido else 1.2
    for j in (1, 0):                                  # perna 1 atrás, perna 0 na frente
        at = a[j] - th
        joelho = (quadril[0] + COXA * math.sin(at), quadril[1] - COXA * math.cos(at))
        ac = at - k[j]
        pe = (joelho[0] + CANELA * math.sin(ac), joelho[1] - CANELA * math.cos(ac))
        cj = cor if j == 0 else tuple(v * 0.55 for v in cor)
        h.linha([quadril, joelho, pe], cj, lw * 1.5, alfa * (1.0 if j == 0 else 0.7), halo=nitido)
        if nitido:
            h.circulo(joelho, 0.055, clareia(cj, 0.4), alfa, 1.4, 0.5)
            h.linha([pe, (pe[0] + 0.16, pe[1])], cj, lw * 1.3, alfa, halo=False)
            if toca[j]:
                h.ponto_luz((pe[0] + 0.05, 0.02), h.px(0.38), cor, 0.55 * alfa)
    h.linha([quadril, ombro], cor, lw * 2.2, alfa, halo=nitido)
    corpo = [(-0.1, -0.02), (0.1, -0.02), (0.1, 0.42), (-0.1, 0.42)]
    pts = [(quadril[0] + px * c + py * s, quadril[1] - px * s + py * c) for px, py in corpo]
    h.forma(pts, cor, alfa, lw, 0.22 if nitido else 0.3, oclusor=nitido)
    cab = (ombro[0] + 0.14 * s, ombro[1] + 0.14 * c)
    h.circulo(cab, 0.12, clareia(cor, 0.35), alfa, lw * 0.9, 0.25, oclusor=nitido)
    if nitido:                                        # visor (mostra o lado para onde olha)
        h.linha([(cab[0] + 0.03 * c + 0.01 * s, cab[1] - 0.03 * s + 0.03 * c),
                 (cab[0] + 0.11 * c + 0.01 * s, cab[1] - 0.11 * s + 0.03 * c)], BRANCO, lw * 0.9, alfa, halo=False)
        h.ponto_luz(quadril, h.px(0.35), cor, 0.25 * alfa)


class Andador(AdaptadorPopulacao):
    Desafio = DesafioAndador
    titulo = "ROBÔ ANDADOR"
    experimento = "003"
    saidas = ("QUADRIL E", "QUADRIL D", "JOELHO E", "JOELHO D")
    rotulos = ("CHEGARAM", "CAÍRAM")
    som_falha = "batida"

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(META / 2 + 0.2, 1.75), escala=64, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        x = float(rod.reg["s"][foco, i, 0])
        perto = Camera2D(centro=(min(max(x + 1.0, 2.2), META - 1.6), 1.45), escala=128, t=t)
        k = min(t / 0.8, 1.0)
        cam = geral.mistura(perto, k)
        m = rod.morte[foco]
        if m >= 0 and rod.reg["estado"][foco, m] == FALHA and 0 <= t - m * rod.dt < 0.35:
            cam.tremor = 8 * (1 - (t - m * rod.dt) / 0.35)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.04, 0.07, 0.12))
        R.poeira(h, t, alfa=0.22)
        h.grade(1.0, alfa=0.035, pontos=False)
        xs = np.linspace(-6, META + 8, 70)                              # horizonte holográfico ao fundo
        h.linha(np.c_[xs, 1.9 + 0.35 * np.sin(xs * 0.5) + 0.2 * np.sin(xs * 1.7)], MAGENTA, 1.4, 0.2, halo=False)
        h.forma([(-6, 0), (META + 8, 0), (META + 8, -2.4), (-6, -2.4)], CIANO, 0.5, 1.5, 0.08)
        h.linha([(-6, 0), (META + 8, 0)], CIANO, 4, 0.95)
        for x in np.arange(-6, META + 8, 1.0):
            h.linha([(x, 0), (x, -0.22 if x % 2 else -0.4)], CIANO, 1, 0.5, halo=False)
            if x % 2 == 0 and 0 <= x <= META:
                h.texto(f"{x:.0f}", (x, -0.85), 18, CIANO, 0.55)
        # largada e chegada
        h.linha([(0, 0), (0, 2.3)], BRANCO, 2, 0.5, tracejado=[8, 8])
        h.texto("LARGADA", (0, 2.55), 17, BRANCO, 0.6)
        pulso = 0.65 + 0.3 * math.sin(t * 5)
        h.forma([(META, 0), (META + 0.12, 0), (META + 0.12, 2.3), (META, 2.3)], VERDE, 0.9, 2.2, 0.4)
        h.linha([(META, 0), (META, 2.3)], VERDE, 3, pulso)
        for j in range(8):
            h.forma([(META + (j % 2) * 0.28, j * 0.29), (META + (j % 2) * 0.28 + 0.28, j * 0.29),
                     (META + (j % 2) * 0.28 + 0.28, j * 0.29 + 0.29), (META + (j % 2) * 0.28, j * 0.29 + 0.29)],
                    VERDE, 0.5, 0.6, 0.55 if j % 2 == 0 else 0.1)
        h.texto(f"CHEGADA · {META:.0f} m", (META, 2.62), 20, VERDE, 0.9)

    # ------------------------------------------------------------ desenho
    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        s, est = rod.reg["s"], rod.reg["estado"]
        i = rod.i(t)
        lider = foco if (modo == "replay" and foco is not None) else rod.lider
        ks = [foco] if lider == foco and modo == "replay" else sorted(set(range(0, rod.n, 7)) | {rod.lider})
        for k in sorted(ks, key=lambda q: q == lider):
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            x, y, th, a1, a2, k1, k2, c1, c2 = s[k, min(i, fim)]
            destaque = k == lider
            e = est[k, i]
            cor = VERDE if e == SUCESSO else (VERMELHO if e == FALHA else (AMARELO if destaque else CIANO))
            tr = s[k, max(0, fim - 60): fim + 1: 3, :2]
            if destaque and len(tr) > 1:
                h.rastro([(float(a), 1.15) for a in tr[:, 0]], cor, 2, 0.35)
            robo(h, float(x), float(y), float(th), (a1, a2), (k1, k2), (c1 > 0.5, c2 > 0.5), cor,
                 1.0 if destaque else 0.16, nitido=destaque, t=t)
            if m >= 0 and e == FALHA and destaque:
                idade = (i - m) * rod.dt
                if 0 <= idade < 0.9:
                    h.pulso((float(x), 0.1), idade, VERMELHO, 1.6, 0.7, 4)
                    h.particulas((float(x), 0.2), idade, (1.0, 0.7, 0.3), n=12, alcance=1.2, dur=0.8, semente=int(k),
                                 gravidade=2.0)
                if idade >= 0.2:
                    h.texto("✕ CAIU", (float(x), 1.7), 26, VERMELHO, min((idade - 0.2) * 3, 1))
            if e == SUCESSO and destaque:
                idade = (i - m) * rod.dt if m >= 0 else 0
                h.pulso((float(x), 1.0), idade, VERDE, 2.2, 0.9, 4)
                h.texto("✓ CHEGOU", (float(x), 2.1), 26, VERDE, min(idade * 3, 1))
        if modo == "replay" and foco is not None:
            x = float(s[foco, min(i, rod.T - 1), 0])
            h.texto(f"{max(x, 0):.1f} m", (x, 2.0), 24, AMARELO, 0.85)

    def ponto(self, rod, foco, nome, t):
        x, y = rod.reg["s"][foco, rod.i(t), :2]
        if nome == "agente":
            return (float(x), float(y) + 0.3)
        if nome == "alvo":
            return (self.Desafio_META, 1.0)
        raise KeyError(nome)

    Desafio_META = META
