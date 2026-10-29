"""Desafio: cruzamento sem semáforo. Uma única IA (a mesma cabeça em todos os carros) dirige 8 carros
que chegam de quatro lados. Passar todos sem bater = sucesso.

Cada "indivíduo" da população é um cruzamento inteiro (8 carros, mesmo cérebro). Todos os cruzamentos de
uma geração começam com o MESMO trânsito, então a comparação entre cérebros é justa.
"""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

COMP, LARG = 4.2, 1.9      # carro (m)
FAIXA = 1.8                 # distância do eixo da rua ao centro da faixa
SAIDA = 19.0                # u a partir do qual o carro "passou"
NOMES_LADO = ("LESTE", "NORTE", "OESTE", "SUL")


def centro(lado, u):
    """Posição (x, y) do carro no lado 0..3 (L, N, O, S) com u metros percorridos desde o centro do cruzamento."""
    x = np.select([lado == 0, lado == 1, lado == 2], [u, FAIXA, -u], -FAIXA)
    y = np.select([lado == 0, lado == 1, lado == 2], [-FAIXA, u, FAIXA], -u)
    return x, y


class Cruzamento:
    nome = "cruzamento"
    camadas = (8, 10, 1)
    dt = 1 / 30
    passos = 420            # 14 s
    n_lados, por_lado = 4, 2
    v_max, a_max = 11.0, 5.0
    cenarios = 4            # cada cérebro é avaliado em 4 trânsitos diferentes por geração
    ga = {"elite": 6, "taxa": 0.1, "forca": 0.2}

    def __init__(self, n, rng, ruido=1.0, por_mundo=False):
        self.n = n
        C = self.C = self.n_lados * self.por_lado
        self.lado = np.arange(C) % 4
        self.eixo = self.lado % 2
        self.rank = np.arange(C) // 4
        formato = (n if por_mundo else 1, 4)
        u0 = -(14.5 + ruido * (rng.random(formato) * 2.5 - 1.0))              # carro da frente de cada lado
        folga = 10.0 + ruido * rng.random(formato) * 2.0                       # distância ao de trás
        v0 = 6.0 + ruido * (rng.random(formato) * 2.0 - 1.0)
        u = np.zeros((formato[0], C))
        v = np.zeros((formato[0], C))
        for c in range(C):
            u[:, c] = u0[:, c % 4] - self.rank[c] * folga[:, c % 4]
            v[:, c] = v0[:, c % 4]
        u, v = np.broadcast_to(u, (n, C)).copy(), np.broadcast_to(v, (n, C)).copy()
        self.s = np.stack([u, v], -1)                                           # (P, C, 2): u, v
        self.eta0 = -u / np.maximum(v, 0.1)                                     # quando cada carro chegaria ao centro
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros((n, C))
        self.bateu = np.zeros(n, bool)
        self.par_bateu = np.full((n, 2), -1)
        self.t_entra = np.full((n, C), -1.0)
        self.t_passou = np.full((n, C), -1.0)
        self.parado = np.zeros((n, C))          # segundos quase parado ANTES do cruzamento
        # vizinhos de faixa cruzada de cada carro: (C, 4)
        self.cruz = np.array([[j for j in range(C) if self.eixo[j] != self.eixo[c]] for c in range(C)])

    # ------------------------------------------------------------------ percepção
    def observa(self):
        u, v = self.s[..., 0], self.s[..., 1]
        P, C = u.shape
        gap = np.ones((P, C))
        dv = np.zeros((P, C))
        for c in range(C):
            if self.rank[c] == 1:
                f = c - 4
                gap[:, c] = np.clip((u[:, f] - u[:, c] - COMP) / 8, -0.5, 1)
                dv[:, c] = 2 * (v[:, f] - v[:, c]) / self.v_max
        cu, cv = u[:, self.cruz], v[:, self.cruz]                                # (P, C, 4)
        chave = np.where(cu < 9.0, np.abs(cu), 99.0)
        ordem = np.argsort(chave, 2)[..., :2]
        u2 = np.take_along_axis(cu, ordem, 2)
        v2 = np.take_along_axis(cv, ordem, 2)
        ok = np.take_along_axis(chave, ordem, 2) < 90
        u2 = np.where(ok, u2 / 25, 1.0)
        v2 = np.where(ok, v2 / self.v_max, 0.0)
        return np.stack([u / 25, v / self.v_max, gap, dv, u2[..., 0], v2[..., 0], u2[..., 1], v2[..., 1]],
                        -1).astype(np.float32)

    # ------------------------------------------------------------------ física
    def retangulos(self):
        u = self.s[..., 0]
        x, y = centro(self.lado[None, :], u)
        horiz = (self.eixo == 0)[None, :]
        hx = np.where(horiz, COMP / 2, LARG / 2)
        hy = np.where(horiz, LARG / 2, COMP / 2)
        return x, y, hx, hy

    def passo(self, saida, t):
        vivo = self.estado == VOANDO
        u, v = self.s[..., 0].copy(), self.s[..., 1].copy()
        a = np.clip(saida[..., 0], -1, 1) * self.a_max
        v = np.clip(v + a * self.dt, 0.0, self.v_max)
        u = u + v * self.dt
        novo = np.stack([u, v], -1)
        self.s[vivo] = novo[vivo]
        self.acel = np.where(vivo[:, None], saida[..., 0], 0)
        u, v = self.s[..., 0], self.s[..., 1]
        seg = t * self.dt
        entrou = vivo[:, None] & (u > -3.5) & (self.t_entra < 0)
        self.t_entra[entrou] = seg
        passou = vivo[:, None] & (u > SAIDA) & (self.t_passou < 0)
        self.t_passou[passou] = seg
        self.parado += (vivo[:, None] & (v < 0.6) & (u < -3.5)) * self.dt
        # colisão entre quaisquer dois carros que ainda não saíram
        x, y, hx, hy = self.retangulos()
        ativo = (u < SAIDA - 2)
        dx = np.abs(x[:, :, None] - x[:, None, :]) < (hx[:, :, None] + hx[:, None, :])
        dy = np.abs(y[:, :, None] - y[:, None, :]) < (hy[:, :, None] + hy[:, None, :])
        par = dx & dy & ativo[:, :, None] & ativo[:, None, :] & ~np.eye(self.C, dtype=bool)[None]
        bate = vivo & par.any((1, 2))
        if bate.any():
            for k in np.where(bate)[0]:
                i, j = np.argwhere(par[k])[0]
                self.par_bateu[k] = (i, j)
        self.bateu |= bate
        self.estado[bate] = FALHA
        self.t_fim[bate] = t
        ok = vivo & ~bate & (self.t_passou >= 0).all(1)
        self.estado[ok] = SUCESSO
        self.t_fim[ok] = t

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        self.estado[vivo] = FALHA
        self.t_fim[vivo] = t

    # ------------------------------------------------------------------ avaliação
    def aptidao(self):
        u = self.s[..., 0]
        prog = np.clip((u + 15) / (SAIDA + 15), 0, 1).mean(1)
        passaram = (self.t_passou >= 0).mean(1)
        rapido = np.where(self.estado == SUCESSO, 1 - self.t_fim / self.passos, 0)
        return 2 * passaram + prog - 1.0 * self.bateu + (self.estado == SUCESSO) * (2 + 2 * rapido)

    def ordem_de_entrada(self):
        """(P, C) carros ordenados por quando chegaram ao cruzamento (só vale onde todos entraram)."""
        te = np.where(self.t_entra < 0, 1e9, self.t_entra)
        return np.argsort(te, 1)

    def metricas(self):
        suc = self.estado == SUCESSO
        passaram = (self.t_passou >= 0).mean(1)
        ordem = self.ordem_de_entrada()
        eixos = self.eixo[ordem]
        alterna = (eixos[:, 1:] != eixos[:, :-1]).mean(1)
        return {
            "bateu": float(self.bateu.mean()),
            "passaram": float(passaram.mean()),
            "tempo": float((self.t_fim[suc] * self.dt).mean()) if suc.any() else 0.0,
            "parou": float((self.parado > 0.25).mean()),                  # carros que esperaram parados
            "alterna": float(alterna[suc].mean()) if suc.any() else 0.0,  # revezamento entre as ruas
            # regra "quem chega primeiro passa primeiro": a 1ª rua a entrar é a do carro que chegaria antes
            "regra": float((self.eixo[np.argmin(np.where(self.t_entra < 0, 1e9, self.t_entra), 1)]
                            == self.eixo[np.argmin(self.eta0, 1)])[suc].mean()) if suc.any() else 0.0,
        }

    def chegou_mas_bateu(self):
        return int((self.bateu & ((self.t_passou >= 0).sum(1) >= 1)).sum())
