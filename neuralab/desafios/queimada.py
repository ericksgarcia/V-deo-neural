"""Desafio: queimada de IAs (dois lados: 3 azuis x 3 vermelhas, duas bolas, quadra em pé dividida ao meio).

Mundo 2D visto de cima, em metros. Cada time fica na SUA metade (azul embaixo, vermelho em cima). Cada time começa com uma bola
no chão do próprio lado. Quem encosta numa bola livre da própria metade pega; solta com a saída "arremessar" na direção em que
está olhando. A bola voa reta (alcance limitado); quem é atingido sai. Bola que erra para no chão: se parar na metade do
inimigo, ele pega. Não há "pegar no ar". Vence quem tiver mais jogadores em pé quando o tempo acaba (ou quando o outro time
zera); o resto é empate. Cada lado tem UM cérebro compartilhado pelos três corpos, sem memória.
"""
import numpy as np

LARG, ALT = 10.0, 14.0
MEIO = ALT / 2
RAIO, RB = 0.4, 0.2
HIT, PICK = RAIO + RB, 0.8
V, ACEL, GIRO = 3.8, 16.0, 5.0
VB, ALCANCE = 11.0, 12.0
LIM_ARR = 0.3                        # saída de arremesso acima disso solta a bola
DT, PASSOS = 1 / 20, 600
CAM = (23, 14, 4)
EQUIPE = np.array([0, 0, 0, 1, 1, 1])
LIVRE, SEGURA, VOA = 0, 1, 2


def _ang(x):
    return (x + np.pi) % (2 * np.pi) - np.pi


class Queimada:
    nome = "queimada"

    def __init__(self, n, rng):
        self.n = n
        ar = np.arange(n)
        self.ar = ar
        x = rng.uniform(1.0, LARG - 1.0, (n, 6))
        y = np.where(EQUIPE[None] == 0, rng.uniform(1.0, MEIO - 1.0, (n, 6)), rng.uniform(MEIO + 1.0, ALT - 1.0, (n, 6)))
        self.P = np.stack([x, y], 2)
        self.ang = np.where(EQUIPE[None] == 0, np.pi / 2, -np.pi / 2) + rng.uniform(-0.8, 0.8, (n, 6))
        self.vel = np.zeros((n, 6, 2))
        self.vivo = np.ones((n, 6), bool)
        self.t_morte = np.full((n, 6), -1)
        # bolas: 0 começa no lado azul, 1 no vermelho
        self.bpos = np.stack([np.stack([rng.uniform(1.5, LARG - 1.5, n), rng.uniform(1.5, MEIO - 1.5, n)], 1),
                              np.stack([rng.uniform(1.5, LARG - 1.5, n), rng.uniform(MEIO + 1.5, ALT - 1.5, n)], 1)], 1)
        self.bvel = np.zeros((n, 2, 2))
        self.bst = np.zeros((n, 2), np.int8)
        self.bdono = np.zeros((n, 2), int)           # quem segura (índice 0-5)
        self.btime = np.zeros((n, 2), int)           # time que arremessou
        self.balc = np.zeros((n, 2))
        self.bdmin = np.full((n, 2), 99.0)
        self.ativo = np.ones(n, bool)
        self.t_fim = np.full(n, -1)
        self.t_ult = np.zeros(n, int)
        self.acao = np.zeros((n, 6, 4))
        # medidas por time (n, 2)
        z = lambda: np.zeros((n, 2))
        self.arremessos, self.acertos, self.pegou, self.segura, self.vivo_t, self.mira, self.recuo = z(), z(), z(), z(), z(), z(), z()

    # ---------------------------------------------------------------- observação
    def _segurando(self):
        h = np.zeros((self.n, 6), bool)
        for b in range(2):
            r = np.where(self.bst[:, b] == SEGURA)[0]
            h[r, self.bdono[r, b]] = True
        return h

    def obs(self):
        n, P = self.n, self.P
        co, si = np.cos(self.ang), np.sin(self.ang)
        sgn = np.where(EQUIPE == 0, 1.0, -1.0)[None]
        rot = lambda dx, dy: (dx * co[..., None] + dy * si[..., None], -dx * si[..., None] + dy * co[..., None])
        # inimigos mais próximos (vivos)
        rel = P[:, None] - P[:, :, None]                                   # a -> b
        d = np.hypot(rel[..., 0], rel[..., 1])
        inim = (EQUIPE[:, None] != EQUIPE[None, :])[None] & self.vivo[:, None, :]
        de = np.where(inim, d, 99.0)
        o = np.argsort(de, 2)[:, :, :2]
        dd = np.take_along_axis(de, o, 2)
        r2 = np.take_along_axis(rel, o[..., None], 2)                       # (n,6,2,2)
        bx, by = r2[..., 0] * co[..., None] + r2[..., 1] * si[..., None], -r2[..., 0] * si[..., None] + r2[..., 1] * co[..., None]
        tem = dd < 98
        segura = self._segurando()
        seg2 = np.take_along_axis(np.broadcast_to(segura[:, None, :], (n, 6, 6)), o, 2)
        e = np.stack([np.where(tem, bx / 10, 0), np.where(tem, by / 10, 0), tem * (seg2 + 1.0) / 2], -1)    # (n,6,2,3)
        # bola inimiga voando (a mais próxima) e bola livre na própria metade (a mais próxima)
        bd = np.hypot(self.bpos[:, None, :, 0] - P[:, :, None, 0], self.bpos[:, None, :, 1] - P[:, :, None, 1])   # (n,6,2)
        voa_in = (self.bst[:, None, :] == VOA) & (self.btime[:, None, :] != EQUIPE[None, :, None])
        k = np.where(voa_in, bd, 99.0).argmin(2)
        ix = (np.arange(n)[:, None], np.arange(6)[None], k)
        tv = voa_in[ix]
        rx, ry = self.bpos[..., 0][np.arange(n)[:, None], k] - P[..., 0], self.bpos[..., 1][np.arange(n)[:, None], k] - P[..., 1]
        vx, vy = self.bvel[..., 0][np.arange(n)[:, None], k], self.bvel[..., 1][np.arange(n)[:, None], k]
        fx, fy = rx * co + ry * si, -rx * si + ry * co
        gx, gy = vx * co + vy * si, -vx * si + vy * co
        voando = np.stack([np.where(tv, fx / 10, 0), np.where(tv, fy / 10, 0), np.where(tv, gx / VB, 0), np.where(tv, gy / VB, 0), tv * 1.0], -1)
        metade = (self.bpos[..., 1] > MEIO).astype(int)                      # (n,2)
        livre_meu = (self.bst[:, None, :] == LIVRE) & (metade[:, None, :] == EQUIPE[None, :, None])
        k2 = np.where(livre_meu, bd, 99.0).argmin(2)
        ix2 = (np.arange(n)[:, None], np.arange(6)[None], k2)
        tl = livre_meu[ix2]
        lx, ly = self.bpos[..., 0][np.arange(n)[:, None], k2] - P[..., 0], self.bpos[..., 1][np.arange(n)[:, None], k2] - P[..., 1]
        lbx, lby = lx * co + ly * si, -lx * si + ly * co
        livre = np.stack([np.where(tl, lbx / 10, 0), np.where(tl, lby / 10, 0), tl * 1.0], -1)
        # próprio estado
        vfx, vfy = self.vel[..., 0] * co + self.vel[..., 1] * si, -self.vel[..., 0] * si + self.vel[..., 1] * co
        prof = np.where(EQUIPE[None] == 0, MEIO - P[..., 1], P[..., 1] - MEIO) / MEIO
        na = self.vivo[:, :3].sum(1)[:, None] / 3.0
        nb = self.vivo[:, 3:].sum(1)[:, None] / 3.0
        meus = np.where(EQUIPE[None] == 0, na, nb)
        deles = np.where(EQUIPE[None] == 0, nb, na)
        x = np.concatenate([np.stack([co, sgn * si, vfx / V, vfy / V, (P[..., 0] - LARG / 2) / (LARG / 2), prof, segura * 1.0], -1),
                            e.reshape(n, 6, 6), voando, livre, meus[..., None], deles[..., None]], -1)
        return x.astype(np.float32)           # (n, 6, 25)

    # ---------------------------------------------------------------- passo
    def passo(self, sa, sb, k):
        n, ar = self.n, self.ar
        act0 = self.ativo.copy()
        a = np.concatenate([sa, sb], 1)
        self.acao = a
        act = act0[:, None] & self.vivo
        self.ang = _ang(self.ang + np.where(act, a[..., 2] * GIRO * DT, 0.0))
        co, si = np.cos(self.ang), np.sin(self.ang)
        ac = ACEL * (a[..., 0:1] * np.stack([co, si], -1) + a[..., 1:2] * np.stack([-si, co], -1))
        v = self.vel + ac * DT - 0.9 * self.vel * DT
        sp = np.hypot(v[..., 0], v[..., 1])
        v = v * np.minimum(1.0, V / np.maximum(sp, 1e-6))[..., None]
        v[~act] = 0.0
        self.vel = v
        self.P = self.P + v * DT
        lo = np.where(EQUIPE[None] == 0, RAIO, MEIO + RAIO)
        hi = np.where(EQUIPE[None] == 0, MEIO - RAIO, ALT - RAIO)
        for ax, l, h in ((0, RAIO, LARG - RAIO), (1, lo, hi)):
            baixo, alto = self.P[..., ax] < l, self.P[..., ax] > h
            self.P[..., ax] = np.where(baixo, l, np.where(alto, h, self.P[..., ax]))
            self.vel[..., ax] = np.where(baixo | alto, 0.0, self.vel[..., ax])
        # pegar bola livre (na própria metade)
        seg = self._segurando()
        for b in range(2):
            livre = (self.bst[:, b] == LIVRE) & act0
            dd = np.hypot(self.P[..., 0] - self.bpos[:, b, None, 0], self.P[..., 1] - self.bpos[:, b, None, 1])
            met = int(0) + (self.bpos[:, b, 1] > MEIO).astype(int)
            ok = act & ~seg & (dd < PICK) & (EQUIPE[None] == met[:, None]) & livre[:, None]
            r = np.where(ok.any(1))[0]
            if len(r):
                who = np.where(ok, dd, 99.0).argmin(1)[r]
                self.bst[r, b] = SEGURA
                self.bdono[r, b] = who
                seg[r, who] = True
                self.pegou[r, EQUIPE[who]] += 1
        # arremessar / carregar
        for b in range(2):
            r = np.where((self.bst[:, b] == SEGURA) & act0)[0]
            if not len(r):
                continue
            h = self.bdono[r, b]
            ha = self.ang[r, h]
            dire = np.stack([np.cos(ha), np.sin(ha)], 1)
            hp = self.P[r, h]
            quer = (a[r, h, 3] > LIM_ARR) & act[r, h]
            self.bpos[r, b] = hp + 0.5 * dire
            rl = r[quer]
            if len(rl):
                dl = dire[quer]
                self.bst[rl, b] = VOA
                self.bpos[rl, b] = hp[quer] + 0.55 * dl
                self.bvel[rl, b] = VB * dl
                self.btime[rl, b] = EQUIPE[h[quer]]
                self.balc[rl, b] = ALCANCE
                self.bdmin[rl, b] = 99.0
                self.arremessos[rl, EQUIPE[h[quer]]] += 1
        # voo (2 microssteps para não atravessar ninguém)
        for _ in range(2):
            for b in range(2):
                fly = (self.bst[:, b] == VOA) & act0
                if not fly.any():
                    continue
                self.bpos[:, b] += np.where(fly[:, None], self.bvel[:, b] * DT / 2, 0.0)
                self.balc[:, b] -= np.where(fly, VB * DT / 2, 0.0)
                mask = (EQUIPE[None] != self.btime[:, b, None]) & self.vivo
                dd = np.hypot(self.P[..., 0] - self.bpos[:, b, None, 0], self.P[..., 1] - self.bpos[:, b, None, 1])
                de = np.where(mask, dd, 99.0)
                self.bdmin[:, b] = np.where(fly, np.minimum(self.bdmin[:, b], de.min(1)), self.bdmin[:, b])
                bate = fly & (de.min(1) < HIT)
                r = np.where(bate)[0]
                if len(r):
                    vit = de.argmin(1)[r]
                    self.vivo[r, vit] = False
                    self.t_morte[r, vit] = k
                    self.acertos[r, self.btime[r, b]] += 1
                    self.vel[r, vit] = 0.0
                    self.bst[r, b] = LIVRE
                    self.bvel[r, b] = 0.0
                    self.mira[r, self.btime[r, b]] += np.exp(-self.bdmin[r, b] / 1.5)
                p = self.bpos[:, b]
                fora = fly & ~bate & ((p[:, 0] < 0) | (p[:, 0] > LARG) | (p[:, 1] < 0) | (p[:, 1] > ALT))
                fim = fly & ~bate & (self.balc[:, b] <= 0)
                for m in (fora, fim):
                    r = np.where(m)[0]
                    if len(r):
                        self.bpos[r, b] = np.clip(self.bpos[r, b], [0.15, 0.15], [LARG - 0.15, ALT - 0.15])
                        self.bst[r, b] = LIVRE
                        self.bvel[r, b] = 0.0
                        self.mira[r, self.btime[r, b]] += np.exp(-self.bdmin[r, b] / 1.5)
        # dono da bola morreu: solta
        for b in range(2):
            r = np.where((self.bst[:, b] == SEGURA) & ~self.vivo[ar, self.bdono[:, b]])[0]
            if len(r):
                self.bst[r, b] = LIVRE
        # medidas
        for t in range(2):
            self.vivo_t[:, t] += np.where(act0, self.vivo[:, 3 * t:3 * t + 3].sum(1), 0)
            quem = np.zeros(n, bool)
            for b in range(2):
                quem |= (self.bst[:, b] == SEGURA) & (EQUIPE[self.bdono[:, b]] == t)
            self.segura[:, t] += act0 & quem
        costas = np.where(EQUIPE[None] == 0, self.P[..., 1] < MEIO * 0.5, self.P[..., 1] > MEIO * 1.5) & self.vivo
        self.recuo[:, 0] += np.where(act0, costas[:, :3].sum(1), 0)
        self.recuo[:, 1] += np.where(act0, costas[:, 3:].sum(1), 0)
        na, nb = self.vivo[:, :3].sum(1), self.vivo[:, 3:].sum(1)
        fim = act0 & ((na == 0) | (nb == 0))
        self.t_fim = np.where(fim, k, self.t_fim)
        self.t_ult = np.where(act0, k, self.t_ult)
        self.ativo = act0 & ~fim

    def acabou(self):
        return not self.ativo.any()

    def finaliza(self, k):
        pass

    # ---------------------------------------------------------------- resultado
    def placar(self):
        """(n,2): jogadores em pé de cada time."""
        return np.stack([self.vivo[:, :3].sum(1), self.vivo[:, 3:].sum(1)], 1)

    def aptidoes(self):
        """(azul, vermelho) por partida."""
        pl = self.placar()
        out = []
        for t in range(2):
            eu, el = pl[:, t], pl[:, 1 - t]
            vit = (eu > el).astype(float)
            f = (3.0 * (3 - el) - 1.0 * (3 - eu) + 2.0 * vit + 0.35 * np.minimum(self.pegou[:, t], 2)
                 + 0.4 * np.minimum(self.mira[:, t], 3) + 1.0 * self.vivo_t[:, t] / (3 * PASSOS))
            out.append(f)
        return out[0], out[1]
