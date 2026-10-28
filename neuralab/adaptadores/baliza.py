"""Adaptador da baliza, vista de cima em estilo holograma (mundo = metros da simulação).

Mundo: x ao longo da rua, y para dentro da pista (y = 0 é o meio-fio; a vaga fica entre dois carros).
"""
import math

import numpy as np

from ..desafios.baliza import COMP, LARG, Baliza as DesafioBaliza
from ..desafios.foguete import FALHA, SUCESSO
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .populacao import AdaptadorPopulacao

CINZA = (0.55, 0.62, 0.8)


class Baliza(AdaptadorPopulacao):
    Desafio = DesafioBaliza
    titulo = "BALIZA"
    experimento = "002"
    saidas = ("ACELERA", "VOLANTE")
    rotulos = ("NA VAGA", "BATIDAS")
    som_falha = "batida"

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        """Enquadramento quase fixo sobre a vaga (a manobra inteira cabe); o replay aproxima de leve."""
        geral = Camera2D(centro=(1.8, 2.6), escala=58, t=t)
        if modo != "replay" or foco is None:
            return geral
        m = rod.morte[foco] * rod.dt
        perto = Camera2D(centro=(0.8, 2.3), escala=76, t=t)
        k = min(t / 0.6, 1.0) - max((t - m) / 0.7, 0.0)
        cam = geral.mistura(perto, k)
        if rod.morte[foco] >= 0 and rod.reg["estado"][foco, rod.morte[foco]] == FALHA and 0 <= t - m < 0.35:
            cam.tremor = 9 * (1 - (t - m) / 0.35)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t, rod=None, k=None):
        D = self.Desafio
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.04)
        R.poeira(h, t, alfa=0.25)
        # pista, calçada e meio-fio
        R.placa(h, -17, 0.0, 19, 8.8, t, CIANO)
        h.forma([(-17, -3.2), (19, -3.2), (19, 0.0), (-17, 0.0)], CIANO, 0.5, 1.5, 0.09)
        h.linha([(-17, 0.0), (19, 0.0)], CIANO, 4, 0.95)
        for x in np.arange(-16, 19, 2.0):                                  # junta de calçada
            h.linha([(x, 0.0), (x, -3.2)], CIANO, 1, 0.12, halo=False)
        h.linha([(-17, 5.6), (19, 5.6)], AMARELO, 2, 0.5, tracejado=[26, 20])   # faixa central
        h.texto("CALÇADA", (-13.5, -1.7), 20, CIANO, 0.4)
        # carros estacionados (cinza neon) + luz de presença
        for ox, oy in D.estacionados:
            R.veiculo_topo(h, (ox, oy), 0.0, COMP, LARG, CINZA, t, 0.85, farois=False)
        # a vaga: contorno tracejado, P no chão, cantoneiras e cota
        m = D.meia_vaga
        pulso = 0.6 + 0.35 * math.sin(t * 5)
        h.forma([(-m, 0.12), (m, 0.12), (m, 2.4), (-m, 2.4)], MAGENTA, 0.9, 2, 0.05)
        h.linha([(-m, 0.12), (m, 0.12), (m, 2.4), (-m, 2.4)], MAGENTA, 2.5, pulso, fechado=True, tracejado=[14, 10])
        h.texto("P", (0, 0.95), 46, MAGENTA, 0.5)
        R.medida(h, (-m, -0.9), (m, -0.9), f"{2 * m:.1f} m", MAGENTA, desloca=0)
        for sx in (-1, 1):
            h.ponto_luz((sx * m, 1.25), 11, MAGENTA, 0.45)
        # linha-guia do carro em foco até o centro da vaga (distância ao vivo)
        if rod is not None and k is not None:
            i = rod.i(t)
            x, y = rod.reg["s"][k, i, :2]
            d = math.hypot(x, y - D.vaga_y)
            if d > 0.6 and rod.reg["estado"][k, i] == 0:
                h.linha([(float(x), float(y)), (0.0, D.vaga_y)], MAGENTA, 1.2, 0.35, tracejado=[6, 8], halo=False)
                h.texto(f"{d:.1f} m", ((float(x) + 0) / 2, (float(y) + D.vaga_y) / 2 + 0.55), 20, MAGENTA, 0.8)

    # ------------------------------------------------------------ desenho
    def desenha(self, h, rod, t, modo, foco):
        D = self.Desafio
        s, est, ac = rod.reg["s"], rod.reg["estado"], rod.reg["acel"]
        i = rod.i(t)
        lider = foco if (modo == "replay" and foco is not None) else rod.lider
        self.cenario(h, t, rod, lider)
        if modo == "replay" and foco is not None:
            ks = [foco]
        else:   # multidão: 1 em cada 3 (a soma de luz de 150 carros viraria uma mancha branca)
            ks = sorted(set(range(0, rod.n, 8)) | {rod.lider})
        for k in ks:
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            x, y, hd, v, e = s[k, min(i, fim)]
            destaque = k == lider
            if est[k, i] == SUCESSO:
                cor = VERDE
            elif est[k, i] == FALHA:
                cor = VERMELHO
            else:
                cor = AMARELO if destaque else CIANO
            # rastro de pneu (só o destaque é nítido; a multidão vira névoa)
            tr = s[k, max(0, fim - 70): fim + 1: 3]
            if len(tr) > 1:
                h.rastro([(a - 1.3 * math.cos(b), c - 1.3 * math.sin(b)) for a, c, b in tr[:, :3]], cor,
                         3 if destaque else 1.0, 0.85 if destaque else 0.07)
            freio = bool(ac[k, i] * v < -0.25) and est[k, i] == 0
            R.veiculo_topo(h, (float(x), float(y)), float(hd), COMP, LARG, cor, t, 1.0 if destaque else 0.07,
                           farois=destaque and est[k, i] == 0, re=bool(v < -0.1) and est[k, i] == 0, freio=freio,
                           esterco=float(e), simples=not destaque)
            if m >= 0 and est[k, m] == FALHA and 0 <= (i - m) * rod.dt < 0.8:
                idade = (i - m) * rod.dt
                if destaque:
                    h.pulso((float(x), float(y)), idade, VERMELHO, 3.0, 0.7, 5)
                    h.ponto_luz((float(x), float(y)), 70 * (1 - idade), (1.0, 0.6, 0.2), 0.8 * (1 - idade))
                h.particulas((float(x), float(y)), idade, (1.0, 0.7, 0.3), n=14 if destaque else 5, alcance=2.0,
                             dur=0.8, semente=int(k))
            if est[k, i] == SUCESSO and destaque:
                idade = (i - m) * rod.dt if m >= 0 else 0
                h.pulso((float(x), float(y)), idade, VERDE, 3.5, 0.9, 5)
                h.texto("✓ NA VAGA", (float(x), float(y) + 1.9), 26, VERDE, min(idade * 3, 1))

    def ponto(self, rod, foco, nome, t):
        x, y = rod.reg["s"][foco, rod.i(t), :2]
        if nome == "agente":
            return (float(x), float(y))
        if nome == "alvo":
            return (0.0, self.Desafio.vaga_y + 0.6)
        raise KeyError(nome)

    def sons(self, rod, t0, t1, modo, foco):
        ev = super().sons(rod, t0, t1, modo, foco)
        return ev

    def ambiente(self, dur):
        return None
