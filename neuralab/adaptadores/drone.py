"""Adaptador do drone na tempestade, vista de lado em estilo holograma (mundo = metros da simulação).

Mundo: x ao longo do voo (saída à esquerda, plataforma à direita), y é a altura. As nuvens ficam em y ~ 28-36.
"""
import math

import numpy as np

from ..desafios.drone import CAUSA_RAIO, Drone as DesafioDrone
from ..desafios.foguete import FALHA, SUCESSO
from ..palco import arte as R
from ..palco.holo import AMARELO, BRANCO, CIANO, LARANJA, MAGENTA, VERDE, VERMELHO, Camera2D, clareia
from .populacao import AdaptadorPopulacao

NUVEM_Y = 29.0
ROXO = (0.55, 0.3, 1.0)


def raio_zigzag(x0, y0, y1, semente, n=12):
    rng = np.random.default_rng(semente)
    ys = np.linspace(y0, y1, n)
    xs = x0 + np.cumsum(rng.normal(0, 0.9, n)) - 0  # caminhada aleatória
    xs = xs - xs[-1] + x0                          # termina exatamente em x0
    return np.c_[xs, ys]


def drone_lado(h, c, ang, cor, t, alfa=1.0, motores=(0.0, 0.0), escala=1.0):
    """Drone de perfil: corpo, braços, dois rotores girando e chama de empuxo. ang > 0 inclina para +x."""
    rot = lambda pts: R._rot(np.asarray(pts, float) * escala, -ang, c)
    for lado, m in zip((-1, 1), motores):
        bx = 1.25 * lado
        if m > 0.04:
            comp = 0.6 + 2.6 * m * (0.85 + 0.15 * math.sin(t * 45 + lado))
            h.forma(rot([(bx - 0.28, -0.35), (bx + 0.28, -0.35), (bx, -0.35 - comp)]), LARANJA, alfa, 1.6, 0.4)
            h.ponto_luz(rot([(bx, -0.5)])[0], (10 + 16 * m) * escala, LARANJA, 0.7 * alfa)
        # rotor: disco que vibra
        w = 0.95 + 0.12 * math.sin(t * 55 + lado * 2)
        h.linha(rot([(bx - w, 0.55), (bx + w, 0.55)]), clareia(cor, 0.3), 2.2, 0.8 * alfa)
        h.linha(rot([(bx, 0.15), (bx, 0.55)]), cor, 2, 0.7 * alfa, halo=False)
    h.linha(rot([(-1.25, 0.15), (-0.5, 0.0)]), cor, 2.2, alfa)
    h.linha(rot([(1.25, 0.15), (0.5, 0.0)]), cor, 2.2, alfa)
    h.forma(rot([(-0.55, 0.3), (0.55, 0.3), (0.7, -0.05), (0.4, -0.4), (-0.4, -0.4), (-0.7, -0.05)]), cor, alfa, 2.4,
            0.28, oclusor=True)
    h.circulo(rot([(0, -0.02)])[0], 0.16 * escala, clareia(cor, 0.6), alfa, 1.6, 0.6)   # olho/câmera


class Drone(AdaptadorPopulacao):
    Desafio = DesafioDrone
    titulo = "DRONE"
    experimento = "003"
    saidas = ("POTÊNCIA", "INCLINA")
    rotulos = ("POUSOS", "DERRUBADOS")
    som_falha = "boom"

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(-0.5, 14.5), escala=24, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        m = rod.morte[foco]
        fim = i if m < 0 else min(i, m)
        x, y = rod.reg["s"][foco, fim, :2]
        alvo = Camera2D(centro=(float(np.clip(x, -10, 8)), float(max(y, 0) * 0.6 + 8.0)), escala=40, t=t)
        cam = geral.mistura(alvo, t / 1.2)
        if m >= 0 and 0 <= t - m * rod.dt < 0.4:
            cam.tremor = 10 * (1 - (t - m * rod.dt) / 0.4)
        return cam

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t, rod):
        D = self.Desafio
        amb = rod.amb
        ts = t
        r = amb.raio_ativo(ts)
        forte = r is not None and r[2]
        h.fundo(brilho_centro=(0.07, 0.04, 0.14), manchas=((0.2, 0.1, (0.45, 0.1, 0.6)), (0.85, 0.8, (0.0, 0.25, 0.45))))
        R.poeira(h, ts, BRANCO, n=60, alfa=0.2)
        h.grade(4.0, alfa=0.035, pontos=False)
        # nuvem de tempestade: base ondulada + volume
        xs = np.linspace(-26, 26, 70)
        base = NUVEM_Y + 1.4 * np.sin(xs * 0.35 + ts * 0.6) + 0.7 * np.sin(xs * 0.9 - ts * 1.1)
        topo = base + 7
        h.forma(list(zip(xs, base)) + list(zip(xs[::-1], topo[::-1])), ROXO, 0.9, 2, 0.1 + 0.25 * forte)
        h.linha(np.c_[xs, base], ROXO, 2.6, 0.8)
        # solo, plataforma e saída
        h.linha([(-26, 0), (26, 0)], CIANO, 3, 0.9)
        for x in np.arange(-26, 27, 2):
            h.linha([(x, 0), (x, -0.9)], CIANO, 1, 0.3, halo=False)
        a, b = D.pad_x - D.pad_meia, D.pad_x + D.pad_meia
        h.forma([(a, 0), (b, 0), (b - 0.5, 0.7), (a + 0.5, 0.7)], AMARELO, 1, 2.5, 0.3)
        for k in range(5):
            h.ponto_luz((a + 0.5 + k * (b - a - 1) / 4, 0.85), 8, AMARELO, 0.4 + 0.6 * (math.sin(ts * 6 - k) > 0))
        h.texto("POUSO", (D.pad_x, -2.3), 22, AMARELO, 0.85)
        h.texto("SAÍDA", (-17.0, -2.3), 20, CIANO, 0.55)
        # vento: campo de riscos (ciano = empurra para a plataforma, magenta = contra)
        for yy in (4.0, 10.0, 16.0, 22.0):
            for xx in np.arange(-22, 23, 4.0):
                for j in range(2):
                    x0 = xx + 2.0 * j + 1.0 * math.sin(yy)
                    w = float(amb.vento(x0, yy, ts))
                    comp = 0.28 * w
                    cor = CIANO if w >= 0 else MAGENTA
                    desl = (ts * 0.4 * w * 0.3 + j) % 1.0
                    x1 = x0 + (desl - 0.5) * 1.2
                    h.linha([(x1, yy), (x1 + comp, yy)], cor, 1.6, min(abs(w) / amb.W, 1.1) * 0.55, halo=False)
        # raios: aviso (coluna pulsando + alerta no chão) e a descarga
        for tsr, xb in amb.raios:
            if tsr - D.aviso <= ts <= tsr:
                k = (ts - (tsr - D.aviso)) / D.aviso
                pulso = 0.35 + 0.65 * (math.sin(ts * (10 + 22 * k)) > 0)
                h.forma([(xb - D.raio_larg, 0), (xb + D.raio_larg, 0), (xb + D.raio_larg, NUVEM_Y),
                         (xb - D.raio_larg, NUVEM_Y)], VERMELHO, 0.35 + 0.65 * k, 1.6, 0.05 + 0.1 * k * pulso)
                h.texto("⚠", (xb, 1.6), 34, AMARELO, pulso)
                h.ponto_luz((xb, NUVEM_Y), 40 + 40 * k, MAGENTA, 0.5 * k)
            elif tsr < ts <= tsr + 0.55:
                idade = ts - tsr
                if idade <= D.golpe + 0.1:
                    zz = raio_zigzag(xb, NUVEM_Y, 0.0, int(tsr * 100))
                    h.linha(zz, BRANCO, 7, 1.0)
                    h.linha(zz + [0.35, 0], MAGENTA, 3, 0.6, halo=False)
                    h.ponto_luz((xb, 0.8), 90, BRANCO, 0.9)
                h.pulso((xb, 0.3), idade, BRANCO, 4.0, 0.5, 5)

    # ------------------------------------------------------------ desenho
    def desenha(self, h, rod, t, modo, foco):
        D = self.Desafio
        s, est, ac = rod.reg["s"], rod.reg["estado"], rod.reg["acel"]
        i = rod.i(t)
        self.cenario(h, t, rod)
        lider = foco if (modo == "replay" and foco is not None) else rod.lider
        ks = [foco] if (modo == "replay" and foco is not None) else sorted(set(range(0, rod.n, 6)) | {rod.lider})
        for k in ks:
            m = rod.morte[k]
            fim = i if m < 0 else min(i, m)
            destaque = k == lider
            if est[k, i] == SUCESSO:
                cor = VERDE
            elif est[k, i] == FALHA:
                cor = VERMELHO
            else:
                cor = AMARELO if destaque else CIANO
            pts = s[k, max(0, fim - 45): fim + 1: 3, :2]
            if len(pts) > 1:
                h.rastro(pts, cor, 2.8 if destaque else 1.1, 0.8 if destaque else 0.08)
            x, y, vx, vy, a, w = s[k, fim]
            if m >= 0 and i >= m and est[k, m] == FALHA:
                idade = (i - m) * rod.dt
                if rod.amb.causa[k] == CAUSA_RAIO and destaque and idade < 0.5:   # fritado: carcaça pisca
                    drone_lado(h, (float(x), float(y)), float(a), BRANCO if int(idade * 30) % 2 else VERMELHO, t)
                R.explosao(h, (float(x), max(float(y), 0.5)), idade, semente=k, escala=2.2 if destaque else 1.0,
                           alfa=1.0 if destaque else 0.2)
                continue
            drone_lado(h, (float(x), float(y)), float(a), cor, t, 1.0 if destaque else 0.14,
                       (float(ac[k, fim, 0]), float(ac[k, fim, 1])) if est[k, i] == 0 else (0, 0),
                       escala=1.7 if destaque else 1.0)
            if est[k, i] == SUCESSO and destaque:
                h.pulso((float(x), float(y) + 1.5), (i - m) * rod.dt if m >= 0 else 0, VERDE, 5, 0.9, 4)
                h.texto("✓ POUSOU", (float(x), float(y) + 4.2), 26, VERDE, 1.0)

    def ponto(self, rod, foco, nome, t):
        i = rod.i(t)
        m = rod.morte[foco]
        x, y = rod.reg["s"][foco, i if m < 0 else min(i, m), :2]
        if nome == "agente":
            return (float(x), float(y) + 1.2)
        if nome == "alvo":
            return (self.Desafio.pad_x, 1.5)
        if nome == "raio":
            ts, xb = rod.amb.raios[0]
            return (xb, 8.0)
        raise KeyError(nome)

    def sons(self, rod, t0, t1, modo, foco):
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        for tsr, xb in rod.amb.raios:                       # trovão no instante do raio
            if t0 <= tsr < t1:
                ev.append((t0, "raio", 1.0))
        pous = quedas = 0
        for k in ks:
            m = rod.morte[k]
            if m >= 0 and t0 <= m * rod.dt < t1:
                if rod.reg["estado"][k, m] == SUCESSO:
                    pous += 1
                elif rod.amb.causa[k] != CAUSA_RAIO:
                    quedas += 1
        if quedas:
            ev.append((t0, "boom", min(0.4 + 0.12 * quedas, 1.1)))
        if pous:
            ev.append((t0, "ding", 2 if modo == "replay" else 1))
        return ev
