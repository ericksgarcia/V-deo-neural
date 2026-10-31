"""Desafio: Dança das Cadeiras. 12 IAs (o MESMO cérebro nas 12) e 11 cadeiras em roda; a música toca, depois para, e quem
ficar sem cadeira sai. Arena em pé (12 x 14 m).

Regras escritas à mão: cadeira ocupada fica da primeira IA que chega (a mais perto, se duas chegam no mesmo instante);
quem senta fica parada na cadeira. Só vale sentar depois que a música para. As IAs se empurram de verdade (corpos sólidos).
Ninguém recebe a regra de "escolher cadeira livre", "esperar do lado da cadeira" ou "empurrar": a IA vê onde está,
a cadeira livre mais perto (e se alguém chega nela antes), a segunda mais perto, o vizinho mais próximo e se a música está tocando.
Nota = cadeiras ocupadas no fim + um pouco por ocupar cedo.
"""
import numpy as np

LARG, ALT = 12.0, 14.0
CX, CY = LARG / 2, ALT / 2
N, C = 12, 11                               # IAs e cadeiras
RC = 2.9                                    # raio da roda de cadeiras
R_AG, R_SENTA = 0.38, 0.5
V_MAX, ACEL = 3.4, 13.0
DT = 1 / 15
T_MUSICA, T_CORRE = 2.5, 3.4                # s
KM = int(round(T_MUSICA / DT))
PASSOS = KM + int(round(T_CORRE / DT))
CAMADAS = (14, 12, 2)
CADEIRAS = np.array([(CX + RC * np.cos(2 * np.pi * k / C + 0.3), CY + RC * np.sin(2 * np.pi * k / C + 0.3)) for k in range(C)], np.float32)


class Rodada:
    nome = "cadeiras"
    camadas = CAMADAS
    dt, passos = DT, PASSOS

    def __init__(self, n, rng):
        self.n = n
        ang = rng.uniform(0, 2 * np.pi, (n, N))
        # espalha as IAs numa faixa em volta da roda, sem empilhar na largada
        ang = (np.arange(N)[None] * 2 * np.pi / N + rng.uniform(-0.35, 0.35, (n, N)) + rng.uniform(0, 2 * np.pi, (n, 1)))
        raio = rng.uniform(3.9, 5.2, (n, N))
        self.p = np.stack([CX + raio * np.cos(ang), CY + raio * np.sin(ang)], -1).astype(np.float32)
        self.v = np.zeros((n, N, 2), np.float32)
        self.senta = np.full((n, N), -1, np.int32)           # cadeira em que sentou (-1 = em pé)
        self.dono = np.full((n, C), -1, np.int32)            # IA sentada em cada cadeira
        self.t_senta = np.full((n, N), np.nan, np.float32)
        self.k = 0
        self.m = {k: np.zeros(n) for k in ("colado", "vel_mus", "junto", "toque", "disputa", "gsum", "gabs")}
        self.n_mus = 0
        self.n_corre = 0

    def musica(self):
        return self.k < KM

    def observa(self):
        n, p, v = self.n, self.p, self.v
        em_pe = self.senta < 0
        livre = self.dono < 0
        ch = CADEIRAS[None]                                                    # (1,C,2)
        D = np.hypot(p[:, :, None, 0] - ch[:, None, :, 0], p[:, :, None, 1] - ch[:, None, :, 1])   # (n,N,C)
        Dl = np.where(livre[:, None, :], D, 1e9)
        ordem = np.argsort(Dl, 2)
        i1, i2 = ordem[..., 0], ordem[..., 1]
        lin = np.arange(n)[:, None]
        c1, c2 = CADEIRAS[i1], CADEIRAS[i2]                                    # (n,N,2)
        d1 = np.take_along_axis(Dl, i1[..., None], 2)[..., 0]
        # alguém chega antes na minha cadeira mais perto?
        Dt = D.transpose(0, 2, 1)[lin, i1]                                     # (n,N,N): [n,i,j] = dist de j a cadeira alvo de i
        Dt = np.where(np.eye(N, dtype=bool)[None] | ~em_pe[:, None, :], 1e9, Dt)
        rival = Dt.min(2) - d1                                                 # >0: eu chego antes
        # vizinho em pé mais perto
        dx, dy = p[:, None, :, 0] - p[:, :, None, 0], p[:, None, :, 1] - p[:, :, None, 1]
        dd = np.hypot(dx, dy) + np.eye(N)[None] * 1e9
        dd = np.where(em_pe[:, None, :], dd, 1e9)
        j = dd.argmin(2)
        viz = np.stack([np.take_along_axis(dx, j[..., None], 2)[..., 0], np.take_along_axis(dy, j[..., None], 2)[..., 0]], -1)
        musica = np.full((n, N, 1), 1.0 if self.musica() else 0.0, np.float32)
        tempo = np.full((n, N, 1), max(self.k - KM, 0) * DT / T_CORRE, np.float32)
        nlivres = np.broadcast_to((livre.sum(1) / C)[:, None, None], (n, N, 1))
        obs = np.concatenate([
            ((p - np.array([CX, CY], np.float32)) / 6.0), v / V_MAX, musica, tempo,
            np.clip((c1 - p) / 6.0, -1, 1), np.clip(rival[..., None] / 3.0, -1, 1),
            np.clip((c2 - p) / 6.0, -1, 1), np.clip(viz / 3.0, -1, 1), nlivres], -1)
        self._D, self._livre = D, livre
        return obs.astype(np.float32)

    def passo(self, acao):
        n, p, v = self.n, self.p, self.v
        em_pe = self.senta < 0
        musica = self.musica()
        # métricas (antes de mover)
        dmin = self._D.min(2)
        if musica:
            self.n_mus += 1
            sp = np.hypot(v[..., 0], v[..., 1])
            self.m["colado"] += ((dmin < 1.0) & em_pe).sum(1) / N
            self.m["vel_mus"] += sp.mean(1)
            cr = (p[..., 0] - CX) * v[..., 1] - (p[..., 1] - CY) * v[..., 0]
            self.m["gsum"] += cr.sum(1)
            self.m["gabs"] += np.abs(cr).sum(1)
        else:
            self.n_corre += 1
            # duas ou mais IAs em pé coladas na mesma cadeira livre
            perto = (self._D < 1.0) & em_pe[:, :, None] & self._livre[:, None, :]
            self.m["junto"] += (perto.sum(1) >= 2).sum(1) / C
        # movimento
        a = np.clip(acao, -1, 1)
        v = v + a * ACEL * DT - 0.8 * v * DT
        sp = np.hypot(v[..., 0], v[..., 1])[..., None]
        v = v * np.minimum(1.0, V_MAX / np.maximum(sp, 1e-6))
        v = np.where(em_pe[..., None], v, 0.0)
        p = p + v * DT
        # corpos sólidos: empurram quem está em pé; quem está sentado é imóvel
        for _ in range(2):
            dx, dy = p[:, None, :, 0] - p[:, :, None, 0], p[:, None, :, 1] - p[:, :, None, 1]
            d = np.hypot(dx, dy) + np.eye(N)[None] * 1e9
            ov = np.clip(2 * R_AG - d, 0, None)
            if not musica and _ == 0:
                self.m["toque"] += ((ov > 0).any(2) & em_pe).sum(1) / N        # fração das IAs em pé que esbarram em alguém
            peso_i = em_pe[:, :, None].astype(np.float32)
            peso_j = em_pe[:, None, :].astype(np.float32)
            tot = np.maximum(peso_i + peso_j, 1e-6)
            f = ov / np.maximum(d, 1e-6)
            mi = (peso_i / tot) * (peso_i > 0)                       # parte do deslocamento que cabe a i
            p[..., 0] += (-dx * f * mi).sum(2)
            p[..., 1] += (-dy * f * mi).sum(2)
        p[..., 0] = np.clip(p[..., 0], R_AG, LARG - R_AG)
        p[..., 1] = np.clip(p[..., 1], R_AG, ALT - R_AG)
        # sentar: só depois da música
        self.k += 1
        if self.k > KM:
            self._senta(p, v)
        self.p, self.v = p.astype(np.float32), v.astype(np.float32)

    def _senta(self, p, v):
        n = self.n
        em_pe = self.senta < 0
        livre = self.dono < 0
        D = np.hypot(p[:, :, None, 0] - CADEIRAS[None, None, :, 0], p[:, :, None, 1] - CADEIRAS[None, None, :, 1])
        cand = (D < R_SENTA) & em_pe[:, :, None] & livre[:, None, :]
        Dm = np.where(cand, D, 1e9)
        venc = Dm.argmin(1)                                          # (n,C): IA mais perto de cada cadeira
        ok = cand.any(1)                                             # (n,C)
        # uma IA só senta em uma cadeira: a mais perto entre as que ela alcança
        for c in range(C):
            ag = venc[:, c]
            lin = np.where(ok[:, c] & (self.senta[np.arange(n), ag] < 0))[0]
            if len(lin):
                self.senta[lin, ag[lin]] = c
                self.dono[lin, c] = ag[lin]
                self.t_senta[lin, ag[lin]] = (self.k - KM) * DT
                p[lin, ag[lin]] = CADEIRAS[c]
                v[lin, ag[lin]] = 0.0

    def acabou(self):
        return False

    def finaliza(self):
        self.m["disputa"] = self.m["junto"] / max(self.n_corre, 1)

    def cheias(self):
        return (self.dono >= 0).sum(1)

    def aptidoes(self):
        cheias = self.cheias() / C
        ts = np.where(np.isnan(self.t_senta), T_CORRE, self.t_senta)
        cedo = np.where(self.senta >= 0, 1 - ts / T_CORRE, 0).sum(1) / C
        return cheias + 0.15 * cedo
