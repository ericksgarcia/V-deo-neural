"""Adaptador do sumô de IAs (A x B), vista de cima em estilo holograma.

Mundo: metros, centro da arena em (0, 0). A arena fecha com o tempo (o anel encolhe).
"""
import math

import numpy as np

from ..coevolucao_sumo import ARQ, partidas, suave_fase
from ..desafios.sumo import ARENA, DT, EM_JOGO, EMPATE, RAIO, VENCE_A, VENCE_B, Sumo as Desafio
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, ROSA, VERDE, VERMELHO, Camera2D, clareia
from .base import Adaptador, Rodada

COR_A, COR_B = CIANO, ROSA
JOGOS = 6


class RodadaSumo(Rodada):
    def __init__(self, hist, g):
        self.g, self.dt = g, DT
        gA, gB = hist["A"][g], hist["B"][g]
        pop = len(gA)
        sem = int(hist["semente"][g])
        ia = np.repeat(np.arange(pop), JOGOS)
        ib = np.random.default_rng(sem).permutation(np.tile(np.arange(pop), JOGOS))
        self.jogo, self.reg = partidas(gA, gB, ia, ib, sem, gravar=True)
        self.ia, self.ib, self.genes_a, self.genes_b = ia, ib, gA, gB
        self.T = self.reg["pos"].shape[2]
        self.duracao = self.T * DT
        j = self.jogo
        self.fim = np.where(j.t_fim >= 0, j.t_fim * DT, self.duracao)
        self.vitrine = np.arange(0, len(ia), JOGOS)
        vit = np.zeros(pop)
        np.add.at(vit, ia, j.estado == VENCE_A)
        self.lider_a = int(np.argmax(vit))
        self.lider = int(np.where(ia == self.lider_a)[0][0])

    def i(self, t):
        return int(min(max(t / DT, 0), self.T - 1))


class Sumo(Adaptador):
    titulo = "SUMÔ DE IAs"
    experimento = "005"
    cores = {"a": COR_A, "b": COR_B, "verde": VERDE, "vermelho": VERMELHO}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["A"])
        self._cache = {}
        # mesma média do roteiro: o HUD mostra exatamente os números falados
        self.suave = {c: suave_fase(hist["m_" + c], hist["fase"]) for c in ("venc_a", "venc_b", "empate")}
        self.treina = hist["treina"]

    def rodada(self, g):
        if g not in self._cache:
            self._cache[g] = RodadaSumo(self.hist, g)
        return self._cache[g]

    # ------------------------------------------------------------ lances
    def duracao_foco(self, rod, foco):
        return float(rod.fim[foco]) + 1.0

    def janela_lance(self, rod, foco):
        return 0.0, float(rod.fim[foco]) + 0.5

    def chaves_lento(self, rod, foco):
        j = rod.jogo
        ch = [float(rod.fim[foco]) - 0.15]
        if j.t_contato[foco] >= 0:
            ch.append(float(j.t_contato[foco]))
        return ch

    def busca(self, rod, tipo):
        """Acha na geração uma luta que mostre o comportamento pedido."""
        j, r = rod.jogo, rod.reg
        fim = np.minimum(j.t_fim, r["pos"].shape[2] - 1).clip(0)
        idx = np.arange(len(fim))
        va, vb = j.estado == VENCE_A, j.estado == VENCE_B
        contato = (j.t_contato >= 0) & (j.t_contato < j.t_fim * DT + 1e-6)
        criterios = {
            "sozinho": ((va | vb) & ~contato, -fim),
            "empurrao_a": (va & contato, j.v_contato),
            "empurrao_b": (vb & contato, j.v_contato),
            "arrancada_a": (va & contato & (j.arrancadas[0] > 0), j.v_contato),
            "arrancada_b": (vb & contato & (j.arrancadas[1] > 0), j.v_contato),
            "espera_a": (va & contato & (j.arrancadas[0] == 0), fim),
            "espera_b": (vb & contato & (j.arrancadas[1] == 0), fim),
            "rapida": ((va | vb) & contato, -fim),
        }
        ok, nota = criterios[tipo]
        sel = np.where(ok)[0]
        if not len(sel):
            return None
        return int(sel[np.argmax(nota[sel])])

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(0.0, 0.0), escala=100, t=t)
        if modo != "replay" or foco is None:
            return geral
        tf = float(rod.fim[foco])
        cam = geral.mistura(Camera2D(centro=(0.0, 0.0), escala=118, t=t), min(t / 0.6, 1.0))
        if 0 <= t - tf < 0.35:
            cam.tremor = 8 * (1 - (t - tf) / 0.35)
        return cam

    # ------------------------------------------------------------ desenho
    def arena(self, rod, t):
        return rod.jogo.arena(min(t, rod.duracao))

    def cenario(self, h, rod, t, texto_fase=None):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.04)
        R.poeira(h, t, alfa=0.25)
        raio = self.arena(rod, t)
        pts = [(raio * math.cos(a), raio * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 120, endpoint=False)]
        h.forma(pts, CIANO, 0.55, 3, 0.07)
        # anel externo (limite original) apagado, mostra que a arena fecha
        h.circulo((0, 0), ARENA, CIANO, 0.18, 1.5, 0.0)
        folga = (ARENA - raio) / (ARENA - 1.4 + 1e-6)
        if folga > 0.01:
            h.circulo((0, 0), raio, AMARELO, 0.35 + 0.4 * folga, 3, 0.0)
        h.circulo((0, 0), 0.12, CIANO, 0.5, 1.5, 0.3)
        h.linha([(-0.4, 0), (0.4, 0)], CIANO, 1, 0.3, halo=False)
        h.linha([(0, -0.4), (0, 0.4)], CIANO, 1, 0.3, halo=False)

    def _lutador(self, h, rod, k, lado, i, t, alfa=1.0, destaque=True):
        cor = COR_A if lado == 0 else COR_B
        x, y = rod.reg["pos"][lado, k, i]
        vx, vy = rod.reg["vel"][lado, k, i]
        j = rod.jogo
        est = int(rod.reg["estado"][k, i])
        perdeu = (lado == 0 and est == VENCE_B) or (lado == 1 and est == VENCE_A)
        ganhou = (lado == 0 and est == VENCE_A) or (lado == 1 and est == VENCE_B)
        c = (float(x), float(y))
        if not destaque:
            h.ponto_luz(c, 9, cor, 0.22 * alfa)
            h.circulo(c, RAIO, cor, 0.1 * alfa, 1.2, 0.03)
            return
        v = math.hypot(vx, vy)
        # rastro
        n = 12
        tr = [tuple(rod.reg["pos"][lado, k, max(i - s * 2, 0)]) for s in range(n)][::-1]
        h.rastro([(float(a), float(b)) for a, b in tr], cor, 3, 0.7 * alfa)
        cor_i = VERMELHO if perdeu and False else cor
        h.ponto_luz(c, 46, cor_i, 0.28 * alfa)
        h.circulo(c, RAIO, cor_i, alfa, 3.2, 0.2)
        h.circulo(c, RAIO * 0.62, clareia(cor_i, 0.4), 0.6 * alfa, 1.6, 0.0)
        if v > 0.4:   # seta de velocidade
            u = (vx / v, vy / v)
            h.seta((c[0] + u[0] * RAIO * 0.7, c[1] + u[1] * RAIO * 0.7),
                   (c[0] + u[0] * (RAIO + 0.15 * v), c[1] + u[1] * (RAIO + 0.15 * v)), cor_i, 2.2, 0.8 * alfa, 0.18)
        # recarga da arrancada
        cd = float(rod.reg["cd"][lado, k, i])
        if cd > 0:
            h.linha([(c[0] + RAIO * 1.35 * math.cos(a), c[1] + RAIO * 1.35 * math.sin(a))
                     for a in np.linspace(-1.2, -1.2 + 2.4 * (1 - cd / 1.4), 8)], BRANCO, 1.6, 0.4, halo=False)
        h.texto("A" if lado == 0 else "B", (c[0], c[1] - 0.14), 26, BRANCO, 0.95 * alfa)

    def desenha(self, h, rod, t, modo, foco):
        j, r = rod.jogo, rod.reg
        i = rod.i(t)
        self.cenario(h, rod, t)
        if modo == "replay" and foco is not None:
            ks = [foco]
        else:
            ks = [rod.lider] + [k for k in rod.vitrine if k != rod.lider]
        for n, k in enumerate(ks):
            destaque = n == 0
            alfa = 1.0
            ik = i
            for lado in (1, 0):
                self._lutador(h, rod, k, lado, ik, t, alfa, destaque)
        # choque do destaque
        k = ks[0]
        if j.t_contato[k] >= 0:
            idade = t - float(j.t_contato[k])
            if 0 <= idade < 0.45:
                ponto = tuple(0.5 * (r["pos"][0, k, i] + r["pos"][1, k, i]))
                h.pulso(ponto, idade, BRANCO, 1.2, 0.45, 4)
                h.particulas(ponto, idade, AMARELO, n=10, alcance=1.0, dur=0.45, semente=int(k))
        # resultado
        if j.t_fim[k] >= 0 and t >= j.t_fim[k] * DT:
            tf = float(j.t_fim[k] * DT)
            est = int(j.estado[k])
            idade = t - tf
            if est in (VENCE_A, VENCE_B):
                perde = 1 if est == VENCE_A else 0
                xp, yp = r["pos"][perde, k, i]
                h.pulso((float(xp), float(yp)), idade, VERMELHO, 2.2, 0.8, 5)
                h.particulas((float(xp), float(yp)), idade, VERMELHO, n=14, alcance=1.6, dur=0.9, semente=int(k))
                cor = COR_A if est == VENCE_A else COR_B
                h.texto(("A" if est == VENCE_A else "B") + " VENCEU", (0, 0.0), 40, cor, min(idade * 3, 1) * 0.95)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        if nome == "a":
            return tuple(float(v) for v in rod.reg["pos"][0, foco, i])
        if nome == "b":
            return tuple(float(v) for v in rod.reg["pos"][1, foco, i])
        if nome == "choque":
            return tuple(float(v) for v in 0.5 * (rod.reg["pos"][0, foco, i] + rod.reg["pos"][1, foco, i]))
        if nome == "centro":
            return (0.0, 0.0)
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        g = rod.g
        q = self.treina[g]
        ta = "TREINANDO" if "A" in q else "CONGELADA"
        tb = "TREINANDO" if "B" in q else "CONGELADA"
        return [(f"IA A · {ta}", "VITÓRIAS", float(self.suave["venc_a"][g]), COR_A),
                (f"IA B · {tb}", "VITÓRIAS", float(self.suave["venc_b"][g]), COR_B)]

    def cerebro(self, rod, t, foco):
        k = foco if foco is not None else rod.lider
        i = rod.i(t)
        q = self.treina[rod.g]
        lado = 1 if ("B" in q and "A" not in q) else 0
        genes = (rod.genes_b[rod.ib[k]:rod.ib[k] + 1] if lado else rod.genes_a[rod.ia[k]:rod.ia[k] + 1])
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(genes)]
        return dict(camadas=ARQ.camadas, pesos=pesos, ativ=rod.reg["ativ_b" if lado else "ativ_a"][k, i],
                    saidas=("RADIAL", "LATERAL", "ARRANCADA"),
                    titulo=f"CÉREBRO // IA {'B' if lado else 'A'}", cor=COR_B if lado else COR_A)

    # ------------------------------------------------------------ som
    def sons(self, rod, t0, t1, modo, foco):
        j = rod.jogo
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else list(rod.vitrine)
        for k in ks:
            tc, tf = float(j.t_contato[k]), float(rod.fim[k])
            solo = len(ks) == 1
            if tc >= 0 and t0 <= tc < t1:
                ev.append((tc, "batida", 0.9 if solo else 0.12))
            if j.t_fim[k] >= 0 and t0 <= tf < t1:
                ev.append((tf, "fora", 1.0 if solo else 0.15))
        return ev
