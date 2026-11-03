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
import analistas
import conferir
import temas
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(AQUI, "fontes")
W, H, FPS, SR = 1080, 1920, 30, 48000
OURO = (255, 208, 92)
CREME = (238, 232, 220)
# Área livre da interface do TikTok (1080x1920): nada de texto embaixo da coluna de ícones à direita
# (curtir/comentar/salvar/compartilhar/perfil) nem na faixa de baixo (nome, legenda, música). Os analistas cobram.
LARG_TEXTO = 740            # largura máxima de qualquer texto centralizado: x 170..910 (folga dos ícones)
Y_CARTAO = 650             # cartão de re-gancho: acima da altura dos ícones (que começam por volta de y 760)
Y_TITULO = 380             # título de abertura (3 linhas) termina antes de y 760
Y_CONTAGEM = 1415           # contagem regressiva embaixo, acima da faixa da legenda do TikTok
# Trilha de fundo (dono, 02/nov/2026): a música enviada pelo dono, a partir de 3:55 (o arquivo já começa ali), BEM BAIXA
# para não atrapalhar a narração. Nível medido contra a voz: -15 dB nas pausas e ~-21 dB debaixo da fala (abaixa sozinha; +3 dB pedido pelo dono).
MUSICA = os.path.join(AQUI, "musica", "trilha.m4a")
MUSICA_PAUSA_DB, MUSICA_DUCK_DB = -15.0, -6.0
MUSICA_LOOP = 0.8           # o vídeo toca a música a partir de 0,8 s e funde no começo dela no fim (loop sem pulo)
LAYOUT_EXTRA = {}           # medidas do render para os analistas (ex.: diferença entre o fim e o começo)
LAYOUT = {}                 # caixas reais de cada elemento desenhado (para o analista de zona segura)


def marca(nome, im, x, y):
    """Registra a área visível (alfa forte) de um elemento desenhado em (x, y)."""
    bb = im.getchannel("A").point(lambda p: 255 if p > 90 else 0).getbbox()
    if bb:
        b = [x + bb[0], y + bb[1], x + bb[2], y + bb[3]]
        a = LAYOUT.get(nome)
        LAYOUT[nome] = b if a is None else [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]

# Identidade do canal (dono, nov/2026): voz Achird no Gemini TTS, UMA requisição por vídeo (trava em narracao()).
VOZ = "Achird"
MODELO_TTS = "gemini-3.8-flash-tts"
MODELO_IMG = "black-forest-labs/flux-schnell"
# Estilo visual fixo de TODAS as imagens (dono, nov/2026): fotografia de natureza ULTRA REALISTA (nada de cara de
# ilustração/pintura/3D) que BRILHA na tela: cores intensas, contraste forte, detalhe nítido de 4K (dono, 02/nov: "a pessoa
# precisa ver e a foto brilhar"); além do prompt, `tratamento()` dá a cor de cinema no render. Modelo: flux-schnell (Replicate).
# Nunca cite marcas (revista, câmera, agência): o modelo desenha o logo na foto (aconteceu no ep01 e no ep03).
ESTILO_IMG = (
    "ultra realistic professional landscape photograph, shot on a full-frame camera with a 24mm lens, real natural light, "
    "true-to-life textures, tack-sharp crisp micro-detail, rich vivid saturated colors, strong contrast, deep shadows and "
    "luminous glowing highlights, clear deep-colored sky (not washed out, not hazy), dramatic golden-hour or blue-hour light, "
    "award-winning nature photography, 8k, photorealistic, eye-catching. "
    "Not an illustration, not a painting, not digital art, not 3D render, not CGI, no fantasy, no text, no letters, "
    "no logo, no watermark, no signature, no border"
)
ESTILO_VOZ = (
    "Voice: Achird. Channel 'Luz da Palavra': a warm Brazilian (pt-BR) Christian friend revealing a hidden detail "
    "of the Bible to one person, close to the microphone, at golden hour. Intimate, reverent and full of wonder, "
    "like someone who just noticed something in Scripture that gave them goosebumps and needs to share it now. "
    "Gentle faith and hope; never a shouting preacher, never a movie-trailer voice, never dark, scary or ominous, "
    "never robotic. "
    "First sentence: urgent and intriguing, slightly faster, a voice that makes someone stop scrolling. "
    "Every few seconds build friendly suspense: before each '…' slow down, lower the voice a little, lean in, hold "
    "a real silence, then say the reveal clearly with quiet amazement; teasers like 'Mas presta atenção' sound like "
    "a secret being shared. Short punchy lines land slowly, word by word. "
    "In the personal turn near the end, become tender and compassionate, a smile in the voice, full of hope, like "
    "speaking to someone who is hurting. The call to comment is light and warm, not salesy. The last "
    "sentence is soft and confident, ending in peace. "
    "Natural Brazilian Portuguese, connected sentences, pace about 2.8 words per second with real pauses before reveals."
)


# ---------------------------------------------------------------- chaves
def carrega_chaves():
    arq = os.path.join(RAIZ, ".cache", "luz.env")
    if os.path.exists(arq):
        for linha in open(arq, encoding="utf-8"):
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.strip().split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    # na nuvem o proxy injeta as chaves do Replicate e do Gemini (segredos do ambiente): basta um valor qualquer aqui
    os.environ.setdefault("REPLICATE_API_TOKEN", "injetada-pelo-proxy")
    os.environ.setdefault("GEMINI_API_KEY", "injetada-pelo-proxy")


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
def _http_json(url, corpo=None, token=None, metodo=None, timeout=120, cabecalhos=None):
    cab = {"Content-Type": "application/json", **(cabecalhos or {})}
    if token:
        cab["Authorization"] = "Bearer " + token
        cab["Prefer"] = "wait"
    req = urllib.request.Request(url, json.dumps(corpo).encode() if corpo is not None else None, cab, method=metodo)
    for tentativa in range(6):          # 429 do Replicate = limite de requisições por minuto: espera e tenta de novo
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or "replicate" not in url or tentativa == 5:
                raise
            print(f"  (Replicate pediu calma, aguardando {10 + 5 * tentativa}s)", flush=True)
            time.sleep(10 + 5 * tentativa)


def gera_imagem(prompt, destino, semente):
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("falta REPLICATE_API_TOKEN (.cache/luz.env)")
    entrada = {"prompt": prompt + ". " + ESTILO_IMG, "aspect_ratio": "9:16", "output_format": "png",
               "num_outputs": 1, "go_fast": True, "megapixels": "1", "seed": semente}
    p = _http_json(f"https://api.replicate.com/v1/models/{MODELO_IMG}/predictions", {"input": entrada}, token,
                   timeout=180)
    while p.get("status") not in ("succeeded", "failed", "canceled"):
        time.sleep(2)
        p = _http_json(p["urls"]["get"], token=token)
    if p["status"] != "succeeded":
        raise RuntimeError(f"Replicate falhou: {p.get('error')}")
    url = p["output"][0] if isinstance(p["output"], list) else p["output"]
    with urllib.request.urlopen(url, timeout=120) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    # schnell sai em ~1 MP: amplia com nitidez suave para o vídeo (1080x1920 + zoom) não ficar mole
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    im.save(destino)


def tratamento(im):
    """Cor de cinema 4K (dono, 02/nov/2026: "a foto precisa brilhar, parecer 4K, diferente do que a pessoa vê no feed").
    Aplicado no render (a imagem paga no Replicate fica intacta no cache): realce de detalhe local (clarity), curva em S,
    vibrância (puxa mais as cores apagadas que as já fortes), brilho suave nas luzes (bloom) e nitidez final."""
    x = np.asarray(im.convert("RGB"), np.float32) / 255
    # clarity: detalhe de média escala (textura de pedra, folhas, nuvens) mais marcado
    borrada = np.asarray(im.convert("RGB").filter(ImageFilter.GaussianBlur(28)), np.float32) / 255
    x = np.clip(x + 0.45 * (x - borrada), 0, 1)
    # curva em S suave: pretos mais profundos e luzes mais vivas, sem estourar
    x = x + 0.22 * x * (1 - x) * (2 * x - 1)
    x = np.clip(0.5 + (x - 0.5) * 1.10, 0, 1)
    # vibrância + saturação
    cinza = x.mean(2, keepdims=True)
    sat = (x.max(2, keepdims=True) - x.min(2, keepdims=True))
    x = np.clip(cinza + (x - cinza) * (1.10 + 0.50 * (1 - sat)), 0, 1)
    # bloom: as luzes fortes ganham um halo quente
    luz = np.clip((x.mean(2, keepdims=True) - 0.62) / 0.38, 0, 1) * x
    halo = np.asarray(Image.fromarray((luz * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(22)), np.float32) / 255
    x = 1 - (1 - x) * (1 - 0.35 * halo)
    out = Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))
    return out.filter(ImageFilter.UnsharpMask(1.6, 90, 2))


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
        h = hashlib.sha1((MODELO_IMG + ESTILO_IMG + prompt).encode()).hexdigest()[:8]
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


def narracao(rot, pasta, autoriza_nova=False):
    texto = texto_tts(rot["cenas"])
    estilo = ESTILO_VOZ + (" " + rot["estilo_extra"] if rot.get("estilo_extra") else "")
    chave = hashlib.sha1((VOZ + MODELO_TTS + estilo + texto).encode()).hexdigest()[:10]
    arq = os.path.join(pasta, f"voz_{chave}.npy")
    if rot.get("voz_cache") and os.path.exists(os.path.join(pasta, rot["voz_cache"])):   # episódio antigo (estilo legado)
        arq = os.path.join(pasta, rot["voz_cache"])
    if os.path.exists(arq):
        print(f"[voz] cache (nenhuma requisição) · {VOZ} · {MODELO_TTS}")
        return np.load(arq)
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("falta GEMINI_API_KEY (.cache/luz.env)")
    livro = os.path.join(pasta, "uso_voz.json")
    usos = json.load(open(livro)) if os.path.exists(livro) else []
    if usos and not autoriza_nova:
        raise SystemExit(f"[voz] TRAVA: este vídeo já usou {len(usos)} requisição(ões) de voz ({usos[-1]['voz']}). "
                         "Regra do canal: 1 por vídeo. Só com licença do dono: --autorizo-nova-voz")
    print(f"[voz] 1 requisição: {VOZ} · {MODELO_TTS}", flush=True)
    usos.append({"voz": VOZ, "modelo": MODELO_TTS, "quando": time.strftime("%Y-%m-%d %H:%M"), "chave": chave})
    json.dump(usos, open(livro, "w"), indent=1)
    corpo = {"contents": [{"parts": [{"text": texto, "speechMetadata": {"style": estilo}}]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOZ}}}}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO_TTS}:generateContent"
    try:                                  # chave no cabeçalho (não na URL): compatível com "Network secrets" do ambiente
        resp = _http_json(url, corpo, timeout=300, cabecalhos={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
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
    pesos = [len(limpa(c["fala"])) + c.get("peso_pausa", 12) * c["fala"].count("…") for c in cenas]
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


def cauda(rot):
    """Silêncio depois da última palavra. Com emenda o vídeo acaba colado na fala e recomeça sem respiro."""
    return 0.12 if rot.get("emenda") else 1.2


def le_musica(segundos, arquivo=MUSICA):
    """Música de fundo mono 48 kHz (os primeiros `segundos`)."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", arquivo, "-t", f"{segundos:.2f}", "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True, check=True)
    x = np.frombuffer(p.stdout, np.float32).copy()
    if len(x) < int(segundos * SR):
        raise RuntimeError(f"a música {arquivo} tem menos de {segundos:.0f} s a partir do ponto de início")
    return x


def _rms_db(x):
    return float(20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9)) if len(x) else -120.0


def trilha(dur, voz_rms, emenda):
    """Música baixa: nível relativo à voz; com emenda, o fim funde no início dela (o loop não dá pulo na música)."""
    n = int(dur * SR)
    x = le_musica(dur + MUSICA_LOOP + 0.5)
    lp = int(MUSICA_LOOP * SR)
    m = x[lp: lp + n].copy()
    if emenda:                      # últimos 0,8 s: m(t) -> x(t + 0,8 - dur), que termina em x(0,8) = 1º quadro
        k = np.linspace(0, 1, lp) ** 0.5
        m[-lp:] = m[-lp:] * (1 - k) + x[:lp] * k
    else:
        m[: SR // 2] *= np.linspace(0, 1, SR // 2)
    ganho = 10 ** (MUSICA_PAUSA_DB / 20) * voz_rms / (np.sqrt(np.mean(m ** 2)) + 1e-9)
    return (m * ganho).astype(np.float32)


def mixa(voz, tempos, cenas, dur, emenda=False):
    n = int(dur * SR)
    v = np.zeros(n, np.float32)
    v[: len(voz)] = voz[:n]
    h = SR // 20                                      # janelas de 50 ms
    fr = np.sqrt(np.mean(v[: n // h * h].reshape(-1, h) ** 2, 1))
    falando = fr > 0.03
    voz_rms = float(np.sqrt(np.mean(fr[falando] ** 2))) if falando.any() else 0.1
    com_musica = os.path.exists(MUSICA)
    mus = trilha(dur, voz_rms, emenda) if com_musica else pad(dur)[:n] * 0.35
    sfx = np.zeros(n, np.float32)

    def poe(som, t0, ganho):
        i = int(max(0, t0) * SR)
        j = min(n, i + len(som))
        sfx[i:j] += som[: j - i] * ganho

    poe(impacto(), 0.0, 0.10 if emenda else 0.35)      # com emenda o "boom" do 0 s quase some (não denuncia o loop)
    for c, (a, b, fa, fb) in zip(cenas, tempos):
        if c.get("card"):
            poe(swell(), a - 1.2 + 0.25, 0.10)
            poe(impacto(), a + 0.25, 0.22)
    # abaixa música/efeitos enquanto a voz fala (ataque e soltura suaves, ~0,3 s)
    env = np.convolve(np.abs(v), np.ones(SR // 10) / (SR // 10), "same")
    env = np.convolve(env, np.ones(SR // 4) / (SR // 4), "same")
    duck = 1 - (1 - 10 ** (MUSICA_DUCK_DB / 20)) * np.clip(env / 0.04, 0, 1)
    fundo = mus * duck
    mix = v + fundo + np.clip(sfx, -0.2, 0.2) * duck
    if not emenda:                                   # com emenda: sem fade-out (o loop não pode "terminar")
        fade = SR
        mix[-fade:] *= np.linspace(1, 0, fade)
    pico = float(np.abs(mix).max())
    # medidas para o analista de som: música x voz nos trechos de fala e nas pausas
    fm = np.sqrt(np.mean(fundo[: n // h * h].reshape(-1, h) ** 2, 1))
    pausa = fr < 0.005
    LAYOUT_EXTRA["audio"] = {
        "musica": os.path.relpath(MUSICA, RAIZ) if com_musica else None,
        "musica_sob_voz_db": round(_rms_db(fm[falando]) - _rms_db(fr[falando]), 1) if falando.any() else None,
        "musica_pausa_db": round(_rms_db(fm[pausa]) - 20 * np.log10(voz_rms), 1) if pausa.any() else None,
        "musica_presente_pct": round(100 * float(np.mean(fm > 10 ** (-60 / 20))), 1),
        "pico_antes_norm": round(pico, 3),
    }
    return (mix / max(1.0, pico / 0.9)).astype(np.float32)


# ---------------------------------------------------------------- visual
def fonte(nome, tam):
    return ImageFont.truetype(os.path.join(FONTES, nome), tam)


def fonte_cabe(nome, tam, txt, largura):
    """Maior fonte (até `tam`) em que o texto cabe em `largura` px."""
    while tam > 40 and fonte(nome, tam).getlength(txt) > largura:
        tam -= 4
    return fonte(nome, tam)


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
    if sombra:   # céu muito colorido: halo escuro largo + sombra + contorno fino, para ler em qualquer fundo
        escuro = Image.new("RGBA", img.size, (8, 6, 14, 0))
        halo = mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(22)).point(lambda p: int(p * 0.8))
        escuro.putalpha(halo)
        img = Image.alpha_composite(img, escuro)
        borda = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.2))
        contorno = Image.new("RGBA", img.size, (10, 6, 12, 0))
        contorno.putalpha(borda.point(lambda p: int(p * 0.92)))
        img = Image.alpha_composite(img, contorno)
    if brilho:
        g = mask.filter(ImageFilter.GaussianBlur(14)).point(lambda p: int(p * 0.35))
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
            if atual and larg + esp + lw > LARG_TEXTO:
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
            self.card, mc = texto_brilho(c["card"], fonte_cabe("Cinzel-Bold.ttf", 96, c["card"], LARG_TEXTO - 40), OURO,
                                         brilho=(255, 150, 30))
            self.card_m = mc
        self.cta = desenha_cta(c["cta"]) if c.get("cta") else None

    def desenha(self, quadro, t):
        if self.card is not None:
            k = np.clip((t - self.a - 0.1) / 0.3, 0, 1)
            esc = 1.3 - 0.3 * (1 - (1 - k) ** 3)
            fim_card = min(self.b, self.a + 2.5)
            a = k * np.clip((fim_card - t) / 0.3, 0, 1)
            im = self.card.resize((int(self.card.width * esc), int(self.card.height * esc)), Image.BILINEAR)
            if a > 0.3:
                marca("cartao", im, (W - im.width) // 2, Y_CARTAO - im.height // 2)
            quadro.alpha_composite(com_alfa(im, a), ((W - im.width) // 2, Y_CARTAO - im.height // 2))
        for img, x, y, t0, d in self.pal:
            k = np.clip((t - t0 + 0.08) / 0.18, 0, 1)
            if k <= 0:
                continue
            fim = np.clip((self.b - t) / 0.15, 0, 1) if self.b < 1e8 else 1
            dy = int(14 * (1 - k))
            if k * fim > 0.3:
                marca("legenda", img, x, y + dy)
            quadro.alpha_composite(com_alfa(img, k * fim), (x, y + dy))
    def desenha_cta(self, quadro, t, fim=1e9):
        if self.cta is not None and self.a <= t < fim:
            k = np.clip((t - self.a) / 0.4, 0, 1) * np.clip((fim - t) / 0.5, 0, 1)
            pulso = 1 + 0.04 * np.sin((t - self.a) * 6)
            im = self.cta.resize((int(self.cta.width * pulso), int(self.cta.height * pulso)), Image.BILINEAR)
            marca("cta", im, (W - im.width) // 2, 1300 - im.height // 2)
            quadro.alpha_composite(com_alfa(im, k), ((W - im.width) // 2, 1300 - im.height // 2))


def desenha_cta(txt):
    f = fonte_cabe("Cinzel-Bold.ttf", 44, txt, LARG_TEXTO - 160)
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


def chip_contagem(seg, prog):
    """Contagem regressiva da revelação, DISCRETA (dono, 02/nov): pílula translúcida pequena, sem brilho nem pulso,
    para não roubar a atenção da legenda. Fica embaixo, fora da área dos ícones do TikTok."""
    f = fonte("Cinzel-Bold.ttf", 30)
    fn = fonte("Cinzel-Bold.ttf", 38)
    txt, num = "A REVELAÇÃO VEM EM ", f"{seg}s"
    tw, nw = int(f.getlength(txt)), int(fn.getlength(num))
    w, h = tw + nw + 56, 70
    img = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, 4 + w, 4 + h), 35, fill=(10, 8, 6, 120), outline=OURO + (110,), width=2)
    x0 = 4 + (w - tw - nw) // 2
    d.text((x0, 4 + 31), txt, font=f, fill=(240, 232, 218, 215), anchor="lm")
    d.text((x0 + tw, 4 + 30), num, font=fn, fill=OURO + (225,), anchor="lm")
    bx0, bx1, by = 4 + 30, 4 + w - 30, 4 + h - 12               # barra fina que esvazia até a revelação
    d.rounded_rectangle((bx0, by, bx1, by + 3), 1, fill=(255, 255, 255, 45))
    d.rounded_rectangle((bx0, by, bx0 + max(3, int((bx1 - bx0) * prog)), by + 3), 1, fill=OURO + (170,))
    return img


def cabecalho(ref):
    f = fonte("Cinzel-Bold.ttf", 40)
    img, m = texto_brilho(ref, f, OURO, brilho=(255, 160, 40), espaco=6)
    camada = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = (W - img.width) // 2
    camada.alpha_composite(img, (x, 230 - img.height // 2))
    marca("referencia", img, x, 230 - img.height // 2)
    d = ImageDraw.Draw(camada)
    for lado in (-1, 1):
        cx = W // 2 + lado * (img.width // 2 - m + 30)
        d.line([(cx, 232), (cx + lado * 90, 232)], fill=OURO + (150,), width=2)
    return camada


def titulo_camadas(linhas):
    out, y = [], Y_TITULO
    for i, ln in enumerate(linhas):
        ultimo = i == len(linhas) - 1
        f = fonte_cabe("Cinzel-Bold.ttf", 104 if ultimo else 86, ln, LARG_TEXTO + 40)
        img, m = texto_brilho(ln, f, OURO if ultimo else (255, 255, 255), brilho=(255, 150, 30) if ultimo else None)
        out.append((img, y - m))
        y += 116 if not ultimo else 130
    return out


def sobreposicao():
    """Escurecimento em cima/embaixo + vinheta, para a letra sempre ler bem."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = ((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2
    a = np.clip(v - 0.25, 0, 1) * 110
    meio = np.exp(-((yy - 1040) / 260) ** 2) * 75            # faixa mais escura atrás da legenda
    topo = np.clip((330 - yy) / 330, 0, 1) * 80
    alfa = np.clip(a + meio + topo, 0, 230).astype(np.uint8)
    img = Image.new("RGBA", (W, H), (4, 4, 8, 0))
    img.putalpha(Image.fromarray(alfa))
    return img


class Fundo:
    def __init__(self, arqs, janelas, provisorio, emenda=False):
        self.emenda = emenda    # loop: a última janela anda ao contrário e termina no enquadramento do 1º quadro
        self.imgs = []
        for arq in arqs:
            im = Image.open(arq).convert("RGB")
            esc = max(W * 1.18 / im.width, H * 1.18 / im.height)
            im = im.resize((int(im.width * esc), int(im.height * esc)), Image.LANCZOS)
            self.imgs.append(im if provisorio else tratamento(im))     # cor de cinema 4K (dono, 02/nov)
        self.jan = janelas      # [(i_img, t0, t1)]
        self.prov = provisorio

    def _quadro(self, i, t, t0, t1, reverso=False):
        im = self.imgs[i]
        k = np.clip(((t1 - t) if reverso else (t - t0)) / max(0.1, t1 - t0), 0, 1.5)
        zoom = 1.0 + 0.15 * k if i % 2 == 0 else 1.15 - 0.15 * k
        cw, ch = W * 1.18 / zoom * im.width / (W * 1.18), H * 1.18 / zoom * im.height / (H * 1.18)
        cw, ch = im.width / 1.18 / zoom * 1.0, im.height / 1.18 / zoom
        dx = (im.width - cw) * (0.5 + 0.35 * (k - 0.5) * (1 if i % 3 else -1))
        dy = (im.height - ch) * (0.5 + 0.2 * (k - 0.5))
        return im.resize((W, H), Image.BILINEAR, box=(dx, dy, dx + cw, dy + ch))

    ANTES, DUR = 0.3, 1.0      # a transição começa 0,3 s antes da fala da nova cena e dura 1,0 s

    def quadro(self, t):
        """Fusão suave (curva ease in-out) entre as imagens: as duas continuam em movimento durante a troca, com um leve
        desfoque e um brilho quente no meio (como um 'dissolve' de cinema), sem corte seco e sem soco de zoom."""
        atual = [j for j in self.jan if j[1] - self.ANTES <= t] or [self.jan[0]]
        idx = self.jan.index(atual[-1])
        i, t0, t1 = atual[-1]
        ini = t0 - self.ANTES if idx > 0 else t0
        rev = self.emenda and idx == len(self.jan) - 1 and idx > 0 and i == self.jan[0][0]
        q = self._quadro(i, t, ini, t1, rev)
        if idx > 0:
            p = (t - ini) / self.DUR
            if 0 <= p < 1:
                pi, p0, p1 = self.jan[idx - 1]
                e = p * p * (3 - 2 * p)
                q = Image.blend(self._quadro(pi, t, p0 - (self.ANTES if idx > 1 else 0), p1), q, e)
                meio = float(np.sin(np.pi * p))
                if meio > 0.05:
                    q = q.filter(ImageFilter.GaussianBlur(5 * meio))
                    q = Image.blend(q, Image.new("RGB", q.size, (255, 226, 170)), 0.10 * meio)
        return q.convert("RGBA")


class Escurece:
    """Escurecimento automático atrás do texto (dono, 02/nov: os analistas acharam cartões difíceis de ler sobre céu claro).
    Mede o brilho do fundo na faixa do cartão e da legenda em cada quadro e escurece só o necessário."""
    NIVEIS = 32

    def __init__(self):
        self.atual = None                      # força suavizada (sem degrau nem tremida de um quadro para o outro)
        yy = np.arange(H, dtype=np.float32)[:, None]
        faixa = np.exp(-((yy - 900) / 380) ** 4) * np.ones((1, W), np.float32)    # plana do cartão (y~650) à legenda (y~1200)
        self.mascaras = [Image.fromarray((faixa * 255 * k / (self.NIVEIS - 1)).astype(np.uint8))
                         for k in range(self.NIVEIS)]
        self.preto = Image.new("RGBA", (W, H), (4, 4, 8, 0))

    @staticmethod
    def brilho(img):
        """Brilho (0-255) do fundo nas áreas de texto: percentil 75 da luminância, em resolução reduzida."""
        p = np.asarray(img.convert("L").resize((108, 192), Image.BILINEAR), np.float32)
        return {"cartao": float(np.percentile(p[57:71, 17:91], 75)), "legenda": float(np.percentile(p[86:124, 17:91], 75))}

    def aplica(self, img):
        b = self.brilho(img)
        alvo = float(np.clip((max(b.values()) - 80) / 60, 0, 1)) * 0.8        # até 80% de escurecimento no centro
        self.atual = alvo if self.atual is None else self.atual + (alvo - self.atual) * 0.12
        k = int(round(self.atual * (self.NIVEIS - 1)))
        if k:
            camada = self.preto.copy()
            camada.putalpha(self.mascaras[k])
            img.alpha_composite(camada)
        return k


def particulas(n=45, semente=1):
    rng = np.random.default_rng(semente)
    return [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.5, 4.5), rng.uniform(12, 40), rng.uniform(0, 6.28))
            for _ in range(n)]


def renderiza(rot, arqs, voz, tempos, saida, provisorio):
    cenas = rot["cenas"]
    dur = len(voz) / SR + cauda(rot)
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
    fundo = Fundo(arqs, [tuple(j) for j in jan], provisorio, bool(rot.get("emenda")))
    sob, cab = sobreposicao(), cabecalho(rot["ref"])
    # quanto o fundo do último quadro difere do primeiro (0 = emenda invisível); o analista automático cobra
    a0 = np.asarray(fundo.quadro(0).convert("RGB").resize((108, 192)), np.float32)
    a1 = np.asarray(fundo.quadro(dur - 1 / FPS).convert("RGB").resize((108, 192)), np.float32)
    LAYOUT_EXTRA["emenda_diff"] = float(np.abs(a0 - a1).mean())
    tit = titulo_camadas(rot["titulo"])
    fim_titulo = (tempos[1][0] + 0.25) if len(tempos) > 1 else tempos[0][1]      # o título some quando entra o 1º re-gancho
    # capa (dono, 02/nov): o TikTok só aceita um QUADRO do vídeo como capa (Buffer: metadata.thumbnailOffset). A capa é o
    # quadro com o título inteiro no ar; a legenda da cena 0 não aparece (o título já é o gancho escrito), capa limpa.
    t_capa = round(min(1.2, max(0.75, fim_titulo - 0.6)), 2)
    LAYOUT_EXTRA["capa_t"] = t_capa
    sem_legenda0 = not rot.get("legenda_cena0", False)
    escur, contraste = Escurece(), {}
    parts = particulas()
    # com emenda o botão "Comente" sai 1,5 s depois de entrar a última fala: o fim fica igual ao começo
    fim_cta = (tempos[-1][0] + 1.5) if rot.get("emenda") else 1e9
    ganchos_t = [tempos[0][0]] + [tp[0] for c, tp in zip(cenas, tempos) if c.get("card") or c.get("cta")]
    rev_t = tempos[rot["revelacao"]][0] if "revelacao" in rot else None
    flash_cor = Image.new("RGBA", (W, H), (255, 214, 140, 255))
    aviso = None
    if provisorio:
        aviso, _ = texto_brilho("RASCUNHO · fundo provisório", fonte("Cormorant-SemiBold.ttf", 36), (255, 120, 120))

    audio = mixa(voz, tempos, cenas, dur, bool(rot.get("emenda")))
    arq_a = saida + ".wav"
    with wave.open(arq_a, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())

    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", arq_a, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", saida]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nq = int(dur * FPS)
    for q in range(nq):
        t = q / FPS
        img = fundo.quadro(t)
        dt_ = [t - h for h in ganchos_t if 0 <= t - h < 0.6]
        if dt_:                                         # clarão dourado curto no gancho (sem zoom no fundo)
            fl = flash_cor.copy()
            forca = 20 if (rot.get("emenda") and t < 0.6) else 70      # com emenda o clarão do 0 s é leve
            fl.putalpha(Image.new("L", (W, H), int(forca * np.exp(-min(dt_) / 0.10))))
            img.alpha_composite(fl)
        img.alpha_composite(sob)
        escur.aplica(img)
        if q % 3 == 0:                                  # contraste: brilho do fundo atrás do texto, por cena (analista)
            ci = max([k for k, o in enumerate(objs) if o.a - 0.05 <= t] or [0])
            b = escur.brilho(img)
            m = contraste.setdefault(ci, {"cartao": 0.0, "legenda": 0.0})
            if cenas[ci].get("card") and t <= objs[ci].a + 2.5:
                m["cartao"] = max(m["cartao"], round(b["cartao"], 1))
            m["legenda"] = max(m["legenda"], round(b["legenda"], 1))
        d = ImageDraw.Draw(img)
        for (x, y, r, vel, fase) in parts:
            yy = (y - vel * t) % H
            xx = x + 14 * np.sin(t * 0.7 + fase)
            a = int(110 + 90 * np.sin(t * 2 + fase))
            d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 210, 140, max(0, a)))
        img.alpha_composite(cab)
        if t < fim_titulo:
            for k, (im, y) in enumerate(tit):
                ka = np.clip((t - 0.12 * k) / 0.3, 0, 1) * np.clip((fim_titulo - 0.2 - t) / 0.25, 0, 1)
                esc = 1.25 - 0.25 * (1 - (1 - np.clip((t - 0.12 * k) / 0.3, 0, 1)) ** 3)
                im2 = im.resize((int(im.width * esc), int(im.height * esc)), Image.BILINEAR) if esc > 1.001 else im
                if ka > 0.3:
                    marca("titulo", im2, (W - im2.width) // 2, y - (im2.height - im.height) // 2)
                img.alpha_composite(com_alfa(im2, ka), ((W - im2.width) // 2, y - (im2.height - im.height) // 2))
        if rev_t is not None and 0 < rev_t - t <= 16 and t > fim_titulo:      # contagem regressiva da revelação
            seg = int(np.ceil(rev_t - t))
            ch = chip_contagem(seg, (rev_t - t) / 16)
            entra = np.clip((t - max(fim_titulo, rev_t - 16)) / 0.5, 0, 1) * np.clip((rev_t - t) / 0.3, 0, 1)
            pos = ((W - ch.width) // 2, Y_CONTAGEM - ch.height // 2)
            marca("contagem", ch, *pos)
            img.alpha_composite(com_alfa(ch, entra), pos)
        for k, o in enumerate(objs):
            if o.a - 0.05 <= t < o.b and not (k == 0 and sem_legenda0 and t < fim_titulo):
                o.desenha(img, t)
            o.desenha_cta(img, t, fim_cta)           # o botão "Comente" fica até o fim (com emenda, some antes)
        if aviso is not None:
            img.alpha_composite(aviso, ((W - aviso.width) // 2, 1560))
        proc.stdin.write(img.convert("RGB").tobytes())
        if q % 150 == 0:
            print(f"  quadro {q}/{nq}", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(arq_a)
    LAYOUT_EXTRA["contraste"] = {str(k): v for k, v in sorted(contraste.items())}
    # capa: o mesmo quadro que o TikTok vai usar, para o dono e os analistas verem
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t_capa:.2f}", "-i", saida, "-frames:v", "1", "-q:v", "2",
                    saida[:-4] + "_capa.jpg"], check=True)


# ---------------------------------------------------------------- principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("--so-texto", action="store_true")
    ap.add_argument("--autorizo-nova-voz", action="store_true", help="só com licença do dono (regra: 1 voz por vídeo)")
    ap.add_argument("--ignora-conferidor", action="store_true", help="só para teste; o canal exige zero FALHA")
    ap.add_argument("--sem-imagens", action="store_true", help="rascunho com fundo provisório (não chama Replicate)")
    ap.add_argument("--ignora-analistas", action="store_true", help="só para teste; o canal exige zero FALHA dos analistas")
    ap.add_argument("--saida", help="pasta de saída (padrão: saida/luz)")
    a = ap.parse_args()
    carrega_chaves()
    rot = json.load(open(a.roteiro, encoding="utf-8"))
    n = sum(len(limpa(c["fala"]).split()) for c in rot["cenas"])
    print("[ganchos] conferindo o roteiro:")
    if conferir.imprime(conferir.confere(rot)) and not a.ignora_conferidor:
        sys.exit("[ganchos] corrija as FALHA acima (python luz_da_palavra/conferir.py <roteiro>) antes de gerar.")
    if a.so_texto:
        print(texto_tts(rot["cenas"]))
        print(f"\n{n} palavras ≈ {n / 2.8:.0f} s")
        return
    pasta = os.path.join(RAIZ, ".cache", "luz", rot["slug"])
    os.makedirs(pasta, exist_ok=True)
    arqs = imagens(rot, pasta, a.sem_imagens)
    voz = ajusta_ritmo(narracao(rot, pasta, a.autorizo_nova_voz), rot.get("teto_pausa", 0.3), rot.get("velocidade", 1.08))
    if rot.get("emenda"):                # loop: corta o silêncio que o TTS deixa no fim (a última palavra cola no começo)
        h = SR // 100
        env = np.abs(voz[: len(voz) // h * h]).reshape(-1, h).max(1)
        fala_ate = (np.where(env > 0.03)[0][-1] + 1) * h if (env > 0.03).any() else len(voz)
        voz = voz[: min(len(voz), fala_ate + int(0.06 * SR))]
    tempos = tempos_cenas(voz, rot["cenas"])
    for c, (x, y, fa, fb) in zip(rot["cenas"], tempos):
        print(f"  {x:5.2f}-{y:5.2f}  {'[GANCHO] ' if conferir.eh_gancho(c) or c.get('cta') else ''}{limpa(c['fala'])}")
    dur_tot = len(voz) / SR + cauda(rot)
    print("[ganchos] com os tempos reais da voz:")
    if conferir.imprime(conferir.confere(rot, [tp[0] for tp in tempos], dur_tot)) and not a.ignora_conferidor:
        sys.exit("[ganchos] há lacunas sem gancho nos tempos reais; ajuste os cartões (sem mudar a fala) e rode de novo.")
    dir_saida = a.saida or os.path.join(RAIZ, "saida", "luz")
    os.makedirs(dir_saida, exist_ok=True)
    nome = rot["slug"] + ("_rascunho" if a.sem_imagens else "")
    saida = os.path.join(dir_saida, nome + ".mp4")
    renderiza(rot, arqs, voz, tempos, saida, a.sem_imagens)
    with open(os.path.join(dir_saida, rot["slug"] + "_legenda.txt"), "w", encoding="utf-8") as f:
        f.write(rot["legenda"] + "\n")
    # o que os analistas precisam para revisar sem renderizar de novo
    json.dump({"layout": LAYOUT, **LAYOUT_EXTRA, "emenda": rot.get("emenda"), "tempos": tempos, "dur": dur_tot, "imagens": arqs,
               "voz_sr": SR, "capa": saida[:-4] + "_capa.jpg"},
              open(os.path.join(pasta, "render.json"), "w"), indent=1)
    np.save(os.path.join(pasta, "voz_final.npy"), voz)
    print(f"[ok] renderizado: {saida}  ({dur_tot:.1f} s)")
    print("[analistas] revisando cada parte do vídeo antes de finalizar:")
    falhas = analistas.analisa(rot, saida, pasta, rascunho=a.sem_imagens)
    if falhas and not a.ignora_analistas:
        sys.exit(f"[analistas] {falhas} FALHA: vídeo NÃO aprovado (relatório em {saida[:-4]}_analise.txt). "
                 "Corrija e rode de novo; o tema não foi registrado.")
    if not a.sem_imagens and not a.saida:
        temas.registra(rot)          # entra na lista de temas (vale 2 meses)
    print(f"[ok] aprovado nos analistas automáticos: {saida}\n[ok] agora rode os 5 analistas Claude (analista-fatos, "
          "analista-imagens, analista-tela, analista-som, analista-post) e só publique com todos APROVADO.")


if __name__ == "__main__":
    main()
