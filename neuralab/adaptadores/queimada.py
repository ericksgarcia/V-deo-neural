"""Adaptador da Queimada de IAs, vista de cima em estilo holograma (mundo = metros da quadra, em pé).

Azuis embaixo, vermelhos em cima, bola amarela. O destaque ("o campeão") é a melhor equipe do lado escolhido (`lado`: "a" = azul
ou "b" = vermelho); a câmera do replay acompanha a partida (sem anel nem rótulo; só a seta presa a cada jogador do campeão).
"""
import math

import numpy as np

from ..coevolucao_queimada import ARQ, partidas, partidas_vitrine
from ..desafios import queimada as Q
from ..palco import arte as R
from ..palco.holo import AMARELO, AZUL, BRANCO, VERMELHO, Camera2D
from .base import Adaptador, Rodada

COR = (AZUL, VERMELHO)


def campeao_da_geracao(hist, g, lado):
    """Índice da melhor equipe do lado ("a"/"b") na geração g: maior nota média em 4 partidas cada."""
    ga, gb = hist["a"][g], hist["b"][g]
    sem = int(hist["semente"][g])
    pop = len(ga)
    rng = np.random.default_rng(sem + 11)
    il = np.repeat(np.arange(pop), 4)
    outro = rng.integers(0, pop, len(il))
    if lado == "b":
        jogo, _ = partidas(ga, gb, outro, il, sem + 12)
        nota = jogo.aptidoes()[1]
    else:
        jogo, _ = partidas(ga, gb, il, outro, sem + 12)
        nota = jogo.aptidoes()[0]
    tot = np.zeros(pop)
    np.add.at(tot, il, nota)
    return int(np.argmax(tot))


class RodadaQ(Rodada):
    def __init__(self, hist, g, lado, campeao=False):
        self.g, self.dt, self.lado = g, Q.DT, lado
        ga, gb = hist["a"][g], hist["b"][g]
        sem = int(hist["semente"][g])
        self.ia, self.ib = partidas_vitrine(len(ga), sem)
        if campeao:         # a MESMA equipe campeã contra 100 times diferentes do outro lado
            self.campeao = campeao_da_geracao(hist, g, lado)
            if lado == "a":
                self.ia = np.full(len(ga), self.campeao)
            else:
                self.ib = np.full(len(ga), self.campeao)
        self.jogo, self.reg = partidas(ga, gb, self.ia, self.ib, sem, gravar=True)
        self.genes_a, self.genes_b = ga, gb
        self.n = len(self.ia)
        self.T = self.reg["vivo"].shape[1]
        self.duracao = self.T * Q.DT
        v = self.reg["vivo"]                                              # (n, T, 6)
        morto = (~v).any(2)                                               # alguém fora
        self.morte = np.where(morto.any(1), morto.argmax(1), -1)          # 1ª eliminação da partida
        self.time_morte = np.full(self.n, -1)
        for k in np.where(self.morte >= 0)[0]:
            self.time_morte[k] = int(Q.EQUIPE[int(np.argmax(~v[k, self.morte[k]]))])
        fa, fb = self.jogo.aptidoes()
        self.lider = int(np.argmax(fa if lado == "a" else fb))

    def i(self, t):
        return int(min(max(t / Q.DT, 0), self.T - 1))


class Queimada(Adaptador):
    titulo = "QUEIMADA DE IAs"
    experimento = "017"
    cores = {"azul": AZUL, "vermelho": VERMELHO, "bola": AMARELO}

    def __init__(self, hist, lado="a"):
        self.hist = hist
        self.lado = lado
        self.total_ger = len(hist["a"])
        self._cache = {}

    def rodada(self, g, campeao=False):
        """ger >= total_ger pede a rodada do CAMPEÃO da geração g - total_ger: a mesma equipe jogando 100 vezes."""
        if g >= self.total_ger:
            g, campeao = g - self.total_ger, True
        if (g, campeao) not in self._cache:
            self._cache[(g, campeao)] = RodadaQ(self.hist, g, self.lado, campeao)
        return self._cache[(g, campeao)]

    # ------------------------------------------------------------ lances
    JANELA = 6.0

    def _janela(self, rod, foco):
        m = rod.morte[foco]
        fim = ((m + 1) * rod.dt + 1.0) if m >= 0 else min(rod.duracao, self.JANELA)
        return max(0.0, fim - self.JANELA), min(fim, rod.duracao)

    def duracao_foco(self, rod, foco):
        return self._janela(rod, foco)[1]

    def janela_lance(self, rod, foco):
        return self._janela(rod, foco)

    def chaves_lento(self, rod, foco):
        m = rod.morte[foco]
        return [m * rod.dt] if m >= 0 else []

    def busca(self, rod, tipo, excluir=()):
        """'campeao' = melhor partida do lado; 'azul_acerta' / 'azul_cai' = 1ª eliminação mais cedo de vermelho / azul;
        'livre' = ninguém eliminado; 'varre' = o lado campeão elimina os 3 mais cedo; 'segura' = lado que mais segura a bola sem lance."""
        j = rod.jogo
        pl = j.placar()
        fa, fb = j.aptidoes()
        m = rod.morte.astype(float)
        eu = 0 if rod.lado == "a" else 1
        crit = {"campeao": (np.ones(rod.n, bool), fa if eu == 0 else fb),
                "azul_acerta": (rod.time_morte == 1, -np.abs(m * rod.dt - 7.0)), "azul_cai": (rod.time_morte == 0, -np.abs(m * rod.dt - 7.0)),
                "acerta": (rod.time_morte == 1 - eu, -np.abs(m * rod.dt - 7.0)), "cai": (rod.time_morte == eu, -np.abs(m * rod.dt - 7.0)),
                "livre": (rod.morte < 0, fa if eu == 0 else fb),
                "varre": (pl[:, 1 - eu] == 0, -j.t_fim.astype(float)),
                "segura": (rod.morte < 0, j.segura[:, eu] / np.maximum(j.t_ult + 1, 1))}
        ok, nota = crit[tipo]
        idx = [int(k) for k in np.where(ok)[0] if int(k) not in excluir]
        return idx[int(np.argmax(nota[idx]))] if idx else None

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(Q.LARG / 2, Q.ALT / 2), escala=73, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        v = rod.reg["vivo"][foco, i]
        c = rod.reg["P"][foco, i][v].mean(0) if v.any() else np.array([Q.LARG / 2, Q.ALT / 2])
        perto = Camera2D(centro=(Q.LARG / 2, float(np.clip(c[1], 5.6, 8.4))), escala=96, t=t)
        cam = geral.mistura(perto, min((t - self._janela(rod, foco)[0]) / 0.8, 1.0))
        m = rod.morte[foco] * rod.dt
        if rod.morte[foco] >= 0 and 0 <= t - m < 0.3:
            cam.tremor = 8 * (1 - (t - m) / 0.3)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.01, 0.02, 0.05))
        h.grade(1.0, alfa=0.035)
        R.poeira(h, t, alfa=0.1)
        borda = [(0, 0), (Q.LARG, 0), (Q.LARG, Q.ALT), (0, Q.ALT)]
        h.forma([(0, 0), (Q.LARG, 0), (Q.LARG, Q.MEIO), (0, Q.MEIO)], AZUL, 0.0, 0.0, 0.05)
        h.forma([(0, Q.MEIO), (Q.LARG, Q.MEIO), (Q.LARG, Q.ALT), (0, Q.ALT)], VERMELHO, 0.0, 0.0, 0.05)
        h.linha(borda, (0.6, 0.85, 1.0), 3.0, 0.6, fechado=True)
        h.linha([(0, Q.MEIO), (Q.LARG, Q.MEIO)], BRANCO, 2.5, 0.55, tracejado=(14, 10))

    # ------------------------------------------------------------ desenho de uma partida
    def _bolas(self, h, rod, k, i, t, alfa=1.0, rastro=True, raio=0.2):
        for b in range(2):
            c = rod.reg["bpos"][k, i, b]
            st = int(rod.reg["bst"][k, i, b])
            tr = None
            if st == Q.VOA and rastro:
                tr = [tuple(map(float, rod.reg["bpos"][k, max(i - d, 0), b])) for d in (6, 4, 2, 0)]
            R.bola(h, (float(c[0]), float(c[1])), t, alfa=alfa, rastro=tr, cor=AMARELO, raio=raio)

    def _fantasma(self, h, rod, k, i, t):
        for p in range(6):
            if not rod.reg["vivo"][k, i, p]:
                continue
            c = rod.reg["P"][k, i, p]
            h.circulo((float(c[0]), float(c[1])), 0.38, COR[Q.EQUIPE[p]], 0.4, 1.6, 0.35)
        for b in range(2):
            c = rod.reg["bpos"][k, i, b]
            h.circulo((float(c[0]), float(c[1])), 0.16, AMARELO, 0.55, 1.5, 0.5)

    def _heroi(self, h, rod, k, i, t):
        v = rod.reg["vivo"][k, i]
        for p in range(6):
            if not v[p]:
                continue
            c = rod.reg["P"][k, i, p]
            e = int(Q.EQUIPE[p])
            h.circulo((float(c[0]), float(c[1])), Q.RAIO, COR[e], 0.4, 1.6, 0.12)
            quieto = np.hypot(*(rod.reg["P"][k, i, p] - rod.reg["P"][k, max(i - 1, 0), p])) < 1e-4
            R.avatar(h, (float(c[0]), float(c[1])), float(rod.reg["ang"][k, i, p]), COR[e], t, alfa=1.0,
                     passo=None if quieto else t * 2.4, escala=2.0, base=False)
            if (e == 0) == (rod.lado == "a"):          # campeão: seta presa a CADA jogador, recalculada a cada quadro
                h.destaque((float(c[0]), float(c[1])), AMARELO, t, raio=0.45)
        self._bolas(h, rod, k, i, t)

    def visiveis(self, rod, maxn=12):
        chave = ("vis", maxn)
        if chave not in rod.__dict__:
            passo = max(1, int(np.ceil(rod.n / maxn)))
            rod.__dict__[chave] = sorted(set(range(0, rod.n, passo)) | {rod.lider})
        return rod.__dict__[chave]

    def _mortes(self, h, rod, k, i, t):
        v = rod.reg["vivo"][k]
        for p in range(6):
            if v[0, p] and v[i, p]:
                continue
            if v[i, p]:
                continue
            ti = int(np.argmax(~v[:, p]))
            idade = (i - ti) * rod.dt
            if 0 <= idade < 1.0:
                c = rod.reg["P"][k, ti, p]
                h.pulso((float(c[0]), float(c[1])), idade, BRANCO, 1.8, 0.8, 4)
                h.particulas((float(c[0]), float(c[1])), idade, AMARELO, n=16, alcance=1.6, dur=0.9, semente=p + 7 * k)
                if idade < 0.7:        # o queimado se apaga no lugar do acerto
                    R.avatar(h, (float(c[0]), float(c[1])), float(rod.reg["ang"][k, ti, p]), (0.7, 0.75, 0.85), t,
                             alfa=0.55 * (1 - idade / 0.7), escala=2.0, base=False)

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        i = rod.i(t)
        if modo == "replay" and foco is not None:
            self._heroi(h, rod, foco, i, t)
            self._mortes(h, rod, foco, i, t)
            return
        for k in [k for k in self.visiveis(rod) if k != rod.lider]:
            self._fantasma(h, rod, k, i, t)
        self._heroi(h, rod, rod.lider, i, t)
        self._mortes(h, rod, rod.lider, i, t)

    def ponto(self, rod, foco, nome, t):
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        if foco is not None:
            t = rod.duracao
        i = rod.i(t)
        v = rod.reg["vivo"][:, i]
        pa, pb = float(v[:, :3].sum(1).mean() / 3), float(v[:, 3:].sum(1).mean() / 3)
        return [("AZUIS EM PÉ", f"{pa:.0%}", pa, AZUL), ("VERMELHOS EM PÉ", f"{pb:.0%}", pb, VERMELHO)]

    def cerebro(self, rod, t, foco):
        k = rod.lider if foco is None else foco
        i = rod.i(t)
        if rod.lado == "a":
            genes, ativ, nome, cor = rod.genes_a[rod.ia[k]:rod.ia[k] + 1], rod.reg["ativ_a"][k, i], "AZUL", AZUL
        else:
            genes, ativ, nome, cor = rod.genes_b[rod.ib[k]:rod.ib[k] + 1], rod.reg["ativ_b"][k, i], "VERMELHO", VERMELHO
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(genes)]
        return dict(camadas=Q.CAM, pesos=pesos, ativ=ativ, saidas=("ANDAR", "LADO", "GIRAR", "LANÇAR"),
                    titulo=f"CÉREBRO // {nome}", cor=cor)

    def sons(self, rod, t0, t1, modo, foco):
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        mortes = lancs = 0
        for k in ks:
            tm = rod.jogo.t_morte[k]
            for p in range(6):
                if tm[p] >= 0 and t0 <= tm[p] * rod.dt < t1:
                    mortes += 1
            st = rod.reg["bst"][k]
            a, b = rod.i(t0), rod.i(t1)
            if b > a:
                lancs += int(((st[a:b] == Q.VOA) & (st[a - 1:b - 1] != Q.VOA)).sum()) if a > 0 else 0
        if mortes:
            ev.append((t0, "batida", min(0.4 + 0.1 * mortes, 1.0) if modo != "replay" else 1.2))
        elif lancs and modo == "replay":
            ev.append((t0, "defesa", 0.5))
        return ev

    def ambiente(self, dur):
        return None
