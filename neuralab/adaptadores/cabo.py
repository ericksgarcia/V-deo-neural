"""Adaptador do cabo de guerra de enxames (A x B), vista de cima, holograma.

Mundo: metros, centro da arena em (0, 0). O enxame A parte de baixo (y < 0) e leva a caixa para y > 0.
A câmera gira a cena 90 graus para a arena comprida ocupar a largura da tela: A fica à esquerda, B à direita.
"""
import math

import numpy as np

from ..coevolucao_cabo import ARQ, partidas, suave_fase
from ..desafios.cabo import (ENCOSTA, EMPATE, GOL, H, K, M, R_CAIXA, R_ROBO, VENCE_A, VENCE_B, W, DT)
from ..palco.holo import AMARELO, BRANCO, CIANO, ROSA, VERDE, VERMELHO, Camera2D, clareia
from .base import Adaptador, Rodada

COR_A, COR_B = CIANO, ROSA
JOGOS = 100
ROT = -90.0
ESC_GERAL = 70


class RodadaCabo(Rodada):
    def __init__(self, hist, g):
        self.g, self.dt = g, DT
        gA, gB = hist["A"][g], hist["B"][g]
        pop = len(gA)
        sem = int(hist["semente"][g])
        ia = np.arange(pop)
        ib = np.random.default_rng(sem).permutation(pop)
        self.jogo, self.reg = partidas(gA, gB, ia, ib, sem, gravar=True)
        self.ia, self.ib, self.genes_a, self.genes_b = ia, ib, gA, gB
        self.T = self.reg["pos"].shape[1]
        self.duracao = self.T * DT
        j = self.jogo
        self.fim = np.where(j.t_fim >= 0, j.t_fim * DT, self.duracao)
        cy = self.reg["pos"][:, :, 2 * K, 1]
        self.vitrine = np.arange(0, pop, 3)
        # líder: o jogo da vitrine com a caixa mais longe do centro (a ação mais clara na tela)
        self.lider = int(self.vitrine[np.argmax(np.abs(cy[self.vitrine]).max(1))])
        self.cy = cy

    def i(self, t):
        return int(min(max(t / DT, 0), self.T - 1))


class Cabo(Adaptador):
    titulo = "CABO DE GUERRA"
    experimento = "006"
    cores = {"a": COR_A, "b": COR_B, "verde": VERDE, "vermelho": VERMELHO}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["A"])
        self._cache = {}
        self.suave = {c: suave_fase(hist["m_" + c], hist["fase"]) for c in ("venc_a", "venc_b", "empate")}
        self.treina = hist["treina"]

    def rodada(self, g):
        if g not in self._cache:
            self._cache[g] = RodadaCabo(self.hist, g)
        return self._cache[g]

    # ------------------------------------------------------------ lances
    def duracao_foco(self, rod, foco):
        return min(float(rod.fim[foco]) + 1.2, rod.duracao)

    def janela_lance(self, rod, foco):
        return 0.0, min(float(rod.fim[foco]) + 0.6, rod.duracao)

    def chaves_lento(self, rod, foco):
        j = rod.jogo
        if j.t_fim[foco] >= 0:
            return [float(rod.fim[foco]) - 0.3]
        return []

    def busca(self, rod, tipo):
        """Acha na geração um jogo que mostre o comportamento pedido."""
        j, r = rod.jogo, rod.reg
        idx = np.arange(len(j.estado))
        va, vb = j.estado == VENCE_A, j.estado == VENCE_B
        fim = rod.fim
        criterios = {
            "vitoria_a": (va, -fim),
            "vitoria_b": (vb, -fim),
            "vitoria": (va | vb, -fim),
            "junto_a": (va, j.enc_pico[0]),
            "junto_b": (vb, j.enc_pico[1]),
            "mexeu": (j.t_mexeu >= 0, -j.t_mexeu),
            "parado": (j.t_mexeu < 0, j.prox[0] + j.prox[1]),
            "equilibrio": (~(va | vb), np.minimum(j.enc[0], j.enc[1])),
            "disputa": (j.t_mexeu >= 0, np.minimum(j.enc[0], j.enc[1])),
        }
        ok, nota = criterios[tipo]
        sel = np.where(ok)[0]
        if not len(sel):
            return None
        return int(sel[np.argmax(nota[sel])])

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(0.0, 0.0), escala=ESC_GERAL, rotacao=ROT, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        cy = float(rod.reg["pos"][foco, i, 2 * K, 1])
        cam = geral.mistura(Camera2D(centro=(0.0, 0.45 * cy), escala=96, rotacao=ROT, t=t), min(t / 0.6, 1.0))
        tf = float(rod.fim[foco])
        if 0 <= t - tf < 0.35 and rod.jogo.t_fim[foco] >= 0:
            cam.tremor = 8 * (1 - (t - tf) / 0.35)
        return cam

    # ------------------------------------------------------------ desenho
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.035)
        from ..palco import arte as R
        R.poeira(h, t, alfa=0.2)
        h.forma([(-W, -H), (W, -H), (W, H), (-W, H)], CIANO, 0.5, 3, 0.04)
        # zonas de gol: quem leva a caixa até lá marca
        h.forma([(-W, GOL), (W, GOL), (W, H), (-W, H)], COR_A, 0.5, 2, 0.1, gradiente=False)
        h.forma([(-W, -H), (W, -H), (W, -GOL), (-W, -GOL)], COR_B, 0.5, 2, 0.1, gradiente=False)
        h.linha([(-W, GOL), (W, GOL)], COR_A, 3, 0.8)
        h.linha([(-W, -GOL), (W, -GOL)], COR_B, 3, 0.8)
        h.linha([(-W, 0), (W, 0)], CIANO, 1, 0.18, tracejado=(0.3, 0.3), halo=False)
        h.texto("GOL DO A", (0, (GOL + H) / 2), 24, COR_A, 0.7)
        h.texto("GOL DO B", (0, -(GOL + H) / 2), 24, COR_B, 0.7)

    def _caixa(self, h, rod, k, i, alfa=1.0, destaque=True):
        c = tuple(float(v) for v in rod.reg["pos"][k, i, 2 * K])
        if not destaque:
            h.circulo(c, R_CAIXA, AMARELO, 0.22 * alfa, 1.5, 0.05)
            return
        oct_ = [(c[0] + R_CAIXA * math.cos(a + math.pi / 8), c[1] + R_CAIXA * math.sin(a + math.pi / 8))
                for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
        h.ponto_luz(c, 90, AMARELO, 0.28 * alfa)
        h.forma(oct_, AMARELO, alfa, 3.4, 0.22)
        h.forma([(c[0] + 0.55 * (x - c[0]), c[1] + 0.55 * (y - c[1])) for x, y in oct_], clareia(AMARELO, 0.5), 0.6 * alfa, 1.6, 0.0)

    def _enxame(self, h, rod, k, i, lado, alfa=1.0, destaque=True):
        cor = COR_A if lado == 0 else COR_B
        base = 0 if lado == 0 else K
        cx = rod.reg["pos"][k, i, 2 * K]
        for r in range(K):
            c = tuple(float(v) for v in rod.reg["pos"][k, i, base + r])
            if not destaque:
                h.ponto_luz(c, 7, cor, 0.3 * alfa)
                continue
            d = math.hypot(c[0] - cx[0], c[1] - cx[1])
            enc = d < ENCOSTA
            tr = [tuple(float(v) for v in rod.reg["pos"][k, max(i - s * 2, 0), base + r]) for s in range(9)][::-1]
            h.rastro(tr, cor, 2.4, 0.5 * alfa)
            h.ponto_luz(c, 30, cor, (0.34 if enc else 0.2) * alfa)
            h.circulo(c, R_ROBO, cor, alfa, 3.0, 0.2)
            if enc:   # linha de força: este robô está empurrando a caixa junto com os outros
                u = ((cx[0] - c[0]) / d, (cx[1] - c[1]) / d)
                h.linha([c, (c[0] + u[0] * (d - R_CAIXA), c[1] + u[1] * (d - R_CAIXA))], BRANCO, 2.2, 0.75 * alfa, halo=False)

    def desenha(self, h, rod, t, modo, foco):
        j, r = rod.jogo, rod.reg
        i = rod.i(t)
        self.cenario(h, t)
        if modo == "replay" and foco is not None:
            ks = [foco]
        else:
            ks = [rod.lider] + [k for k in rod.vitrine if k != rod.lider]
        for n, k in enumerate(ks):
            destaque = n == 0 or len(ks) == 1
            alfa = 1.0 if destaque else 0.55
            self._caixa(h, rod, k, i, alfa, destaque)
            for lado in (0, 1):
                self._enxame(h, rod, k, i, lado, alfa, destaque)
        k = ks[0]
        if j.t_fim[k] >= 0 and t >= j.t_fim[k] * DT:
            idade = t - float(j.t_fim[k] * DT)
            est = int(j.estado[k])
            cor = COR_A if est == VENCE_A else COR_B
            c = tuple(float(v) for v in r["pos"][k, i, 2 * K])
            h.pulso(c, idade, cor, 2.6, 0.9, 5)
            h.particulas(c, idade, cor, n=26, alcance=2.4, dur=1.1, semente=int(k))
            h.texto("ENXAME " + ("A" if est == VENCE_A else "B") + " VENCEU", (0, 0.0), 38, cor, min(idade * 3, 1) * 0.95)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        P = rod.reg["pos"][foco, i]
        if nome == "caixa":
            return tuple(float(v) for v in P[2 * K])
        if nome in ("a", "b"):
            base = 0 if nome == "a" else K
            c = P[base:base + K].mean(0)
            return tuple(float(v) for v in c)
        if nome == "gol_a":
            return (0.0, GOL)
        if nome == "gol_b":
            return (0.0, -GOL)
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        g = rod.g
        q = self.treina[g]
        ta = "TREINANDO" if "A" in q else "CONGELADO"
        tb = "TREINANDO" if "B" in q else "CONGELADO"
        return [(f"ENXAME A · {ta}", "VITÓRIAS", float(self.suave["venc_a"][g]), COR_A),
                (f"ENXAME B · {tb}", "VITÓRIAS", float(self.suave["venc_b"][g]), COR_B)]

    def cerebro(self, rod, t, foco):
        k = foco if foco is not None else rod.lider
        i = rod.i(t)
        q = self.treina[rod.g]
        lado = 1 if ("B" in q and "A" not in q) else 0
        base = K if lado else 0
        P = rod.reg["pos"][k, i]
        d = np.linalg.norm(P[base:base + K] - P[2 * K], axis=1)
        robo = int(np.argmin(d))
        genes = (rod.genes_b[rod.ib[k]:rod.ib[k] + 1] if lado else rod.genes_a[rod.ia[k]:rod.ia[k] + 1])
        pesos = [(W_[0], b[0]) for W_, b in ARQ.desempacota(genes)]
        ativ = np.asarray(rod.reg["ativ_b" if lado else "ativ_a"][k, i, robo], dtype=np.float32)
        return dict(camadas=ARQ.camadas, pesos=pesos, ativ=ativ, saidas=("ACEL X", "ACEL Y"),
                    titulo=f"CÉREBRO // ENXAME {'B' if lado else 'A'} (1 DE 5 CORPOS)", cor=COR_B if lado else COR_A)

    # ------------------------------------------------------------ som
    def sons(self, rod, t0, t1, modo, foco):
        j = rod.jogo
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else list(rod.vitrine[:12])
        solo = len(ks) == 1
        for k in ks:
            tf = float(rod.fim[k])
            if j.t_fim[k] >= 0 and t0 <= tf < t1:
                ev.append((tf, "rede", 1.0 if solo else 0.12))
            tm = float(j.t_mexeu[k])
            if tm >= 0 and t0 <= tm < t1:
                ev.append((tm, "batida", 0.8 if solo else 0.08))
        return ev
