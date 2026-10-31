"""Adaptador da Queimada de IAs, vista de cima em estilo holograma (quadra em pé, mundo = metros).

Azuis (ciano) na metade de baixo, vermelhas (magenta) na de cima, bola neon. Quem é atingido vira um clarão e some da
quadra (sem violência). O "campeão" é a melhor equipe azul da geração (torneio contra os vermelhos da própria geração); nos
replays é a MESMA equipe jogando 60 partidas, e cada azul vivo leva a seta de destaque presa a ele.
"""
import math

import numpy as np

from ..coevolucao_queimada import ARQ, partidas
from ..desafios import queimada as Q
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .base import Adaptador, Rodada

AZUL, ROSA = CIANO, MAGENTA
BOLA = (1.0, 0.92, 0.45)


def campeao_da_geracao(hist, g, rodadas=4):
    """Índice da melhor equipe azul da geração g: maior nota média em `rodadas` partidas contra os vermelhos da geração."""
    cache = hist.setdefault("_camp", {}) if isinstance(hist, dict) else {}
    if g not in cache:
        ga, gb = hist["az"][g], hist["vm"][g]
        pop = len(ga)
        sem = int(hist["semente"][g])
        rng = np.random.default_rng(sem + 11)
        ia = np.repeat(np.arange(pop), rodadas)
        jogo, _ = partidas(ga, gb, ia, rng.integers(0, pop, len(ia)), sem + 12)
        nota = np.zeros(pop)
        np.add.at(nota, ia, jogo.aptidoes()[0])
        cache[g] = int(np.argmax(nota))
    return cache[g]


class RodadaQ(Rodada):
    def __init__(self, hist, g, campeao=False):
        self.g, self.dt = g, Q.DT
        ga, gb = hist["az"][g], hist["vm"][g]
        sem = int(hist["semente"][g])
        pop = len(ga)
        ib = np.random.default_rng(sem).permutation(pop)
        ia = np.arange(pop)
        if campeao:
            self.campeao = campeao_da_geracao(hist, g)
            ia = np.full(pop, self.campeao)
        self.ia, self.ib = ia, ib
        self.jogo, self.reg = partidas(ga, gb, ia, ib, sem, gravar=True)
        self.genes_a, self.genes_b = ga, gb
        self.n = pop
        self.T = self.reg["bp"].shape[1]
        self.duracao = self.T * Q.DT
        vivo = self.reg["vivo"]                                   # (n, T, 2, NS)
        caiu = ~vivo
        self.t_cai = np.where(caiu.any(1), caiu.argmax(1), -1)    # (n, 2, NS): passo em que cada jogador saiu
        primeiro = np.where(self.t_cai >= 0, self.t_cai, 10 ** 9).reshape(pop, -1).min(1)
        self.primeiro = np.where(primeiro < 10 ** 9, primeiro, -1)
        fa, _ = self.jogo.aptidoes()
        self.lider = int(np.argmax(fa))

    def i(self, t):
        return int(min(max(t / Q.DT, 0), self.T - 1))

    def contagem(self, t, k=None):
        """Jogadores na quadra no instante t: de uma partida (k) ou somados em todas."""
        v = self.reg["vivo"][:, self.i(t)] if k is None else self.reg["vivo"][k:k + 1, self.i(t)]
        return int(v[:, 0].sum()), int(v[:, 1].sum()), 3 * len(v)


class Queimada(Adaptador):
    titulo = "QUEIMADA DE IAs"
    experimento = "017"
    cores = {"azul": AZUL, "vermelha": ROSA, "bola": BOLA}
    JANELA = 6.0

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["az"])
        self._cache = {}

    def rodada(self, g, campeao=False):
        """ger >= total_ger pede o CAMPEÃO da geração g - total_ger: a mesma equipe azul jogando 60 partidas."""
        if g >= self.total_ger:
            g, campeao = g - self.total_ger, True
        if (g, campeao) not in self._cache:
            self._cache[(g, campeao)] = RodadaQ(self.hist, g, campeao)
        return self._cache[(g, campeao)]

    # ------------------------------------------------------------ lances
    def _janela(self, rod, foco):
        m = rod.primeiro[foco]
        if m < 0:
            return 0.0, min(rod.duracao, self.JANELA)
        fim = min((m + 1) * rod.dt + 1.0, rod.duracao)
        return max(0.0, fim - self.JANELA), fim

    def duracao_foco(self, rod, foco):
        return self._janela(rod, foco)[1]

    def janela_lance(self, rod, foco):
        return self._janela(rod, foco)

    def chaves_lento(self, rod, foco):
        m = rod.primeiro[foco]
        return [m * rod.dt] if m >= 0 else []

    def busca(self, rod, tipo, excluir=()):
        """'acerto' = azul acerta um vermelho (o mais cedo); 'levou' = azul é atingido primeiro (mais cedo);
        'vence' = azul vence 3x0 ou com mais gente; 'segura' = azul na frente segurando a bola por mais tempo;
        'zero' = ninguém atingido e a bola mais rápida."""
        j = rod.jogo
        v = rod.t_cai
        t_verm = np.where(v[:, 1] >= 0, v[:, 1], 10 ** 9).min(1)
        t_azul = np.where(v[:, 0] >= 0, v[:, 0], 10 ** 9).min(1)
        a, b = j.vivos()
        todos = np.ones(rod.n, bool)
        crit = {"acerto": (t_verm < 10 ** 9, -t_verm.astype(float)),
                "levou": ((t_azul < 10 ** 9) & (t_azul <= t_verm), -t_azul.astype(float)),
                "levou_tarde": ((t_azul < 10 ** 9) & (t_azul <= t_verm), t_azul.astype(float)),
                "vence": (a > b, (a - b) * 10.0 - j.t_fim / Q.PASSOS),
                "segura": (a > b, j.seg_lider[0] / np.maximum(j.lider_passos[0], 1) + 0.01 * j.lider_passos[0]),
                "zero": ((t_azul == 10 ** 9) & (t_verm == 10 ** 9), j.seg_passos[0] + j.seg_passos[1])}
        ok, nota = crit[tipo]
        idx = [int(k) for k in np.where(ok)[0] if int(k) not in excluir]
        return idx[int(np.argmax(nota[idx]))] if idx else None

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(Q.LARG / 2, Q.ALT / 2), escala=60, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        b = rod.reg["bp"][foco, i]
        perto = Camera2D(centro=(Q.LARG / 2, float(np.clip(0.5 * b[1] + 0.5 * Q.ALT / 2, 5.0, 11.0))), escala=70, t=t)
        cam = geral.mistura(perto, min((t - self._janela(rod, foco)[0]) / 0.8, 1.0))
        m = rod.primeiro[foco] * rod.dt
        if rod.primeiro[foco] >= 0 and 0 <= t - m < 0.3:
            cam.tremor = 6 * (1 - (t - m) / 0.3)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.02, 0.04, 0.09))
        h.grade(1.0, alfa=0.04)
        R.poeira(h, t, alfa=0.15)
        meio = Q.MEIO
        h.forma([(0, 0), (Q.LARG, 0), (Q.LARG, meio), (0, meio)], AZUL, 0.0, 0.0, 0.05)
        h.forma([(0, meio), (Q.LARG, meio), (Q.LARG, Q.ALT), (0, Q.ALT)], ROSA, 0.0, 0.0, 0.05)
        borda = [(0, 0), (Q.LARG, 0), (Q.LARG, Q.ALT), (0, Q.ALT)]
        h.linha(borda, BRANCO, 3.5, 0.75, fechado=True)
        h.linha([(0, meio), (Q.LARG, meio)], BRANCO, 3.0, 0.6, tracejado=[14, 10], halo=False)

    # ------------------------------------------------------------ jogadores
    def _jogador(self, h, rod, k, tm, j, i, t, nitido):
        cor = AZUL if tm == 0 else ROSA
        m = rod.t_cai[k, tm, j]
        idade = (i - m) * rod.dt if (m >= 0 and i >= m) else -1.0
        if 0 <= idade:
            if idade < 0.9:
                p = rod.reg["pa" if tm == 0 else "pb"][k, m, j]
                h.pulso((float(p[0]), float(p[1])), idade, BRANCO, 1.8, 0.8, 3)
                h.particulas((float(p[0]), float(p[1])), idade, cor, n=8, alcance=1.6, dur=0.9, semente=int(k * 7 + j))
            return
        p = rod.reg["pa" if tm == 0 else "pb"][k, i, j]
        if not nitido:
            h.circulo((float(p[0]), float(p[1])), Q.R * 1.1, cor, 0.16, 1.6, 0.3)
            return
        ant = rod.reg["pa" if tm == 0 else "pb"][k, max(i - 1, 0), j]
        v = p - ant
        ang = math.atan2(v[1], v[0]) if np.hypot(*v) > 1e-3 else (math.pi / 2 if tm == 0 else -math.pi / 2)
        R.avatar(h, (float(p[0]), float(p[1])), ang, cor, t, alfa=1.0, passo=(t * 2.4 if np.hypot(*v) > 1e-3 else None),
                 escala=1.9, base=False)

    def _bola(self, h, rod, k, i, t):
        b = rod.reg["bp"][k, i]
        est = rod.reg["est"][k, i]
        if est == Q.VOO:
            tr = rod.reg["bp"][k, max(0, i - 6): i + 1]
            if len(tr) > 1:
                h.rastro([tuple(q) for q in tr], BOLA, 11, 0.9)
        h.ponto_luz((float(b[0]), float(b[1])), 52 if est == Q.VOO else 40, BOLA, 0.8)
        h.circulo((float(b[0]), float(b[1])), Q.RB * 1.6, BOLA, 1.0, 4.0, 0.95)

    def _jogo(self, h, rod, k, i, t, nitido, replay):
        for tm in (1, 0):
            for j in range(Q.NS):
                self._jogador(h, rod, k, tm, j, i, t, nitido)
        if nitido:
            self._bola(h, rod, k, i, t)
            if replay:
                for j in range(Q.NS):
                    if rod.t_cai[k, 0, j] < 0 or i < rod.t_cai[k, 0, j]:
                        p = rod.reg["pa"][k, i, j]
                        h.destaque((float(p[0]), float(p[1])), AMARELO, t, raio=0.45)

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        i = rod.i(t)
        if modo == "replay" and foco is not None:
            self._jogo(h, rod, foco, i, t, True, True)
            return
        fantasmas = [k for k in range(0, rod.n, max(1, rod.n // 5)) if k != rod.lider][:5]
        for k in fantasmas:
            self._jogo(h, rod, k, i, t, False, False)
            b = rod.reg["bp"][k, i]
            h.circulo((float(b[0]), float(b[1])), Q.RB * 1.1, BOLA, 0.3, 1.5, 0.5)
        self._jogo(h, rod, rod.lider, i, t, True, False)

    def ponto(self, rod, foco, nome, t):
        return tuple(float(v) for v in rod.reg["bp"][foco, rod.i(t)])

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        a, b, tot = rod.contagem(t, foco)
        return [("AZUIS NA QUADRA", f"{a}/{tot}", a / tot, AZUL), ("VERMELHAS NA QUADRA", f"{b}/{tot}", b / tot, ROSA)]

    def cerebro(self, rod, t, foco):
        k = rod.lider if foco is None else foco
        i = rod.i(t)
        genes = rod.genes_a[rod.ia[k]:rod.ia[k] + 1]
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(genes)]
        return dict(camadas=Q.CAMADAS, pesos=pesos, ativ=rod.reg["ativ_a"][k, i], saidas=("→ X", "↑ Y", "LANÇA", "MIRA"),
                    titulo="CÉREBRO // AZUL", cor=AZUL)

    def sons(self, rod, t0, t1, modo, foco):
        a, b = rod.i(t0), rod.i(t1)
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        n = 0
        for k in ks:
            m = rod.primeiro[k]
            if m >= 0 and a <= m < b:
                n += 1
        return [(t0, "batida", min(0.4 + 0.1 * n, 1.0) if modo != "replay" else 1.0)] if n else []

    def ambiente(self, dur):
        return None
