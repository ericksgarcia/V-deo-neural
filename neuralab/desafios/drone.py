"""Desafio: um drone cruza uma tempestade e pousa na plataforma (física 2D simplificada, com vento).

O vento sopra na horizontal e muda com a altitude e com o tempo (camadas + rajadas). O drone tem um
sensor de vento e uma bateria limitada: lutar contra a tempestade gasta bateria.
"""
import numpy as np

from .foguete import FALHA, SUCESSO, VOANDO, Foguete


def vento(x, y, t, fase):
    """Vento horizontal (m/s) em (x, y) no instante t (s). `fase` (N,) varia a rajada de cada partida."""
    camada = 5.5 * np.tanh((y - 38.0) / 18.0)                  # alto: a favor (+x); baixo: contra (-x)
    rajada = 3.2 * np.sin(0.9 * t + 0.07 * x + fase) * (0.4 + y / 100.0)
    return camada + rajada


class Drone(Foguete):
    nome = "drone"
    camadas = (9, 12, 2)
    passos = 480           # 16 s
    mundo = (-50.0, 50.0, 0.0, 100.0)
    arrasto = 0.35         # quanto o vento empurra o drone (1/s)
    combustivel_s = 9.0    # s de motor a pleno (bateria)
    ga = {}

    def __init__(self, n, rng, ruido=0.6, forca=1.0):
        self.n = n
        self.forca = forca   # 1 = tempestade do treino; >1 = tempestade mais forte (teste de estresse)
        x = np.full(n, -30.0) + rng.normal(0, 2.0 * ruido, n)
        y = np.full(n, 62.0) + rng.normal(0, 3.0 * ruido, n)
        vx = rng.normal(0, 1.0 * ruido, n)
        vy = rng.normal(0, 1.0 * ruido, n)
        ang = rng.normal(0, 0.08 * ruido, n)
        self.s = np.stack([x, y, vx, vy, ang, np.zeros(n)], 1)
        self.comb = np.ones(n)
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros(n)
        self.impacto = np.zeros(n)
        self.dx_final = np.zeros(n)
        self.fase = rng.uniform(0, 2 * np.pi, n)
        self.t = 0.0
        self.vento_med = np.zeros(n)   # soma do vento sentido (m/s·passos), p/ saber quem "surfou"
        self.passos_vivo = np.zeros(n)
        self.bateu_chao = np.zeros(n, bool)

    def vento_em(self):
        x, y = self.s[:, 0], self.s[:, 1]
        return self.forca * vento(x, y, self.t, self.fase)

    def observa(self):
        x, y, vx, vy, a, w = self.s.T
        wd = self.vento_em()
        return np.stack([(x - self.pad_x) / 50, y / 100, vx / 15, vy / 15,
                         np.sin(a), np.cos(a), w / 3, self.comb * 2 - 1, wd / 8], 1).astype(np.float32)

    def passo(self, saida, t):
        self.t = t * self.dt
        vivo = self.estado == VOANDO
        thr = (saida[:, 0] + 1) / 2 * (self.comb > 0)
        tor = saida[:, 1]
        x, y, vx, vy, a, w = self.s.T.copy()
        wd = self.forca * vento(x, y, self.t, self.fase)
        w = w + (tor * self.giro_max - 0.8 * w) * self.dt
        a = a + w * self.dt
        ax = np.sin(a) * thr * self.empuxo_max + self.arrasto * (wd - vx)
        ay = np.cos(a) * thr * self.empuxo_max - self.g
        vx, vy = vx + ax * self.dt, vy + ay * self.dt
        x, y = x + vx * self.dt, y + vy * self.dt
        novo = np.stack([x, y, vx, vy, a, w], 1)
        self.s[vivo] = novo[vivo]
        self.comb[vivo] = np.maximum(0, self.comb[vivo] - thr[vivo] * self.dt / self.combustivel_s)
        self.acel = np.where(vivo, thr, 0)
        self.vento_med[vivo] += wd[vivo] * np.sign(self.pad_x - x[vivo])   # + = vento empurrando para a plataforma
        self.passos_vivo[vivo] += 1

        x, y, vx, vy, a, w = self.s.T
        tocou = vivo & (y <= 0)
        fora = vivo & ((np.abs(x) > 58) | (y > 125))
        no_pad = np.abs(x - self.pad_x) <= self.pad_meia
        ok = tocou & no_pad & (np.abs(vy) <= 5.0) & (np.abs(vx) <= 3.0) & (np.abs(a) <= 0.35)
        self.impacto[tocou] = np.hypot(vx, vy)[tocou]
        self.impacto[fora] = 30
        self.s[tocou, 1] = 0
        self.estado[ok] = SUCESSO
        self.estado[(tocou & ~ok) | fora] = FALHA
        acabou = tocou | fora
        self.t_fim[acabou] = t
        self.dx_final[acabou] = np.abs(x - self.pad_x)[acabou]

    def metricas(self):
        suc = self.estado == SUCESSO
        a_favor = self.vento_med / np.maximum(self.passos_vivo, 1)
        return {
            "bateria": float(self.comb[suc].mean()) if suc.any() else 0.0,        # bateria que sobrou nos pousos
            "vento_favor": float(a_favor[suc].mean()) if suc.any() else 0.0,        # m/s médio a favor nos pousos
            "alt_media": float(self.s[:, 1].mean()),
        }
