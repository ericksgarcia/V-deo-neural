"""Desafio de dois lados: CABO DE GUERRA DE ENXAMES (A x B), vista de cima.

Cada lado é um enxame de 5 robôs controlados pela MESMA rede neural (um cérebro, cinco corpos). No meio há uma
caixa pesada: um robô sozinho quase não a move, quatro ou cinco juntos movem. Vence o enxame que levar a caixa
até a linha do gol do outro. Nada aqui ensina "formação", "cercar" ou "empurrar junto": cada robô só controla a
própria aceleração (x, y) e enxerga a caixa, o time e o adversário mais próximo.

Unidades: metros e segundos. Arena de 8 m x 14 m. O enxame A parte de baixo e leva a caixa para cima.
"""
import numpy as np

W, H = 4.0, 7.0          # meia largura e meia altura da arena
GOL = 4.8                # a caixa passa de |y| = GOL: ponto
K = 5                    # robôs por enxame
M = 2 * K + 1            # corpos: A (0..K-1), B (K..2K-1), caixa (2K)
R_ROBO, R_CAIXA = 0.4, 0.95
MASSA_CAIXA = 15.0
DT = 1 / 30
PASSOS = 450             # 15 s
ACEL = 10.0
ATRITO_ROBO = 0.8
ATRITO_CAIXA = 2.0
VMAX = 5.0
ENCOSTA = R_ROBO + R_CAIXA + 0.15   # distância centro a centro que conta como "encostado"

EM_JOGO, VENCE_A, VENCE_B, EMPATE = 0, 1, 2, 3
RAIOS = np.array([R_ROBO] * (2 * K) + [R_CAIXA])
IMASSA = np.array([1.0] * (2 * K) + [1.0 / MASSA_CAIXA])

PI, PJ = np.triu_indices(M, 1)
SOMA = RAIOS[PI] + RAIOS[PJ]
WI = IMASSA[PI] / (IMASSA[PI] + IMASSA[PJ])      # quem é mais leve se desloca mais
WJ = IMASSA[PJ] / (IMASSA[PI] + IMASSA[PJ])
INC_I = np.zeros((len(PI), M))
INC_I[np.arange(len(PI)), PI] = 1.0
INC_J = np.zeros((len(PI), M))
INC_J[np.arange(len(PI)), PJ] = 1.0


class Cabo:
    nome = "cabo"
    camadas = (14, 10, 2)    # -> aceleração x, aceleração y (no referencial do enxame: +y = rumo ao gol dele)
    dt = DT
    passos = PASSOS

    def __init__(self, n, rng):
        self.n = n
        self.pos = np.zeros((n, M, 2))
        self.vel = np.zeros((n, M, 2))
        xs = np.linspace(-2.8, 2.8, K)
        for i in range(K):
            self.pos[:, i] = np.stack([xs[i] + rng.normal(0, 0.25, n), -4.3 + rng.normal(0, 0.35, n)], 1)
            self.pos[:, K + i] = np.stack([xs[i] + rng.normal(0, 0.25, n), 4.3 + rng.normal(0, 0.35, n)], 1)
        self.pos[:, 2 * K] = rng.normal(0, 0.08, (n, 2))
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.prox = np.zeros((2, n))          # soma de "quão perto da caixa" ao longo do jogo
        self.enc = np.zeros((2, n))           # soma de robôs encostados na caixa
        self.atras = np.zeros((2, n))         # soma de encostados que estão atrás da caixa (lado do próprio enxame)
        self.t_mexeu = np.full(n, -1.0)       # primeira vez que a caixa se afastou 1 m do centro
        self.coesao2 = np.zeros((2, n))       # dispersão do enxame aos 2 s
        self.passos_vivos = np.zeros(n)
        self.enc_pico = np.zeros((2, n))      # pico de robôs encostados na caixa ao mesmo tempo

    # ---------------------------------------------------------- observação (no referencial do enxame)
    def obs(self, lado):
        sg = 1.0 if lado == 0 else -1.0       # B enxerga o mundo espelhado em y
        meus = slice(0, K) if lado == 0 else slice(K, 2 * K)
        deles = slice(K, 2 * K) if lado == 0 else slice(0, K)
        p, v = self.pos[:, meus], self.vel[:, meus]
        cx, cv = self.pos[:, 2 * K][:, None], self.vel[:, 2 * K][:, None]
        f = np.array([1.0, sg])
        rel_caixa = (cx - p) * f / 6.0
        media = (p.sum(1, keepdims=True) - p) / (K - 1)
        rel_time = (media - p) * f / 6.0
        d = np.linalg.norm(self.pos[:, deles][:, None, :, :] - p[:, :, None, :], axis=3)   # (n,K,K)
        j = d.argmin(2)
        viz = np.take_along_axis(self.pos[:, deles][:, None, :, :].repeat(K, 1), j[:, :, None, None], 2)[:, :, 0]
        rel_op = (viz - p) * f / 6.0
        dist_cx = np.linalg.norm(cx - p, axis=2)
        frac = ((dist_cx < ENCOSTA).mean(1, keepdims=True)).repeat(K, 1)
        prog = (sg * self.pos[:, 2 * K, 1] / GOL)[:, None].repeat(K, 1)
        o = np.concatenate([rel_caixa, v * f / VMAX, (cv * f).repeat(K, 1) / 3.0, prog[:, :, None], rel_time, rel_op,
                            (p * f) / np.array([W, H]), frac[:, :, None]], 2)
        return o.astype(np.float32)               # (n, K, 14)

    # ---------------------------------------------------------- passo
    def passo(self, sa, sb, k):
        t = k * DT
        em = (self.estado == EM_JOGO)[:, None, None]
        for lado, s in ((0, sa), (1, sb)):
            sl = slice(0, K) if lado == 0 else slice(K, 2 * K)
            a = s.copy()
            if lado == 1:
                a[:, :, 1] *= -1
            nrm = np.linalg.norm(a, axis=2, keepdims=True)
            a = a / np.maximum(nrm, 1.0)
            self.vel[:, sl] += (a * ACEL - ATRITO_ROBO * self.vel[:, sl]) * DT * em
            v = np.linalg.norm(self.vel[:, sl], axis=2, keepdims=True)
            self.vel[:, sl] *= np.minimum(1.0, VMAX / np.maximum(v, 1e-6))
        self.vel[:, 2 * K] -= ATRITO_CAIXA * self.vel[:, 2 * K] * DT * em[:, 0]
        self.pos += self.vel * DT * em
        for _ in range(2):
            self._colisoes(em)
        self._paredes(em)
        # métricas
        cx = self.pos[:, 2 * K]
        ativo = (self.estado == EM_JOGO)
        self.passos_vivos[ativo] += 1
        if self.t_mexeu is not None:
            novo = ativo & (self.t_mexeu < 0) & (np.linalg.norm(cx, axis=1) > 1.0)
            self.t_mexeu[novo] = t
        for lado in (0, 1):
            sl = slice(0, K) if lado == 0 else slice(K, 2 * K)
            d = np.linalg.norm(self.pos[:, sl] - cx[:, None], axis=2)
            enc = d < ENCOSTA
            atras_ = enc & (((self.pos[:, sl, 1] - cx[:, None, 1]) * (1 if lado == 0 else -1)) < -0.2)
            self.prox[lado] += ativo * np.exp(-d / 2.5).mean(1)
            self.enc[lado] += ativo * enc.sum(1)
            self.atras[lado] += ativo * atras_.sum(1)
            self.enc_pico[lado] = np.maximum(self.enc_pico[lado], ativo * enc.sum(1))
        if k == 60:
            for lado in (0, 1):
                sl = slice(0, K) if lado == 0 else slice(K, 2 * K)
                p = self.pos[:, sl]
                dd = np.linalg.norm(p[:, :, None] - p[:, None], axis=3)
                self.coesao2[lado] = dd.sum((1, 2)) / (K * (K - 1))
        ganhou_a = ativo & (cx[:, 1] >= GOL)
        ganhou_b = ativo & (cx[:, 1] <= -GOL)
        self.estado[ganhou_a] = VENCE_A
        self.estado[ganhou_b & ~ganhou_a] = VENCE_B
        self.t_fim[ativo & (self.estado != EM_JOGO)] = k

    def _colisoes(self, em):
        """Choque entre todos os pares de corpos (só os 55 pares distintos), resolvido de uma vez só."""
        P, V = self.pos, self.vel
        d = P[:, PJ] - P[:, PI]                                   # de i para j
        dist = np.sqrt((d * d).sum(2))
        pen = np.maximum(SOMA - dist, 0.0)
        if not pen.any():
            return
        nrm = d / np.maximum(dist, 1e-6)[..., None]
        P += np.matmul(-INC_I.T, nrm * (pen * WI)[..., None]) * em
        P += np.matmul(INC_J.T, nrm * (pen * WJ)[..., None]) * em
        vrel = ((V[:, PJ] - V[:, PI]) * nrm).sum(2)                # >0 afastando, <0 aproximando
        imp = np.where((pen > 0) & (vrel < 0), -1.1 * vrel / (IMASSA[PI] + IMASSA[PJ]), 0.0)
        V += np.matmul(-INC_I.T, nrm * (imp * IMASSA[PI])[..., None]) * em
        V += np.matmul(INC_J.T, nrm * (imp * IMASSA[PJ])[..., None]) * em

    def _paredes(self, em):
        P, V = self.pos, self.vel
        lim_x = W - RAIOS
        for eixo, lim in ((0, lim_x),):
            acima = P[:, :, eixo] > lim
            abaixo = P[:, :, eixo] < -lim
            P[:, :, eixo] = np.clip(P[:, :, eixo], -lim, lim)
            V[:, :, eixo] = np.where(acima | abaixo, -0.3 * V[:, :, eixo], V[:, :, eixo])
        lim_y = H - RAIOS
        acima = P[:, :, 1] > lim_y
        abaixo = P[:, :, 1] < -lim_y
        P[:, :, 1] = np.clip(P[:, :, 1], -lim_y, lim_y)
        V[:, :, 1] = np.where(acima | abaixo, -0.3 * V[:, :, 1], V[:, :, 1])

    def tempo_esgotou(self):
        self.estado[self.estado == EM_JOGO] = EMPATE

    def acabou(self):
        return (self.estado != EM_JOGO).all()

    # ---------------------------------------------------------- notas
    def aptidoes(self):
        T = PASSOS
        cy = self.pos[:, 2 * K, 1]
        out = []
        for lado, sg in ((0, 1.0), (1, -1.0)):
            prog = np.clip(sg * cy / GOL, -1, 1)
            prox = self.prox[lado] / np.maximum(self.passos_vivos, 1)
            rapido = 1 - np.clip(self.passos_vivos / T, 0, 1)
            venceu = self.estado == (VENCE_A if lado == 0 else VENCE_B)
            out.append(np.where(venceu, 1.0 + 0.3 * rapido, 0.3 + 0.4 * prog + 0.2 * prox))
        return out[0], out[1]
