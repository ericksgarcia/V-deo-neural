"""Desafio: um drone cruza uma tempestade (vento em rajadas + raios avisados) e pousa na plataforma.

Vista de lado. O vento é o mesmo para toda a população em uma geração e muda de uma geração para a outra,
então a rede não pode decorar o clima: tem que aprender a lidar com ele.
"""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

CAUSA_RAIO, CAUSA_CHAO, CAUSA_SAIU = 1, 2, 3


class Drone:
    nome = "drone"
    camadas = (11, 12, 2)
    dt = 1 / 30
    passos = 600  # 20 s
    mundo = (-22.0, 22.0, 0.0, 20.0)

    g = 4.0
    empuxo_max = 2.2 * g
    giro_max = 3.0
    pad_x, pad_meia = 15.0, 2.4
    bateria_s = 7.0          # segundos de motor no máximo (pairar gasta ~45% disso)
    arrasto = 0.6            # o ar puxa o drone para a velocidade do vento
    aviso, golpe, raio_larg = 1.2, 0.2, 1.7   # s de aviso, s de duração do raio, meia largura (m)
    zona = 4.5                                  # "na rota do raio": a menos de 4,5 m da coluna quando o aviso começa
    ga = {"elite": 10, "taxa": 0.1, "forca": 0.2}

    def __init__(self, n, rng, ruido=1.0):
        self.n = n
        x = np.full(n, -17.0) + rng.normal(0, 0.8, n)
        y = np.full(n, 9.0) + rng.normal(0, 0.8, n)
        vx = rng.normal(0, 0.6, n)
        vy = rng.normal(0, 0.6, n)
        ang = rng.normal(0, 0.05, n)
        self.s = np.stack([x, y, vx, vy, ang, np.zeros(n)], 1)   # x y vx vy ângulo giro
        self.bat = np.ones(n)
        self.estado = np.zeros(n, np.int8)
        self.causa = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros((n, 2))       # empuxo dos rotores esquerdo e direito (para desenhar)
        self.impacto = np.zeros(n)
        self.dx_final = np.zeros(n)
        self.chegou = np.zeros(n, bool)    # chegou a 4 m da plataforma
        self.t = 0.0
        self.visto = [False] * 3
        self.risco = [np.zeros(n, bool) for _ in range(3)]   # estavam na zona do raio quando o aviso começou
        self.n_risco = self.n_fritado = 0
        # tempestade desta geração
        self.W = ruido * rng.uniform(3.2, 4.2)
        self.fase = rng.uniform(0, 2 * np.pi, 3)
        self.vies = rng.uniform(-0.25, 0.25)             # tendência média (a favor ou contra)
        ts = np.sort(rng.uniform(3.0, 11.0, 3))
        for k in range(1, 3):                           # raios espaçados
            ts[k] = max(ts[k], ts[k - 1] + 2.2)
        self.raios = [(float(t), float(rng.uniform(-9, 11))) for t in ts]

    # ------------------------------------------------------------ ambiente
    def vento(self, x, y, t):
        f = self.fase
        w = (0.55 * np.sin(2 * np.pi * (t / 5.5 - x / 45) + f[0]) + 0.45 * np.sin(2 * np.pi * (t / 2.6 + x / 19) + f[1])
             + self.vies)
        return self.W * w * (1 + 0.025 * np.asarray(y))

    def sopro_vertical(self, x, t):
        return 0.3 * self.W * np.sin(2 * np.pi * (t / 3.1 - x / 13) + self.fase[2])

    def raio_ativo(self, t):
        """(x, aviso 0-1, golpe) do raio mais próximo de cair ou caindo; None se não há."""
        for ts, xb in self.raios:
            if ts - self.aviso <= t <= ts + self.golpe:
                return xb, min(max((t - (ts - self.aviso)) / self.aviso, 0.0), 1.0), t >= ts
        return None

    # ------------------------------------------------------------ simulação
    def observa(self):
        x, y, vx, vy, a, w = self.s.T
        r = self.raio_ativo(self.t)
        if r is None:
            dxb, av = np.zeros(self.n), np.zeros(self.n)
        else:
            dxb, av = np.clip((x - r[0]) / 6, -1, 1), np.full(self.n, r[1])
        wv = self.vento(x, y, self.t)
        return np.stack([(x - self.pad_x) / 20, y / 10, vx / 8, vy / 8, np.sin(a), np.cos(a), w / 3,
                         self.bat * 2 - 1, wv / 8, dxb, av], 1).astype(np.float32)

    def passo(self, saida, t):
        self.t = t * self.dt
        vivo = self.estado == VOANDO
        com = (saida[:, 0] + 1) / 2
        dif = saida[:, 1] * 0.5
        esq = np.clip(com - dif, 0, 1) * (self.bat > 0)
        dir_ = np.clip(com + dif, 0, 1) * (self.bat > 0)
        thr = (esq + dir_) / 2
        x, y, vx, vy, a, w = self.s.T.copy()
        w = w + ((esq - dir_) * self.giro_max * 1.6 - 0.8 * w) * self.dt   # esquerdo mais forte = inclina para +x
        a = a + w * self.dt
        wv = self.vento(x, y, self.t)
        ax = np.sin(a) * thr * self.empuxo_max + self.arrasto * (wv - vx)
        ay = np.cos(a) * thr * self.empuxo_max - self.g + self.arrasto * (self.sopro_vertical(x, self.t) - vy) * 0.5
        vx, vy = vx + ax * self.dt, vy + ay * self.dt
        x, y = x + vx * self.dt, y + vy * self.dt
        novo = np.stack([x, y, vx, vy, a, w], 1)
        self.s[vivo] = novo[vivo]
        self.bat[vivo] = np.maximum(0, self.bat[vivo] - thr[vivo] * self.dt / self.bateria_s)
        self.acel = np.where(vivo[:, None], np.stack([esq, dir_], 1), 0)

        x, y, vx, vy, a, w = self.s.T
        self.chegou |= vivo & (np.hypot(x - self.pad_x, y) < 4.5)
        r = self.raio_ativo(self.t)
        atingido = np.zeros(self.n, bool)
        if r is not None and r[2]:
            atingido = vivo & (np.abs(x - r[0]) < self.raio_larg)
        for k, (ts, xb) in enumerate(self.raios):
            if self.t >= ts - self.aviso and not self.visto[k]:       # começa o aviso: quem está perto da coluna?
                self.visto[k] = True
                self.risco[k] = vivo & (np.abs(x - xb) < self.zona)
                self.n_risco += int(self.risco[k].sum())
            if r is not None and r[2] and abs(r[0] - xb) < 1e-9:
                self.n_fritado += int((atingido & self.risco[k]).sum())
        tocou = vivo & ~atingido & (y <= 0)
        fora = vivo & ~atingido & ~tocou & ((np.abs(x) > 26) | (y > 22))
        no_pad = np.abs(x - self.pad_x) <= self.pad_meia
        ok = tocou & no_pad & (np.abs(vy) <= 2.8) & (np.abs(vx) <= 2.2) & (np.abs(a) <= 0.3)
        self.impacto[tocou] = np.hypot(vx, vy)[tocou]
        self.impacto[fora | atingido] = 30
        self.s[tocou, 1] = 0
        self.estado[ok] = SUCESSO
        self.estado[(tocou & ~ok) | fora | atingido] = FALHA
        self.causa[atingido] = CAUSA_RAIO
        self.causa[tocou & ~ok] = CAUSA_CHAO
        self.causa[fora] = CAUSA_SAIU
        acabou = tocou | fora | atingido
        self.t_fim[acabou] = t
        self.dx_final[acabou] = np.abs(x - self.pad_x)[acabou]

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        self.estado[vivo] = FALHA
        self.causa[vivo] = CAUSA_SAIU
        self.t_fim[vivo] = t
        self.dx_final[vivo] = np.abs(self.s[vivo, 0] - self.pad_x)
        self.impacto[vivo] = 30

    def aptidao(self):
        x, y, vx, vy, a, w = self.s.T
        perto = 1 - np.minimum(np.hypot(x - self.pad_x, y) / 40, 1)
        suave = np.exp(-self.impacto / 5)
        reto = 1 - np.minimum(np.abs(a) / 1.5, 1)
        f = 2 * perto + perto ** 2 * (3 * suave + 0.5 * reto) - 0.5 * (self.causa == CAUSA_RAIO)
        return f + (self.estado == SUCESSO) * (5 + 2 * self.bat)

    def metricas(self):
        suc = self.estado == SUCESSO
        return {
            "raio": float((self.causa == CAUSA_RAIO).mean()),     # fritos por raio
            "risco": float(self.n_risco),                         # drones que estavam na rota de um raio
            "fritado": float(self.n_fritado),                     # ... e foram atingidos
            "desvio": 1 - self.n_fritado / self.n_risco if self.n_risco else 1.0,   # escaparam do raio
            "perto": float(self.chegou.mean()),                   # chegaram a 4,5 m da plataforma
            "bat": float(self.bat[suc].mean()) if suc.any() else 0.0,   # bateria que sobrou nos que pousaram
            "tempo": float((self.t_fim[suc] * self.dt).mean()) if suc.any() else 0.0,
        }

    def chegou_mas_bateu(self):
        return int(((self.estado == FALHA) & (self.dx_final <= self.pad_meia) & (self.causa == CAUSA_CHAO)).sum())
