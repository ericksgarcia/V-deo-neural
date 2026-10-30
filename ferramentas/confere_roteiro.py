#!/usr/bin/env python3
"""Confere o roteiro de um vídeo contra o guia `docs/ROTEIRO.md` (limites medíveis).

Uso:
  python gerar.py <tema> --so-roteiro > .cache/roteiro_<tema>.txt
  python ferramentas/confere_roteiro.py .cache/roteiro_<tema>.txt

Lê a saída de `--so-roteiro` (linhas "  N tipo fala [CARTÃO n]" e, depois de "legenda:", o texto do post).
Imprime FALHA (bloqueia), AVISO (revisar com o analista) ou ok. Código de saída 1 se houver FALHA.
"""
import re
import sys

PROIBIDAS = [
    r"mais votad", r"vira o pr[óo]ximo", r"pr[óo]ximo v[íi]deo", r"pr[óo]ximo epis[óo]dio", r"voc[êe] escolhe",
    r"\bvot(e|ar|a[çc][ãa]o|os)\b", r"qual voc[êe] quer ver", r"quer ver", r"comenta\s+(a|b|ab|\d+)\b",
    r"motor mais r[áa]pido", r"ganha um motor", r"vai ganhar",
]
RE_NUM = re.compile(r"\d[\d.,]*%?")
# números por extenso (de 11 para cima, e decimais): escapavam da contagem e saem pequenos na legenda
_EXT = (r"onze|doze|treze|catorze|quatorze|quinze|dezesseis|dezessete|dezoito|dezenove|vinte|trinta|quarenta|"
        r"cinquenta|sessenta|setenta|oitenta|noventa|cento|duzentos|trezentos|quatrocentos|quinhentos|seiscentos|"
        r"setecentos|oitocentos|novecentos|mil")
RE_EXT = re.compile(rf"(?i)\b\w+\s+v[íi]rgula\s+\w+\b|\b(?:{_EXT})(?:\s+(?:e\s+)?(?:{_EXT}|um|uma|dois|duas|três|quatro|cinco|seis|sete|oito|nove|"
                    rf"dez))*(?:\s+v[íi]rgula\s+\w+)?\b")
PROMESSA = re.compile(r"(?i)\bno (fim|final)\b|at[ée] o (fim|final)|teste final|[úu]ltimo teste|no teste")
PAUSA = {"short": 0.15, "long": 0.55}
PAL_S = 2.6   # palavras por segundo (README/NARRACAO)


def le(arq):
    txt = open(arq, encoding="utf-8").read() if arq != "-" else sys.stdin.read()
    cenas, legenda, na_legenda = [], [], False
    for ln in txt.splitlines():
        if ln.strip() == "legenda:":
            na_legenda = True
            continue
        if na_legenda:
            legenda.append(ln)
            continue
        m = re.match(r"^\s+(\d+)\s+(\S+)\s+(.*)$", ln)
        if m:
            fala, cartao = m.group(3), None
            c = re.search(r"\s+\[CART[ÃA]O (\d+)\]\s*$", fala)
            if c:
                cartao, fala = int(c.group(1)), fala[:c.start()]
            cenas.append({"tipo": m.group(2), "fala": fala, "cartao": cartao})
    return cenas, "\n".join(legenda).strip()


def limpa(f):
    return re.sub(r"<(short|long) pause>", " ", f)


def palavras(f):
    return re.findall(r"[\wÀ-ÿ]+(?:[-'][\wÀ-ÿ]+)*", limpa(f))


def dados(f):
    """Números de dado numa fala, sem contar o número da geração ('Geração 47', 'ger. 47')."""
    sem = re.sub(rf"(?i)\b(gera[çc][ãa]o|ger\.?)\s*(\d+|(?:(?:{_EXT}|e|um|dois|três|quatro|cinco|seis|sete|oito|nove)\s*)+)",
                 " ", limpa(f))
    achados = RE_NUM.findall(sem) + RE_EXT.findall(sem)
    return achados[: (len(achados) + 1) // 2] if len(achados) > 1 else achados   # "de X para Y" conta como 1 dado


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    cenas, legenda = le(sys.argv[1])
    if not cenas:
        sys.exit("nenhuma cena encontrada: use a saída de `python gerar.py <tema> --so-roteiro`")
    res = []   # (nivel, texto)

    def r(nivel, txt):
        res.append((nivel, txt))

    # ---- tamanho e duração
    pal = [len(palavras(c["fala"])) for c in cenas]
    total = sum(pal)
    n_short = sum(c["fala"].count("<short pause>") for c in cenas)
    n_long = sum(c["fala"].count("<long pause>") for c in cenas)
    dur = total / PAL_S + n_short * PAUSA["short"] + n_long * PAUSA["long"] + 0.22 * len(cenas)
    ini, t = [], 0.0
    for c, p in zip(cenas, pal):
        ini.append(t)
        t += p / PAL_S + c["fala"].count("<short pause>") * 0.15 + c["fala"].count("<long pause>") * 0.55 + 0.22
    print(f"cenas: {len(cenas)} · palavras: {total} · duração estimada: {dur:.0f} s (confirme com --so-voz)")
    if total > 150:
        r("FALHA", f"{total} palavras (máx 150; alvo 100–140)")
    elif total > 140:
        r("AVISO", f"{total} palavras (alvo 100–140)")
    elif total < 90:
        r("AVISO", f"{total} palavras: muito curto? (alvo 100–140)")
    if dur > 62:
        r("FALHA", f"duração estimada {dur:.0f} s (teto 60 s)")
    elif dur > 56:
        r("AVISO", f"duração estimada {dur:.0f} s (alvo 40–55 s)")
    if len(cenas) > 16:
        r("AVISO", f"{len(cenas)} cenas (muitas; funda cenas)")

    # ---- descobertas
    cartoes = {c["cartao"] for c in cenas if c["cartao"]}
    if len(cartoes) > 3:
        r("FALHA", f"{len(cartoes)} cartões de descoberta (máx 3)")
    if not cartoes:
        r("AVISO", "nenhum cartão de descoberta detectado")

    # ---- gancho
    g = cenas[0]["fala"]
    gp = len(palavras(g))
    if gp > 16:
        r("FALHA", f"gancho com {gp} palavras (máx 16)")
    if not re.match(r"^\W*\w*ei\b", limpa(g).strip(), re.I):
        r("FALHA", "gancho não começa com verbo em 1ª pessoa terminado em -ei (Tirei, Treinei, Coloquei…): precisa para o laço")
    if not dados(g) and not re.search(r"(?i)\b(nenhum|nenhuma|ninguém|só um|só uma|uma só|nem se mexe)\b", g):
        r("AVISO", "gancho sem número/impossibilidade concreta da geração 1")
    if re.search(r"(?i)incr[íi]vel|chocante|voc[êe] n[ãa]o vai acreditar|olha o que", g):
        r("FALHA", "gancho com hype/frase vazia")

    # ---- números
    todos = [len(dados(c["fala"])) for c in cenas]
    if sum(todos) > 8:
        r("FALHA", f"{sum(todos)} números falados (máx ~6 dados; limite duro 8)")
    elif sum(todos) > 6:
        r("AVISO", f"{sum(todos)} números falados (alvo ≤ 6 dados)")
    for k, nn in enumerate(todos):
        if nn > 3:
            r("AVISO", f"cena {k}: {nn} números na mesma fala (1 número herói por cena)")

    # ---- números por extenso (desde o layout v3: algarismos na fala; a voz lê por extenso sozinha)
    ext = [(k, m.group(0)) for k, c in enumerate(cenas)
           for m in RE_EXT.finditer(re.sub(r"(?i)\b(gera[çc][ãa]o|ger\.?)\s+\w+", " ", limpa(c["fala"])))]
    if ext:
        r("AVISO", "número por extenso na fala (" + "; ".join(f"cena {k}: '{x}'" for k, x in ext[:4]) +
          "): escreva em algarismos (\"73\", \"1,8\"); a legenda mostra o número grande em amarelo e a voz lê por extenso")

    # ---- ritmo por cena e revelações (retenção v3, docs/ROTEIRO.md §13)
    for k, p in enumerate(pal):
        if k and p > 18:
            r("AVISO", f"cena {k}: {p} palavras (≈ {p / PAL_S:.0f} s de fala): cena longa demais; quebre em 2 ou corte")
    if len(cenas) > 1 and pal[1] > 16:
        r("AVISO", f"cena 1 (premissa + regra) com {pal[1]} palavras (≤ 16): é onde mais gente sai")
    if n_long < 2:
        r("AVISO", f"{n_long} <long pause>: use 2 a 4 revelações (a pausa longa antes do número vira suspense automático)")
    elif n_long > 5:
        r("AVISO", f"{n_long} <long pause>: suspense demais cansa (2 a 4)")
    if not any(PROMESSA.search(c["fala"]) for c in cenas[:3]):
        r("AVISO", "nenhuma promessa do teste final nas 3 primeiras cenas (ex.: \"No fim, eu testo o campeão num lugar "
                   "que ele nunca viu.\") — é o que segura até o fim (§13)")

    # ---- herói
    n_fala = sum(bool(re.search(r"(?i)\bcampe[ãa]o\b|\bcampe[ãa]\b", c["fala"])) for c in cenas)
    if n_fala < 2:
        r("FALHA", f"'o campeão/a campeã' dito em {n_fala} fala(s) (mín 2)")

    # ---- re-gancho (40–60% do tempo)
    janela = [k for k in range(len(cenas)) if 0.40 * dur <= ini[k] <= 0.60 * dur]
    padrao = re.compile(r"(?i)\?|e a[íi]\b|at[ée] que|\bmas\b|s[óo] que|pegadinha|n[ãa]o esperava|trava|ser[áa] que")
    if not any(padrao.search(cenas[k]["fala"]) for k in janela):
        r("AVISO", f"sem re-gancho entre 40% e 60% do tempo (cenas {janela}): reabra uma dúvida (docs/ROTEIRO.md §6)")

    # ---- CTA e laço
    ultimo = cenas[-1]["fala"]
    sem_tag = limpa(ultimo).strip()
    if not re.search(r"(?i)quando eu\W*$", sem_tag):
        r("FALHA", "a última fala não termina em '…quando eu…' (laço falado, §7)")
    if "?" not in ultimo:
        r("FALHA", "o CTA (última cena) não contém uma pergunta")
    else:
        perg = [x for x in re.split(r"(?<=[.!?…])\s+", sem_tag) if x.strip().endswith("?")]
        if perg and len(palavras(perg[-1])) > 18:
            r("AVISO", f"pergunta do CTA com {len(palavras(perg[-1]))} palavras (alvo ≤ 16)")
    pool = "\n".join(c["fala"] for c in cenas) + "\n" + legenda
    for pat in PROIBIDAS:
        m = re.search(pat, pool, re.I)
        if m:
            r("FALHA", f"expressão proibida (CTA sem votação): '{m.group(0)}'")

    # ---- legenda
    if not legenda:
        r("AVISO", "legenda não encontrada na saída (rode com gerar.py atualizado)")
    else:
        linhas = [x for x in legenda.splitlines() if x.strip()]
        tags = re.findall(r"#\w+", legenda)
        if not 3 <= len(tags) <= 5:
            r("FALHA", f"{len(tags)} hashtags (use 3 a 5)")
        if linhas and re.match(r"(?i)\s*simula", linhas[0]):
            r("FALHA", "linha 1 da legenda é descrição; deve ser curiosidade (§9)")
        if linhas and len(linhas[0]) > 140:
            r("AVISO", f"linha 1 da legenda com {len(linhas[0])} caracteres (≤ 120)")
        if not re.search(r"(?i)\b(manda|marca|compartilh|envia|mostra)\b", legenda):
            r("FALHA", "legenda sem gatilho de compartilhar (§9, linha 3)")
        if not re.search(r"(?i)aprendendo sozinha|aprende sozinha|aprendeu sozinha", legenda):
            r("AVISO", "legenda sem o termo pesquisável 'IA aprendendo sozinha'")

    # ---- saída
    falhas = 0
    for nivel, txt in res:
        print(f"{nivel:<6} {txt}")
        falhas += nivel == "FALHA"
    if not res:
        print("ok: nenhuma pendência medível")
    print(f"\n{falhas} falha(s). Itens não medíveis (re-gancho pago, herói com queda e acerto, honestidade, descoberta clara) "
          "ficam com os analistas (docs/ROTEIRO.md §10).")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
