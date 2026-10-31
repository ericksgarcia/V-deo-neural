"""Adaptador do Paciente Zero, vista de cima em estilo holograma (mundo = metros da cidade).

Cada ponto é uma IA: ciano = saudável, verde-tóxico = infectado. Quem se contagia solta um anel de pulso.
O vídeo mostra UMA cidade da vitrine por geração (a mais típica: a que fecha mais perto da média).
"""
import math

import numpy as np

from ..coevolucao_paciente import ARQ, campeao_sau, cidades, vitrine
from ..desafios import paciente as P
from ..palco.holo import AMARELO, BRANCO, CIANO, VERMELHO, Camera2D
from .base import Adaptador, Rodada

TOXICO = (0.62, 1.0, 0.12)
CINZA = (0.55, 0.62, 0.8)


class RodadaCidade(Rodada):
    def __init__(self, hist, g, campeao=False):
        self.g, self.dt = g, P.DT
        gs, gv = hist["sau"][g], hist["vir"][g]
        sem = int(hist["semente"][g])
        isa, ivi = vitrine(len(gs), sem)
        jogo, reg = cidades(gs, gv, isa, ivi, sem, gravar=True)
        final = jogo.curva[:, -1]
        w = int(np.argmin(np.abs(final - final.mean())))               # a cidade mais típica
        if campeao:                                                    # a cidade do campeão: vitrine pareia o saudável i com a cidade i
            w = campeao_sau(hist, g)
        self.mundo, self.genes_s, self.genes_v, self.isa, self.ivi = w, gs, gv, int(isa[w]), int(ivi[w])
        self.p = reg["p"][w]                                           # (T, A, 2)
        self.inf = reg["inf"][w]                                       # (T, A)
        self.ativ_s, self.ativ_v = reg["ativ_s"][w], reg["ativ_v"][w]
        self.t_inf = jogo.t_inf[w]
        self.curva = jogo.curva[w]
        self.T = self.p.shape[0]
        self.duracao = self.T * P.DT
        self.n = P.A
        self.final = int(final[w])

    def i(self, t):
        return int(min(max(t / P.DT, 0), self.T - 1))

    def contagem(self, t):
        n = int(self.inf[self.i(t)].sum())
        return P.A - n, n


class Paciente(Adaptador):
    titulo = "PACIENTE ZERO"
    experimento = "010"
    cores = {"saudavel": CIANO, "infectado": TOXICO}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["sau"])
        self._cache = {}
        k = 7
        self.suave = np.convolve(np.pad(hist["m_saudaveis"], (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")

    def rodada(self, g):
        """g < total_ger: a cidade mais típica da geração; g >= total_ger: a cidade do CAMPEÃO da geração g - total_ger."""
        if g not in self._cache:
            camp = g >= self.total_ger
            self._cache[g] = RodadaCidade(self.hist, g - self.total_ger if camp else g, camp)
        return self._cache[g]

    # ------------------------------------------------------------ lances (replay: foco = agente)
    def duracao_foco(self, rod, foco):
        return min(rod.duracao, 12.0)

    def janela_lance(self, rod, foco):
        return 0.0, min(rod.duracao, 12.0)

    def chaves_lento(self, rod, foco):
        ti = rod.t_inf[foco]
        return [ti * P.DT] if ti > 0 else []

    def busca(self, rod, tipo):
        """Agente para o replay. 'zero' = paciente zero; 'primeiro' = a primeira vítima; 'ultimo' = o último
        a se contagiar; 'ileso' = um saudável que chega ao fim da cidade sem se contagiar."""
        ti = rod.t_inf
        if tipo == "zero":
            return 0
        cont = np.where(ti > 0)[0]
        if tipo == "primeiro":
            return int(cont[np.argmin(ti[cont])]) if len(cont) else 1
        if tipo == "ultimo":
            return int(cont[np.argmax(ti[cont])]) if len(cont) else 1
        ileso = np.where(ti < 0)[0]
        return int(ileso[0]) if len(ileso) else 1

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(P.LARG / 2, P.ALT / 2), escala=45, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        a, z = rod.p[i, foco], rod.p[i, 0]
        meio = ((a[0] + z[0]) / 2, (a[1] + z[1]) / 2)
        perto = Camera2D(centro=(float(np.clip(meio[0], 6, P.LARG - 6)), float(np.clip(meio[1], 5, P.ALT - 5))),
                         escala=70, t=t)
        return geral.mistura(perto, min(t / 0.8, 1.0))

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.05)
        borda = [(0, 0), (P.LARG, 0), (P.LARG, P.ALT), (0, P.ALT)]
        h.forma(borda, CIANO, 0.5, 2.0, 0.02)
        h.linha(borda, CIANO, 3.5, 0.9, fechado=True)

    def _pontos(self, h, xs, ys, cor, r_m, alfa):
        import cairo
        ctx = h.ctx
        ctx.set_operator(cairo.OPERATOR_ADD)
        X, Y = h.tela(np.asarray(xs, float), np.asarray(ys, float))
        r = h.px(r_m)
        h._cor(cor, alfa)
        for x, y in zip(X, Y):
            ctx.arc(float(x), float(y), r, 0, 2 * math.pi)
            ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        i = rod.i(t)
        p, inf = rod.p[i], rod.inf[i]
        sau, vir = ~inf, inf
        zoom = h.cam.escala > 60
        # saudáveis: núcleo claro + halo suave
        self._pontos(h, p[sau, 0], p[sau, 1], CIANO, 0.42 if not zoom else 0.3, 0.16)
        self._pontos(h, p[sau, 0], p[sau, 1], (0.85, 1.0, 1.0), 0.17 if not zoom else 0.14, 0.9)
        # infectados: halo tóxico pulsando + núcleo
        pulso = 0.8 + 0.2 * math.sin(t * 9)
        self._pontos(h, p[vir, 0], p[vir, 1], TOXICO, 0.62 * pulso, 0.20)
        self._pontos(h, p[vir, 0], p[vir, 1], (0.95, 1.0, 0.6), 0.2, 0.95)
        # anel de pulso de quem acabou de se contagiar
        novos = np.where((rod.t_inf >= 0) & (rod.t_inf <= i) & ((i - rod.t_inf) * P.DT < 0.9) & (rod.t_inf > 0))[0]
        for a in novos[:30]:
            h.pulso((float(p[a, 0]), float(p[a, 1])), (i - rod.t_inf[a]) * P.DT, TOXICO, 1.8, 0.9, 3)
        # destaque individual (segue o agente a cada quadro, sem anel nem rótulo): paciente zero e, no replay, o agente em foco
        if vir[0]:
            h.destaque((float(p[0, 0]), float(p[0, 1])), VERMELHO, t, 0.45)
        if modo == "replay" and foco is not None and foco != 0:
            h.destaque((float(p[foco, 0]), float(p[foco, 1])), TOXICO if inf[foco] else AMARELO, t, 0.45)
            tr = rod.p[max(0, i - 30): i + 1: 2, foco]
            if len(tr) > 1:
                h.rastro([tuple(q) for q in tr], TOXICO if inf[foco] else CIANO, 3, 0.8)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        p, inf = rod.p[i], rod.inf[i]
        if nome in ("zero", "ladrao"):
            return tuple(float(v) for v in p[0])
        if nome == "foco":
            return tuple(float(v) for v in p[foco])
        if nome == "infectados":
            return tuple(float(v) for v in p[inf].mean(0)) if inf.any() else tuple(float(v) for v in p[0])
        if nome == "saudaveis":
            return tuple(float(v) for v in p[~inf].mean(0)) if (~inf).any() else tuple(float(v) for v in p[0])
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        if foco is not None and False:
            t = rod.duracao
        s, v = rod.contagem(t)
        return [("SAUDÁVEIS", f"{s}/{P.A}", s / P.A, CIANO), ("INFECTADOS", f"{v}/{P.A}", v / P.A, TOXICO)]

    def cerebro(self, rod, t, foco):
        i = rod.i(t)
        genes = rod.genes_s[rod.isa:rod.isa + 1]
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(genes)]
        return dict(camadas=P.CAMADAS, pesos=pesos, ativ=rod.ativ_s[i], saidas=("→ X", "↑ Y"),
                    titulo="CÉREBRO // SAUDÁVEL", cor=CIANO)

    def sons(self, rod, t0, t1, modo, foco):
        a, b = rod.i(t0), rod.i(t1)
        if b <= a:
            return []
        novos = int(((rod.t_inf > a) & (rod.t_inf <= b)).sum())
        return [(t0, "batida", min(0.25 + 0.08 * novos, 0.7))] if novos else []

    def ambiente(self, dur):
        return None
