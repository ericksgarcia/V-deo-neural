"""Transcrição local (faster-whisper) e alinhamento das palavras do roteiro com a narração.

Grátis e offline (depois de baixar o modelo uma vez). Usado para:
  - sincronizar a legenda palavra a palavra com a voz;
  - conferir se a voz falou o que estava escrito (ex.: "32" lido como "três ponto dois").
"""
import difflib
import re
import subprocess

import numpy as np

_MODELO = {}


def modelo(nome="small"):
    if nome not in _MODELO:
        from faster_whisper import WhisperModel
        _MODELO[nome] = WhisperModel(nome, device="cpu", compute_type="int8")
    return _MODELO[nome]


def audio16k(caminho):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32)


def para16k(x, sr):
    if sr == 16000:
        return x.astype(np.float32)
    t = np.arange(int(len(x) * 16000 / sr)) * sr / 16000
    return np.interp(t, np.arange(len(x)), x).astype(np.float32)


def transcreve(audio, nome="small", idioma=None):
    """audio: caminho ou array 16 kHz -> ([(ini, fim, frase)], [(ini, fim, palavra)], idioma)."""
    x = audio16k(audio) if isinstance(audio, str) else audio
    segs, info = modelo(nome).transcribe(x, language=idioma, word_timestamps=True)
    frases, palavras = [], []
    for s in segs:
        frases.append((s.start, s.end, s.text.strip()))
        palavras += [(w.start, w.end, w.word.strip()) for w in (s.words or [])]
    return frases, palavras, info.language


def normaliza(s):
    s = s.lower()
    s = re.sub(r"[^\wà-ú\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def alinha(texto, falado, palavras_whisper, dur):
    """Tempo de cada palavra do roteiro (como aparece na legenda).

    texto: frase do roteiro ("Geração 32: ...");  falado: versão enviada à voz ("Geração trinta e dois: ...").
    Usa os tempos do Whisper quando a contagem bate; senão distribui pelo tamanho das palavras."""
    from .audio import falavel
    visiveis = texto.split()
    partes = [len(falavel(p).split()) or 1 for p in visiveis]
    ws = [w for w in palavras_whisper if normaliza(w[2])]
    if ws and abs(len(ws) - sum(partes)) <= max(1, sum(partes) // 12):
        out, k = [], 0
        for p, n in zip(visiveis, partes):
            a = ws[min(k, len(ws) - 1)]
            b = ws[min(k + n - 1, len(ws) - 1)]
            out.append((a[0], b[1], p))
            k += n
        return out
    ini = ws[0][0] if ws else 0.0
    fim = ws[-1][1] if ws else dur
    pesos = np.array([len(p) + 2 for p in visiveis], float)
    cs = np.concatenate([[0], np.cumsum(pesos)]) / pesos.sum() * (fim - ini) + ini
    return [(cs[i], cs[i + 1], p) for i, p in enumerate(visiveis)]


_IGUAIS = {"para": "pra", "sem": "cem", "cento": "cem", "ia": "ia", "é": "e"}


def _canon(s):
    from .audio import falavel
    return " ".join(_IGUAIS.get(w, w) for w in normaliza(falavel(s)).split())


def confere(falado, transcrito):
    """Semelhança 0-1 entre o que devia ser dito e o que o Whisper ouviu (ignora homófonos e
    números escritos em algarismos ou por extenso)."""
    return difflib.SequenceMatcher(None, _canon(falado), _canon(transcrito)).ratio()
