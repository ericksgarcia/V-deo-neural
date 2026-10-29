"""Desafio: porta giratória. 16 IAs (o mesmo cérebro em todas) saem da sala da esquerda e precisam chegar à
sala da direita por uma única porta giratória em cruz. A porta não tem motor: ela só gira quando as IAs a
empurram (atrito faz ela parar). Cada "indivíduo" da população é uma sala inteira com 16 IAs.

Mundo em metros; centro da porta em (0, 0). Sucesso = as 16 passam antes do tempo acabar.
"""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

RW = 2.4                    # raio da porta (e do cilindro de vidro)
R_AG = 0.30                 # raio de cada IA
SALA_X, SALA_Y = 10.0, 5.5  # meia-largura de cada sala e meia-altura
X_PASSOU = 3.4              # passou da porta quando x > X_PASSOU
SEN_ARCO = np.sin(np.radians(40.0))   # o cilindro fecha em cima e embaixo (|y|/rho >= sen 40°)
I_PORTA, ATRITO, W_MAX = 3.0, 3.0, 1.6
A_MAX, V_MAX, ARRASTO = 7.0, 2.2, 1.2
K_BLADE, C_BLADE, K_AG, K_PAREDE = 140.0, 12.0, 90.0, 220.0
SUBPASSOS = 2


class Porta:
    nome = "porta"
    camadas = (13, 12, 2)
    dt = 1 / 30
    passos = 600            # 20 s
    n_ag = 16
    ga = {"elite": 8, "taxa": 0.1, "forca": 0.2}

    def __init__(self, n, rng, ruido=1.0, por_mundo=False):
        self.n = n
        N = self.N = self.n_ag
        formato = (n if por_mundo else 1)
        # as 16 IAs começam espalhadas na sala da esquerda (a mesma largada em todos os indivíduos)
        x = -(3.6 + rng.random((formato, N)) * 5.2)
        y = (rng.random((formato, N)) * 2 - 1) * 4.6
        for _ in range(12):     # afasta quem nasceu em cima do outro
            dx = x[:, :, None] - x[:, None, :]
            dy = y[:, :, None] - y[:, None, :]
            d = np.sqrt(dx ** 2 + dy ** 2) + np.eye(N)[None] * 9
            f = np.clip(0.75 - d, 0, None) / d * 0.5
            x = np.clip(x + (f * dx).sum(2), -SALA_X + 0.5, -3.4)
            y = np.clip(y + (f * dy).sum(2), -SALA_Y + 0.5, SALA_Y - 0.5)
        phi0 = np.pi / 4 + ruido * (rng.random(formato) * 2 - 1) * 0.5     # ângulo inicial da porta
        x, y, phi0 = (np.broadcast_to(a, (n,) + a.shape[1:]).copy() for a in (x, y, phi0))
        self.s = np.stack([x, y, np.zeros_like(x), np.zeros_like(x)], -1)      # (P, N, 4): x, y, vx, vy
        self.phi = phi0
        self.w = np.zeros(n)
        self.passou = np.zeros((n, N), bool)
        self.t_passou = np.full((n, N), -1.0)
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros((n, N, 2))
        # métricas
        self.t_trava = np.zeros(n)         # segundos com gente encostada na porta e a porta parada
        self.t_empurra = np.zeros(n)       # segundos com gente empurrando a porta
        self.t_contra = np.zeros(n)        # segundos com empurrões que se anulam (porta parada, muita gente)
        self.por_giro = np.zeros(n)        # quantas IAs passaram por cada sentido
        self.giro_pos = np.zeros(n)
        self.giro_neg = np.zeros(n)
        self.cont = np.zeros(n)            # IAs encostadas na porta (soma no tempo)
        self.n_encostadas = np.zeros(n)

    # ------------------------------------------------------------------ geometria
    def pas(self):
        """Pontas das 4 pás: (P, 4, 2)."""
        ang = self.phi[:, None] + np.arange(4) * np.pi / 2
        return np.stack([np.cos(ang), np.sin(ang)], -1)

    def mais_perto_pa(self, p):
        """Para cada IA (P,N,2): ponto mais perto de qualquer pá (P,N,2) e distância (P,N)."""
        e = self.pas()                                                     # (P,4,2)
        s = np.clip(np.einsum("pnc,pkc->pnk", p, e), 0, RW)               # (P,N,4)
        q = s[..., None] * e[:, None]                                      # (P,N,4,2)
        d = p[:, :, None, :] - q
        dist = np.sqrt((d ** 2).sum(-1)) + 1e-9
        k = dist.argmin(2)
        qk = np.take_along_axis(q, k[:, :, None, None], 2)[:, :, 0]
        return qk, np.take_along_axis(dist, k[:, :, None], 2)[:, :, 0], q, dist

    # ------------------------------------------------------------------ percepção
    def observa(self):
        x, y, vx, vy = (self.s[..., i] for i in range(4))
        p = self.s[..., :2]
        qk, dist, _, _ = self.mais_perto_pa(p)
        dq = np.clip((qk - p) / 3, -1, 1)
        # vizinhos ainda na sala (os 2 mais próximos)
        dx = x[:, None, :] - x[:, :, None]
        dy = y[:, None, :] - y[:, :, None]
        d = np.sqrt(dx ** 2 + dy ** 2) + np.eye(self.N)[None] * 99 + self.passou[:, None, :] * 99
        ordem = np.argsort(d, 2)[..., :2]
        n1x = np.take_along_axis(dx, ordem, 2)
        n1y = np.take_along_axis(dy, ordem, 2)
        ok = np.take_along_axis(d, ordem, 2) < 3.0
        n1x = np.where(ok, n1x / 3, 0.0)
        n1y = np.where(ok, n1y / 3, 0.0)
        w = (self.w / W_MAX)[:, None] * np.ones((1, self.N))
        c4 = np.cos(4 * self.phi)[:, None] * np.ones((1, self.N))
        s4 = np.sin(4 * self.phi)[:, None] * np.ones((1, self.N))
        return np.stack([x / 9, y / SALA_Y, vx / V_MAX, vy / V_MAX, w, c4, s4, dq[..., 0], dq[..., 1],
                         n1x[..., 0], n1y[..., 0], n1x[..., 1], n1y[..., 1]], -1).astype(np.float32)

    # ------------------------------------------------------------------ física
    def passo(self, saida, t):
        vivo = self.estado == VOANDO
        seg = t * self.dt
        a_cmd = np.clip(saida, -1, 1) * A_MAX * (~self.passou)[..., None] * vivo[:, None, None]
        self.acel = np.where(vivo[:, None, None], np.clip(saida, -1, 1), 0.0)
        h = self.dt / SUBPASSOS
        N = self.N
        for _ in range(SUBPASSOS):
            p = self.s[..., :2]
            v = self.s[..., 2:]
            ativa = ~self.passou
            F = a_cmd - ARRASTO * v
            # pás x IAs
            e = self.pas()
            s = np.clip(np.einsum("pnc,pkc->pnk", p, e), 0, RW)
            q = s[..., None] * e[:, None]                                      # (P,N,4,2)
            d = p[:, :, None, :] - q
            dist = np.sqrt((d ** 2).sum(-1)) + 1e-9
            pen = np.clip(R_AG + 0.07 - dist, 0, None) * ativa[..., None]      # (P,N,4)
            n = d / dist[..., None]
            vq = self.w[:, None, None, None] * np.stack([-q[..., 1], q[..., 0]], -1)
            vrel = ((v[:, :, None, :] - vq) * n).sum(-1)
            fn = K_BLADE * pen - C_BLADE * np.minimum(vrel, 0) * (pen > 0)
            fn = np.clip(fn, 0, 60) * (pen > 0)
            Fp = fn[..., None] * n                                              # força na IA (P,N,4,2)
            F = F + Fp.sum(2)
            tau = -(q[..., 0] * Fp[..., 1] - q[..., 1] * Fp[..., 0]).sum((1, 2))   # torque na porta
            # IA x IA
            dx = p[:, :, None, 0] - p[:, None, :, 0]
            dy = p[:, :, None, 1] - p[:, None, :, 1]
            dd = np.sqrt(dx ** 2 + dy ** 2) + np.eye(N)[None] * 99
            pa = np.clip(2 * R_AG - dd, 0, None) * ativa[:, :, None] * ativa[:, None, :]
            fa = K_AG * pa / dd
            F = F + np.stack([(fa * dx).sum(2), (fa * dy).sum(2)], -1)
            # paredes: a divisória x=0 (fora do cilindro) e o cilindro (só fecha em cima e embaixo)
            x, y = p[..., 0], p[..., 1]
            rho = np.sqrt(x ** 2 + y ** 2) + 1e-9
            fora = np.abs(y) > RW
            lado = np.where(x < 0, -1.0, 1.0)
            pw = np.clip(R_AG - np.abs(x), 0, None) * fora * ativa
            F[..., 0] += K_PAREDE * pw * lado
            arco = (np.abs(y) / rho >= SEN_ARCO)
            sa = rho - RW
            pc = np.clip(R_AG + 0.04 - np.abs(sa), 0, None) * arco * ativa
            F += (K_PAREDE * pc * np.sign(sa + 1e-6) / rho)[..., None] * p
            # integra
            v = v + F * h
            sp = np.sqrt((v ** 2).sum(-1, keepdims=True)) + 1e-9
            v = v * np.minimum(1.0, V_MAX / sp)
            p = p + v * h
            p[..., 0] = np.clip(p[..., 0], -SALA_X + R_AG, SALA_X - R_AG)
            p[..., 1] = np.clip(p[..., 1], -SALA_Y + R_AG, SALA_Y - R_AG)
            v = np.where(ativa[..., None], v, 0.0)
            self.s[..., :2], self.s[..., 2:] = p, v
            self.w = np.clip(self.w + (tau - ATRITO * I_PORTA * self.w) / I_PORTA * h, -W_MAX, W_MAX)
            self.phi = self.phi + self.w * h
        # métricas e chegada
        novo = (self.s[..., 0] > X_PASSOU) & ~self.passou & vivo[:, None]
        self.t_passou[novo] = seg
        self.passou |= novo
        self.giro_pos += (novo & (self.w[:, None] > 0.05)).sum(1)
        self.giro_neg += (novo & (self.w[:, None] < -0.05)).sum(1)
        p = self.s[..., :2]
        perto = (np.sqrt((p ** 2).sum(-1)) < RW + 0.6) & ~self.passou
        enc = perto.sum(1)
        parada = np.abs(self.w) < 0.12
        self.cont += enc * self.dt * vivo
        self.t_empurra += (np.abs(self.w) > 0.3) * self.dt * vivo
        self.t_trava += ((enc >= 3) & parada) * self.dt * vivo
        ok = vivo & self.passou.all(1)
        self.estado[ok] = SUCESSO
        self.t_fim[ok] = t

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        self.estado[vivo] = FALHA
        self.t_fim[vivo] = t

    def extra(self):
        return np.stack([self.phi, self.w], -1)

    # ------------------------------------------------------------------ avaliação
    def aptidao(self):
        x = self.s[..., 0]
        prog = np.clip((x + 9.5) / 13.0, 0, 1).mean(1)
        passaram = self.passou.mean(1)
        rapido = np.where(self.estado == SUCESSO, 1 - self.t_fim / self.passos, 0)
        return 3 * passaram + prog + (self.estado == SUCESSO) * (2 + 2 * rapido)

    def metricas(self):
        suc = self.estado == SUCESSO
        return {
            "passaram": float(self.passou.mean()),
            "trava": float(self.t_trava.mean()),                 # s com 3+ IAs na porta e a porta parada
            "gira": float(self.t_empurra.mean()),                # s com a porta girando forte
            "tempo": float((self.t_fim[suc] * self.dt).mean()) if suc.any() else 0.0,
            "sentido": float((np.maximum(self.giro_pos, self.giro_neg) / np.maximum(self.giro_pos + self.giro_neg, 1)).mean()),
        }

    def chegou_mas_bateu(self):
        return int(((self.passou.sum(1) >= 1) & (self.estado == FALHA)).sum())
