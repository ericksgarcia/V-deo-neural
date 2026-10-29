"""Desafio: escolta VIP (dois lados: 3 seguranças protegem o VIP, 3 assassinos querem tocá-lo).

Mundo 2D visto de cima, em metros. O VIP é PROGRAMADO: anda em linha reta, devagar, da porta da esquerda até a saída da
direita (ele não decide nada). Quem evolui são os seguranças e os assassinos, cada lado com UM cérebro compartilhado
pelos três corpos. Todos têm a mesma física; segurança tem mais massa (empurra mais do que é empurrado).
"""
import numpy as np

VIVO, CHEGOU, MORTO = 0, 1, 2

LARG, ALT = 24.0, 14.0
VIP0, SAIDA, V_VIP = (2.5, 7.0), 22.0, 1.5
RAIO, TOQUE = 0.4, 0.9
V_SEG, V_ASS, ACEL = 4.2, 4.6, 14.0
M_SEG, M_ASS = 1.6, 1.0
DT, PASSOS = 1 / 20, 280
NS = 3
CAMADAS = (19, 14, 2)


def _ordena(d, rel):
    """Ordena inimigos por distância: devolve (rel dos 2 mais próximos, dist do mais próximo)."""
    o = np.argsort(d, 2)
    r = np.take_along_axis(rel, o[..., None], 2)
    return r[:, :, 0], r[:, :, 1], np.take_along_axis(d, o, 2)[:, :, 0]


class Escolta:
    nome = "escolta"
    camadas = CAMADAS
    dt, passos = DT, PASSOS

    def __init__(self, n, rng, ruido=1.0):
        self.n = n
        self.vip = np.tile(VIP0, (n, 1)).astype(float)
        self.g = np.stack([VIP0[0] + rng.uniform(-1.2, 1.2, (n, NS)) + 0.3 * rng.normal(0, 1, (n, NS)) * ruido,
                           VIP0[1] + rng.uniform(-1.8, 1.8, (n, NS))], 2)
        lado = rng.integers(0, 2, (n, NS))
        self.a = np.stack([rng.uniform(11.0, 21.0, (n, NS)),
                           np.where(lado == 0, rng.uniform(0.8, 3.5, (n, NS)), rng.uniform(10.5, 13.2, (n, NS)))], 2)
        self.vg, self.va = np.zeros((n, NS, 2)), np.zeros((n, NS, 2))
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.min_vip = np.full(n, 99.0)
        self.passos_vivo = np.zeros(n)
        self.escudo = np.zeros(n)          # passos com assassino perto E segurança no caminho
        self.perto = np.zeros(n)           # passos com assassino a menos de 4 m
        self.cola = np.zeros(n)            # soma da distância média segurança-VIP
        self.abre = np.zeros(n)            # passos com assassino perto vindo de lados opostos
        self.contatos = np.zeros(n)        # passos de contato segurança-assassino
        self.bate_parede = np.zeros(n)     # passos de assassino colado na parede com segurança encostado

    # ---- observações (19)
    def _obs(self, p, v, outros_amigos, inimigos, vmax):
        n = self.n
        vip = self.vip[:, None, :]
        parede = np.stack([p[..., 0], LARG - p[..., 0], p[..., 1], ALT - p[..., 1]], -1) / 6.0
        relv = (vip - p) / 8.0
        d_in = np.hypot(*(inimigos[:, None] - p[:, :, None]).transpose(3, 0, 1, 2))     # (n, NS, NS)
        rel_in = (inimigos[:, None] - p[:, :, None]) / 8.0
        r1, r2, dmin = _ordena(d_in, rel_in)
        rel_am = (outros_amigos - p[:, :, None]) / 8.0                                   # (n, NS, NS-1, 2)
        return np.concatenate([(p - [LARG / 2, ALT / 2]) / [LARG / 2, ALT / 2], v / vmax, relv, (dmin / 8.0)[..., None],
                               r1, r2, rel_am.reshape(n, NS, -1), parede], -1).astype(np.float32)

    @staticmethod
    def _amigos(p):
        """(n, NS, NS-1, 2): posição dos dois colegas de cada corpo."""
        idx = np.array([[1, 2], [0, 2], [0, 1]])
        return p[:, idx]

    def obs_seguranca(self):
        return self._obs(self.g, self.vg, self._amigos(self.g), self.a, V_SEG)

    def obs_assassino(self):
        return self._obs(self.a, self.va, self._amigos(self.a), self.g, V_ASS)

    def _separa(self):
        """Colisões círculo-círculo entre os seis corpos (massas diferentes) e com as bordas."""
        pos = np.concatenate([self.g, self.a], 1)
        vel = np.concatenate([self.vg, self.va], 1)
        inv = np.array([1 / M_SEG] * NS + [1 / M_ASS] * NS)
        cont = np.zeros(self.n)
        for i in range(2 * NS):
            for j in range(i + 1, 2 * NS):
                d = pos[:, j] - pos[:, i]
                dist = np.hypot(d[:, 0], d[:, 1])
                over = 2 * RAIO - dist
                m = over > 0
                if not m.any():
                    continue
                nrm = d / np.maximum(dist, 1e-6)[:, None]
                w = inv[i] + inv[j]
                push = (over * m)[:, None] * nrm
                pos[:, i] -= push * (inv[i] / w)
                pos[:, j] += push * (inv[j] / w)
                vn = ((vel[:, j] - vel[:, i]) * nrm).sum(1)
                imp = np.where(m & (vn < 0), -vn * 1.0 / w, 0.0)[:, None] * nrm
                vel[:, i] -= imp * inv[i]
                vel[:, j] += imp * inv[j]
                if i < NS <= j:
                    cont += m
        for ax, lim in ((0, LARG), (1, ALT)):
            baixo, alto = pos[..., ax] < RAIO, pos[..., ax] > lim - RAIO
            pos[..., ax] = np.where(baixo, RAIO, np.where(alto, lim - RAIO, pos[..., ax]))
            vel[..., ax] = np.where(baixo | alto, 0.0, vel[..., ax])
        self.g, self.a = pos[:, :NS], pos[:, NS:]
        self.vg, self.va = vel[:, :NS], vel[:, NS:]
        return cont

    def passo(self, sg, sa, k):
        vivo = self.estado == VIVO
        for nome, vmax in (("g", V_SEG), ("a", V_ASS)):
            p, v, s = getattr(self, nome), getattr(self, "v" + nome), sg if nome == "g" else sa
            v_novo = v + s * ACEL * DT - 0.9 * v * DT
            vel = np.hypot(v_novo[..., 0], v_novo[..., 1])
            v_novo = v_novo * np.minimum(1.0, vmax / np.maximum(vel, 1e-6))[..., None]
            v_novo[~vivo] = 0
            setattr(self, "v" + nome, v_novo)
            setattr(self, nome, p + v_novo * DT)
        self.vip[vivo, 0] += V_VIP * DT
        cont = self._separa()
        d_vip = np.hypot(*(self.a - self.vip[:, None]).transpose(2, 0, 1))                # (n, NS)
        dmin = d_vip.min(1)
        self.min_vip = np.where(vivo, np.minimum(self.min_vip, dmin), self.min_vip)
        self.passos_vivo += vivo
        # medidas
        perto = vivo & (dmin < 4.0)
        self.perto += perto
        dg = np.hypot(*(self.g - self.vip[:, None]).transpose(2, 0, 1)).mean(1)
        self.cola += np.where(vivo, dg, 0)
        # segurança no caminho: algum segurança a < 1,1 m do segmento VIP -> assassino mais próximo
        ia = d_vip.argmin(1)
        alvo = self.a[np.arange(self.n), ia]
        seg = alvo - self.vip
        L2 = np.maximum((seg ** 2).sum(1), 1e-6)
        rel = self.g - self.vip[:, None]
        tt = np.clip((rel * seg[:, None]).sum(2) / L2[:, None], 0, 1)
        proj = self.vip[:, None] + tt[..., None] * seg[:, None]
        dsegm = np.hypot(*(self.g - proj).transpose(2, 0, 1))
        no_caminho = (dsegm < 1.1).any(1)
        self.escudo += perto & no_caminho
        # assassinos vindos de lados opostos (um acima e outro abaixo do VIP) a menos de 5 m
        perto5 = d_vip < 5.0
        acima = (self.a[..., 1] > self.vip[:, None, 1] + 0.5) & perto5
        abaixo = (self.a[..., 1] < self.vip[:, None, 1] - 0.5) & perto5
        self.abre += vivo & acima.any(1) & abaixo.any(1)
        self.contatos += vivo * (cont > 0)
        morto = vivo & (dmin < TOQUE)
        chegou = vivo & ~morto & (self.vip[:, 0] >= SAIDA)
        self.estado[morto] = MORTO
        self.estado[chegou] = CHEGOU
        self.t_fim[morto | chegou] = k

    def acabou(self):
        return bool((self.estado != VIVO).all())

    def finaliza(self, k):
        vivo = self.estado == VIVO
        self.estado[vivo] = CHEGOU if False else VIVO
        self.t_fim[vivo] = k

    def aptidoes(self):
        """(segurança, assassino) por partida."""
        vivo_fim = self.estado != MORTO
        morto = self.estado == MORTO
        tempo = np.where(self.t_fim >= 0, self.t_fim, PASSOS) / PASSOS
        prog = np.clip((self.vip[:, 0] - VIP0[0]) / (SAIDA - VIP0[0]), 0, 1)
        dmed_g = self.cola / np.maximum(self.passos_vivo, 1)
        fg = 7 * vivo_fim + 2.5 * morto * tempo + 1.5 * np.minimum(self.min_vip, 6) / 6 + 0.8 * np.exp(-dmed_g / 3)
        fa = 7 * morto + 3 * morto * (1 - tempo) + 3 * np.exp(-self.min_vip / 5) + 0.5 * (1 - prog) * morto
        return fg, fa
