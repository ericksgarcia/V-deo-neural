"""Desafio: Paciente Zero. Uma cidade de IAs saudáveis, um vírus e dois cérebros que evoluem juntos.

Mundo 2D visto de cima, em metros. Cada partida é uma cidade com `A` agentes: um começa infectado (paciente zero).
Encostar num infectado contagia na hora. Todos os saudáveis de uma cidade usam o MESMO cérebro saudável e todos os
infectados usam o MESMO cérebro infectado (quem se contagia troca de cérebro). Ninguém recebe regra programada:
nem "fugir", nem "manter distância", nem "perseguir". O saudável é nota pelo tempo que a cidade segue saudável;
o vírus, pelo contrário.
"""
import os

import numpy as np

LARG, ALT = 22.0, 18.0
A = int(os.environ.get("PAC_A", 80))                                     # agentes por cidade (1 paciente zero + 79 saudáveis)
RAIO, CONTAGIO = 0.25, 0.8
RAIO_CORPO = 0.35
V_SAU, V_INF, ACEL = 3.0, float(os.environ.get("PAC_VINF", 3.3)), 12.0
DT, PASSOS = 1 / 15, 450                   # 30 s de cidade
R_VIZ, R_LOCAL = 8.0, 5.0
CAMADAS = (18, 12, 2)
PERTO_PAREDE = 2.5


class Cidade:
    nome = "paciente"
    camadas = CAMADAS
    dt, passos = DT, PASSOS

    def __init__(self, n, rng):
        self.n = n
        u = rng.uniform(0.0, 1.0, (n, A, 2))                # sorteio único: as n primeiras cidades não dependem de n
        self.p = (1.0 + u * [LARG - 2.0, ALT - 2.0]).astype(np.float32)
        self.v = np.zeros((n, A, 2), np.float32)
        self.inf = np.zeros((n, A), bool)
        self.inf[:, 0] = True                              # o paciente zero
        self.t_inf = np.full((n, A), -1, np.int32)
        self.t_inf[:, 0] = 0
        self.k = 0
        # acumuladores das métricas (por cidade)
        self.s_sau = np.zeros(n)                           # soma de (saudáveis) ao longo do tempo
        self.s_nn = np.zeros(n)                            # distância média ao saudável mais perto
        self.s_inf_d = np.zeros(n)                         # distância média ao infectado mais perto
        self.s_par = np.zeros(n)                           # fração de saudáveis perto da parede
        self.s_aglo = np.zeros(n)                          # fração de saudáveis com 3+ saudáveis a menos de 2 m
        self.curva = []                                    # nº de infectados por passo (P,)

    def _d2(self):
        x, y = self.p[..., 0], self.p[..., 1]
        dx = x[:, None, :] - x[:, :, None]                         # (P, A, A): de i para j
        dy = y[:, None, :] - y[:, :, None]
        d2 = dx * dx + dy * dy
        idx = np.arange(A)
        d2[:, idx, idx] = 1e9
        self._d2_atual = d2
        return d2

    def contagia(self, d2):
        """Saudável a menos de CONTAGIO de algum infectado vira infectado (dentro da observação do passo)."""
        perto = (np.where(self.inf[:, None, :], d2, 1e9).min(2) < CONTAGIO ** 2) & ~self.inf
        self.t_inf = np.where(perto, self.k, self.t_inf)
        self.inf = self.inf | perto

    def observa(self):
        d2 = self._d2()
        self.contagia(d2)
        inf = self.inf
        big = 1e9
        w_inf_all, w_sau_all = inf[:, None, :], ~inf[:, None, :]
        d2_inf = np.where(w_inf_all, d2, big)
        d2_sau = np.where(w_sau_all, d2, big)
        j_inf, j_sau = d2_inf.argmin(2), d2_sau.argmin(2)
        lin = np.arange(self.n)[:, None]
        v_inf = np.where((d2_inf.min(2) < big / 2)[..., None], self.p[lin, j_inf] - self.p, 0.0) / R_VIZ
        v_sau = np.where((d2_sau.min(2) < big / 2)[..., None], self.p[lin, j_sau] - self.p, 0.0) / R_VIZ
        viz = d2 < R_LOCAL ** 2
        w_inf = (viz & w_inf_all).astype(np.float32)
        w_sau = (viz & w_sau_all).astype(np.float32)
        n_inf, n_sau = w_inf.sum(2), w_sau.sum(2)
        c_inf = (w_inf @ self.p / np.maximum(n_inf, 1)[..., None] - self.p) * (n_inf > 0)[..., None] / R_LOCAL
        c_sau = (w_sau @ self.p / np.maximum(n_sau, 1)[..., None] - self.p) * (n_sau > 0)[..., None] / R_LOCAL
        x, y = self.p[..., 0], self.p[..., 1]
        paredes = np.stack([x, LARG - x, y, ALT - y], -1)
        obs = np.concatenate([
            np.stack([(x - LARG / 2) / (LARG / 2), (y - ALT / 2) / (ALT / 2)], -1),
            self.v / V_INF,
            np.clip(v_inf, -1, 1), np.clip(v_sau, -1, 1), np.clip(c_inf, -1, 1), np.clip(c_sau, -1, 1),
            np.minimum(n_inf, 5)[..., None] / 5.0, np.minimum(n_sau, 5)[..., None] / 5.0,
            1 - np.clip(paredes / 6.0, 0, 1)], -1)
        # métricas desta passada: só saudáveis contam
        sau = ~inf
        ns = np.maximum(sau.sum(1), 1)
        self.s_sau += sau.sum(1) / (A - 1)
        self.s_nn += (np.sqrt(d2_sau.min(2)).clip(0, 8) * sau).sum(1) / ns
        self.s_inf_d += (np.sqrt(d2_inf.min(2)).clip(0, 12) * sau).sum(1) / ns
        self.s_par += ((paredes.min(-1) < PERTO_PAREDE) & sau).sum(1) / ns
        self.s_aglo += (((d2_sau < 2.0 ** 2).sum(2) >= 3) & sau).sum(1) / ns
        self.curva.append(inf.sum(1))
        return obs.astype(np.float32)

    def passo(self, a_sau, a_inf):
        acao = np.where(self.inf[..., None], a_inf, a_sau)
        vmax = np.where(self.inf, V_INF, V_SAU)[..., None]
        v = self.v + acao * ACEL * DT - 0.9 * self.v * DT
        vel = np.sqrt((v * v).sum(-1, keepdims=True))
        v = v * np.minimum(1.0, vmax / np.maximum(vel, 1e-6))
        p = self.p + v * DT
        # corpos sólidos: quem se sobrepõe é empurrado para fora (ninguém se empilha no mesmo ponto)
        d = np.sqrt(self._d2_atual)
        w = np.maximum(0.0, 2 * RAIO_CORPO - d) / np.maximum(d, 1e-3)
        w = w.astype(np.float32)
        p = p + 0.5 * (p * w.sum(2)[..., None] - w @ p)
        for ax, lim in ((0, LARG), (1, ALT)):
            baixo, alto = p[..., ax] < RAIO, p[..., ax] > lim - RAIO
            p[..., ax] = np.where(baixo, RAIO, np.where(alto, lim - RAIO, p[..., ax]))
            v[..., ax] = np.where(baixo | alto, 0.0, v[..., ax])
        self.p, self.v = p.astype(np.float32), v.astype(np.float32)
        self.k += 1

    def acabou(self):
        return False

    def finaliza(self):
        self.curva = np.array(self.curva).T                # (P, T)

    def aptidoes(self):
        """(saudável, vírus) por cidade: tempo médio de saudáveis na cidade e o contrário."""
        sau = self.s_sau / self.k
        return sau, 1 - sau
