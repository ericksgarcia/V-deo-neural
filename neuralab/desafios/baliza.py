"""Desafio: fazer baliza (estacionar em paralelo entre dois carros, de ré)."""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

COMP, LARG = 4.5, 1.9  # carro (m)


def cantos(x, y, h, comp=COMP, larg=LARG):
    """(N,) -> (N, 4, 2) cantos do retângulo orientado."""
    c, s = np.cos(h), np.sin(h)
    dx = np.array([1, 1, -1, -1]) * comp / 2
    dy = np.array([1, -1, -1, 1]) * larg / 2
    px = x[:, None] + dx * c[:, None] - dy * s[:, None]
    py = y[:, None] + dx * s[:, None] + dy * c[:, None]
    return np.stack([px, py], -1)


class Baliza:
    nome = "baliza"
    camadas = (7, 10, 2)
    dt = 1 / 30
    passos = 540  # 18 s
    mundo = (-16.0, 16.0, -1.0, 9.0)

    vaga_y = 1.25
    meia_vaga = 3.6  # espaço livre = 7,2 m (1,6x o carro)
    estacionados = [(-(3.6 + COMP / 2), 1.25), (3.6 + COMP / 2, 1.25)]
    v_max, ester_max, forca_acel = 3.0, 0.6, 3.0

    def __init__(self, n, rng, ruido=0.3):
        self.n = n
        x = np.full(n, 6.6) + rng.normal(0, 0.5 * ruido, n)
        y = np.full(n, 3.9) + rng.normal(0, 0.25 * ruido, n)
        h = np.zeros(n) + rng.normal(0, 0.05 * ruido, n)
        self.s = np.stack([x, y, h, np.zeros(n), np.zeros(n)], 1)  # x y rumo vel esterço
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros(n)
        self.bateu = np.zeros(n, bool)
        self.parado_bem = np.zeros(n)

    def observa(self):
        x, y, h, v, e = self.s.T
        return np.stack([x / 8, (y - self.vaga_y) / 3, np.sin(h), np.cos(h) - 1,
                         v / self.v_max, e / self.ester_max, np.tanh(self.parado_bem / 15)], 1).astype(np.float32)

    def colide(self, x, y, h):
        cc = cantos(x, y, h)
        bate = (cc[..., 1] < 0.05).any(1) | (cc[..., 1] > 8.5).any(1) | (np.abs(cc[..., 0]) > 15.5).any(1)
        for ox, oy in self.estacionados:
            dentro = (np.abs(cc[..., 0] - ox) < COMP / 2) & (np.abs(cc[..., 1] - oy) < LARG / 2)
            bate |= dentro.any(1)
            oc = cantos(np.array([ox]), np.array([oy]), np.array([0.0]))[0]  # (4,2)
            rx, ry = oc[None, :, 0] - x[:, None], oc[None, :, 1] - y[:, None]
            c, s = np.cos(h)[:, None], np.sin(h)[:, None]
            lx, ly = rx * c + ry * s, -rx * s + ry * c
            bate |= ((np.abs(lx) < COMP / 2) & (np.abs(ly) < LARG / 2)).any(1)
        return bate

    def passo(self, saida, t):
        vivo = self.estado == VOANDO
        x, y, h, v, e = self.s.T.copy()
        e = e + (saida[:, 1] * self.ester_max - e) * min(1, 6 * self.dt)
        v = np.clip(v + saida[:, 0] * self.forca_acel * self.dt - 0.4 * v * self.dt, -self.v_max, self.v_max)
        h = h + v / (COMP * 0.6) * np.tan(e) * self.dt
        x = x + v * np.cos(h) * self.dt
        y = y + v * np.sin(h) * self.dt
        novo = np.stack([x, y, h, v, e], 1)
        self.s[vivo] = novo[vivo]
        self.acel = np.where(vivo, saida[:, 0], 0)

        x, y, h, v, e = self.s.T
        bate = vivo & self.colide(x, y, h)
        self.bateu |= bate
        self.estado[bate] = FALHA
        self.t_fim[bate] = t
        bom = vivo & ~bate & (np.abs(x) < 1.0) & (np.abs(y - self.vaga_y) < 0.45) & (np.abs(np.sin(h)) < 0.12)
        self.parado_bem = np.where(bom, self.parado_bem + 1, 0)
        ok = bom & (np.abs(v) < 0.6)
        self.estado[ok] = SUCESSO
        self.t_fim[ok] = t

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        self.estado[vivo] = FALHA
        self.t_fim[vivo] = t

    def erro(self):
        x, y, h, v, e = self.s.T
        return np.hypot(x / 2, (y - self.vaga_y)) + 2 * np.abs(np.sin(h))

    def aptidao(self):
        f = 3 * np.exp(-self.erro() / 1.5) * (1 + np.exp(-np.abs(self.s[:, 3]))) - 0.5 * self.bateu
        return f + (self.estado == SUCESSO) * 6

    def chegou_mas_bateu(self):
        x, y, h, v, e = self.s.T
        return int((self.bateu & (np.abs(x) < 3) & (y < 2.5)).sum())
