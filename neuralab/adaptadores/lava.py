"""Adaptador de "O Chão é Lava", visto de lado em estilo holograma (mundo = metros; y = 0 é o chão).

Torre de plataformas (ciano), lava neon subindo (laranja) e 8 IAs; a campeã da torre é destacada em amarelo.
IAs em cima de outra (degrau) ganham um brilho magenta no ponto de apoio.
"""
import math

import numpy as np

from ..desafios.foguete import SUCESSO
from ..desafios.lava import H_AG, LARG, MIN_VIVAS, TOPO, W_AG, Lava as DesafioLava
from ..palco.holo import AMARELO, BRANCO, CIANO, LARANJA, MAGENTA, VERDE, VERMELHO, Camera2D, clareia
from .populacao import AdaptadorPopulacao

ESCALA = 68


class Lava(AdaptadorPopulacao):
    Desafio = DesafioLava
    titulo = "O CHÃO É LAVA"
    experimento = "006"
    saidas = ("ANDAR ◂▸", "PULAR", "—")
    rotulos = ("TORRES QUE SALVARAM", "AINDA TENTANDO")
    som_falha = "batida"

    # ------------------------------------------------------------ dados por torre
    def torre(self, rod, k):
        """(morte por IA em passos, campeã) — cacheado."""
        chave = ("torre", k)
        if chave not in rod.__dict__:
            y = rod.reg["s"][k, :, :, 1]                       # (T, N)
            lava = rod.reg["extra"][k, :, 0]                   # (T,)
            morta = y < lava[:, None] - 1e-6
            morte = np.where(morta.any(0), morta.argmax(0), -1)
            vivas_fim = morte < 0
            ymax = y.max(0)
            quem = int(np.argmax(vivas_fim * 100 + ymax - 0.001 * np.where(morte >= 0, morte, 0)))
            rod.__dict__[chave] = (morte, quem)
        return rod.__dict__[chave]

    def heroi(self, rod, k):
        return self.torre(rod, k)[1]

    def torre_de(self, rod, foco):
        return rod.lider if foco is None else foco

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(LARG / 2, 4.1), escala=ESCALA, t=t)
        if modo != "replay" or foco is None:
            return geral
        i = rod.i(t)
        sk = rod.reg["s"][foco, i]
        c = self.heroi(rod, foco)
        hx = float(np.clip(sk[c, 0], 3.5, LARG - 3.5))
        hy = float(np.clip(sk[c, 1] + 1.6, 2.6, TOPO - 0.3))
        perto = Camera2D(centro=(hx, hy), escala=ESCALA * 1.55, t=t)
        return geral.mistura(perto, min(t / 0.8, 1.0))

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t, plat, nivel):
        h.fundo(brilho_centro=(0.05, 0.06, 0.1))
        h.grade(1.0, alfa=0.03, pontos=False)
        h.linha([(0, -1.4), (0, 10.5)], CIANO, 2.5, 0.35, halo=False)
        h.linha([(LARG, -1.4), (LARG, 10.5)], CIANO, 2.5, 0.35, halo=False)
        for k in range(1, len(plat)):
            x0, x1, tp = (float(v) for v in plat[k])
            h.forma([(x0, tp), (x1, tp), (x1, tp - 0.16), (x0, tp - 0.16)], CIANO, 0.9, 2.2, 0.28)
            h.ponto_luz(((x0 + x1) / 2, tp), 22, CIANO, 0.18)
        h.linha([(0, 0), (LARG, 0)], CIANO, 3, 0.7)
        # lava
        xs = np.linspace(0, LARG, 60)
        topo = nivel + 0.09 * np.sin(xs * 2.2 + t * 3.0) + 0.05 * np.sin(xs * 5.1 - t * 4.2)
        h.forma([(0, -1.4)] + [(float(x), float(y)) for x, y in zip(xs, topo)] + [(LARG, -1.4)],
                LARANJA, 0.85, 2.5, 0.38)
        h.linha([(float(x), float(y)) for x, y in zip(xs, topo)], (1.0, 0.85, 0.35), 3.5, 0.95)
        for k in range(7):                                  # bolhas
            bx = (k * 2.07 + t * (0.3 + 0.05 * k)) % LARG
            by = nivel - ((t * 0.7 + k * 0.37) % 1.0) * 0.6
            h.circulo((bx, by), 0.07 + 0.03 * (k % 3), (1.0, 0.8, 0.3), 0.55, 1.4, 0.4)

    # ------------------------------------------------------------ desenho
    def desenha(self, h, rod, t, modo, foco):
        k = self.torre_de(rod, foco)
        i = rod.i(t)
        s = rod.reg["s"][k, i]
        nivel = float(rod.reg["extra"][k, i, 0])
        self.cenario(h, t, rod.amb.plat[k], nivel)
        morte, quem = self.torre(rod, k)
        N = s.shape[0]
        for c in range(N):
            m = morte[c]
            if 0 <= m <= i:
                idade = (i - m) * rod.dt
                if idade < 0.9:
                    x, y = float(s[c, 0]), float(s[c, 1])
                    h.particulas((x, max(y, nivel)), idade, LARANJA, 16, 1.4, 0.9, semente=c, gravidade=-3)
                    h.pulso((x, nivel), idade, VERMELHO, 0.9, 0.7, 3)
                continue
            x, y = float(s[c, 0]), float(s[c, 1])
            heroi = c == quem
            cor = AMARELO if heroi else CIANO
            pts = [(x - W_AG / 2, y), (x + W_AG / 2, y), (x + W_AG / 2, y + H_AG), (x - W_AG / 2, y + H_AG)]
            if heroi:
                tr = rod.reg["s"][k, max(0, i - 45): i + 1: 3, c, :2]
                if len(tr) > 1:
                    h.rastro([(float(a), float(b) + H_AG / 2) for a, b in tr], AMARELO, 3, 0.7)
            h.forma(pts, cor, 1.0, 2.6, 0.3, oclusor=True)
            h.circulo((x, y + H_AG * 0.62), 0.09, BRANCO, 0.95, 1.2, 0.9)       # "olho"
            if y - nivel < 0.9:                                                  # lava perto: fica vermelha
                h.circulo((x, y + H_AG / 2), 0.55, VERMELHO, 0.35, 1.6, 0.0)
        # degrau: brilho magenta onde alguém pisa na cabeça de outra IA
        for c in range(N):
            if 0 <= morte[c] <= i:
                continue
            sob = int(rod.reg["extra"][k, i, 1 + c])
            if sob >= 0:
                h.ponto_luz((float(s[c, 0]), float(s[c, 1])), 14, MAGENTA, 0.8)
        hx, hy = float(s[quem, 0]), float(s[quem, 1])
        if not (0 <= morte[quem] <= i):
            h.circulo((hx, hy + H_AG / 2), 0.62 + 0.06 * math.sin(t * 6), AMARELO, 0.7, 2.0, 0.0)
            h.ponto_luz((hx, hy + H_AG / 2), 26, AMARELO, 0.5)
            h.texto("CAMPEÃ", (hx, hy + 1.35), 26, AMARELO, 1.0)
        vivas = int(sum(1 for c in range(N) if not (0 <= morte[c] <= i)))
        h.texto(f"{vivas}/{N}", (LARG - 1.1, 9.6), 28, VERDE if vivas >= MIN_VIVAS else VERMELHO, 0.95)
        if rod.reg["estado"][k, i] == SUCESSO:
            idade = max((i - rod.morte[k]) * rod.dt, 0.0)
            h.texto("✓ SALVAS", (LARG / 2, 9.4), 30, VERDE, min(idade * 3 + 0.3, 1))

    # ------------------------------------------------------------ telestrador / HUD
    def ponto(self, rod, foco, nome, t):
        k = self.torre_de(rod, foco)
        s = rod.reg["s"][k, rod.i(t)]
        c = self.heroi(rod, k)
        if nome == "lava":
            return (LARG / 2, float(rod.reg["extra"][k, rod.i(t), 0]))
        return (float(s[c, 0]), float(s[c, 1]) + H_AG / 2)

    def medidores(self, rod, t, foco):
        k = self.torre_de(rod, foco)
        i = rod.i(t)
        morte, _ = self.torre(rod, k)
        N = len(morte)
        vivas = int(sum(1 for c in range(N) if not (0 <= morte[c] <= i)))
        nivel = float(rod.reg["extra"][k, i, 0])
        return [("VIVAS", f"{vivas}/{N}", vivas / N, VERDE),
                ("LAVA", f"{nivel:.1f} m", min(nivel / TOPO, 1.0), LARANJA)]

    def cerebro(self, rod, t, foco):
        k = self.torre_de(rod, foco)
        c = self.heroi(rod, k)
        pesos = [(W[0], b[0]) for W, b in self.arq.desempacota(rod.genes[k:k + 1])]
        return dict(camadas=self.Desafio.camadas, pesos=pesos, ativ=rod.reg["ativ"][k, rod.i(t), c],
                    saidas=self.saidas, titulo="CÉREBRO // CAMPEÃ", cor=CIANO)

    def duracao_foco(self, rod, foco):
        return rod.duracao

    def chaves_lento(self, rod, foco):
        return []

    def busca(self, rod, tipo):
        """'primeiro' = torre que salvou mais IAs (desempata por altura); 'quase' = melhor torre que falhou;
        'falha' = a pior torre; 'lento' = igual a 'primeiro'."""
        est = rod.reg["estado"][:, -1]
        y = rod.reg["s"][:, :, :, 1]
        lava = rod.reg["extra"][:, :, 0]
        vivas = (y[:, -1, :] >= lava[:, -1:] - 1e-6).sum(1)
        altura = y.max(1).mean(1)
        nota = vivas + 0.01 * altura
        if tipo in ("primeiro", "lento"):
            return int(np.argmax(nota))
        fal = np.where(est != SUCESSO)[0]
        if not len(fal):
            return None
        return int(fal[np.argmax(nota[fal])]) if tipo == "quase" else int(fal[np.argmin(nota[fal])])

    def ambiente(self, dur):
        return None
