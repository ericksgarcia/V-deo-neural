"""Adaptador do Cão Pastor, vista de cima (arena em pé, mundo = metros).

O cão (laranja) leva 15 ovelhas (brancas) ao curral (3 paredes, no alto). Ovelha dentro do curral fica verde.
O vídeo mostra UMA cidade por geração: a mais típica, ou, com `ger >= total_ger`, a cidade do CAMPEÃO da geração (ger - total_ger).
"""
import math

import numpy as np

from ..coevolucao_pastor import ARQ, campeao, cidades
from ..desafios import pastor as P
from ..palco.holo import AMARELO, BRANCO, CIANO, VERDE, Camera2D
from .base import Adaptador, Rodada

LARANJA = (1.0, 0.55, 0.15)
OVELHA = (0.92, 0.96, 1.0)


class RodadaPastor(Rodada):
    def __init__(self, hist, g, camp=False):
        self.g, self.dt = g, P.DT
        genes = hist["genes"][g]
        sem = int(hist["semente"][g])
        pop = len(genes)
        jogo, reg = cidades(genes, np.arange(pop), sem, gravar=True)
        din = jogo.dentro().sum(1)
        w = campeao(hist, g) if camp else int(np.argmin(np.abs(din - din.mean())))
        self.mundo, self.genes, self.cerebro_i = w, genes, w
        self.c, self.o, self.ativ = reg["c"][w], reg["o"][w], reg["ativ"][w]
        self.T = self.c.shape[0]
        self.duracao = self.T * P.DT
        self.dentro = P_dentro(self.o)                     # (T, N)
        self.final = int(self.dentro[-1].sum())

    def i(self, t):
        return int(min(max(t / P.DT, 0), self.T - 1))

    def contagem(self, t):
        return int(self.dentro[self.i(t)].sum())


def P_dentro(o):
    return (o[..., 0] > P.PX0 + 0.1) & (o[..., 0] < P.PX1 - 0.1) & (o[..., 1] > P.PY0 + 0.3)


class Pastor(Adaptador):
    titulo = "CÃO PASTOR"
    experimento = "018"
    cores = {"cão": LARANJA, "ovelhas": OVELHA, "curral": VERDE}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["genes"])
        self._cache = {}

    def rodada(self, g):
        if g not in self._cache:
            camp = g >= self.total_ger
            self._cache[g] = RodadaPastor(self.hist, g - self.total_ger if camp else g, camp)
        return self._cache[g]

    # ------------------------------------------------------------ lances (foco = o cão, índice 0)
    def duracao_foco(self, rod, foco):
        return min(rod.duracao, 12.0)

    def janela_lance(self, rod, foco):
        return 0.0, min(rod.duracao, 12.0)

    def chaves_lento(self, rod, foco):
        ent = np.where(rod.dentro.any(1))[0]
        return [ent[0] * P.DT] if len(ent) else []

    def busca(self, rod, tipo):
        return 0

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(P.LARG / 2, P.ALT / 2), escala=46, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        c = rod.c[i]
        cent = rod.o[i].mean(0)
        cx = float(np.clip(0.5 * c[0] + 0.5 * cent[0], 5.5, P.LARG - 5.5))
        cy = float(np.clip(0.5 * c[1] + 0.5 * cent[1] + 1.0, 6.0, P.ALT - 6.0))
        return geral.mistura(Camera2D(centro=(cx, cy), escala=64, t=t), min(t / 0.8, 1.0))

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.06, 0.05))
        h.grade(1.0, alfa=0.05)
        borda = [(0, 0), (P.LARG, 0), (P.LARG, P.ALT), (0, P.ALT)]
        h.forma(borda, CIANO, 0.5, 2.0, 0.02)
        h.linha(borda, CIANO, 3.5, 0.9, fechado=True)
        # curral: piso verde suave e 3 paredes (esquerda, direita; o topo é a borda da arena)
        h.forma([(P.PX0, P.PY0), (P.PX1, P.PY0), (P.PX1, P.ALT), (P.PX0, P.ALT)], VERDE, 0.5, 0.0, 0.10)
        h.linha([(P.PX0, P.PY0), (P.PX0, P.ALT)], VERDE, 5.0, 0.95)
        h.linha([(P.PX1, P.PY0), (P.PX1, P.ALT)], VERDE, 5.0, 0.95)
        h.texto("CURRAL", (P.LARG / 2, P.ALT - 1.0), 22, VERDE, 0.8)

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
        o, c, din = rod.o[i], rod.c[i], rod.dentro[i]
        perto = h.cam.escala >= 60
        # rastro do cão
        tr = rod.c[max(0, i - 15): i + 1: 3]
        if len(tr) > 1:
            h.rastro([tuple(q) for q in tr], LARANJA, 7, 0.6)
        # ovelhas
        fora = ~din
        self._pontos(h, o[fora, 0], o[fora, 1], OVELHA, 0.95 if perto else 1.1, 0.25)
        self._pontos(h, o[fora, 0], o[fora, 1], (1, 1, 1), 0.5 if perto else 0.6, 1.0)
        self._pontos(h, o[din, 0], o[din, 1], VERDE, 0.95 if perto else 1.1, 0.30)
        self._pontos(h, o[din, 0], o[din, 1], (0.8, 1.0, 0.9), 0.5 if perto else 0.6, 1.0)
        # cão: corpo grande laranja com halo e nariz na direção do movimento
        self._pontos(h, [c[0]], [c[1]], LARANJA, 1.2 if perto else 1.4, 0.30)
        self._pontos(h, [c[0]], [c[1]], (1.0, 0.75, 0.4), 0.65 if perto else 0.8, 1.0)
        v = rod.c[min(i + 1, rod.T - 1)] - rod.c[max(i - 1, 0)]
        if math.hypot(v[0], v[1]) > 0.02:
            a = math.atan2(v[1], v[0])
            h.linha([(c[0], c[1]), (c[0] + 0.9 * math.cos(a), c[1] + 0.9 * math.sin(a))], LARANJA, 10, 1.0)
        # clarão curto de ovelha que acabou de entrar no curral (evento no ponto exato)
        if i > 0:
            novas = np.where(din & ~rod.dentro[max(i - 4, 0)])[0]
            for k in novas:
                h.pulso((float(o[k, 0]), float(o[k, 1])), 0.15, VERDE, 1.0, 0.5, 3)
        if modo == "replay" and foco is not None:
            h.destaque((float(c[0]), float(c[1])), AMARELO, t, 0.7)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        if nome == "foco":
            return tuple(float(v) for v in rod.c[i])
        return P.ENTR

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        n = rod.contagem(t)
        return [("NO CURRAL", f"{n}/{P.N}", n / P.N, VERDE), ("FORA", f"{P.N - n}/{P.N}", (P.N - n) / P.N, LARANJA)]

    def cerebro(self, rod, t, foco):
        i = rod.i(t)
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(rod.genes[rod.cerebro_i:rod.cerebro_i + 1])]
        return dict(camadas=P.CAMADAS, pesos=pesos, ativ=rod.ativ[i], saidas=("→ X", "↑ Y"), titulo="CÉREBRO // CÃO", cor=LARANJA)

    def sons(self, rod, t0, t1, modo, foco):
        a, b = rod.i(t0), rod.i(t1)
        if b <= a:
            return []
        novas = int(rod.dentro[b].sum() - rod.dentro[a].sum())
        return [(t0, "batida", min(0.25 + 0.1 * novas, 0.6))] if novas > 0 else []

    def ambiente(self, dur):
        return None
