"""Desafio: Queimada de IAs (dois lados: 3 azuis x 3 vermelhas, uma bola).

Quadra em pé (vista de cima), metros. Azuis na metade de baixo, vermelhas na de cima; ninguém cruza a linha do meio.
Uma bola: quem encosta nela solta/pega. Quem tem a bola decide QUANDO arremessar (a mira é automática no adversário mais
perto, com antecipação do movimento, e o cérebro ainda corrige o ângulo). Bola em voo que toca um adversário o tira da quadra
(vira fantasma). Regra do relógio (escrita à mão): passados `TEMPO` segundos, vence quem tem mais jogadores na quadra.
Cada lado tem UM cérebro compartilhado pelos três corpos.
"""
import numpy as np

LARG, ALT = 10.0, 16.0
MEIO = ALT / 2
R, RB = 0.45, 0.2
V_MAX, ACEL = 4.2, 15.0
V_BOLA = 12.0
DT, TEMPO = 1 / 20, 20.0
PASSOS = int(TEMPO / DT)
NS = 3
CAMADAS = (31, 16, 4)

LIVRE, SEGURA, VOO = 0, 1, 2


def _inverte(p):
    """Espelha o eixo y (o time de cima enxerga a quadra como se fosse o de baixo)."""
    q = p.copy()
    q[..., 1] = ALT - q[..., 1]
    return q


class Queimada:
    nome = "queimada"
    camadas = CAMADAS
    dt, passos = DT, PASSOS

    def __init__(self, n, rng, lento=0.0):
        self.n, self.rng = n, rng
        # lento > 0: currículo (adversários andam mais devagar)
        self.vmax = np.array([V_MAX, V_MAX * (1 - lento)])
        self.p = np.zeros((2, n, NS, 2))
        for t in range(2):
            self.p[t, ..., 0] = rng.uniform(1.5, LARG - 1.5, (n, NS))
            base = rng.uniform(1.5, MEIO - 1.5, (n, NS))
            self.p[t, ..., 1] = base if t == 0 else ALT - base
        self.v = np.zeros((2, n, NS, 2))
        self.vivo = np.ones((2, n, NS), bool)
        ar = np.arange(n)
        self.dono_t = rng.integers(0, 2, n)               # time que começa com a bola
        self.dono_i = rng.integers(0, NS, n)
        self.estado = np.full(n, SEGURA, np.int8)
        self.bp = self.p[self.dono_t, ar, self.dono_i].copy()
        self.bv = np.zeros((n, 2))
        self.lanca_t = np.zeros(n, np.int8)               # quem arremessou a bola em voo
        self.cd = np.zeros((2, n, NS))                    # tempo até poder pegar de novo
        self.acabou_j = np.zeros(n, bool)
        # medidas
        self.arremessos = np.zeros((2, n))
        self.acertos = np.zeros((2, n))
        self.pegadas = np.zeros((2, n))
        self.seg_passos = np.zeros((2, n))                # passos segurando a bola
        self.seg_lider = np.zeros((2, n))                 # passos segurando a bola ESTANDO na frente
        self.lider_passos = np.zeros((2, n))
        self.arr_lider = np.zeros((2, n))                 # arremessos feitos estando na frente
        self.dist_arr = [[], []]
        self.t_primeiro = np.full(n, -1)
        self.t_fim = np.full(n, PASSOS)
        self.passo_k = 0

    # ------------------------------------------------------------ observação
    def obs(self, t):
        n, e = self.n, 1 - t
        flip = t == 1
        P = _inverte(self.p) if flip else self.p
        me, en = P[t], P[e]
        v = self.v[t] * (np.array([1, -1]) if flip else 1)
        bp = _inverte(self.bp) if flip else self.bp
        bv = self.bv * (np.array([1, -1]) if flip else 1)
        vivo_m, vivo_e = self.vivo[t], self.vivo[e]
        tem = (self.estado == SEGURA)[:, None] & (self.dono_t == t)[:, None] & (self.dono_i[:, None] == np.arange(NS))
        mate_seg = (self.estado == SEGURA) & (self.dono_t == t)
        en_seg = (self.estado == SEGURA) & (self.dono_t == e)
        voo = self.estado == VOO
        voo_amea = voo & (self.lanca_t == e)
        voo_meu = voo & (self.lanca_t == t)
        rel_b = (bp[:, None] - me) / 8.0
        # ameaça: bola inimiga em voo
        rel = me - bp[:, None]
        v2 = np.maximum((bv ** 2).sum(1), 1e-6)[:, None]
        tc = np.clip((rel * bv[:, None]).sum(2) / v2, 0, 2.0)
        perp = rel - bv[:, None] * tc[..., None]
        lado = (bv[:, None, 0] * rel[..., 1] - bv[:, None, 1] * rel[..., 0]) / V_BOLA
        amea = voo_amea[:, None]
        # inimigos mais próximos (vivos)
        d = np.hypot(*(en[:, None] - me[:, :, None]).transpose(3, 0, 1, 2))
        d = np.where(vivo_e[:, None, :], d, 99.0)
        o = np.argsort(d, 2)
        ren = np.take_along_axis(en[:, None] - me[:, :, None], o[..., None], 2)
        r1, r2 = ren[:, :, 0] / 10.0, ren[:, :, 1] / 10.0
        r1 = np.where((np.take_along_axis(d, o, 2)[:, :, 0] < 90)[..., None], r1, 0)
        r2 = np.where((np.take_along_axis(d, o, 2)[:, :, 1] < 90)[..., None], r2, 0)
        idx = np.array([[1, 2], [0, 2], [0, 1]])
        mates = (me[:, idx] - me[:, :, None]) / 8.0
        mates_v = vivo_m[:, idx].astype(float)
        mates = mates * mates_v[..., None]
        na, ne = vivo_m.sum(1), vivo_e.sum(1)
        cont = np.stack([na / 3.0, ne / 3.0, (na - ne) / 3.0], 1)
        f = np.concatenate([
            ((me[..., 0] - LARG / 2) / (LARG / 2))[..., None], ((me[..., 1] - MEIO / 2) / (MEIO / 2))[..., None],
            v / V_MAX, tem[..., None].astype(float), rel_b, np.broadcast_to((bv / V_BOLA)[:, None], (n, NS, 2)),
            np.broadcast_to(np.stack([self.estado == LIVRE, mate_seg, en_seg, voo_amea, voo_meu], 1)[:, None].astype(float), (n, NS, 5)),
            (tc / 2.0 * amea)[..., None], (np.clip(lado, -3, 3) / 3 * amea)[..., None], (np.clip(np.hypot(perp[..., 0], perp[..., 1]), 0, 3) / 3 * amea)[..., None],
            r1, r2, mates.reshape(n, NS, -1), mates_v,
            np.broadcast_to(cont[:, None], (n, NS, 3)),
            np.full((n, NS, 1), self.passo_k / PASSOS)], -1)
        return f.astype(np.float32)

    # ------------------------------------------------------------ passo
    def passo(self, sa, sb):
        n, ar = self.n, np.arange(self.n)
        ativo = ~self.acabou_j
        sai = (sa, sb)
        for t in range(2):
            s = sai[t]
            mov = s[..., :2] * (np.array([1, -1]) if t == 1 else 1)
            v = self.v[t] + mov * ACEL * DT - 0.9 * self.v[t] * DT
            sp = np.hypot(v[..., 0], v[..., 1])
            v = v * np.minimum(1.0, self.vmax[t] / np.maximum(sp, 1e-6))[..., None]
            v[~self.vivo[t] | ~ativo[:, None]] = 0
            self.v[t] = v
            self.p[t] = self.p[t] + v * DT
            lo, hi = (R, MEIO - R) if t == 0 else (MEIO + R, ALT - R)
            self.p[t, ..., 0] = np.clip(self.p[t, ..., 0], R, LARG - R)
            self.p[t, ..., 1] = np.clip(self.p[t, ..., 1], lo, hi)
        self.cd = np.maximum(self.cd - DT, 0)
        # corpos se empurram (mesmo time e times diferentes não atravessam: separação simples dentro do time)
        for t in range(2):
            for i in range(NS):
                for j in range(i + 1, NS):
                    d = self.p[t, :, j] - self.p[t, :, i]
                    dist = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)
                    over = np.maximum(2 * R - dist, 0) * (self.vivo[t, :, i] & self.vivo[t, :, j])
                    push = (d / dist[:, None]) * (over / 2)[:, None]
                    self.p[t, :, i] -= push
                    self.p[t, :, j] += push
        # ---- arremesso
        seg = (self.estado == SEGURA) & ativo
        di, dt_ = self.dono_i, self.dono_t
        sd = np.where(dt_[:, None] == 0, sa[ar, di], sb[ar, di])           # (n,4) saída do dono
        quer = seg & (sd[:, 2] > 0.35) & (self.cd[dt_, ar, di] <= 0)
        if quer.any():
            q = np.where(quer)[0]
            tq, iq = dt_[q], di[q]
            orig = self.p[tq, q, iq]
            ini = 1 - tq
            ep = self.p[ini, q]                                              # (m,3,2)
            dd = np.hypot(*(ep - orig[:, None]).transpose(2, 0, 1))
            dd = np.where(self.vivo[ini, q], dd, 99.0)
            j = dd.argmin(1)
            alvo = ep[np.arange(len(q)), j]
            dist = dd[np.arange(len(q)), j]
            vel_al = self.v[ini, q, j]
            tvoo = dist / V_BOLA
            fut = alvo + vel_al * tvoo[:, None] * 0.9
            ang = np.arctan2(fut[:, 1] - orig[:, 1], fut[:, 0] - orig[:, 0])
            ang = ang + sd[q, 3] * 0.45
            self.bp[q] = orig
            self.bv[q] = np.stack([np.cos(ang), np.sin(ang)], 1) * V_BOLA
            self.estado[q] = VOO
            self.lanca_t[q] = tq
            self.cd[tq, q, iq] = 0.6
            self.arremessos[tq, q] += 1
            for t in (0, 1):
                m = tq == t
                if m.any():
                    self.dist_arr[t].extend(dist[m].tolist())
            lid = (self.vivo[tq, q].sum(1) > self.vivo[1 - tq, q].sum(1))
            self.arr_lider[tq, q] += lid
        # ---- bola
        seg = (self.estado == SEGURA) & ativo
        if seg.any():
            self.bp[seg] = self.p[self.dono_t[seg], ar[seg], self.dono_i[seg]]
            self.bv[seg] = 0
        voo = (self.estado == VOO) & ativo
        liv = (self.estado == LIVRE) & ativo
        self.bp[voo | liv] += self.bv[voo | liv] * DT
        fric = np.where(voo, 0.6, 1.8)
        self.bv[voo | liv] *= np.exp(-fric[voo | liv, None] * DT)
        for ax, lim in ((0, LARG), (1, ALT)):
            b = (self.bp[:, ax] < RB) | (self.bp[:, ax] > lim - RB)
            b &= voo | liv
            self.bp[:, ax] = np.clip(self.bp[:, ax], RB, lim - RB)
            self.bv[b, ax] *= -0.6
        vel = np.hypot(self.bv[:, 0], self.bv[:, 1])
        para = voo & (vel < 4.5)
        self.estado[para] = LIVRE
        # o gandula: bola parada é rolada até o jogador vivo mais perto da metade em que ela está
        vel = np.hypot(self.bv[:, 0], self.bv[:, 1])
        parada = (self.estado == LIVRE) & ativo & (vel < 2.0)
        if parada.any():
            metade = (self.bp[:, 1] > MEIO).astype(int)
            w = np.where(parada)[0]
            pos = self.p[metade[w], w]
            d = np.hypot(*(pos - self.bp[w][:, None]).transpose(2, 0, 1))
            d = np.where(self.vivo[metade[w], w], d, 99.0)
            k = d.argmin(1)
            ok = d[np.arange(len(w)), k] < 90
            dirv = pos[np.arange(len(w)), k] - self.bp[w]
            dirv = dirv / np.maximum(np.hypot(dirv[:, 0], dirv[:, 1]), 1e-6)[:, None]
            self.bv[w[ok]] = dirv[ok] * 4.0
        # ---- acerto
        acerto = np.zeros(n, bool)
        if voo.any():
            for t in range(2):
                e = 1 - t
                m = voo & (self.lanca_t == t) & ~acerto
                if not m.any():
                    continue
                d = np.hypot(*(self.p[e] - self.bp[:, None]).transpose(2, 0, 1))
                bate = (d < R + RB) & self.vivo[e] & m[:, None]
                algum = bate.any(1)
                if algum.any():
                    w = np.where(algum)[0]
                    k = np.where(bate[w], -d[w], -1e9).argmax(1)
                    self.vivo[e, w, k] = False
                    self.v[e, w, k] = 0
                    self.acertos[t, w] += 1
                    self.bv[w] *= -0.3
                    self.estado[w] = LIVRE
                    acerto[w] = True
                    nova = (self.t_primeiro[w] < 0)
                    self.t_primeiro[w[nova]] = self.passo_k
                    # quem segurava a bola e foi atingido (não aplicável: só voo)
        # ---- pegar
        liv = (self.estado == LIVRE) & ativo & (np.hypot(self.bv[:, 0], self.bv[:, 1]) < 6.0)
        if liv.any():
            for t in range(2):
                d = np.hypot(*(self.p[t] - self.bp[:, None]).transpose(2, 0, 1))
                ok = (d < R + RB + 0.12) & self.vivo[t] & (self.cd[t] <= 0) & liv[:, None]
                algum = ok.any(1) & (self.estado == LIVRE)
                if algum.any():
                    w = np.where(algum)[0]
                    k = np.where(ok[w], -d[w], -1e9).argmax(1)
                    self.estado[w] = SEGURA
                    self.dono_t[w], self.dono_i[w] = t, k
                    self.pegadas[t, w] += 1
                    self.bv[w] = 0
        # ---- medidas por passo
        seg = (self.estado == SEGURA) & ativo
        na, nb = self.vivo[0].sum(1), self.vivo[1].sum(1)
        for t in range(2):
            m = seg & (self.dono_t == t)
            self.seg_passos[t] += m
            lid = (na > nb) if t == 0 else (nb > na)
            self.lider_passos[t] += lid & ativo
            self.seg_lider[t] += m & lid
        fim = ativo & ((na == 0) | (nb == 0))
        self.t_fim[fim & (self.t_fim == PASSOS)] = self.passo_k
        self.acabou_j |= fim
        self.passo_k += 1

    def acabou(self):
        return bool(self.acabou_j.all())

    def finaliza(self):
        pass

    def vivos(self):
        return self.vivo[0].sum(1), self.vivo[1].sum(1)

    def resultado(self):
        """+1 se o time 0 vence, -1 se o time 1 vence, 0 empate (mais jogadores na quadra no fim)."""
        a, b = self.vivos()
        return np.sign(a - b)

    def aptidoes(self, acerto=1.0):
        """(azul, vermelho) por partida."""
        a, b = self.vivos()
        r = self.resultado()
        tempo = 1 - self.t_fim / PASSOS
        fa = 4 * (r > 0) + 1.2 * (r == 0) + 0.6 * (a - b) / 3 * 1.0 + acerto * 0.8 * self.acertos[0] + 0.5 * np.minimum(self.pegadas[0], 4) + 0.4 * tempo * (r > 0)
        fb = 4 * (r < 0) + 1.2 * (r == 0) + 0.6 * (b - a) / 3 * 1.0 + acerto * 0.8 * self.acertos[1] + 0.5 * np.minimum(self.pegadas[1], 4) + 0.4 * tempo * (r < 0)
        return fa, fb
