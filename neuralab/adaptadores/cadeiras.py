"""Adaptador da Dança das Cadeiras, vista de cima (arena em pé, mundo = metros).

12 IAs (ciano) correm em volta de 11 cadeiras; quando a música para, cada cadeira vira verde com a IA que chegou primeiro.
Quem fica sem cadeira só esmaece (rosa) e fica de fora. O vídeo mostra UMA rodada por geração: a mais típica, ou, com
`ger >= total_ger`, a rodada do CAMPEÃO da geração (ger - total_ger).
"""
import math

import numpy as np

from ..coevolucao_cadeiras import ARQ, campeao, rodadas
from ..desafios import cadeiras as K
from ..palco.holo import AMARELO, BRANCO, CIANO, VERDE, Camera2D
from .base import Adaptador, Rodada

ROSA = (1.0, 0.35, 0.6)


class RodadaCadeiras(Rodada):
    def __init__(self, hist, g, camp=False):
        self.g, self.dt = g, K.DT
        genes = hist["genes"][g]
        sem = int(hist["semente"][g])
        pop = len(genes)
        jogo, reg = rodadas(genes, np.arange(pop), sem, gravar=True)
        ch = jogo.cheias()
        w = campeao(hist, g) if camp else int(np.argmin(np.abs(ch - ch.mean())))
        self.mundo, self.genes, self.cerebro_i = w, genes, w
        self.p, self.senta, self.ativ = reg["p"][w], reg["senta"][w], reg["ativ"][w]
        self.T = self.p.shape[0]
        self.duracao = self.T * K.DT
        self.final = int((self.senta[-1] >= 0).sum())

    def i(self, t):
        return int(min(max(t / K.DT, 0), self.T - 1))

    def sentadas(self, t):
        return int((self.senta[self.i(t)] >= 0).sum())


class Cadeiras(Adaptador):
    titulo = "DANÇA DAS CADEIRAS"
    experimento = "019"
    cores = {"ias": CIANO, "cadeiras": VERDE, "campeão": AMARELO, "música": ROSA}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["genes"])
        self._cache = {}

    def rodada(self, g):
        if g not in self._cache:
            camp = g >= self.total_ger
            self._cache[g] = RodadaCadeiras(self.hist, g - self.total_ger if camp else g, camp)
        return self._cache[g]

    def duracao_foco(self, rod, foco):
        return rod.duracao

    def janela_lance(self, rod, foco):
        return 0.0, rod.duracao

    def chaves_lento(self, rod, foco):
        return [K.KM * K.DT - 0.3]                       # a música vai parar

    def busca(self, rod, tipo):
        return 0

    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(K.CX, K.CY), escala=82, t=t)
        if modo != "replay" or foco is None:
            return geral
        return geral.mistura(Camera2D(centro=(K.CX, K.CY), escala=104, t=t), min(t / 0.8, 1.0))

    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.08))
        h.grade(1.0, alfa=0.05)
        borda = [(0, 0), (K.LARG, 0), (K.LARG, K.ALT), (0, K.ALT)]
        h.forma(borda, CIANO, 0.5, 2.0, 0.02)
        h.linha(borda, CIANO, 3.5, 0.9, fechado=True)

    def _pontos(self, h, xs, ys, cor, r_m, alfa):
        import cairo
        ctx = h.ctx
        ctx.set_operator(cairo.OPERATOR_ADD)
        X, Y = h.tela(np.asarray(xs, float), np.asarray(ys, float))
        r = h.px(r_m)
        h._cor(cor, alfa)
        for x, y in zip(np.atleast_1d(X), np.atleast_1d(Y)):
            ctx.arc(float(x), float(y), r, 0, 2 * math.pi)
            ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)

    def desenha(self, h, rod, t, modo, foco):
        i = rod.i(t)
        self.cenario(h, t)
        p, sen = rod.p[i], rod.senta[i]
        musica = i < K.KM
        ocupada = np.zeros(K.C, bool)
        ocupada[sen[sen >= 0]] = True
        # cadeiras: quadrados neon (livre = ciano, ocupada = verde)
        for c in range(K.C):
            x, y = (float(v) for v in K.CADEIRAS[c])
            m = 0.42
            cor = VERDE if ocupada[c] else CIANO
            h.forma([(x - m, y - m), (x + m, y - m), (x + m, y + m), (x - m, y + m)], cor, 0.9 if ocupada[c] else 0.75, 3.0, 0.3 if ocupada[c] else 0.12)
        # música: nota piscando enquanto toca; "PAROU!" logo depois
        if musica:
            pisca = 0.65 + 0.35 * math.sin(t * 9.0)
            h.texto("♪ MÚSICA ♪", (K.CX, K.ALT - 1.0), 40, ROSA, pisca)
        elif i - K.KM < 14:
            h.texto("PAROU!", (K.CX, K.ALT - 1.0), 48, AMARELO, 1.0)
        # rastro curto de cada IA em pé
        em_pe = sen < 0
        for a in np.where(em_pe)[0]:
            tr = rod.p[max(0, i - 8): i + 1: 2, a]
            if len(tr) > 1:
                h.rastro([tuple(q) for q in tr], CIANO, 5, 0.35)
        # IAs: em pé = ciano; sentada = verde; no fim, quem ficou sem cadeira esmaece em rosa
        fim = (not musica) and i >= rod.T - 1
        fora = em_pe & fim
        pe = em_pe & ~fim
        self._pontos(h, p[pe, 0], p[pe, 1], CIANO, 0.62, 0.20)
        self._pontos(h, p[pe, 0], p[pe, 1], (0.8, 1.0, 1.0), 0.40, 1.0)
        self._pontos(h, p[fora, 0], p[fora, 1], ROSA, 0.62, 0.22)
        self._pontos(h, p[fora, 0], p[fora, 1], (1.0, 0.7, 0.85), 0.40, 0.8)
        s = sen >= 0
        self._pontos(h, p[s, 0], p[s, 1], VERDE, 0.62, 0.24)
        self._pontos(h, p[s, 0], p[s, 1], (0.75, 1.0, 0.85), 0.40, 1.0)
        # clarão curto de quem acabou de sentar (evento no ponto exato)
        if i > 0:
            novas = np.where((sen >= 0) & (rod.senta[max(i - 4, 0)] < 0))[0]
            for a in novas:
                h.pulso((float(p[a, 0]), float(p[a, 1])), 0.15, VERDE, 0.9, 0.5, 3)

    def ponto(self, rod, foco, nome, t):
        return (K.CX, K.CY)

    def medidores(self, rod, t, foco):
        n = rod.sentadas(t)
        return [("CADEIRAS CHEIAS", f"{n}/{K.C}", n / K.C, VERDE), ("EM PÉ", f"{K.N - n}/{K.N}", (K.N - n) / K.N, CIANO)]

    def cerebro(self, rod, t, foco):
        i = rod.i(t)
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(rod.genes[rod.cerebro_i:rod.cerebro_i + 1])]
        return dict(camadas=K.CAMADAS, pesos=pesos, ativ=rod.ativ[i], saidas=("→ X", "↑ Y"), titulo="CÉREBRO // 12 IAs", cor=CIANO)

    def sons(self, rod, t0, t1, modo, foco):
        a, b = rod.i(t0), rod.i(t1)
        if b <= a:
            return []
        novas = int((rod.senta[b] >= 0).sum() - (rod.senta[a] >= 0).sum())
        return [(t0, "batida", min(0.25 + 0.1 * novas, 0.6))] if novas > 0 else []

    def ambiente(self, dur):
        return None
