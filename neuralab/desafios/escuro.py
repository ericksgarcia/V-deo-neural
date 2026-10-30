"""Desafio: esconde-esconde no escuro (dois lados: 3 caçadores com lanterna x 3 fugitivos).

Mundo 2D visto de cima, em metros, tudo escuro. Cada caçador tem uma lanterna (cone) e só enxerga o fugitivo que estiver
DENTRO do cone; só pega quem está iluminado e a menos de CAPT metros (quem está colado nas costas dele não é pego).
Os fugitivos veem as lanternas (os feixes aparecem no escuro) e sabem se estão iluminados. Cada lado tem UM cérebro
compartilhado pelos três corpos. Os cérebros não têm memória: cada decisão olha só o instante atual.
"""
import numpy as np

VIVO, PEGO = 0, 1

LARG, ALT = 24.0, 14.0
RAIO, CAPT = 0.4, 0.9
ALCANCE, MEIO = 7.0, 0.5            # lanterna: alcance (m) e meio ângulo (rad, ~29 graus)
V_CAC, V_FUG, ACEL = 3.6, 4.0, 14.0
GIRO = 4.5                           # rad/s, caçador
DT, PASSOS = 1 / 20, 300
NC = NF = 3
CAM_C = (15, 12, 2)
CAM_F = (20, 14, 2)


def _ang(x):
    return (x + np.pi) % (2 * np.pi) - np.pi


class Escuro:
    nome = "escuro"

    def __init__(self, n, rng):
        self.n = n
        self.c = np.stack([rng.uniform(1.5, 22.5, (n, NC)), rng.uniform(1.5, 12.5, (n, NC))], 2)
        self.f = np.stack([rng.uniform(1.5, 22.5, (n, NF)), rng.uniform(1.5, 12.5, (n, NF))], 2)
        # ninguém começa iluminado nem colado
        for _ in range(3):
            d = np.hypot(*(self.f[:, None] - self.c[:, :, None]).transpose(3, 0, 1, 2)).min(1)
            ruim = d < 4.0
            k = int(ruim.sum())
            self.f[ruim] = np.stack([rng.uniform(1.5, 22.5, k), rng.uniform(1.5, 12.5, k)], 1)
        self.ang = rng.uniform(-np.pi, np.pi, (n, NC))
        self.vc = np.zeros((n, NC))                  # velocidade escalar do caçador
        self.vf = np.zeros((n, NF, 2))
        self.estado = np.zeros((n, NF), np.int8)
        self.t_pego = np.full((n, NF), -1)
        self.t_ult = np.zeros(n, int)
        self._luz = self._ilumina()
        self.acao_c = np.zeros((n, NC, 2))
        # medidas
        self.vivo_f = np.zeros(n)                    # passos-fugitivo vivos
        self.aceso = np.zeros(n)                     # passos-fugitivo vivos e iluminados
        self.cego_c = np.zeros(n)                    # passos-caçador sem ninguém na luz
        self.giro_cego = np.zeros(n)                 # soma de |giro| nesses passos
        self.parado = np.zeros(n)                    # fugitivo vivo parado com caçador a < 9 m
        self.perto9 = np.zeros(n)                    # fugitivo vivo com caçador a < 9 m
        self.costas = np.zeros(n)                    # fugitivo a < 3 m de caçador, atrás dele
        self.perto3 = np.zeros(n)                    # fugitivo a < 3 m de caçador
        self.luz_c = np.zeros(n)                     # passos-caçador com alguém na luz

    # ---- geometria
    def _rel(self):
        """(n, NC, NF, 2): vetor caçador -> fugitivo."""
        return self.f[:, None] - self.c[:, :, None]

    def _ilumina(self):
        rel = self._rel()
        d = np.hypot(rel[..., 0], rel[..., 1])
        fora = _ang(np.arctan2(rel[..., 1], rel[..., 0]) - self.ang[..., None])
        return (d < ALCANCE) & (np.abs(fora) < MEIO) & (self.estado[:, None, :] == VIVO)

    # ---- observações
    def obs_cacador(self):
        n = self.n
        rel = self._rel()
        d = np.hypot(rel[..., 0], rel[..., 1])
        co, si = np.cos(self.ang), np.sin(self.ang)
        bx = rel[..., 0] * co[..., None] + rel[..., 1] * si[..., None]
        by = -rel[..., 0] * si[..., None] + rel[..., 1] * co[..., None]
        luz = self._luz
        dl = np.where(luz, d, 99.0)
        k = dl.argmin(2)
        tem = luz.any(2)
        ix = (np.arange(n)[:, None], np.arange(NC)[None, :], k)
        vx, vy = np.where(tem, bx[ix] / ALCANCE, 0.0), np.where(tem, by[ix] / ALCANCE, 0.0)
        # colegas no referencial do corpo
        idx = np.array([[1, 2], [0, 2], [0, 1]])
        am = self.c[:, idx] - self.c[:, :, None]
        ax = am[..., 0] * co[..., None] + am[..., 1] * si[..., None]
        ay = -am[..., 0] * si[..., None] + am[..., 1] * co[..., None]
        parede = np.stack([self.c[..., 0], LARG - self.c[..., 0], self.c[..., 1], ALT - self.c[..., 1]], -1) / 6.0
        return np.concatenate([np.stack([co, si, self.vc / V_CAC, vx, vy, tem.astype(float)], -1),
                            (self.c - [LARG / 2, ALT / 2]) / [LARG / 2, ALT / 2],
                            ax / 8.0, ay / 8.0, parede[..., :3]], -1).astype(np.float32)

    def obs_fugitivo(self):
        n = self.n
        rel = (self.c[:, None] - self.f[:, :, None])                 # (n, NF, NC, 2): fugitivo -> caçador
        d = np.hypot(rel[..., 0], rel[..., 1])
        o = np.argsort(d, 2)
        r = np.take_along_axis(rel, o[..., None], 2) / 8.0           # ordenado por distância
        co, si = np.cos(self.ang), np.sin(self.ang)
        cs = np.stack([co, si], -1)[:, None].repeat(NF, 1)           # (n, NF, NC, 2)
        cs = np.take_along_axis(cs, o[..., None], 2)
        dmin = np.take_along_axis(d, o, 2)[..., 0]
        luz = self._luz.any(1)
        idx = np.array([[1, 2], [0, 2], [0, 1]])
        am = (self.f[:, idx] - self.f[:, :, None]) / 8.0
        parede = np.stack([self.f[..., 0], LARG - self.f[..., 0], self.f[..., 1], ALT - self.f[..., 1]], -1) / 6.0
        return np.concatenate([r[:, :, 0], cs[:, :, 0], r[:, :, 1], cs[:, :, 1], luz[..., None].astype(float),
                               (dmin / 8.0)[..., None], self.vf / V_FUG, am.reshape(n, NF, -1), parede],
                              -1).astype(np.float32)

    # ---- passo
    def passo(self, sc, sf, k):
        vivo_p = self.estado == VIVO
        ativo = vivo_p.any(1)
        # caçadores: sc[...,0] = acelerar/frear, sc[...,1] = girar
        self.acao_c = sc
        self.ang = _ang(self.ang + sc[..., 1] * GIRO * DT)
        self.vc = np.clip(self.vc + sc[..., 0] * ACEL * DT - 0.9 * self.vc * DT, -0.3 * V_CAC, V_CAC)
        self.c = self.c + np.stack([np.cos(self.ang), np.sin(self.ang)], -1) * self.vc[..., None] * DT
        # fugitivos
        v = self.vf + sf * ACEL * DT - 0.9 * self.vf * DT
        vel = np.hypot(v[..., 0], v[..., 1])
        v = v * np.minimum(1.0, V_FUG / np.maximum(vel, 1e-6))[..., None]
        v[~vivo_p] = 0
        self.vf = v
        self.f = self.f + v * DT
        for pos, vel_ in ((self.c, None), (self.f, self.vf)):
            for ax, lim in ((0, LARG), (1, ALT)):
                baixo, alto = pos[..., ax] < RAIO, pos[..., ax] > lim - RAIO
                pos[..., ax] = np.where(baixo, RAIO, np.where(alto, lim - RAIO, pos[..., ax]))
                if vel_ is not None:
                    vel_[..., ax] = np.where(baixo | alto, 0.0, vel_[..., ax])
        self.vc = np.where((self.c[..., 0] <= RAIO) | (self.c[..., 0] >= LARG - RAIO) |
                           (self.c[..., 1] <= RAIO) | (self.c[..., 1] >= ALT - RAIO), 0.0, self.vc)
        # luz e captura
        self._luz = self._ilumina()
        rel = self._rel()
        d = np.hypot(rel[..., 0], rel[..., 1])
        pega = (self._luz & (d < CAPT)).any(1) & vivo_p
        self.t_pego = np.where(pega, k, self.t_pego)
        self.estado = np.where(pega, PEGO, self.estado).astype(np.int8)
        # medidas (sobre quem estava vivo no começo do passo)
        iluminado = self._luz.any(1) & vivo_p
        self.vivo_f += vivo_p.sum(1)
        self.aceso += iluminado.sum(1)
        sem_luz = ~self._luz.any(2)
        self.cego_c += sem_luz.sum(1) * ativo
        self.giro_cego += (np.abs(sc[..., 1]) * sem_luz).sum(1) * ativo
        self.luz_c += (~sem_luz).sum(1) * ativo
        dmin_c = d.min(1)
        vel_f = np.hypot(self.vf[..., 0], self.vf[..., 1])
        p9 = vivo_p & (dmin_c < 9.0)
        self.perto9 += p9.sum(1)
        self.parado += (p9 & (vel_f < 0.4)).sum(1)
        p3 = vivo_p & (dmin_c < 3.0)
        co, si = np.cos(self.ang), np.sin(self.ang)
        fora = np.abs(_ang(np.arctan2(rel[..., 1], rel[..., 0]) - self.ang[..., None]))
        atras = ((d < 3.0) & (fora > 1.9)).any(1)
        self.perto3 += p3.sum(1)
        self.costas += (p3 & atras).sum(1)
        self.t_ult = np.where(ativo, k, self.t_ult)

    def acabou(self):
        return bool((self.estado != VIVO).all())

    def finaliza(self, k):
        pass

    def aptidoes(self):
        """(caçador, fugitivo) por partida."""
        pegos = (self.estado == PEGO)
        npego = pegos.sum(1)
        tempo = np.where(pegos, self.t_pego, PASSOS) / PASSOS
        luz_frac = self.luz_c / np.maximum(self.cego_c + self.luz_c, 1)
        fc = 3.0 * npego + 1.5 * (pegos * (1 - tempo)).sum(1) + 0.6 * luz_frac
        ff = 2.0 * tempo.mean(1) + 1.0 * (~pegos).mean(1) + 0.6 * (1 - self.aceso / np.maximum(self.vivo_f, 1))
        return fc, ff
