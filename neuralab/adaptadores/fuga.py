"""Adaptador da Fuga com Cobertura, vista de cima (arena em pé, mundo = metros).

Azuis (ciano) atravessam de baixo para cima; a torreta (vermelha, no centro) dispara balas neon; 4 blocos verdes deslizam e
absorvem os tiros. Quem é atingido some com um clarão. O vídeo mostra UMA cidade por geração: a mais típica, ou, com
`ger >= total_ger`, a cidade do CAMPEÃO da geração (ger - total_ger).
"""
import math

import numpy as np

from ..coevolucao_fuga import ARQ, campeao, cidades
from ..desafios import fuga as F
from ..palco.holo import AMARELO, BRANCO, CIANO, VERDE, VERMELHO, Camera2D
from .base import Adaptador, Rodada

BLOCO = (0.4, 1.0, 0.62)


class RodadaFuga(Rodada):
    def __init__(self, hist, g, camp=False):
        self.g, self.dt = g, F.DT
        genes = hist["genes"][g]
        sem = int(hist["semente"][g])
        pop = len(genes)
        jogo, reg = cidades(genes, np.arange(pop), sem, gravar=True)
        n_cheg = jogo.chegou.sum(1)
        w = campeao(hist, g) if camp else int(np.argmin(np.abs(n_cheg - n_cheg.mean())))
        self.mundo, self.genes, self.cerebro_i = w, genes, w
        for c in ("p", "vivo", "chegou", "bp", "bvivo", "bx", "ativ"):
            setattr(self, c, reg[c][w])
        self.t_chegou, self.t_morte = jogo.t_chegou[w], jogo.t_morte[w]
        self.T = self.p.shape[0]
        self.duracao = self.T * F.DT
        self.final = int(n_cheg[w])

    def i(self, t):
        return int(min(max(t / F.DT, 0), self.T - 1))

    def contagem(self, t):
        i = self.i(t)
        return int(self.chegou[i].sum()), int((~self.vivo[i]).sum())


class Fuga(Adaptador):
    titulo = "FUGA COM COBERTURA"
    experimento = "011"
    cores = {"azul": CIANO, "torreta": VERMELHO, "bloco": BLOCO}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["genes"])
        self._cache = {}

    def rodada(self, g):
        if g not in self._cache:
            camp = g >= self.total_ger
            self._cache[g] = RodadaFuga(self.hist, g - self.total_ger if camp else g, camp)
        return self._cache[g]

    # ------------------------------------------------------------ lances (replay: foco = azul)
    def duracao_foco(self, rod, foco):
        return min(rod.duracao, 12.0)

    def janela_lance(self, rod, foco):
        return 0.0, min(rod.duracao, 12.0)

    def chaves_lento(self, rod, foco):
        t = rod.t_morte[foco]
        return [t * F.DT] if t > 0 else []

    def busca(self, rod, tipo):
        """'chegou' = um azul que chega à linha; 'caiu' = o primeiro que é atingido; 'ultimo' = o último a chegar."""
        ch = np.where(rod.t_chegou >= 0)[0]
        mo = np.where(rod.t_morte >= 0)[0]
        if tipo == "caiu":
            return int(mo[np.argmin(rod.t_morte[mo])]) if len(mo) else 0
        if tipo == "ultimo":
            return int(ch[np.argmax(rod.t_chegou[ch])]) if len(ch) else 0
        return int(ch[np.argmin(rod.t_chegou[ch])]) if len(ch) else 0

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(F.LARG / 2, F.ALT / 2), escala=46, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        a = rod.p[i, foco]
        vivos = rod.p[i][rod.vivo[i]]
        grupo = vivos.mean(0) if len(vivos) else a
        cx = float(np.clip(0.6 * a[0] + 0.4 * grupo[0], 5.5, F.LARG - 5.5))
        cy = float(np.clip(0.7 * a[1] + 0.3 * grupo[1] - 1.5, 6.0, F.ALT - 6.0))
        perto = Camera2D(centro=(cx, cy), escala=70, t=t)
        return geral.mistura(perto, min(t / 0.8, 1.0))

    # ------------------------------------------------------------ cenário
    def cenario(self, h, rod, i, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.05)
        borda = [(0, 0), (F.LARG, 0), (F.LARG, F.ALT), (0, F.ALT)]
        h.forma(borda, CIANO, 0.5, 2.0, 0.02)
        h.linha(borda, CIANO, 3.5, 0.9, fechado=True)
        # linha de chegada (verde, tracejada) e linha de saída
        h.linha([(0.2, F.CHEGADA), (F.LARG - 0.2, F.CHEGADA)], VERDE, 3.0, 0.8, tracejado=[10, 8], halo=True)
        h.texto("CHEGADA", (F.LARG / 2, F.CHEGADA + 0.55), 20, VERDE, 0.8)

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
        self.cenario(h, rod, i, t)
        p, vivo, cheg = rod.p[i], rod.vivo[i], rod.chegou[i]
        # blocos deslizantes
        for j in range(F.K):
            cx, cy = float(rod.bx[i, j]), float(F.BLOCO_Y[j])
            ret = [(cx - F.BLOCO_HW, cy - F.BLOCO_HH), (cx + F.BLOCO_HW, cy - F.BLOCO_HH),
                   (cx + F.BLOCO_HW, cy + F.BLOCO_HH), (cx - F.BLOCO_HW, cy + F.BLOCO_HH)]
            h.forma(ret, BLOCO, 0.95, 3.0, 0.4)
        # torreta: corpo + cano apontando para o último disparo
        h.circulo((F.TX, F.TY), 0.55, VERMELHO, 1.0, 3.0, 0.5)
        vivos_i = np.where(vivo & ~cheg)[0]
        if len(vivos_i):
            d = p[vivos_i] - np.array([F.TX, F.TY])
            alvo = p[vivos_i[np.argmin(np.hypot(d[:, 0], d[:, 1]))]]
            ang = math.atan2(alvo[1] - F.TY, alvo[0] - F.TX)
            h.linha([(F.TX, F.TY), (F.TX + 1.0 * math.cos(ang), F.TY + 1.0 * math.sin(ang))], VERMELHO, 6, 1.0)
        # balas: laser curto com rastro
        for b in np.where(rod.bvivo[i])[0]:
            pb = rod.bp[i, b]
            ant = rod.bp[max(i - 2, 0), b]
            h.linha([tuple(ant), tuple(pb)], (1.0, 0.45, 0.4), 4, 0.9)
            self._pontos(h, [pb[0]], [pb[1]], (1.0, 0.85, 0.8), 0.14, 1.0)
        # azuis: rastro curto, halo e núcleo (corpos grandes para ler no celular)
        for a in range(F.A):
            if vivo[a] or cheg[a]:
                tr = rod.p[max(0, i - 9): i + 1: 3, a]
                if len(tr) > 1:
                    h.rastro([tuple(q) for q in tr], VERDE if cheg[a] else CIANO, 3.5, 0.5)
        ativos = vivo
        self._pontos(h, p[ativos, 0], p[ativos, 1], CIANO, 0.62 if h.cam.escala < 60 else 0.5, 0.22)
        self._pontos(h, p[ativos, 0], p[ativos, 1], (0.85, 1.0, 1.0), 0.3 if h.cam.escala < 60 else 0.26, 0.97)
        # quem chegou fica verde na linha
        self._pontos(h, p[cheg, 0], p[cheg, 1], VERDE, 0.5, 0.3)
        # clarão de quem acabou de ser atingido (evento no ponto exato)
        for a in np.where((rod.t_morte >= 0) & (rod.t_morte <= i) & ((i - rod.t_morte) * F.DT < 0.7))[0]:
            h.pulso((float(rod.p[rod.t_morte[a], a, 0]), float(rod.p[rod.t_morte[a], a, 1])), (i - rod.t_morte[a]) * F.DT,
                    VERMELHO, 1.6, 0.7, 3)
        if modo == "replay" and foco is not None:
            if vivo[foco] or cheg[foco]:
                h.destaque((float(p[foco, 0]), float(p[foco, 1])), AMARELO, t, 0.35)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        if nome == "foco":
            return tuple(float(v) for v in rod.p[i, foco])
        return (F.TX, F.TY)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        c, m = rod.contagem(t)
        return [("CHEGARAM", f"{c}/{F.A}", c / F.A, VERDE), ("ATINGIDOS", f"{m}/{F.A}", m / F.A, VERMELHO)]

    def cerebro(self, rod, t, foco):
        i = rod.i(t)
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(rod.genes[rod.cerebro_i:rod.cerebro_i + 1])]
        return dict(camadas=F.CAMADAS, pesos=pesos, ativ=rod.ativ[i], saidas=("→ X", "↑ Y"), titulo="CÉREBRO // AZUL", cor=CIANO)

    def sons(self, rod, t0, t1, modo, foco):
        a, b = rod.i(t0), rod.i(t1)
        if b <= a:
            return []
        mortes = int(((rod.t_morte > a) & (rod.t_morte <= b)).sum())
        return [(t0, "batida", min(0.3 + 0.1 * mortes, 0.7))] if mortes else []

    def ambiente(self, dur):
        return None
