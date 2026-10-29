"""Adaptador do Dilema da Ambulância, visto de cima em estilo holograma (x = ao longo da avenida, y = lateral).

Uma avenida de 3 faixas, 24 carros e a ambulância (branca, sirene azul/vermelha) vindo de trás. A câmera acompanha a
ambulância. Cada geração mostra UMA avenida (a típica: a de nota mediana); o replay foca numa avenida escolhida.
"""
import math

import numpy as np

from ..desafios import ambulancia as M
from ..desafios.foguete import FALHA, SUCESSO
from ..palco import arte as R
from ..palco.holo import AMARELO, AZUL, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .populacao import AdaptadorPopulacao

C = M.Ambulancia.C
CINZA = (0.55, 0.62, 0.8)


class Ambulancia(AdaptadorPopulacao):
    Desafio = M.Ambulancia
    titulo = "AMBULÂNCIA"
    experimento = "011"
    saidas = ("ACELERA", "DESVIA")
    rotulos = ("CHEGOU A TEMPO", "NÃO CHEGOU")
    som_falha = "batida"

    # ------------------------------------------------------------ leitura das gravações
    def mundo(self, rod, foco):
        """Avenida mostrada: a do replay, ou a típica (nota mediana) no ao vivo."""
        if foco is not None:
            return foco
        if "tipico" not in rod.__dict__:
            rod.tipico = int(np.argsort(rod.apt)[len(rod.apt) // 2])
        return rod.tipico

    def estado_em(self, rod, k, i):
        e = rod.reg["extra"][k, i]
        return e[:C], e[C:2 * C], e[2 * C:3 * C] > 0.5, e[3 * C], e[3 * C + 1], e[3 * C + 2]    # xs, ys, batido, ax, ay, av

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        k = self.mundo(rod, foco)
        i = rod.i(t)
        ax = float(rod.reg["extra"][k, i, 3 * C])
        geral = Camera2D(centro=(ax + 8.0, M.LARG_VIA / 2), escala=34, t=t)
        if modo != "replay" or foco is None:
            return geral
        perto = Camera2D(centro=(ax + 6.0, M.LARG_VIA / 2), escala=44, t=t)
        cam = geral.mistura(perto, min(t / 0.8, 1.0))
        if rod.morte[foco] >= 0 and rod.reg["estado"][foco, rod.morte[foco]] == FALHA and 0 <= t - rod.morte[foco] * rod.dt < 0.35:
            cam.tremor = 9 * (1 - (t - rod.morte[foco] * rod.dt) / 0.35)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t, ax):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.035)
        R.poeira(h, t, alfa=0.2)
        x0, x1 = ax - 28, ax + 42
        W = M.LARG_VIA
        h.forma([(x0, 0), (x1, 0), (x1, W), (x0, W)], CIANO, 0.35, 1.2, 0.05)
        for y in (0, W):
            h.linha([(x0, y), (x1, y)], CIANO, 3.2, 0.9)
        for f in (M.FAIXA, 2 * M.FAIXA):
            h.linha([(x0, f), (x1, f)], AMARELO, 2, 0.45, tracejado=[22, 18])
        # marcos de distância
        for m in range(int(x0 // 20) * 20, int(x1) + 20, 20):
            if 0 <= m <= M.FIM:
                h.linha([(m, -0.4), (m, 0.0)], CIANO, 2, 0.6, halo=False)
                h.texto(f"{m}", (m, -1.3), 16, CIANO, 0.5)
        # linha de chegada
        if x0 < M.FIM < x1 + 5:
            n = 6
            for j in range(n):
                cor = BRANCO if j % 2 == 0 else (0.2, 0.25, 0.35)
                h.forma([(M.FIM, j * W / n), (M.FIM + 1.2, j * W / n), (M.FIM + 1.2, (j + 1) * W / n), (M.FIM, (j + 1) * W / n)],
                        cor, 0.7, 1.0, 0.5, gradiente=False)
            h.texto("CHEGADA", (M.FIM + 0.6, -1.7), 20, VERDE, 0.9)

    # ------------------------------------------------------------ desenho
    def desenha(self, h, rod, t, modo, foco):
        k = self.mundo(rod, foco)
        i = rod.i(t)
        xs, ys, bat, ax, ay, av = self.estado_em(rod, k, i)
        self.cenario(h, t, ax)
        est = rod.reg["estado"][k, i]
        m = rod.morte[k]
        for c in range(C):
            if xs[c] < ax - 24 or xs[c] > ax + 40:
                continue
            cor = VERMELHO if bat[c] else (CIANO if c % 2 == 0 else AZUL)
            freio = bool(rod.reg["acel"][k, i, c] < -0.25) and not bat[c]
            R.veiculo_topo(h, (float(xs[c]), float(ys[c])), 0.0, M.COMP, M.LARG, cor, t, 1.0,
                           farois=not bat[c], freio=freio)
            if bat[c]:
                h.particulas((float(xs[c]), float(ys[c])), (t * 1.7 + c) % 1.3, (1.0, 0.7, 0.3), n=4, alcance=1.6, dur=1.2,
                             semente=c)
        # ambulância: corpo branco, cruz, sirene alternando, cone de luz e ondas de som
        sir = int(t * 6) % 2
        R.veiculo_topo(h, (float(ax), float(ay)), 0.0, M.COMP_A, M.LARG_A, BRANCO, t, 1.0, farois=True)
        for j, dy in enumerate((-0.55, 0.55)):
            on = (j == sir)
            h.ponto_luz((float(ax - 0.4), float(ay + dy)), 34 if on else 12, VERMELHO if j == 0 else AZUL, 1.0 if on else 0.35)
        h.pulso((float(ax), float(ay)), (t * 1.3) % 0.9, VERMELHO if sir else AZUL, 5.0, 0.9, 3)
        tr = rod.reg["extra"][k, max(0, i - 25): i + 1: 2]
        pts = [(float(e[3 * C]) - 2.6, float(e[3 * C + 1])) for e in tr]
        if len(pts) > 1:
            h.rastro(pts, BRANCO, 3, 0.6)
        h.texto("AMBULÂNCIA", (float(ax), float(ay) + 2.0), 15, BRANCO, 0.9)
        if est == SUCESSO and m >= 0 and i >= m:
            idade = (i - m) * rod.dt
            h.pulso((float(ax), float(ay)), idade, VERDE, 5.0, 0.9, 5)
            h.texto("✓ CHEGOU", (float(ax), float(ay) - 2.6), 26, VERDE, min(idade * 3, 1))
        elif est == FALHA and m >= 0 and i >= m:
            idade = (i - m) * rod.dt
            h.pulso((float(ax), float(ay)), idade, VERMELHO, 4.0, 0.7, 5)
            if m < rod.T - 2:                  # bateu (e não só esgotou o prazo)
                h.texto("BATEU", (float(ax), float(ay) - 2.6), 26, VERMELHO, min(idade * 4, 1))

    # ------------------------------------------------------------ pontos para o telestrador
    def ponto(self, rod, foco, nome, t):
        k = self.mundo(rod, foco)
        xs, ys, bat, ax, ay, av = self.estado_em(rod, k, rod.i(t))
        if nome == "ambulancia":
            return (float(ax), float(ay))
        if nome in ("bloqueio", "carro"):       # o carro que está à frente da ambulância, na faixa dela
            m = (xs > ax) & (np.abs(ys - ay) < 2.2)
            if m.any():
                c = int(np.argmin(np.where(m, xs - ax, 1e9)))
                return (float(xs[c]), float(ys[c]))
            return (float(ax + 8), float(ay))
        if nome == "batida":
            b = np.where(bat)[0]
            if len(b):
                c = b[np.argmin(np.abs(xs[b] - ax))]
                return (float(xs[c]), float(ys[c]))
            return (float(ax + 8), float(ay))
        if nome == "corredor":
            return (float(ax + 10), float(ay))
        raise KeyError(nome)

    def carro_perto(self, rod, k, i):
        xs, ys, bat, ax, ay, av = self.estado_em(rod, k, i)
        m = xs > ax - 4
        return int(np.argmin(np.where(m, np.abs(xs - ax), 1e9))) if m.any() else 0

    def cerebro(self, rod, t, foco):
        k = self.mundo(rod, foco)
        i = rod.i(t)
        c = self.carro_perto(rod, k, i)
        pesos = [(W[0], b[0]) for W, b in self.arq.desempacota(rod.genes[k:k + 1])]
        return dict(camadas=self.Desafio.camadas, pesos=pesos, ativ=rod.reg["ativ"][k, i, c],
                    saidas=self.saidas, titulo="CÉREBRO // CARROS", cor=CIANO)

    def sons(self, rod, t0, t1, modo, foco):
        k = self.mundo(rod, foco)
        a, b = rod.i(t0), rod.i(t1)
        ev = []
        if b > a:
            bat = rod.reg["extra"][k, :, 2 * C:3 * C] > 0.5
            novos = int((bat[b] & ~bat[a]).sum())
            if novos:
                ev.append((t0, "batida", min(0.5 + 0.2 * novos, 1.3)))
            m = rod.morte[k]
            if m >= 0 and a <= m < b and rod.reg["estado"][k, m] == SUCESSO:
                ev.append((t0, "ding", 2 if modo == "replay" else 1))
        return ev

    def busca(self, rod, tipo):
        """'primeiro' = ambulância mais rápida; 'lento' = a mais demorada que chegou; 'falha'/'quase' = não chegou;
        'bateu' = a ambulância bateu; 'caos' = avenida com mais carros batidos."""
        est = rod.reg["estado"][:, -1]
        suc = np.where(est == SUCESSO)[0]
        fal = np.where(est == FALHA)[0]
        if tipo == "primeiro" and len(suc):
            return int(suc[np.argmin(rod.morte[suc])])
        if tipo == "lento" and len(suc):
            return int(suc[np.argmax(rod.morte[suc])])
        if tipo in ("falha", "quase") and len(fal):
            return int(fal[np.argmax(rod.apt[fal])]) if tipo == "quase" else int(fal[0])
        if tipo == "caos":
            bat = rod.reg["extra"][:, -1, 2 * C:3 * C].sum(1)
            return int(np.argmax(bat))
        return None
