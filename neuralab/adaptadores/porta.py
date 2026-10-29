"""Adaptador da porta giratória, visto de cima em estilo holograma (mundo = metros; centro da porta = 0,0).

Duas salas, um cilindro de vidro com a porta em cruz (magenta) e 16 IAs (ciano) que saem da esquerda.
Mostra a sala do líder da geração; uma IA é destacada (a primeira a passar) com rastro amarelo.
"""
import math

import numpy as np

from ..desafios.foguete import FALHA, SUCESSO
from ..desafios.porta import R_AG, RW, SALA_X, SALA_Y, SEN_ARCO, W_MAX, X_PASSOU, Porta as DesafioPorta
from ..palco.holo import AMARELO, BRANCO, CIANO, MAGENTA, VERDE, VERMELHO, Camera2D
from .populacao import AdaptadorPopulacao

ESCALA = 47


class Porta(AdaptadorPopulacao):
    Desafio = DesafioPorta
    titulo = "PORTA GIRATÓRIA"
    experimento = "013"
    saidas = ("FORÇA ▸", "FORÇA ▴")
    rotulos = ("SALAS QUE PASSARAM", "AINDA TENTANDO")
    som_falha = "batida"

    # ------------------------------------------------------------ câmera
    def camera(self, rod, t, modo, foco):
        geral = Camera2D(centro=(-0.8, 0.0), escala=ESCALA, t=t)
        if modo != "replay" or foco is None:
            return geral
        perto = Camera2D(centro=(-1.2, 0.0), escala=ESCALA * 1.55, t=t)
        return geral.mistura(perto, min(t / 0.8, 1.0))

    # ------------------------------------------------------------ cenário
    def cenario(self, h, t, phi, w):
        h.fundo(brilho_centro=(0.03, 0.05, 0.1))
        h.grade(1.0, alfa=0.03)
        S, Y = SALA_X, SALA_Y
        # salas
        h.forma([(-S, -Y), (0, -Y), (0, Y), (-S, Y)], CIANO, 0.22, 1.2, 0.04)
        h.forma([(0, -Y), (S, -Y), (S, Y), (0, Y)], VERDE, 0.22, 1.2, 0.04)
        h.linha([(-S, -Y), (S, -Y), (S, Y), (-S, Y)], CIANO, 3, 0.8, fechado=True)
        # divisória com o cilindro
        h.linha([(0, -Y), (0, -RW)], CIANO, 3.2, 0.95)
        h.linha([(0, RW), (0, Y)], CIANO, 3.2, 0.95)
        a0 = math.asin(SEN_ARCO)
        for sinal in (1, -1):
            pts = [(RW * math.cos(a), sinal * RW * math.sin(a)) for a in np.linspace(a0, math.pi - a0, 24)]
            h.linha(pts, CIANO, 3.2, 0.95)
        h.circulo((0, 0), RW, CIANO, 0.18, 1.2, 0.04)
        # pás
        for k in range(4):
            a = phi + k * math.pi / 2
            ponta = (RW * math.cos(a), RW * math.sin(a))
            h.linha([(0, 0), ponta], MAGENTA, 5, 0.95)
            h.ponto_luz(ponta, 8, MAGENTA, 0.5)
        h.circulo((0, 0), 0.22, AMARELO, 0.95, 2.5, 0.6)
        h.ponto_luz((0, 0), 18, AMARELO, 0.5 + 0.5 * min(abs(w) / W_MAX, 1))
        # sentido de giro
        if abs(w) > 0.1:
            sg = 1 if w > 0 else -1
            pts = [(1.0 * math.cos(a), 1.0 * math.sin(a)) for a in np.linspace(phi + 0.3, phi + 0.3 + sg * 0.9, 10)]
            h.linha(pts, AMARELO, 2.5, 0.8)
        h.texto("DE LÁ", (-S + 2.0, Y - 0.7), 16, CIANO, 0.55)
        h.texto("PARA CÁ", (S - 2.2, Y - 0.7), 16, VERDE, 0.7)

    # ------------------------------------------------------------ desenho
    def heroi(self, rod, k):
        """A IA destacada do indivíduo k: a primeira a passar (ou a que chegou mais longe)."""
        chave = ("heroi", k)
        if chave not in rod.__dict__:
            x = rod.reg["s"][k, :, :, 0]
            passou = x > X_PASSOU
            quando = np.where(passou.any(0), passou.argmax(0), 10 ** 6)
            rod.__dict__[chave] = int(np.argmin(quando)) if passou.any() else int(x[-1].argmax())
        return rod.__dict__[chave]

    def sala(self, rod, foco):
        return rod.lider if foco is None else foco

    def desenha(self, h, rod, t, modo, foco):
        k = self.sala(rod, foco)
        i = rod.i(t)
        phi, w = rod.reg["extra"][k, i]
        self.cenario(h, t, float(phi), float(w))
        s = rod.reg["s"][k, i]
        hero = self.heroi(rod, k)
        N = s.shape[0]
        for c in range(N):
            x, y, vx, vy = s[c]
            ja = x > X_PASSOU
            cor = VERDE if ja else (AMARELO if c == hero else CIANO)
            esperando = (not ja) and abs(vx) + abs(vy) < 0.25
            alfa = 0.55 if ja else 1.0
            if c == hero:
                tr = rod.reg["s"][k, max(0, i - 60): i + 1: 3, c, :2]
                if len(tr) > 1:
                    h.rastro([(float(a), float(b)) for a, b in tr], AMARELO, 3, 0.75)
            h.circulo((float(x), float(y)), R_AG, cor, alfa, 2.4, 0.5 if c == hero else 0.3)
            if esperando and c != hero:
                h.circulo((float(x), float(y)), R_AG * 0.45, VERMELHO, 0.35, 1.2, 0.5)
            if not ja:
                sp = math.hypot(vx, vy)
                if sp > 0.2:
                    h.linha([(float(x), float(y)), (float(x + vx * 0.25), float(y + vy * 0.25))], cor, 2, 0.6, halo=False)
        hx, hy = float(s[hero, 0]), float(s[hero, 1])
        if s[hero, 0] <= X_PASSOU:
            h.circulo((hx, hy), R_AG * 1.9, AMARELO, 0.5, 1.5, 0.0)
        h.texto("CAMPEÃO", (hx, hy + 0.95), 15, AMARELO, 0.9)
        passou = int((s[:, 0] > X_PASSOU).sum())
        if rod.reg["estado"][k, i] == SUCESSO:
            idade = max((i - rod.morte[k]) * rod.dt, 0.0)
            h.pulso((3.0, 0.0), idade, VERDE, 4.0, 0.9, 5)
            h.texto(f"✓ TODAS PASSARAM", (3.5, 0.0), 22, VERDE, min(idade * 3, 1))
        elif passou:
            h.texto(f"{passou}/{N}", (S_TEXTO, SALA_Y - 1.6), 26, VERDE, 0.9)

    # ------------------------------------------------------------ telestrador / HUD
    def ponto(self, rod, foco, nome, t):
        k = self.sala(rod, foco)
        if nome == "porta":
            return (0.0, 0.0)
        s = rod.reg["s"][k, rod.i(t)]
        c = self.heroi(rod, k)
        return (float(s[c, 0]), float(s[c, 1]))

    def medidores(self, rod, t, foco):
        k = self.sala(rod, foco)
        i = rod.i(t)
        s = rod.reg["s"][k, i]
        passou = int((s[:, 0] > X_PASSOU).sum())
        w = float(rod.reg["extra"][k, i, 1])
        return [("PASSARAM", f"{passou}/{len(s)}", passou / len(s), VERDE),
                ("PORTA", f"{abs(w):.1f} rad/s", min(abs(w) / W_MAX, 1.0), MAGENTA)]

    def cerebro(self, rod, t, foco):
        k = self.sala(rod, foco)
        c = self.heroi(rod, k)
        pesos = [(W[0], b[0]) for W, b in self.arq.desempacota(rod.genes[k:k + 1])]
        return dict(camadas=self.Desafio.camadas, pesos=pesos, ativ=rod.reg["ativ"][k, rod.i(t), c],
                    saidas=self.saidas, titulo="CÉREBRO // CAMPEÃO", cor=CIANO)

    def duracao_foco(self, rod, foco):
        m = rod.morte[foco]
        return (m + 1) * rod.dt + 1.5 if m >= 0 else rod.duracao

    def chaves_lento(self, rod, foco):
        return []

    def busca(self, rod, tipo):
        """'primeiro' = sala que terminou mais rápido (ou a que passou mais gente); 'lento' = a mais demorada que
        terminou; 'quase'/'falha' = sala que não terminou (a que passou mais gente / qualquer)."""
        est = rod.reg["estado"][:, -1]
        suc = np.where(est == SUCESSO)[0]
        fal = np.where(est == FALHA)[0]
        x = rod.reg["s"][:, -1, :, 0]
        passaram = (x > X_PASSOU).sum(1)
        if tipo == "primeiro":
            if len(suc):
                return int(suc[np.argmin(rod.morte[suc])])
            return int(np.argmax(passaram))
        if tipo == "lento" and len(suc):
            return int(suc[np.argmax(rod.morte[suc])])
        if tipo in ("quase", "falha") and len(fal):
            return int(fal[np.argmax(passaram[fal])]) if tipo == "quase" else int(fal[np.argmin(passaram[fal])])
        return None

    def ambiente(self, dur):
        return None


S_TEXTO = 7.4
