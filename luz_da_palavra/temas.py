"""Lista de temas já usados no Luz da Palavra. Cada tema vale 60 dias (2 meses): nesse prazo NÃO se repete.

    python luz_da_palavra/temas.py                      # lista os temas e quando cada um libera de novo
    python luz_da_palavra/temas.py --checa "palavras"   # procura temas parecidos ainda no prazo
    python luz_da_palavra/temas.py --roteiro <json>     # confere se o roteiro repete tema/passagem no prazo

O gerador (`gerar.py`) usa isto sozinho: recusa um roteiro repetido e registra o tema novo ao terminar o vídeo.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata

ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temas.json")
VALIDADE_DIAS = 60
VAZIAS = {"de", "da", "do", "das", "dos", "e", "o", "a", "os", "as", "um", "uma", "que", "em", "no", "na", "por", "pra",
          "para", "com", "se", "mesmo", "jesus", "deus", "biblia", "versiculo"}


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^a-z0-9 ]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def palavras(t):
    return {w for w in norm(t).split() if len(w) > 2 and w not in VAZIAS}


def passagens(ref):
    """'JOÃO 11:35' -> {('joao', 11)}; 'JOÃO 18:18 e 21:9' -> {('joao', 18), ('joao', 21)} (livro + capítulo)."""
    out = set()
    m = re.match(r"\s*((?:[1-3]\s)?[^\d]+?)\s+(\d.*)$", norm(ref).strip())
    if not m:
        return out
    livro = m.group(1).strip()
    for cap in re.findall(r"(\d+)\s*[: ]\s*\d+", ref.lower().replace(":", " ")):
        out.add((livro, int(cap)))
    if not out:
        out = {(livro, int(n)) for n in re.findall(r"\d+", m.group(2))[:1]}
    return out


def carrega():
    return json.load(open(ARQ, encoding="utf-8")) if os.path.exists(ARQ) else []


def ativos(hoje=None):
    hoje = hoje or dt.date.today()
    return [t for t in carrega() if dt.date.fromisoformat(t["libera_em"]) > hoje]


def conflitos(rot, hoje=None):
    """Temas ainda no prazo que o roteiro repete (mesmo tema_id, mesma passagem ou palavras-chave muito parecidas)."""
    achados = []
    ps = passagens(rot.get("ref", ""))
    kw = palavras(rot.get("tema", "") + " " + " ".join(rot.get("titulo", [])))
    for t in ativos(hoje):
        if t["slug"] == rot.get("slug"):
            continue
        motivo = None
        if rot.get("tema_id") and rot["tema_id"] == t["tema_id"]:
            motivo = "mesmo tema_id"
        elif ps & passagens(t["ref"]):
            motivo = "mesma passagem (livro + capítulo)"
        else:
            comum = kw & palavras(t["tema"] + " " + " ".join(t.get("titulo", [])))
            if len(comum) >= 3:
                motivo = "palavras em comum: " + ", ".join(sorted(comum))
        if motivo:
            achados.append((t, motivo))
    return achados


def registra(rot, hoje=None):
    hoje = hoje or dt.date.today()
    if any(t["slug"] == rot["slug"] for t in carrega()):
        return                                    # já registrado: o prazo de 2 meses não reinicia
    lista = carrega()
    lista.append({"slug": rot["slug"], "tema_id": rot.get("tema_id", rot["slug"]), "tema": rot.get("tema", ""),
                  "ref": rot["ref"], "titulo": rot.get("titulo", []), "feito_em": hoje.isoformat(),
                  "libera_em": (hoje + dt.timedelta(days=VALIDADE_DIAS)).isoformat()})
    json.dump(lista, open(ARQ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checa")
    ap.add_argument("--roteiro")
    a = ap.parse_args()
    hoje = dt.date.today()
    if a.roteiro:
        rot = json.load(open(a.roteiro, encoding="utf-8"))
        c = conflitos(rot)
        for t, m in c:
            print(f"REPETIDO: '{t['tema']}' ({t['ref']}, {t['feito_em']}), {m}; libera em {t['libera_em']}")
        print("-> LIVRE" if not c else "-> BLOQUEADO (tema no prazo de 2 meses)")
        sys.exit(1 if c else 0)
    if a.checa:
        kw = palavras(a.checa)
        achou = [t for t in carrega() if kw & palavras(t["tema"] + " " + " ".join(t.get("titulo", [])) + " " + t["ref"])]
        for t in achou:
            ativo = dt.date.fromisoformat(t["libera_em"]) > hoje
            print(("NO PRAZO " if ativo else "liberado ") + f"{t['tema']} ({t['ref']}), libera em {t['libera_em']}")
        print("(nada parecido)" if not achou else "")
        return
    print(f"{'estado':9} {'ref':14} {'libera em':11} tema")
    for t in sorted(carrega(), key=lambda t: t["libera_em"]):
        ativo = dt.date.fromisoformat(t["libera_em"]) > hoje
        print(f"{'NO PRAZO' if ativo else 'liberado':9} {t['ref']:14} {t['libera_em']:11} {t['tema']}")


if __name__ == "__main__":
    main()
