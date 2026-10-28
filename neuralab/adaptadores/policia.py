"""Adaptador de polícia e ladrão, vista de cima em estilo holograma (mundo = metros da arena).

Na multidão, cada partida é um par de "fantasmas" translúcidos (ladrão ciano, policial magenta): a soma de luz mostra
por onde cada lado costuma passar; quem é pego pisca vermelho e se dissolve; quem foge fica verde junto ao cofre.
"""
import math

import numpy as np

from ..coevolucao_policia import ARQ, partidas, partidas_vitrine
from ..desafios import policia as P
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .base import Adaptador, Rodada

CINZA = (0.55, 0.62, 0.8)


class RodadaPC(Rodada):
    def __init__(self, hist, g):
        self.g, self.dt = g, P.DT
        gl, gp = hist["lad"][g], hist["pol"][g]
        sem = int(hist["semente"][g])
        self.il, self.ip = partidas_vitrine(gl, gp, sem)
        self.jogo, self.reg = partidas(gl, gp, self.il, self.ip, sem, gravar=True)
        self.genes_l, self.genes_p = gl, gp
        self.n = len(self.il)
        self.T = self.reg["l"].shape[1]
        self.duracao = self.T * P.DT
        est = self.reg["estado"]
        feito = est != 0
        self.morte = np.where(feito.any(1), feito.argmax(1), -1)       # passo em que a partida acabou
        j = self.jogo
        fl, _ = j.aptidoes()
        esc = np.where(j.estado == P.ESCAPOU)[0]
        self.lider = int(esc[np.argmin(j.t_fim[esc])]) if len(esc) else int(np.argmax(fl))

    def i(self, t):
        return int(min(max(t / P.DT, 0), self.T - 1))

    def contagem(self, t):
        e = self.reg["estado"][:, self.i(t)]
        return int((e == P.ESCAPOU).sum()), int((e == P.PEGO).sum())


class Policia(Adaptador):
    titulo = "POLÍCIA E LADRÃO"
    experimento = "005"
    cores = {"ladrao": CIANO, "policia": MAGENTA, "cofre": AMARELO}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["lad"])
        self._cache = {}
        k = 7
        sv = lambda x: np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")
        self.suave = {c: sv(hist["m_" + c]) for c in ("fuga", "pego")}

    def rodada(self, g):
        if g not in self._cache:
            self._cache[g] = RodadaPC(self.hist, g)
        return self._cache[g]

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
        """Um lance da geração com o comportamento pedido. Tipos: escapa (fuga mais rápida), escapa_lento, pego
        (captura mais rápida), emboscada (pego com o policial já esperando no cofre), isca (fugiu depois de
        recuar), cima/baixo (fugiu contornando o quarteirão por esse lado), quase (pego a poucos metros do cofre)."""
        j = rod.jogo
        esc, peg = j.estado == P.ESCAPOU, j.estado == P.PEGO
        rapido = -j.t_fim.astype(float)
        crit = {
            "escapa": (esc, rapido), "escapa_lento": (esc, -rapido),
            "pego": (peg, rapido),
            "emboscada": (peg & j.cruzou & (j.pol_cofre_cruza < 4.0), rapido),
            "isca": (esc & ((np.maximum.accumulate(rod.reg["l"][:, :, 0], 1) - rod.reg["l"][:, :, 0]).max(1) > 3.0),
                     rapido),
            "cima": (esc & j.cruzou & (j.y_cruza > 9.5), rapido),
            "baixo": (esc & j.cruzou & (j.y_cruza < 4.5), rapido),
            "quase": (peg & (j.min_cofre < 5.0), -j.min_cofre),
        }
        ok, nota = crit[tipo]
        idx = [int(k) for k in np.where(ok)[0] if int(k) not in excluir]
        if not idx:
            return None
        return idx[int(np.argmax(nota[idx]))]

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(12.0, 7.0), escala=41, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        a, b = rod.reg["l"][foco, i], rod.reg["p"][foco, i]
        m = rod.morte[foco] * rod.dt
        meio = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        perto = Camera2D(centro=(float(meio[0]), float(meio[1])), escala=62, t=t)
        cam = geral.mistura(perto, min(t / 0.8, 1.0))
        if rod.jogo.estado[foco] == P.PEGO and 0 <= t - m < 0.3:
            cam.tremor = 8 * (1 - (t - m) / 0.3)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.05)
        R.poeira(h, t, alfa=0.2)
        borda = [(0, 0), (P.LARG, 0), (P.LARG, P.ALT), (0, P.ALT)]
        h.forma(borda, CIANO, 0.5, 2.0, 0.025)
        h.linha(borda, CIANO, 3.5, 0.9, fechado=True)
        for x0, y0, x1, y1 in P.PAREDES:
            h.forma([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], CINZA, 0.9, 2.2, 0.18, oclusor=True)
            h.linha([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], CINZA, 2.2, 0.8, fechado=True, halo=False)
        # o cofre
        cx, cy = P.COFRE
        pulso = 0.55 + 0.35 * math.sin(t * 4)
        h.circulo((cx, cy), P.R_COFRE, AMARELO, 0.9, 2.5, 0.07)
        h.linha([(cx + P.R_COFRE * math.cos(u), cy + P.R_COFRE * math.sin(u)) for u in np.linspace(0, 6.4, 40)],
                AMARELO, 2.0, pulso, tracejado=[10, 8], halo=False)
        h.texto("COFRE", (cx, cy + 0.15), 20, AMARELO, 0.95)
        h.ponto_luz((cx, cy), 60, AMARELO, 0.35)
        h.texto("LARGADA", (1.9, 12.9), 15, CIANO, 0.35)

    # ------------------------------------------------------------ fantasmas
    def visiveis(self, rod, maxn=70):
        chave = ("vis", maxn)
        if chave not in rod.__dict__:
            ok = np.where(rod.jogo.estado == P.ESCAPOU)[0][: maxn // 2]
            resto = np.setdiff1d(np.arange(rod.n), ok)
            passo = max(1, int(np.ceil(len(resto) / max(maxn - len(ok), 1))))
            rod.__dict__[chave] = sorted(set(ok.tolist()) | set(resto[::passo].tolist()) | {rod.lider})
        return rod.__dict__[chave]

    def aparencia(self, rod, k, i):
        """(cor_ladrao, alfa_l, alfa_rastro_l, alfa_policial) ou None se já dissolveu."""
        m = rod.morte[k]
        e = rod.reg["estado"][k, i]
        if e == 0 or m < 0 or i < m:
            return CIANO, 0.16, 0.07, 0.13
        idade = (i - m) * rod.dt
        if e == P.ESCAPOU:
            return VERDE, min(0.4 + idade * 1.5, 0.95), 0.4, max(0.13 * (1 - idade / 1.2), 0.0)
        if idade > 1.1:
            return None
        s = 1 - idade / 1.1
        return (VERMELHO if e == P.PEGO else CINZA), 0.55 * s ** 1.4 + (0.3 if idade < 0.12 else 0), 0.18 * s, 0.13 * s

    def _par(self, h, rod, k, i, t, lider, alfa_extra=1.0):
        """Desenha ladrão + policial de uma partida (nítido se for o destaque, fantasma se for da multidão)."""
        l, p = rod.reg["l"], rod.reg["p"]
        m = rod.morte[k]
        fim = i if m < 0 else min(i, m)
        pl, pp = l[k, i], p[k, i]
        est = rod.reg["estado"][k, i]
        vl = l[k, i] - l[k, max(i - 1, 0)]
        vp = p[k, i] - p[k, max(i - 1, 0)]
        if lider:
            cor_l = VERDE if est == P.ESCAPOU else (VERMELHO if est == P.PEGO else CIANO)
            for traj, cor in ((l, cor_l), (p, MAGENTA)):
                tr = traj[k, max(0, fim - 50): fim + 1: 2]
                if len(tr) > 1:
                    h.rastro([tuple(q) for q in tr], cor, 3, 0.8)
            ang_l = math.atan2(vl[1], vl[0]) if np.hypot(*vl) > 1e-4 else 0.0
            ang_p = math.atan2(pl[1] - pp[1], pl[0] - pp[0]) if np.hypot(*vp) < 1e-4 else math.atan2(vp[1], vp[0])
            run = (est == 0)
            R.avatar(h, (float(pp[0]), float(pp[1])), ang_p, MAGENTA, t, alfa=alfa_extra, passo=(t * 2.4 if run else None),
                     escala=1.5, base=False)
            R.avatar(h, (float(pl[0]), float(pl[1])), ang_l, cor_l, t, alfa=alfa_extra, passo=(t * 2.4 if run else None),
                     escala=1.5, base=False)
            if est == 0:
                h.cone((float(pp[0]), float(pp[1])), math.atan2(pl[1] - pp[1], pl[0] - pp[0]), 0.35, 4.0, MAGENTA, 0.25)
                d = math.hypot(pl[0] - pp[0], pl[1] - pp[1])
                h.linha([tuple(pl), tuple(pp)], AMARELO, 1.2, 0.35, tracejado=[6, 8], halo=False)
                h.texto(f"{d:.1f} m", ((pl[0] + pp[0]) / 2, (pl[1] + pp[1]) / 2 + 0.7), 18, AMARELO, 0.8)
            return
        ap = self.aparencia(rod, k, i)
        if ap is None:
            return
        cor, a_l, a_rastro, a_p = ap
        tr = l[k, max(0, fim - 40): fim + 1: 3]
        if len(tr) > 1:
            h.rastro([tuple(q) for q in tr], cor, 1.2, a_rastro)
        tp = p[k, max(0, fim - 40): fim + 1: 3]
        if len(tp) > 1 and a_p > 0.01:
            h.rastro([tuple(q) for q in tp], MAGENTA, 1.0, a_p * 0.4)
        if a_p > 0.01:
            h.circulo((float(pp[0]), float(pp[1])), 0.42, MAGENTA, a_p * 1.4, 1.4, 0.35)
        h.circulo((float(pl[0]), float(pl[1])), 0.36, cor, a_l, 1.6, 0.4)
        if est == P.PEGO and 0 <= (i - m) * rod.dt < 0.8:
            h.particulas((float(pl[0]), float(pl[1])), (i - m) * rod.dt, (1.0, 0.7, 0.3), n=5, alcance=1.6, dur=0.8,
                         semente=int(k))
        if est == P.ESCAPOU and 0 <= (i - m) * rod.dt < 1.2:
            h.pulso((float(pl[0]), float(pl[1])), (i - m) * rod.dt, VERDE, 2.0, 0.6, 3)

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        i = rod.i(t)
        if modo == "replay" and foco is not None:
            self._par(h, rod, foco, i, t, True)
            est, m = rod.reg["estado"][foco, i], rod.morte[foco]
            idade = (i - m) * rod.dt if m >= 0 else 0
            pl = rod.reg["l"][foco, i]
            if est == P.PEGO:
                h.pulso((float(pl[0]), float(pl[1])), idade, VERMELHO, 3.0, 0.7, 5)
                h.ponto_luz((float(pl[0]), float(pl[1])), 70 * max(1 - idade, 0), (1.0, 0.6, 0.2), 0.8 * max(1 - idade, 0))
                h.texto("PEGO!", (float(pl[0]), float(pl[1]) + 1.8), 26, VERMELHO, min(idade * 3, 1))
            elif est == P.ESCAPOU:
                h.pulso((float(pl[0]), float(pl[1])), idade, VERDE, 3.5, 0.9, 5)
                h.texto("✓ ESCAPOU", (float(pl[0]), float(pl[1]) + 1.8), 26, VERDE, min(idade * 3, 1))
            return
        ks = [k for k in self.visiveis(rod) if k != rod.lider]
        for k in ks:
            self._par(h, rod, k, i, t, False)
        self._par(h, rod, rod.lider, i, t, True, 1.0)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        if nome == "ladrao":
            return tuple(float(v) for v in rod.reg["l"][foco, i])
        if nome == "policia":
            return tuple(float(v) for v in rod.reg["p"][foco, i])
        if nome in ("alvo", "cofre"):
            return P.COFRE
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        if foco is not None:
            t = rod.duracao
        e, p = rod.contagem(t)
        return [("LADRÕES", f"{e}/{rod.n}", e / rod.n, VERDE), ("PRESOS", f"{p}/{rod.n}", p / rod.n, VERMELHO)]

    def cerebro(self, rod, t, foco):
        k = rod.lider if foco is None else foco
        i = rod.i(t)
        genes = rod.genes_l[rod.il[k]:rod.il[k] + 1]
        pesos = [(W[0], b[0]) for W, b in ARQ.desempacota(genes)]
        return dict(camadas=P.CAMADAS, pesos=pesos, ativ=rod.reg["ativ_l"][k, i], saidas=("→ X", "↑ Y"),
                    titulo="CÉREBRO // LADRÃO", cor=CIANO)

    def sons(self, rod, t0, t1, modo, foco):
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        pegos = fugas = 0
        for k in ks:
            m = rod.morte[k]
            if m >= 0 and t0 <= m * rod.dt < t1:
                if rod.reg["estado"][k, m] == P.ESCAPOU:
                    fugas += 1
                elif rod.reg["estado"][k, m] == P.PEGO:
                    pegos += 1
        if pegos:
            ev.append((t0, "batida", min(0.4 + 0.1 * pegos, 1.0) if modo != "replay" else 1.2))
        if fugas:
            ev.append((t0, "ding", 2 if modo == "replay" else 1))
        return ev

    def ambiente(self, dur):
        return None
