"""Adaptador do foguete, vista de lado em estilo holograma (mundo = metros da simulação)."""
import math

import numpy as np

from ..desafios.foguete import FALHA, SUCESSO, Foguete as DesafioFoguete
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .populacao import AdaptadorPopulacao


class Foguete(AdaptadorPopulacao):
    Desafio = DesafioFoguete
    titulo = "FOGUETE"
    experimento = "001"
    saidas = ("MOTOR", "GIRO")
    rotulos = ("POUSOS", "EXPLOSÕES")
    som_falha = "boom"

    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(0.0, 46.0), escala=9.6, t=t)
        if modo != "replay" or foco is None:
            return geral
        x, y = rod.reg["s"][foco, rod.i(t), :2]
        perto = Camera2D(centro=(float(x), float(max(y, 9.0))), escala=26, t=t)
        cam = geral.mistura(perto, t / 1.2)
        m = rod.morte[foco]
        if m >= 0 and 0 <= t - m * rod.dt < 0.4:
            cam.tremor = 10 * (1 - (t - m * rod.dt) / 0.4)
        return cam

    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.05, 0.03, 0.1), manchas=((0.2, 0.15, (0.4, 0.1, 0.5)), (0.8, 0.85, (0.0, 0.25, 0.4))))
        R.poeira(h, t, BRANCO, n=110, alfa=0.4)                      # estrelas
        h.grade(5.0, alfa=0.04, pontos=False)
        # relevo holográfico ao fundo (linha de horizonte)
        xs = np.linspace(-70, 70, 60)
        ys = 4 + 3 * np.sin(xs * 0.11) + 2 * np.sin(xs * 0.37 + 1)
        h.linha(np.c_[xs, ys], MAGENTA, 1.6, 0.35)
        h.linha([(-80, 0), (80, 0)], CIANO, 3, 0.9)
        for x in np.arange(-70, 71, 5):  # marcações do solo
            h.linha([(x, 0), (x, -1.2)], CIANO, 1, 0.3, halo=False)
        D = self.Desafio
        a, b = D.pad_x - D.pad_meia, D.pad_x + D.pad_meia
        h.forma([(a, 0), (b, 0), (b - 1, 1.2), (a + 1, 1.2)], AMARELO, 1, 2.5, 0.3)
        for k in range(5):
            x = a + 1 + k * (b - a - 2) / 4
            h.ponto_luz((x, 1.4), 7, AMARELO, 0.4 + 0.6 * (math.sin(t * 6 - k) > 0))
        R.medida(h, (a, -2.5), (b, -2.5), f"{2 * D.pad_meia:.0f} m", AMARELO, desloca=0)

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        s, est, ac = rod.reg["s"], rod.reg["estado"], rod.reg["acel"]
        i = rod.i(t)
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        for k in ks:
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            destaque = (k == foco) or (k == rod.lider and modo != "replay")
            cor = AMARELO if destaque and modo != "replay" else (VERDE if est[k, i] == SUCESSO else CIANO)
            pts = s[k, max(0, fim - 40): fim + 1: 2, :2]
            if len(pts) > 1:
                h.rastro(pts, cor, 2.5 if destaque else 1.2, 0.8 if destaque else 0.12)
            if m >= 0 and i >= m and est[k, m] == FALHA:
                R.explosao(h, (float(s[k, m, 0]), max(float(s[k, m, 1]), 0.5)), (i - m) * rod.dt, semente=k,
                           escala=2.5 if destaque else 1.2, alfa=1.0 if destaque else 0.25)
                continue
            x, y, vx, vy, a, w = s[k, i]
            R.foguete_lado(h, (float(x), float(y)), float(a), 0.95, cor, t, 1.0 if destaque else 0.13,
                           motor=float(ac[k, i]))
            if est[k, i] == SUCESSO:
                h.pulso((float(x), float(y) + 2), (i - m) * rod.dt if m >= 0 else 0, VERDE, 6, 0.9, 4)

    def ponto(self, rod, foco, nome, t):
        x, y = rod.reg["s"][foco, rod.i(t), :2]
        if nome == "agente":
            return (float(x), float(y) + 2.5)
        if nome == "alvo":
            return (self.Desafio.pad_x, 1.0)
        raise KeyError(nome)
