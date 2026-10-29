"""Kit de HUD "laboratório high-tech" reutilizável em qualquer vídeo (1080x1920).

Peças: fundo com grade, cabeçalho, painéis de vidro chanfrados, medidores em anel, contador,
linha do tempo com marcos, console de eventos, rede neural com pulsos, moldura de câmera,
cartão de descoberta, selo de replay, telestrador, legenda grande e tela final.
Nenhuma peça sabe qual é o desafio: recebem só números, textos e cores.
"""
import math

import cairo
import numpy as np

W, H = 1080, 1920
TITULO, UI, MONO, MONO_B = "Inter Display Black", "Inter SemiBold", "JetBrains Mono", "JetBrains Mono ExtraBold"

C = {
    "fundo": (0.018, 0.028, 0.05),
    "vidro": (0.04, 0.07, 0.11),
    "ciano": (0.23, 0.91, 1.0),
    "ciano2": (0.12, 0.45, 0.6),
    "texto": (0.92, 0.96, 1.0),
    "sutil": (0.45, 0.56, 0.66),
    "verde": (0.3, 1.0, 0.62),
    "vermelho": (1.0, 0.3, 0.38),
    "amarelo": (1.0, 0.8, 0.2),
    "azul": (0.3, 0.62, 1.0),
    "preto": (0, 0, 0),
    "branco": (1, 1, 1),
    "tele": (1.0, 0.92, 0.25),
}

# layout (y) — o que importa fica longe da coluna de botões do TikTok (x > ~950, y 800-1500)
TOPO = (150, 150)        # y, altura da fileira de painéis de cima
CENA = (30, 312, 1020, 868)   # a cena termina em y=1180; a legenda tem faixa própria logo abaixo
LEGENDA_Y = 1292
BAIXO = (1345, 165)


def cor(ctx, c, a=1.0):
    c = C[c] if isinstance(c, str) else c
    ctx.set_source_rgba(c[0], c[1], c[2], a)


def fonte(ctx, familia, tam):
    ctx.select_font_face(familia, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(tam)


def texto(ctx, s, x, y, tam, c="texto", a=1.0, familia=UI, alinha="e", contorno=0, espaco=0.0):
    fonte(ctx, familia, tam)
    w = ctx.text_extents(s).x_advance + espaco * max(len(s) - 1, 0)
    x = x - w / 2 if alinha == "c" else (x - w if alinha == "d" else x)
    if espaco:
        for ch in s:
            texto(ctx, ch, x, y, tam, c, a, familia, contorno=contorno)
            fonte(ctx, familia, tam)
            x += ctx.text_extents(ch).x_advance + espaco
        return w
    if contorno:
        ctx.move_to(x, y)
        ctx.text_path(s)
        cor(ctx, "preto", 0.9 * a)
        ctx.set_line_width(contorno)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    ctx.move_to(x, y)
    cor(ctx, c, a)
    ctx.show_text(s)
    return w


def larg(ctx, s, tam, familia=UI):
    fonte(ctx, familia, tam)
    return ctx.text_extents(s).x_advance


def suave(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def brilho(ctx, x, y, r, c, a):
    c = C[c] if isinstance(c, str) else c
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *c, a)
    g.add_color_stop_rgba(1, *c, 0)
    ctx.set_source(g)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.fill()


def chanfro(ctx, x, y, w, h, k=18):
    """Retângulo com cantos chanfrados (superior direito e inferior esquerdo)."""
    ctx.move_to(x, y)
    ctx.line_to(x + w - k, y)
    ctx.line_to(x + w, y + k)
    ctx.line_to(x + w, y + h)
    ctx.line_to(x + k, y + h)
    ctx.line_to(x, y + h - k)
    ctx.close_path()


def _neon(ctx, c, a, larg_=1.5):
    """Contorno com brilho: duas passadas (larga e fraca, fina e forte)."""
    cor(ctx, c, 0.18 * a)
    ctx.set_line_width(larg_ * 5)
    ctx.stroke_preserve()
    cor(ctx, c, 0.9 * a)
    ctx.set_line_width(larg_)
    ctx.stroke()


# ------------------------------------------------------------------ fundo e moldura

class Fundo:
    """Fundo estático pré-renderizado: gradiente, grade de pontos, vinheta."""

    def __init__(self):
        self.sup = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        ctx = cairo.Context(self.sup)
        g = cairo.LinearGradient(0, 0, 0, H)
        g.add_color_stop_rgb(0, 0.03, 0.05, 0.09)
        g.add_color_stop_rgb(0.5, *C["fundo"])
        g.add_color_stop_rgb(1, 0.01, 0.015, 0.03)
        ctx.set_source(g)
        ctx.paint()
        for y in range(0, H, 24):
            for x in range(0, W, 24):
                cor(ctx, "ciano", 0.05 if (x // 24 + y // 24) % 5 else 0.09)
                ctx.rectangle(x, y, 1.5, 1.5)
                ctx.fill()
        brilho(ctx, W / 2, 770, 900, "ciano2", 0.12)
        v = cairo.RadialGradient(W / 2, H / 2, 500, W / 2, H / 2, 1250)
        v.add_color_stop_rgba(0, 0, 0, 0, 0)
        v.add_color_stop_rgba(1, 0, 0, 0, 0.7)
        ctx.set_source(v)
        ctx.paint()


def cabecalho(ctx, marca, experimento, titulo, t):
    y = 92
    # logotipo: hexágono com um nó
    cx, cy, r = 54, y - 10, 15
    ctx.move_to(cx + r, cy)
    for k in range(1, 7):
        ctx.line_to(cx + r * math.cos(k * math.pi / 3), cy + r * math.sin(k * math.pi / 3))
    _neon(ctx, "ciano", 1, 2)
    brilho(ctx, cx, cy, 10, "ciano", 0.9)
    texto(ctx, marca, 80, y, 26, "texto", familia=MONO_B, espaco=2)
    texto(ctx, f"// EXP {experimento} · {titulo}", 80 + larg(ctx, marca, 26, MONO_B) + 2 * len(marca) + 14, y, 22,
          "sutil", familia=MONO)
    pisca = 0.35 + 0.65 * (math.sin(t * 5) > -0.2)
    brilho(ctx, 772, y - 9, 16, "vermelho", 0.6 * pisca)
    cor(ctx, "vermelho", pisca)
    ctx.arc(772, y - 9, 6, 0, 2 * math.pi)
    ctx.fill()
    texto(ctx, "SIMULAÇÃO REAL", 1050, y, 22, "vermelho", familia=MONO_B, alinha="d")


def painel(ctx, x, y, w, h, titulo, c="ciano", indice=None, a=1.0):
    """Painel de vidro com borda neon e etiqueta."""
    chanfro(ctx, x, y, w, h)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgba(0, *C["vidro"], 0.88 * a)
    g.add_color_stop_rgba(1, 0.02, 0.035, 0.06, 0.92 * a)
    ctx.set_source(g)
    ctx.fill_preserve()
    cor(ctx, c, 0.45 * a)
    ctx.set_line_width(1.2)
    ctx.stroke()
    # filete brilhante no topo
    cor(ctx, c, 0.9 * a)
    ctx.rectangle(x + 14, y - 1, min(90, w * 0.3), 3)
    ctx.fill()
    rotulo = f"{indice:02d} // {titulo}" if indice is not None else titulo
    texto(ctx, rotulo, x + 16, y + 28, 17, c, 0.9 * a, familia=MONO_B, espaco=1)


def scanlines(ctx, t, a=1.0):
    """Linhas de varredura bem sutis + uma faixa de luz que desce devagar."""
    cor(ctx, "preto", 0.10 * a)
    for y in range(0, H, 4):
        ctx.rectangle(0, y, W, 1)
    ctx.fill()
    yv = (t * 260) % (H + 300) - 150
    g = cairo.LinearGradient(0, yv - 80, 0, yv + 80)
    g.add_color_stop_rgba(0, *C["ciano"], 0)
    g.add_color_stop_rgba(0.5, *C["ciano"], 0.035 * a)
    g.add_color_stop_rgba(1, *C["ciano"], 0)
    ctx.set_source(g)
    ctx.rectangle(0, yv - 80, W, 160)
    ctx.fill()


def moldura_cena(ctx, t, rotulo_cam="CAM 01", velocidade=None, tempo_sim=None, ret=CENA):
    """Moldura de visor de câmera em volta da cena 2.5D."""
    x, y, w, h = ret
    chanfro(ctx, x, y, w, h, 26)
    _neon(ctx, "ciano", 0.55, 1.2)
    L = 46
    ctx.set_line_width(4)
    cor(ctx, "ciano", 0.95)
    for (px, py, sx, sy) in ((x + 8, y + 8, 1, 1), (x + w - 8, y + h - 8, -1, -1),
                             (x + w - 8, y + 34, -1, 1), (x + 8, y + h - 34, 1, -1)):
        ctx.move_to(px, py + sy * L)
        ctx.line_to(px, py)
        ctx.line_to(px + sx * L, py)
    ctx.stroke()
    # réguas laterais
    for k in range(41):
        yy = y + 60 + k * (h - 120) / 40
        tam = 16 if k % 5 == 0 else 8
        cor(ctx, "ciano", 0.5 if k % 5 == 0 else 0.25)
        ctx.rectangle(x + 2, yy, tam, 1.4)
        ctx.rectangle(x + w - 2 - tam, yy, tam, 1.4)
    ctx.fill()
    for k in range(31):
        xx = x + 80 + k * (w - 160) / 30
        tam = 12 if k % 5 == 0 else 6
        cor(ctx, "ciano", 0.45 if k % 5 == 0 else 0.22)
        ctx.rectangle(xx, y + h - 2 - tam, 1.4, tam)
    ctx.fill()
    # mira central
    mx, my = x + w / 2, y + h / 2
    cor(ctx, "ciano", 0.18)
    ctx.set_line_width(1)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ctx.move_to(mx + dx * 14, my + dy * 14)
        ctx.line_to(mx + dx * 34, my + dy * 34)
    ctx.stroke()
    replay = rotulo_cam.startswith("◀◀")
    texto(ctx, rotulo_cam if replay else f"● {rotulo_cam}", x + 30, y + 52, 24, "amarelo" if replay else "ciano",
          0.95, familia=MONO_B)
    if velocidade is not None:
        rot = f"LENTO {velocidade:.1f}x" if velocidade < 0.9 else ("TEMPO REAL" if velocidade < 1.15
                                                                    else f"ACELERADO {velocidade:.1f}x")
        texto(ctx, rot, x + w - 30, y + 52, 24, "amarelo" if velocidade < 0.9 else "texto", 0.85,
              familia=MONO_B, alinha="d")


def recorte_cena(ctx, ret=CENA):
    x, y, w, h = ret
    chanfro(ctx, x, y, w, h, 26)
    ctx.clip()


# ------------------------------------------------------------------ medidores

def medidor_anel(ctx, cx, cy, r, valor, c, rotulo, sub=None, a=1.0):
    """Anel segmentado (0-100%) com número grande no centro."""
    n = 48
    ini = math.radians(135)
    tot = math.radians(270)
    acesos = valor * n
    ctx.set_line_width(10)
    for k in range(n):
        a0 = ini + tot * k / n
        a1 = a0 + tot / n * 0.7
        ctx.new_path()
        ctx.arc(cx, cy, r, a0, a1)
        on = k < acesos
        cor(ctx, c if on else "ciano2", (0.95 if on else 0.25) * a)
        ctx.stroke()
    if acesos > 0:
        ang = ini + tot * min(valor, 1)
        brilho(ctx, cx + r * math.cos(ang), cy + r * math.sin(ang), 22, c, 0.8 * a)
    cor(ctx, c, 0.3 * a)
    ctx.set_line_width(1)
    ctx.new_path()
    ctx.arc(cx, cy, r - 16, 0, 2 * math.pi)
    ctx.stroke()
    texto(ctx, f"{valor * 100:.0f}", cx - 6, cy + 16, 50, "texto", a, familia=MONO_B, alinha="c")
    texto(ctx, "%", cx + larg(ctx, f"{valor * 100:.0f}", 50, MONO_B) / 2 - 2, cy + 16, 22, c, a, familia=MONO_B)
    texto(ctx, rotulo, cx, cy + r + 8, 19, c, a, familia=MONO_B, alinha="c", espaco=1)
    if sub:
        texto(ctx, sub, cx, cy + 46, 15, "sutil", a, familia=MONO, alinha="c")


def linha_tempo(ctx, x, y, w, h, serie, g, total, marcos=(), c="ciano", a=1.0):
    """Mini-gráfico da série por geração até g, com cabeça de leitura e marcos (descobertas)."""
    serie = np.asarray(serie, float)
    cor(ctx, "ciano2", 0.35 * a)
    ctx.set_line_width(1)
    for k in range(3):
        yy = y + h * k / 2
        ctx.move_to(x, yy)
        ctx.line_to(x + w, yy)
    ctx.stroke()
    n = max(1, min(int(g), len(serie)))
    xs = x + np.arange(n) / max(total - 1, 1) * w
    ys = y + h - np.clip(serie[:n], 0, 1) * h
    if n >= 2:
        ctx.move_to(xs[0], y + h)
        for u, v in zip(xs, ys):
            ctx.line_to(u, v)
        ctx.line_to(xs[-1], y + h)
        ctx.close_path()
        gr = cairo.LinearGradient(0, y, 0, y + h)
        gr.add_color_stop_rgba(0, *C[c] if isinstance(c, str) else c, 0.35 * a)
        gr.add_color_stop_rgba(1, *C[c] if isinstance(c, str) else c, 0.0)
        ctx.set_source(gr)
        ctx.fill()
        ctx.move_to(xs[0], ys[0])
        for u, v in zip(xs[1:], ys[1:]):
            ctx.line_to(u, v)
        cor(ctx, c, a)
        ctx.set_line_width(2)
        ctx.stroke()
    px = x + (n - 1) / max(total - 1, 1) * w
    cor(ctx, "texto", 0.8 * a)
    ctx.rectangle(px - 0.75, y - 6, 1.5, h + 12)
    ctx.fill()
    brilho(ctx, px, ys[-1] if n else y + h, 12, c, 0.9 * a)
    for gm, nome, cm in marcos:
        if gm > g:
            continue
        mx = x + gm / max(total - 1, 1) * w
        cor(ctx, cm, 0.95 * a)
        ctx.move_to(mx, y - 4)
        ctx.line_to(mx - 5, y - 12)
        ctx.line_to(mx + 5, y - 12)
        ctx.close_path()
        ctx.fill()


def contador_geracao(ctx, x, y, w, h, g, total, serie, marcos, rotulo_serie, a=1.0):
    painel(ctx, x, y, w, h, "GERAÇÃO", indice=1, a=a)
    texto(ctx, f"{g:03d}", x + 16, y + 88, 58, "texto", a, familia=MONO_B)
    texto(ctx, f"/{total}", x + 20 + larg(ctx, f"{g:03d}", 58, MONO_B), y + 88, 24, "sutil", a, familia=MONO)
    linha_tempo(ctx, x + 18, y + 108, w - 36, 28, serie, g, total, marcos, a=a)


# ------------------------------------------------------------------ console e rede

def console(ctx, x, y, w, h, linhas, t, a=1.0, n=4, tam=22):
    """Terminal de eventos. linhas: [(instante, texto, cor)]; as novas aparecem digitando."""
    painel(ctx, x, y, w, h, "LOG DO EXPERIMENTO", indice=4, a=a)
    vis = [l for l in linhas if l[0] <= t][-n:]
    passo = 30
    yy = y + h - 18 - (len(vis) - 1) * passo
    maxw = w - 60
    for k, (t0, s, c) in enumerate(vis):
        while s and larg(ctx, s, tam, MONO) > maxw:   # corta com reticências
            s = s[:-2] + "…"
        idade = t - t0
        n_ch = int(len(s) * min(idade / 0.5, 1))
        alfa = a * (0.5 + 0.5 * (k == len(vis) - 1))
        texto(ctx, ">", x + 14, yy, tam, "ciano", alfa, familia=MONO_B)
        texto(ctx, s[:n_ch], x + 36, yy, tam, c, alfa, familia=MONO)
        if k == len(vis) - 1 and (t * 2) % 1 < 0.5:
            cor(ctx, "ciano", alfa)
            ctx.rectangle(x + 38 + larg(ctx, s[:n_ch], tam, MONO), yy - tam * 0.8, 10, tam)
            ctx.fill()
        yy += passo


def rede(ctx, x, y, w, h, camadas, pesos, ativ, t, saidas=(), titulo="CÉREBRO DO LÍDER", c="ciano", a=1.0):
    """Rede neural: nós acendem com a ativação; pulsos correm nas ligações mais fortes."""
    painel(ctx, x, y, w, h, titulo, c=c, indice=5, a=a)
    x0, y0, ww, hh = x + 24, y + 44, w - 160, h - 56
    cols = len(camadas)
    pos = []
    for ci, n in enumerate(camadas):
        xs = x0 + ci * ww / (cols - 1)
        pos.append([(xs, y0 + hh * (j + 0.5) / n) for j in range(n)])
    for ci, (Wm, _) in enumerate(pesos):
        for i, (xa, ya) in enumerate(pos[ci]):
            for j, (xb, yb) in enumerate(pos[ci + 1]):
                wv = float(Wm[i, j])
                f = min(abs(wv) / 2.0, 1)
                if f < 0.15:
                    continue
                cc = c if wv > 0 else "vermelho"
                cor(ctx, cc, 0.08 + 0.35 * f * a)
                ctx.set_line_width(0.6 + 1.6 * f)
                ctx.move_to(xa, ya)
                ctx.line_to(xb, yb)
                ctx.stroke()
                if f > 0.6:   # pulso de sinal viajando
                    u = (t * 1.2 + (i * 7 + j * 3 + ci) * 0.137) % 1
                    brilho(ctx, xa + (xb - xa) * u, ya + (yb - ya) * u, 6, cc, 0.9 * a)
    idx = 0
    for ci, col in enumerate(pos):
        for j, (px, py) in enumerate(col):
            v = float(ativ[idx]) if ativ is not None and idx < len(ativ) else 0.0
            idx += 1
            r = 8 if ci == cols - 1 else 5.5
            brilho(ctx, px, py, r * 3, c, 0.5 * abs(v) * a)
            cor(ctx, "fundo", a)
            ctx.arc(px, py, r + 2, 0, 2 * math.pi)
            ctx.fill()
            cor(ctx, c if v >= 0 else "vermelho", (0.3 + 0.7 * min(abs(v), 1)) * a)
            ctx.arc(px, py, r, 0, 2 * math.pi)
            ctx.fill()
            if ci == cols - 1 and j < len(saidas):
                texto(ctx, saidas[j], px + 16, py + 6, 16, "texto", 0.9 * a, familia=MONO_B)
                barra = min(abs(v), 1) * 60
                cor(ctx, c, 0.8 * a)
                ctx.rectangle(px + 16, py + 12, barra, 3)
                ctx.fill()


# ------------------------------------------------------------------ cartões e selos

def cartao_descoberta(ctx, t_local, dur, c, numero, rotulo, nome, stat, ret=CENA):
    """'DESCOBERTA #n': entra grande (com falha digital) por ~1,3 s e encolhe para um selo no canto."""
    if t_local < 0:
        return
    x0, y0, w0, h0 = ret
    sai = suave((dur - t_local) / 0.3)
    grande = 1 - suave((t_local - 1.3) / 0.35)
    entra = suave(t_local / 0.35)
    # interpola entre o cartão grande (topo da cena) e o selo compacto (canto superior esquerdo)
    gx, gy, gw, gh = x0 + 30, y0 + 80, w0 - 60, 220
    sx, sy, sw, sh = x0 + 20, y0 + 74, 560, 92
    k = grande
    x, y = sx + (gx - sx) * k, sy + (gy - sy) * k
    w, h = sw + (gw - sw) * k, sh + (gh - sh) * k
    a = min(entra, sai)
    if a <= 0:
        return
    ctx.save()
    if t_local < 0.35:
        rng = np.random.default_rng(int(t_local * 60))
        ctx.translate((rng.random() - 0.5) * 40 * (1 - entra), 0)
    chanfro(ctx, x, y, w, h, 22 + 8 * k)
    cor(ctx, (0.02, 0.035, 0.07), 0.95 * a)
    ctx.fill_preserve()
    _neon(ctx, c, a, 2)
    if k > 0.05:
        sy_ = y + (t_local * 300) % h
        cor(ctx, c, 0.12 * a * k)
        ctx.rectangle(x, sy_, w, 3)
        ctx.fill()
    tam_rot = 20 + 4 * k
    texto(ctx, f"DESCOBERTA #{numero:02d}  ·  {rotulo}", x + 24, y + 30 + 18 * k, tam_rot, c, a, familia=MONO_B,
          espaco=1)
    tam_nome = 40 + 52 * k
    if larg(ctx, nome, tam_nome, TITULO) > w - 50:
        tam_nome *= (w - 50) / larg(ctx, nome, tam_nome, TITULO)
    texto(ctx, nome, x + 22, y + 74 + 72 * k, tam_nome, "texto", a, familia=TITULO)
    if k > 0.3:
        texto(ctx, stat, x + 26, y + 196, 26, c, a * k, familia=MONO_B)
    ctx.restore()


def carimbo(ctx, s, c, t_local, ret=CENA, sub=None):
    """Número grande na cena (ex.: 'FORA 42%'), entra com um pulo; serve de 'interruptor' visual."""
    if t_local < 0:
        return
    x0, y0, w0, h0 = ret
    k = suave(t_local / 0.25)
    pop = 1 + 0.25 * (1 - k)
    ctx.save()
    ctx.translate(x0 + w0 - 30, y0 + 150)
    ctx.scale(pop, pop)
    wc = max(larg(ctx, s, 64, TITULO), larg(ctx, sub or "", 26, MONO_B)) + 44
    chanfro(ctx, -wc, -64, wc, 134 if sub else 96, 16)
    cor(ctx, (0.015, 0.025, 0.05), 0.88 * k)
    ctx.fill_preserve()
    _neon(ctx, c, k, 2)
    texto(ctx, s, -22, 0, 64, c, k, familia=TITULO, alinha="d")
    if sub:
        texto(ctx, sub, -22, 44, 26, "texto", k, familia=MONO_B, alinha="d")
    ctx.restore()


def titulo_gancho(ctx, linhas, t_local, ret=CENA):
    """Promessa do vídeo, fixa e grande no topo da cena desde o quadro 0."""
    x0, y0, w0, h0 = ret
    a = suave((2.0 - t_local) / 0.4)          # entra no 1º quadro e some em ~2 s para liberar a cena
    if a <= 0:
        return
    for j, (s, c) in enumerate(linhas):
        tam = 70
        if larg(ctx, s, tam, TITULO) > w0 - 80:
            tam *= (w0 - 80) / larg(ctx, s, tam, TITULO)
        texto(ctx, s, x0 + w0 / 2, y0 + 118 + j * 78, tam, c, a, familia=TITULO, alinha="c", contorno=14)


def faixa_escolha(ctx, t_local, pergunta, opcoes, ret=CENA):
    """Chamada final sobre a cena (não é tela própria): pergunta + dois botões pulsando."""
    x0, y0, w0, h0 = ret
    k = suave(t_local / 0.35)
    if k <= 0:
        return
    y = y0 + 90
    chanfro(ctx, x0 + 24, y, w0 - 48, 250, 26)
    cor(ctx, (0.015, 0.025, 0.05), 0.97 * k)
    ctx.fill_preserve()
    _neon(ctx, "ciano", k, 1.5)
    tam = 52
    if larg(ctx, pergunta, tam, TITULO) > w0 - 120:
        tam *= (w0 - 120) / larg(ctx, pergunta, tam, TITULO)
    texto(ctx, pergunta, x0 + w0 / 2, y + 70, tam, "texto", k, familia=TITULO, alinha="c")
    n = len(opcoes)
    bw = (w0 - 80 - 30 * (n - 1)) / n
    for j, (nome, c) in enumerate(opcoes):
        bx = x0 + 40 + j * (bw + 30)
        pulso = 1 + 0.04 * math.sin(t_local * 6 + j * 3)
        ctx.save()
        ctx.translate(bx + bw / 2, y + 170)
        ctx.scale(pulso, pulso)
        chanfro(ctx, -bw / 2, -50, bw, 100, 20)
        cor(ctx, c, 0.18 * k)
        ctx.fill_preserve()
        _neon(ctx, c, k, 2.5)
        tn = 40 if larg(ctx, nome, 40, TITULO) < bw - 40 else 40 * (bw - 40) / larg(ctx, nome, 40, TITULO)
        texto(ctx, nome, 0, 14, tn, "texto", k, familia=TITULO, alinha="c")
        ctx.restore()


def selo_replay(ctx, t_local, a=1.0, ret=CENA):
    x, y, w, h = ret
    if 0 <= t_local < 0.22:  # transição: clarão ciano que apaga + linha de varredura diagonal
        k = t_local / 0.22
        cor(ctx, "ciano", 0.38 * (1 - k) ** 2)
        ctx.rectangle(x, y, w, h)
        ctx.fill()
        xs = x - 120 + (w + 240) * k
        ctx.set_line_width(5)
        cor(ctx, "ciano", 0.9 * (1 - k))
        ctx.move_to(xs, y)
        ctx.line_to(xs - 180, y + h)
        ctx.stroke()
    # o rótulo "◀◀ REPLAY" fica na moldura (canto superior esquerdo, em amarelo)


def tele_circulo(ctx, x, y, rx, ry, prog, a=1.0):
    n = 60
    fim = int(n * min(prog, 1)) + 1
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(fim):
        ang = -math.pi / 2 + i / n * 2 * math.pi * 1.08
        w = 1 + 0.05 * math.sin(i * 0.7)
        (ctx.move_to if i == 0 else ctx.line_to)(x + rx * w * math.cos(ang), y + ry * w * math.sin(ang))
    cor(ctx, "tele", 0.25 * a)
    ctx.set_line_width(16)
    ctx.stroke_preserve()
    cor(ctx, "tele", a)
    ctx.set_line_width(6)
    ctx.stroke()


def tele_seta(ctx, x0, y0, x1, y1, prog, a=1.0, curva=0.25):
    prog = min(max(prog, 0), 1)
    if prog <= 0:
        return
    mx, my = (x0 + x1) / 2 - curva * (y1 - y0), (y0 + y1) / 2 + curva * (x1 - x0)
    pts = []
    for i in range(41):
        u = i / 40 * prog
        pts.append(((1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u * u * x1,
                    (1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u * u * y1))
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    cor(ctx, "tele", a)
    ctx.set_line_width(6)
    ctx.stroke()
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    ang = math.atan2(by - ay, bx - ax)
    for d in (2.6, -2.6):
        ctx.move_to(bx, by)
        ctx.line_to(bx + 28 * math.cos(ang + d), by + 28 * math.sin(ang + d))
    ctx.stroke()


def tele_rotulo(ctx, s, x, y, a=1.0, tam=34):
    texto(ctx, s, x, y, tam, "tele", a, familia=TITULO, alinha="c", contorno=8)


# ------------------------------------------------------------------ legenda

def blocos_de_palavras(palavras, max_chars=22, max_palavras=4):
    """[(ini, fim, palavra)] -> [(ini, fim, [palavras])] curtos, quebrando em pontuação."""
    blocos, atual = [], []
    for ini, fim, p in palavras:
        txt = " ".join(w for _, _, w in atual)
        if atual and (len(txt) + 1 + len(p) > max_chars or len(atual) >= max_palavras):
            blocos.append(atual)
            atual = []
        atual.append((ini, fim, p))
        if p[-1:] in ".?!…,:":
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    out = []
    for k, b in enumerate(blocos):
        prox = blocos[k + 1][0][0] if k + 1 < len(blocos) else b[-1][1] + 0.5
        out.append((b[0][0], max(prox, b[-1][1]), [w for _, _, w in b]))
    return out


def legenda(ctx, blocos, t, destaques, y=LEGENDA_Y):
    """1-3 palavras por vez, enormes, com contorno e um 'pulo' quando entram."""
    atual = next((b for b in blocos if b[0] <= t < b[1]), None)
    if not atual:
        return
    ini, _, palavras = atual
    pop = 1 + 0.16 * (1 - suave((t - ini) / 0.1))
    tam = 88
    esp = larg(ctx, " ", tam, TITULO)
    ws = [larg(ctx, p, tam, TITULO) for p in palavras]
    total = sum(ws) + esp * (len(ws) - 1)
    if total > 840:
        f = 840 / total
        tam, ws, esp, total = tam * f, [w * f for w in ws], esp * f, 840
    ctx.save()
    ctx.translate(W / 2, y)
    ctx.scale(pop, pop)
    xx = -total / 2
    for p, w in zip(palavras, ws):
        limpa = p.strip(".,:;!?…\"'").lower()
        c = destaques.get(limpa, "branco")
        texto(ctx, p, xx, 0, tam, c, familia=TITULO, contorno=16)
        xx += w + esp
    ctx.restore()


# ------------------------------------------------------------------ telas de dados

def grafico_eras(ctx, ret, serie, total, eras, g_atual, titulo, rotulo_y, a=1.0, faixa_ref=None, final=None):
    """Gráfico grande da série por geração com faixas coloridas por 'era' (rótulos horizontais no topo).

    faixa_ref=(min, max, rótulo): faixa de referência horizontal (ex.: futebol profissional).
    final: texto grande na ponta da curva quando ela chega ao fim."""
    x, y, w, h = ret
    x0, y0, ww, hh = x + 100, y + 220, w - 160, h - 330
    texto(ctx, titulo, x + w / 2, y + 120, 44, "texto", a, familia=TITULO, alinha="c")
    n = max(2, min(int(g_atual), len(serie)))
    for g0, g1, nome, c in eras:
        if g0 > n:
            continue
        xa = x0 + g0 / total * ww
        xb = x0 + min(g1, n) / total * ww
        cor(ctx, c, 0.2 * a)
        ctx.rectangle(xa, y0, max(xb - xa, 3), hh)
        ctx.fill()
        cor(ctx, c, 0.9 * a)
        ctx.rectangle(xa, y0 - 8, max(xb - xa, 3), 5)
        ctx.fill()
        if nome:
            texto(ctx, nome, (xa + xb) / 2, y0 - 22, 22, c, a, familia=MONO_B, alinha="c")
    s_ = np.asarray(serie, float)
    lo = 0.5 if s_.min() >= 0.45 else 0.0       # eixo se adapta: 50-100% (gols) ou 0-100% (aprendizado)
    hi = 1.0 if s_.max() > 0.6 else (0.6 if s_.max() > 0.3 else 0.4)
    yv = lambda v: y0 + hh - (np.clip(v, lo, hi) - lo) / (hi - lo) * hh
    if faixa_ref:
        a0, a1, rot = faixa_ref
        cor(ctx, "verde", 0.16 * a)
        ctx.rectangle(x0, yv(a1), ww, yv(a0) - yv(a1))
        ctx.fill()
        texto(ctx, rot, x0 + 14, yv(a1) - 10, 22, "verde", a, familia=MONO_B)
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        cor(ctx, "ciano2", 0.4 * a)
        ctx.rectangle(x0, yv(v), ww, 1)
        ctx.fill()
        texto(ctx, f"{v * 100:.0f}%", x0 - 12, yv(v) + 8, 22, "sutil", a, familia=MONO_B, alinha="d")
    xs = x0 + np.arange(n) / total * ww
    sm = np.convolve(np.pad(np.asarray(serie[:n], float), (3, 3), mode="edge"), np.ones(7) / 7, "valid")
    ys = yv(sm)
    ctx.move_to(xs[0], ys[0])
    for u, v in zip(xs[1:], ys[1:]):
        ctx.line_to(u, v)
    cor(ctx, "ciano", 0.28 * a)
    ctx.set_line_width(14)
    ctx.stroke_preserve()
    cor(ctx, "texto", a)
    ctx.set_line_width(5)
    ctx.stroke()
    brilho(ctx, xs[-1], ys[-1], 26, "branco", 0.9 * a)
    texto(ctx, rotulo_y, x0, y + h - 60, 22, "sutil", a, familia=MONO_B)
    texto(ctx, f"GERAÇÃO {n}", x0 + ww, y + h - 60, 22, "sutil", a, familia=MONO_B, alinha="d")
    if final and n >= len(serie) - 1:
        fx, fy = min(xs[-1], x0 + ww - 10), ys[-1] - 60
        wc = larg(ctx, final, 64, TITULO) + 40
        chanfro(ctx, fx - wc, fy - 62, wc, 88, 14)
        cor(ctx, (0.015, 0.025, 0.05), 0.92 * a)
        ctx.fill_preserve()
        _neon(ctx, "verde", a, 2)
        texto(ctx, final, fx - 20, fy, 64, "verde", a, familia=TITULO, alinha="d")


def barras(ctx, ret, itens, titulo, sub, progresso, destaque=None, atual=None, cor_destaque="vermelho", a=1.0,
           rotulo_destaque="◀ MELHOR"):
    """Barras horizontais (animam uma vez). itens: [(rotulo, valor 0-1, cor)]."""
    x, y, w, h = ret
    texto(ctx, titulo, x + w / 2, y + 120, 48, "texto", a, familia=TITULO, alinha="c")
    texto(ctx, sub, x + w / 2, y + 166, 26, "texto", 0.7 * a, familia=MONO_B, alinha="c")
    n = len(itens)
    alt = min(150 if n <= 3 else 72, (h - 260) / max(n, 1))
    fs = 30 if n > 3 else 40
    bx = x + (250 if n > 3 else 330)
    bw = 560 if n > 3 else 480
    topo = y + 210 + max(0, (h - 260 - alt * n) / 2 - 40)    # poucas barras: centraliza no painel
    for k, it in enumerate(itens):
        rot, v, c = it[:3]
        txt = it[3] if len(it) > 3 else None   # texto do valor (ex.: segundos); senão, a porcentagem
        yy = topo + k * alt
        p = suave(progresso * 1.5 - k * 0.07)
        dest, at = destaque == k, atual == k
        cc = cor_destaque if dest else ("texto" if at else c)
        texto(ctx, rot, x + 40, yy + alt * 0.62, fs - 2, cc if (dest or at) else "texto", a, familia=MONO_B)
        cor(ctx, "ciano2", 0.2 * a)
        ctx.rectangle(bx, yy + 10, bw, alt - 22)
        ctx.fill()
        cor(ctx, cc, (1.0 if (dest or at) else 0.55) * a)
        ctx.rectangle(bx, yy + 10, bw * v * p, alt - 22)
        ctx.fill()
        if dest:
            brilho(ctx, bx + bw * v * p, yy + alt / 2, 50, cc, 0.7 * a)
        texto(ctx, txt if (txt and p > 0.95) else ("" if txt else f"{v * p * 100:.0f}%"), bx + bw * v * p + 14, yy + alt * 0.66, fs + 6, cc if (dest or at) else "texto",
              a, familia=MONO_B)
        if dest:
            texto(ctx, rotulo_destaque, bx + bw * v * p + 110, yy + alt * 0.66, 30, cc, a, familia=MONO_B)
        if at:
            texto(ctx, "◀ ATUAL", bx + bw * v * p + 110, yy + alt * 0.66, 24, "texto", a, familia=MONO_B)


def tela_final(ctx, ret, t_local, pergunta, opcoes, a=1.0):
    """Chamada final: pergunta + dois times (gera comentário de torcida)."""
    x, y, w, h = ret
    k = suave(t_local / 0.4)
    tam = 64 if larg(ctx, pergunta, 64, TITULO) < w - 80 else 64 * (w - 80) / larg(ctx, pergunta, 64, TITULO)
    texto(ctx, pergunta, x + w / 2, y + 150, tam, "texto", k * a, familia=TITULO, alinha="c")
    for j, (nome, c) in enumerate(opcoes):
        yy = y + 210 + j * 175
        pulso = 1 + 0.03 * math.sin(t_local * 6 + j * 2)
        bw, bh = 760 * pulso, 150
        bx = x + w / 2 - bw / 2
        chanfro(ctx, bx, yy, bw, bh, 30)
        cor(ctx, (0.02, 0.03, 0.05), 0.92 * k)
        ctx.fill_preserve()
        _neon(ctx, c, k * a, 3)
        texto(ctx, "AB"[j], bx + 50, yy + 102, 80, c, k * a, familia=MONO_B)
        tn = 58 if larg(ctx, nome, 58, TITULO) < bw - 190 else 58 * (bw - 190) / larg(ctx, nome, 58, TITULO)
        texto(ctx, nome, bx + 150, yy + 96, tn, "texto", k * a, familia=TITULO)
    texto(ctx, "COMENTA  ↓", x + w / 2, y + 600, 30, "ciano", k * a * (0.5 + 0.5 * math.sin(t_local * 5)),
          familia=MONO_B, alinha="c")


def rodape(ctx, s, a=1.0):
    cor(ctx, "ciano", 0.35 * a)
    ctx.rectangle(30, 1520, 1020, 1)
    ctx.fill()
    tam = 20
    while larg(ctx, s, tam, MONO) > 1020 and tam > 11:   # o rodapé sempre cabe na largura útil
        tam -= 1
    texto(ctx, s, 30, 1556, tam, "sutil", a, familia=MONO)
