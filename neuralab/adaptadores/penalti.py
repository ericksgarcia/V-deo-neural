"""Adaptador do pênalti (batedor x goleiro), vista de cima em estilo holograma.

Mundo: x lateral (0 = meio do gol), y profundidade (0 = marca do pênalti, 11 = linha do gol).
"""
import math

import numpy as np

from ..coevolucao import ARQ_BAT, partidas
from ..desafios.penalti import DEFESA, DT, FORA, GOL, MEIO_GOL, PULO_DUR, VOO
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, ROSA, VERDE, VERMELHO, Camera2D
from .base import Adaptador, Rodada

AZUL = ROSA        # o goleiro é rosa-neon (contrasta com o campo ciano); nome mantido p/ o roteiro
LINHA_GOL, FUNDO_REDE = 11.0, 12.6


def pos_batedor(r):
    r = min(max(r, 0.0), 1.0)
    return -2.3 + 1.75 * r, -2.25 + 1.9 * r


class RodadaPenalti(Rodada):
    def __init__(self, hist, g, jogos_por_batedor=8):
        self.g, self.dt = g, DT
        gb, gg = hist["bat"][g], hist["gol"][g]
        pop = len(gb)
        sem = int(hist["semente"][g])
        ib = np.repeat(np.arange(pop), jogos_por_batedor)
        ig = np.random.default_rng(sem).permutation(np.tile(np.arange(pop), jogos_por_batedor))
        self.jogo, self.reg = partidas(gb, gg, ib, ig, sem, gravar=True)
        self.ib, self.ig, self.genes_b, self.genes_g = ib, ig, gb, gg
        self.T = self.reg["r"].shape[1]
        self.duracao = self.T * DT
        j = self.jogo
        self.fim = np.where(j.t_fim >= 0, j.t_fim * DT, self.duracao)
        self.vitrine = np.arange(0, len(ib), jogos_por_batedor)  # uma cobrança por batedor = 100 lances
        gols = np.zeros(pop)
        np.add.at(gols, ib, j.estado == GOL)
        self.lider_b = int(np.argmax(gols))
        self.lider = int(np.where(ib == self.lider_b)[0][0])

    def i(self, t):
        return int(min(max(t / DT, 0), self.T - 1))


def _bola_pos(j, k, t):
    """Posição da bola (x, y) e se o lance já terminou."""
    tc = j.chute_t[k]
    if tc < 0 or t < tc:
        return (0.0, 0.0), False
    u = (t - tc) / VOO
    x = j.alvo[k] * min(u, 1)
    y = LINHA_GOL * min(u, 1)
    if u > 1:
        extra = min(u - 1, 0.5)
        lado = np.sign(j.alvo[k]) or 1
        if j.estado[k] == GOL:
            y += extra * 3.0
        elif j.estado[k] == DEFESA:  # rebate para fora
            x += lado * extra * 4
            y -= extra * 5
        else:
            x += lado * extra * 2
            y += extra * 4
    return (float(x), float(y)), u > 1


class Penalti(Adaptador):
    titulo = "PÊNALTI"
    experimento = "004"
    cores = {"bat": AMARELO, "gol": AZUL, "verde": VERDE, "vermelho": VERMELHO}

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["bat"])
        self._cache = {}
        k = 7  # mesmas médias móveis do roteiro: o HUD mostra exatamente os números falados
        sv = lambda x: np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")
        self.suave = {c: sv(hist["m_" + c]) for c in ("gol", "defesa", "fora")}

    def rodada(self, g):
        if g not in self._cache:
            self._cache[g] = RodadaPenalti(self.hist, g)
        return self._cache[g]

    # ------------------------------------------------------------ lances
    def duracao_foco(self, rod, foco):
        return float(rod.fim[foco]) + 1.0

    def janela_lance(self, rod, foco):
        """Trecho essencial de um lance (para montagens rápidas): do preparo do chute até o resultado."""
        tc = float(rod.jogo.chute_t[foco])
        return max(tc - 0.7, 0.0), float(rod.fim[foco]) + 0.45

    def chaves_lento(self, rod, foco):
        j = rod.jogo
        ch = [float(j.chute_t[foco]) + VOO * 0.75]
        if j.pulo_t[foco] >= 0:
            ch.append(float(j.pulo_t[foco]))
        return ch

    def busca(self, rod, tipo):
        """Acha na geração um lance que mostre o comportamento pedido (para o replay)."""
        j = rod.jogo
        antes = (j.pulo_t >= 0) & (j.pulo_t < j.chute_t + 0.05)
        gol, defesa, fora = j.estado == GOL, j.estado == DEFESA, j.estado == FORA
        lado_errado = np.sign(j.pulo_dir) != np.sign(j.alvo)
        finta = (np.abs(j.corpo_antes) > 0.35) & (np.sign(j.corpo_antes) != np.sign(j.canto_pedido))
        criterios = {
            "paciente": (defesa & ~antes, -np.abs(j.alvo)),
            "leitura": (defesa & antes & ~lado_errado & (np.sign(j.corpo_antes) == np.sign(j.alvo)),
                        np.abs(j.corpo_antes)),
            "finta": (gol & finta & antes & lado_errado, np.abs(j.corpo_antes) + np.abs(j.alvo) * 0.2),
            "fora": (fora, np.abs(j.alvo)),
            "gol": (gol, np.abs(j.alvo)),
        }
        ok, nota = criterios[tipo]
        idx = np.where(ok)[0]
        if not len(idx):
            return None
        return int(idx[np.argmax(nota[idx])])

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        """Enquadramento fixo da marca até a rede (batedor, bola e goleiro sempre juntos).

        No replay, aproxima de leve (até 1,15x) entre o chute e o resultado; no ao vivo, quando as
        bolas chegam, aproxima do gol para mostrar o mapa de chutes."""
        geral = Camera2D(centro=(0.2, 5.3), escala=54, t=t)
        j = rod.jogo
        if modo != "replay" or foco is None:
            tc = float(np.median(j.chute_t[rod.vitrine]))
            gol = Camera2D(centro=(0.0, 9.4), escala=88, t=t)
            return geral.mistura(gol, (t - tc - 0.1) / 0.6)
        tc, tf = float(j.chute_t[foco]), float(rod.fim[foco])
        perto = Camera2D(centro=(float(np.clip(j.alvo[foco], -3, 3)) * 0.25, 6.2), escala=62, t=t)
        k = min((t - (tc - 0.3)) / 0.5, 1.0) - max((t - tf - 0.6) / 0.6, 0.0)
        cam = geral.mistura(perto, k)
        if 0 <= t - tf < 0.35:  # tremida no impacto
            cam.tremor = 9 * (1 - (t - tf) / 0.35)
        return cam

    # ------------------------------------------------------------ desenho
    def cenario(self, h, t, rede_impacto=None):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.045)
        R.poeira(h, t, alfa=0.3)
        R.placa(h, -20.16, -5.5, 20.16, LINHA_GOL, t, CIANO)            # grande área
        h.linha([(-20, LINHA_GOL), (20, LINHA_GOL)], CIANO, 3, 0.8)
        h.linha([(-9.16, LINHA_GOL), (-9.16, LINHA_GOL - 5.5), (9.16, LINHA_GOL - 5.5), (9.16, LINHA_GOL)],
                CIANO, 2, 0.55)
        h.circulo((0, 0), 0.14, BRANCO, 0.9, 2, 0.6)                       # marca do pênalti
        h.pulso((0, 0), (t % 1.6), CIANO, 0.8, 1.6, 2)
        h.texto("MARCA · 11 m", (0, -0.75), 20, CIANO, 0.55)
        # rede (ondula perto do ponto onde a bola entrou)
        for x in np.linspace(-MEIO_GOL, MEIO_GOL, 19):
            dx = 0.0
            if rede_impacto:
                ix, idade = rede_impacto
                dx = 0.25 * math.exp(-((x - ix) ** 2) / 0.8) * math.sin(idade * 30) * math.exp(-idade * 4)
            h.linha([(x, LINHA_GOL), (x * 1.04 + dx, FUNDO_REDE)], BRANCO, 1, 0.16, halo=False)
        for y in np.linspace(LINHA_GOL + 0.3, FUNDO_REDE, 6):
            h.linha([(-MEIO_GOL * 1.03, y), (MEIO_GOL * 1.03, y)], BRANCO, 1, 0.16, halo=False)
        h.linha([(-MEIO_GOL, LINHA_GOL), (-MEIO_GOL * 1.04, FUNDO_REDE), (MEIO_GOL * 1.04, FUNDO_REDE),
                 (MEIO_GOL, LINHA_GOL)], BRANCO, 1.6, 0.5)
        h.linha([(-MEIO_GOL, LINHA_GOL), (MEIO_GOL, LINHA_GOL)], BRANCO, 4, 1)
        for x in (-MEIO_GOL, MEIO_GOL):
            h.ponto_luz((x, LINHA_GOL), 16, BRANCO)

    def _goleiro(self, h, j, reg, k, i, t, alfa=1.0, cheio=True, escala=2.0):
        x = float(reg["xg"][k, i])
        pt = float(j.pulo_t[k])
        q = 0.0 if pt < 0 or t < pt else min((t - pt) / (PULO_DUR * 0.6), 1.0)
        c = (x, LINHA_GOL - 0.45)
        if cheio:
            if q > 0:  # rastro do mergulho (duas poses anteriores, apagadas)
                for atras, a2 in ((0.12, 0.18), (0.06, 0.3)):
                    q2 = max(q - atras / (PULO_DUR * 0.6), 0.0)
                    x2 = float(reg["xg"][k, max(i - int(atras / DT), 0)])
                    R.avatar(h, (x2, c[1]), -math.pi / 2, AZUL, t, None, alfa=a2 * alfa, bracos=0.7, mergulho=q2,
                             lado_mergulho=int(j.pulo_dir[k]) or 1, base=False, detalhe=False, escala=escala)
            R.avatar(h, c, -math.pi / 2, AZUL, t, "1", alfa=alfa, bracos=0.7, mergulho=q,
                     lado_mergulho=int(j.pulo_dir[k]) or 1, escala=escala)
        else:  # fantasma barato: só o eixo do corpo
            ang = 0.0 if q > 0.4 else math.pi / 2
            d = 0.35 + 0.6 * q
            a = (x - d * math.cos(ang), c[1] - d * math.sin(ang))
            b = (x + d * math.cos(ang), c[1] + d * math.sin(ang))
            h.linha([a, b], AZUL, 3, alfa, halo=False)

    def _batedor(self, h, j, reg, k, i, t, alfa=1.0, cone=True):
        r = float(reg["r"][k, i])
        corpo = float(reg["corpo"][k, i])
        x, y = pos_batedor(r)
        tc = float(j.chute_t[k])
        corre = tc < 0 or t < tc
        frente = math.atan2(0 - y, 0 - x) if corre else math.radians(80)
        corpo_ang = math.atan2(LINHA_GOL - y, corpo * MEIO_GOL - x)
        if cone and corre:
            h.cone((x, y), corpo_ang, 0.38, 6.0, AMARELO, 0.22 * alfa)
        R.avatar(h, (x, y), frente, AMARELO, t, "10", alfa=alfa, corpo_ang=corpo_ang,
                 passo=(r * 4.5) if corre and r < 1 else None, escala=2.0)

    def _resultado(self, h, j, k, t, alfa=1.0, forte=True):
        if j.t_fim[k] < 0 or t < j.t_fim[k] * DT:
            return
        tf = float(j.t_fim[k] * DT)
        x = float(np.clip(j.alvo[k], -MEIO_GOL - 1.4, MEIO_GOL + 1.4))
        est = int(j.estado[k])
        cor = {GOL: VERDE, DEFESA: AZUL, FORA: VERMELHO}[est]
        y = LINHA_GOL + (0.6 if est == GOL else (-0.2 if est == DEFESA else 0.9))
        idade = t - tf
        if forte:
            h.pulso((x, y), idade, cor, 1.6, 0.8, 5)
            h.particulas((x, y), idade, cor, n=16, alcance=1.6, dur=0.9, semente=int(k))
        h.ponto_luz((x, y), 10 if forte else 6, cor, alfa)

    def desenha(self, h, rod, t, modo, foco):
        j, reg = rod.jogo, rod.reg
        i = rod.i(t)
        if modo == "replay" and foco is not None:
            k = foco
            tf = float(rod.fim[k])
            imp = (float(j.alvo[k]), t - tf) if (j.estado[k] == GOL and t >= tf) else None
            self.cenario(h, t, imp)
            self._goleiro(h, j, reg, k, i, t)
            self._batedor(h, j, reg, k, i, t)
            (bx, by), _ = _bola_pos(j, k, t)
            tc = float(j.chute_t[k])
            rastro = None
            if tc >= 0 and t > tc:
                rastro = [_bola_pos(j, k, u)[0] for u in np.linspace(max(tc, t - 0.25), t, 14)]
            R.bola(h, (bx, by), t, rastro=rastro)
            self._resultado(h, j, k, t)
            return
        # ao vivo: 100 cobranças ao mesmo tempo. Batedores translúcidos, leque de chutes, mapa de resultados.
        self.cenario(h, t)
        for k in rod.vitrine:
            r = float(reg["r"][k, i])
            tc = float(j.chute_t[k])
            if tc < 0 or t < tc + 0.2:   # batedor fantasma correndo
                bx, by = pos_batedor(r)
                h.ponto_luz((bx, by), 14, AMARELO, 0.22)
                h.circulo((bx, by), 0.22, AMARELO, 0.25, 1.2, 0.05)
            if tc >= 0 and t >= tc:      # leque: trajetória de cada chute
                u = min((t - tc) / VOO, 1.0)
                h.linha([(0, 0), (j.alvo[k] * u, LINHA_GOL * u)], AMARELO, 1.2, 0.16, halo=False)
                if u < 1:
                    h.ponto_luz((j.alvo[k] * u, LINHA_GOL * u), 7, BRANCO, 0.8)
            self._goleiro(h, j, reg, k, i, t, alfa=0.22, cheio=False)
            self._resultado(h, j, k, t, alfa=0.7, forte=False)
            if j.estado[k] == FORA and j.t_fim[k] >= 0 and t >= j.t_fim[k] * DT:   # × vermelho fora das traves
                x = float(np.clip(j.alvo[k], -MEIO_GOL - 1.6, MEIO_GOL + 1.6))
                for dx in (-0.15, 0.15):
                    h.linha([(x - dx, LINHA_GOL + 0.75), (x + dx, LINHA_GOL + 1.05)], VERMELHO, 2.5, 0.8)
        k = rod.lider
        self._goleiro(h, j, reg, k, i, t)
        (bx, by), _ = _bola_pos(j, k, t)
        R.bola(h, (bx, by), t)

    def ponto(self, rod, foco, nome, t):
        j, reg = rod.jogo, rod.reg
        i = rod.i(t)
        if nome == "goleiro":
            return (float(reg["xg"][foco, i]), LINHA_GOL - 0.45)
        if nome == "batedor":
            return pos_batedor(float(reg["r"][foco, i]))
        if nome == "bola_fim":
            return (float(np.clip(j.alvo[foco], -4.6, 4.6)), LINHA_GOL + 0.3)
        if nome == "canto_corpo":
            return (float(j.corpo_antes[foco]) * MEIO_GOL, LINHA_GOL - 1.0)
        if nome == "frente_corpo":  # 2,6 m à frente do batedor, na direção para onde o corpo aponta
            x, y = pos_batedor(float(reg["r"][foco, i]))
            a = math.atan2(LINHA_GOL - y, float(reg["corpo"][foco, i]) * MEIO_GOL - x)
            return (x + 2.6 * math.cos(a), y + 2.6 * math.sin(a))
        raise KeyError(nome)

    # ------------------------------------------------------------ HUD
    def medidores(self, rod, t, foco):
        g = rod.g
        return [("BATEDOR", "GOLS", float(self.suave["gol"][g]), AMARELO),
                ("GOLEIRO", "DEFESAS", float(self.suave["defesa"][g]), AZUL)]

    def cerebro(self, rod, t, foco):
        k = foco if foco is not None else rod.lider
        i = rod.i(t)
        genes = rod.genes_b[rod.ib[k]:rod.ib[k] + 1]
        pesos = [(W[0], b[0]) for W, b in ARQ_BAT.desempacota(genes)]
        return dict(camadas=ARQ_BAT.camadas, pesos=pesos, ativ=rod.reg["ativ_b"][k, i],
                    saidas=("RITMO", "CORPO", "CANTO"), titulo="CÉREBRO // BATEDOR", cor=AMARELO)

    # ------------------------------------------------------------ som
    def sons(self, rod, t0, t1, modo, foco):
        j = rod.jogo
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else list(rod.vitrine)
        for k in ks:
            tc, tf = float(j.chute_t[k]), float(rod.fim[k])
            if t0 <= tc < t1:
                ev.append((tc, "chute", 1.0 if len(ks) == 1 else 0.25))
            if t0 <= tf < t1:
                tipo = {GOL: "rede", DEFESA: "defesa", FORA: "fora"}[int(j.estado[k])]
                ev.append((tf, tipo, 1.0 if len(ks) == 1 else 0.2))
        return ev

    def ambiente(self, dur):
        from .. import audio
        return audio.torcida(dur)
