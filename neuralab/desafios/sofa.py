"""Desafio: mudança de sofá. Duas IAs presas pelas pontas de um sofá rígido empurram e puxam para passar
por um corredor com uma quina em L. O sofá é um corpo rígido (posição, giro, velocidades); cada ponta aplica
uma força (ao longo do sofá e de lado) e o resto é física: quem puxa para o mesmo lado anda, quem puxa para
lados opostos gira. As duas pontas usam o MESMO cérebro (os mesmos genes), cada uma vendo o mundo da sua
ponta. Cada "indivíduo" da população é um sofá com suas duas pontas.
"""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

COMP, LARG = 3.0, 0.8        # sofá (m)
ARG = 3.1                    # largura do corredor (m)
MEIA = ARG / 2
X_INI, X_QUINA = -11.0, 0.0  # início do corredor horizontal; x do eixo do corredor vertical
Y_TOPO = 11.0                # fim do corredor vertical
Y_META = 8.0                 # o centro do sofá precisa passar daqui, na vertical
COMPR_PROG = (X_QUINA - X_INI) + Y_TOPO   # comprimento do eixo do corredor (m)

# pontos de contato ao longo do contorno do sofá, no referencial dele: (K, 2)
_u = np.linspace(-COMP / 2, COMP / 2, 9)
PONTOS = np.array([(a, b) for a in _u for b in (-LARG / 2, LARG / 2)] +
                  [(-COMP / 2, 0.0), (COMP / 2, 0.0)])


def livre(x, y):
    """True onde (x, y) está dentro do corredor em L (horizontal [X_INI, X_QUINA+MEIA] + vertical para cima)."""
    h = (x >= X_INI) & (x <= X_QUINA + MEIA) & (np.abs(y) <= MEIA)
    v = (np.abs(x - X_QUINA) <= MEIA) & (y >= -MEIA) & (y <= Y_TOPO)
    return h | v


def pontos_mundo(x, y, th):
    """(N,) -> (N, K, 2) pontos do contorno do sofá no mundo."""
    c, s = np.cos(th)[:, None], np.sin(th)[:, None]
    px = x[:, None] + PONTOS[None, :, 0] * c - PONTOS[None, :, 1] * s
    py = y[:, None] + PONTOS[None, :, 0] * s + PONTOS[None, :, 1] * c
    return px, py


def bate_parede(x, y, th):
    px, py = pontos_mundo(x, y, th)
    fora = ~livre(px, py)
    # a quina interna (ponto) pode furar a borda do sofá entre dois pontos de contato
    qx, qy = X_QUINA - MEIA, MEIA
    c, s = np.cos(th), np.sin(th)
    dx, dy = qx - x, qy - y
    lu, lp = dx * c + dy * s, -dx * s + dy * c
    dentro = (np.abs(lu) < COMP / 2) & (np.abs(lp) < LARG / 2)
    return fora.any(1) | dentro


def progresso(x, y):
    """Quanto do eixo do corredor o centro já andou (m)."""
    return np.minimum(x, X_QUINA) - X_INI + np.maximum(y, 0.0)


class Sofa:
    nome = "sofa"
    camadas = (8, 12, 2)
    dt = 1 / 30
    passos = 750             # 25 s
    f_max, massa = 5.0, 1.0
    arrasto, arrasto_ang = 2.5, 5.0
    ga = {"elite": 8, "taxa": 0.12, "forca": 0.2}

    def __init__(self, n, rng, ruido=0.3):
        self.n = n
        self.I = self.massa * (COMP ** 2 + LARG ** 2) / 12
        x = np.full(n, X_INI + COMP / 2 + 0.5) + rng.normal(0, 0.3 * ruido, n)
        y = rng.normal(0, 0.25 * ruido, n)
        th = rng.normal(0, 0.15 * ruido, n)
        self.s = np.stack([x, y, th, np.zeros(n), np.zeros(n), np.zeros(n)], 1)   # x y giro vx vy omega
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros(n)
        self.f = np.zeros((n, 2, 2))        # forças aplicadas em cada ponta, no referencial do sofá (u, p)
        self.bateu = np.zeros(n, bool)
        self.batidas = np.zeros(n)          # nº de passos encostado na parede
        self.prog_max = np.zeros(n)
        self.t_quina = np.full(n, -1.0)     # 1º instante com o centro no meio da quina
        self.contra = np.zeros(n)           # passos em que as duas pontas puxam em sentidos opostos (ao longo do sofá)
        self.gira = np.zeros(n)             # passos girando (|omega| alto)
        self.pivo = np.zeros(n)             # passos girando com uma ponta quase parada e a outra correndo
        self.rebo = np.zeros(n)             # passos andando com uma ponta empurrando e a outra de ré/puxando
        self.vivo_passos = np.zeros(n)
        self.v_curva = np.zeros(n)          # soma da velocidade enquanto o sofá faz a curva (giro entre 20° e 70°)
        self.n_curva = np.zeros(n)

    def pontas(self, x=None, y=None, th=None):
        if x is None:
            x, y, th = self.s[:, 0], self.s[:, 1], self.s[:, 2]
        c, s = np.cos(th), np.sin(th)
        a = np.stack([x - COMP / 2 * c, y - COMP / 2 * s], -1)
        b = np.stack([x + COMP / 2 * c, y + COMP / 2 * s], -1)
        return a, b

    def observa(self):
        x, y, th, vx, vy, om = self.s.T
        c, s = np.cos(th), np.sin(th)
        vu, vp = vx * c + vy * s, -vx * s + vy * c
        base = np.stack([x / 10, y / 10, s, c, vu / 4, vp / 4, om / 5], 1)
        ends = [np.concatenate([base, np.full((self.n, 1), lado)], 1) for lado in (-1.0, 1.0)]
        # a ponta B vê o mundo "de cabeça para baixo": u e p trocam de sinal
        ends[1][:, [4, 5]] *= -1
        ends[1][:, 2] *= -1
        ends[1][:, 3] *= -1
        return np.stack(ends, 1).astype(np.float32)   # (P, 2 pontas, 8)

    def passo(self, saida, t):
        vivo = self.estado == VOANDO
        x, y, th, vx, vy, om = self.s.T.copy()
        f = np.clip(saida, -1, 1) * self.f_max            # (P, 2, 2): [ponta, (u, p)]
        fb = f[:, 1].copy()
        fb[:, 0] *= -1                                      # a ponta B enxerga u e p invertidos
        fb[:, 1] *= -1
        self.f = np.stack([f[:, 0], fb], 1)
        fa, fbb = self.f[:, 0], self.f[:, 1]
        c, s = np.cos(th), np.sin(th)
        # forças no mundo
        fx = (fa[:, 0] + fbb[:, 0]) * c - (fa[:, 1] + fbb[:, 1]) * s
        fy = (fa[:, 0] + fbb[:, 0]) * s + (fa[:, 1] + fbb[:, 1]) * c
        # torque: ponta A em -COMP/2 (alavanca), ponta B em +COMP/2; só a parte perpendicular gira
        tau = (fbb[:, 1] - fa[:, 1]) * COMP / 2
        vx2 = vx + (fx / self.massa - self.arrasto * vx) * self.dt
        vy2 = vy + (fy / self.massa - self.arrasto * vy) * self.dt
        om2 = om + (tau / self.I - self.arrasto_ang * om) * self.dt
        nx, ny, nth = x + vx2 * self.dt, y + vy2 * self.dt, th + om2 * self.dt
        bate = bate_parede(nx, ny, nth) & vivo
        # na batida o sofá fica onde estava e quica um pouco para trás
        nx, ny, nth = np.where(bate, x, nx), np.where(bate, y, ny), np.where(bate, th, nth)
        vx2, vy2, om2 = np.where(bate, -0.25 * vx2, vx2), np.where(bate, -0.25 * vy2, vy2), np.where(bate, -0.25 * om2, om2)
        novo = np.stack([nx, ny, nth, vx2, vy2, om2], 1)
        self.s[vivo] = novo[vivo]
        self.acel = np.where(vivo, np.hypot(fx, fy) / (2 * self.f_max), 0)
        self.bateu |= bate
        self.batidas += bate
        x, y, th = self.s[:, 0], self.s[:, 1], self.s[:, 2]
        pr = progresso(x, y)
        self.prog_max = np.where(vivo, np.maximum(self.prog_max, pr), self.prog_max)
        naquina = vivo & (self.t_quina < 0) & (pr >= (X_QUINA - X_INI) - 0.5)
        self.t_quina[naquina] = t * self.dt
        # métricas de comportamento
        self.vivo_passos += vivo
        self.contra += vivo & (fa[:, 0] * fbb[:, 0] < -0.8)
        om_ = np.abs(self.s[:, 5])
        girando = vivo & (om_ > 0.8)
        self.gira += girando
        ca, cb = np.cos(th), np.sin(th)
        a, b = self.pontas()
        # velocidade de cada ponta
        va = np.hypot(self.s[:, 3] + self.s[:, 5] * (COMP / 2) * cb, self.s[:, 4] - self.s[:, 5] * (COMP / 2) * ca)
        vb = np.hypot(self.s[:, 3] - self.s[:, 5] * (COMP / 2) * cb, self.s[:, 4] + self.s[:, 5] * (COMP / 2) * ca)
        lento, rapido = np.minimum(va, vb), np.maximum(va, vb)
        self.pivo += girando & (rapido > 1.0) & (lento < 0.3 * rapido)
        self.rebo += vivo & (np.hypot(self.s[:, 3], self.s[:, 4]) > 0.8) & (np.minimum(fa[:, 0], fbb[:, 0]) < -0.4 * self.f_max * 0.5) \
            & (np.maximum(fa[:, 0], fbb[:, 0]) > 0.4 * self.f_max * 0.5)
        meio = vivo & (np.abs(np.sin(th)) > 0.34) & (np.abs(np.sin(th)) < 0.94) & (y > -MEIA)
        self.v_curva += meio * np.hypot(self.s[:, 3], self.s[:, 4])
        self.n_curva += meio
        ok = vivo & (y >= Y_META) & (np.abs(np.sin(th)) > 0.8)
        self.estado[ok] = SUCESSO
        self.t_fim[ok] = t

    def extra(self):
        return self.f.reshape(self.n, 4).copy() / self.f_max   # forças (u, p) de cada ponta, de -1 a 1

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        self.estado[vivo] = FALHA
        self.t_fim[vivo] = t

    def aptidao(self):
        x, y, th = self.s[:, 0], self.s[:, 1], self.s[:, 2]
        prog = np.clip(self.prog_max / COMPR_PROG, 0, 1)
        vert = np.abs(np.sin(th))
        # depois da quina vale ficar na vertical
        apos = np.clip((y - 0.5) / 4, 0, 1)
        rapido = np.where(self.estado == SUCESSO, 1 - self.t_fim / self.passos, 0)
        return 3 * prog + apos * vert - 0.4 * np.minimum(self.batidas / 200, 1) + (self.estado == SUCESSO) * (3 + 2 * rapido)

    def metricas(self):
        suc = self.estado == SUCESSO
        vp = np.maximum(self.vivo_passos, 1)
        return {
            "quina": float((self.t_quina >= 0).mean()),                       # chegaram à quina
            "bateu": float(self.batidas.mean() * self.dt),                    # segundos médios encostado na parede
            "tempo": float((self.t_fim[suc] * self.dt).mean()) if suc.any() else 0.0,
            "prog": float(np.clip(self.prog_max / COMPR_PROG, 0, 1).mean()),
            "contra": float((self.contra / vp).mean()),                       # fração do tempo em cabo de guerra
            "gira": float((self.gira / vp).mean()),
            "pivo": float((self.pivo / vp).mean()),
            "rebo": float((self.rebo / vp).mean()),
            "curva": float((self.v_curva.sum() / max(self.n_curva.sum(), 1))),        # velocidade média (m/s) na curva
            "fez_curva": float((self.n_curva > 0).mean()),
        }

    def chegou_mas_bateu(self):
        return int(((self.t_quina >= 0) & (self.estado != SUCESSO)).sum())
