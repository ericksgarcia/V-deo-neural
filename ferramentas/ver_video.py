#!/usr/bin/env python3
""""Ver" um vídeo sem API paga: quadros, mosaico, cortes de cena e transcrição local (Whisper).

Gera numa pasta:
  quadros/          um quadro a cada N segundos (nome = segundo do quadro)
  mosaico.jpg       todos os quadros numa imagem, para um analista (humano ou Claude) olhar
  cortes.txt        instantes de troca de cena (detecção de cena do ffmpeg)
  transcricao.txt   fala com tempo de cada trecho (faster-whisper, roda local, grátis)
  palavras.json     tempo de cada palavra (usado para conferir sincronia de legenda)
  resumo.md         tudo junto, pronto para os analistas de .claude/agents/

Uso:
  python ferramentas/ver_video.py video.mp4 [--saida pasta] [--intervalo 2] [--modelo small]
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from neuralab.fala import transcreve  # noqa: E402


def roda(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def quadros(video, pasta, intervalo):
    q = os.path.join(pasta, "quadros")
    os.makedirs(q, exist_ok=True)
    for f in os.listdir(q):
        os.remove(os.path.join(q, f))
    roda(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps=1/{intervalo},scale=360:-2",
          os.path.join(q, "q_%03d.jpg")], check=True)
    nomes = sorted(os.listdir(q))
    for k, n in enumerate(nomes):  # renomeia com o segundo correspondente
        os.rename(os.path.join(q, n), os.path.join(q, f"t{k * intervalo:06.1f}s.jpg"))
    cols = 6
    linhas = (len(nomes) + cols - 1) // cols
    roda(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", os.path.join(q, "t*.jpg"),
          "-filter_complex", f"tile={cols}x{linhas}:padding=4", "-frames:v", "1",
          os.path.join(pasta, "mosaico.jpg")], check=True)
    return len(nomes)


def cortes(video, limiar=0.3):
    r = roda(["ffmpeg", "-i", video, "-vf", f"select='gt(scene,{limiar})',showinfo", "-vsync", "vfr",
              "-f", "null", "-"])
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def duracao(video):
    r = roda(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video], check=True)
    return float(r.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--saida")
    ap.add_argument("--intervalo", type=float, default=2.0)
    ap.add_argument("--modelo", default="small", help="modelo do Whisper: tiny, base, small, medium")
    ap.add_argument("--sem-fala", action="store_true")
    a = ap.parse_args()
    pasta = a.saida or os.path.splitext(a.video)[0] + "_visto"
    os.makedirs(pasta, exist_ok=True)

    dur = duracao(a.video)
    n = quadros(a.video, pasta, a.intervalo)
    cs = cortes(a.video)
    with open(os.path.join(pasta, "cortes.txt"), "w") as f:
        f.write("\n".join(f"{t:.2f}" for t in cs) + "\n")
    linhas = [f"# {os.path.basename(a.video)}", "", f"- duração: {dur:.1f}s",
              f"- quadros: {n} (1 a cada {a.intervalo:g}s) em `quadros/`, mosaico em `mosaico.jpg`",
              f"- cortes de cena: {', '.join(f'{t:.1f}s' for t in cs) or 'nenhum detectado'}", ""]
    if not a.sem_fala:
        frases, palavras, idioma = transcreve(a.video, a.modelo)
        with open(os.path.join(pasta, "transcricao.txt"), "w") as f:
            f.write("\n".join(f"{i:6.1f}-{e:6.1f}  {t}" for i, e, t in frases) + "\n")
        with open(os.path.join(pasta, "palavras.json"), "w") as f:
            json.dump(palavras, f, ensure_ascii=False)
        fala = sum(e - i for i, e, _ in frases)
        nw = len(palavras)
        linhas += [f"- idioma: {idioma} · {nw} palavras · {nw / max(dur, 1) * 60:.0f} palavras/min · "
                   f"fala ocupa {fala / dur:.0%} do vídeo", "", "## Transcrição", ""]
        linhas += [f"- `{i:5.1f}s` {t}" for i, e, t in frases]
    with open(os.path.join(pasta, "resumo.md"), "w") as f:
        f.write("\n".join(linhas) + "\n")
    print("\n".join(linhas))
    print(f"\n-> {pasta}")


if __name__ == "__main__":
    main()
