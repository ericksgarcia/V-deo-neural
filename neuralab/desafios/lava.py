"""Desafio: o chão é lava (vista de lado). 8 IAs (o mesmo cérebro em todas) começam no chão de uma torre de
plataformas; a lava sobe sem parar. Cada "indivíduo" da população é uma torre inteira com 8 IAs.

Mundo em metros: x para a direita (0..LARG), y para cima (0 = chão, onde a lava nasce). Cada IA é uma caixa
(largura W_AG, altura H_AG, y = pés). Plataformas são "de mão única": dá para atravessar por baixo e pousar por
cima. Uma IA também pode pousar na CABEÇA de outra (vira degrau). Nada é programado: a rede só escolhe andar e pular.
Sucesso = pelo menos MIN_VIVAS das IAs ainda fora da lava quando o tempo acaba.
"""
import numpy as np

from .foguete import VOANDO, SUCESSO, FALHA

LARG = 14.0
G = 22.0
V_PULO, V_MAX, A_CHAO, A_AR = 8.6, 4.2, 22.0, 11.0
W_AG, H_AG = 0.5, 0.55
LAVA_V0, LAVA_ACEL = 0.26, 0.008       # a lava sobe a LAVA_V0 m/s e acelera um pouco
N_PLAT = 6
Y0, DY = 1.45, 1.45                    # altura da 1ª plataforma e espaço vertical médio entre elas
TOPO = Y0 + DY * (N_PLAT - 1)          # altura da plataforma mais alta
MIN_VIVAS = 4


def lava_y(seg):
    return LAVA_V0 * seg + 0.5 * LAVA_ACEL * seg * seg


class Lava:
    nome = "lava"
    camadas = (14, 12, 3)
    dt = 1 / 30
    passos = 450            # 15 s
    n_ag = 8
    ga = {"elite": 8, "taxa": 0.1, "forca": 0.2}

    def __init__(self, n, rng, ruido=0.25, por_mundo=False):
        self.n = n
        N = self.N = self.n_ag
        f = n if por_mundo else 1
        # layout: 6 plataformas de largura ~3,6 m, escalonadas; o chão (y = 0) cobre tudo
        ln = np.arange(N_PLAT)
        cx = 7.0 + np.where(ln % 2 == 0, -1, 1) * (2.2 + 1.2 * ruido * (rng.random((f, N_PLAT)) * 2 - 1) * 0.5)
        cx = np.clip(cx, 2.3, LARG - 2.3)
        larg = 3.6 - 0.35 * ruido * rng.random((f, N_PLAT))
        alt = Y0 + DY * ln + ruido * 0.12 * (rng.random((f, N_PLAT)) * 2 - 1)
        plat = np.stack([cx - larg / 2, cx + larg / 2, alt], -1)       # (f, M, 3): x0, x1, topo
        piso = np.broadcast_to(np.array([[[0.0, LARG, 0.0]]]), (f, 1, 3))
        plat = np.concatenate([piso, plat], 1)
        self.plat = np.broadcast_to(plat, (n,) + plat.shape[1:]).copy()
        x = 1.5 + rng.random((f, N)) * (LARG - 3.0)
        x, = (np.broadcast_to(a, (n,) + a.shape[1:]).copy() for a in (x,))
        self.s = np.stack([x, np.zeros_like(x), np.zeros_like(x), np.zeros_like(x)], -1)     # x, y(pés), vx, vy
        self.chao = np.ones((n, N), bool)
        self.sobre = np.full((n, N), -1)           # índice da IA em cima da qual está (ou -1)
        self.viva = np.ones((n, N), bool)
        self.t_morte = np.full((n, N), -1.0)
        self.y_max = np.zeros((n, N))
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.acel = np.zeros((n, N, 2))
        self.lava = 0.0
        # métricas
        self.t_degrau = np.zeros((n, N))           # segundos de pé na cabeça de outra IA
        self.foi_degrau = np.zeros((n, N), bool)   # já serviu de degrau para alguém
        self.subiu_por_cima = np.zeros((n, N), bool)   # pulou da cabeça de outra e pousou numa plataforma mais alta
        self.nivel_deg = np.zeros((n, N))          # nível (altura) onde estava ao sair da cabeça
        self.pulos = np.zeros((n, N))

    # ------------------------------------------------------------------ percepção
    def observa(self):
        x, y, vx, vy = (self.s[..., i] for i in range(4))
        # plataforma mais "útil" acima (a mais baixa cujo topo está acima dos pés)
        topo = self.plat[..., 2][:, None, :]                                   # (P,1,M)
        x0, x1 = self.plat[..., 0][:, None, :], self.plat[..., 1][:, None, :]
        acima = topo > (y[..., None] + 0.05)
        dxb = np.maximum(np.maximum(x0 - x[..., None], x[..., None] - x1), 0)       # distância horizontal à borda
        custo = np.where(acima, (topo - y[..., None]) + 1.0 * dxb, 99.0)
        k = custo.argmin(2)
        ex = np.take_along_axis(np.broadcast_to(x0 + x1, custo.shape), k[..., None], 2)[..., 0] / 2
        et = np.take_along_axis(np.broadcast_to(topo, custo.shape), k[..., None], 2)[..., 0]
        hx = np.take_along_axis(np.broadcast_to((x1 - x0) / 2, custo.shape), k[..., None], 2)[..., 0]
        tem = (custo.min(2) < 90)
        dx = np.where(tem, (ex - x) / 4, 0.0)
        dy = np.where(tem, (et - y) / 2, 0.0)
        # a IA viva mais próxima
        dxa = self.s[:, None, :, 0] - x[:, :, None]
        dya = self.s[:, None, :, 1] - y[:, :, None]
        d = np.sqrt(dxa ** 2 + dya ** 2) + np.eye(self.N)[None] * 99 + (~self.viva)[:, None, :] * 99
        j = d.argmin(2)
        ok = np.take_along_axis(d, j[..., None], 2)[..., 0] < 2.5
        ax = np.where(ok, np.take_along_axis(dxa, j[..., None], 2)[..., 0] / 2.5, 0.0)
        ay = np.where(ok, np.take_along_axis(dya, j[..., None], 2)[..., 0] / 2.5, 0.0)
        folga = (y - self.lava) / 3
        return np.stack([x / LARG * 2 - 1, y / TOPO, vx / V_MAX, vy / V_PULO, self.chao * 1.0,
                         np.clip(folga, -1, 2), dx, dy, np.clip(hx / 2, 0, 1), ax, ay,
                         (self.sobre >= 0) * 1.0, np.full_like(x, np.sin(self.passo_t * 0.0)),
                         np.full_like(x, self.lava / TOPO)], -1).astype(np.float32)

    passo_t = 0

    # ------------------------------------------------------------------ física
    def passo(self, saida, t):
        self.passo_t = t
        vivo = self.estado == VOANDO
        seg = t * self.dt
        self.lava = lava_y(seg)
        ativa = self.viva & vivo[:, None]
        cmd = np.clip(saida, -1, 1)
        self.acel = np.where(ativa[..., None], cmd[..., :2], 0.0)
        x, y, vx, vy = (self.s[..., i].copy() for i in range(4))
        # horizontal
        a = np.where(self.chao, A_CHAO, A_AR)
        alvo = cmd[..., 0] * V_MAX
        vx = np.where(ativa, vx + np.clip(alvo - vx, -a * self.dt, a * self.dt), 0.0)
        # pulo (precisa estar apoiada)
        pula = ativa & self.chao & (cmd[..., 1] > 0.35)
        saiu_de_cima = pula & (self.sobre >= 0)
        self.nivel_deg = np.where(saiu_de_cima, y, self.nivel_deg)
        self.pulos += pula
        vy = np.where(pula, V_PULO, vy)
        self.chao = np.where(pula, False, self.chao)
        # IAs que estavam em cima de outra e a outra morreu/saiu: caem
        suporte_ok = (self.sobre >= 0)
        if suporte_ok.any():
            j = np.maximum(self.sobre, 0)
            xj = np.take_along_axis(self.s[..., 0], j, 1)
            yj = np.take_along_axis(self.s[..., 1], j, 1)
            vj = np.take_along_axis(self.viva, j, 1)
            ainda = suporte_ok & vj & (np.abs(x - xj) < W_AG * 0.95) & (np.abs(y - (yj + H_AG)) < 0.12)
            self.chao = np.where(suporte_ok & ~ainda & ~pula, False, self.chao)
            self.sobre = np.where(ainda & ~pula, self.sobre, -1)
        # vertical
        y_ant = y.copy()
        vy = np.where(self.chao & ativa, 0.0, vy - G * self.dt)
        y = np.where(ativa, y + vy * self.dt, y)
        # carona: quem está em cima de outra acompanha a altura dela
        # pouso em plataforma (só descendo)
        x0, x1, tp = (self.plat[..., k][:, None, :] for k in range(3))
        dentro = (x[..., None] > x0 - 0.12) & (x[..., None] < x1 + 0.12)
        cruza = (y_ant[..., None] >= tp - 1e-3) & (y[..., None] <= tp) & (vy[..., None] <= 0)
        pouso = dentro & cruza
        achou = pouso.any(2)
        alt_p = np.where(pouso, tp, -1e9).max(2)
        y = np.where(achou & ativa, alt_p, y)
        vy = np.where(achou & ativa, 0.0, vy)
        # pouso na cabeça de outra IA
        dxa = x[:, :, None] - x[:, None, :]                                   # i - j
        topo_j = (y_ant[:, None, :] + H_AG)                                     # topo de j (altura antiga)
        topo_j_n = (y[:, None, :] + H_AG)
        cab = (np.abs(dxa) < W_AG * 0.9) & self.viva[:, None, :] & ativa[:, :, None] & ~np.eye(self.N, dtype=bool)[None]
        desce = (vy[:, :, None] <= 0) & (y_ant[:, :, None] >= topo_j - 0.02) & (y[:, :, None] <= topo_j_n)
        pc = cab & desce
        acha_c = pc.any(2) & ~achou
        jc = np.where(pc, topo_j_n, -1e9).argmax(2)
        alt_c = np.take_along_axis(np.broadcast_to(topo_j_n, pc.shape), jc[..., None], 2)[..., 0]
        y = np.where(acha_c, alt_c, y)
        vy = np.where(acha_c, 0.0, vy)
        # estado de apoio
        pousou_agora = (achou | acha_c) & ativa
        self.sobre = np.where(acha_c, jc, np.where(achou, -1, self.sobre))
        # se cai da plataforma (sem apoio): chão = False; verifica apoio atual
        sobre_plat = (dentro & (np.abs(y[..., None] - tp) < 1e-3)).any(2)
        sobre_ag = self.sobre >= 0
        apoiada = (sobre_plat | sobre_ag) & (vy <= 0)
        self.chao = np.where(ativa, apoiada | pousou_agora, self.chao)
        # IA que estava em cima de uma e agora pousou numa plataforma mais alta
        subiu = achou & ativa & (self.nivel_deg > 0) & (alt_p > self.nivel_deg + 0.3)
        self.subiu_por_cima |= subiu
        self.nivel_deg = np.where(achou, 0.0, self.nivel_deg)
        # contabiliza degrau
        self.t_degrau += (self.sobre >= 0) * ativa * self.dt
        if (self.sobre >= 0).any():
            alvo_i = np.where(self.sobre >= 0, self.sobre, 0)
            marca = np.zeros_like(self.foi_degrau)
            idx = np.nonzero(self.sobre >= 0)
            marca[idx[0], alvo_i[idx]] = True
            self.foi_degrau |= marca
        # integra
        x = np.clip(x + vx * self.dt, W_AG / 2, LARG - W_AG / 2)
        self.s[..., 0], self.s[..., 1], self.s[..., 2], self.s[..., 3] = x, y, vx, vy
        self.y_max = np.maximum(self.y_max, np.where(self.viva, y, 0))
        # lava
        morre = ativa & (y < self.lava)
        self.viva &= ~morre
        self.t_morte[morre] = seg
        vivas = self.viva.sum(1)
        if t >= self.passos - 1:
            pass
        self.t_fim_cand = vivas

    def finaliza(self, t):
        vivo = self.estado == VOANDO
        ok = vivo & (self.viva.sum(1) >= MIN_VIVAS)
        self.estado[ok] = SUCESSO
        self.estado[vivo & ~ok] = FALHA
        self.t_fim[vivo] = t

    def extra(self):
        """Gravado por passo: [nível da lava, índice da IA sob cada IA (-1 = nenhuma)...]."""
        return np.concatenate([np.full((self.n, 1), self.lava), self.sobre], 1)

    # ------------------------------------------------------------------ avaliação
    def aptidao(self):
        tmax = self.passos * self.dt
        tv = np.where(self.viva, tmax, np.where(self.t_morte >= 0, self.t_morte, 0)) / tmax
        alt = self.y_max / TOPO
        vivas = self.viva.mean(1)
        return 2.0 * vivas + 1.0 * tv.mean(1) + 0.8 * alt.mean(1) + (self.viva.sum(1) >= MIN_VIVAS) * 2

    def metricas(self):
        return {
            "vivas": float(self.viva.sum(1).mean()),
            "alt": float(self.y_max.mean()),
            "degrau": float((self.t_degrau >= 0.5).mean()),         # fração das IAs que ficaram 0,5 s+ na cabeça de outra
            "serviu": float(self.foi_degrau.mean()),                # fração das IAs que serviram de degrau
            "subiu": float(self.subiu_por_cima.mean()),             # pularam da cabeça de outra e pousaram mais alto
            "topo": float((self.y_max >= TOPO - 0.05).any(1).mean()),
            "pulos": float(self.pulos.mean()),
        }

    def chegou_mas_bateu(self):
        return int(((self.viva.sum(1) >= 1) & (self.estado == FALHA)).sum())
