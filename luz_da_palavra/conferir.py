"""Conferidor de GANCHOS do Luz da Palavra (roda antes de gastar voz/imagem; o gerador exige zero FALHA).

    python luz_da_palavra/conferir.py luz_da_palavra/roteiros/ep02_lazaro.json

Regras (pedido do dono, nov/2026: apelação máxima no gancho inicial e em um gancho/re-gancho a cada ~5 s):
  gancho inicial  = 1ª fala com <= 12 palavras, sem abertura fraca, com nome bíblico + palavra de choque ou número;
  laço aberto     = a 2ª fala promete algo ("quase ninguém percebe", "o motivo vai mexer com você");
  re-ganchos      = cena com cartão, reticências "…" ou pergunta; no máximo ~5,5 s entre dois ganchos;
  revelação       = o roteiro marca em qual cena ela vem ("revelacao"); a tela mostra a contagem regressiva;
  fechamento      = CTA com pergunta do episódio (resposta curta e comparável, nunca "curte e comenta") antes da
                    última fala; a última fala fica em aberto e EMENDA na 1ª (o vídeo recomeça sem a pessoa notar);
  honestidade     = "fatos" com o versículo de cada afirmação; tema fora do prazo de 2 meses.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import temas  # noqa: E402

FRACAS = ("olá", "ola", "oi ", "bom dia", "boa noite", "hoje ", "você sabia", "voce sabia", "vamos ", "neste vídeo",
          "nesse vídeo", "bem-vindo", "fala, ", "e aí", "deixa eu")
SAGRADOS = ("jesus", "deus", "senhor", "espírito", "pedro", "paulo", "moisés", "davi", "maria", "lázaro", "abraão", "josé",
            "elias", "jó", "judas", "tiago", "joão", "mateus", "pai", "cristo", "salomão", "daniel", "sansão", "rute")
CHOQUE = ("ninguém", "nunca", "quase", "mesmo", "escondido", "segredo", "proibido", "morreu", "negou", "chorou", "traiu",
          "mentiu", "erro", "pecado", "ignorou", "esqueceu", "abandonou", "omitiu", "errado", "verdade", "arrepi", "chocante",
          "demorou", "calou", "fugiu", "rejeitou", "perdeu", "só ", "apenas", "primeira", "única", "último", "ultima")
PROMESSA = ("ninguém", "quase", "motivo", "segredo", "detalhe", "vai ", "espera", "presta", "antes", "escondid", "pista",
            "verdade", "por quê", "porque", "?")
CTA_GENERICO = ("curte e comenta", "comenta amém", "comente amém", "deixa seu like", "deixa o like", "se inscreve",
                "segue o canal", "compartilha esse vídeo", "curta e comente")
MAX_GAP, GAP_FALHA, ALVO_FIM = 5.5, 7.0, 55


def limpa(t):
    return t.replace("*", "")


def nprs(t):
    return len(limpa(t).split())


def eh_gancho(c):
    f = c["fala"]
    return bool(c.get("card")) or bool(c.get("cta")) or "…" in f or "?" in f


def estima(cenas):
    """Início estimado de cada cena (antes da voz existir): ~3 palavras/s + respiro + suspense nas reticências."""
    t, out = 0.0, []
    for c in cenas:
        out.append(t)
        t += nprs(c["fala"]) / 3.0 + 0.45 + 0.7 * c["fala"].count("…")
    return out, t


def gaps(cenas, inicios, fim):
    """[(t, tempo até o gancho seguinte)] entre ganchos (o início da cena 0 conta como gancho)."""
    ts = [inicios[0]] + [t for c, t in zip(cenas[1:], inicios[1:]) if eh_gancho(c)] + [fim - 1.2]   # 1,2 s = cauda sem voz
    return [(a, b - a) for a, b in zip(ts[:-1], ts[1:])]


def confere(rot, inicios=None, fim=None):
    """Lista de (nível, texto). Nível FALHA bloqueia o gerador."""
    r = []
    cenas = rot["cenas"]
    if inicios is None:
        inicios, fim = estima(cenas)
    f0 = limpa(cenas[0]["fala"])
    baixo = f0.lower()
    if nprs(f0) > 14:
        r.append(("FALHA", f"gancho inicial com {nprs(f0)} palavras (máx. 14, ideal <= 12)"))
    elif nprs(f0) > 12:
        r.append(("AVISO", f"gancho inicial com {nprs(f0)} palavras (ideal <= 12)"))
    if any(baixo.startswith(x) or baixo.startswith(x.strip()) and len(x.strip()) > 4 for x in FRACAS):
        r.append(("FALHA", "gancho inicial começa com abertura fraca (saudação/'você sabia'/'hoje')"))
    sag = [x for x in SAGRADOS if re.search(r"\b" + x + r"\b", baixo)]
    cho = [x for x in CHOQUE if x in baixo + " "]
    if not sag:
        r.append(("AVISO", "gancho sem nome bíblico (Jesus, Pedro, Maria…): o nome concreto prende mais"))
    if not cho and not re.search(r"\d", baixo):
        r.append(("AVISO", "gancho sem palavra de choque/contraste (ninguém, nunca, mesmo, negou, escondido…) nem número"))
    # o título grande na tela e o gancho falado precisam contar a MESMA coisa (no ep03 divergiram)
    tit = " ".join(rot.get("titulo", [])).lower()
    pal_g = {w for w in re.findall(r"\w{4,}", baixo)} - {"estava", "mesmo", "quando", "porque", "depois"}
    if tit and not any(w in tit for w in pal_g):
        r.append(("AVISO", "título da tela não repete nenhuma palavra forte do gancho falado (devem dizer a mesma coisa)"))
    tags = re.findall(r"#\w+", rot.get("legenda", ""))
    genericas = {"#jesus", "#biblia", "#fe", "#deus", "#evangelho", "#fyp", "#foryou", "#viral"}
    if tags and not [t for t in tags if t.lower() not in genericas]:
        r.append(("AVISO", "legenda só com hashtags genéricas: inclua 1-2 do episódio (ex.: #elias, #lazaro, #pedro)"))
    if not cenas[0].get("titulo"):
        r.append(("AVISO", "cena 0 sem \"titulo\": true (o gancho precisa estar escrito grande na tela em 0 s)"))
    if len(cenas) > 1 and not any(p in limpa(cenas[1]["fala"]).lower() for p in PROMESSA):
        r.append(("AVISO", "2ª fala não abre um laço (ex.: 'quase ninguém percebe', 'o motivo vai mexer com você')"))
    cards = [c for c in cenas if c.get("card")]
    if len(cards) < 5:
        r.append(("FALHA", f"só {len(cards)} cartões de re-gancho (mín. 5)"))
    for c in cards:
        if len(c["card"]) > 22:
            r.append(("AVISO", f"cartão longo '{c['card']}' (> 22 letras; encolhe a fonte)"))
    prim = next((t for c, t in zip(cenas, inicios) if c.get("card")), None)
    if prim is None or prim > 9:
        r.append(("AVISO", "1º cartão de re-gancho depois de 9 s"))
    gs = gaps(cenas, inicios, fim)
    for i, (t, g) in enumerate(gs):
        if i == len(gs) - 1:                      # último trecho = a fala de fechamento (payoff), pode ser um pouco mais longa
            if g > 8.0:
                r.append(("FALHA", f"fala final com {g:.1f} s sem gancho (máx. 8 s)"))
        elif g > GAP_FALHA:
            r.append(("FALHA", f"{g:.1f} s sem gancho a partir de {t:.0f} s (máx. {MAX_GAP} s; ideal ~5)"))
        elif g > MAX_GAP:
            r.append(("AVISO", f"{g:.1f} s sem gancho a partir de {t:.0f} s (ideal <= {MAX_GAP} s)"))
    if "revelacao" not in rot:
        r.append(("AVISO", "sem \"revelacao\" (índice da cena da revelação): a contagem regressiva não aparece"))
    elif not 3 <= rot["revelacao"] < len(cenas):
        r.append(("FALHA", "\"revelacao\" fora do intervalo de cenas"))
    ctas = [c for c in cenas[:-1] if c.get("cta")]
    if not ctas:
        r.append(("FALHA", "sem CTA (\"cta\") antes da última fala"))
    for c in ctas:                                 # CTA que dá vontade de ler o que os outros escreveram
        fl = limpa(c["fala"]).lower()
        if any(g in fl for g in CTA_GENERICO):
            r.append(("FALHA", f"CTA genérico ('{limpa(c['fala'])}'): faça uma pergunta do episódio com resposta curta "
                               "(escolha entre opções, SIM/NÃO, uma palavra ou um nome) que as pessoas queiram comparar"))
        elif "?" not in fl and " ou " not in fl and "nome" not in fl:
            r.append(("AVISO", "CTA sem pergunta, escolha ou nome: a resposta precisa ser curta e comparável"))
        if len(c["cta"]) > 30:
            r.append(("AVISO", f"botão do CTA longo '{c['cta']}' (> 30 letras)"))
    if ctas and "?" not in rot.get("legenda", "").split("\n")[0] + rot.get("legenda", ""):
        r.append(("AVISO", "legenda do post sem a pergunta do CTA (repita a pergunta na legenda)"))
    # EMENDA: a última fala termina no meio de uma frase que continua na 1ª fala -> o vídeo recomeça sem a pessoa notar
    ultima = limpa(cenas[-1]["fala"]).strip()
    if not rot.get("emenda"):
        r.append(("FALHA", "sem \"emenda\": a última fala precisa emendar na 1ª (escreva a frase completa em \"emenda\")"))
    else:
        if re.search(r"[.!?]$", ultima):
            r.append(("FALHA", "última fala termina com ponto final: precisa ficar em aberto e continuar na 1ª fala"))
        junta = re.sub(r"\W+", " ", (ultima + " " + limpa(cenas[0]["fala"])).lower()).strip()
        if re.sub(r"\W+", " ", limpa(rot["emenda"]).lower()).strip() != junta:
            r.append(("FALHA", "\"emenda\" precisa ser exatamente a última fala + a 1ª fala (a frase que o loop forma)"))
        if cenas[-1]["img"] != cenas[0]["img"]:
            r.append(("FALHA", "na emenda a última cena usa a MESMA imagem da 1ª (senão o recomeço aparece como corte)"))
    n = sum(nprs(c["fala"]) for c in cenas)
    if not 100 <= n <= 145:
        r.append(("AVISO", f"{n} palavras (alvo 100-145)"))
    if fim > ALVO_FIM + 6:
        r.append(("AVISO", f"duração estimada {fim:.0f} s (alvo <= {ALVO_FIM} s)"))
    if len(rot.get("fatos", [])) < 2:
        r.append(("FALHA", "\"fatos\" com menos de 2 itens: toda afirmação precisa do versículo"))
    if len(rot.get("ganchos", [])) < 3:
        r.append(("AVISO", "\"ganchos\": liste 3 candidatos de gancho inicial (e justifique o escolhido)"))
    for t, m in temas.conflitos(rot):
        r.append(("FALHA", f"tema repetido no prazo de 2 meses: '{t['tema']}' ({t['ref']}), {m}; libera em {t['libera_em']}"))
    return r


def imprime(res):
    for nivel, msg in res:
        print(f"  {nivel}: {msg}")
    f = sum(1 for n, _ in res if n == "FALHA")
    print(f"  -> {'OK' if not f else 'BLOQUEADO'} ({f} FALHA, {len(res) - f} AVISO)")
    return f


if __name__ == "__main__":
    rot = json.load(open(sys.argv[1], encoding="utf-8"))
    ini, fim = estima(rot["cenas"])
    print(f"duração estimada {fim:.0f} s; ganchos em:", ", ".join(f"{t:.0f}s" for t, _ in gaps(rot["cenas"], ini, fim)))
    sys.exit(1 if imprime(confere(rot, ini, fim)) else 0)
