"""Adaptador da Escolta VIP, vista de cima em estilo holograma (mundo = metros da arena).

Seguranças ciano, assassinos magenta, VIP dourado andando para a saída (verde). Na multidão cada partida é um
trio de fantasmas translúcidos; o destaque (o "campeão", a melhor equipe de seguranças da geração) aparece nítido.
"""
import math

import numpy as np

from ..coevolucao_escolta import ARQ, partidas, partidas_vitrine
from ..desafios import escolta as E
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .base import Adaptador, Rodada

CINZA = (0.55, 0.62, 0.8)


def seg_no_caminho(vip, ass, segs):
    """Algum segurança a menos de 1,1 m do segmento VIP -> assassino? (um instante)."""
    d = ass - vip
    L2 = max(float(d @ d), 1e-6)
    tt = np.clip(((segs - vip) @ d) / L2, 0, 1)
    proj = vip + tt[:, None] * d
    return bool((np.hypot(*(segs - proj).T) < 1.1).any())


def campeao_da_geracao(gs, ga, sem):
    """Índice da melhor equipe de seguranças da geração: a de maior nota média em 4 partidas cada."""
    pop = len(gs)
    rng = np.random.default_rng(sem + 11)
    il = np.repeat(np.arange(pop), 4)
    jogo, _ = partidas(gs, ga, il, rng.integers(0, pop, len(il)), sem + 12)
    nota = np.zeros(pop)
    np.add.at(nota, il, jogo.aptidoes()[0])
    return int(np.argmax(nota))


class RodadaE(Rodada):
    def __init__(self, hist, g, campeao=False):
        self.g, self.dt = g, E.DT
        gs, ga = hist["seg"][g], hist["ass"][g]
        sem = int(hist["semente"][g])
        self.il, self.ip = partidas_vitrine(len(gs), sem)
        if campeao:         # a MESMA equipe campeã contra 100 times de assassinos diferentes
            self.campeao = campeao_da_geracao(gs, ga, sem)
            self.il = np.full(len(gs), self.campeao)
        self.jogo, self.reg = partidas(gs, ga, self.il, self.ip, sem, gravar=True)
        self.genes_s = gs
        self.n = len(self.il)
        self.T = self.reg["vip"].shape[1]
        self.duracao = self.T * E.DT
        feito = self.reg["estado"] != 0
        self.morte = np.where(feito.any(1), feito.argmax(1), -1)
        fg, _ = self.jogo.aptidoes()
        self.lider = int(np.argmax(fg))

    def i(self, t):
        return int(min(max(t / E.DT, 0), self.T - 1))

    def contagem(self, t):
        e = self.reg["estado"][:, self.i(t)]
        return int((e == E.CHEGOU).sum()), int((e == E.MORTO).sum())


class Escolta(Adaptador):
    titulo = "ESCOLTA VIP"
    experimento = "014"
    cores = {"seguranca": CIANO, "assassino": MAGENTA, "vip": AMARELO}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["seg"])
        self._cache = {}

    def rodada(self, g, campeao=False):
        """ger >= total_ger pede a rodada do CAMPEÃO da geração g - total_ger: a mesma equipe jogando 100 vezes
        (usada nos replays, para o herói ser sempre ela). Abaixo disso, a vitrine normal."""
        if g >= self.total_ger:
            g, campeao = g - self.total_ger, True
        if (g, campeao) not in self._cache:
            self._cache[(g, campeao)] = RodadaE(self.hist, g, campeao)
        return self._cache[(g, campeao)]

    # ------------------------------------------------------------ lances
    def duracao_foco(self, rod, foco):
        m = rod.morte[foco]
        return (m + 1) * rod.dt + 1.0 if m >= 0 else rod.duracao

    def janela_lance(self, rod, foco):
        m = rod.morte[foco]
        return 0.0, ((m + 1) * rod.dt + 0.5) if m >= 0 else rod.duracao

    def chaves_lento(self, rod, foco):
        m = rod.morte[foco]
        return [m * rod.dt] if m >= 0 else []

    def busca(self, rod, tipo, excluir=()):
        """Um lance da geração. 'campeao' = a melhor equipe de seguranças; 'salvo' = VIP chegou à saída;
        'morto' = VIP morto mais rápido; 'morto_tarde' = VIP morto mais tarde; 'escudo' = VIP morto com seguranças
        coladas nele (mais perto de salvá-lo)."""
        j = rod.jogo
        sal, mor = j.estado == E.CHEGOU, j.estado == E.MORTO
        t = j.t_fim.astype(float)
        fg, _ = j.aptidoes()
        crit = {"campeao": (np.ones(rod.n, bool), fg), "salvo": (sal, fg), "morto": (mor, -t),
                "morto_tarde": (mor, t), "escudo": (mor, j.escudo / np.maximum(j.perto, 1))}
        ok, nota = crit[tipo]
        idx = [int(k) for k in np.where(ok)[0] if int(k) not in excluir]
        return idx[int(np.argmax(nota[idx]))] if idx else None

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(12.0, 7.0), escala=41, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        v = rod.reg["vip"][foco, i]
        m = rod.morte[foco] * rod.dt
        perto = Camera2D(centro=(float(np.clip(v[0] + 2.0, 7.0, 15.0)), float(np.clip(v[1], 5.0, 9.0))), escala=52, t=t)
        cam = geral.mistura(perto, min(t / 0.8, 1.0))
        if rod.jogo.estado[foco] == E.MORTO and 0 <= t - m < 0.3:
            cam.tremor = 8 * (1 - (t - m) / 0.3)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.05)
        R.poeira(h, t, alfa=0.2)
        borda = [(0, 0), (E.LARG, 0), (E.LARG, E.ALT), (0, E.ALT)]
        h.forma(borda, CIANO, 0.5, 2.0, 0.025)
        h.linha(borda, CIANO, 3.5, 0.9, fechado=True)
        # tapete do VIP e saída
        h.linha([(E.VIP0[0], E.VIP0[1]), (E.SAIDA, E.VIP0[1])], AMARELO, 1.6, 0.25, tracejado=[10, 10], halo=False)
        pulso = 0.55 + 0.35 * math.sin(t * 4)
        h.forma([(E.SAIDA, 5.2), (E.LARG, 5.2), (E.LARG, 8.8), (E.SAIDA, 8.8)], VERDE, 0.8, 2.0, 0.08)
        h.linha([(E.SAIDA, 5.2), (E.LARG - 0.05, 5.2), (E.LARG - 0.05, 8.8), (E.SAIDA, 8.8)], VERDE, 2.4, pulso,
                fechado=True, halo=False)
        h.texto("SAÍDA", (E.SAIDA + 0.95, 7.0), 18, VERDE, 0.95)
        h.texto("PORTA", (1.6, 12.9), 15, AMARELO, 0.35)

    # ------------------------------------------------------------ fantasmas
    def visiveis(self, rod, maxn=48):
        chave = ("vis", maxn)
        if chave not in rod.__dict__:
            sal = np.where(rod.jogo.estado == E.CHEGOU)[0][: maxn // 3]
            resto = np.setdiff1d(np.arange(rod.n), sal)
            passo = max(1, int(np.ceil(len(resto) / max(maxn - len(sal), 1))))
            rod.__dict__[chave] = sorted(set(sal.tolist()) | set(resto[::passo].tolist()) | {rod.lider})
        return rod.__dict__[chave]

    def _fantasma(self, h, rod, k, i):
        m, e = rod.morte[k], rod.reg["estado"][k, i]
        idade = (i - m) * rod.dt if (m >= 0 and i >= m) else -1.0
        if e == E.MORTO and idade > 1.1:
            return
        s = 1.0 if idade < 0 else max(1 - idade / 1.1, 0.0)
        v = rod.reg["vip"][k, i]
        cor_v = VERDE if e == E.CHEGOU else (VERMELHO if e == E.MORTO else AMARELO)
        a = 0.2 * s if e != E.CHEGOU else 0.3
        for p in rod.reg["g"][k, i]:
            h.circulo((float(p[0]), float(p[1])), 0.4, CIANO, a, 1.6, 0.4)
        for p in rod.reg["a"][k, i]:
            h.circulo((float(p[0]), float(p[1])), 0.38, MAGENTA, a, 1.6, 0.4)
        tr = rod.reg["vip"][k, max(0, i - 30): i + 1: 3]
        if len(tr) > 1:
            h.rastro([tuple(q) for q in tr], cor_v, 1.2, 0.2 * s)
        h.circulo((float(v[0]), float(v[1])), 0.42, cor_v, 0.65 * s + (0.3 if 0 <= idade < 0.12 else 0), 2.0, 0.5)
        if e == E.MORTO and 0 <= idade < 0.8:
            h.particulas((float(v[0]), float(v[1])), idade, (1.0, 0.7, 0.3), n=5, alcance=1.6, dur=0.8, semente=int(k))
        if e == E.CHEGOU and 0 <= idade < 1.2:
            h.pulso((float(v[0]), float(v[1])), idade, VERDE, 2.0, 0.6, 3)

    # ------------------------------------------------------------ destaque
    def _heroi(self, h, rod, k, i, t):
        g, a = rod.reg["g"][k, i], rod.reg["a"][k, i]
        v = rod.reg["vip"][k, i]
        e = rod.reg["estado"][k, i]
        m = rod.morte[k]
        fim = i if m < 0 else min(i, m)
        for traj, cor in ((rod.reg["vip"][k], AMARELO),):
            tr = traj[max(0, fim - 50): fim + 1: 2]
            if len(tr) > 1:
                h.rastro([tuple(q) for q in tr], cor, 3, 0.8)
        vivo = e == E.VIVO
        for q, cor in ((g, CIANO), (a, MAGENTA)):
            for c in range(q.shape[1] if q.ndim == 3 else q.shape[0]):
                pass
        ang_g = [math.atan2(v[1] - p[1], v[0] - p[0]) for p in g]
        prev = rod.reg["g"][k, max(i - 1, 0)]
        for c in range(E.NS):
            vel = g[c] - prev[c]
            ang = math.atan2(vel[1], vel[0]) if np.hypot(*vel) > 1e-4 else ang_g[c]
            R.avatar(h, (float(g[c][0]), float(g[c][1])), ang, CIANO, t, alfa=1.0, passo=(t * 2.4 if vivo else None),
                     escala=1.5, base=False)
        preva = rod.reg["a"][k, max(i - 1, 0)]
        for c in range(E.NS):
            vel = a[c] - preva[c]
            ang = math.atan2(vel[1], vel[0]) if np.hypot(*vel) > 1e-4 else math.pi
            R.avatar(h, (float(a[c][0]), float(a[c][1])), ang, MAGENTA, t, alfa=1.0, passo=(t * 2.4 if vivo else None),
                     escala=1.5, base=False)
        cor_v = VERDE if e == E.CHEGOU else (VERMELHO if e == E.MORTO else AMARELO)
        h.circulo((float(v[0]), float(v[1])), 0.55, cor_v, 0.95, 3.0, 0.7)
        h.ponto_luz((float(v[0]), float(v[1])), 36, cor_v, 0.5)
        if vivo:
            h.texto("VIP", (float(v[0]), float(v[1]) + 1.15), 22, AMARELO, 1.0)
            d = np.hypot(*(a - v).T)
            ia = int(d.argmin())
            escudo = seg_no_caminho(v, a[ia], g)
            if d[ia] < 6.0:
                h.linha([tuple(v), tuple(a[ia])], VERDE if escudo else VERMELHO, 1.4, 0.55, tracejado=[6, 8], halo=False)
            if escudo and d[ia] < 4.0:
                h.texto("ESCUDO", (float(v[0]), float(v[1]) - 1.3), 22, VERDE, 0.95)
        self._legenda_campeao(h, g, t, vivo)

    @staticmethod
    def _legenda_campeao(h, g, t, vivo):
        """Anel pulsante em volta da equipe campeã + rótulo grande (o espectador sempre sabe quem acompanhar)."""
        c = g.mean(0)
        r = 1.9 + 0.25 * math.sin(t * 5)
        h.circulo((float(c[0]), float(c[1])), r, CIANO, 0.8, 2.6, 0.12)
        h.texto("CAMPEÃO", (float(c[0]), float(c[1]) + r + 0.9), 32, CIANO, 1.0)

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        i = rod.i(t)
        if modo == "replay" and foco is not None:
            self._heroi(h, rod, foco, i, t)
            e, m = rod.reg["estado"][foco, i], rod.morte[foco]
            idade = (i - m) * rod.dt if m >= 0 else 0
            v = rod.reg["vip"][foco, i]
            if e == E.MORTO:
                h.pulso((float(v[0]), float(v[1])), idade, VERMELHO, 3.0, 0.7, 5)
                h.ponto_luz((float(v[0]), float(v[1])), 70 * max(1 - idade, 0), (1.0, 0.6, 0.2), 0.8 * max(1 - idade, 0))
                h.texto("VIP CAIU!", (float(v[0]), float(v[1]) + 1.8), 26, VERMELHO, min(idade * 3, 1))
            elif e == E.CHEGOU:
                h.pulso((float(v[0]), float(v[1])), idade, VERDE, 3.5, 0.9, 5)
                h.texto("✓ VIP SALVO", (float(v[0]) - 1.5, float(v[1]) + 1.8), 26, VERDE, min(idade * 3, 1))
            return
        for k in [k for k in self.visiveis(rod) if k != rod.lider]:
            self._fantasma(h, rod, k, i)
        self._heroi(h, rod, rod.lider, i, t)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        if nome == "vip":
            return tuple(float(v) for v in rod.reg["vip"][foco, i])
        if nome == "seguranca":
            g = rod.reg["g"][foco, i]
            return tuple(float(v) for v in g[int(np.argmax(g[:, 0]))])
        if nome == "assassino":
            v = rod.reg["vip"][foco, i]
            a = rod.reg["a"][foco, i]
            return tuple(float(x) for x in a[int(np.hypot(*(a - v).T).argmin())])
        if nome in ("saida", "alvo"):
            return (E.SAIDA + 1.0, 7.0)
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        if foco is not None:
            t = rod.duracao
        s, m = rod.contagem(t)
        if foco is not None and hasattr(rod, "campeao"):     # replay do campeão: mostra a geração (os números da voz)
            s = int(round(rod.n * float(self.hist["m_vip_vivo"][rod.g])))
            m = rod.n - s
        return [("VIPs SALVOS", f"{s}/{rod.n}", s / rod.n, VERDE), ("VIPs MORTOS", f"{m}/{rod.n}", m / rod.n, VERMELHO)]

    def cerebro(self, rod, t, foco):
        k = rod.lider if foco is None else foco
        i = rod.i(t)
        genes = rod.genes_s[rod.il[k]:rod.il[k] + 1]
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(genes)]
        return dict(camadas=E.CAMADAS, pesos=pesos, ativ=rod.reg["ativ_g"][k, i], saidas=("→ X", "↑ Y"),
                    titulo="CÉREBRO // SEGURANÇA", cor=CIANO)

    def sons(self, rod, t0, t1, modo, foco):
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        mortos = salvos = 0
        for k in ks:
            m = rod.morte[k]
            if m >= 0 and t0 <= m * rod.dt < t1:
                if rod.reg["estado"][k, m] == E.CHEGOU:
                    salvos += 1
                elif rod.reg["estado"][k, m] == E.MORTO:
                    mortos += 1
        if mortos:
            ev.append((t0, "batida", min(0.4 + 0.1 * mortos, 1.0) if modo != "replay" else 1.2))
        if salvos:
            ev.append((t0, "ding", 2 if modo == "replay" else 1))
        return ev

    def ambiente(self, dur):
        return None
