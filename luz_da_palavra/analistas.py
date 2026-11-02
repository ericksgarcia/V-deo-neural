"""Analistas do Luz da Palavra: revisam CADA parte do vídeo pronto antes de ele ser aprovado (pedido do dono, nov/2026).

    python luz_da_palavra/analistas.py luz_da_palavra/roteiros/ep03_sussurro.json      # revisa o vídeo já renderizado
    python luz_da_palavra/analistas.py <roteiro> --video outro.mp4                     # revisa outro arquivo

O gerador chama isto sozinho no fim; com qualquer FALHA o vídeo NÃO é aprovado e o tema não é registrado.
Regra do dono (nov/2026): o Gemini serve SÓ para a voz (TTS). Nenhum analista chama API externa.

Analistas automáticos (código, aqui):
  1. técnico        formato 1080x1920/30 fps, duração, quadros pretos, volume (LUFS) e pico;
  2. zona segura    nenhum texto embaixo dos ícones do TikTok (coluna da direita), da faixa de baixo nem do topo
                    (caixas reais de cada elemento, gravadas pelo gerador em .cache/luz/<slug>/render.json);
  3. ritmo          velocidade da fala por cena, tempo de leitura dos cartões, cenas curtas demais;
  4. emenda         o fim cola no começo (mesmo fundo, sem silêncio) para a pessoa rever sem perceber.
Depois monta o pacote .cache/luz/<slug>/revisao/ (imagens.jpg, quadros_N.jpg com a interface do TikTok em vermelho,
roteiro.txt) para os analistas Claude (.claude/agents/analista-*.md): fatos bíblicos, imagens e tela.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
W, H = 1080, 1920
# Interface do TikTok sobre um vídeo 1080x1920 (com folga): (x0, y0, x1, y1)
ZONAS = {
    "ícones do TikTok (coluna da direita)": (940, 760, W, 1580),
    "nome/legenda/música do TikTok (faixa de baixo)": (0, 1500, W, H),
    "abas do topo do TikTok": (0, 0, W, 150),
}
MARGEM_LADO = 60


def limpa(t):
    return t.replace("*", "")


# ---------------------------------------------------------------- 1. técnico
def tecnico(mp4, rot):
    out = []
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", mp4],
                                     capture_output=True, text=True, check=True).stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    if not v or (int(v["width"]), int(v["height"])) != (W, H):
        out.append(("FALHA", f"resolução {v and v['width']}x{v and v['height']} (precisa 1080x1920)"))
    elif v["codec_name"] != "h264" or v.get("pix_fmt") != "yuv420p":
        out.append(("FALHA", f"vídeo {v['codec_name']}/{v.get('pix_fmt')} (precisa h264/yuv420p)"))
    if v and abs(eval(v["r_frame_rate"]) - 30) > 0.5:
        out.append(("AVISO", f"fps {v['r_frame_rate']} (padrão 30)"))
    if not a:
        out.append(("FALHA", "sem áudio"))
    if dur > 60:
        out.append(("FALHA", f"duração {dur:.1f} s (teto 60 s)"))
    elif not 40 <= dur <= 55:
        out.append(("AVISO", f"duração {dur:.1f} s (alvo 40-55 s)"))
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", mp4, "-vf", "blackdetect=d=0.25:pix_th=0.06", "-an",
                        "-f", "null", "-"], capture_output=True, text=True)
    r2 = subprocess.run(["ffmpeg", "-v", "info", "-i", mp4, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"],
                        capture_output=True, text=True)
    for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr):
        out.append(("FALHA", f"quadro preto de {float(m.group(1)):.1f}s a {float(m.group(2)):.1f}s"))
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", r2.stderr)
    pico = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r2.stderr)
    if lufs:
        i = float(lufs[-1])
        if not -20 <= i <= -10:
            out.append(("FALHA" if not -24 <= i <= -8 else "AVISO", f"volume integrado {i:.1f} LUFS (alvo -16 a -12)"))
    if pico and float(pico[-1]) > -0.3:
        out.append(("AVISO", f"pico {float(pico[-1]):.1f} dBFS (risco de estourar)"))
    info_txt = f"{dur:.1f} s, {lufs[-1] if lufs else '?'} LUFS, pico {pico[-1] if pico else '?'} dBFS"
    return out, info_txt


# ---------------------------------------------------------------- 2. zona segura
def zona_segura(layout):
    out = []
    for nome, (x0, y0, x1, y1) in sorted(layout.items()):
        for zona, (a0, b0, a1, b1) in ZONAS.items():
            if x0 < a1 and x1 > a0 and y0 < b1 and y1 > b0:
                out.append(("FALHA", f"{nome} (x {x0}-{x1}, y {y0}-{y1}) fica embaixo de: {zona}"))
        if x0 < MARGEM_LADO or x1 > W - MARGEM_LADO:
            out.append(("AVISO", f"{nome} encosta na borda (x {x0}-{x1})"))
    return out, ", ".join(f"{k} y{v[1]}-{v[3]}" for k, v in sorted(layout.items(), key=lambda kv: kv[1][1]))


# ---------------------------------------------------------------- 3. ritmo
def ritmo(rot, tempos):
    out = []
    for i, (c, (a, b, fa, fb)) in enumerate(zip(rot["cenas"], tempos)):
        n = len(limpa(c["fala"]).split())
        fala = max(fb - fa, 0.01)
        if n / fala > 4.2:
            out.append(("AVISO", f"cena {i}: {n / fala:.1f} palavras/s (corrido demais para ler)"))
        if c.get("card"):
            visivel = min(b, a + 2.5) - a
            if visivel < 0.9:
                out.append(("FALHA", f"cena {i}: cartão '{c['card']}' fica só {visivel:.1f}s na tela"))
        if b < 1e8 and b - a < 0.8:
            out.append(("AVISO", f"cena {i}: dura só {b - a:.1f}s"))
    return out, f"{len(tempos)} cenas"


# ---------------------------------------------------------------- 4. emenda
def emenda(rot, rend, mp4):
    """O vídeo termina no meio da frase que a 1ª fala completa, sem respiro e com o mesmo fundo do 1º quadro."""
    if not rot.get("emenda"):
        return [("FALHA", "roteiro sem \"emenda\" (a última fala precisa emendar na 1ª)")], ""
    out = []
    dif = rend.get("emenda_diff")
    if dif is not None and dif > 10:
        out.append(("FALHA", f"fundo do último quadro difere do 1º (diferença {dif:.1f}; máx. 10): o recomeço vira corte"))
    a, b, fa, fb = rend["tempos"][-1]
    sobra = rend["dur"] - fb
    if sobra > 0.45:
        out.append(("FALHA", f"{sobra:.2f} s de silêncio depois da última palavra (máx. 0,45): o loop fica perceptível"))
    return out, f"diferença de fundo {dif if dif is None else round(dif, 1)}, sobra {sobra:.2f} s · \"{rot['emenda']}\""


# ---------------------------------------------------------------- pacote para os analistas Claude
def _quadro(mp4, t):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", mp4, "-frames:v", "1", "-f", "image2pipe",
                        "-vcodec", "png", "-"], capture_output=True, check=True)
    return Image.open(io.BytesIO(p.stdout)).convert("RGB")


def _rotulo(im, txt):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 34), fill=(0, 0, 0))
    d.text((8, 6), txt, fill=(255, 255, 0), font=ImageFont.load_default(20))
    return im


def _mosaico(ims, colunas, destino):
    w, h = ims[0].size
    linhas = (len(ims) + colunas - 1) // colunas
    m = Image.new("RGB", (w * colunas, h * linhas), (30, 30, 30))
    for k, im in enumerate(ims):
        m.paste(im, ((k % colunas) * w, (k // colunas) * h))
    m.save(destino, quality=88)


def pacote_revisao(rot, mp4, rend, pasta):
    """Monta em .cache/luz/<slug>/revisao/ o material que os analistas Claude leem (sem nenhuma API externa)."""
    dest = os.path.join(pasta, "revisao")
    os.makedirs(dest, exist_ok=True)
    tempos, dur = rend["tempos"], rend["dur"]
    # imagens de fundo, com o número e a fala de cada uma
    usos = {}
    for c in rot["cenas"]:
        usos.setdefault(c["img"], []).append(limpa(c["fala"]))
    ims = [_rotulo(Image.open(a).convert("RGB").resize((432, 768)), f"IMAGEM {i}") for i, a in enumerate(rend["imagens"])]
    _mosaico(ims, 4, os.path.join(dest, "imagens.jpg"))
    # quadros-chave: um por cena, com a interface do TikTok marcada em vermelho
    linhas, quadros = [], []
    rev = rot.get("revelacao")
    for i, (c, (a, b, fa, fb)) in enumerate(zip(rot["cenas"], tempos)):
        fim = min(b, dur - 0.1)
        t = min(fa + 0.75 * (min(fb, fim) - fa), a + 2.2) if c.get("card") else fa + 0.9 * (min(fb, fim) - fa)
        im = _quadro(mp4, t)
        cam = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(cam)
        for (x0, y0, x1, y1) in ZONAS.values():
            d.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(255, 0, 0, 255), width=6, fill=(255, 0, 0, 40))
        im = Image.alpha_composite(im.convert("RGBA"), cam).convert("RGB").resize((360, 640))
        quadros.append(_rotulo(im, f"cena {i} · {t:.1f}s"))
        esperado = [f"fala: {limpa(c['fala'])}"]
        if i == 0:
            esperado.append(f"título: {' / '.join(rot['titulo'])}")
        if c.get("card"):
            esperado.append(f"cartão: {c['card']}")
        if c.get("cta"):
            esperado.append(f"botão: {c['cta']}")
        if rev is not None and 0 < tempos[rev][0] - t <= 16 and i > 1:
            esperado.append("contagem 'A REVELAÇÃO VEM EM Ns' embaixo")
        linhas.append(f"cena {i} ({t:.1f}s, img {c['img']}): " + "; ".join(esperado))
    for k in range(0, len(quadros), 8):
        _mosaico(quadros[k:k + 8], 4, os.path.join(dest, f"quadros_{k // 8 + 1}.jpg"))
    texto = [f"REF: {rot['ref']}", f"TÍTULO: {' / '.join(rot['titulo'])}", "", "FATOS:"] + [f"- {f}" for f in rot["fatos"]]
    texto += ["", "FALAS (tempos reais):"] + [
        f"{i:2d} {a:5.1f}-{min(b, dur):5.1f}s img{c['img']} {limpa(c['fala'])}" + (f"  [cartão {c['card']}]" if c.get("card") else "")
        for i, (c, (a, b, _, _)) in enumerate(zip(rot["cenas"], tempos))]
    texto += ["", "PROMPTS DAS IMAGENS:"] + [f"{i}: {p}  | fala: {' / '.join(usos.get(i, ['(não usada)']))}"
                                            for i, p in enumerate(rot["imagens"])]
    texto += ["", "QUADROS-CHAVE (o que deve aparecer; vermelho = interface do TikTok):"] + linhas
    texto += ["", "LEGENDA DO POST:", rot["legenda"]]
    open(os.path.join(dest, "roteiro.txt"), "w", encoding="utf-8").write("\n".join(texto) + "\n")
    return dest


# ---------------------------------------------------------------- orquestra
def analisa(rot, mp4, pasta, rascunho=False):
    """Roda todos os analistas, imprime e grava o relatório; devolve o número de FALHA."""
    rend = json.load(open(os.path.join(pasta, "render.json")))
    tempos, dur = rend["tempos"], rend["dur"]
    times = [
        ("1. técnico", lambda: tecnico(mp4, rot)),
        ("2. zona segura (TikTok)", lambda: zona_segura(rend["layout"])),
        ("3. ritmo", lambda: ritmo(rot, tempos)),
        ("4. emenda (loop)", lambda: emenda(rot, rend, mp4)),
    ]
    linhas, falhas = [f"Analistas automáticos · {os.path.basename(mp4)}", ""], 0
    for nome, fn in times:
        try:
            probs, resumo = fn()
        except Exception as e:                               # analista que não rodou = não aprovado
            probs, resumo = [("FALHA", f"analista não conseguiu rodar: {e}")], ""
        nf = sum(1 for n, _ in probs if n == "FALHA")
        falhas += nf
        bloco = [f"{nome}: {'OK' if not probs else f'{nf} FALHA, {len(probs) - nf} AVISO'}"
                 + (f"  ({resumo})" if resumo else "")] + [f"    {n}: {m}" for n, m in probs]
        linhas += bloco
        print("\n".join(bloco), flush=True)
    dest = pacote_revisao(rot, mp4, rend, pasta)
    linhas += ["", "APROVADO nos automáticos" if not falhas else f"NÃO APROVADO: {falhas} FALHA",
               f"Pacote para os analistas Claude (fatos, imagens, tela): {dest}"]
    print(f"  -> {linhas[-2]}\n  {linhas[-1]}")
    with open(mp4[:-4] + "_analise.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
    return falhas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("--video")
    a = ap.parse_args()
    sys.path.insert(0, AQUI)
    import gerar
    gerar.carrega_chaves()
    rot = json.load(open(a.roteiro, encoding="utf-8"))
    mp4 = a.video or os.path.join(RAIZ, "saida", "luz", rot["slug"] + ".mp4")
    sys.exit(1 if analisa(rot, mp4, os.path.join(RAIZ, ".cache", "luz", rot["slug"])) else 0)


if __name__ == "__main__":
    main()
