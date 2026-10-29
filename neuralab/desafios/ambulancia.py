"""Desafio: o dilema da ambulância. Uma avenida de 3 faixas, 24 carros (todos com o MESMO cérebro) e uma ambulância
que vem de trás, mais rápida. A ambulância é programada só para dirigir (escolhe a faixa mais livre e segue o carro da
frente); quem aprende a abrir caminho, ou não, são os carros. Sucesso = a ambulância chega ao fim sem bater.

Mundo 2D visto de cima, em metros: x = distância ao longo da avenida, y = posição lateral (0 a 10,8).
Cada "indivíduo" da população é uma avenida inteira (24 carros, mesmo cérebro). Todas as avenidas de uma geração
começam com o MESMO trânsito, então a comparação entre cérebros é justa.
"""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

FAIXA, N_FAIXAS = 3.6, 3
LARG_VIA = FAIXA * N_FAIXAS
CENTROS = (FAIXA / 2) + FAIXA * np.arange(N_FAIXAS)          # 1,8 / 5,4 / 9,0
COMP, LARG = 4.2, 1.9                                        # carro (m)
COMP_A, LARG_A = 5.4, 2.1                                    # ambulância
FIM = 200.0
V_CARRO, V_AMB, A_CARRO, LAT, LAT_AMB = 14.0, 22.0, 4.0, 6.0, 3.0


class Ambulancia:
    nome = "ambulancia"
    camadas = (8, 10, 2)
    dt = 1 / 20
    passos = 200            # 10 s: o prazo da ambulância
    C = 24
    cenarios = 4            # cada cérebro é avaliado em 4 avenidas diferentes por geração
    ga = {"elite": 6, "taxa": 0.1, "forca": 0.2}

    def __init__(self, n, rng, ruido=1.0, por_mundo=False):
        self.n = n
        C = self.C
        m = n if por_mundo else 1
        lane = np.tile(np.arange(N_FAIXAS), (m, C // N_FAIXAS))               # 8 carros por faixa
        rank = np.repeat(np.arange(C // N_FAIXAS), N_FAIXAS)[None]
        s0 = 22.0 + rank * 20.0 + lane * 6.5 + ruido * rng.uniform(-3, 3, (m, C))   # escalonados: nenhuma faixa livre
        v0 = 10.0 + ruido * rng.uniform(-1.5, 1.5, (m, C))
        y0 = CENTROS[lane] + ruido * rng.uniform(-0.3, 0.3, (m, C))
        self.s = np.broadcast_to(s0, (n, C)).astype(np.float32).copy()
        self.y = np.broadcast_to(y0, (n, C)).astype(np.float32).copy()
        self.vs = np.broadcast_to(v0, (n, C)).astype(np.float32).copy()
        self.vy = np.zeros((n, C), np.float32)
        self.batido = np.zeros((n, C), bool)                                   # carro que bateu (fica parado)
        self.a_s = np.zeros(n, np.float32)                                     # ambulância
        self.a_y = np.full(n, CENTROS[1], np.float32)
        self.a_v = np.full(n, 12.0, np.float32)
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros((n, C), np.float32)
        self.bateu = np.zeros(n, bool)                  # a ambulância bateu
        self.par_bateu = np.full(n, -1)
        self.k = 0
        # medidas
        self.t_lenta = np.zeros(n)                      # tempo da ambulância abaixo de 60% da velocidade
        self.carona = np.zeros((n, C))                  # segundos de cada carro colado atrás da ambulância, rápido
        self.livre = np.zeros((n, C))                   # segundos em que o carro está à frente da ambulância fora da faixa dela
        self.bloqueio = np.zeros((n, C))                # segundos em que o carro está na frente, na faixa da ambulância
        self.min_dist_amb = np.full((n, C), 99.0)

    # ------------------------------------------------------------------ percepção
    def _gaps(self):
        """Distância livre à frente de cada carro (mesma faixa lateral) -> (P, C)."""
        ds = self.s[:, None, :] - self.s[:, :, None]                          # j à frente de i
        dy = np.abs(self.y[:, None, :] - self.y[:, :, None])
        m = (ds > 0) & (dy < LARG + 0.3)
        return np.where(m, ds - COMP, 99.0).min(2)

    def observa(self):
        ds = (self.a_s[:, None] - self.s) / 40.0                               # >0: ambulância atrás do carro? (a - s)
        dy = (self.a_y[:, None] - self.y) / LARG_VIA
        gap = np.clip(self._gaps() / 30.0, 0, 1)
        dyy = self.y[:, None, :] - self.y[:, :, None]
        dss = np.abs(self.s[:, None, :] - self.s[:, :, None])
        perto = (dss < 7.0) & (np.abs(dyy) > 0.5)
        np.einsum("pii->pi", dss)[:] = 99
        esq = ((dyy < 0) & (dss < 7.0) & (np.abs(dyy) < FAIXA * 1.3) & (dss > 0)).any(2)       # alguém a y menor
        dre = ((dyy > 0) & (dss < 7.0) & (np.abs(dyy) < FAIXA * 1.3) & (dss > 0)).any(2)
        o = np.stack([self.y / LARG_VIA * 2 - 1, self.vs / V_CARRO, self.vy / 4.0, np.clip(-ds, -1.5, 1.5),
                      dy, gap, ~esq, ~dre], -1)
        return o.astype(np.float32)

    # ------------------------------------------------------------------ física
    def _controle_ambulancia(self):
        """Faixa mais livre (com histerese) e velocidade que acompanha o carro da frente."""
        d = self.s - self.a_s[:, None]
        ok = ~self.batido | True
        folga = []
        for c in CENTROS:
            m = (d > -COMP) & (np.abs(self.y - c) < LARG / 2 + LARG_A / 2 + 0.2)
            folga.append(np.where(m, d - COMP / 2 - COMP_A / 2, 99.0).min(1))
        folga = np.stack(folga, 1)                                              # (P, 3)
        atual = np.argmin(np.abs(self.a_y[:, None] - CENTROS[None]), 1)
        ganho = folga - folga[np.arange(self.n), atual][:, None] - 6.0 * np.abs(np.arange(N_FAIXAS)[None] - atual[:, None])
        alvo = np.where(ganho.max(1) > 8.0, ganho.argmax(1), atual)
        # velocidade pelo carro à frente na faixa em que a ambulância está
        ya = self.a_y
        m = (d > 0) & (np.abs(self.y - ya[:, None]) < LARG / 2 + LARG_A / 2 + 0.2)
        gap = np.where(m, d - COMP / 2 - COMP_A / 2, 99.0)
        j = gap.argmin(1)
        g = gap[np.arange(self.n), j]
        vf = self.vs[np.arange(self.n), j]
        vt = np.where(g < 60, np.clip(vf + (g - 9.0) * 1.2, 0.0, V_AMB), V_AMB)
        return CENTROS[alvo], vt.astype(np.float32)

    def passo(self, saida, t):
        vivo = self.estado == VOANDO
        dt = self.dt
        # carros
        a = np.clip(saida[..., 0], -1, 1) * A_CARRO
        la = np.clip(saida[..., 1], -1, 1) * LAT
        vs = np.clip(self.vs + a * dt, 0.0, V_CARRO)
        vy = np.clip(self.vy + la * dt - 1.5 * self.vy * dt, -4.0, 4.0)
        ml = vivo[:, None] & ~self.batido
        self.vs, self.vy = np.where(ml, vs, 0.0).astype(np.float32), np.where(ml, vy, 0.0).astype(np.float32)
        self.s = self.s + self.vs * dt
        self.y = self.y + self.vy * dt
        lo, hi = LARG / 2, LARG_VIA - LARG / 2
        enc = (self.y < lo) | (self.y > hi)
        self.y = np.clip(self.y, lo, hi)
        self.vy = np.where(enc, 0.0, self.vy)
        self.acel = np.where(vivo[:, None], saida[..., 0], 0).astype(np.float32)
        # ambulância
        ya, vt = self._controle_ambulancia()
        dv = np.clip(vt - self.a_v, -12.0 * dt, 8.0 * dt)
        self.a_v = np.where(vivo, self.a_v + dv, self.a_v).astype(np.float32)
        self.a_y = np.where(vivo, self.a_y + np.clip(ya - self.a_y, -LAT_AMB * dt, LAT_AMB * dt), self.a_y).astype(np.float32)
        self.a_s = np.where(vivo, self.a_s + self.a_v * dt, self.a_s).astype(np.float32)
        seg = t * dt
        # colisões carro x carro (os dois ficam parados, viram obstáculo)
        dx = np.abs(self.s[:, :, None] - self.s[:, None, :]) < COMP
        dyl = np.abs(self.y[:, :, None] - self.y[:, None, :]) < LARG
        par = dx & dyl & ~np.eye(self.C, dtype=bool)[None]
        self.batido |= par.any(2) & vivo[:, None]
        # colisão ambulância x carro
        bx = np.abs(self.s - self.a_s[:, None]) < (COMP + COMP_A) / 2
        by = np.abs(self.y - self.a_y[:, None]) < (LARG + LARG_A) / 2
        bate_a = bx & by
        bate = vivo & bate_a.any(1)
        self.par_bateu = np.where(bate, bate_a.argmax(1), self.par_bateu)
        self.bateu |= bate
        self.estado[bate] = FALHA
        self.t_fim[bate] = t
        ok = vivo & ~bate & (self.a_s >= FIM)
        self.estado[ok] = SUCESSO
        self.t_fim[ok] = t
        # medidas
        d = self.s - self.a_s[:, None]
        dyc = np.abs(self.y - self.a_y[:, None])
        self.t_lenta += (vivo & (self.a_v < 0.6 * V_AMB)) * dt
        colado = (d < 0) & (d > -14.0) & (dyc < 2.2) & (self.vs > 11.0)
        self.carona += vivo[:, None] * colado * dt
        frente = (d > 0) & (d < 30.0)
        self.bloqueio += vivo[:, None] * (frente & (dyc < 2.2)) * dt
        self.livre += vivo[:, None] * (frente & (dyc >= 2.2)) * dt
        self.min_dist_amb = np.where(vivo[:, None], np.minimum(self.min_dist_amb, np.abs(d)), self.min_dist_amb)
        self.k = t + 1

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        self.estado[vivo] = FALHA
        self.t_fim[vivo] = t

    # ------------------------------------------------------------------ avaliação
    def aptidao(self):
        tempo = np.where(self.estado == SUCESSO, self.t_fim / self.passos, 1.0)
        prog = np.clip(self.a_s / FIM, 0, 1)
        carros = np.clip((self.s - 0) / 250.0, 0, 1).mean(1)
        return (2.5 * (1 - tempo) + 1.5 * prog - 2.0 * self.bateu + 0.6 * carros
                - 1.2 * self.batido.mean(1) + (self.estado == SUCESSO) * 1.0)

    def metricas(self):
        suc = self.estado == SUCESSO
        return {
            "chegou": float(suc.mean()),
            "bateu": float(self.bateu.mean()),
            "tempo": float((self.t_fim[suc] * self.dt).mean()) if suc.any() else self.passos * self.dt,
            "lenta": float(self.t_lenta.mean()),
            "carros_bateram": float(self.batido.mean()),
            "carona": float((self.carona > 1.5).any(1).mean()),
            "livre": float((self.livre.sum(1) / np.maximum(self.livre.sum(1) + self.bloqueio.sum(1), 1e-6)).mean()),
        }

    def extra(self):
        """O que o vídeo precisa gravar a cada passo: carros (x, y, bateu) e ambulância (x, y, v) -> (P, 3C+3)."""
        return np.concatenate([self.s, self.y, self.batido, self.a_s[:, None], self.a_y[:, None], self.a_v[:, None]], 1)

    def chegou_mas_bateu(self):
        return int((self.bateu & (self.a_s > 0.6 * FIM)).sum())
