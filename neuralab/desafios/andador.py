"""Desafio: robô bípede aprendendo a andar (vista de lado, física 2D simples).

Corpo = tronco (massa pontual com giro) + duas pernas sem massa (quadril e joelho). O chão empurra
os pés como mola amortecida com atrito; essa força age sobre o tronco. Nenhum passo é programado:
a rede só escolhe o ângulo-alvo de quadril e joelho de cada perna.
"""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

G = 9.8
MASSA, INERCIA = 20.0, 3.0
COXA, CANELA, QUADRIL_ABAIXO = 0.5, 0.5, 0.3
SUB = 4                       # subpassos de física por passo da rede
K_CHAO, C_CHAO, K_ATR, MU = 6000.0, 300.0, 250.0, 0.9
Y_INICIAL, Y_CAIU, TH_CAIU = 1.32, 0.85, 1.15
VJ, F_MAX = 4.0, 600.0       # velocidade máxima das juntas (rad/s) e força máxima de cada pé (N)
META = 14.0                   # metros até a linha de chegada


def pes(x, y, th, a, k):
    """Posição dos dois pés. a, k: (N,2) ângulos de quadril e joelho. -> (N,2,2) [x, y]."""
    qx = x - QUADRIL_ABAIXO * np.sin(th)
    qy = y - QUADRIL_ABAIXO * np.cos(th)
    at = a - th[:, None]
    ac = at - k
    fx = qx[:, None] + COXA * np.sin(at) + CANELA * np.sin(ac)
    fy = qy[:, None] - COXA * np.cos(at) - CANELA * np.cos(ac)
    return np.stack([fx, fy], -1)


class Andador:
    nome = "andador"
    camadas = (11, 12, 4)
    dt = 1 / 30
    passos = 450   # 15 s
    ga = {"elite": 6, "taxa": 0.1, "forca": 0.2}

    def __init__(self, n, rng, ruido=0.3, mu=MU):
        self.n, self.mu = n, mu
        self.x = rng.normal(0, 0.02, n)
        self.y = np.full(n, Y_INICIAL) + rng.normal(0, 0.01 * ruido, n)
        self.th = rng.normal(0, 0.03 * ruido, n)
        self.vx, self.vy, self.w = np.zeros(n), np.zeros(n), np.zeros(n)
        self.a = np.zeros((n, 2)) + rng.normal(0, 0.05 * ruido, (n, 2))
        self.k = np.full((n, 2), 0.15)
        self.pe = pes(self.x, self.y, self.th, self.a, self.k)
        self.toca = np.zeros((n, 2), bool)
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros(n)
        self.caiu_frente = np.zeros(n, bool)
        self.caiu = np.zeros(n, bool)
        self.x_max = np.zeros(n)
        self.vivo_t = np.zeros(n)
        self.rel = np.zeros(n)
        self.pulos = np.zeros(n)            # tempo com os dois pés no ar
        self._c = np.zeros((n, 5))          # somas para a correlação entre os quadris

    @property
    def s(self):
        """Estado gravado por passo: x y th a1 a2 k1 k2 toca1 toca2 (N, 9)."""
        return np.concatenate([np.stack([self.x, self.y, self.th], 1), self.a, self.k, self.toca], 1)

    def observa(self):
        return np.concatenate([
            np.stack([self.th, self.w / 3, (self.y - 1.0) * 2, self.vx / 2, self.vy / 2], 1),
            self.a, self.k - 0.6, self.toca], 1).astype(np.float32)

    def passo(self, saida, t):
        vivo = self.estado == VOANDO
        alvo_a = saida[:, 0:2] * 0.9
        alvo_k = (saida[:, 2:4] + 1) * 0.5 * 1.7
        h = self.dt / SUB
        for _ in range(SUB):
            m = vivo[:, None]
            self.a = np.where(m, self.a + np.clip(alvo_a - self.a, -VJ * h, VJ * h), self.a)
            self.k = np.where(m, self.k + np.clip(alvo_k - self.k, -VJ * h, VJ * h), self.k)
            novo = pes(self.x, self.y, self.th, self.a, self.k)
            vel = (novo - self.pe) / h
            self.pe = novo
            pen = np.maximum(-novo[..., 1], 0)
            fn = np.where(pen > 0, np.minimum(np.maximum(K_CHAO * pen - C_CHAO * vel[..., 1], 0), F_MAX), 0)
            ft = -np.clip(K_ATR * vel[..., 0], -self.mu * fn, self.mu * fn)
            fx, fy = ft.sum(1), fn.sum(1) - MASSA * G
            rx, ry = novo[..., 0] - self.x[:, None], novo[..., 1] - self.y[:, None]
            tq = (rx * fn - ry * ft).sum(1)          # torque anti-horário
            ax, ay, aw = fx / MASSA, fy / MASSA, -tq / INERCIA - 0.8 * self.w
            nvx, nvy, nw = self.vx + ax * h, self.vy + ay * h, self.w + aw * h
            self.vx = np.where(vivo, nvx, self.vx)
            self.vy = np.where(vivo, nvy, self.vy)
            self.w = np.where(vivo, nw, self.w)
            self.x = np.where(vivo, self.x + self.vx * h, self.x)
            self.y = np.where(vivo, self.y + self.vy * h, self.y)
            self.th = np.where(vivo, self.th + self.w * h, self.th)
            self.toca = pen > 0
        self.acel = np.where(vivo, np.abs(saida).mean(1), 0)
        self.x_max = np.maximum(self.x_max, self.x)
        self.vivo_t = np.where(vivo, self.vivo_t + self.dt, self.vivo_t)
        ar = vivo & ~self.toca.any(1)
        self.pulos += ar * self.dt
        c = self._c
        a1, a2 = self.a[:, 0], self.a[:, 1]
        c[vivo] += np.stack([a1, a2, a1 * a1, a2 * a2, a1 * a2], 1)[vivo]
        self.rel = self.rel + vivo

        caiu = vivo & ((self.y < Y_CAIU) | (np.abs(self.th) > TH_CAIU) | ~np.isfinite(self.y))
        self.caiu |= caiu
        self.caiu_frente |= caiu & (self.th > 0)
        self.estado[caiu] = FALHA
        self.t_fim[caiu] = t
        ok = vivo & ~caiu & (self.x >= META)
        self.estado[ok] = SUCESSO
        self.t_fim[ok] = t

    def finaliza(self, t):
        """Quem não caiu nem chegou fica como está (em pé, sem terminar): não conta como queda."""
        self.t_fim[self.estado == VOANDO] = t

    def correlacao(self):
        """Correlação entre os quadris das duas pernas: +1 pernas juntas (pulos), -1 alternadas (passos)."""
        n = np.maximum(self.rel, 1)
        s1, s2, q1, q2, p = (self._c[:, i] for i in range(5))
        cov = p / n - (s1 / n) * (s2 / n)
        v1, v2 = q1 / n - (s1 / n) ** 2, q2 / n - (s2 / n) ** 2
        return np.where((v1 > 1e-4) & (v2 > 1e-4), cov / np.sqrt(np.maximum(v1 * v2, 1e-12)), 0.0)

    def aptidao(self):
        sobe = np.clip(self.x_max, -2, META + 2)
        return sobe + 0.15 * self.vivo_t + (self.estado == SUCESSO) * (6 + 3 * (1 - self.t_fim / self.passos))

    def metricas(self):
        """Números por geração que o roteiro usa para contar a história."""
        apt = self.aptidao()
        topo = np.argsort(-apt)[: max(self.n // 10, 5)]
        corr = self.correlacao()
        anda = self.x_max > 3
        return {
            "dist": float(self.x_max[topo].mean()),                   # metros dos 10% melhores
            "dist_max": float(self.x_max.max()),
            "cai": float(self.caiu.mean()),
            "frente": float(self.caiu_frente[self.caiu].mean()) if self.caiu.any() else 0.0,
            "em_pe": float((~self.caiu).mean()),   # não caíram (ficaram de pé ou chegaram)
            "alt": float((anda & (corr < -0.3)).mean()),               # andaram 3 m+ alternando as pernas
            "junta": float((anda & (corr > 0.5)).mean()),              # andaram 3 m+ com as pernas juntas
            "ar": float(self.pulos[topo].mean() / max(self.vivo_t[topo].mean(), 1e-6)),
        }

    def chegou_mas_bateu(self):
        return int((self.caiu & (self.x_max > 0.5 * META)).sum())
