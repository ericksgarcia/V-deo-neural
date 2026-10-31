"""Roteiro do episódio Dança das Cadeiras (guia v2-v5 + trava de retenção §17): 12 IAs (o MESMO cérebro nas 12) e 11 cadeiras.

Curadoria autorizada (§16.2): regras escritas à mão (música 2,5 s, depois 3,4 s para sentar; cadeira é de quem chega primeiro; corpos sólidos);
sementes 3, 5, 7, 11, 13, 17, 19, 23 treinadas (200 gerações, população 60) e escolhida a de melhor história. Nota = cadeiras ocupadas no fim + um pouco
por ocupar cedo. Nada premia "desviar", "rodar" nem "esperar perto da cadeira".
Descobertas medidas (médias da TURMA, janelas de 7 gerações): esbarrões (fração das IAs em pé encostando em alguém), ciranda (parcela do movimento
em volta da roda que vai para o mesmo sentido) e coladas (IAs em pé a menos de 1 m de uma cadeira enquanto a música toca).
Todo número falado sai da vitrine do treino ou de 300 rodadas novas.
"""
import numpy as np

from ..coevolucao_cadeiras import campeao, rodadas
from ..desafios import cadeiras as K
from ..palco.holo import AMARELO, CIANO

BRANCO = (0.92, 0.96, 1.0)
VERDE = (0.3, 1.0, 0.62)
ROSA = (1.0, 0.35, 0.6)

DESTAQUES = {"campeão": AMARELO, "IAs": CIANO, "cadeiras": VERDE, "música": ROSA, "ciranda": CIANO, "coladas": VERDE}


def suave(x, k=7):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def eventos(hist):
    G = len(hist["m_cheias"])
    ev = {"G": G}
    for k in ("cheias", "perfeita", "colado", "toque", "giro"):
        ev[k] = suave(hist["m_" + k])
    ev["same"] = (1.0 + ev["giro"]) / 2.0                     # parcela do movimento que vai para o sentido dominante
    ev["desvio"] = ev["ciranda"] = ev["colada"] = ev["calma"] = None
    t0, s0 = ev["toque"][:3].mean(), ev["same"][:3].mean()
    ev["desvio"] = next((g for g in range(3, G) if ev["toque"][g] <= 0.55 * t0), None)
    if ev["desvio"] is None:
        return ev
    ev["ciranda"] = next((g for g in range(ev["desvio"] + 3, G) if ev["same"][g] >= 0.88 and ev["same"][g] >= s0 + 0.2), None)
    if ev["ciranda"] is None:
        return ev
    base = ev["ciranda"] + 20
    if base >= G - 20:
        return ev
    ev["colada"] = next((g for g in range(base, G) if ev["perfeita"][g] >= ev["perfeita"][base] + 0.15), None)
    if ev["colada"] is not None:
        ev["calma"] = (base + ev["colada"]) // 2
    return ev


def nota_historia(hist):
    ev = eventos(hist)
    if None in (ev["desvio"], ev["ciranda"], ev["colada"]):
        return 0.0
    pf = ev["perfeita"]
    return float(min(pf[-10:].mean(), 0.6) * 6 + ev["cheias"][-10:].mean() + (ev["colada"] - ev["ciranda"]) / ev["G"] * 2)


def duelo(hist, g, rodadas_n=300, semente=77):
    """O campeão da geração g em rodadas novas: (rodadas com as 11 cadeiras cheias em 100, cadeiras ocupadas em média)."""
    genes = hist["genes"][g]
    j, _ = rodadas(genes, np.full(rodadas_n, campeao(hist, g)), semente + g)
    ch = j.cheias()
    return float((ch == K.C).mean()), float(ch.mean())


def pct(x):
    return f"{100 * x:.0f}"


def monta(hist, A):
    ev = eventos(hist)
    G = ev["G"]
    if None in (ev["desvio"], ev["ciranda"], ev["colada"]):
        raise RuntimeError("Esta semente não tem a história completa (desvio, ciranda, coladas): troque a semente.")
    g1, g2, g3, gc = ev["desvio"], ev["ciranda"], ev["colada"], ev["calma"]
    n, c = K.N, K.C
    ch0 = int(round(c * float(hist["m_cheias"][:3].mean())))
    t0, t1 = int(round(100 * float(hist["m_toque"][:3].mean()))), int(round(100 * float(ev["toque"][g1])))
    s0, s1 = int(round(100 * float(ev["same"][:3].mean()))), int(round(100 * float(ev["same"][g2])))
    p_c, p_3 = int(round(100 * float(ev["perfeita"][gc]))), int(round(100 * float(ev["perfeita"][g3])))
    c_c, c_3 = int(round(100 * float(ev["colado"][gc]))), int(round(100 * float(ev["colado"][g3])))
    um, fin = duelo(hist, 0), duelo(hist, G - 1)
    C = G
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ------------------------------------------------------------ GANCHO (3 candidatos no analista; este é o escolhido)
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("12 IAs x 11 CADEIRAS", BRANCO), (f"SÓ {ch0} CADEIRA OCUPADA", AMARELO)],
         log=[(f"{n} IAs · {c} CADEIRAS", CIANO), ("NINGUÉM SABE O JOGO", AMARELO)],
         carimbo={"texto": f"{ch0} DE {c}", "cor": AMARELO, "em": 0.5, "sub": "CADEIRAS OCUPADAS EM MÉDIA · GERAÇÃO 1"},
         fala=f"Soltei {n} IAs numa dança das cadeiras. <short pause> Na geração 1, só {ch0} cadeira foi ocupada.")
    # ------------------------------------------------------------ PREMISSA + REGRA + PROMESSA (o campeão da geração 1 falha)
    cena(tipo="replay", ger=C, foco=0, grupo="g1b", log=[("CAMPEÃO DA GER 001", CIANO), ("QUEM SENTA MAIS VIRA PAI DA TURMA", VERDE)],
         fala="É tipo festa de criança: a música para, a cadeira é de quem chega primeiro.")
    cena(tipo="replay", ger=C, foco=0, grupo="g1b", log=[("CAMPEÃO DA GER 001 · SEM CADEIRA", ROSA), ("ELE CORRE E MESMO ASSIM FICA DE PÉ", AMARELO)],
         fala="Mas o campeão, o cérebro de todas, ficava sem cadeira. <short pause> De novo. No fim, tem teste.")
    # ------------------------------------------------------------ DESCOBERTA 1: o desvio
    cena(tipo="replay", ger=C + g1, foco=0,
         cartao={"numero": 1, "rotulo": "IAs", "nome": "O DESVIO", "cor": AMARELO, "stat": f"ESBARRÕES {t0}% → {t1}% DAS IAs"},
         log=[(f"GER {g1 + 1:03d} · ESBARRÕES {t0}% → {t1}%", AMARELO), ("NINGUÉM MANDOU DESVIAR", CIANO)],
         fala=f"Aí elas se esbarravam. <short pause> Até aprenderem a desviar: de {t0} para {t1} a cada cem. <short pause> Educadas.")
    marcos.append((g1, "1", AMARELO))
    # ------------------------------------------------------------ DESCOBERTA 2: a ciranda
    cena(tipo="replay", ger=C + g2, foco=0,
         cartao={"numero": 2, "rotulo": "IAs", "nome": "A CIRANDA", "cor": CIANO, "stat": f"MESMO SENTIDO {s0}% → {s1}% DO MOVIMENTO"},
         log=[(f"GER {g2 + 1:03d} · MESMO SENTIDO {s0}% → {s1}%", CIANO), ("ELAS RODAM JUNTAS, SEM COMBINAR", VERDE)],
         fala=f"Então formaram uma ciranda, sem ninguém mandar. <long pause> Pro mesmo lado: de {s0} para {s1} a cada cem.")
    marcos.append((g2, "2", CIANO))
    # ------------------------------------------------------------ RE-GANCHO: o placar trava
    cena(tipo="ao_vivo", ger=gc, grupo="calma", vel=1.0,
         log=[(f"GER {gc + 1:03d} · RODADAS COMPLETAS {p_c}%", ROSA), ("O PLACAR TRAVOU", AMARELO)],
         fala="Só que travou. <short pause> Acabou? <long pause>")
    # ------------------------------------------------------------ DESCOBERTA 3: coladas na cadeira
    cena(tipo="replay", ger=C + g3, foco=0,
         cartao={"numero": 3, "rotulo": "IAs", "nome": "COLADAS", "cor": VERDE, "stat": f"RODADAS COMPLETAS {p_c}% → {p_3}%"},
         log=[(f"GER {g3 + 1:03d} · COMPLETAS {p_c}% → {p_3}%", VERDE), (f"PERTO DE UMA CADEIRA: {c_c}% → {c_3}% DO TEMPO", CIANO)],
         fala=f"Mas não. Elas esperaram coladas nas cadeiras. <long pause> Todas sentadas: de {p_c} para {p_3} rodadas a cada cem.")
    marcos.append((g3, "3", VERDE))
    # ------------------------------------------------------------ TESTE (chute)
    itens = [("CAMPEÃO 1", um[0], CIANO), (f"CAMPEÃO {G}", fin[0], VERDE)]
    kw = dict(tipo="barras", grupo="teste", ger=G - 1, fundo_escuro=0.35, fundo_vivo=0.9, fundo_vel=2.0, itens=itens, titulo="TODAS AS CADEIRAS CHEIAS",
              sub="rodadas novas", destaque=1, cor_destaque="verde", rotulo_destaque="",
              log=[("TESTE: RODADAS NOVAS", AMARELO), (f"COMPLETAS {pct(um[0])}% → {pct(fin[0])}%", AMARELO)])
    cena(teste=True, **kw,
         fala=f"Hora do teste. <short pause> O campeão inicial enchia tudo em {pct(um[0])} de 100. Chuta aí: e o final? <long pause>")
    cena(**dict(kw, sub="rodadas com as 11 cadeiras cheias"), fala=f"{pct(fin[0])} em 100. <short pause> Coitada da que sobrou.")
    # ------------------------------------------------------------ CTA + LAÇO
    cena(tipo="replay", ger=C + G - 1, foco=0, grupo="fim", destaques={"campeão": AMARELO, "IAs": CIANO},
         fala="Combinaram a ciranda? Ou são cópias do mesmo cérebro? <short pause> Porque tudo começou quando eu…")

    info = {"marca": "VÍDEO NEURAL", "serie": suave(hist["m_cheias"], 5), "serie_rotulo": "% CADEIRAS OCUPADAS",
            "marcos": marcos, "rotulo_vivo": f"{n} IAs · {c} CADEIRAS", "nome_teste": "TESTE FINAL",
            "rodape": f"{n} IAs COM O MESMO CÉREBRO · {c} CADEIRAS · REGRAS PROGRAMADAS, SÓ O CÉREBRO EVOLUI · {G} GERAÇÕES · NOTA = CADEIRAS OCUPADAS"}
    post = (f"12 IAs, 11 cadeiras e só {ch0} ocupada na geração 1. Aí elas inventaram uma ciranda 🪑\n"
            f"IA aprendendo sozinha por seleção natural. Simulação real de uma dança das cadeiras: {n} IAs, {c} cadeiras, {G} gerações, números medidos no treino.\n"
            "Marca quem sempre empurra na dança das cadeiras 👇\n\n"
            "#inteligenciaartificial #ia #aprendizadodemaquina #simulacao #dancadascadeiras")
    ev["teste"] = {"um": um, "fin": fin, "toque": (t0, t1), "same": (s0, s1), "perf": (p_c, p_3), "colado": (c_c, c_3), "ch0": ch0}
    return cenas, info, post, ev
