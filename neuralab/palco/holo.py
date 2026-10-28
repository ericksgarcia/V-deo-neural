"""Motor 2D holográfico: câmera 2D + primitivas neon + brilho (bloom).

Tudo é desenhado em coordenadas do mundo (metros, y para cima) e convertido pela Camera2D.
As espessuras de linha são em pixels (o neon fica nítido em qualquer zoom). As cores somam
(mistura aditiva): 100 rastros sobrepostos viram um mapa de calor luminoso.

Uso em um quadro:
    h = Holo(largura, altura, Camera2D(centro=(0, 5), escala=60))
    h.fundo()
    h.grade(1.0)
    h.linha([(0, 0), (3, 4)], CIANO)
    h.forma(pontos, AMARELO)
    sup = h.finaliza()          # aplica o bloom e devolve a superfície pronta
"""
import math
from dataclasses import dataclass

import cairo
import numpy as np
from PIL import Image, ImageFilter

CIANO = (0.25, 0.92, 1.0)
MAGENTA = (1.0, 0.3, 0.8)
ROSA = (1.0, 0.36, 0.72)
AMARELO = (1.0, 0.74, 0.12)
AZUL = (0.3, 0.55, 1.0)
VERDE = (0.3, 1.0, 0.6)
VERMELHO = (1.0, 0.28, 0.35)
LARANJA = (1.0, 0.55, 0.15)
BRANCO = (1.0, 1.0, 1.0)


def clareia(c, k=0.55):
    """Mistura com branco: o 'miolo' quente de uma linha neon."""
    return tuple(v + (1 - v) * k for v in c)


@dataclass
class Camera2D:
    centro: tuple = (0.0, 0.0)   # ponto do mundo no meio da cena
    escala: float = 60.0         # pixels por metro
    rotacao: float = 0.0         # graus
    tremor: float = 0.0          # intensidade de tremida (px)
    t: float = 0.0               # tempo (para a tremida)

    def mistura(self, outra, k):
        k = min(max(k, 0.0), 1.0)
        k = k * k * (3 - 2 * k)
        l = lambda a, b: a + (b - a) * k
        return Camera2D((l(self.centro[0], outra.centro[0]), l(self.centro[1], outra.centro[1])),
                        l(self.escala, outra.escala), l(self.rotacao, outra.rotacao),
                        l(self.tremor, outra.tremor), self.t)


class Holo:
    def __init__(self, largura, altura, cam, fundo_cor=(0.01, 0.02, 0.04)):
        self.w, self.h, self.cam = int(largura), int(altura), cam
        self.sup = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.w, self.h)
        self.ctx = cairo.Context(self.sup)
        self.ctx.set_antialias(cairo.ANTIALIAS_GOOD)
        self.fundo_cor = fundo_cor
        a = math.radians(cam.rotacao)
        self._c, self._s = math.cos(a), math.sin(a)
        if cam.tremor:
            self._dx = cam.tremor * math.sin(cam.t * 53.1) * math.sin(cam.t * 7.3)
            self._dy = cam.tremor * math.cos(cam.t * 47.7) * math.sin(cam.t * 5.9)
        else:
            self._dx = self._dy = 0.0

    # ------------------------------------------------------------------ coordenadas
    def tela(self, x, y):
        x = np.asarray(x, float) - self.cam.centro[0]
        y = np.asarray(y, float) - self.cam.centro[1]
        xr, yr = x * self._c - y * self._s, x * self._s + y * self._c
        return self.w / 2 + xr * self.cam.escala + self._dx, self.h / 2 - yr * self.cam.escala + self._dy

    def px(self, metros):
        return metros * self.cam.escala

    def _caminho(self, pts, fechado=False):
        P = np.asarray(pts, float)
        X, Y = self.tela(P[:, 0], P[:, 1])
        ctx = self.ctx
        ctx.move_to(X[0], Y[0])
        for a, b in zip(X[1:], Y[1:]):
            ctx.line_to(a, b)
        if fechado:
            ctx.close_path()

    def _cor(self, c, a):
        self.ctx.set_source_rgba(c[0], c[1], c[2], a)

    # ------------------------------------------------------------------ fundo
    def fundo(self, brilho_centro=(0.05, 0.12, 0.2), manchas=((0.15, 0.1, (0.35, 0.1, 0.5)),
                                                             (0.85, 0.9, (0.0, 0.3, 0.45)))):
        """Fundo índigo profundo + manchas de luz coloridas (profundidade) que andam com a câmera."""
        ctx = self.ctx
        g = cairo.LinearGradient(0, 0, 0, self.h)
        g.add_color_stop_rgb(0, 0.012, 0.016, 0.045)
        g.add_color_stop_rgb(1, 0.02, 0.03, 0.07)
        ctx.set_source(g)
        ctx.paint()
        cx, cy = self.cam.centro
        for u, v, c in manchas:
            x = u * self.w - cx * self.cam.escala * 0.08
            y = v * self.h + cy * self.cam.escala * 0.08
            r = max(self.w, self.h) * 0.6
            gg = cairo.RadialGradient(x, y, 0, x, y, r)
            gg.add_color_stop_rgba(0, *c, 0.2)
            gg.add_color_stop_rgba(1, *c, 0)
            ctx.set_source(gg)
            ctx.paint()
        g = cairo.RadialGradient(self.w / 2, self.h * 0.55, 0, self.w / 2, self.h * 0.55, max(self.w, self.h) * 0.6)
        g.add_color_stop_rgba(0, *brilho_centro, 0.5)
        g.add_color_stop_rgba(1, *brilho_centro, 0)
        ctx.set_source(g)
        ctx.paint()

    def grade(self, passo=1.0, cor=CIANO, alfa=0.12, limites=None, pontos=True):
        """Grade holográfica do chão, que esmaece nas bordas da tela."""
        ctx = self.ctx
        if limites is None:
            x0, y0 = self.mundo(0, self.h)
            x1, y1 = self.mundo(self.w, 0)
            limites = (min(x0, x1) - passo, max(x0, x1) + passo, min(y0, y1) - passo, max(y0, y1) + passo)
        xa, xb, ya, yb = limites
        ctx.set_line_width(1)
        for x in np.arange(math.floor(xa / passo) * passo, xb + 1e-6, passo):
            self._caminho([(x, ya), (x, yb)])
            self._cor(cor, alfa * (1.6 if abs(x / passo) % 5 < 1e-6 else 1))
            ctx.stroke()
        for y in np.arange(math.floor(ya / passo) * passo, yb + 1e-6, passo):
            self._caminho([(xa, y), (xb, y)])
            self._cor(cor, alfa * (1.6 if abs(y / passo) % 5 < 1e-6 else 1))
            ctx.stroke()
        if pontos:
            for x in np.arange(math.floor(xa / passo) * passo, xb + 1e-6, passo):
                for y in np.arange(math.floor(ya / passo) * passo, yb + 1e-6, passo):
                    X, Y = self.tela(x, y)
                    self._cor(cor, alfa * 2.2)
                    ctx.rectangle(X - 1.2, Y - 1.2, 2.4, 2.4)
            ctx.fill()

    def mundo(self, X, Y):
        """Pixel -> mundo (inverso de tela)."""
        xr = (X - self.w / 2 - self._dx) / self.cam.escala
        yr = -(Y - self.h / 2 - self._dy) / self.cam.escala
        x = xr * self._c + yr * self._s
        y = -xr * self._s + yr * self._c
        return x + self.cam.centro[0], y + self.cam.centro[1]

    # ------------------------------------------------------------------ primitivas neon
    def linha(self, pts, cor, larg=3.0, alfa=1.0, fechado=False, tracejado=None, halo=True):
        ctx = self.ctx
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        if tracejado:
            ctx.set_dash(tracejado)
        if halo:
            self._caminho(pts, fechado)
            self._cor(cor, 0.22 * alfa)
            ctx.set_line_width(larg * 3.2)
            ctx.stroke()
        self._caminho(pts, fechado)
        self._cor(cor, 0.85 * alfa)
        ctx.set_line_width(larg)
        ctx.stroke()
        self._caminho(pts, fechado)
        self._cor(clareia(cor, 0.4), 0.6 * alfa)
        ctx.set_line_width(max(larg * 0.35, 0.8))
        ctx.stroke()
        ctx.set_dash([])
        ctx.set_operator(cairo.OPERATOR_OVER)

    def forma(self, pts, cor, alfa=1.0, larg=2.5, preenche=0.16, gradiente=True, oclusor=False):
        """Polígono holográfico: preenchimento translúcido com gradiente + borda neon.

        oclusor=True pinta antes um fundo escuro opaco: a forma 'tampa' o que está atrás
        (camadas limpas em vez de luz somada)."""
        ctx = self.ctx
        if oclusor:
            self._caminho(pts, True)
            ctx.set_source_rgba(0.012, 0.02, 0.05, 0.92 * alfa)
            ctx.fill()
        ctx.set_operator(cairo.OPERATOR_ADD)
        self._caminho(pts, True)
        if gradiente:
            P = np.asarray(pts, float)
            X, Y = self.tela(P[:, 0], P[:, 1])
            g = cairo.LinearGradient(0, Y.min(), 0, Y.max())
            g.add_color_stop_rgba(0, *cor, preenche * 1.6 * alfa)
            g.add_color_stop_rgba(1, *cor, preenche * 0.4 * alfa)
            ctx.set_source(g)
        else:
            self._cor(cor, preenche * alfa)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
        self.linha(pts, cor, larg, alfa, fechado=True)

    def preenche(self, pts, cor, alfa=0.1):
        """Só o preenchimento translúcido (sem borda): bloco cheio que não vira grade de contornos."""
        ctx = self.ctx
        ctx.set_operator(cairo.OPERATOR_ADD)
        self._caminho(pts, True)
        self._cor(cor, alfa)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)

    def circulo(self, c, r, cor, alfa=1.0, larg=2.5, preenche=0.12, oclusor=False):
        k = np.linspace(0, 2 * math.pi, 40)
        self.forma(np.c_[c[0] + r * np.cos(k), c[1] + r * np.sin(k)], cor, alfa, larg, preenche, gradiente=False,
                   oclusor=oclusor)

    def ponto_luz(self, c, raio_px, cor, alfa=1.0):
        """Brilho radial (bola, faísca, luz)."""
        X, Y = self.tela(*c)
        ctx = self.ctx
        ctx.set_operator(cairo.OPERATOR_ADD)
        g = cairo.RadialGradient(float(X), float(Y), 0, float(X), float(Y), raio_px)
        g.add_color_stop_rgba(0, *clareia(cor, 0.8), alfa)
        g.add_color_stop_rgba(0.25, *cor, 0.7 * alfa)
        g.add_color_stop_rgba(1, *cor, 0)
        ctx.set_source(g)
        ctx.arc(float(X), float(Y), raio_px, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)

    def rastro(self, pts, cor, larg=3.0, alfa=1.0):
        """Rastro que some na cauda (mais forte perto da ponta)."""
        P = np.asarray(pts, float)
        n = len(P)
        if n < 2:
            return
        ctx = self.ctx
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        X, Y = self.tela(P[:, 0], P[:, 1])
        for i in range(1, n):
            k = i / (n - 1)
            ctx.move_to(X[i - 1], Y[i - 1])
            ctx.line_to(X[i], Y[i])
            self._cor(cor, alfa * k * k)
            ctx.set_line_width(larg * (0.3 + 0.7 * k))
            ctx.stroke()
        ctx.set_operator(cairo.OPERATOR_OVER)

    def cone(self, origem, angulo, abertura, comprimento, cor, alfa=0.5):
        """Leque de luz (visão, farol, direção do corpo). Ângulo em radianos no mundo."""
        X, Y = self.tela(*origem)
        ctx = self.ctx
        ctx.set_operator(cairo.OPERATOR_ADD)
        r = self.px(comprimento)
        g = cairo.RadialGradient(float(X), float(Y), 0, float(X), float(Y), r)
        g.add_color_stop_rgba(0, *cor, alfa)
        g.add_color_stop_rgba(1, *cor, 0)
        ctx.set_source(g)
        rot = math.radians(self.cam.rotacao)
        a = -(angulo + rot)
        ctx.move_to(float(X), float(Y))
        ctx.arc(float(X), float(Y), r, a - abertura / 2, a + abertura / 2)
        ctx.close_path()
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)

    def pulso(self, c, idade, cor, raio=1.5, dur=0.6, larg=4):
        """Anel que se expande e some (impacto, sucesso, alerta)."""
        if idade < 0 or idade > dur:
            return
        k = idade / dur
        X, Y = self.tela(*c)
        ctx = self.ctx
        ctx.set_operator(cairo.OPERATOR_ADD)
        ctx.arc(float(X), float(Y), self.px(raio) * (0.2 + 0.8 * k), 0, 2 * math.pi)
        self._cor(cor, (1 - k) * 0.9)
        ctx.set_line_width(larg * (1 - k) + 1)
        ctx.stroke()
        ctx.set_operator(cairo.OPERATOR_OVER)

    def particulas(self, c, idade, cor, n=18, alcance=2.0, dur=0.9, semente=0, gravidade=0.0):
        if idade < 0 or idade > dur:
            return
        k = idade / dur
        rng = np.random.default_rng(semente)
        ang = rng.uniform(0, 2 * math.pi, n)
        vel = rng.uniform(0.3, 1.0, n) * alcance
        for a, v in zip(ang, vel):
            d = v * (1 - (1 - k) ** 2)
            p = (c[0] + d * math.cos(a), c[1] + d * math.sin(a) - gravidade * k * k)
            self.ponto_luz(p, 7 * (1 - k) + 2, cor, 1 - k)

    def seta(self, a, b, cor, larg=3, alfa=1.0, ponta=0.5):
        self.linha([a, b], cor, larg, alfa)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for d in (2.6, -2.6):
            self.linha([b, (b[0] + ponta * math.cos(ang + d), b[1] + ponta * math.sin(ang + d))], cor, larg, alfa)

    def texto(self, s, c, tam=22, cor=CIANO, alfa=1.0, alinha="c", familia="JetBrains Mono ExtraBold"):
        X, Y = self.tela(*c)
        ctx = self.ctx
        ctx.select_font_face(familia, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(tam)
        w = ctx.text_extents(s).x_advance
        x = float(X) - (w / 2 if alinha == "c" else (w if alinha == "d" else 0))
        ctx.move_to(x, float(Y))
        self._cor(cor, alfa)
        ctx.show_text(s)

    # ------------------------------------------------------------------ pós-processamento
    def finaliza(self, bloom=1.0, vinheta=0.55):
        if bloom > 0:
            _bloom(self.sup, bloom)
        if vinheta:
            ctx = self.ctx
            g = cairo.RadialGradient(self.w / 2, self.h / 2, min(self.w, self.h) * 0.35,
                                     self.w / 2, self.h / 2, max(self.w, self.h) * 0.75)
            g.add_color_stop_rgba(0, 0, 0, 0, 0)
            g.add_color_stop_rgba(1, 0, 0, 0, vinheta)
            ctx.set_source(g)
            ctx.paint()
        return self.sup


def _bloom(sup, forca=1.0):
    """Brilho real: reduz, desfoca em duas escalas e soma de volta (as partes claras 'vazam')."""
    sup.flush()
    w, h = sup.get_width(), sup.get_height()
    est = sup.get_stride()
    buf = np.ndarray((h, est // 4, 4), np.uint8, sup.get_data())[:, :w, :]
    img = Image.frombuffer("RGBA", (w, h), np.ascontiguousarray(buf).tobytes(), "raw", "RGBA", 0, 1)
    soma = np.zeros((h, w, 3), np.float32)
    for div, raio, peso in ((4, 3, 0.9), (10, 6, 0.8)):
        p = img.resize((max(w // div, 1), max(h // div, 1)), Image.BILINEAR)
        p = p.filter(ImageFilter.GaussianBlur(raio)).resize((w, h), Image.BILINEAR)
        soma += np.asarray(p, np.float32)[:, :, :3] * peso
    rgb = buf[:, :, :3].astype(np.float32)
    rgb += soma * forca
    buf[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    buf[:, :, 3] = 255
    sup.mark_dirty()
