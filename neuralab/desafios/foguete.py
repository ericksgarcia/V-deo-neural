"""Desafio: pousar um foguete numa plataforma (física 2D simplificada)."""
import numpy as np

VOANDO, SUCESSO, FALHA = 0, 1, 2


class Foguete:
    nome = "foguete"
    camadas = (8, 10, 2)
    dt = 1 / 30
    passos = 420  # 14 s de simulação
    mundo = (-50.0, 50.0, 0.0, 100.0)  # xmin, xmax, ymin, ymax (metros)

    g = 4.0
    empuxo_max = 2.3 * g
    giro_max = 3.0
    pad_x, pad_meia = 20.0, 7.0
    combustivel_s = 7.0

    def __init__(self, n, rng, ruido=0.6):
        self.n = n
        x = np.full(n, -30.0) + rng.normal(0, 2.0 * ruido, n)
        y = np.full(n, 88.0) + rng.normal(0, 2.0 * ruido, n)
        vx = np.full(n, 7.0) + rng.normal(0, 1.5 * ruido, n)
        vy = np.zeros(n) + rng.normal(0, 1.0 * ruido, n)
        ang = np.full(n, 0.35) + rng.normal(0, 0.08 * ruido, n)
        self.s = np.stack([x, y, vx, vy, ang, np.zeros(n)], 1)
        self.comb = np.ones(n)
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros(n)  # último throttle, para desenhar a chama
        self.impacto = np.zeros(n)
        self.dx_final = np.zeros(n)

    def observa(self):
        x, y, vx, vy, a, w = self.s.T
        return np.stack([(x - self.pad_x) / 50, y / 100, vx / 15, vy / 15,
                         np.sin(a), np.cos(a), w / 3, self.comb * 2 - 1], 1).astype(np.float32)

    def passo(self, saida, t):
        vivo = self.estado == VOANDO
        thr = (saida[:, 0] + 1) / 2 * (self.comb > 0)
        tor = saida[:, 1]
        x, y, vx, vy, a, w = self.s.T.copy()
        w = w + (tor * self.giro_max - 0.8 * w) * self.dt
        a = a + w * self.dt
        ax = np.sin(a) * thr * self.empuxo_max
        ay = np.cos(a) * thr * self.empuxo_max - self.g
        vx, vy = vx + ax * self.dt, vy + ay * self.dt
        x, y = x + vx * self.dt, y + vy * self.dt
        novo = np.stack([x, y, vx, vy, a, w], 1)
        self.s[vivo] = novo[vivo]
        self.comb[vivo] = np.maximum(0, self.comb[vivo] - thr[vivo] * self.dt / self.combustivel_s)
        self.acel = np.where(vivo, thr, 0)

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
        acabou = (tocou | fora)
        self.t_fim[acabou] = t
        self.dx_final[acabou] = np.abs(x - self.pad_x)[acabou]

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        self.estado[vivo] = FALHA
        self.t_fim[vivo] = t
        self.dx_final[vivo] = np.abs(self.s[vivo, 0] - self.pad_x)
        self.impacto[vivo] = 30  # não pousou: pior que bater devagar

    def aptidao(self):
        x, y, vx, vy, a, w = self.s.T
        perto = 1 - np.minimum(np.hypot(x - self.pad_x, y) / 80, 1)
        suave = np.exp(-self.impacto / 6)
        reto = 1 - np.minimum(np.abs(a) / 1.5, 1)
        f = 2 * perto + perto ** 2 * (3 * suave + 0.5 * reto)
        return f + (self.estado == SUCESSO) * (5 + 2 * self.comb)

    # descrição do "quase lá" para o roteiro: chegou na plataforma mas bateu
    def chegou_mas_bateu(self):
        return int(((self.estado == FALHA) & (self.dx_final <= self.pad_meia) & (self.impacto < 30)).sum())
