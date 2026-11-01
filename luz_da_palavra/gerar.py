"""Luz da Palavra: vídeo vertical (1080x1920) com imagem de fundo (Replicate), narração (Gemini TTS) e legenda dourada.

Uso:
    python luz_da_palavra/gerar.py luz_da_palavra/roteiros/ep01_fogo.json            # vídeo completo
    python luz_da_palavra/gerar.py <roteiro> --so-texto                              # mostra o texto e o tempo previsto
    python luz_da_palavra/gerar.py <roteiro> --sem-imagens                           # rascunho com fundo provisório

Chaves: variáveis REPLICATE_API_TOKEN e GEMINI_API_KEY, ou o arquivo .cache/luz.env (fora do git) com
    REPLICATE_API_TOKEN=...
    GEMINI_API_KEY=...
Tudo que custa (imagens e voz) fica em cache em .cache/luz/<slug>/; rodar de novo não gasta nada.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(AQUI, "fontes")
W, H, FPS, SR = 1080, 1920, 30, 48000
OURO = (246, 196, 84)
CREME = (238, 232, 220)

VOZ = "Charon"
MODELO_TTS = "gemini-3.8-flash-tts"
MODELO_IMG = "black-forest-labs/flux-1.1-pro"
ESTILO_VOZ = (
    "Voice: Charon. You are a Brazilian (pt-BR) Christian storyteller revealing a hidden detail of the Bible to one "
    "friend, close to the microphone. Warm, deep, reverent and gripping, like someone who just discovered something "
    "that gave them chills and can't wait to share it. Not a preacher shouting, not a movie trailer. "
    "Open with urgency and intrigue, as if stopping the listener mid-scroll. Every few seconds create a little "
    "suspense: slow down and lower the voice before each reveal, hold the silence, then say the reveal clearly. "
    "When the text says 'Mas presta atenção' or 'vai te arrepiar', lean in and almost whisper with wonder. "
    "At the end, become tender and hopeful, full of faith. Natural Brazilian Portuguese, never robotic. "
    "Pace: brisk and clear, about 2.8 words per second, with real pauses before reveals."
)


# ---------------------------------------------------------------- chaves
def carrega_chaves():
    arq = os.path.join(RAIZ, ".cache", "luz.env")
    if os.path.exists(arq):
        for linha in open(arq, encoding="utf-8"):
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.strip().split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# ---------------------------------------------------------------- texto
def limpa(fala):
    return fala.replace("*", "")


def texto_tts(cenas):
    partes = []
    for c in cenas:
        t = limpa(c["fala"]).replace("…", "… <long pause>")
        partes.append(t)
    return "\n<short pause>\n".join(partes)


def palavras(fala):
    """[(palavra, destaque)] respeitando *marcas* (podem cobrir mais de uma palavra)."""
    out, dentro = [], False
    for tok in fala.split():
        ini = tok.startswith("*")
        if ini:
            dentro = True
        fim = tok.rstrip(".,:;!?…").endswith("*")
        out.append((tok.replace("*", ""), dentro))
        if fim:
            dentro = False
    return out


# ---------------------------------------------------------------- imagens (Replicate)
def _http_json(url, corpo=None, token=None, metodo=None, timeout=120):
    cab = {"Content-Type": "application/json"}
    if token:
        cab["Authorization"] = "Bearer " + token
        cab["Prefer"] = "wait"
    req = urllib.request.Request(url, json.dumps(corpo).encode() if corpo is not None else None, cab, method=metodo)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def gera_imagem(prompt, destino, semente):
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("falta REPLICATE_API_TOKEN (.cache/luz.env)")
    entrada = {"prompt": prompt + ", ultra detailed, photorealistic, 8k, film grain",
               "aspect_ratio": "9:16", "output_format": "png", "seed": semente, "safety_tolerance": 2}
    p = _http_json(f"https://api.replicate.com/v1/models/{MODELO_IMG}/predictions", {"input": entrada}, token,
                   timeout=180)
    while p.get("status") not in ("succeeded", "failed", "canceled"):
        time.sleep(2)
        p = _http_json(p["urls"]["get"], token=token)
    if p["status"] != "succeeded":
        raise RuntimeError(f"Replicate falhou: {p.get('error')}")
    url = p["output"][0] if isinstance(p["output"], list) else p["output"]
    with urllib.request.urlopen(url, timeout=120) as r:
        Image.open(io.BytesIO(r.read())).convert("RGB").save(destino)


def fundo_provisorio(i, destino):
    """Céu procedural só para rascunho (sem Replicate). Marcado como provisório no vídeo."""
    rng = np.random.default_rng(i + 7)
    h, w = 1920 // 4, 1080 // 4
    y = np.linspace(0, 1, h)[:, None, None]
    topo = np.array([[20, 40, 60], [40, 30, 60], [30, 50, 70], [60, 45, 30]][i % 4], np.float32)
    meio = np.array([230, 150, 70], np.float32)
    base = np.array([8, 10, 16], np.float32)
    img = np.where(y < 0.55, topo + (meio - topo) * (np.minimum(y, .55) / 0.55) ** 2,
                   meio + (base - meio) * (np.clip(y - 0.55, 0, 1) / 0.45) ** 0.5)
    ruido = np.zeros((h, w), np.float32)
    for esc in (4, 8, 16, 32):
        r = rng.random((h // esc + 2, w // esc + 2)).astype(np.float32)
        ruido += np.array(Image.fromarray((r * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255 / esc
    img = img * (0.75 + 0.5 * ruido[..., None])
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((1080, 1920), Image.BICUBIC) \
        .filter(ImageFilter.GaussianBlur(3)).save(destino)


def imagens(rot, pasta, provisorio):
    arqs = []
    for i, prompt in enumerate(rot["imagens"]):
        h = hashlib.sha1((MODELO_IMG + prompt).encode()).hexdigest()[:8]
        arq = os.path.join(pasta, f"img{i}_{h}.png")
        if not os.path.exists(arq):
            if provisorio:
                arq = os.path.join(pasta, f"prov{i}.png")
                if not os.path.exists(arq):
                    fundo_provisorio(i, arq)
            else:
                print(f"[img] gerando {i + 1}/{len(rot['imagens'])} no Replicate…", flush=True)
                gera_imagem(prompt, arq, 1000 + i)
        arqs.append(arq)
    return arqs


# ---------------------------------------------------------------- voz (Gemini TTS)
def _le_wav(dados):
    with wave.open(io.BytesIO(dados)) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    return x, sr


def narracao(rot, pasta):
    texto = texto_tts(rot["cenas"])
    chave = hashlib.sha1((VOZ + MODELO_TTS + ESTILO_VOZ + texto).encode()).hexdigest()[:10]
    arq = os.path.join(pasta, f"voz_{chave}.npy")
    if os.path.exists(arq):
        print("[voz] cache (nenhuma requisição)")
        return np.load(arq)
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("falta GEMINI_API_KEY (.cache/luz.env)")
    print(f"[voz] 1 requisição: {VOZ} · {MODELO_TTS}", flush=True)
    corpo = {"contents": [{"parts": [{"text": texto, "speechMetadata": {"style": ESTILO_VOZ}}]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOZ}}}}}
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO_TTS}:generateContent?key="
           + os.environ["GEMINI_API_KEY"])
    try:
        resp = _http_json(url, corpo, timeout=300)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"TTS falhou ({e.code}): {e.read().decode('utf-8', 'ignore')[:300]}")
    dados = base64.b64decode(resp["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
    if dados[:4] == b"RIFF":
        x, sr = _le_wav(dados)
    else:
        x, sr = np.frombuffer(dados, np.int16).astype(np.float32) / 32768, 24000
    t = np.arange(int(len(x) * SR / sr)) * sr / SR
    x = np.interp(t, np.arange(len(x)), x).astype(np.float32)
    # apara silêncio das pontas
    env = np.convolve(np.abs(x), np.ones(480) / 480, "same")
    idx = np.where(env > 0.01)[0]
    x = x[max(0, idx[0] - 2400): idx[-1] + 4800]
    x = x / (np.abs(x).max() + 1e-9) * 0.89
    np.save(arq, x)
    return x


def ajusta_ritmo(x, teto=0.3, fator=1.08):
    """Ritmo local (sem nova requisição): encurta silêncios longos e acelera sem mudar o tom."""
    partes, ini = [], 0
    for a, b in silencios(x, minimo=teto):
        fica = teto if b - a < 1.0 else teto * 2      # pausa de suspense (antes de revelação) fica mais longa
        if b - a <= fica:
            continue
        partes.append(x[ini:int((a + fica / 2) * SR)])
        ini = int((b - fica / 2) * SR)
    partes.append(x[ini:])
    y = np.concatenate(partes).astype(np.float32)
    if abs(fator - 1) < 1e-3:
        return y
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", f"atempo={fator}", "-f", "f32le", "-"], input=y.tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32).copy()


def silencios(x, minimo=0.18, limiar=0.015):
    h = SR // 100
    n = len(x) // h
    sil = np.abs(x[: n * h]).reshape(n, h).max(1) < limiar
    out, i = [], 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            if (j - i) * 0.01 >= minimo and i > 0 and j < n:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def tempos_cenas(x, cenas):
    """Fronteiras das cenas nos silêncios da narração (o TTS recebe uma pausa entre cenas)."""
    dur = len(x) / SR
    sil = silencios(x)
    pesos = [len(limpa(c["fala"])) + 12 * c["fala"].count("…") for c in cenas]
    ini, limites = 0.0, []
    for k in range(len(cenas) - 1):
        resto = sum(pesos[k:])
        esperado = ini + (dur - ini) * pesos[k] / resto
        cand = [s for s in sil if s[0] > ini + 0.6]
        if cand:
            melhor = min(cand, key=lambda s: abs((s[0] + s[1]) / 2 - esperado) - 0.8 * (s[1] - s[0]))
            corte = (melhor[0] + melhor[1]) / 2
            sil = [s for s in sil if s[0] > melhor[1]]
        else:
            corte = esperado
        limites.append(corte)
        ini = corte
    bordas = [0.0] + limites + [dur]
    # dentro de cada cena: início e fim da fala real (sem o silêncio das pontas)
    out = []
    for a, b in zip(bordas[:-1], bordas[1:]):
        seg = np.abs(x[int(a * SR): int(b * SR)])
        h = SR // 100
        env = seg[: len(seg) // h * h].reshape(-1, h).max(1) if len(seg) >= h else np.zeros(1)
        voz = np.where(env > 0.03)[0]
        fa = a + (voz[0] * 0.01 if len(voz) else 0)
        fb = a + ((voz[-1] + 1) * 0.01 if len(voz) else b - a)
        out.append((a, b, fa, fb))
    return out


# ---------------------------------------------------------------- trilha e efeitos
def pad(dur, semente=3):
    t = np.arange(int(dur * SR)) / SR
    acordes = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66], [164.81, 207.65, 246.94]]
    x = np.zeros_like(t)
    passo = 6.0
    for k, ac in enumerate(acordes * int(dur // (passo * 4) + 2)):
        a = k * passo
        if a > dur:
            break
        m = (t >= a - 1) & (t < a + passo + 1.5)
        tt = t[m] - a
        env = np.clip((tt + 1) / 1.5, 0, 1) * np.clip((passo + 1.5 - tt) / 1.5, 0, 1)
        for f in ac:
            for d in (-0.6, 0.6):
                x[m] += np.sin(2 * np.pi * (f + d) * t[m]) * env * 0.06
                x[m] += np.sin(2 * np.pi * (f / 2) * t[m]) * env * 0.03
    lfo = 0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * t)
    return (x * lfo).astype(np.float32)


def swell(dur=1.2, semente=0):
    rng = np.random.default_rng(semente)
    n = int(dur * SR)
    r = rng.standard_normal(n).astype(np.float32)
    r = np.convolve(r, np.ones(40) / 40, "same")
    env = np.linspace(0, 1, n) ** 3
    return r * env * 0.6


def impacto():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * (55 + 30 * np.exp(-t * 8)) * t) * np.exp(-t * 2.5) * 0.9).astype(np.float32)


def mixa(voz, tempos, cenas, dur):
    n = int(dur * SR)
    mus = pad(dur)[:n]
    sfx = np.zeros(n, np.float32)

    def poe(som, t0, ganho):
        i = int(max(0, t0) * SR)
        j = min(n, i + len(som))
        sfx[i:j] += som[: j - i] * ganho

    poe(impacto(), 0.0, 0.35)
    for c, (a, b, fa, fb) in zip(cenas, tempos):
        if c.get("card"):
            poe(swell(), a - 1.2 + 0.25, 0.10)
            poe(impacto(), a + 0.25, 0.22)
    v = np.zeros(n, np.float32)
    v[: len(voz)] = voz[:n]
    # abaixa música/efeitos enquanto a voz fala
    env = np.convolve(np.abs(v), np.ones(4800) / 4800, "same")
    duck = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    mix = v + (mus * 0.35 + np.clip(sfx, -0.2, 0.2)) * duck
    fade = int(1.0 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return (mix / max(1.0, np.abs(mix).max() / 0.9)).astype(np.float32)


# ---------------------------------------------------------------- visual
def fonte(nome, tam):
    return ImageFont.truetype(os.path.join(FONTES, nome), tam)


def texto_brilho(txt, f, cor, brilho=None, sombra=True, espaco=0):
    """Camada RGBA com texto + sombra suave (+ brilho dourado opcional)."""
    bb = f.getbbox(txt)
    asc, desc = f.getmetrics()
    bb = (bb[0], 0, bb[2], asc + desc)             # altura fixa: todas as palavras na mesma linha de base
    tw, th = bb[2] - bb[0] + espaco * len(txt), bb[3] - bb[1]
    m = 40
    img = Image.new("RGBA", (tw + 2 * m, th + 2 * m), (0, 0, 0, 0))
    mask = Image.new("L", img.size, 0)
    dm = ImageDraw.Draw(mask)
    if espaco:
        xx = m
        for ch in txt:
            dm.text((xx, m - bb[1]), ch, font=f, fill=255)
            xx += f.getlength(ch) + espaco
    else:
        dm.text((m - bb[0], m - bb[1]), txt, font=f, fill=255)
    if sombra:
        s = mask.filter(ImageFilter.GaussianBlur(10)).point(lambda p: int(p * 0.85))
        img.paste((0, 0, 0, 255), (0, 4), s)
    if brilho:
        g = mask.filter(ImageFilter.GaussianBlur(14)).point(lambda p: int(p * 0.55))
        camada = Image.new("RGBA", img.size, brilho + (0,))
        camada.putalpha(g)
        img = Image.alpha_composite(img, camada)
    sol = Image.new("RGBA", img.size, cor + (0,))
    sol.putalpha(mask)
    return Image.alpha_composite(img, sol), m


def com_alfa(img, a):
    if a >= 0.999:
        return img
    r = img.copy()
    r.putalpha(img.getchannel("A").point(lambda p: int(p * a)))
    return r


class Cena:
    def __init__(self, c, tempos):
        self.c = c
        self.a, self.b, self.fa, self.fb = tempos
        f = fonte("Cormorant-SemiBold.ttf", 78)
        fi = fonte("Cormorant-SemiBoldItalic.ttf", 78)
        pal = palavras(c["fala"])
        # quebra em linhas de até 860 px
        linhas, atual, larg = [], [], 0
        esp = f.getlength(" ")
        for w_, d in pal:
            lw = (fi if d else f).getlength(w_)
            if atual and larg + esp + lw > 860:
                linhas.append(atual)
                atual, larg = [], 0
            atual.append((w_, d, lw))
            larg += (esp if len(atual) > 1 else 0) + lw
        if atual:
            linhas.append(atual)
        total = sum(len(limpa(w_)) + 1 for w_, _ in pal)
        self.pal, acum = [], 0
        y0 = 1040 - (len(linhas) * 96) // 2
        for li, ln in enumerate(linhas):
            lw = sum(p[2] for p in ln) + esp * (len(ln) - 1)
            x = (W - lw) / 2
            for w_, d, pw in ln:
                img, m = texto_brilho(w_, fi if d else f, OURO if d else CREME, brilho=(255, 170, 40) if d else None)
                t = self.fa + (self.fb - self.fa) * acum / total
                acum += len(w_) + 1
                self.pal.append((img, int(x - m), int(y0 + li * 96 - m), t, d))
                x += pw + esp
        self.card = None
        if c.get("card"):
            self.card, mc = texto_brilho(c["card"], fonte("Cinzel-Bold.ttf", 96), OURO, brilho=(255, 150, 30))
            self.card_m = mc
        self.cta = desenha_cta(c["cta"]) if c.get("cta") else None

    def desenha(self, quadro, t):
        if self.card is not None:
            k = np.clip((t - self.a) / 0.35, 0, 1)
            esc = 1.35 - 0.35 * (1 - (1 - k) ** 3)
            a = k * np.clip((self.b - t) / 0.3, 0, 1)
            im = self.card.resize((int(self.card.width * esc), int(self.card.height * esc)), Image.BILINEAR)
            quadro.alpha_composite(com_alfa(im, a), ((W - im.width) // 2, 760 - im.height // 2))
        for img, x, y, t0, d in self.pal:
            k = np.clip((t - t0 + 0.08) / 0.18, 0, 1)
            if k <= 0:
                continue
            fim = np.clip((self.b - t) / 0.15, 0, 1) if self.b < 1e8 else 1
            dy = int(14 * (1 - k))
            quadro.alpha_composite(com_alfa(img, k * fim), (x, y + dy))
    def desenha_cta(self, quadro, t):
        if self.cta is not None and t >= self.a:
            k = np.clip((t - self.a) / 0.4, 0, 1)
            pulso = 1 + 0.04 * np.sin((t - self.a) * 6)
            im = self.cta.resize((int(self.cta.width * pulso), int(self.cta.height * pulso)), Image.BILINEAR)
            quadro.alpha_composite(com_alfa(im, k), ((W - im.width) // 2, 1300 - im.height // 2))


def desenha_cta(txt):
    f = fonte("Cinzel-Bold.ttf", 44)
    tw = int(f.getlength(txt))
    w, h = tw + 150, 104
    img = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    g = Image.new("L", img.size, 0)
    ImageDraw.Draw(g).rounded_rectangle((30, 30, 30 + w, 30 + h), 52, fill=200)
    g = g.filter(ImageFilter.GaussianBlur(16))
    brilho = Image.new("RGBA", img.size, (255, 170, 40, 0))
    brilho.putalpha(g)
    img = Image.alpha_composite(img, brilho)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((30, 30, 30 + w, 30 + h), 52, fill=(14, 12, 10, 235), outline=OURO, width=4)
    # ícone de balão
    bx, by = 30 + 48, 30 + h // 2
    d.rounded_rectangle((bx - 22, by - 18, bx + 22, by + 14), 8, fill=OURO)
    d.polygon([(bx - 10, by + 12), (bx - 16, by + 26), (bx + 2, by + 12)], fill=OURO)
    for k in (-10, 0, 10):
        d.ellipse((bx + k - 3, by - 5, bx + k + 3, by + 1), fill=(14, 12, 10))
    d.text((30 + 96, 30 + h // 2), txt, font=f, fill=OURO, anchor="lm")
    return img


def cabecalho(ref):
    f = fonte("Cinzel-Bold.ttf", 40)
    img, m = texto_brilho(ref, f, OURO, brilho=(255, 160, 40), espaco=6)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = (W - img.width) // 2
    camada.alpha_composite(img, (x, 230 - img.height // 2))
    d = ImageDraw.Draw(camada)
    for lado in (-1, 1):
        cx = W // 2 + lado * (img.width // 2 - m + 30)
        d.line([(cx, 232), (cx + lado * 90, 232)], fill=OURO + (150,), width=2)
    return camada


def titulo_camadas(linhas):
    out, y = [], 470
    for i, ln in enumerate(linhas):
        ultimo = i == len(linhas) - 1
        f = fonte("Cinzel-Bold.ttf", 104 if ultimo else 86)
        img, m = texto_brilho(ln, f, OURO if ultimo else (255, 255, 255), brilho=(255, 150, 30) if ultimo else None)
        out.append((img, y - m))
        y += 116 if not ultimo else 130
    return out


def sobreposicao():
    """Escurecimento em cima/embaixo + vinheta, para a letra sempre ler bem."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2
    a = np.clip(v, 0, 1) * 150
    meio = np.exp(-((yy - 1040) / 300) ** 2) * 90            # faixa mais escura atrás da legenda
    topo = np.clip((420 - yy) / 420, 0, 1) * 110
    alfa = np.clip(a + meio + topo, 0, 230).astype(np.uint8)
    img = Image.new("RGBA", (W, H), (4, 4, 8, 0))
    img.putalpha(Image.fromarray(alfa))
    return img


class Fundo:
    def __init__(self, arqs, janelas, provisorio):
        self.imgs = []
        for arq in arqs:
            im = Image.open(arq).convert("RGB")
            esc = max(W * 1.18 / im.width, H * 1.18 / im.height)
            self.imgs.append(im.resize((int(im.width * esc), int(im.height * esc)), Image.LANCZOS))
        self.jan = janelas      # [(i_img, t0, t1)]
        self.prov = provisorio

    def _quadro(self, i, t, t0, t1):
        im = self.imgs[i]
        k = np.clip((t - t0) / max(0.1, t1 - t0), 0, 1.2)
        zoom = 1.0 + 0.10 * k if i % 2 == 0 else 1.10 - 0.10 * k
        cw, ch = W * 1.18 / zoom * im.width / (W * 1.18), H * 1.18 / zoom * im.height / (H * 1.18)
        cw, ch = im.width / 1.18 / zoom * 1.0, im.height / 1.18 / zoom
        dx = (im.width - cw) * (0.5 + 0.35 * (k - 0.5) * (1 if i % 3 else -1))
        dy = (im.height - ch) * (0.5 + 0.2 * (k - 0.5))
        return im.resize((W, H), Image.BILINEAR, box=(dx, dy, dx + cw, dy + ch))

    def quadro(self, t):
        atual = [j for j in self.jan if j[1] <= t] or [self.jan[0]]
        i, t0, t1 = atual[-1]
        q = self._quadro(i, t, t0, t1)
        idx = self.jan.index(atual[-1])
        if idx > 0 and t - t0 < 0.5:
            pi, p0, p1 = self.jan[idx - 1]
            q = Image.blend(self._quadro(pi, t, p0, p1), q, (t - t0) / 0.5)
        return q.convert("RGBA")


def particulas(n=45, semente=1):
    rng = np.random.default_rng(semente)
    return [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.5, 4.5), rng.uniform(12, 40), rng.uniform(0, 6.28))
            for _ in range(n)]


def renderiza(rot, arqs, voz, tempos, saida, provisorio):
    cenas = rot["cenas"]
    dur = len(voz) / SR + 1.2
    tempos = [list(tp) for tp in tempos]
    tempos[-1][1] = 1e9
    objs = [Cena(c, tp) for c, tp in zip(cenas, tempos)]
    jan, ult = [], None
    for c, tp in zip(cenas, tempos):
        if c["img"] != ult:
            jan.append([c["img"], tp[0], None])
            ult = c["img"]
    for k in range(len(jan)):
        jan[k][2] = jan[k + 1][1] if k + 1 < len(jan) else dur
    fundo = Fundo(arqs, [tuple(j) for j in jan], provisorio)
    sob, cab = sobreposicao(), cabecalho(rot["ref"])
    tit = titulo_camadas(rot["titulo"])
    fim_titulo = tempos[1][1] if len(tempos) > 1 else tempos[0][1]
    parts = particulas()
    aviso = None
    if provisorio:
        aviso, _ = texto_brilho("RASCUNHO · fundo provisório", fonte("Cormorant-SemiBold.ttf", 36), (255, 120, 120))

    audio = mixa(voz, tempos, cenas, dur)
    arq_a = saida + ".wav"
    with wave.open(arq_a, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())

    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", arq_a, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", saida]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nq = int(dur * FPS)
    for q in range(nq):
        t = q / FPS
        img = fundo.quadro(t)
        img.alpha_composite(sob)
        d = ImageDraw.Draw(img)
        for (x, y, r, vel, fase) in parts:
            yy = (y - vel * t) % H
            xx = x + 14 * np.sin(t * 0.7 + fase)
            a = int(110 + 90 * np.sin(t * 2 + fase))
            d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 210, 140, max(0, a)))
        img.alpha_composite(cab)
        if t < fim_titulo:
            for k, (im, y) in enumerate(tit):
                ka = np.clip((t - 0.12 * k) / 0.3, 0, 1) * np.clip((fim_titulo - t) / 0.3, 0, 1)
                esc = 1.25 - 0.25 * (1 - (1 - np.clip((t - 0.12 * k) / 0.3, 0, 1)) ** 3)
                im2 = im.resize((int(im.width * esc), int(im.height * esc)), Image.BILINEAR) if esc > 1.001 else im
                img.alpha_composite(com_alfa(im2, ka), ((W - im2.width) // 2, y - (im2.height - im.height) // 2))
        for o in objs:
            if o.a - 0.05 <= t < o.b:
                o.desenha(img, t)
            o.desenha_cta(img, t)                    # o botão "Comente" fica até o fim
        if aviso is not None:
            img.alpha_composite(aviso, ((W - aviso.width) // 2, 1560))
        proc.stdin.write(img.convert("RGB").tobytes())
        if q % 150 == 0:
            print(f"  quadro {q}/{nq}", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(arq_a)


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("--so-texto", action="store_true")
    ap.add_argument("--sem-imagens", action="store_true", help="rascunho com fundo provisório (não chama Replicate)")
    a = ap.parse_args()
    carrega_chaves()
    rot = json.load(open(a.roteiro, encoding="utf-8"))
    n = sum(len(limpa(c["fala"]).split()) for c in rot["cenas"])
    if a.so_texto:
        print(texto_tts(rot["cenas"]))
        print(f"\n{n} palavras ≈ {n / 2.8:.0f} s")
        return
    pasta = os.path.join(RAIZ, ".cache", "luz", rot["slug"])
    os.makedirs(pasta, exist_ok=True)
    arqs = imagens(rot, pasta, a.sem_imagens)
    voz = ajusta_ritmo(narracao(rot, pasta), rot.get("teto_pausa", 0.3), rot.get("velocidade", 1.08))
    tempos = tempos_cenas(voz, rot["cenas"])
    for c, (x, y, fa, fb) in zip(rot["cenas"], tempos):
        print(f"  {x:5.2f}-{y:5.2f}  {limpa(c['fala'])}")
    os.makedirs(os.path.join(RAIZ, "saida", "luz"), exist_ok=True)
    nome = rot["slug"] + ("_rascunho" if a.sem_imagens else "")
    saida = os.path.join(RAIZ, "saida", "luz", nome + ".mp4")
    renderiza(rot, arqs, voz, tempos, saida, a.sem_imagens)
    with open(os.path.join(RAIZ, "saida", "luz", rot["slug"] + "_legenda.txt"), "w", encoding="utf-8") as f:
        f.write(rot["legenda"] + "\n")
    print(f"[ok] {saida}  ({len(voz) / SR + 1.2:.1f} s)")


if __name__ == "__main__":
    main()
