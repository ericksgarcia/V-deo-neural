"""Adaptador do drone na tempestade, vista de lado em estilo holograma (mundo = metros da simulação)."""
import math

import numpy as np

from ..desafios.drone import Drone as DesafioDrone, vento
from ..desafios.foguete import FALHA, SUCESSO
from ..palco import arte as R
from ..palco.holo import AMARELO, AZUL, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D, clareia
from .populacao import AdaptadorPopulacao


def drone_lado(h, c, ang, escala, cor, t, alfa=1.0, motor=0.0):
    """Drone de perfil: corpo, braços, dois rotores borrados e jato de empuxo. ang = inclinação (rad)."""
    rot = lambda pts: R._rot(np.asarray(pts, float) * escala, -ang, c)
    if motor > 0.05:
        f = 0.8 + 0.2 * math.sin(t * 45 + c[0])
        for dx in (-1.9, 1.9):
            h.forma(rot([(dx - 0.35, -0.5), (dx + 0.35, -0.5), (dx, -0.5 - 3.2 * motor * f)]), CIANO, 0.5 * alfa, 1.2, 0.5)
        h.ponto_luz(rot([(0, -0.8)])[0], 16 * motor + 5, CIANO, 0.7 * alfa)
    h.forma(rot([(-0.9, 0.4), (0.9, 0.4), (1.1, -0.3), (0.6, -0.8), (-0.6, -0.8), (-1.1, -0.3)]), cor, alfa, 2.4, 0.22)
    h.linha(rot([(-1.9, 0.5), (-0.9, 0.1)]), cor, 1.8, alfa)
    h.linha(rot([(1.9, 0.5), (0.9, 0.1)]), cor, 1.8, alfa)
    for dx in (-1.9, 1.9):
        giro = 0.5 + 0.5 * math.sin(t * 60 + dx)
        h.linha(rot([(dx - 1.5, 0.75), (dx + 1.5, 0.75)]), clareia(cor, 0.4), 2.2, (0.35 + 0.4 * giro) * alfa)
    h.circulo(rot([(0, -0.1)])[0], 0.28 * escala, clareia(cor, 0.5), alfa, 1.6, 0.4)


class Drone(AdaptadorPopulacao):
    Desafio = DesafioDrone
    titulo = "DRONE"
    experimento = "003"
    saidas = ("MOTOR", "GIRO")
    rotulos = ("POUSOS", "CAÍDAS")
    som_falha = "boom"

    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(0.0, 46.0), escala=9.6, t=t)
        if modo != "replay" or foco is None:
            return geral
        x, y = rod.reg["s"][foco, rod.i(t), :2]
        perto = Camera2D(centro=(float(x), float(max(y, 11.0))), escala=24, t=t)
        cam = geral.mistura(perto, t / 1.2)
        m = rod.morte[foco]
        if m >= 0 and rod.reg["estado"][foco, m] == FALHA and 0 <= t - m * rod.dt < 0.4:
            cam.tremor = 10 * (1 - (t - m * rod.dt) / 0.4)
        return cam

    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.04, 0.04, 0.12), manchas=((0.2, 0.1, (0.25, 0.1, 0.5)), (0.8, 0.8, (0.0, 0.2, 0.4))))
        R.poeira(h, t, BRANCO, n=60, alfa=0.25)
        h.grade(5.0, alfa=0.04, pontos=False)
        # camadas de vento: faixas de partículas que correm para onde o vento sopra naquela altura
        for k, y in enumerate(range(6, 96, 6)):
            v = float(vento(0.0, float(y), t, 0.0))
            cor = VERDE if v > 0 else MAGENTA
            for j in range(5):
                x0 = ((j * 23 + k * 11 + v * t * 2.2) % 120) - 60
                h.linha([(x0, y), (x0 + 4 * np.sign(v) * (0.5 + abs(v) / 5), y)], cor, 1.8,
                        min(0.25 + abs(v) / 14, 0.7), halo=False)
        # nuvens e relâmpago (efeito visual; não entra em nenhuma conta)
        flash = max(0.0, 1 - ((t * 0.37) % 1.0) * 14) if (int(t * 0.37) % 2 == 0) else 0.0
        for cx, cy in ((-38, 92), (-10, 98), (22, 94), (46, 90)):
            h.forma([(cx - 14, cy - 2), (cx - 9, cy + 3), (cx - 2, cy + 5), (cx + 6, cy + 3), (cx + 13, cy - 2)],
                    AZUL, 0.5, 1.6, 0.14 + 0.25 * flash)
        if flash > 0.02:
            x0 = -22 + 10 * int(t * 0.37)
            raio = [(x0, 91), (x0 + 2.5, 80), (x0 - 1.5, 72), (x0 + 3, 58), (x0 - 1, 50)]
            h.linha(raio, BRANCO, 3, flash)
            h.ponto_luz((x0, 90), 80, BRANCO, 0.5 * flash)
        h.linha([(-80, 0), (80, 0)], CIANO, 3, 0.9)
        for x in np.arange(-70, 71, 5):
            h.linha([(x, 0), (x, -1.2)], CIANO, 1, 0.3, halo=False)
        D = self.Desafio
        a, b = D.pad_x - D.pad_meia, D.pad_x + D.pad_meia
        h.forma([(a, 0), (b, 0), (b - 1, 1.2), (a + 1, 1.2)], AMARELO, 1, 2.5, 0.3)
        for k in range(5):
            x = a + 1 + k * (b - a - 2) / 4
            h.ponto_luz((x, 1.4), 7, AMARELO, 0.4 + 0.6 * (math.sin(t * 6 - k) > 0))
        R.medida(h, (a, -2.5), (b, -2.5), f"{2 * D.pad_meia:.0f} m", AMARELO, desloca=0)
        h.texto("VENTO A FAVOR", (-40, 70), 18, VERDE, 0.55)
        h.texto("VENTO CONTRA", (-40, 12), 18, MAGENTA, 0.55)

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        s, est, ac = rod.reg["s"], rod.reg["estado"], rod.reg["acel"]
        i = rod.i(t)
        ks = [foco] if (modo == "replay" and foco is not None) else range(0, rod.n, 2)
        lider = rod.lider
        for k in ks:
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            destaque = (k == foco) or (k == lider and modo != "replay")
            cor = AMARELO if destaque and modo != "replay" else (VERDE if est[k, i] == SUCESSO else CIANO)
            pts = s[k, max(0, fim - 45): fim + 1: 2, :2]
            if len(pts) > 1:
                h.rastro(pts, cor, 2.5 if destaque else 1.2, 0.8 if destaque else 0.1)
            if m >= 0 and i >= m and est[k, m] == FALHA:
                R.explosao(h, (float(s[k, m, 0]), max(float(s[k, m, 1]), 0.5)), (i - m) * rod.dt, semente=k,
                           escala=2.2 if destaque else 1.0, alfa=1.0 if destaque else 0.2)
                continue
            x, y, vx, vy, a, w = s[k, i]
            drone_lado(h, (float(x), float(y)), float(a), (1.1 if modo == "replay" else 1.7) if destaque else 1.2, cor, t,
                       1.0 if destaque else 0.3, motor=float(ac[k, i]))
            if est[k, i] == SUCESSO:
                h.pulso((float(x), float(y) + 2), (i - m) * rod.dt if m >= 0 else 0, VERDE, 6, 0.9, 4)
        if modo == "replay" and foco is not None:
            x, y = s[foco, i, :2]
            v = float(vento(float(x), float(y), i * rod.dt, float(rod.fase[foco])))
            h.seta((float(x) - 4 * np.sign(v), float(y) + 4.5), (float(x) - 4 * np.sign(v) + 0.5 * v, float(y) + 4.5),
                   VERDE if v > 0 else MAGENTA, 3, 0.8)
            h.texto(f"VENTO {v:+.1f} m/s", (float(x), float(y) + 6.5), 16, VERDE if v > 0 else MAGENTA, 0.9)

    def ponto(self, rod, foco, nome, t):
        x, y = rod.reg["s"][foco, rod.i(t), :2]
        if nome == "agente":
            return (float(x), float(y) + 2.5)
        if nome == "alvo":
            return (self.Desafio.pad_x, 1.0)
        raise KeyError(nome)
