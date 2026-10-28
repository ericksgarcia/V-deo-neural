"""Narração (Gemini TTS), trilha sintetizada e efeitos sonoros, tudo em numpy."""
import base64
import hashlib
import io
import json
import os
import re
import subprocess
import urllib.request
import wave

import numpy as np

SR = 48000
API = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


def _le_wav(dados):
    with wave.open(io.BytesIO(dados)) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(1)
    return x, sr


def _reamostra(x, sr):
    if sr == SR:
        return x
    t = np.arange(int(len(x) * SR / sr)) * sr / SR
    return np.interp(t, np.arange(len(x)), x).astype(np.float32)


def _apara(x, limiar=0.012, folga=0.04):
    env = np.convolve(np.abs(x), np.ones(480) / 480, "same")
    idx = np.where(env > limiar)[0]
    if not len(idx):
        return x
    a, b = max(0, idx[0] - int(folga * SR)), min(len(x), idx[-1] + int(folga * SR))
    return x[a:b]


_UNID = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
         "treze", "catorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
_DEZ = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
_CEM = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos",
        "oitocentos", "novecentos"]


def por_extenso(n):
    """Inteiro (0..999.999) por extenso em português; o TTS lê "32" como "três ponto dois"."""
    if n < 20:
        return _UNID[n]
    if n < 100:
        d, u = divmod(n, 10)
        return _DEZ[d] + (f" e {_UNID[u]}" if u else "")
    if n == 100:
        return "cem"
    if n < 1000:
        c, r = divmod(n, 100)
        return _CEM[c] + (f" e {por_extenso(r)}" if r else "")
    m, r = divmod(n, 1000)
    pre = "mil" if m == 1 else f"{por_extenso(m)} mil"
    if not r:
        return pre
    return pre + (" e " if r < 100 or r % 100 == 0 else " ") + por_extenso(r)


def falavel(texto):
    return re.sub(r"\d{1,3}(?:\.\d{3})+|\d+", lambda m: por_extenso(int(m.group().replace(".", ""))), texto)


def _tts(texto, voz, modelo):
    corpo = {"contents": [{"parts": [{"text": texto}]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}}
    url = API.format(modelo)
    if os.environ.get("GEMINI_API_KEY"):
        url += "?key=" + os.environ["GEMINI_API_KEY"]
    req = urllib.request.Request(url, json.dumps(corpo).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        parte = json.load(r)["candidates"][0]["content"]["parts"][0]["inlineData"]
    dados = base64.b64decode(parte["data"])
    if dados[:4] == b"RIFF":
        x, sr = _le_wav(dados)
    else:  # PCM cru 16-bit 24 kHz
        x, sr = np.frombuffer(dados, np.int16).astype(np.float32) / 32768, 24000
    return _reamostra(x, sr)


def _silencios(x, minimo=0.25, limiar=0.02):
    h = SR // 50
    n = len(x) // h
    sil = np.abs(x[: n * h]).reshape(n, h).max(1) < limiar
    out, i = [], 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            if (j - i) * 0.02 >= minimo and i > 0 and j < n:
                out.append((i + j) / 2 * 0.02)
            i = j
        else:
            i += 1
    return np.array(out)


def narra_lote(falas, cache, voz="Charon", modelo="gemini-3.8-flash-tts", velocidade=1.15, tentativa=0):
    """Narra todas as falas numa ÚNICA chamada (mesmo timbre do início ao fim) e corta por fala.

    O corte usa os tempos de cada palavra que o Whisper (local) ouve no áudio inteiro, alinhados
    com o texto do roteiro; assim cada fala cai na cena certa. Devolve uma lista de áudios mono
    float32 a 48 kHz, ou None se a API não estiver disponível.
    O texto vai puro: instruções de estilo no prompt acabam sendo lidas em voz alta."""
    os.makedirs(cache, exist_ok=True)
    textos = [falavel(f) for f in falas]
    extra = f"|t{tentativa}" if tentativa else ""
    chave = hashlib.sha1(f"{modelo}|{voz}|{velocidade}|{textos}{extra}".encode()).hexdigest()[:16]
    arq = os.path.join(cache, chave + "_v2.npz")
    if os.path.exists(arq):
        z = np.load(arq)
        return [z[f"f{k}"] for k in range(len(falas))]
    antigo = os.path.join(cache, chave + ".npz")
    if os.path.exists(antigo):  # cache da versão anterior: as partes juntas são o áudio inteiro
        z = np.load(antigo)
        x = np.concatenate([z[f"f{k}"] for k in range(len(falas))])
    else:
        try:
            x = _tts("\n\n".join(textos), voz, modelo)
        except Exception as e:  # sem rede/chave: segue só com legendas
            print(f"  [aviso] TTS indisponível ({e}); usando só legenda")
            return None
        x = _apara(x)
        if abs(velocidade - 1) > 1e-3:
            x = _atempo(x, velocidade)
        x = (0.9 * x / (np.abs(x).max() + 1e-6)).astype(np.float32)
    partes = _segmenta(x, falas)
    np.savez(arq, completo=x, **{f"f{k}": p for k, p in enumerate(partes)})
    return partes


def _segmenta(x, falas):
    """Corta o áudio inteiro em uma parte por fala, alinhando o texto com as palavras do Whisper."""
    import difflib
    from .fala import _canon, para16k, transcreve
    _, ws, _ = transcreve(para16k(x, SR), idioma="pt")
    roteiro = [(tok, k) for k, f in enumerate(falas) for tok in _canon(f).split()]
    ouvido = [(tok, j) for j, w in enumerate(ws) for tok in _canon(w[2]).split()]
    sm = difflib.SequenceMatcher(None, [a for a, _ in roteiro], [a for a, _ in ouvido], autojunk=False)
    ini = [None] * len(falas)
    fim = [None] * len(falas)
    for bloco in sm.get_matching_blocks():
        for d in range(bloco.size):
            k = roteiro[bloco.a + d][1]
            j = ouvido[bloco.b + d][1]
            ini[k] = ws[j][0] if ini[k] is None else min(ini[k], ws[j][0])
            fim[k] = ws[j][1] if fim[k] is None else max(fim[k], ws[j][1])
    dur = len(x) / SR
    # falas sem nenhuma palavra reconhecida: interpola entre as vizinhas
    for k in range(len(falas)):
        if ini[k] is None:
            a = fim[k - 1] if k > 0 and fim[k - 1] is not None else 0.0
            b = next((ini[j] for j in range(k + 1, len(falas)) if ini[j] is not None), dur)
            ini[k], fim[k] = a, b
    cortes = [0.0]
    for k in range(len(falas) - 1):
        cortes.append(max((fim[k] + ini[k + 1]) / 2, cortes[-1]))
    cortes.append(dur)
    return [_apara(x[int(a * SR):int(b * SR)]).astype(np.float32) for a, b in zip(cortes[:-1], cortes[1:])]


def _atempo(x, fator):
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-filter:a", f"atempo={fator}", "-f", "f32le", "-"], input=x.astype(np.float32).tobytes(),
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32).copy()


# ---------------------------------------------------------------- síntese

def _env(n, ataque=0.005, queda=0.2):
    t = np.arange(n) / SR
    return np.minimum(t / ataque, 1) * np.exp(-t / queda)


def _lp(x, corte):
    """Passa-baixa barato por média móvel dupla (suficiente para timbre)."""
    k = max(1, int(SR / corte / 2))
    ker = np.ones(k) / k
    return np.convolve(np.convolve(x, ker, "same"), ker, "same")


def _nota(f, dur, forma="serra"):
    t = np.arange(int(dur * SR)) / SR
    if forma == "serra":
        return (2 * ((t * f) % 1) - 1) * 0.6 + 0.4 * (2 * ((t * f * 1.005) % 1) - 1)
    return np.sin(2 * np.pi * f * t)


def trilha(dur, bpm=124, semente=0):
    """Arpejo eletrônico em lá menor com baixo, bumbo e chimbal."""
    n = int(dur * SR)
    out = np.zeros(n + SR, np.float32)
    batida = 60 / bpm
    acordes = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 52, 55, 60], [55, 59, 62, 67]]  # Am F C G
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    passo = batida / 4
    k = 0
    t = 0.0
    while t < dur:
        compasso = int(t / (batida * 4)) % 4
        ac = acordes[compasso]
        i = int(t * SR)
        nota = ac[[0, 1, 2, 3, 2, 1, 3, 2][k % 8]] + 12
        s = _nota(hz(nota), passo * 0.95) * _env(int(passo * 0.95 * SR), 0.003, 0.09) * 0.11
        out[i:i + len(s)] += s
        if k % 4 == 0:  # baixo + bumbo a cada tempo
            b = _nota(hz(ac[0] - 12), batida * 0.9) * _env(int(batida * 0.9 * SR), 0.004, 0.25) * 0.16
            out[i:i + len(b)] += b
            m = int(0.25 * SR)
            tt = np.arange(m) / SR
            kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12) * 0.5
            out[i:i + m] += kick
        if k % 4 == 2:
            m = int(0.05 * SR)
            hat = np.random.default_rng(k).normal(0, 1, m) * np.exp(-np.arange(m) / SR * 80) * 0.05
            out[i:i + m] += np.diff(hat, prepend=0)
        k += 1
        t += passo
    pad = np.zeros_like(out)
    for c in range(int(dur / (batida * 4)) + 1):
        i = int(c * batida * 4 * SR)
        m = int(batida * 4 * SR)
        s = sum(_nota(hz(f), batida * 4, "seno") for f in acordes[c % 4][:3]) * 0.03
        fade = np.minimum(1, np.minimum(np.arange(m), m - np.arange(m)) / (0.3 * SR))
        pad[i:i + m] += (s * fade)[: len(pad) - i]
    out = _lp(out, 6000) + pad
    return out[:n]


def boom(intensidade=1.0, semente=0):
    m = int(0.7 * SR)
    rng = np.random.default_rng(semente)
    tt = np.arange(m) / SR
    ruido = _lp(rng.normal(0, 1, m), 900) * np.exp(-tt * 6)
    grave = np.sin(2 * np.pi * (35 + 60 * np.exp(-tt * 20)) * tt) * np.exp(-tt * 7)
    return (0.5 * ruido + 0.6 * grave) * 0.5 * intensidade


def batida(intensidade=1.0, semente=0):
    """Colisão de carro: estalo de ruído + lata ressoando."""
    m = int(0.5 * SR)
    rng = np.random.default_rng(semente)
    tt = np.arange(m) / SR
    ruido = rng.normal(0, 1, m)
    estalo = (ruido - _lp(ruido, 1500)) * np.exp(-tt * 25)
    lata = sum(np.sin(2 * np.pi * f * tt + rng.random() * 6) for f in (523, 787, 1243, 1871)) * np.exp(-tt * 14) / 4
    corpo = _lp(ruido, 400) * np.exp(-tt * 18)
    return (0.6 * estalo + 0.35 * lata + 0.5 * corpo) * 0.6 * intensidade


def ding(alto=False):
    m = int(0.6 * SR)
    tt = np.arange(m) / SR
    f = 1318 if alto else 988
    s = (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.5 * tt)) * np.exp(-tt * 7)
    return s * (0.32 if alto else 0.2)


def whoosh(semente=0):
    m = int(0.45 * SR)
    rng = np.random.default_rng(semente)
    tt = np.arange(m) / SR
    env = np.sin(np.pi * tt / tt[-1]) ** 2
    return _lp(rng.normal(0, 1, m), 2500) * env * 0.18


def chute(intensidade=1.0, semente=0):
    m = int(0.18 * SR)
    tt = np.arange(m) / SR
    grave = np.sin(2 * np.pi * (60 + 140 * np.exp(-tt * 60)) * tt) * np.exp(-tt * 28)
    clique = np.random.default_rng(semente).normal(0, 1, m) * np.exp(-tt * 140)
    return (0.8 * grave + 0.25 * clique) * 0.7 * intensidade


def torcida_explode(intensidade=1.0, semente=0, dur=2.2, ohh=False):
    """Explosão da torcida (gol) ou 'uhhh' (defesa/fora): ruído filtrado com envelope."""
    m = int(dur * SR)
    rng = np.random.default_rng(semente)
    tt = np.arange(m) / SR
    ruido = rng.normal(0, 1, m)
    banda = _lp(ruido, 2400 if not ohh else 900) - _lp(ruido, 250)
    env = np.minimum(tt / (0.08 if not ohh else 0.25), 1) * np.exp(-tt / (0.9 if not ohh else 0.6))
    voz = 0
    if ohh:  # vogal coletiva: alguns harmônicos graves desafinados
        voz = sum(np.sin(2 * np.pi * f * tt * (1 - 0.08 * tt)) for f in (180, 230, 270, 340)) / 4 * 0.5
    return (banda * 0.9 + voz) * env * 0.5 * intensidade


def rede(intensidade=1.0, semente=0):
    m = int(0.35 * SR)
    tt = np.arange(m) / SR
    chiado = _lp(np.random.default_rng(semente).normal(0, 1, m), 5000) * np.exp(-tt * 9)
    s = torcida_explode(1.0, semente, 2.4)
    s[:m] += chiado * 0.35
    return s * intensidade


def defesa(intensidade=1.0, semente=0):
    m = int(0.12 * SR)
    tt = np.arange(m) / SR
    tapa = np.random.default_rng(semente).normal(0, 1, m) * np.exp(-tt * 70)
    s = torcida_explode(0.9, semente, 1.6, ohh=True)
    s[:m] += tapa * 0.6
    return s * intensidade


def fora(intensidade=1.0, semente=0):
    return torcida_explode(0.7, semente, 1.4, ohh=True) * intensidade


def glitch(semente=0):
    """Ruído digital curto para a entrada de cartões/hologramas."""
    m = int(0.28 * SR)
    rng = np.random.default_rng(semente)
    tt = np.arange(m) / SR
    quad = np.sign(np.sin(2 * np.pi * (300 + 900 * rng.random(8)).repeat(m // 8 + 1)[:m] * tt))
    return quad * (rng.random(m) > 0.3) * np.exp(-tt * 9) * 0.08


def tique(semente=0):
    m = int(0.02 * SR)
    tt = np.arange(m) / SR
    return np.sin(2 * np.pi * 2400 * tt) * np.exp(-tt * 300) * 0.06


def torcida(dur, semente=0):
    """Murmúrio contínuo de estádio com ondas lentas."""
    n = int(dur * SR)
    rng = np.random.default_rng(semente)
    r = rng.normal(0, 1, n).astype(np.float32)
    banda = _lp(r, 1400) - _lp(r, 200)
    onda = 0.7 + 0.3 * np.sin(2 * np.pi * np.arange(n) / SR / 7.0)
    return (banda * onda * 0.09).astype(np.float32)


SONS = {"boom": boom, "batida": batida, "chute": chute, "rede": rede, "defesa": defesa, "fora": fora,
        "glitch": lambda i, k: glitch(k), "tique": lambda i, k: tique(k), "whoosh": lambda i, k: whoosh(k),
        "ding": lambda i, k: ding(i > 1)}


def mixa(dur, falas, eventos, semente=0, ambiente=None, musica=0.55):
    """falas: [(t, audio)], eventos: [(t, tipo, intensidade)] -> estéreo float32."""
    n = int(dur * SR)
    voz = np.zeros(n + SR * 3, np.float32)
    for t, a in falas:
        i = int(t * SR)
        voz[i:i + len(a)] += a[: len(voz) - i]
    sfx = np.zeros_like(voz)
    for k, (t, tipo, inten) in enumerate(eventos):
        f = SONS[tipo]
        s = f(inten, k)
        i = int(max(t, 0) * SR)
        sfx[i:i + len(s)] += s[: len(sfx) - i]
    mus = np.zeros_like(voz)
    mus[:n] = trilha(dur, semente=semente)
    amb = np.zeros_like(voz)
    if ambiente is not None:
        amb[: min(n, len(ambiente))] = ambiente[:n]
    env = np.convolve(np.abs(voz), np.ones(4800) / 4800, "same")
    duck = 1 - 0.6 * np.clip(env / 0.05, 0, 1)
    mix = voz * 1.0 + sfx * 1.1 + mus * duck * musica + amb * (0.6 + 0.4 * duck)
    mix = mix[:n]
    fade = int(0.25 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix * 1.1) * 0.95
    return np.stack([mix, mix], 1).astype(np.float32)
