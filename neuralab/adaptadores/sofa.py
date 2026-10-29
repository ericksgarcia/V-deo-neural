"""Adaptador da mudança de sofá, visto de cima em estilo holograma (mundo = metros).

Corredor em L (entra pela esquerda, sai por cima). O sofá é um retângulo rígido; cada ponta é uma IA
(ciano e magenta) com uma seta da força que ela faz. A multidão de fantasmas mostra os sofás da geração.
"""
import math

import numpy as np

from ..desafios.foguete import FALHA, SUCESSO
from ..desafios.sofa import (COMP, LARG, MEIA, X_INI, X_QUINA, Y_META, Y_TOPO, Sofa as DesafioSofa, bate_parede)
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .populacao import AdaptadorPopulacao

CENTRO = (-4.6, 4.6)
ESCALA = 62


def cantos(x, y, th, comp=COMP, larg=LARG):
    c, s = math.cos(th), math.sin(th)
    return [(x + a * c - b * s, y + a * s + b * c) for a, b in ((comp / 2, larg / 2), (comp / 2, -larg / 2),
                                                               (-comp / 2, -larg / 2), (-comp / 2, larg / 2))]


class Sofa(AdaptadorPopulacao):
    Desafio = DesafioSofa
    titulo = "MUDANÇA DE SOFÁ"
    experimento = "012"
    saidas = ("FORÇA ▸", "FORÇA ▴")
    rotulos = ("PASSARAM", "AINDA TENTANDO")
    som_falha = "batida"

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=CENTRO, escala=ESCALA, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        x, y = rod.reg["s"][foco, i, :2]
        seguir = Camera2D(centro=(0.5 * CENTRO[0] + 0.5 * float(np.clip(x, -6, 1.5)),
                                  0.5 * CENTRO[1] + 0.5 * float(np.clip(y, 0, 8))), escala=ESCALA * 1.12, t=t)
        return geral.mistura(seguir, min(t / 0.8, 1.0))

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t, rod=None):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.03)
        m = MEIA
        L = [(X_INI - 0.6, -m), (X_QUINA + m, -m), (X_QUINA + m, Y_TOPO), (X_QUINA - m, Y_TOPO),
             (X_QUINA - m, m), (X_INI - 0.6, m)]
        h.forma(L, CIANO, 0.28, 1.2, 0.05)
        h.linha(L, CIANO, 3.2, 0.85, fechado=True)
        # quina interna em destaque
        h.ponto_luz((X_QUINA - m, m), 14, AMARELO, 0.55)
        h.texto("A QUINA", (X_QUINA - m - 1.7, m + 0.6), 15, AMARELO, 0.6)
        # zona de chegada
        y0 = Y_META
        h.forma([(X_QUINA - m, y0), (X_QUINA + m, y0), (X_QUINA + m, Y_TOPO), (X_QUINA - m, Y_TOPO)], VERDE, 0.5, 1.5, 0.07)
        h.linha([(X_QUINA - m, y0), (X_QUINA + m, y0)], VERDE, 3, 0.55 + 0.3 * math.sin(t * 4), tracejado=[10, 8])
        h.texto("CHEGADA", (X_QUINA, Y_TOPO - 0.9), 16, VERDE, 0.7)
        # seta de entrada
        h.seta((X_INI - 0.2, 0.0), (X_INI + 1.4, 0.0), CIANO, 3, 0.4)

    # ------------------------------------------------------------ desenho
    def sofa(self, h, x, y, th, cor, alfa=1.0, forcas=None, brilho=True):
        h.forma(cantos(x, y, th), cor, alfa, 3.0 if brilho else 2.0, 0.22 if brilho else 0.12)
        if not brilho:
            return
        c, s = math.cos(th), math.sin(th)
        for sinal, c_ponta in ((-1, CIANO), (1, MAGENTA)):
            px, py = x + sinal * COMP / 2 * c, y + sinal * COMP / 2 * s
            h.circulo((px, py), 0.28, c_ponta, alfa, 3.0, 0.5)
            h.ponto_luz((px, py), 22, c_ponta, 0.5 * alfa)
            if forcas is not None:
                fu, fp = forcas[0 if sinal < 0 else 1]
                gx, gy = fu * c - fp * s, fu * s + fp * c
                if math.hypot(gx, gy) > 0.15:
                    h.seta((px, py), (px + gx * 0.5, py + gy * 0.5), c_ponta, 3, 0.9 * alfa, 0.25)

    def desenha(self, h, rod, t, modo, foco):
        s, est = rod.reg["s"], rod.reg["estado"]
        i = rod.i(t)
        lider = foco if (modo == "replay" and foco is not None) else rod.lider
        self.cenario(h, t, rod)
        if modo == "replay" and foco is not None:
            ks = [foco]
        else:
            ks = [k for k in self.fantasmas(rod, 70) if k != lider]
        for k in ks:
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            x, y, th = s[k, min(i, fim), :3]
            if modo == "replay" and foco is not None:
                continue
            cor, a, _ = self.aparencia(rod, k, i)
            self.sofa(h, float(x), float(y), float(th), cor, min(1.0, a * 2.4 + 0.12), brilho=False)
        # o destaque (líder ou lance) com rastro, pontas e setas de força
        k = lider
        m = rod.morte[k]
        fim = i if m < 0 else min(i, m)
        x, y, th = (float(v) for v in s[k, min(i, fim), :3])
        feito = est[k, min(i, rod.T - 1)] == SUCESSO
        enc = bool(bate_parede(np.array([x]), np.array([y]), np.array([th]))[0])
        tr = s[k, max(0, fim - 90): fim + 1: 4, :2]
        if len(tr) > 1:
            h.rastro([(float(a), float(b)) for a, b in tr], VERDE if feito else CIANO, 3, 0.55)
        f = rod.reg["extra"][k, min(i, rod.T - 1)] if "extra" in rod.reg else None
        cor = VERDE if feito else (AMARELO if self.encostado(rod, k, i) else BRANCO)
        self.sofa(h, x, y, th, cor, 1.0, forcas=None if f is None else f.reshape(2, 2))
        if self.encostado(rod, k, i):
            ax, ay = self.ponto_encosto(rod, k, i)
            h.ponto_luz((ax, ay), 26, VERMELHO, 0.8)
            h.particulas((ax, ay), (t * 3) % 0.9, (1.0, 0.65, 0.3), n=5, alcance=0.8, dur=0.9, semente=int(k))
        if feito and m >= 0:
            idade = max((i - m) * rod.dt, 0)
            h.pulso((x, y), idade, VERDE, 3.5, 0.9, 5)
            h.texto("✓ PASSOU", (X_QUINA, Y_TOPO + 0.9), 22, VERDE, min(idade * 3, 1))

    # ------------------------------------------------------------ apoio
    def encostado(self, rod, k, i):
        j = min(i, rod.T - 1)
        x, y, th = rod.reg["s"][k, j, :3]
        # encostado = ainda existe parede a menos de 0,12 m de algum ponto do sofá
        from ..desafios.sofa import PONTOS, livre
        c, s = math.cos(th), math.sin(th)
        for dx, dy in ((0.12, 0), (-0.12, 0), (0, 0.12), (0, -0.12)):
            px = x + PONTOS[:, 0] * c - PONTOS[:, 1] * s + dx
            py = y + PONTOS[:, 0] * s + PONTOS[:, 1] * c + dy
            if (~livre(px, py)).any():
                return True
        return False

    def ponto_encosto(self, rod, k, i):
        j = min(i, rod.T - 1)
        x, y, th = rod.reg["s"][k, j, :3]
        from ..desafios.sofa import PONTOS, livre
        c, s = math.cos(th), math.sin(th)
        px = x + PONTOS[:, 0] * c - PONTOS[:, 1] * s
        py = y + PONTOS[:, 0] * s + PONTOS[:, 1] * c
        for dx, dy in ((0.12, 0), (-0.12, 0), (0, 0.12), (0, -0.12)):
            mau = ~livre(px + dx, py + dy)
            if mau.any():
                q = int(np.argmax(mau))
                return float(px[q]), float(py[q])
        return float(x), float(y)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        x, y, th = (float(v) for v in rod.reg["s"][foco, i, :3])
        if nome == "quina":
            return (X_QUINA - MEIA, MEIA)
        if nome == "encosto":
            return self.ponto_encosto(rod, foco, i)
        if nome == "pontas":
            return (x, y)
        return (x, y)

    def duracao_foco(self, rod, foco):
        m = rod.morte[foco]
        return (m + 1) * rod.dt + 1.2 if m >= 0 else rod.duracao

    def cerebro(self, rod, t, foco):
        k = rod.lider if foco is None else foco
        i = rod.i(t)
        pesos = [(W[0], b[0]) for W, b in self.arq.desempacota(rod.genes[k:k + 1])]
        return dict(camadas=self.Desafio.camadas, pesos=pesos, ativ=rod.reg["ativ"][k, i, 0],
                    saidas=self.saidas, titulo="CÉREBRO // PONTA A", cor=CIANO)

    def ambiente(self, dur):
        return None
