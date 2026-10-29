"""Desafio: corrida de carrinhos. Baterias de 4 carros disputam 2 voltas numa pista fechada.

Cada carro enxerga a pista à frente e o rival mais próximo (à frente e atrás). O toque entre
carros é de verdade (perde velocidade), então ultrapassar, defender e bater são comportamentos
que a seleção pode ou não descobrir. A aptidão premia andar longe E andar à frente dos outros.
"""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

COMP, LARG = 3.0, 1.4          # carro (m)
LARG_PISTA = 4.6               # meia largura da pista (m)
VOLTAS = 2
GRID = 4                       # carros por bateria


def _pista(M=720):
    t = np.linspace(0, 2 * np.pi, M, endpoint=False)
    # elipse alongada com uma "barriga" e uma curva fechada: tem reta, curva larga e curva lenta
    x = 17 * np.cos(t) + 3.0 * np.cos(2 * t) * np.sin(t)
    y = 33 * np.sin(t) + 5.0 * np.sin(3 * t)
    P = np.stack([x, y], 1)
    d = np.diff(np.vstack([P, P[:1]]), axis=0)
    seg = np.hypot(d[:, 0], d[:, 1])
    S = np.concatenate([[0], np.cumsum(seg)[:-1]])
    TH = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    return P, S, float(seg.sum()), TH


PISTA, ARCO, COMPRIMENTO, TANGENTE = _pista()
PASSO_ARCO = COMPRIMENTO / len(ARCO)


def ang(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class Corrida:
    nome = "corrida"
    camadas = (10, 12, 2)
    dt = 1 / 30
    passos = 780  # 26 s
    mundo = (-26.0, 26.0, -44.0, 44.0)
    v_max, esterc_max, ester_lat = 22.0, 0.5, 20.0
    ga = {"elite": 10, "taxa": 0.1, "forca": 0.15}

    def __init__(self, n, rng, ruido=1.0):
        assert n % GRID == 0
        self.n = n
        perm = rng.permutation(n)
        self.heat = np.empty(n, int)
        self.slot = np.empty(n, int)
        self.heat[perm] = np.arange(n) // GRID
        self.slot[perm] = np.arange(n) % GRID
        self.mates = np.stack([np.where(self.heat == h)[0] for h in range(n // GRID)])[self.heat]  # (n, GRID)
        i0 = 0
        atras = np.array([0.0, 0.0, 7.0, 7.0])[self.slot] + rng.normal(0, 0.3 * ruido, n)
        lado = np.array([-1.7, 1.7, -1.7, 1.7])[self.slot] + rng.normal(0, 0.15 * ruido, n)
        idx = (i0 - (atras / PASSO_ARCO).astype(int)) % len(ARCO)
        th = TANGENTE[idx]
        x = PISTA[idx, 0] - np.sin(th) * lado
        y = PISTA[idx, 1] + np.cos(th) * lado
        h = th + rng.normal(0, 0.03 * ruido, n)
        self.s = np.stack([x, y, h, np.zeros(n), np.zeros(n)], 1)
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros(n)
        self.idx = idx
        self.prog = -atras.copy()
        self.off = lado.copy()
        self.herr = np.zeros(n)
        self.bateu_parede = np.zeros(n, bool)
        self.toques = np.zeros(n, int)
        self.ultra = np.zeros(n, int)       # ultrapassagens feitas
        self.bloqueio = np.zeros(n, int)    # passos "fechando a porta"
        self.ordem = self._ordem()
        self.atualiza_geo()

    # ------------------------------------------------------------ geometria
    def _ordem(self):
        p = self.prog[self.mates]                 # (n, GRID)
        return (p[:, :, None] < p[:, None, :]).sum(2)[np.arange(self.n), np.argmax(self.mates == np.arange(self.n)[:, None], 1)]

    def atualiza_geo(self):
        x, y, h = self.s[:, 0], self.s[:, 1], self.s[:, 2]
        d2 = (x[:, None] - PISTA[None, :, 0]) ** 2 + (y[:, None] - PISTA[None, :, 1]) ** 2
        idx = d2.argmin(1)
        da = ARCO[idx] - ARCO[self.idx]
        da = np.where(da < -COMPRIMENTO / 2, da + COMPRIMENTO, np.where(da > COMPRIMENTO / 2, da - COMPRIMENTO, da))
        self.prog = self.prog + da
        self.idx = idx
        th = TANGENTE[idx]
        self.off = -(x - PISTA[idx, 0]) * np.sin(th) + (y - PISTA[idx, 1]) * np.cos(th)
        self.herr = ang(h - th)

    def _a_frente(self, k_m):
        M = len(ARCO)
        return ang(TANGENTE[(self.idx + int(k_m / PASSO_ARCO)) % M] - TANGENTE[self.idx])

    def rivais(self):
        """Rival vivo mais próximo à frente e atrás, no referencial do carro: (n,4) = fx, fy, tx, ty."""
        x, y, h = self.s[:, 0], self.s[:, 1], self.s[:, 2]
        mx, my = x[self.mates], y[self.mates]
        dx, dy = mx - x[:, None], my - y[:, None]
        c, s = np.cos(h)[:, None], np.sin(h)[:, None]
        lx, ly = dx * c + dy * s, -dx * s + dy * c
        vivo = (self.estado[self.mates] == VOANDO) & (self.mates != np.arange(self.n)[:, None])
        dist = np.hypot(lx, ly)
        out = np.zeros((self.n, 4))
        out[:, 0] = out[:, 2] = 1.0
        for j, sinal in ((0, 1), (2, -1)):
            ok = vivo & (sinal * lx > 0) & (dist < 15)
            dd = np.where(ok, dist, 99)
            k = dd.argmin(1)
            tem = ok[np.arange(self.n), k]
            out[:, j] = np.where(tem, np.abs(lx[np.arange(self.n), k]) / 15, 1.0)
            out[:, j + 1] = np.where(tem, ly[np.arange(self.n), k] / 4, 0.0)
        return out

    def observa(self):
        v = self.s[:, 3]
        r = self.rivais()
        return np.column_stack([v / self.v_max, self.off / LARG_PISTA, np.sin(self.herr), np.cos(self.herr) - 1,
                                self._a_frente(8) * 1.5, self._a_frente(22), r]).astype(np.float32)

    # ------------------------------------------------------------ passo
    def passo(self, saida, t):
        vivo = self.estado == VOANDO
        x, y, h, v, e = self.s.T.copy()
        e = e + (saida[:, 1] * self.esterc_max - e) * min(1, 8 * self.dt)
        v = np.clip(v + (saida[:, 0] * 9.0 - 0.012 * v * v) * self.dt, 0, self.v_max)
        giro = np.clip(v / (COMP * 0.6) * np.tan(e), -self.ester_lat / np.maximum(v, 1), self.ester_lat / np.maximum(v, 1))
        h = h + giro * self.dt
        x = x + v * np.cos(h) * self.dt
        y = y + v * np.sin(h) * self.dt
        novo = np.stack([x, y, h, v, e], 1)
        self.s[vivo] = novo[vivo]
        self.acel = np.where(vivo, saida[:, 0], 0)
        ord_antes = self.ordem.copy()
        self.colide_carros(vivo)
        self.atualiza_geo()
        self.ordem = self._ordem()
        vivo2 = vivo & (self.estado == VOANDO)
        self.ultra += (vivo2 & (self.ordem < ord_antes)).astype(int)
        self.contabiliza_bloqueio(vivo2)
        parede = vivo2 & (np.abs(self.off) > LARG_PISTA)
        self.bateu_parede |= parede
        self.estado[parede] = FALHA
        self.t_fim[parede] = t
        fim = vivo2 & ~parede & (self.prog >= VOLTAS * COMPRIMENTO)
        self.estado[fim] = SUCESSO
        self.t_fim[fim] = t

    def colide_carros(self, vivo):
        x, y, h, v = self.s[:, 0], self.s[:, 1], self.s[:, 2], self.s[:, 3]
        off = np.array([0.8, -0.8])
        raio = 1.45
        for a in range(GRID):
            for b in range(a + 1, GRID):
                i = np.where(self.slot == a)[0]
                i = i[np.argsort(self.heat[i])]
                j = np.where(self.slot == b)[0]
                j = j[np.argsort(self.heat[j])]
                ok = vivo[i] & vivo[j] & (self.estado[i] == VOANDO) & (self.estado[j] == VOANDO)
                if not ok.any():
                    continue
                best = np.full(len(i), 99.0)
                dxy = np.zeros((len(i), 2))
                for oa in off:
                    for ob in off:
                        ax = x[i] + oa * np.cos(h[i]); ay = y[i] + oa * np.sin(h[i])
                        bx = x[j] + ob * np.cos(h[j]); by = y[j] + ob * np.sin(h[j])
                        d = np.hypot(ax - bx, ay - by)
                        pior = d < best
                        best = np.where(pior, d, best)
                        dxy = np.where(pior[:, None], np.stack([ax - bx, ay - by], 1), dxy)
                bate = ok & (best < raio)
                if not bate.any():
                    continue
                n = dxy / np.maximum(best, 1e-3)[:, None]
                push = np.where(bate, (raio - best) / 2 + 0.02, 0.0)[:, None] * n
                self.s[i, 0] += push[:, 0]; self.s[i, 1] += push[:, 1]
                self.s[j, 0] -= push[:, 0]; self.s[j, 1] -= push[:, 1]
                # quem vinha de trás perde mais velocidade
                tras_i = self.prog[i] < self.prog[j]
                self.s[i, 3] *= np.where(bate, np.where(tras_i, 0.78, 0.97), 1.0)
                self.s[j, 3] *= np.where(bate, np.where(tras_i, 0.97, 0.78), 1.0)
                self.toques[i] += bate
                self.toques[j] += bate

    def contabiliza_bloqueio(self, vivo):
        """Passos em que o carro da frente se joga na direção de quem vem atrás, colado nele."""
        p = self.prog[self.mates]; o = self.off[self.mates]
        eu = np.arange(self.n)[:, None]
        atras = (self.mates != eu) & (p < self.prog[:, None]) & (self.prog[:, None] - p < 9) & (np.abs(o - self.off[:, None]) < 2.4)
        atras &= self.estado[self.mates] == VOANDO
        tem = atras.any(1)
        k = np.where(atras, self.prog[:, None] - p, 99).argmin(1)
        o_r = o[np.arange(self.n), k]
        e = self.s[:, 4]
        # direção lateral do carro (para a esquerda da pista = off aumenta): ester positivo vira à esquerda
        rumo_lat = np.sin(self.herr) * self.s[:, 3]
        # o rival está à esquerda (o_r > off) e eu me movo para a esquerda (rumo_lat > 0), ou vice-versa
        fecha = tem & vivo & (np.sign(o_r - self.off) * rumo_lat > 0.8)
        self.bloqueio += fecha

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        self.estado[vivo] = FALHA
        self.t_fim[vivo] = t

    def extra(self):
        return np.stack([self.prog, self.off, self.ordem.astype(float)], 1).astype(np.float32)

    def aptidao(self):
        p = np.maximum(self.prog, 0) / COMPRIMENTO                   # voltas andadas
        media = p[self.mates].mean(1)
        f = p + 0.5 * (p - media)                                   # andar longe e à frente dos rivais
        ganhou = self.estado == SUCESSO
        f = f + ganhou * (1.0 + (self.passos - self.t_fim) / self.passos)
        return f - 0.15 * self.bateu_parede

    def metricas(self):
        suc = self.estado == SUCESSO
        return {
            "parede": float(self.bateu_parede.mean()),
            "voltas": float((np.maximum(self.prog, 0) / COMPRIMENTO).mean()),
            "toque": float((self.toques > 0).mean()),
            "ultra": float(self.ultra.mean()),
            "bloqueio": float((self.bloqueio * self.dt).mean()),
            "tempo": float((self.t_fim[suc] * self.dt).min()) if suc.any() else 0.0,
        }

    def chegou_mas_bateu(self):
        return int((self.bateu_parede & (self.prog > 0.7 * VOLTAS * COMPRIMENTO)).sum())
