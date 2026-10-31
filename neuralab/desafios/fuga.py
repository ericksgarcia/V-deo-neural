"""Desafio: Fuga com Cobertura. 12 IAs azuis atravessam a zona de tiro de uma torreta, de baixo para cima, até a linha de chegada.

Mundo 2D visto de cima, ARENA EM PÉ (14 x 22 m). A torreta (centro) e os 4 blocos que deslizam são PROGRAMADOS e fixos; só o
cérebro azul evolui (os 12 azuis de uma cidade usam o MESMO cérebro). Ninguém recebe regra de "esconder", "zigue-zague" ou "esperar":
só vê a posição, a torreta, a bala mais próxima, o bloco mais próximo e se há um bloco entre ele e a torreta. Nota = quão longe chega
(mais bônus por chegar). A torreta mira um azul qualquer dentro do alcance, sem prever o movimento, e erra um pouco; bala lenta e visível.

Curadoria (31/out/2026, autorizada pelo dono): bala visível (8 m/s), 1 tiro a cada 0,8 s, pequeno erro de mira; zona de tiro de 10,5 m.
"""
import numpy as np

LARG, ALT = 14.0, 22.0
A = 12                                    # azuis por cidade
RAIO = 0.3
V_MAX, ACEL = 3.0, 12.0
DT, PASSOS = 1 / 15, 300                  # 20 s por cidade
TX, TY = LARG / 2, 11.0                   # torreta
ALCANCE = 10.5
V_BALA, CAD, ERRO_MIRA = 11.0, 2, 0.035
NB = 6                                    # balas em voo (anel)
K = 4                                     # blocos
BLOCO_Y = np.array([5.0, 7.5, 14.5, 17.0], np.float32)
BLOCO_HW, BLOCO_HH, BLOCO_V = 1.8, 0.3, 1.2
BLOCO_AMP = 5.0
CHEGADA = ALT - 1.5
CAMADAS = (16, 12, 2)


class Cidade:
    nome = "fuga"
    camadas = CAMADAS
    dt, passos = DT, PASSOS

    def __init__(self, n, rng):
        self.n = n
        u = rng.uniform(0.0, 1.0, (n, A, 2))                         # sorteio único: as n primeiras cidades não dependem de n
        self.p = (np.stack([1.0 + u[..., 0] * (LARG - 2.0), 1.0 + u[..., 1] * 2.0], -1)).astype(np.float32)
        self.v = np.zeros((n, A, 2), np.float32)
        self.vivo = np.ones((n, A), bool)
        self.chegou = np.zeros((n, A), bool)
        self.t_chegou = np.full((n, A), -1, np.int32)
        self.t_morte = np.full((n, A), -1, np.int32)
        self.ymax = self.p[..., 1].copy()
        self.fase = rng.uniform(0, 2 * np.pi, (n, K)).astype(np.float32)
        self.bp = np.zeros((n, NB, 2), np.float32)
        self.bv = np.zeros((n, NB, 2), np.float32)
        self.bvivo = np.zeros((n, NB), bool)
        self.disparos = 0
        self.rng = np.random.default_rng(int(rng.integers(1 << 30)))
        self.k = 0
        self.s_atras = np.zeros(n)
        self.s_zona = np.zeros(n)
        self.s_lat = np.zeros(n)
        self.s_vivo = np.zeros(n)

    def blocos(self, k=None):
        """Centro x dos blocos no passo k: deslizam de um lado a outro (determinístico pela fase da cidade)."""
        k = self.k if k is None else k
        w = BLOCO_V / BLOCO_AMP
        sinal = np.where(np.arange(K) % 2 == 0, 1.0, -1.0)
        return (LARG / 2 + BLOCO_AMP * np.sin(w * k * DT * sinal + self.fase)).astype(np.float32)   # (n, K)

    def _coberto(self, bx):
        """True se há um bloco entre o azul e a torreta (segmento azul -> torreta atravessa o bloco)."""
        px, py = self.p[..., 0][:, :, None], self.p[..., 1][:, :, None]
        cy = BLOCO_Y[None, None, :]
        den = np.where(np.abs(TY - py) < 1e-3, 1e-3, TY - py)
        t = (cy - py) / den
        x_em = px + t * (TX - px)
        ok = (t > 0) & (t < 1) & (np.abs(x_em - bx[:, None, :]) < BLOCO_HW + 0.2)
        return ok.any(2)

    def observa(self):
        self.bx = self.blocos()
        bx = self.bx
        n = self.n
        x, y = self.p[..., 0], self.p[..., 1]
        dxt, dyt = TX - x, TY - y
        dt_ = np.hypot(dxt, dyt)
        coberto = self._coberto(bx)
        # bala mais próxima
        db = np.hypot(self.bp[:, None, :, 0] - x[:, :, None], self.bp[:, None, :, 1] - y[:, :, None])
        db = np.where(self.bvivo[:, None, :], db, 1e9)
        jb = db.argmin(2)
        lin = np.arange(n)[:, None]
        tem_b = db.min(2) < 6.0
        rb = (self.bp[lin, jb] - self.p) / 6.0
        vb = self.bv[lin, jb] / V_BALA
        rb = np.where(tem_b[..., None], rb, 0.0)
        vb = np.where(tem_b[..., None], vb, 0.0)
        # bloco mais próximo
        dbl = np.hypot(bx[:, None, :] - x[:, :, None], BLOCO_Y[None, None, :] - y[:, :, None])
        jk = dbl.argmin(2)
        rk = np.stack([(bx[lin, jk] - x) / 6.0, (BLOCO_Y[jk] - y) / 6.0], -1)
        sinal = np.where(jk % 2 == 0, 1.0, -1.0)
        w = BLOCO_V / BLOCO_AMP
        vk = (BLOCO_AMP * w * np.cos(w * self.k * DT * sinal + self.fase[lin, jk]) * sinal / BLOCO_V)[..., None]
        obs = np.concatenate([
            ((x - LARG / 2) / (LARG / 2))[..., None], ((y - 11.0) / 11.0)[..., None],
            self.v / V_MAX,
            ((CHEGADA - y) / ALT)[..., None],
            np.clip(np.stack([dxt, dyt], -1) / 10.0, -1, 1), (dt_ < ALCANCE)[..., None].astype(np.float32),
            np.clip(rb, -1, 1), vb, np.clip(rk, -1, 1), vk, coberto[..., None].astype(np.float32)], -1)
        # métricas desta passada (só azuis vivos que ainda não chegaram)
        ativo = self.vivo & ~self.chegou
        na = np.maximum(ativo.sum(1), 1)
        zona = ativo & (dt_ < ALCANCE)
        self.s_zona += zona.sum(1) / A
        self.s_atras += (zona & coberto).sum(1) / A
        self.s_lat += (np.abs(self.v[..., 0]) * ativo).sum(1) / na
        self.s_vivo += (self.vivo.sum(1)) / A
        return obs.astype(np.float32)

    def passo(self, acao):
        ativo = self.vivo & ~self.chegou
        a = np.where(ativo[..., None], acao, 0.0)
        v = self.v + a * ACEL * DT - 0.9 * self.v * DT
        vel = np.sqrt((v * v).sum(-1, keepdims=True))
        v = v * np.minimum(1.0, V_MAX / np.maximum(vel, 1e-6))
        v = np.where(ativo[..., None], v, 0.0)
        p = self.p + v * DT
        # azuis sólidos entre si
        dx = p[..., 0][:, None, :] - p[..., 0][:, :, None]
        dy = p[..., 1][:, None, :] - p[..., 1][:, :, None]
        d = np.sqrt(dx * dx + dy * dy)
        idx = np.arange(A)
        d[:, idx, idx] = 1e9
        w = (np.maximum(0.0, 2 * RAIO - d) / np.maximum(d, 1e-3)).astype(np.float32)
        p = p + 0.5 * (p * w.sum(2)[..., None] - w @ p) * ativo[..., None]
        # blocos sólidos (empurra pelo eixo de menor penetração)
        bx = self.blocos(self.k + 1)
        for j in range(K):
            ox = (BLOCO_HW + RAIO) - np.abs(p[..., 0] - bx[:, j][:, None])
            oy = (BLOCO_HH + RAIO) - np.abs(p[..., 1] - BLOCO_Y[j])
            dentro = (ox > 0) & (oy > 0)
            por_y = dentro & (oy < ox)
            por_x = dentro & ~por_y
            p[..., 1] = np.where(por_y, p[..., 1] + np.sign(p[..., 1] - BLOCO_Y[j]) * oy, p[..., 1])
            p[..., 0] = np.where(por_x, p[..., 0] + np.sign(p[..., 0] - bx[:, j][:, None]) * ox, p[..., 0])
        for ax, lim in ((0, LARG), (1, ALT)):
            baixo, alto = p[..., ax] < RAIO, p[..., ax] > lim - RAIO
            p[..., ax] = np.where(baixo, RAIO, np.where(alto, lim - RAIO, p[..., ax]))
            v[..., ax] = np.where(baixo | alto, 0.0, v[..., ax])
        self.p, self.v = p.astype(np.float32), v.astype(np.float32)
        # torreta: a cada CAD passos mira o azul mais perto (sem prever o movimento) com erro
        if self.k % CAD == 0:
            alvo_d = np.where(ativo, np.hypot(TX - self.p[..., 0], TY - self.p[..., 1]), 1e9)
            sorteio = np.where(alvo_d < ALCANCE, self.rng.random((self.n, A)), -1.0)   # um azul qualquer na zona de tiro
            j = sorteio.argmax(1)
            lin = np.arange(self.n)
            ok = sorteio[lin, j] >= 0
            ang = np.arctan2(self.p[lin, j, 1] - TY, self.p[lin, j, 0] - TX) + self.rng.normal(0, ERRO_MIRA, self.n)
            slot = self.disparos % NB
            self.bp[ok, slot] = (TX, TY)
            self.bv[ok, slot] = np.stack([np.cos(ang), np.sin(ang)], -1)[ok] * V_BALA
            self.bvivo[ok, slot] = True
            self.disparos += 1
        # balas: voam, somem em bloco/parede, acertam azul
        self.bp = self.bp + self.bv * DT
        for j in range(K):
            dentro = (np.abs(self.bp[..., 0] - bx[:, j][:, None]) < BLOCO_HW + 0.1) & (np.abs(self.bp[..., 1] - BLOCO_Y[j]) < BLOCO_HH + 0.25)
            self.bvivo &= ~dentro
        fora = (self.bp[..., 0] < 0) | (self.bp[..., 0] > LARG) | (self.bp[..., 1] < 0) | (self.bp[..., 1] > ALT)
        self.bvivo &= ~fora
        dist = np.hypot(self.bp[:, :, None, 0] - self.p[:, None, :, 0], self.bp[:, :, None, 1] - self.p[:, None, :, 1])
        acerto = (dist < RAIO + 0.15) & self.bvivo[:, :, None] & ativo[:, None, :]
        morre = acerto.any(1)
        self.bvivo &= ~acerto.any(2)
        self.t_morte = np.where(morre & (self.t_morte < 0), self.k, self.t_morte)
        self.vivo &= ~morre
        novo = self.vivo & ~self.chegou & (self.p[..., 1] >= CHEGADA)
        self.t_chegou = np.where(novo, self.k, self.t_chegou)
        self.chegou |= novo
        self.ymax = np.maximum(self.ymax, self.p[..., 1])
        self.k += 1

    def acabou(self):
        return False

    def finaliza(self):
        pass

    def aptidoes(self):
        """Nota por cidade: progresso médio dos azuis + bônus por chegar (mais rápido = mais) + um pouco por seguir vivo."""
        prog = np.clip((self.ymax - 2.0) / (CHEGADA - 2.0), 0, 1)
        rapido = np.where(self.chegou, 1.0 - self.t_chegou / PASSOS, 0.0)
        return (prog + 1.0 * self.chegou + 0.5 * rapido + 0.15 * self.vivo).mean(1)
