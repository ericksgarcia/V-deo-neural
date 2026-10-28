"""Desafio de dois lados: SUMÔ de IAs (A x B) numa arena redonda. Perde quem sair da arena.

Nada aqui codifica "truques". Cada lutador só controla uma aceleração (para fora/dentro e de lado, em
relação ao centro da arena) e um impulso curto (arrancada) com tempo de recarga. Empurrar, esperar,
desviar no último segundo... ou surgem do treino ou não surgem.

Unidades: metros e segundos. Arena de raio 4 m, lutadores de raio 0,5 m.
"""
import numpy as np

ARENA = 4.0
RAIO = 0.5
DT = 1 / 30
PASSOS = 240            # 8 s de luta
ENCOLHE_DE, ENCOLHE_ATE, ARENA_MIN = 2.0, 6.0, 1.4   # a arena fecha: a luta não pode travar
ACEL = 11.0
ATRITO = 0.8
VMAX = 7.0
ARRANCADA = 5.0         # m/s somados à velocidade
RECARGA = 1.4           # s
REST = 0.55             # elasticidade do choque
LARGADA = 2.2           # distância de cada um ao centro

EM_JOGO, VENCE_A, VENCE_B, EMPATE = 0, 1, 2, 3


class Sumo:
    nome = "sumo"
    camadas = (9, 10, 3)   # -> aceleração radial, aceleração lateral, arrancada
    dt = DT
    passos = PASSOS

    def __init__(self, n, rng):
        self.n = n
        ang = rng.uniform(0, 2 * np.pi, n)
        u = np.stack([np.cos(ang), np.sin(ang)], 1)
        jit = rng.normal(0, 0.12, (2, n, 2))
        self.pos = np.stack([u * LARGADA, -u * LARGADA]) + jit
        self.vel = np.zeros((2, n, 2))
        self.cd = np.zeros((2, n))
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.t_contato = np.full(n, -1.0)
        self.v_contato = np.zeros(n)
        self.arrancadas = np.zeros((2, n))
        self.vivo_t = np.zeros(n)
        self.v1 = np.zeros((2, n, 2))      # velocidade aos 1,0 s
        self.p1 = np.zeros((2, n, 2))      # posição aos 1,0 s
        self.p2 = np.zeros((2, n, 2))      # posição aos 2,0 s

    def arena(self, t):
        """Raio da arena no instante t: fixo no começo e depois vai fechando."""
        u = min(max((t - ENCOLHE_DE) / (ENCOLHE_ATE - ENCOLHE_DE), 0.0), 1.0)
        return ARENA + (ARENA_MIN - ARENA) * u

    # ---------------------------------------------------------- eixos de cada lutador
    def _eixos(self, k):
        p = self.pos[k]
        d = np.linalg.norm(p, axis=1, keepdims=True)
        er = np.where(d > 1e-6, p / np.maximum(d, 1e-6), np.array([1.0, 0.0]))
        et = np.stack([-er[:, 1], er[:, 0]], 1)
        return er, et, d[:, 0]

    def obs(self, k, t=0.0):
        er, et, d = self._eixos(k)
        A = self.arena(t)
        q = 1 - k
        dp = self.pos[q] - self.pos[k]
        dv = self.vel[q] - self.vel[k]
        pr = lambda v, e: np.sum(v * e, 1)
        return np.stack([d / A, pr(self.vel[k], er) / VMAX, pr(self.vel[k], et) / VMAX,
                         pr(dp, er) / ARENA, pr(dp, et) / ARENA, pr(dv, er) / VMAX, pr(dv, et) / VMAX,
                         (self.cd[k] <= 0) * 1.0, (self.cd[q] <= 0) * 1.0], 1).astype(np.float32)

    # ---------------------------------------------------------- passo
    def passo(self, sa, sb, k):
        t = k * DT
        em = self.estado == EM_JOGO
        for lado, s in ((0, sa), (1, sb)):
            er, et, _ = self._eixos(lado)
            a = s[:, 0:1] * er + s[:, 1:2] * et
            nrm = np.linalg.norm(a, axis=1, keepdims=True)
            a = a / np.maximum(nrm, 1.0)
            quer = (s[:, 2] > 0.5) & (self.cd[lado] <= 0) & em
            dirc = np.where(nrm > 0.15, a / np.maximum(nrm, 1e-6), self.vel[lado] / np.maximum(
                np.linalg.norm(self.vel[lado], axis=1, keepdims=True), 1e-6))
            self.vel[lado] += quer[:, None] * dirc * ARRANCADA
            self.cd[lado] = np.where(quer, RECARGA, np.maximum(self.cd[lado] - DT, 0))
            self.arrancadas[lado] += quer
            self.vel[lado] += (a * ACEL - ATRITO * self.vel[lado]) * DT * em[:, None]
            v = np.linalg.norm(self.vel[lado], axis=1, keepdims=True)
            self.vel[lado] *= np.minimum(1.0, VMAX / np.maximum(v, 1e-6))
            self.pos[lado] += self.vel[lado] * DT * em[:, None]
        if k == 30:
            self.v1, self.p1 = self.vel.copy(), self.pos.copy()
        if k == 60:
            self.p2 = self.pos.copy()
        # choque
        d = self.pos[1] - self.pos[0]
        dist = np.linalg.norm(d, axis=1)
        bate = (dist < 2 * RAIO) & em
        if bate.any():
            n = d / np.maximum(dist, 1e-6)[:, None]
            folga = (2 * RAIO - dist) / 2
            self.pos[0] -= bate[:, None] * n * folga[:, None]
            self.pos[1] += bate[:, None] * n * folga[:, None]
            vn = np.sum((self.vel[0] - self.vel[1]) * n, 1)
            j = np.where(bate & (vn > 0), (1 + REST) * vn / 2, 0.0)
            self.vel[0] -= j[:, None] * n
            self.vel[1] += j[:, None] * n
            novo = bate & (self.t_contato < 0)
            self.t_contato[novo] = t
            self.v_contato[novo] = vn[novo]
        # saída da arena
        A = self.arena(t)
        fora = [np.linalg.norm(self.pos[i], axis=1) > A for i in (0, 1)]
        self.vivo_t[em] = t
        a_fora, b_fora = fora[0] & em, fora[1] & em
        self.estado[a_fora & ~b_fora] = VENCE_B
        self.estado[b_fora & ~a_fora] = VENCE_A
        self.estado[a_fora & b_fora] = EMPATE
        acabou = em & (self.estado != EM_JOGO)
        self.t_fim[acabou] = k

    def tempo_esgotou(self):
        self.estado[self.estado == EM_JOGO] = EMPATE

    def acabou(self):
        return (self.estado != EM_JOGO).all()

    # ---------------------------------------------------------- notas
    def aptidoes(self):
        T = PASSOS * DT
        rapido = 1 - np.clip(self.vivo_t / T, 0, 1)
        sobrev = np.clip(self.vivo_t / T, 0, 1)
        # empate: vale mais quem ficou mais perto do centro que o outro
        da, db = np.linalg.norm(self.pos[0], axis=1), np.linalg.norm(self.pos[1], axis=1)
        ctrl = np.clip((db - da) / ARENA, -1, 1)
        a = np.where(self.estado == VENCE_A, 1.0 + 0.2 * rapido,
                     np.where(self.estado == EMPATE, 0.3 + 0.2 * ctrl, 0.1 * sobrev))
        b = np.where(self.estado == VENCE_B, 1.0 + 0.2 * rapido,
                     np.where(self.estado == EMPATE, 0.3 - 0.2 * ctrl, 0.1 * sobrev))
        return a, b
