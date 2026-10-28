"""Desafio: polícia e ladrão numa arena com paredes (dois lados: o ladrão quer chegar ao cofre, o policial quer pegá-lo).

Mundo 2D visto de cima, em metros. Cada partida é 1 ladrão x 1 policial; todos os agentes têm a mesma física
(aceleram em qualquer direção), o ladrão é um pouco mais rápido, o policial começa perto do cofre.
"""
import numpy as np

VOANDO, ESCAPOU, PEGO, TEMPO = 0, 1, 2, 3

LARG, ALT = 24.0, 14.0
PAREDES = [(9.0, 4.5, 15.0, 9.5),            # o quarteirão do meio
           (18.0, 2.2, 19.6, 4.0), (18.0, 10.0, 19.6, 11.8),    # pilares perto do cofre
           (4.5, 2.8, 6.0, 4.3), (4.5, 9.7, 6.0, 11.2)]          # pilares de largada
COFRE, R_COFRE = (22.3, 7.0), 1.5
RAIO, CAPTURA = 0.35, 0.9
V_LAD, V_POL, ACEL = 5.0, 4.4, 14.0
DT, PASSOS = 1 / 20, 320
RAIO_VISAO = 8.0
ANG = np.arange(8) * np.pi / 4
DIRS = np.stack([np.cos(ANG), np.sin(ANG)], 1)          # (8, 2)
CAMADAS = (16, 12, 2)


_INV = (1.0 / np.where(np.abs(DIRS) < 1e-9, 1e-9, DIRS)).astype(np.float32)      # (8, 2)
_IX, _IY = _INV[:, 0][None], _INV[:, 1][None]
_PAR = np.array(PAREDES, np.float32)


def raios(p):
    """Distância (0-1) até a parede em 8 direções, para posições p (N, 2)."""
    px, py = p[:, 0:1].astype(np.float32), p[:, 1:2].astype(np.float32)
    melhor = np.full((len(p), 8), RAIO_VISAO, np.float32)
    # saída da arena: por eixo, o maior dos dois cruzamentos; vale o menor entre os eixos
    tx = np.maximum((0 - px) * _IX, (LARG - px) * _IX)
    ty = np.maximum((0 - py) * _IY, (ALT - py) * _IY)
    melhor = np.minimum(melhor, np.minimum(tx, ty))
    for x0, y0, x1, y1 in _PAR:
        ax, bx = (x0 - px) * _IX, (x1 - px) * _IX
        ay, by = (y0 - py) * _IY, (y1 - py) * _IY
        entra = np.maximum(np.minimum(ax, bx), np.minimum(ay, by))
        sai = np.minimum(np.maximum(ax, bx), np.maximum(ay, by))
        bate = (sai >= np.maximum(entra, 0)) & (entra > 0)
        melhor = np.minimum(melhor, np.where(bate, entra, 1e9))
    return melhor / RAIO_VISAO


def empurra(p, v):
    """Resolve colisão círculo x paredes e bordas (in place)."""
    for x0, y0, x1, y1 in PAREDES:
        cx, cy = np.clip(p[:, 0], x0, x1), np.clip(p[:, 1], y0, y1)
        dx, dy = p[:, 0] - cx, p[:, 1] - cy
        d = np.hypot(dx, dy)
        fora = d > 1e-6
        perto = fora & (d < RAIO)
        nx = np.where(fora, dx / np.maximum(d, 1e-6), 0.0)
        ny = np.where(fora, dy / np.maximum(d, 1e-6), 0.0)
        p[:, 0] += np.where(perto, (RAIO - d) * nx, 0.0)
        p[:, 1] += np.where(perto, (RAIO - d) * ny, 0.0)
        vn = v[:, 0] * nx + v[:, 1] * ny
        cut = perto & (vn < 0)
        v[:, 0] -= np.where(cut, vn * nx, 0.0)
        v[:, 1] -= np.where(cut, vn * ny, 0.0)
        dentro = (~fora) & (p[:, 0] > x0) & (p[:, 0] < x1) & (p[:, 1] > y0) & (p[:, 1] < y1)
        if dentro.any():                         # centro dentro da parede: sai pelo lado mais próximo
            lados = np.stack([p[:, 0] - x0, x1 - p[:, 0], p[:, 1] - y0, y1 - p[:, 1]], 1)
            s = lados.argmin(1)
            for k, (ax, sg) in enumerate([(0, -1), (0, 1), (1, -1), (1, 1)]):
                m = dentro & (s == k)
                p[m, ax] = (x0, x1, y0, y1)[k] + sg * RAIO
                v[m, ax] = 0
    for ax, lim in ((0, LARG), (1, ALT)):
        baixo, alto = p[:, ax] < RAIO, p[:, ax] > lim - RAIO
        p[baixo, ax], p[alto, ax] = RAIO, lim - RAIO
        v[baixo | alto, ax] = 0


class Policia:
    nome = "policia"
    camadas = CAMADAS
    dt, passos = DT, PASSOS

    def __init__(self, n, rng, ruido=1.0):
        self.n = n
        self.pl = np.stack([1.8 + rng.normal(0, 0.5 * ruido, n), 7.0 + rng.uniform(-3.2, 3.2, n) * min(ruido, 1.0)
                            + rng.normal(0, 0.3 * ruido, n)], 1).clip(0.8, [4.0, 13.0])
        self.pp = np.stack([19.8 + rng.uniform(-1.8, 1.0, n), 7.0 + rng.uniform(-2.6, 2.6, n)], 1)
        self.vl, self.vp = np.zeros((n, 2)), np.zeros((n, 2))
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.min_cofre = np.full(n, 99.0)
        self.dist_med = np.zeros(n)
        self.passos_vivo = np.zeros(n)
        self.max_x = self.pl[:, 0].copy()
        self.cruzou = np.zeros(n, bool)
        self.y_cruza = np.zeros(n)
        self.pol_cofre_cruza = np.zeros(n)
        self.t_cruza = np.full(n, -1.0)

    # ---- observações (16): posição, velocidade, cofre, adversário, 8 raios
    def _obs(self, p, v, q):
        g = np.array(COFRE)
        return np.concatenate([((p - [LARG / 2, ALT / 2]) / [LARG / 2, ALT / 2]), v / V_LAD,
                               (g - p) / [LARG / 2, ALT / 2], (q - p) / [LARG / 2, ALT / 2], raios(p)], 1).astype(np.float32)

    def obs_ladrao(self):
        return self._obs(self.pl, self.vl, self.pp)

    def obs_policia(self):
        return self._obs(self.pp, self.vp, self.pl)

    def passo(self, sl, sp, k):
        vivo = self.estado == VOANDO
        for p, v, s, vmax in ((self.pl, self.vl, sl, V_LAD), (self.pp, self.vp, sp, V_POL)):
            v_novo = v + s * ACEL * DT - 0.9 * v * DT
            vel = np.hypot(v_novo[:, 0], v_novo[:, 1])
            v_novo *= np.minimum(1.0, vmax / np.maximum(vel, 1e-6))[:, None]
            v_novo[~vivo] = 0
            v[:] = v_novo
            p += v * DT
            empurra(p, v)
        g = np.array(COFRE)
        dg = np.hypot(*(self.pl - g).T)
        dm = np.hypot(*(self.pl - self.pp).T)
        self.min_cofre = np.where(vivo, np.minimum(self.min_cofre, dg), self.min_cofre)
        self.dist_med += np.where(vivo, dm, 0)
        self.passos_vivo += vivo
        self.max_x = np.maximum(self.max_x, self.pl[:, 0])
        cruza = vivo & ~self.cruzou & (self.pl[:, 0] >= 12.0)
        self.y_cruza = np.where(cruza, self.pl[:, 1], self.y_cruza)
        self.pol_cofre_cruza = np.where(cruza, np.hypot(*(self.pp - g).T), self.pol_cofre_cruza)
        self.t_cruza = np.where(cruza, k * DT, self.t_cruza)
        self.cruzou |= cruza
        pego = vivo & (dm < CAPTURA)
        fugiu = vivo & ~pego & (dg < R_COFRE)
        self.estado[pego] = PEGO
        self.estado[fugiu] = ESCAPOU
        self.t_fim[pego | fugiu] = k

    def acabou(self):
        return bool((self.estado != VOANDO).all())

    def finaliza(self, k):
        vivo = self.estado == VOANDO
        self.estado[vivo] = TEMPO
        self.t_fim[vivo] = k

    def aptidoes(self):
        """(ladrão, policial) por partida."""
        esc, peg = self.estado == ESCAPOU, self.estado == PEGO
        tempo = np.where(self.t_fim >= 0, self.t_fim, PASSOS) / PASSOS
        dmed = self.dist_med / np.maximum(self.passos_vivo, 1)
        fl = (3 * np.exp(-self.min_cofre / 6) + 7 * esc + 2 * esc * (1 - tempo) - 2.5 * peg * (1 - tempo)
              + 0.6 * np.minimum(dmed, 8) / 8)
        fp = 7 * peg + 3 * peg * (1 - tempo) - 4 * esc + 2.0 * np.exp(-dmed / 4) + 0.8 * np.exp(-self.min_cofre / 3) * (~esc)
        return fl, fp
