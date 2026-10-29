"""Adaptador do cruzamento sem semáforo, visto de cima em estilo holograma (mundo = metros; centro = 0,0).

Duas ruas: a horizontal (ciano) e a vertical (magenta). Oito carros por cruzamento, o mesmo cérebro em todos.
"""
import math

import numpy as np

from ..desafios.cruzamento import COMP, FAIXA, LARG, SAIDA, Cruzamento as DesafioCruzamento, centro
from ..desafios.foguete import FALHA, SUCESSO
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .populacao import AdaptadorPopulacao

ANG = (0.0, math.pi / 2, math.pi, -math.pi / 2)
COR_EIXO = (CIANO, MAGENTA)
MEIA_RUA = 3.6


class Cruzamento(AdaptadorPopulacao):
    Desafio = DesafioCruzamento
    titulo = "CRUZAMENTO"
    experimento = "005"
    saidas = ("ACELERA",)
    rotulos = ("SEM BATIDA", "BATIDAS")
    som_falha = "batida"

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(0.0, 0.0), escala=24, t=t)
        if modo != "replay" or foco is None:
            return geral
        m = rod.morte[foco] * rod.dt
        perto = Camera2D(centro=(0.0, 0.0), escala=31, t=t)
        k = min(t / 0.6, 1.0) - max((t - m) / 0.7, 0.0)
        cam = geral.mistura(perto, k)
        if rod.morte[foco] >= 0 and rod.reg["estado"][foco, rod.morte[foco]] == FALHA and 0 <= t - m < 0.35:
            cam.tremor = 9 * (1 - (t - m) / 0.35)
        return cam

    # ------------------------------------------------------------ cenário
    def semaforo_riscado(self, h, c, t):
        x, y = c
        h.forma([(x - 0.35, y - 0.9), (x + 0.35, y - 0.9), (x + 0.35, y + 0.9), (x - 0.35, y + 0.9)],
                (0.5, 0.55, 0.7), 0.55, 1.4, 0.1)
        for dy in (-0.55, 0, 0.55):
            h.circulo((x, y + dy), 0.15, (0.4, 0.45, 0.6), 0.35, 1.2, 0.0)
        h.linha([(x - 0.8, y - 1.15), (x + 0.8, y + 1.15)], VERMELHO, 3.5, 0.85 + 0.15 * math.sin(t * 6))

    def cenario(self, h, t):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.035)
        R.poeira(h, t, alfa=0.2)
        L = 40
        m = MEIA_RUA
        # as duas ruas (placas de vidro) e a caixa do cruzamento
        h.forma([(-L, -m), (L, -m), (L, m), (-L, m)], CIANO, 0.35, 1.2, 0.05)
        h.forma([(-m, -L), (m, -L), (m, L), (-m, L)], MAGENTA, 0.35, 1.2, 0.05)
        for s in (-1, 1):   # beiras
            h.linha([(-L, s * m), (-m, s * m)], CIANO, 3, 0.8)
            h.linha([(m, s * m), (L, s * m)], CIANO, 3, 0.8)
            h.linha([(s * m, -L), (s * m, -m)], MAGENTA, 3, 0.8)
            h.linha([(s * m, m), (s * m, L)], MAGENTA, 3, 0.8)
        # faixas centrais tracejadas (somem dentro do cruzamento)
        h.linha([(-L, 0), (-m, 0)], AMARELO, 2, 0.5, tracejado=[22, 18])
        h.linha([(m, 0), (L, 0)], AMARELO, 2, 0.5, tracejado=[22, 18])
        h.linha([(0, -L), (0, -m)], AMARELO, 2, 0.5, tracejado=[22, 18])
        h.linha([(0, m), (0, L)], AMARELO, 2, 0.5, tracejado=[22, 18])
        # zona de perigo: contorno pulsando e cantoneiras
        p = 0.55 + 0.35 * math.sin(t * 4)
        h.forma([(-m, -m), (m, -m), (m, m), (-m, m)], AMARELO, 0.9, 2.0, 0.05)
        h.linha([(-m, -m), (m, -m), (m, m), (-m, m)], AMARELO, 2.5, p, fechado=True, tracejado=[12, 9])
        for sx in (-1, 1):
            for sy in (-1, 1):
                h.ponto_luz((sx * m, sy * m), 10, AMARELO, 0.4)
                self.semaforo_riscado(h, (sx * (m + 1.5), sy * (m + 1.5)), t)
        h.texto("SEM SEMÁFORO", (0, 0), 20, AMARELO, 0.55)

    # ------------------------------------------------------------ desenho
    def pos(self, rod, k, i):
        u = rod.reg["s"][k, i, :, 0]
        x, y = centro(self.lado, u)
        return x, y

    @property
    def lado(self):
        return np.arange(8) % 4

    def desenha(self, h, rod, t, modo, foco):
        s, est, ac = rod.reg["s"], rod.reg["estado"], rod.reg["acel"]
        i = rod.i(t)
        lider = foco if (modo == "replay" and foco is not None) else rod.lider
        self.cenario(h, t)
        if modo == "replay" and foco is not None:
            ks = [foco]
        else:
            ks = sorted(set(range(0, rod.n, 8)) | {rod.lider})
        for k in ks:
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            destaque = k == lider
            bateu_ja = m >= 0 and est[k, m] == FALHA and i >= m
            for c in range(8):
                u, v = s[k, min(i, fim), c]
                if u > SAIDA + 6:
                    continue
                lado = c % 4
                x, y = centro(np.array(lado), u)
                ang = ANG[lado]
                cor = VERMELHO if bateu_ja and u < SAIDA - 2 else COR_EIXO[lado % 2]
                if destaque and not bateu_ja and v < 0.6 and u < -3.5 and u > -14:
                    cor = AMARELO   # esperando
                if destaque:
                    tr = s[k, max(0, fim - 60): fim + 1: 3, c, 0]
                    pts = [tuple(float(q) for q in centro(np.array(lado), uu)) for uu in tr]
                    if len(pts) > 1:
                        h.rastro([(a - 1.0 * math.cos(ang), b - 1.0 * math.sin(ang)) for a, b in pts], cor, 3, 0.7)
                freio = bool(ac[k, min(i, fim)][c] < -0.25 and v > 0.2) and not bateu_ja
                R.veiculo_topo(h, (float(x), float(y)), ang, COMP, LARG, cor, t, 1.0 if destaque else 0.07,
                               farois=destaque and not bateu_ja, freio=freio, simples=not destaque)
            if bateu_ja and (i - m) * rod.dt < 0.9:
                idade = (i - m) * rod.dt
                cx, cy = self.ponto_batida(rod, k)
                if destaque:
                    h.pulso((cx, cy), idade, VERMELHO, 3.2, 0.7, 5)
                    h.ponto_luz((cx, cy), 80 * (1 - idade), (1.0, 0.6, 0.2), 0.8 * (1 - idade))
                h.particulas((cx, cy), idade, (1.0, 0.7, 0.3), n=16 if destaque else 5, alcance=2.4, dur=0.9,
                             semente=int(k))
            if destaque and bateu_ja:
                cx, cy = self.ponto_batida(rod, k)
                h.texto("BATEU", (cx, cy + 2.4), 24, VERMELHO, min((i - m) * rod.dt * 4, 1))
            if destaque and est[k, i] == SUCESSO:
                idade = max((i - m) * rod.dt, 0)
                h.pulso((0.0, 0.0), idade, VERDE, 5.0, 0.9, 5)
                h.texto("✓ TODOS PASSARAM", (0.0, 5.6), 24, VERDE, min(idade * 3, 1))

    # ------------------------------------------------------------ pontos para o telestrador
    def ponto_batida(self, rod, k):
        m = max(int(rod.morte[k]), 0)
        u = rod.reg["s"][k, m, :, 0]
        x, y = centro(self.lado, u)
        horiz = (np.arange(8) % 2) == 0
        hx = np.where(horiz, COMP / 2, LARG / 2)
        hy = np.where(horiz, LARG / 2, COMP / 2)
        ativo = u < SAIDA - 2
        melhor, par = 1e9, None
        for a in range(8):
            for b in range(a + 1, 8):
                if ativo[a] and ativo[b] and abs(x[a] - x[b]) < hx[a] + hx[b] and abs(y[a] - y[b]) < hy[a] + hy[b]:
                    d = abs(x[a] - x[b]) + abs(y[a] - y[b])
                    if d < melhor:
                        melhor, par = d, (a, b)
        if par is None:
            return 0.0, 0.0
        a, b = par
        return float((x[a] + x[b]) / 2), float((y[a] + y[b]) / 2)

    def carro_mais_perto(self, rod, k, i, filtro=None):
        u = rod.reg["s"][k, i, :, 0]
        v = rod.reg["s"][k, i, :, 1]
        cand = [c for c in range(8) if -14 < u[c] < SAIDA and (filtro is None or filtro(u[c], v[c]))]
        return min(cand, key=lambda c: abs(u[c])) if cand else None

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        if nome == "cruzamento":
            return (0.0, 0.0)
        if nome == "batida":
            return self.ponto_batida(rod, foco)
        c = self.carro_mais_perto(rod, foco, i, (lambda u, v: v < 1.0 and u < -3.5) if nome == "espera" else None)
        if c is None:
            return (0.0, 0.0)
        x, y = centro(np.array(c % 4), rod.reg["s"][foco, i, c, 0])
        return (float(x), float(y))

    def cerebro(self, rod, t, foco):
        k = rod.lider if foco is None else foco
        i = rod.i(t)
        c = self.carro_mais_perto(rod, k, i) or 0
        pesos = [(W[0], b[0]) for W, b in self.arq.desempacota(rod.genes[k:k + 1])]
        return dict(camadas=self.Desafio.camadas, pesos=pesos, ativ=rod.reg["ativ"][k, i, c],
                    saidas=self.saidas, titulo="CÉREBRO // LÍDER", cor=CIANO)

    def duracao_foco(self, rod, foco):
        m = rod.morte[foco]
        return (m + 1) * rod.dt + 1.0 if m >= 0 else rod.duracao

    def busca(self, rod, tipo):
        """'primeiro'/'lento' = sucessos mais rápido/lento; 'quase'/'falha' = batidas (a que passou mais carros / qualquer)."""
        est = rod.reg["estado"][:, -1]
        suc = np.where(est == SUCESSO)[0]
        fal = np.where(est == FALHA)[0]
        if tipo == "primeiro" and len(suc):
            return int(suc[np.argmin(rod.morte[suc])])
        if tipo == "lento" and len(suc):
            return int(suc[np.argmax(rod.morte[suc])])
        if tipo in ("quase", "falha") and len(fal):
            return int(fal[np.argmax(rod.apt[fal])]) if tipo == "quase" else int(fal[0])
        return None

    def ambiente(self, dur):
        return None
