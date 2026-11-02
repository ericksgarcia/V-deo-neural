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
  4. emenda         o fim cola no começo (mesmo fundo, sem silêncio) para a pessoa rever sem perceber;
  5. som            música do dono presente e BAIXA (dB contra a voz), sem som morto, sem estouro, ritmo da narração
                    (geral e por cena: pega TTS que pulou/repetiu), nível igual no fim e no começo (loop);
  6. contraste      brilho do fundo atrás do cartão e da legenda (medido em cada quadro, já com o escurecimento automático);
  7. ortografia     palavras fora do dicionário pt-BR na tela e na legenda (pyspellchecker);
  8. post           legenda (tamanho, pergunta do CTA repetida, hashtags), capa gerada e visível na grade do perfil;
  9. integridade    áudio e vídeo com a mesma duração, imagem parada, tamanho do arquivo.
O dono não revisa antes de postar (02/nov/2026): o que pode ser medido é medido aqui, e o resto vai para os analistas Claude.
Depois monta o pacote .cache/luz/<slug>/revisao/ (imagens.jpg, quadros_N.jpg com a interface do TikTok em vermelho,
frases_N.jpg com cada frase inteira, capa.jpg, emenda.jpg, som.png e roteiro.txt) para os analistas Claude
(.claude/agents/analista-*.md): fatos, imagens, tela, som e post.
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


# ---------------------------------------------------------------- 5. som
def _audio_mono(mp4, sr=16000):
    import numpy as np
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.float32), sr


def som(rot, rend, mp4, pasta):
    """O dono não ouve antes de postar (02/nov): o que dá para medir do som, medimos. Música baixa debaixo da voz, sem
    buraco de silêncio, sem estouro, narração no ritmo certo (o TTS às vezes pula ou repete trecho) e loop sem pulo."""
    import numpy as np
    out, au = [], rend.get("audio") or {}
    if not au.get("musica"):
        out.append(("FALHA", "vídeo sem a música de fundo do dono (luz_da_palavra/musica/trilha.m4a)"))
    else:
        sob, pau = au.get("musica_sob_voz_db"), au.get("musica_pausa_db")
        if sob is None or sob > -16:
            out.append(("FALHA", f"música alta demais debaixo da fala ({sob} dB da voz; máx. -16): atrapalha a narração"))
        elif sob > -17.5:
            out.append(("AVISO", f"música um pouco alta debaixo da fala ({sob} dB da voz; ideal -18 a -26)"))
        elif sob < -34:
            out.append(("AVISO", f"música quase inaudível debaixo da fala ({sob} dB da voz)"))
        if pau is not None and pau > -12:
            out.append(("FALHA", f"música alta demais nas pausas ({pau} dB da voz; máx. -12)"))
        if au.get("musica_presente_pct", 100) < 95:
            out.append(("FALHA", f"música some em parte do vídeo (presente em {au['musica_presente_pct']}%)"))
    x, sr = _audio_mono(mp4)
    h = sr // 20
    fr = 20 * np.log10(np.sqrt(np.mean(x[: len(x) // h * h].reshape(-1, h) ** 2, 1)) + 1e-9)
    mudo, maior = 0, 0
    for v in fr:
        mudo = mudo + 1 if v < -50 else 0
        maior = max(maior, mudo)
    if maior * 0.05 >= 1.0:
        out.append(("FALHA", f"{maior * 0.05:.1f} s de silêncio total no meio do vídeo (som morto)"))
    if np.mean(np.abs(x) > 0.99) > 1e-4:
        out.append(("FALHA", "áudio estourado (clipping) no arquivo final"))
    # narração: ritmo geral e por cena (cena muito mais longa/curta que o texto = TTS pulou, repetiu ou travou)
    voz_arq = os.path.join(pasta, "voz_final.npy")
    if os.path.exists(voz_arq):
        v = np.load(voz_arq)
        vsr = rend.get("voz_sr", 48000)
        hv = vsr // 20
        ev = np.sqrt(np.mean(v[: len(v) // hv * hv].reshape(-1, hv) ** 2, 1))
        fala_s = float(np.sum(ev > 0.02)) * 0.05
        n = sum(len(limpa(c["fala"]).split()) for c in rot["cenas"])
        taxa = n / max(fala_s, 0.1)
        if not 1.9 <= taxa <= 4.2:
            out.append(("FALHA", f"narração a {taxa:.1f} palavras por segundo de fala (normal 2,2-3,8): voz arrastada, "
                                 "corrida ou com trecho faltando"))
        buraco, maior = 0, 0
        for e in ev:
            buraco = buraco + 1 if e < 0.01 else 0
            maior = max(maior, buraco)
        if maior * 0.05 > 1.6:
            out.append(("AVISO", f"pausa de {maior * 0.05:.1f} s dentro da narração (normal até 1,2 s)"))
        razoes = []
        for i, (c, (a, b, fa, fb)) in enumerate(zip(rot["cenas"], rend["tempos"])):
            letras = len(limpa(c["fala"]).replace(" ", ""))
            if letras >= 12:
                razoes.append((i, (fb - fa) / letras))
        if len(razoes) >= 4:
            med = float(np.median([r for _, r in razoes]))
            for i, r in razoes:
                if r > med * 1.9 or r < med * 0.45:
                    out.append(("AVISO", f"cena {i}: tempo de fala {r / med:.1f}x o normal para o tamanho do texto "
                                         "(conferir se o TTS repetiu, pulou ou alongou algo)"))
    if rot.get("emenda"):                             # o fim e o começo do som precisam ter o mesmo nível (loop)
        a0 = 20 * np.log10(np.sqrt(np.mean(x[: int(0.3 * sr)] ** 2)) + 1e-9)
        a1 = 20 * np.log10(np.sqrt(np.mean(x[-int(0.3 * sr):] ** 2)) + 1e-9)
        if abs(a0 - a1) > 9:
            out.append(("AVISO", f"nível do som no fim ({a1:.0f} dB) e no começo ({a0:.0f} dB) muito diferentes: o loop pula"))
    resumo = (f"música {au.get('musica_sob_voz_db')} dB sob a voz, {au.get('musica_pausa_db')} dB nas pausas, "
              f"presente {au.get('musica_presente_pct')}%")
    return out, resumo


# ---------------------------------------------------------------- 6. contraste
def contraste(rot, rend):
    """Brilho do fundo (0-255, percentil 75) atrás do cartão e da legenda, medido no render já escurecido."""
    out, piores = [], []
    for k, m in (rend.get("contraste") or {}).items():
        for el, lim_f, lim_a in (("cartao", 175, 145), ("legenda", 165, 135)):
            v = m.get(el, 0)
            if v > lim_f:
                out.append(("FALHA", f"cena {k}: fundo claro demais atrás do {el} (brilho {v:.0f}; máx. {lim_f}): ilegível"))
            elif v > lim_a:
                out.append(("AVISO", f"cena {k}: fundo claro atrás do {el} (brilho {v:.0f}): leitura difícil"))
            piores.append(v)
    if not rend.get("contraste"):
        out.append(("AVISO", "render sem medida de contraste (gerado com versão antiga)"))
    return out, f"pior brilho atrás do texto {max(piores) if piores else '?'}"


# ---------------------------------------------------------------- 7. ortografia
def ortografia(rot):
    """Palavras fora do dicionário pt-BR no que vai para a tela e para o post (o analista-tela julga cada uma)."""
    try:
        from spellchecker import SpellChecker
    except ImportError:
        return [("AVISO", "pyspellchecker não instalado (pip install pyspellchecker): ortografia só pelo analista Claude")], ""
    sc = SpellChecker(language="pt")
    textos = [c["fala"] for c in rot["cenas"]] + [c.get("card", "") for c in rot["cenas"]] + \
             [c.get("cta", "") for c in rot["cenas"]] + rot["titulo"] + [re.sub(r"#\S+", "", rot["legenda"])]
    nomes = set()
    for f in rot.get("fatos", []) + [rot.get("ref", "")]:
        nomes |= {w.lower() for w in re.findall(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+", f)}
    comuns = {"pra", "pro", "tá", "né", "comenta", "comente", "amém", "aleluia", "ok"}
    palavras_ = set()
    for t in textos:
        for w in re.findall(r"[A-Za-zÀ-ÿ]+(?:-[A-Za-zÀ-ÿ]+)*", limpa(t)):
            for parte in w.lower().split("-"):
                if len(parte) > 2 and not parte.isupper():
                    palavras_.add(parte)
    desconhecidas = sorted(w for w in sc.unknown(palavras_) if w not in nomes and w not in comuns)
    out = [("AVISO", f"fora do dicionário (conferir grafia): {', '.join(desconhecidas)}")] if desconhecidas else []
    return out, f"{len(palavras_)} palavras conferidas"


# ---------------------------------------------------------------- 8. post (legenda, CTA, capa)
GENERICAS = {"#jesus", "#biblia", "#fe", "#deus", "#evangelho", "#fy", "#fyp", "#foryou", "#viral", "#cristao", "#gospel"}


def post(rot, rend):
    out = []
    leg = rot.get("legenda", "")
    if not leg.strip():
        return [("FALHA", "legenda do post vazia")], ""
    if len(leg) > 2200:
        out.append(("FALHA", f"legenda com {len(leg)} caracteres (TikTok aceita até 2200)"))
    tags = re.findall(r"#\w+", leg.lower())
    if not 3 <= len(tags) <= 8:
        out.append(("AVISO", f"{len(tags)} hashtags (ideal 3-8)"))
    if not [t for t in tags if t not in GENERICAS]:
        out.append(("AVISO", "só hashtags genéricas: inclua 1-2 do episódio"))
    if re.search(r"curt[ae] e comenta|comenta am[eé]m", leg.lower()):
        out.append(("FALHA", "legenda com CTA genérico (\"curte e comenta amém\"): use a pergunta do episódio"))
    cta = [c for c in rot["cenas"] if c.get("cta")]
    if cta:
        chave = {w for w in re.findall(r"[a-zà-ÿ]{4,}", limpa(cta[0]["fala"]).lower())}
        tem = {w for w in re.findall(r"[a-zà-ÿ]{4,}", leg.lower())}
        if chave and len(chave & tem) / len(chave) < 0.5:
            out.append(("FALHA", "a legenda não repete a pergunta do CTA (a regra é repetir para puxar comentário)"))
    if "?" not in leg:
        out.append(("AVISO", "legenda sem pergunta"))
    if re.search(r"https?://|www\.", leg):
        out.append(("AVISO", "link na legenda (o TikTok não deixa clicar e pode reduzir alcance)"))
    capa = rend.get("capa")
    if not capa or not os.path.exists(capa):
        out.append(("FALHA", "capa não gerada (saida/luz/<slug>_capa.jpg)"))
    else:
        tit = rend["layout"].get("titulo")
        # a grade do perfil mostra o meio em 3:4 (y 240-1680): o título da capa precisa caber ali
        if not tit or tit[1] < 240 or tit[3] > 1680:
            out.append(("FALHA", f"título da capa fora da área que aparece na grade do perfil: {tit}"))
    return out, f"{len(leg)} caracteres, {len(tags)} hashtags, capa em {rend.get('capa_t')} s"


# ---------------------------------------------------------------- 9. integridade
def integridade(mp4):
    out = []
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", mp4],
                                     capture_output=True, text=True, check=True).stdout)
    durs = {s["codec_type"]: float(s.get("duration", 0)) for s in info["streams"]}
    if abs(durs.get("video", 0) - durs.get("audio", 0)) > 0.2:
        out.append(("FALHA", f"vídeo {durs.get('video', 0):.2f} s e áudio {durs.get('audio', 0):.2f} s com durações diferentes"))
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", mp4, "-vf", "freezedetect=n=0.0008:d=2.5", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    for m in re.finditer(r"freeze_start: ([\d.]+)", r.stderr):
        out.append(("AVISO", f"imagem parada a partir de {float(m.group(1)):.1f} s (vídeo pode parecer travado)"))
    tam = os.path.getsize(mp4) / 1e6
    if tam > 250:
        out.append(("FALHA", f"arquivo de {tam:.0f} MB (limite prático 250 MB)"))
    return out, f"{tam:.1f} MB"


# ---------------------------------------------------------------- pacote para os analistas Claude
def _quadro(mp4, t, do_fim=False):
    pos = ["-sseof", f"-{t:.2f}"] if do_fim else ["-ss", f"{t:.2f}"]
    p = subprocess.run(["ffmpeg", "-v", "error", *pos, "-i", mp4, "-frames:v", "1", "-f", "image2pipe",
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


def pacote_revisao(rot, mp4, rend, pasta, rascunho=False):
    """Monta em .cache/luz/<slug>/revisao/ o material que os analistas Claude leem (sem nenhuma API externa)."""
    dest = os.path.join(pasta, "revisao")
    os.makedirs(dest, exist_ok=True)
    tempos, dur = rend["tempos"], rend["dur"]
    # imagens de fundo, com o número e a fala de cada uma
    usos = {}
    for c in rot["cenas"]:
        usos.setdefault(c["img"], []).append(limpa(c["fala"]))
    sys.path.insert(0, AQUI)
    import gerar                      # o mosaico mostra a foto COM o tratamento de cor, como aparece no vídeo
    trat = (lambda im: im) if rascunho else gerar.tratamento
    ims = [_rotulo(trat(Image.open(a).convert("RGB")).resize((432, 768)), f"IMAGEM {i}") for i, a in enumerate(rend["imagens"])]
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
    # frases inteiras: quadro no FIM de cada fala (legenda completa) para conferir ortografia frase por frase
    inteiras = []
    for i, (c, (a, b, fa, fb)) in enumerate(zip(rot["cenas"], tempos)):
        t = max(fa, min(fb + 0.05, b - 0.12, dur - 0.1))
        im = _quadro(mp4, t).resize((360, 640))
        inteiras.append(_rotulo(im, f"cena {i} fim · {t:.1f}s"))
    for k in range(0, len(inteiras), 8):
        _mosaico(inteiras[k:k + 8], 4, os.path.join(dest, f"frases_{k // 8 + 1}.jpg"))
    # capa (quadro que o TikTok usa) + grade do perfil (recorte 3:4 do meio)
    if rend.get("capa") and os.path.exists(rend["capa"]):
        capa = Image.open(rend["capa"]).convert("RGB")
        grade = capa.crop((0, 240, W, 1680)).resize((540, 720))
        m = Image.new("RGB", (540 + 20 + 405, 720), (30, 30, 30))
        m.paste(capa.resize((405, 720)), (0, 0))
        m.paste(grade, (425, 0))
        _rotulo(m, f"CAPA ({rend.get('capa_t')} s) · lado direito: como aparece na grade do perfil (3:4)").save(
            os.path.join(dest, "capa.jpg"), quality=90)
    # emenda: último quadro x primeiro quadro, lado a lado
    ult = _quadro(mp4, 0.1, do_fim=True).resize((360, 640))
    pri = _quadro(mp4, 0).resize((360, 640))
    m = Image.new("RGB", (740, 640), (30, 30, 30))
    m.paste(_rotulo(ult, "ÚLTIMO quadro"), (0, 0))
    m.paste(_rotulo(pri, "PRIMEIRO quadro"), (380, 0))
    m.save(os.path.join(dest, "emenda.jpg"), quality=88)
    # som: forma de onda + espectrograma (o analista-som não ouve, mas lê a figura)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4, "-filter_complex",
                    "[0:a]aformat=channel_layouts=mono,showwavespic=s=1600x300:colors=0xffd05c[w];"
                    "[0:a]aformat=channel_layouts=mono,showspectrumpic=s=1600x500:legend=1:scale=log[s];"
                    "[w]scale=1600:300[w2];[s]scale=1600:-2[s2];[w2][s2]vstack=inputs=2:shortest=0",
                    "-frames:v", "1", os.path.join(dest, "som.png")], capture_output=True)
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
        ("5. som (música e narração)", lambda: som(rot, rend, mp4, pasta)),
        ("6. contraste do texto", lambda: contraste(rot, rend)),
        ("7. ortografia", lambda: ortografia(rot)),
        ("8. post (legenda, CTA, capa)", lambda: post(rot, rend)),
        ("9. integridade do arquivo", lambda: integridade(mp4)),
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
    dest = pacote_revisao(rot, mp4, rend, pasta, rascunho)
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
