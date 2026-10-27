"""Adaptador da baliza, vista de cima em estilo holograma (mundo = metros da simulação)."""
import math

import numpy as np

from ..desafios.baliza import COMP, LARG, Baliza as DesafioBaliza
from ..desafios.foguete import FALHA, SUCESSO
from ..palco import arte as R
from ..palco.holo import AMARELO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .populacao import AdaptadorPopulacao

CINZA = (0.55, 0.6, 0.72)


class Baliza(AdaptadorPopulacao):
    Desafio = DesafioBaliza
    titulo = "BALIZA"
    experimento = "002"
    saidas = ("ACELERA", "VOLANTE")
    rotulos = ("NA VAGA", "BATIDAS")
    som_falha = "batida"

    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(1.2, 3.0), escala=40, t=t)
        if modo != "replay" or foco is None:
            return geral
        x, y = rod.reg["s"][foco, rod.i(t), :2]
        perto = Camera2D(centro=(float(x) * 0.6, 2.4), escala=62, t=t)
        cam = geral.mistura(perto, t / 1.5)
        m = rod.morte[foco]
        if m >= 0 and rod.reg["estado"][foco, m] == FALHA and 0 <= t - m * rod.dt < 0.35:
            cam.tremor = 8 * (1 - (t - m * rod.dt) / 0.35)
        return cam

    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.04)
        R.poeira(h, t, alfa=0.25)
        R.placa(h, -14, -0.05, 16, 8.5, t, CIANO)                 # pista
        h.linha([(-20, 0), (20, 0)], CIANO, 4, 0.9)                  # meio-fio
        h.forma([(-20, -2.6), (20, -2.6), (20, -0.05), (-20, -0.05)], CIANO, 0.35, 1, 0.04)   # calçada
        h.linha([(-20, 5.6), (20, 5.6)], AMARELO, 2, 0.5, tracejado=[22, 18])
        D = self.Desafio
        for ox, oy in D.estacionados:
            R.veiculo_topo(h, (ox, oy), 0.0, COMP, LARG, CINZA, t, 0.7, farois=False)
        m = D.meia_vaga
        h.linha([(-m, 0.1), (m, 0.1), (m, 2.4), (-m, 2.4)], MAGENTA, 2.5, 0.6 + 0.3 * math.sin(t * 5),
                fechado=True, tracejado=[12, 10])
        h.texto("VAGA", (0, 1.25), 18, MAGENTA, 0.8)
        R.medida(h, (-m, -1.2), (m, -1.2), f"{2 * m:.1f} m", MAGENTA, desloca=0)

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        s, est = rod.reg["s"], rod.reg["estado"]
        i = rod.i(t)
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        for k in ks:
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            x, y, hd, v, e = s[k, min(i, fim)]
            destaque = (k == foco) or (k == rod.lider and modo != "replay")
            if est[k, i] == SUCESSO:
                cor = VERDE
            elif est[k, i] == FALHA:
                cor = VERMELHO
            else:
                cor = AMARELO if destaque and modo != "replay" else CIANO
            tr = s[k, max(0, fim - 60): fim + 1: 3]
            if len(tr) > 1:
                h.rastro([(a - 1.3 * math.cos(b), c - 1.3 * math.sin(b)) for a, c, b in tr[:, :3]], cor,
                         2.5 if destaque else 1.0, 0.8 if destaque else 0.1)
            R.veiculo_topo(h, (float(x), float(y)), float(hd), COMP, LARG, cor, t, 1.0 if destaque else 0.1,
                           farois=destaque, re=v < -0.1)
            if m >= 0 and est[k, m] == FALHA and 0 <= (i - m) * rod.dt < 0.7:
                if destaque:
                    h.pulso((float(x), float(y)), (i - m) * rod.dt, VERMELHO, 2.5, 0.7, 4)
                h.particulas((float(x), float(y)), (i - m) * rod.dt, VERMELHO, n=10, alcance=1.5, dur=0.7,
                             semente=k)
            if est[k, i] == SUCESSO and destaque:
                h.pulso((float(x), float(y)), (i - m) * rod.dt if m >= 0 else 0, VERDE, 3, 0.9, 4)

    def ponto(self, rod, foco, nome, t):
        x, y = rod.reg["s"][foco, rod.i(t), :2]
        if nome == "agente":
            return (float(x), float(y))
        if nome == "alvo":
            return (0.0, self.Desafio.vaga_y)
        raise KeyError(nome)
