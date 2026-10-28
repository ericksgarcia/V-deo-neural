"""Adaptador de polícia e ladrão no labirinto, vista de cima em estilo holograma.

Mundo: metros do mapa (1 bloco = 1 m), x = coluna, y = linha contada de baixo.
"""
import math

import numpy as np

from ..desafios.policia import COL, DT, ESCAPOU, LIN, PAREDE, PASSOS, PILARES, PRESO
from ..perseguicao import ARQ_LAD, partidas
from ..palco import arte as R
from ..palco.holo import AMARELO, AZUL, BRANCO, CIANO, VERDE, VERMELHO, Camera2D
from .base import Adaptador, Rodada

LADRAO, POLICIA = AMARELO, AZUL
PAREDE_COR = (0.42, 0.3, 1.0)     # roxo-neon: não se confunde com o azul da polícia


def _bordas():
    """Contorno das paredes: só as arestas entre parede e corredor, emendadas em segmentos longos."""
    seg = []
    for y in range(LIN):
        for viz, yy in ((y - 1, y), (y + 1, y + 1)):     # aresta de baixo e de cima de cada bloco
            x = 0
            while x < COL:
                if PAREDE[y, x] and 0 <= viz < LIN and not PAREDE[viz, x]:
                    x0 = x
                    while x < COL and PAREDE[y, x] and not PAREDE[viz, x]:
                        x += 1
                    seg.append(((x0, yy), (x, yy)))
                else:
                    x += 1
    for x in range(COL):
        for viz, xx in ((x - 1, x), (x + 1, x + 1)):
            y = 0
            while y < LIN:
                if PAREDE[y, x] and 0 <= viz < COL and not PAREDE[y, viz]:
                    y0 = y
                    while y < LIN and PAREDE[y, x] and not PAREDE[y, viz]:
                        y += 1
                    seg.append(((xx, y0), (xx, y)))
                else:
                    y += 1
    return seg


BORDAS = _bordas()
BLOCOS = [[(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)] for y in range(LIN) for x in range(COL) if PAREDE[y, x]]


class RodadaPolicia(Rodada):
    def __init__(self, hist, g, jogos=4):
        self.g, self.dt = g, DT
        gl, gp = hist["lad"][g], hist["pol"][g]
        pop = len(gl)
        sem = int(hist["semente"][g])
        il = np.repeat(np.arange(pop), jogos)
        ip = np.random.default_rng(sem).permutation(np.tile(np.arange(pop), jogos))
        self.jogo, self.reg = partidas(gl, gp, il, ip, sem, gravar=True)
        self.il, self.ip, self.genes_l = il, ip, gl
        self.T = self.reg["pl"].shape[1]
        self.duracao = (self.T - 1) * DT
        j = self.jogo
        self.fim = (j.t_fim + 1) * DT
        self.vitrine = np.arange(0, len(il), jogos)      # uma perseguição por ladrão = 100 ao mesmo tempo
        # líder ao vivo: a perseguição mais longa da vitrine que termina em prisão (mostra os dois lados)
        v = self.vitrine
        presos = v[j.estado[v] == PRESO]
        self.lider = int(presos[np.argmax(self.fim[presos])]) if len(presos) else int(v[0])

    def f(self, t):
        return min(max(t / DT, 0.0), self.T - 1.0)

    def i(self, t):
        return int(round(self.f(t)))

    def pos(self, chave, k, t):
        """Posição interpolada (suave na câmera lenta)."""
        f = self.f(t)
        a = int(f)
        b = min(a + 1, self.T - 1)
        u = f - a
        P = self.reg[chave][k]
        return P[a] * (1 - u) + P[b] * u

    def rumo(self, chave, k, t):
        a = self.pos(chave, k, max(t - 0.25, 0))
        b = self.pos(chave, k, t + 0.05)
        d = b - a
        if d.ndim == 1:
            return math.atan2(d[1], d[0]) if np.hypot(*d) > 1e-3 else None
        return [math.atan2(e[1], e[0]) if np.hypot(*e) > 1e-3 else None for e in d]


class Policia(Adaptador):
    titulo = "POLÍCIA × LADRÃO"
    experimento = "005"
    cores = {"lad": LADRAO, "pol": POLICIA, "verde": VERDE, "vermelho": VERMELHO}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["lad"])
        self._cache = {}
        k = 7   # mesmas médias móveis do roteiro: o HUD mostra exatamente os números falados
        sv = lambda x: np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")
        self.suave = {c: sv(hist["m_" + c]) for c in ("preso", "oculto", "laco", "cerco")}

    def rodada(self, g):
        if g not in self._cache:
            if len(self._cache) > 6:
                self._cache.pop(next(iter(self._cache)))
            self._cache[g] = RodadaPolicia(self.hist, g)
        return self._cache[g]

    # ------------------------------------------------------------ lances
    def duracao_foco(self, rod, foco):
        return min(float(rod.fim[foco]) + 1.0, rod.duracao)

    def janela_lance(self, rod, foco):
        f = float(rod.fim[foco])
        return max(f - 3.0, 0.0), min(f + 0.5, rod.duracao)

    def chaves_lento(self, rod, foco):
        if rod.jogo.estado[foco] == PRESO:
            return [float(rod.fim[foco]) - 0.15]
        return []

    def busca(self, rod, tipo, minimo=None):
        """Acha na geração um lance que mostre o comportamento pedido (para o replay)."""
        j = rod.jogo
        preso, escapou = j.estado == PRESO, j.estado == ESCAPOU
        voltas = np.abs(j.ang).max(1) / (2 * np.pi)
        oculto = j.oculto / np.maximum(j.vivo, 1)
        criterios = {
            "laco": (escapou & (voltas >= 1.0), voltas),
            "cerco": (j.cerco, -rod.fim),
            "esconde": (escapou & (oculto > 0.5), oculto),
            "rico": (escapou & (j.diamantes >= 2), j.diamantes * 100 + oculto),
            "preso": (preso, -rod.fim),
            "preso_longo": (preso, rod.fim),
            "escapou": (escapou, oculto),
        }
        ok, nota = criterios[tipo]
        idx = np.where(ok)[0]
        if not len(idx):
            return None
        return int(idx[np.argmax(nota[idx])])

    def pilar_do_laco(self, rod, foco):
        return int(np.argmax(np.abs(rod.jogo.ang[foco])))

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(COL / 2, LIN / 2 - 0.15), escala=58.5, t=t)
        if modo != "replay" or foco is None:
            return geral
        # replay: aproxima de leve do ladrão (o mapa inteiro continua quase todo visível)
        p = rod.pos("pl", foco, t)
        cx = float(np.clip(p[0], COL / 2 - 1.6, COL / 2 + 1.6))
        cy = float(np.clip(p[1], LIN / 2 - 1.2, LIN / 2 + 1.0))
        perto = Camera2D(centro=(cx, cy), escala=66, t=t)
        cam = geral.mistura(perto, min(t / 0.8, 1.0) * 0.9)
        f = float(rod.fim[foco])
        if rod.jogo.estado[foco] == PRESO and 0 <= t - f < 0.35:
            cam.tremor = 8 * (1 - (t - f) / 0.35)
        return cam

    # ------------------------------------------------------------ desenho
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.04, 0.1))
        h.grade(1.0, alfa=0.035)
        R.poeira(h, t, alfa=0.2)
        for b in BLOCOS:
            h.preenche(b, PAREDE_COR, 0.13)
        for a, b in BORDAS:
            h.linha([a, b], PAREDE_COR, 2.6, 0.85)
        # delegacia no centro
        h.texto("DP", (8.5, 6.5), 20, POLICIA, 0.35)

    def _sirene(self, h, p, t, alfa):
        lado = int(t * 6) % 2
        h.ponto_luz((p[0] - 0.12, p[1] + 0.05), 16, VERMELHO, (0.9 if lado else 0.25) * alfa)
        h.ponto_luz((p[0] + 0.12, p[1] + 0.05), 16, AZUL, (0.25 if lado else 0.9) * alfa)

    def _lance(self, h, rod, k, t, cheio=True):
        """Uma perseguição completa: rastros, visão, policiais, ladrão e resultado."""
        j = rod.jogo
        f = float(rod.fim[k])
        tt = min(t, f)
        pl = rod.pos("pl", k, tt)
        pp = rod.pos("pp", k, tt)
        i = rod.i(tt)
        a0 = max(0, i - 45)
        h.rastro([tuple(q) for q in rod.reg["pl"][k, a0:i + 1:2]] + [tuple(pl)], LADRAO, 3, 0.7)
        for p in range(2):
            h.rastro([tuple(q) for q in rod.reg["pp"][k, a0:i + 1:2, p]] + [tuple(pp[p])], POLICIA, 2.4, 0.55)
        ve = rod.reg["ve"][k, i]
        acabou = t >= f
        if not acabou:
            for p in range(2):
                if ve[p]:       # laser de visão: linha reta, nenhuma parede no meio
                    h.linha([tuple(pp[p]), tuple(pl)], VERMELHO, 1.6, 0.55, tracejado=[6, 6], halo=False)
            if not ve.any() and cheio:   # ninguém vê: a polícia só sabe onde ele ESTAVA
                q = rod.reg["visto"][k, i]
                h.circulo(tuple(q), 0.32, POLICIA, 0.5, 1.4, 0.03)
                h.texto("?", (float(q[0]), float(q[1]) - 0.17), 26, POLICIA, 0.75)
        rl = rod.rumo("pl", k, tt) or 0.0
        rp = rod.rumo("pp", k, tt)
        for p in range(2):
            R.avatar(h, tuple(pp[p]), rp[p] or -math.pi / 2, POLICIA, t, None, alfa=1.0,
                     passo=None if acabou else t * 3.2 + p * 0.5, escala=0.95, base=False)
            self._sirene(h, pp[p], t, 1.0)
        preso = j.estado[k] == PRESO
        cor_l = VERMELHO if (acabou and preso) else (VERDE if (acabou and j.estado[k] == ESCAPOU) else LADRAO)
        R.avatar(h, tuple(pl), rl, cor_l, t, None, passo=None if acabou else t * 3.5, escala=0.95, base=False)
        if acabou:
            idade = t - f
            if preso:
                h.pulso(tuple(pl), idade, VERMELHO, 2.2, 0.8, 5)
                h.particulas(tuple(pl), idade, VERMELHO, n=14, alcance=1.4, dur=0.8, semente=int(k))
                h.texto("PRESO!", (float(pl[0]), float(pl[1]) + 0.85), 30, VERMELHO, min(idade * 4, 1))
            else:
                h.pulso(tuple(pl), idade, VERDE, 2.2, 0.9, 5)
                h.texto("ESCAPOU!", (float(pl[0]), float(pl[1]) + 0.85), 30, VERDE, min(idade * 4, 1))

    def desenha(self, h, rod, t, modo, foco):
        self.cenario(h, t)
        if modo == "replay" and foco is not None:
            self._lance(h, rod, foco, t)
            return
        # ao vivo: 100 perseguições sobrepostas no mesmo mapa (pontos translúcidos) + o líder em destaque
        j = rod.jogo
        for k in rod.vitrine:
            if k == rod.lider:
                continue
            f = float(rod.fim[k])
            pl = rod.pos("pl", k, min(t, f))
            if t < f:
                h.ponto_luz(tuple(pl), 10, LADRAO, 0.35)
                for p in rod.pos("pp", k, t):
                    h.ponto_luz(tuple(p), 8, POLICIA, 0.25)
            elif j.estado[k] == PRESO:
                idade = t - f
                h.pulso(tuple(pl), idade, VERMELHO, 1.0, 0.6, 3)
                h.circulo(tuple(pl), 0.16, VERMELHO, 0.55, 1.2, 0.3)
            else:
                h.circulo(tuple(pl), 0.16, VERDE, 0.6, 1.2, 0.3)
        self._lance(h, rod, rod.lider, t, cheio=False)

    def ponto(self, rod, foco, nome, t):
        f = float(rod.fim[foco])
        tt = min(t, f)
        if nome == "ladrao":
            return tuple(rod.pos("pl", foco, tt))
        if nome in ("pol0", "pol1"):
            return tuple(rod.pos("pp", foco, tt)[int(nome[-1])])
        if nome == "visto":
            return tuple(rod.reg["visto"][foco, rod.i(tt)])
        if nome == "pilar":
            return tuple(PILARES[self.pilar_do_laco(rod, foco)])
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        g = rod.g
        return [("POLÍCIA", "PRESOS", float(self.suave["preso"][g]), POLICIA),
                ("LADRÃO", "SEM SER VISTO", float(self.suave["oculto"][g]), LADRAO)]

    def cerebro(self, rod, t, foco):
        k = foco if foco is not None else rod.lider
        i = min(rod.i(t), rod.reg["ativ_l"].shape[1] - 1)
        genes = rod.genes_l[rod.il[k]:rod.il[k] + 1]
        pesos = [(W[0], b[0]) for W, b in ARQ_LAD.desempacota(genes)]
        return dict(camadas=ARQ_LAD.camadas, pesos=pesos, ativ=rod.reg["ativ_l"][k, i],
                    saidas=("ANDA X", "ANDA Y"), titulo="CÉREBRO // LADRÃO", cor=LADRAO)

    # ------------------------------------------------------------ som
    def sons(self, rod, t0, t1, modo, foco):
        j = rod.jogo
        ev = []
        if modo == "replay" and foco is not None:
            ks = [foco]
        else:
            ks = list(rod.vitrine)
        for k in ks:
            f = float(rod.fim[k])
            if t0 <= f < t1:
                if j.estado[k] == PRESO:
                    ev.append((f, "sirene", 1.0 if len(ks) == 1 else 0.12))
                elif len(ks) == 1:
                    ev.append((f, "ding", 2))
        if len(ks) == 1:   # bipe quando o ladrão volta a ser visto
            k = ks[0]
            a, b = rod.i(t0), rod.i(t1)
            ve = rod.reg["ve"][k].any(1)
            if b > a and ve[b] and not ve[a] and t1 < float(rod.fim[k]):
                ev.append((t1, "alerta", 1.0))
        return ev

    def ambiente(self, dur):
        return None


__all__ = ["Policia", "LADRAO", "POLICIA", "PASSOS"]
