"""Adaptador da corrida de carrinhos, vista de cima em holograma (mundo = metros da simulação).

Cada geração tem 40 baterias de 4 carros. O destaque é a bateria do líder (ou do carro em foco): os 4
carros dela em cores diferentes, com a posição (P1..P4) ao vivo; as outras baterias viram névoa.
"""
import math

import numpy as np

from ..desafios.corrida import COMP, LARG, LARG_PISTA, COMPRIMENTO, PISTA, TANGENTE, Corrida as DesafioCorrida
from ..desafios.foguete import FALHA, SUCESSO
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .populacao import AdaptadorPopulacao

LARANJA = (1.0, 0.55, 0.15)
CORES_BAT = [AMARELO, CIANO, MAGENTA, LARANJA]


class Corrida(AdaptadorPopulacao):
    Desafio = DesafioCorrida
    titulo = "CORRIDA"
    experimento = "003"
    saidas = ("ACELERA", "VOLANTE")
    rotulos = ("TERMINARAM", "SAÍRAM DA PISTA")
    som_falha = "batida"

    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(0.0, 0.0), escala=21.5, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        x, y = rod.reg["s"][foco, i, :2]
        perto = Camera2D(centro=(float(x) * 0.8, float(y) * 0.8), escala=34, t=t)
        k = min(t / 0.7, 1.0)
        cam = geral.mistura(perto, k)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(2.0, alfa=0.035)
        R.poeira(h, t, alfa=0.2)
        n = len(PISTA)
        nx, ny = -np.sin(TANGENTE), np.cos(TANGENTE)
        ext = [(float(PISTA[i, 0] + nx[i] * LARG_PISTA), float(PISTA[i, 1] + ny[i] * LARG_PISTA)) for i in range(0, n, 6)]
        inte = [(float(PISTA[i, 0] - nx[i] * LARG_PISTA), float(PISTA[i, 1] - ny[i] * LARG_PISTA)) for i in range(0, n, 6)]
        h.forma(ext, CIANO, 0.0, 1.0, 0.05, gradiente=False)
        h.linha(ext, CIANO, 3.5, 0.95, fechado=True)
        h.linha(inte, CIANO, 3.5, 0.95, fechado=True)
        h.linha([(float(PISTA[i, 0]), float(PISTA[i, 1])) for i in range(0, n, 6)], AMARELO, 1.5, 0.22, fechado=True,
                tracejado=[10, 22], halo=False)
        # linha de largada/chegada (índice 0 da pista)
        a = (PISTA[0, 0] + nx[0] * LARG_PISTA, PISTA[0, 1] + ny[0] * LARG_PISTA)
        b = (PISTA[0, 0] - nx[0] * LARG_PISTA, PISTA[0, 1] - ny[0] * LARG_PISTA)
        h.linha([a, b], BRANCO, 5, 0.9)
        h.texto("LARGADA", (float(PISTA[0, 0]) + 7.5, float(PISTA[0, 1])), 22, BRANCO, 0.55)

    # ------------------------------------------------------------ desenho
    def _bateria(self, rod, foco):
        return rod.lider if foco is None else foco

    def desenha(self, h, rod, t, modo, foco):
        s, est, ac = rod.reg["s"], rod.reg["estado"], rod.reg["acel"]
        extra = rod.reg["extra"]
        i = rod.i(t)
        self.cenario(h, t)
        k0 = self._bateria(rod, foco)
        mates = list(self._mates(rod, k0))
        # névoa: 1 em cada 5 das outras baterias, só contorno
        if not (modo == "replay" and foco is not None):
            for k in range(0, rod.n, 5):
                if k in mates:
                    continue
                x, y, hd, v, e = s[k, i]
                R.veiculo_topo(h, (float(x), float(y)), float(hd), COMP, LARG, CIANO, t, 0.07, simples=True)
        # bateria em destaque: ordem de chegada define a cor da posição
        ordem = extra[mates, i, 2].astype(int)
        for j, k in enumerate(mates):
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            x, y, hd, v, e = s[k, min(i, fim)]
            ehfoco = k == k0
            cor = CORES_BAT[j % 4]
            if est[k, i] == SUCESSO:
                cor = VERDE
            elif est[k, i] == FALHA:
                cor = VERMELHO
            tr = s[k, max(0, fim - 60): fim + 1: 3]
            if len(tr) > 1:
                h.rastro([(a - 1.3 * math.cos(b), c - 1.3 * math.sin(b)) for a, c, b in tr[:, :3]], cor,
                         3.2 if ehfoco else 2.0, 0.85 if ehfoco else 0.5)
            freio = bool(ac[k, i] < -0.3) and est[k, i] == 0
            R.veiculo_topo(h, (float(x), float(y)), float(hd), COMP, LARG, cor, t, 1.0 if ehfoco else 0.85,
                           farois=est[k, i] == 0, freio=freio, esterco=float(e))
            if est[k, i] == 0:
                h.texto(f"P{4 - int(ordem[j])}", (float(x), float(y) + 2.1), 22, cor, 0.95)
            if m >= 0 and est[k, m] == FALHA and 0 <= (i - m) * rod.dt < 0.8:
                idade = (i - m) * rod.dt
                h.pulso((float(x), float(y)), idade, VERMELHO, 3.0, 0.7, 5)
                h.ponto_luz((float(x), float(y)), 70 * (1 - idade), (1.0, 0.6, 0.2), 0.8 * (1 - idade))
                h.particulas((float(x), float(y)), idade, (1.0, 0.7, 0.3), n=14, alcance=2.2, dur=0.8, semente=int(k))
            if est[k, i] == SUCESSO and m >= 0:
                idade = (i - m) * rod.dt
                h.pulso((float(x), float(y)), idade, VERDE, 3.5, 0.9, 5)

    def _mates(self, rod, k):
        # a bateria do carro k = os 4 mais próximos no gene de largada (guardados na rodada)
        return rod.mates[k]

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        if nome == "agente":
            x, y = rod.reg["s"][foco, i, :2]
            return (float(x), float(y))
        if nome.startswith("rival"):
            j = int(nome[5:])
            x, y = rod.reg["s"][rod.mates[foco][j], i, :2]
            return (float(x), float(y))
        if nome == "largada":
            return (float(PISTA[0, 0]), float(PISTA[0, 1]))
        raise KeyError(nome)

    def duracao_foco(self, rod, foco):
        mates = rod.mates[foco]
        ms = [rod.morte[k] for k in mates]
        fim = max(ms) if all(m >= 0 for m in ms) else rod.T - 1
        return min((fim + 1) * rod.dt + 0.8, rod.duracao)

    def chaves_lento(self, rod, foco):
        return []

    def janela_lance(self, rod, foco):
        return 0.0, min(self.duracao_foco(rod, foco), 7.0)

    def medidores(self, rod, t, foco):
        if foco is not None:
            t = rod.duracao
        s, f = rod.contagem(t)
        return [(self.rotulos[0], f"{s}/{rod.n}", s / rod.n, VERDE),
                (self.rotulos[1], f"{f}/{rod.n}", f / rod.n, VERMELHO)]

    def ambiente(self, dur):
        return None
