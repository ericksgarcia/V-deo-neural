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


def _decimal(m):
    i, d = m.group(1), m.group(2)
    dec = " ".join(por_extenso(int(x)) for x in d) if d.startswith("0") else por_extenso(int(d))
    return f"{por_extenso(int(i))} vírgula {dec}"


def falavel(texto, tags=False):
    """Texto como a voz deve dizer: números por extenso, siglas expandidas. As tags de evento (<short pause>...)
    são removidas, exceto quando `tags=True` (roteiro enviado ao TTS)."""
    if not tags:
        texto = re.sub(r"<[^>]+>", " ", texto)
    texto = re.sub(r"\bIA\b", "inteligência artificial", texto)
    texto = re.sub(r"(\d+),(\d+)", _decimal, texto)   # 1,8 -> "um vírgula oito"
    texto = re.sub(r"\d{1,3}(?:\.\d{3})+|\d+", lambda m: por_extenso(int(m.group().replace(".", ""))), texto)
    return texto.replace("%", " por cento")


class CotaEsgotada(RuntimeError):
    """A voz já usou as requisições permitidas (limite local ou recusa da API)."""


LIMITE_REQUISICOES = 10          # por voz, a cada 24 h (cota da conta)
# VOZ OFICIAL DO CANAL (decisão do dono, reafirmada em 31/out/2026): TODO vídeo usa a voz Achird no Gemini TTS 3.8.
# `narra_lote` recusa qualquer outra combinação, a menos que o dono tenha autorizado (`autorizada=True`).
VOZ_OFICIAL = "Achird"
MODELO_OFICIAL = "gemini-3.8-flash-tts"
VOZES_RESERVA = ["Charon", "Orus", "Fenrir", "Puck", "Iapetus", "Algenib", "Enceladus"]   # só com reserva=True


def confirma_voz(voz, modelo, autorizada=False):
    """Garante (e mostra no log) que a narração usa Achird + Gemini 3.8. Levanta erro se for outra coisa."""
    if (voz, modelo) != (VOZ_OFICIAL, MODELO_OFICIAL) and not autorizada:
        raise ValueError(f"voz/modelo fora do padrão do canal: {voz} / {modelo} "
                         f"(o padrão é {VOZ_OFICIAL} / {MODELO_OFICIAL}; só mude com licença do dono)")
    print(f"  [voz] confirmado: {voz} · {modelo}")
    return voz, modelo


def _uso_arq(cache):
    return os.path.join(cache, "uso.json")


def _usos(cache, voz):
    """Requisições reais já feitas com esta voz nas últimas 24 h (registradas por este projeto)."""
    import time
    try:
        regs = json.load(open(_uso_arq(cache)))
    except Exception:
        regs = []
    agora = time.time()
    return [r for r in regs if r["voz"] == voz and agora - r["t"] < 24 * 3600]


def _registra_uso(cache, voz, modelo):
    import time
    try:
        regs = json.load(open(_uso_arq(cache)))
    except Exception:
        regs = []
    regs.append({"t": time.time(), "voz": voz, "modelo": modelo})
    json.dump(regs, open(_uso_arq(cache), "w"))


def _tts(texto, voz, modelo, style=None):
    """UMA requisição ao TTS. Gemini 3.8: o texto é um roteiro literal (tudo é falado, exceto tags em inglês
    <assim>); estilo e ritmo vão em speechMetadata.style, ao lado do texto. Sem tentativas automáticas:
    cada chamada gasta cota."""
    parte = {"text": texto}
    if style:
        parte["speechMetadata"] = {"style": style}
    corpo = {"contents": [{"parts": [parte]}],
             "generationConfig": {"responseModalities": ["AUDIO"],
                                  "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voz}}}}}
    url = API.format(modelo)
    if os.environ.get("GEMINI_API_KEY"):
        url += "?key=" + os.environ["GEMINI_API_KEY"]
    req = urllib.request.Request(url, json.dumps(corpo).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", "ignore")[:300]
        if e.code == 429 or "RESOURCE_EXHAUSTED" in detalhe:
            raise CotaEsgotada(f"cota da voz {voz} esgotada: {detalhe}")
        raise RuntimeError(f"TTS falhou ({e.code}): {detalhe}")
    parte = resp["candidates"][0]["content"]["parts"][0]["inlineData"]
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


ESTILO_PADRAO = (
    "Voice: Achird. You are a warm, curious Brazilian (pt-BR) friend sharing something you just watched and can't "
    "stop thinking about, on the phone, close to the microphone. Not an announcer, not a YouTuber, not a movie-trailer "
    "narrator. Speak natural, relaxed Brazilian Portuguese, with small human touches: a short breath, a half-smile, a "
    "quiet laugh at the funny failures, affectionate teasing of the little AIs as if they were clumsy pets. "
    "Your core feeling is wonder: you find this genuinely amazing and you want a friend who knows nothing about "
    "artificial intelligence to feel that too. Explain every idea in plain everyday words, as if to a curious "
    "grandmother or a smart ten-year-old, and let the amazement show in your voice when something works "
    "('olha só o que ela fez sozinha'), never in shouting. "
    "Suspense is gentle and friendly, the kind you feel when a friend says 'espera, a parte boa vem agora': lower "
    "your voice a little, slow down, lean in, smile with the voice, then say the key number simply and let it land. "
    "Never dark, never ominous, never whispery like a horror film, never a deep dramatic trailer voice, never "
    "shouting or hype. Keep every sentence connected to the last, like one continuous story told in one breath "
    "of curiosity, with no abrupt switches of mood between sentences; use soft bridges ('aí', 'só que', 'e sabe o "
    "que ela fez?') in a natural, flowing rhythm. "
    "Pace: calm and clear, about 2.6 words per second, with real silences. "
    "Emotional shape: open intrigued and a little incredulous; explain the rules plainly with dry humor; go quiet "
    "and slow before a reveal, then say the number simply; right after a number lands a tiny amused reaction is "
    "welcome (the joke comes after the reveal, never before it); when you dare the listener to guess ('Chuta aí'), "
    "say it low and teasing, like a friend making a bet, then stay silent; when something finally works, sound "
    "genuinely moved and relieved, not hyped; end light, playful and truly curious about the listener's answer.")


def narra_lote(falas, cache, voz=VOZ_OFICIAL, modelo=MODELO_OFICIAL, estilo=None, antes=None,
               tts_textos=None, ritmo=4.0, faixa=(0.84, 1.1), reserva=False, forcar=False, autorizada=False):
    """Narra todas as falas com UMA ÚNICA requisição (mesmo timbre do início ao fim) e molda tudo localmente.

    falas  : textos visíveis de cada cena (sem tags).
    antes  : tags opcionais por cena (ex.: "<long pause>") inseridas ANTES da fala no roteiro enviado ao TTS.
    A voz é cacheada por (modelo, voz, estilo, texto): o mesmo pedido nunca é repetido. Se a cota da voz
    estiver esgotada, tenta as vozes de reserva (uma requisição em cada). Todo o resto é local: corte por cena
    (palavras do Whisper), ritmo de cada fala para ~`ritmo` palavras/s (limitado a `faixa` de velocidade, sem
    deixar a voz artificial) e volume igualado. Devolve áudios mono float32 a 48 kHz, ou None sem TTS."""
    os.makedirs(cache, exist_ok=True)
    confirma_voz(voz, modelo, autorizada)
    estilo = estilo or ESTILO_PADRAO
    if not estilo.lstrip().startswith(f"Voice: {voz}"):   # a direção de voz sempre nomeia a voz do canal
        estilo = f"Voice: {voz}. " + estilo
    textos = [falavel(f) for f in falas]
    antes = antes or [""] * len(falas)
    enviados = [falavel(f, tags=True) for f in (tts_textos or falas)]
    roteiro = "\n\n".join((a + " " if a else "") + t for a, t in zip(antes, enviados))
    vozes = [voz] + [v for v in VOZES_RESERVA if v != voz] if reserva else [voz]
    x = None
    for v in vozes:
        base = hashlib.sha1(f"{modelo}|{v}|{estilo}|{roteiro}".encode()).hexdigest()[:16]
        bruto = os.path.join(cache, base + "_bruto.npy")
        if os.path.exists(bruto) and not forcar:
            x, voz = np.load(bruto), v
            break
        if len(_usos(cache, v)) >= LIMITE_REQUISICOES:
            print(f"  [cota] voz {v}: {LIMITE_REQUISICOES} requisições nas últimas 24 h; tentando outra voz")
            continue
        try:
            print(f"  [tts] 1 requisição ({modelo}, voz {v})")
            _registra_uso(cache, v, modelo)
            x = _apara(_tts(roteiro, v, modelo, estilo))
        except CotaEsgotada as e:
            print(f"  [cota] {e}")
            continue
        except Exception as e:  # sem rede/chave: segue só com legendas
            print(f"  [aviso] TTS indisponível ({e}); usando só legenda")
            return None
        x = (0.9 * x / (np.abs(x).max() + 1e-6)).astype(np.float32)
        np.save(bruto, x)
        voz = v
        break
    if x is None:
        print("  [aviso] nenhuma voz disponível; usando só legenda")
        return None
    return _molda(x, falas, textos, ritmo, faixa)


def _pausas(p, minimo=0.25, limiar=0.02):
    """[(inicio, fim)] em amostras dos silêncios de pelo menos `minimo` s no meio da fala."""
    h = int(0.01 * SR)
    n = len(p) // h
    sil = np.abs(p[: n * h]).reshape(n, h).max(1) < limiar
    runs, i = [], 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            if (j - i) * 0.01 >= minimo and i > 0 and j < n:
                runs.append((i * h, j * h))
            i = j
        else:
            i += 1
    return runs


def _enxuga(p, curta=0.15, inclina=0.30, longa=0.55, minimo=0.25):
    """Encurta os silêncios de uma fala: pausa g -> clip(curta + inclina*(g - minimo), curta, longa).
    Assim a pausa curta fica ~0,15 s e a dramática (tag <long pause>) no máximo ~0,55 s: o suspense continua,
    a narração deixa de arrastar. Emenda com fades de 8 ms para não estalar."""
    runs = _pausas(p, minimo)
    if not runs:
        return p
    f = int(0.008 * SR)
    pedacos, pos = [], 0
    for a, b in runs:
        g = (b - a) / SR
        novo = int(np.clip(curta + inclina * (g - minimo), curta, longa) * SR)
        fala_ = p[pos:a + f].copy()
        if len(fala_) > 2 * f:
            fala_[-f:] *= np.linspace(1, 0, f)
        pedacos += [fala_, np.zeros(novo, np.float32)]
        pos = max(b - f, a)
        entrada = p[pos:pos + f].copy()                  # a fala seguinte entra com fade para não estalar
        p = np.concatenate([p[:pos], entrada * np.linspace(0, 1, len(entrada)), p[pos + f:]])
    pedacos.append(p[pos:])
    return np.concatenate(pedacos).astype(np.float32)


def _molda(x, falas, textos, ritmo, faixa, com_pausas=None):
    """Corta o áudio inteiro por fala e molda ritmo, pausas e volume de cada uma (tudo local, sem API).

    ritmo = palavras por segundo ENQUANTO FALA (sem contar os silêncios). Falas mais rápidas que isso são
    desaceleradas até lá (nunca além de `faixa`); depois os silêncios longos são encurtados."""
    partes = []
    alvo_rms = None
    for t, p in zip(textos, _segmenta(x, falas)):
        palavras = len(t.split())
        parado = sum(b - a for a, b in _pausas(p)) / SR
        vel = palavras / max(len(p) / SR - parado, 1e-3)
        if palavras >= 5 and vel > ritmo:
            p = _atempo(p, float(np.clip(ritmo / vel, faixa[0], 1.0)))
        elif palavras >= 5 and vel < ritmo * 0.85:
            p = _atempo(p, float(np.clip(ritmo * 0.85 / vel, 1.0, faixa[1])))
        p = _enxuga(p)
        voz_ = p[np.abs(p) > 0.02]
        rms = float(np.sqrt(np.mean(voz_ ** 2))) if len(voz_) else 0.1
        alvo_rms = alvo_rms or rms
        p = p * (alvo_rms / max(rms, 1e-4))
        pico = float(np.abs(p).max()) or 1.0
        partes.append((p * min(1.0, 0.9 / pico)).astype(np.float32))
    return partes


def ritmo_das_falas(falas, partes):
    """Palavras faladas por segundo de cada fala (para conferir o ritmo da narração)."""
    return [len(falavel(f).split()) / max(len(p) / SR, 1e-3) for f, p in zip(falas, partes)]


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
    """Arpejo eletrônico em lá menor com baixo, bumbo e chimbal. Vai abrindo (filtro e volume) do começo ao fim:
    a energia sobe junto com a história."""
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
    w = np.linspace(0.0, 1.0, len(out)).astype(np.float32)
    out = (_lp(out, 2200) * (1 - w) + _lp(out, 7000) * w) * (0.8 + 0.2 * w) + pad
    return out[:n]


def riser(dur=0.6, semente=0):
    """Subida de suspense que preenche o silêncio antes de uma revelação (ruído que abre + tom que sobe)."""
    dur = float(min(max(dur, 0.25), 2.0))
    m = int(dur * SR)
    tt = np.arange(m) / SR
    u = tt / dur
    r = np.random.default_rng(semente).normal(0, 1, m).astype(np.float32)
    ruido = (_lp(r, 900) * (1 - u) + _lp(r, 5000) * u) * 0.25
    tom = np.sin(2 * np.pi * (220 * tt + 330 * tt * u)) * 0.35
    return ((ruido + tom) * u ** 2).astype(np.float32)


def impacto(intensidade=1.0, semente=0):
    """Batida grave curta no instante da revelação."""
    m = int(0.6 * SR)
    tt = np.arange(m) / SR
    sub = np.sin(2 * np.pi * (40 + 70 * np.exp(-tt * 25)) * tt) * np.exp(-tt * 7)
    r = np.random.default_rng(semente).normal(0, 1, m)
    ar = _lp(r, 3000) * np.exp(-tt * 30) * 0.3
    return ((sub + ar) * intensidade).astype(np.float32)


def coracao(intensidade=1.0, semente=0):
    """Batida dupla de coração (tum-tum), grave e baixa: preenche o silêncio da aposta sem competir com nada."""
    m = int(0.45 * SR)
    tt = np.arange(m) / SR
    x = np.zeros(m, np.float32)
    for atraso, amp in ((0.0, 1.0), (0.17, 0.7)):
        u = np.clip(tt - atraso, 0, None)
        x += (np.sin(2 * np.pi * 52 * u) * np.exp(-u * 18) * (tt >= atraso) * amp).astype(np.float32)
    return (x * 0.5 * intensidade).astype(np.float32)


def boom(intensidade=1.0, semente=0):
    m = int(0.7 * SR)
    rng = np.random.default_rng(semente)
    tt = np.arange(m) / SR
    ruido = _lp(rng.normal(0, 1, m), 900) * np.exp(-tt * 6)
    grave = np.sin(2 * np.pi * (35 + 60 * np.exp(-tt * 20)) * tt) * np.exp(-tt * 7)
    return (0.5 * ruido + 0.6 * grave) * 0.5 * intensidade


def raio(intensidade=1.0, semente=0):
    """Raio: estalo agudo seguido de trovão grave rolando."""
    m = int(1.4 * SR)
    rng = np.random.default_rng(semente)
    tt = np.arange(m) / SR
    r = rng.normal(0, 1, m)
    estalo = (r - _lp(r, 2500)) * np.exp(-tt * 38)
    trovao = _lp(r, 380) * np.exp(-tt * 2.6) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * tt))
    grave = np.sin(2 * np.pi * (42 + 30 * np.exp(-tt * 9)) * tt) * np.exp(-tt * 3.5)
    return (0.55 * estalo + 1.3 * trovao + 0.5 * grave) * 0.45 * intensidade


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


SONS = {"boom": boom, "raio": raio, "batida": batida, "chute": chute, "rede": rede, "defesa": defesa, "fora": fora,
        "glitch": lambda i, k: glitch(k), "tique": lambda i, k: tique(k), "whoosh": lambda i, k: whoosh(k),
        "ding": lambda i, k: ding(i > 1), "riser": lambda i, k: riser(i, k), "impacto": impacto,
        "coracao": coracao}


# Regra do canal: efeitos NUNCA competem com a voz. Cada efeito é limitado a este pico (≈ -14 dBFS)
# e ainda é abaixado enquanto a voz fala.
SFX_PICO = 0.2


def mixa(dur, falas, eventos, semente=0, ambiente=None, musica=0.55, silencios=()):
    """falas: [(t, audio)], eventos: [(t, tipo, intensidade)] -> estéreo float32.
    silencios: [(t0, t1)] trechos de suspense em que a música quase some (volta com a revelação em t1)."""
    n = int(dur * SR)
    voz = np.zeros(n + SR * 3, np.float32)
    for t, a in falas:
        i = int(t * SR)
        voz[i:i + len(a)] += a[: len(voz) - i]
    sfx = np.zeros_like(voz)
    for k, (t, tipo, inten) in enumerate(eventos):
        f = SONS[tipo]
        s = f(inten, k)
        pico = float(np.abs(s).max()) if len(s) else 0.0
        if pico > SFX_PICO:
            s = s * (SFX_PICO / pico)
        i = int(max(t, 0) * SR)
        sfx[i:i + len(s)] += s[: len(sfx) - i]
    mus = np.zeros_like(voz)
    mus[:n] = trilha(dur, semente=semente)
    corte = np.ones(len(mus), np.float32)
    for t0, t1 in silencios:
        i0, i1 = int(t0 * SR), int(t1 * SR)
        ramp = int(0.08 * SR)
        corte[i0:i1] = np.minimum(corte[i0:i1], 0.12)
        corte[max(i0 - ramp, 0):i0] = np.minimum(corte[max(i0 - ramp, 0):i0], np.linspace(1, 0.12, i0 - max(i0 - ramp, 0)))
    mus *= corte
    amb = np.zeros_like(voz)
    if ambiente is not None:
        amb[: min(n, len(ambiente))] = ambiente[:n]
    env = np.convolve(np.abs(voz), np.ones(4800) / 4800, "same")
    duck = 1 - 0.6 * np.clip(env / 0.05, 0, 1)
    mix = voz * 1.0 + sfx * (1.0 - 0.5 * np.clip(env / 0.05, 0, 1)) + mus * duck * musica + amb * (0.6 + 0.4 * duck)
    mix = mix[:n]
    fade = int(0.25 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix * 1.1) * 0.95
    return np.stack([mix, mix], 1).astype(np.float32)
