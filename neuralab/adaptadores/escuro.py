"""Adaptador do Esconde-Esconde no Escuro, vista de cima em estilo holograma (mundo = metros da arena).

Caçadores magenta com lanterna (cone amarelo), fugitivos ciano que só ficam nítidos quando a luz os pega. O destaque
("o campeão") é a melhor equipe do lado escolhido (`lado`: "fug" ou "cac"); a câmera do replay o segue (sem anel/rótulo).
"""
import math

import numpy as np

from ..coevolucao_escuro import ARQ_C, ARQ_F, partidas, partidas_vitrine
from ..desafios import escuro as E
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .base import Adaptador, Rodada


def campeao_da_geracao(hist, g, lado):
    """Índice da melhor equipe do lado ("fug"/"cac") na geração g: maior nota média em 4 partidas cada."""
    gc, gf = hist["cac"][g], hist["fug"][g]
    sem = int(hist["semente"][g])
    pop = len(gc)
    rng = np.random.default_rng(sem + 11)
    il = np.repeat(np.arange(pop), 4)
    outro = rng.integers(0, pop, len(il))
    if lado == "fug":
        jogo, _ = partidas(gc, gf, outro, il, sem + 12)
        nota = jogo.aptidoes()[1]
    else:
        jogo, _ = partidas(gc, gf, il, outro, sem + 12)
        nota = jogo.aptidoes()[0]
    tot = np.zeros(pop)
    np.add.at(tot, il, nota)
    return int(np.argmax(tot))


class RodadaE(Rodada):
    def __init__(self, hist, g, lado, campeao=False):
        self.g, self.dt, self.lado = g, E.DT, lado
        gc, gf = hist["cac"][g], hist["fug"][g]
        sem = int(hist["semente"][g])
        self.ic, self.iff = partidas_vitrine(len(gc), sem)
        if campeao:         # a MESMA equipe campeã contra 100 times diferentes do outro lado
            self.campeao = campeao_da_geracao(hist, g, lado)
            if lado == "fug":
                self.iff = np.full(len(gc), self.campeao)
            else:
                self.ic = np.full(len(gc), self.campeao)
        self.jogo, self.reg = partidas(gc, gf, self.ic, self.iff, sem, gravar=True)
        self.genes_c, self.genes_f = gc, gf
        self.n = len(self.ic)
        self.T = self.reg["estado"].shape[1]
        self.duracao = self.T * E.DT
        pego = self.reg["estado"] != 0                                   # (n, T, NF)
        qualquer = pego.any(2)
        self.morte = np.where(qualquer.any(1), qualquer.argmax(1), -1)    # 1ª captura da partida
        fc, ff = self.jogo.aptidoes()
        self.lider = int(np.argmax(ff if lado == "fug" else fc))

    def i(self, t):
        return int(min(max(t / E.DT, 0), self.T - 1))

    def contagem(self, t):
        e = self.reg["estado"][:, self.i(t)]
        return int((e == E.PEGO).sum()), int(e.size)


class Escuro(Adaptador):
    titulo = "ESCONDE-ESCONDE NO ESCURO"
    experimento = "016"
    cores = {"cacador": MAGENTA, "fugitivo": CIANO, "luz": AMARELO}

    def __init__(self, hist, lado="fug"):
        self.hist = hist
        self.lado = lado
        self.total_ger = len(hist["cac"])
        self._cache = {}

    def rodada(self, g, campeao=False):
        """ger >= total_ger pede a rodada do CAMPEÃO da geração g - total_ger: a mesma equipe jogando 100 vezes."""
        if g >= self.total_ger:
            g, campeao = g - self.total_ger, True
        if (g, campeao) not in self._cache:
            self._cache[(g, campeao)] = RodadaE(self.hist, g, self.lado, campeao)
        return self._cache[(g, campeao)]

    # ------------------------------------------------------------ lances
    JANELA = 6.0           # segundos de simulação mostrados num replay

    def _janela(self, rod, foco):
        m = rod.morte[foco]
        fim = ((m + 1) * rod.dt + 0.8) if m >= 0 else min(rod.duracao, self.JANELA)
        return max(0.0, fim - self.JANELA), fim

    def duracao_foco(self, rod, foco):
        return self._janela(rod, foco)[1]

    def janela_lance(self, rod, foco):
        return self._janela(rod, foco)

    def chaves_lento(self, rod, foco):
        m = rod.morte[foco]
        return [m * rod.dt] if m >= 0 else []

    def busca(self, rod, tipo, excluir=()):
        """Um lance da geração. 'campeao' = a melhor partida do lado; 'pego' = primeira captura mais cedo;
        'pego_tarde' = captura mais tarde; 'livre' = ninguém pego; 'todos' = os três pegos;
        'costas' = fugitivo mais tempo nas costas do caçador; 'giro' = caçador girando mais sem ver ninguém."""
        j = rod.jogo
        pegos = (j.estado == E.PEGO).sum(1)
        fc, ff = j.aptidoes()
        m = rod.morte.astype(float)
        crit = {"campeao": (np.ones(rod.n, bool), ff if rod.lado == "fug" else fc),
                "pego": (m >= 0, -m), "pego_tarde": (m >= 0, m), "livre": (pegos == 0, ff),
                "todos": (pegos == E.NF, -m),
                "costas": (np.ones(rod.n, bool), j.costas / np.maximum(j.perto3, 1) + 0.01 * j.perto3),
                "giro": (np.ones(rod.n, bool), j.giro_cego / np.maximum(j.cego_c, 1))}
        ok, nota = crit[tipo]
        idx = [int(k) for k in np.where(ok)[0] if int(k) not in excluir]
        return idx[int(np.argmax(nota[idx]))] if idx else None

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(12.0, 7.0), escala=41, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        c = rod.reg["f"][foco, i].mean(0) if rod.lado == "fug" else rod.reg["c"][foco, i].mean(0)
        perto = Camera2D(centro=(float(np.clip(c[0], 7.0, 17.0)), float(np.clip(c[1], 4.5, 9.5))), escala=52, t=t)
        cam = geral.mistura(perto, min((t - self._janela(rod, foco)[0]) / 0.8, 1.0))
        m = rod.morte[foco] * rod.dt
        if rod.morte[foco] >= 0 and 0 <= t - m < 0.3:
            cam.tremor = 8 * (1 - (t - m) / 0.3)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.01, 0.015, 0.035))
        h.grade(1.0, alfa=0.035)
        R.poeira(h, t, alfa=0.12)
        borda = [(0, 0), (E.LARG, 0), (E.LARG, E.ALT), (0, E.ALT)]
        h.forma(borda, CIANO, 0.35, 2.0, 0.012)
        h.linha(borda, CIANO, 3.0, 0.65, fechado=True)

    # ------------------------------------------------------------ desenho de uma partida
    def _feixes(self, h, rod, k, i, alfa):
        for c in range(E.NC):
            p, a = rod.reg["c"][k, i, c], float(rod.reg["ang"][k, i, c])
            h.cone((float(p[0]), float(p[1])), a, 2 * E.MEIO, E.ALCANCE, AMARELO, alfa)

    def _fantasma(self, h, rod, k, i):
        est = rod.reg["estado"][k, i]
        luz = rod.reg["luz"][k, i]
        self._feixes(h, rod, k, i, 0.035)
        for c in range(E.NC):
            p = rod.reg["c"][k, i, c]
            h.circulo((float(p[0]), float(p[1])), 0.38, MAGENTA, 0.22, 1.6, 0.4)
        for f in range(E.NF):
            if est[f] == E.PEGO:
                continue
            p = rod.reg["f"][k, i, f]
            h.circulo((float(p[0]), float(p[1])), 0.36, BRANCO if luz[f] else CIANO, 0.45 if luz[f] else 0.08, 1.6, 0.4)

    def _heroi(self, h, rod, k, i, t):
        """Partida em destaque: caçadores com feixe, fugitivos só nítidos quando iluminados."""
        est = rod.reg["estado"][k, i]
        luz = rod.reg["luz"][k, i]
        self._feixes(h, rod, k, i, 0.42)
        ip = max(i - 1, 0)
        for c in range(E.NC):
            p = rod.reg["c"][k, i, c]
            R.avatar(h, (float(p[0]), float(p[1])), float(rod.reg["ang"][k, i, c]), MAGENTA, t, alfa=1.0,
                     passo=t * 2.4, escala=1.5, base=False)
        for f in range(E.NF):
            p = rod.reg["f"][k, i, f]
            q = rod.reg["f"][k, ip, f]
            vel = p - q
            ang = math.atan2(vel[1], vel[0]) if np.hypot(*vel) > 1e-4 else 0.0
            if est[f] == E.PEGO:
                continue
            acesa = bool(luz[f])
            R.avatar(h, (float(p[0]), float(p[1])), ang, BRANCO if acesa else CIANO, t,
                     alfa=1.0 if acesa else 0.32, passo=t * 2.4 if np.hypot(*vel) > 1e-4 else None, escala=1.5, base=False)

    def visiveis(self, rod, maxn=14):
        chave = ("vis", maxn)
        if chave not in rod.__dict__:
            passo = max(1, int(np.ceil(rod.n / maxn)))
            rod.__dict__[chave] = sorted(set(range(0, rod.n, passo)) | {rod.lider})
        return rod.__dict__[chave]

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        i = rod.i(t)
        if modo == "replay" and foco is not None:
            self._heroi(h, rod, foco, i, t)
            est = rod.reg["estado"][foco, i]
            m = rod.morte[foco]
            for f in range(E.NF):
                if est[f] == E.PEGO:
                    p = rod.reg["f"][foco, i, f]
                    idade = (i - int(np.argmax(rod.reg["estado"][foco, :, f] != 0))) * rod.dt
                    h.pulso((float(p[0]), float(p[1])), idade, VERMELHO, 2.4, 0.7, 4)
                    if idade < 1.2:
                        h.texto("PEGO!", (float(p[0]), float(p[1]) + 1.5), 24, VERMELHO, min(idade * 4, 1))
            return
        for k in [k for k in self.visiveis(rod) if k != rod.lider]:
            self._fantasma(h, rod, k, i)
        self._heroi(h, rod, rod.lider, i, t)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        if nome == "fugitivo":
            est = rod.reg["estado"][foco, i]
            f = rod.reg["f"][foco, i]
            viv = np.where(est == E.VIVO)[0]
            return tuple(float(x) for x in f[viv[0] if len(viv) else 0])
        if nome == "cacador":
            c = rod.reg["c"][foco, i]
            f = rod.reg["f"][foco, i].mean(0)
            return tuple(float(x) for x in c[int(np.hypot(*(c - f).T).argmin())])
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        if foco is not None:
            t = rod.duracao
        p, n = rod.contagem(t)
        n_f = n * E.NF
        pegos = int((rod.reg["estado"][:, rod.i(t)] == E.PEGO).sum())
        iluminado = float(rod.reg["luz"][:, rod.i(t)].mean())
        if foco is not None and hasattr(rod, "campeao"):     # replay do campeão: mostra a geração (os números da voz)
            pegos = int(round(n_f * float(self.hist["m_pegos"][rod.g])))
        return [("FUGITIVOS PEGOS", f"{pegos}/{n_f}", pegos / n_f, VERMELHO),
                ("ILUMINADOS AGORA", f"{iluminado:.0%}", iluminado, AMARELO)]

    def cerebro(self, rod, t, foco):
        k = rod.lider if foco is None else foco
        i = rod.i(t)
        if rod.lado == "fug":
            genes, arq, ativ, nome, cor = rod.genes_f[rod.iff[k]:rod.iff[k] + 1], ARQ_F, rod.reg["ativ_f"][k, i], "FUGITIVO", CIANO
            camadas, saidas = E.CAM_F, ("→ X", "↑ Y")
        else:
            genes, arq, ativ, nome, cor = rod.genes_c[rod.ic[k]:rod.ic[k] + 1], ARQ_C, rod.reg["ativ_c"][k, i], "CAÇADOR", MAGENTA
            camadas, saidas = E.CAM_C, ("ANDAR", "GIRAR")
        pesos = [(W[0], b[0]) for W, b in arq.desempacota(genes)]
        return dict(camadas=camadas, pesos=pesos, ativ=ativ, saidas=saidas, titulo=f"CÉREBRO // {nome}", cor=cor)

    def sons(self, rod, t0, t1, modo, foco):
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        pegos = 0
        for k in ks:
            for f in range(E.NF):
                tp = rod.jogo.t_pego[k, f]
                if tp >= 0 and t0 <= tp * rod.dt < t1:
                    pegos += 1
        if pegos:
            ev.append((t0, "batida", min(0.4 + 0.1 * pegos, 1.0) if modo != "replay" else 1.2))
        return ev

    def ambiente(self, dur):
        return None
