"""Desafio de dois lados: BATEDOR contra GOLEIRO, cobrança de pênalti (co-evolução).

Nada aqui codifica "truques". O batedor só controla o ritmo da corrida, para onde o corpo
aponta e o canto do chute; o goleiro só controla passos laterais e quando/para onde pular.
Finta, paradinha, goleiro paciente, cavadinha... ou surgem do treino ou não surgem.

Unidades: metros e segundos. x = lateral (0 = meio do gol), gol tem 7,32 m.
"""
import numpy as np

MEIO_GOL = 3.66
DT = 1 / 30
PASSOS = 110          # ~3,7 s gravados
LIMITE_CHUTE = 2.6    # o juiz não deixa enrolar: depois disso o chute sai apressado (e torto)
LEVANTA = 0.6         # quanto tempo o goleiro fica no chão depois do pulo
VOO = 0.40            # tempo da bola até a linha (s): ~100 km/h
CORRIDA = 1.0         # corrida a toda velocidade leva 1 s
GIRO_CORPO = 3.0      # unidades de corpo por segundo (corpo em [-1, 1])
PASSO_GOLEIRO = 1.5   # m/s andando
PULO_VEL, PULO_DUR = 4.5, 0.55
ALCANCE_EM_PE, ALCANCE_PULO = 0.5, 0.85
REACAO = 0.12         # o goleiro enxerga a bola com atraso (tempo de reação humano)

CORRENDO, VOANDO, GOL, DEFESA, FORA = 0, 1, 2, 3, 4


class Penalti:
    nome = "penalti"
    camadas_bat = (8, 10, 3)   # -> ritmo, giro do corpo, canto
    camadas_gol = (9, 10, 2)   # -> passo lateral, pulo
    dt = DT
    passos = PASSOS

    def __init__(self, n, rng):
        self.n = n
        self.rng = rng
        self.r = np.zeros(n)              # progresso da corrida (1 = chegou na bola)
        self.vr = np.zeros(n)
        self.corpo = rng.uniform(-0.2, 0.2, n)
        self.dcorpo = np.zeros(n)
        self.xg = np.zeros(n)             # goleiro
        self.vg = np.zeros(n)
        self.pulo_t = np.full(n, -1.0)    # instante do pulo (-1 = não pulou)
        self.pulo_dir = np.zeros(n)
        self.chute_t = np.full(n, -1.0)
        self.alvo = np.zeros(n)           # x onde a bola cruza a linha
        self.altura = rng.uniform(0.2, 1.9, n)
        self.canto_pedido = np.zeros(n)
        self.corpo_no_chute = np.zeros(n)
        self.corpo_antes = np.zeros(n)    # 0,4 s antes do chute: o que o goleiro "leu"
        self.hist_corpo = []
        self.estado = np.zeros(n, np.int8)
        self.t_fim = np.full(n, -1)
        self.ruido = rng.normal(0, 1, n)

    # ---------------------------------------------------------- bola
    def bola(self, t):
        """Posição lateral e progresso (0..1) da bola no instante t (s)."""
        voou = self.chute_t >= 0
        p = np.where(voou, np.clip((t - self.chute_t) / VOO, 0, 1), 0)
        return self.alvo * p, p

    # ---------------------------------------------------------- observações
    def obs_batedor(self, t):
        pulou = self.pulo_t >= 0
        return np.stack([np.full(self.n, t / 3), self.r, self.vr, self.corpo, self.xg / MEIO_GOL,
                         pulou * 1.0, pulou * self.pulo_dir, self.vg / PASSO_GOLEIRO], 1).astype(np.float32)

    def obs_goleiro(self, t):
        xb, p = self.bola(t - REACAO)
        voou = self.chute_t >= 0
        return np.stack([np.full(self.n, t / 3), self.r, self.vr, self.corpo, self.dcorpo / GIRO_CORPO,
                         voou * 1.0, xb / MEIO_GOL, self.xg / MEIO_GOL, (self.pulo_t >= 0) * 1.0],
                        1).astype(np.float32)

    # ---------------------------------------------------------- passo
    def passo(self, sb, sg, k):
        t = k * DT
        correndo = self.estado == CORRENDO
        # batedor
        ritmo = (sb[:, 0] + 1) / 2
        self.vr = np.where(correndo, ritmo, 0)
        self.r = np.where(correndo, np.minimum(self.r + self.vr * DT / CORRIDA, 1), self.r)
        self.dcorpo = np.where(correndo, sb[:, 1] * GIRO_CORPO, 0)
        self.corpo = np.clip(self.corpo + self.dcorpo * DT, -1, 1)
        self.hist_corpo.append(self.corpo.copy())
        apressado = correndo & (self.r < 1) & (t >= LIMITE_CHUTE)
        chuta = correndo & ((self.r >= 1) | apressado)
        if chuta.any():
            canto = np.clip(sb[:, 2], -1, 1)
            # chutar contra o corpo é possível, mas sai torto; chute apressado sai pior ainda
            erro = 0.3 + 0.9 * np.abs(canto - self.corpo) / 2 + 1.2 * apressado
            x = canto * (MEIO_GOL + 0.3) + self.ruido * erro
            atras = max(0, len(self.hist_corpo) - 1 - int(0.4 / DT))
            self.corpo_antes[chuta] = self.hist_corpo[atras][chuta]
            self.alvo[chuta] = x[chuta]
            self.canto_pedido[chuta] = canto[chuta]
            self.corpo_no_chute[chuta] = self.corpo[chuta]
            self.chute_t[chuta] = t
            self.estado[chuta] = VOANDO
        # goleiro
        vivo = self.estado <= VOANDO
        levantou = (self.pulo_t >= 0) & (t - self.pulo_t > PULO_DUR + LEVANTA)
        self.pulo_t[levantou] = -1.0   # pulou cedo demais: levanta e pode tentar de novo
        no_chao = self.pulo_t < 0
        pula = vivo & no_chao & (sg[:, 1] > 0.6)
        self.pulo_t[pula] = t
        self.pulo_dir[pula] = np.where(sg[pula, 0] >= 0, 1, -1)
        no_ar = (self.pulo_t >= 0) & (t - self.pulo_t < PULO_DUR)
        self.vg = np.where(no_ar, self.pulo_dir * PULO_VEL,
                           np.where(self.pulo_t < 0, sg[:, 0] * PASSO_GOLEIRO, 0))
        self.vg = np.where(vivo, self.vg, 0)
        self.xg = np.clip(self.xg + self.vg * DT, -MEIO_GOL - 0.5, MEIO_GOL + 0.5)
        # bola chega
        xb, p = self.bola(t)
        chegou = (self.estado == VOANDO) & (p >= 1)
        if chegou.any():
            alcance = np.where(self.pulo_t >= 0, ALCANCE_PULO, ALCANCE_EM_PE)
            fora = np.abs(self.alvo) > MEIO_GOL
            pegou = np.abs(self.alvo - self.xg) <= alcance
            self.estado[chegou & fora] = FORA
            self.estado[chegou & ~fora & pegou] = DEFESA
            self.estado[chegou & ~fora & ~pegou] = GOL
            self.t_fim[chegou] = k

    def acabou(self):
        return (self.estado >= GOL).all()

    # ---------------------------------------------------------- notas
    def aptidoes(self):
        gol = self.estado == GOL
        defesa = self.estado == DEFESA
        fora = self.estado == FORA
        perto = 1 - np.minimum(np.abs(self.alvo - self.xg) / 4, 1)
        bat = gol * 1.0 - fora * 0.3
        gol_ = defesa * 1.0 + (~fora) * 0.25 * perto
        return bat, gol_
