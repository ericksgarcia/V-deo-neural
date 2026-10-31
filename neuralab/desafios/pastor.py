"""Desafio: Cão Pastor. 1 cão (IA) leva 15 ovelhas ao curral, no alto da arena em pé (14 x 22 m).

As ovelhas são PROGRAMADAS (fogem do cão, tendem a ficar juntas, não se encostam) e o curral tem 3 paredes. Só o cérebro do cão evolui.
Ninguém recebe a regra de "ir por trás", "dar a volta" ou "ficar longe": o cão vê o rebanho, a ovelha mais afastada, o curral e a
ovelha mais perto. Nota = ovelhas dentro do curral no fim + um pouco por aproximar o rebanho da entrada (recompensa guiada).
"""
import numpy as np

LARG, ALT = 14.0, 22.0
N = 15                                     # ovelhas por cidade
RAIO_C, RAIO_O = 0.35, 0.3
V_CAO, ACEL = 3.6, 14.0
V_OV, R_FUGA = 2.2, 4.5
DT, PASSOS = 1 / 15, 420                   # 28 s
PX0, PX1, PY0 = 4.5, 9.5, 17.5             # curral: paredes em x=4.5 e 9.5, de y=17.5 até o topo
ENTR = (7.0, PY0)
PAREDE = 0.12
CAMADAS = (16, 12, 2)


class Cidade:
    nome = "pastor"
    camadas = CAMADAS
    dt, passos = DT, PASSOS

    def __init__(self, n, rng):
        self.n = n
        u = rng.normal(0.0, 1.0, (n, N, 2))
        cx = rng.uniform(4.0, 10.0, n)
        cy = rng.uniform(4.0, 8.0, n)
        self.o = np.stack([cx[:, None] + 0.9 * u[..., 0], cy[:, None] + 0.9 * u[..., 1]], -1).clip(0.6, [LARG - 0.6, ALT - 0.6]).astype(np.float32)
        self.vo = np.zeros((n, N, 2), np.float32)
        self.c = np.stack([rng.uniform(2.0, 12.0, n), np.full(n, 1.0)], -1).astype(np.float32)
        self.vc = np.zeros((n, 2), np.float32)
        self.rng = np.random.default_rng(int(rng.integers(1 << 30)))
        self.k = 0
        self.d0 = np.hypot(self.o[..., 0] - ENTR[0], self.o[..., 1] - ENTR[1]).mean(1)
        self.s_atras = np.zeros(n)
        self.s_dist = np.zeros(n)
        self.s_perto = np.zeros(n)
        self.s_aberto = np.zeros(n)
        self.s_pen = np.zeros(n)
        self.s_fora = np.zeros(n)

    def dentro(self, o=None):
        o = self.o if o is None else o
        return (o[..., 0] > PX0 + 0.1) & (o[..., 0] < PX1 - 0.1) & (o[..., 1] > PY0 + 0.3)

    def observa(self):
        n, o, c = self.n, self.o, self.c
        din = self.dentro()
        fora = ~din
        nf = np.maximum(fora.sum(1), 1)
        cent = (o * fora[..., None]).sum(1) / nf[:, None]
        cent = np.where((fora.sum(1) > 0)[:, None], cent, np.array(ENTR, np.float32))
        d_oc = np.hypot(o[..., 0] - c[:, None, 0], o[..., 1] - c[:, None, 1])
        d_cent = np.hypot(o[..., 0] - cent[:, None, 0], o[..., 1] - cent[:, None, 1])
        d_cent = np.where(fora, d_cent, -1.0)
        j_long = d_cent.argmax(1)
        lin = np.arange(n)
        longe = o[lin, j_long]
        d_perto = np.where(fora, d_oc, 1e9)
        j_p = d_perto.argmin(1)
        perto = o[lin, j_p]
        esp = np.where(fora, d_cent, 0).sum(1) / nf
        ent = np.array(ENTR, np.float32)
        obs = np.concatenate([
            ((c[:, 0] - LARG / 2) / (LARG / 2))[:, None], ((c[:, 1] - 11.0) / 11.0)[:, None], self.vc / V_CAO,
            np.clip((cent - c) / 10.0, -1, 1), np.clip((longe - c) / 10.0, -1, 1),
            np.clip((ent - c) / 10.0, -1, 1), np.clip((ent - cent) / 10.0, -1, 1),
            np.clip((perto - c) / 5.0, -1, 1), din.mean(1)[:, None], np.clip(esp / 3.0, 0, 1)[:, None]], -1)
        # métricas
        ativo = fora.sum(1) > 0
        ao_pen = ent - cent
        atras = (((c - cent) * ao_pen).sum(1) < 0) & ativo
        self.s_atras += atras
        self.s_dist += np.hypot(*(cent - c).T) * ativo
        self.s_perto += (np.where(fora, d_oc, 9).min(1) < 1.6) & ativo
        self.s_fora += ativo
        self.s_pen += din.mean(1)
        self.s_esp = esp
        return obs.astype(np.float32)

    def _paredes(self, p, r):
        for x in (PX0, PX1):
            ox = (PAREDE + r) - np.abs(p[..., 0] - x)
            oy_in = p[..., 1] > PY0 - 0.05
            dentro = (ox > 0) & oy_in
            p[..., 0] = np.where(dentro, p[..., 0] + np.sign(p[..., 0] - x + 1e-6) * ox, p[..., 0])
        return p

    def passo(self, acao):
        n, o, c = self.n, self.o, self.c
        # cão
        v = self.vc + acao * ACEL * DT - 0.9 * self.vc * DT
        vel = np.hypot(v[:, 0], v[:, 1])[:, None]
        v = v * np.minimum(1.0, V_CAO / np.maximum(vel, 1e-6))
        c = c + v * DT
        c = self._paredes(c, RAIO_C)
        for ax, lim in ((0, LARG), (1, ALT)):
            b, a = c[:, ax] < RAIO_C, c[:, ax] > lim - RAIO_C
            c[:, ax] = np.where(b, RAIO_C, np.where(a, lim - RAIO_C, c[:, ax]))
            v[:, ax] = np.where(b | a, 0.0, v[:, ax])
        # ovelhas
        din = self.dentro()
        dx, dy = o[..., 0] - c[:, None, 0], o[..., 1] - c[:, None, 1]
        d = np.maximum(np.hypot(dx, dy), 1e-3)
        fuga = np.clip(1.0 - d / R_FUGA, 0, 1)[..., None] * (np.stack([dx, dy], -1) / d[..., None]) * 2.2 * V_OV
        cent = o.mean(1, keepdims=True)
        coes = (cent - o)
        dc = np.maximum(np.hypot(coes[..., 0], coes[..., 1]), 1e-3)[..., None]
        coes = coes / dc * np.clip(dc - 1.5, 0, 3) * 0.25
        ex = o[:, None, :, 0] - o[:, :, None, 0]
        ey = o[:, None, :, 1] - o[:, :, None, 1]
        dd = np.hypot(ex, ey) + np.eye(N)[None] * 1e9
        w = np.clip(1.0 - dd / 0.9, 0, 1) / np.maximum(dd, 1e-3)
        sep = -np.stack([(w * ex).sum(2), (w * ey).sum(2)], -1) * 1.0
        ruido = self.rng.normal(0, 0.25, o.shape).astype(np.float32)
        des = fuga + coes + sep + ruido
        vel_d = np.hypot(des[..., 0], des[..., 1])[..., None]
        des = des * np.minimum(1.0, V_OV / np.maximum(vel_d, 1e-6))
        vo = self.vo + (des - self.vo) * min(1.0, 5.0 * DT)
        o = o + vo * DT
        o = self._paredes(o, RAIO_O)
        for ax, lim in ((0, LARG), (1, ALT)):
            b, a = o[..., ax] < RAIO_O, o[..., ax] > lim - RAIO_O
            o[..., ax] = np.where(b, RAIO_O, np.where(a, lim - RAIO_O, o[..., ax]))
            vo[..., ax] = np.where(b | a, 0.0, vo[..., ax])
        self.o, self.vo, self.c, self.vc = o.astype(np.float32), vo.astype(np.float32), c.astype(np.float32), v.astype(np.float32)
        self.k += 1

    def acabou(self):
        return False

    def finaliza(self):
        pass

    def aptidoes(self):
        din = self.dentro().mean(1)
        d = np.hypot(self.o[..., 0] - ENTR[0], self.o[..., 1] - ENTR[1]).mean(1)
        prog = np.clip(1.0 - d / self.d0, 0, 1)
        return din + 0.4 * prog + 0.3 * self.s_pen / max(self.k, 1)
