"""Desafio de dois lados: 2 POLICIAIS contra 1 LADRÃO num labirinto (co-evolução).

O ladrão ganha pontos roubando DIAMANTES (um por vez, em pontos fixos do mapa; todo mundo sabe onde
está o da vez: o alarme dispara). Se for preso, perde metade do que roubou. Nada aqui codifica
"truques". Cada agente só escolhe para onde andar (vx, vy). Todos enxergam só em linha reta (paredes
bloqueiam a visão) e até ALCANCE metros. Os dois policiais dividem o que veem (rádio) e lembram onde o
ladrão foi visto pela última vez. Esperar no cofre, esconder-se, cercar pelos dois lados... ou surgem
do treino ou não surgem.

Unidades: metros e segundos. Cada bloco do mapa tem 1 m. x = coluna, y = linha contada de baixo.
"""
import numpy as np

MAPA = [
    "#################",
    "#...............#",
    "#.##.###.###.##.#",
    "#.##.#.....#.##.#",
    "#....#.###.#....#",
    "##.#...#.#...#.##",
    "#..###.....###..#",
    "##.#...#.#...#.##",
    "#....#.###.#....#",
    "#.##.#.....#.##.#",
    "#.##.###.###.##.#",
    "#...............#",
    "#################",
]
LIN, COL = len(MAPA), len(MAPA[0])
PAREDE = np.array([[c == "#" for c in linha] for linha in MAPA[::-1]])   # PAREDE[y, x], y para cima
LIVRES = np.array([(x + 0.5, y + 0.5) for y in range(LIN) for x in range(COL) if not PAREDE[y, x]])

DT = 0.1
PASSOS = 200            # 20 s: se o ladrão aguentar, ele vence
V_LADRAO, V_POLICIA = 2.2, 2.0
RAIO = 0.26             # meio corpo (colisão com a parede)
ALCANCE = 7.0           # até onde se enxerga em linha reta
PEGA = 0.6              # distância de captura
RAIOS = 8               # sensores de parede: 8 direções, até 4 m
SENSOR = 4.0
DELEGACIA = np.array([[7.5, 6.5], [9.5, 6.5]])   # os policiais saem do centro do mapa
COFRES = np.array([[1.5, 1.5], [15.5, 1.5], [1.5, 11.5], [15.5, 11.5], [8.5, 1.5], [8.5, 11.5]])
ROUBA = 0.6             # distância para pegar o diamante
VIGIA = 2.5             # policial a menos disso do diamante = vigiando o cofre

FUGINDO, PRESO, ESCAPOU = 0, 1, 2

_ANG = np.arange(RAIOS) * 2 * np.pi / RAIOS
_DIR = np.stack([np.cos(_ANG), np.sin(_ANG)], 1)
_PASSO_RAIO = np.linspace(0.3, SENSOR, 14)


def parede(x, y):
    xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
    fora = (xi < 0) | (xi >= COL) | (yi < 0) | (yi >= LIN)
    return fora | PAREDE[np.clip(yi, 0, LIN - 1), np.clip(xi, 0, COL - 1)]


def _caminhos():
    """Distância andando pelos corredores (em blocos) entre todo par de blocos livres (busca em largura)."""
    ids = -np.ones((LIN, COL), int)
    livres = [(y, x) for y in range(LIN) for x in range(COL) if not PAREDE[y, x]]
    for k, (y, x) in enumerate(livres):
        ids[y, x] = k
    n = len(livres)
    viz = -np.ones((n, 4), int)
    for k, (y, x) in enumerate(livres):
        for j, (dy, dx) in enumerate(((0, 1), (1, 0), (0, -1), (-1, 0))):
            if 0 <= y + dy < LIN and 0 <= x + dx < COL and ids[y + dy, x + dx] >= 0:
                viz[k, j] = ids[y + dy, x + dx]
    dist = np.full((n, n), 99.0)
    for a in range(n):
        dist[a, a] = 0
        fila = [a]
        for u in fila:
            for v in viz[u]:
                if v >= 0 and dist[a, v] > dist[a, u] + 1:
                    dist[a, v] = dist[a, u] + 1
                    fila.append(v)
    return ids, viz, dist


IDS, VIZ, DIST = _caminhos()
_CENTRO = LIVRES   # mesma ordem dos ids (linha por linha, de baixo para cima)


def bloco(p):
    xi = np.clip(np.floor(p[:, 0]).astype(int), 0, COL - 1)
    yi = np.clip(np.floor(p[:, 1]).astype(int), 0, LIN - 1)
    return IDS[yi, xi]


def caminho(p, alvo):
    """GPS: direção (dx, dy) do próximo passo pelo corredor de p até alvo, e a distância andando (blocos)."""
    a, b = bloco(p), bloco(alvo)
    a = np.where(a < 0, 0, a)
    b = np.where(b < 0, 0, b)
    dv = np.where(VIZ[a] >= 0, DIST[np.maximum(VIZ[a], 0), b[:, None]], 99.0)       # (M, 4)
    prox = VIZ[a, np.argmin(dv, 1)]
    mesmo = (a == b) | (dv.min(1) >= 99)
    alvo_local = np.where(mesmo[:, None], alvo, _CENTRO[np.maximum(prox, 0)])
    d = alvo_local - p
    d = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
    return d, DIST[a, b]


def anda(p, v):
    """Move p (M,2) com velocidade v (M,2) por DT, deslizando nas paredes (eixo por eixo)."""
    p = p.copy()
    for ax in (0, 1):
        novo = p.copy()
        novo[:, ax] += v[:, ax] * DT
        s = np.sign(v[:, ax])
        borda = novo[:, ax] + s * RAIO
        o = 1 - ax
        bate = np.zeros(len(p), bool)
        for d in (-0.85, 0.0, 0.85):
            q = novo.copy()
            q[:, ax] = borda
            q[:, o] += d * RAIO
            bate |= parede(q[:, 0], q[:, 1])
        p[:, ax] = np.where(bate, p[:, ax], novo[:, ax])
    return p


def sensores(p):
    """(M,2) -> (M, RAIOS) distância até a parede em cada direção, normalizada 0..1."""
    pts = p[:, None, None, :] + _DIR[None, :, None, :] * _PASSO_RAIO[None, None, :, None]
    bate = parede(pts[..., 0], pts[..., 1])
    primeiro = np.where(bate.any(2), bate.argmax(2), len(_PASSO_RAIO) - 1)
    return _PASSO_RAIO[primeiro] / SENSOR


def enxerga(a, b):
    """(M,2),(M,2) -> bool: b está a até ALCANCE de a e nenhuma parede corta a linha."""
    d = np.linalg.norm(b - a, axis=1)
    u = np.linspace(0.05, 0.95, 24)
    pts = a[:, None, :] + (b - a)[:, None, :] * u[None, :, None]
    return (d <= ALCANCE) & ~parede(pts[..., 0], pts[..., 1]).any(1)


def pilares():
    """Blocos de parede internos (componentes conectados), com o centro de cada um: dar a volta
    completa em um deles é o 'laço no quarteirão'."""
    vis = np.zeros_like(PAREDE)
    out = []
    for y in range(1, LIN - 1):
        for x in range(1, COL - 1):
            if PAREDE[y, x] and not vis[y, x]:
                pilha, cel = [(y, x)], []
                vis[y, x] = True
                while pilha:
                    cy, cx = pilha.pop()
                    cel.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 < ny < LIN - 1 and 0 < nx < COL - 1 and PAREDE[ny, nx] and not vis[ny, nx]:
                            vis[ny, nx] = True
                            pilha.append((ny, nx))
                c = np.array(cel, float)
                out.append((c[:, 1].mean() + 0.5, c[:, 0].mean() + 0.5))
    return np.array(out)


PILARES = pilares()


class Policia:
    nome = "policia"
    # entradas do ladrão: 8 paredes + 2x policial(vê, dx, dy, idade) + GPS até o diamante(dx, dy, dist) + tempo
    # entradas do policial: 8 paredes + ladrão(vê, idade) + GPS até onde o ladrão foi visto(3) +
    #                       GPS até o diamante(3) + parceiro(dx, dy) + papel + tempo
    camadas_lad = (20, 12, 2)
    camadas_pol = (20, 12, 2)
    dt = DT
    passos = PASSOS

    def __init__(self, n, rng):
        self.n = n
        self.pp = np.repeat(DELEGACIA[None], n, 0) + rng.uniform(-0.15, 0.15, (n, 2, 2))
        # ladrão nasce num bloco livre a pelo menos 6 m da delegacia
        longe = LIVRES[np.linalg.norm(LIVRES - DELEGACIA.mean(0), axis=1) >= 6]
        self.pl = longe[rng.integers(0, len(longe), n)] + rng.uniform(-0.15, 0.15, (n, 2))
        self.rng = rng
        self.cofre = rng.integers(0, len(COFRES), n)   # índice do cofre com o diamante da vez
        self.diamantes = np.zeros(n)
        self.rouba_oculto = np.zeros(n)            # diamantes pegos sem nenhum policial ver
        self.vigia = np.zeros(n)                   # passos com um policial de guarda perto do diamante
        self.pego_cofre = np.zeros(n, bool)        # preso a menos de VIGIA do diamante
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        # o que cada lado sabe do outro (última posição vista e há quanto tempo)
        self.visto_pol = self.pl.copy()            # onde a polícia viu o ladrão pela última vez
        self.idade_pol = np.full(n, 9.0)           # s desde a última vez (9 = nunca viu)
        self.visto_lad = self.pp.copy()            # onde o ladrão viu cada policial
        self.idade_lad = np.full((n, 2), 9.0)
        self.ve_pol = np.zeros(n, bool)
        self.ve_lad = np.zeros((n, 2), bool)
        self.oculto = np.zeros(n)                  # passos vivo sem ser visto
        self.vivo = np.zeros(n)
        self.dist_par = np.zeros(n)
        self.ang = np.zeros((n, len(PILARES)))     # ângulo acumulado do ladrão em volta de cada pilar
        self._ang_ant = self._angulos()
        self.cerco = np.zeros(n, bool)
        self.dmin = np.full(n, 99.0)
        self._visao()

    def _angulos(self):
        d = self.pl[:, None, :] - PILARES[None]
        return np.arctan2(d[..., 1], d[..., 0])

    def _visao(self):
        n = self.n
        ve = np.stack([enxerga(self.pp[:, j], self.pl) for j in range(2)], 1)    # (n, 2) a linha é simétrica
        self.ve_lad = ve
        self.ve_pol = ve.any(1)
        self.visto_pol = np.where(self.ve_pol[:, None], self.pl, self.visto_pol)
        self.idade_pol = np.where(self.ve_pol, 0.0, np.minimum(self.idade_pol + DT, 9.0))
        self.visto_lad = np.where(ve[..., None], self.pp, self.visto_lad)
        self.idade_lad = np.where(ve, 0.0, np.minimum(self.idade_lad + DT, 9.0))
        _ = n

    # ---------------------------------------------------------- observações
    def obs_ladrao(self, t):
        rel = (self.visto_lad - self.pl[:, None, :]) / ALCANCE                  # (n, 2, 2)
        sab = np.concatenate([self.ve_lad[..., None] * 1.0, rel, self.idade_lad[..., None] / 9], 2)
        gd, dd = caminho(self.pl, COFRES[self.cofre])
        return np.concatenate([sensores(self.pl), sab.reshape(self.n, 8), gd, dd[:, None] / 30,
                               np.full((self.n, 1), t / 20)], 1).astype(np.float32)

    def obs_policia(self, t, j):
        p = self.pp[:, j]
        gv, dv = caminho(p, self.visto_pol)
        gd, dd = caminho(p, COFRES[self.cofre])
        par = (self.pp[:, 1 - j] - p) / ALCANCE
        return np.concatenate([sensores(p), self.ve_pol[:, None] * 1.0, self.idade_pol[:, None] / 9,
                               gv, dv[:, None] / 30, gd, dd[:, None] / 30, par,
                               np.full((self.n, 1), 1.0 if j else -1.0), np.full((self.n, 1), t / 20)],
                              1).astype(np.float32)

    # ---------------------------------------------------------- passo
    def passo(self, sl, sp, k):
        """sl (n,2) saída do ladrão; sp (n,2,2) saídas dos dois policiais (tanh, -1..1)."""
        ativo = self.estado == FUGINDO
        m = ativo[:, None]

        def vel(s, vmax):
            norma = np.maximum(np.linalg.norm(s, axis=-1, keepdims=True), 1.0)
            return s / norma * vmax

        self.pl = np.where(m, anda(self.pl, vel(sl, V_LADRAO)), self.pl)
        for j in range(2):
            self.pp[:, j] = np.where(m, anda(self.pp[:, j], vel(sp[:, j], V_POLICIA)), self.pp[:, j])
        a = self._angulos()
        da = (a - self._ang_ant + np.pi) % (2 * np.pi) - np.pi
        self.ang += da * m
        self._ang_ant = a
        dc = np.linalg.norm(COFRES[self.cofre] - self.pl, axis=1)
        roubou = ativo & (dc <= ROUBA)
        if roubou.any():
            self.diamantes += roubou
            self.rouba_oculto += roubou & ~self.ve_pol
            novo = (self.cofre + self.rng.integers(1, len(COFRES), self.n)) % len(COFRES)
            self.cofre = np.where(roubou, novo, self.cofre)
        self._visao()
        dv = np.linalg.norm(self.pp - COFRES[self.cofre][:, None, :], axis=2)      # (n, 2)
        self.vigia += ativo & (dv.min(1) <= VIGIA)
        self.vivo += ativo
        self.oculto += ativo & ~self.ve_pol
        self.dist_par += ativo * np.linalg.norm(self.pp[:, 0] - self.pp[:, 1], axis=1)
        d = np.linalg.norm(self.pp - self.pl[:, None, :], axis=2)                # (n, 2)
        self.dmin = np.where(ativo, np.minimum(self.dmin, d.min(1)), self.dmin)
        pego = ativo & (d.min(1) <= PEGA)
        if pego.any():
            # cerco: os dois policiais perto, vindo de lados opostos (ângulo > 110 graus visto do ladrão)
            v0, v1 = self.pp[:, 0] - self.pl, self.pp[:, 1] - self.pl
            cos = (v0 * v1).sum(1) / (np.linalg.norm(v0, axis=1) * np.linalg.norm(v1, axis=1) + 1e-9)
            self.cerco |= pego & (cos < np.cos(np.radians(110))) & (d.max(1) <= 3.5)
            dcf = np.linalg.norm(COFRES[self.cofre] - self.pl, axis=1)
            self.pego_cofre |= pego & (dcf <= VIGIA)
            self.estado[pego] = PRESO
            self.t_fim[pego] = k
        if k == PASSOS - 1:
            fim = self.estado == FUGINDO
            self.estado[fim] = ESCAPOU
            self.t_fim[fim] = k

    def acabou(self):
        return (self.estado != FUGINDO).all()

    def finaliza(self, k):
        fim = self.estado == FUGINDO
        self.estado[fim] = ESCAPOU
        self.t_fim[fim] = k

    # ---------------------------------------------------------- notas
    def aptidoes(self):
        preso = self.estado == PRESO
        t = np.where(self.t_fim >= 0, self.t_fim + 1, PASSOS) / PASSOS     # fração do tempo que durou
        lad = self.diamantes * np.where(preso, 0.5, 1.0) + 0.3 * t
        pol = preso * (1.5 - t) - 0.25 * self.diamantes + 0.3 * (1 - np.minimum(self.dmin / 10, 1))
        return lad, pol
