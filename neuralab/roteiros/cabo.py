"""Roteiro do episódio Cabo de Guerra de Enxames: dois enxames de 5 robôs disputam uma caixa pesada.

Regra de ouro: todo número falado sai do treino. O HUD mostra a mesma média móvel (5 gerações, sem atravessar o
início de uma fase), então o número que aparece na tela é o número falado.
"""
import numpy as np

from ..adaptadores.cabo import COR_A, COR_B
from ..coevolucao_cabo import FASES, limites_fases, suave_fase, torneio

BRANCO = (0.92, 0.96, 1.0)
VERDE, VERMELHO, AMARELO = (0.3, 1.0, 0.62), (1.0, 0.3, 0.38), (1.0, 0.74, 0.12)
QUEM = {"A": ("SÓ O A TREINA", COR_A), "B": ("SÓ O B TREINA", COR_B), "AB": ("OS DOIS TREINAM", AMARELO)}


def pct(x):
    return f"{100 * x:.0f}%"


def n1(x):
    return f"{x:.1f}".replace(".", ",")


def em_dez(x):
    n = int(round(x * 10))
    nomes = ["nenhum", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"]
    return f"{nomes[n]} em cada dez"


def series(hist):
    f = hist["fase"]
    return {k[2:]: suave_fase(v, f) for k, v in hist.items() if k.startswith("m_")}


def nota_historia(hist):
    """Quão limpa é a história: o enxame que treina sozinho vence o congelado, e juntos aparecem encostar e
    empurrar em grupo."""
    M, L = series(hist), limites_fases()
    a1, b1 = L[0][1], L[1][1]
    pts = 2.0 * (M["venc_a"][a1] > 0.3) + 2.0 * (M["venc_b"][b1] > 0.3)
    pts += 2.0 * min(M["pico_a"][-1] / 4.0, 1) + 1.0 * min(M["pico_b"][-1] / 4.0, 1)
    pts += 1.0 * (M["enc_a"][-1] > 2 * M["enc_a"][0] + 0.3)
    pts += 1.0 * (M["mexeu"][-1] > 0.9)
    pts += 1.0 * (0.12 < M["venc_a"][-1] and M["venc_a"][-1] < 0.8)
    return float(pts)


def monta(hist, A):
    M, L = series(hist), limites_fases()
    G = len(hist["A"])
    fim = [b for _, b in L]
    cenas = []

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    D = {"A": COR_A, "B": COR_B, "azul": COR_A, "rosa": COR_B, "caixa": AMARELO, "junto": VERDE, "juntos": VERDE,
         "sozinho": VERMELHO, "ninguém": VERMELHO, "gol": AMARELO}

    def luta(g, tipo, *alternativas):
        rod = A.rodada(g)
        for t in (tipo,) + alternativas:
            k = A.busca(rod, t)
            if k is not None:
                return k
        return None

    def primeira(serie, cond, ini=0):
        for g in range(ini, G):
            if cond(serie[g]):
                return g
        return G - 1

    # ---------------------------------------------------------------- GANCHO: vitória do enxame A em grupo
    gh = fim[2]
    kh = luta(gh, "junto_a", "vitoria_a", "vitoria")
    marcas = [{"tipo": "circulo", "em": 1.0, "alvo": "caixa", "segue": True, "texto": "CAIXA", "rx": 70, "ry": 70}]
    cena(tipo="replay", ger=gh, foco=kh, grupo="gancho", marcas=marcas, inicio=0.0,
         titulo_gancho=[("5 ROBÔS", BRANCO), ("1 CAIXA", AMARELO)],
         fala="Cinco robôs. Uma caixa pesada. Sozinho, nenhum consegue mover.")

    # ---------------------------------------------------------------- PREMISSA + GERAÇÃO 1
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[("CABO DE GUERRA · ENXAME A × ENXAME B", BRANCO), ("LEVE A CAIXA ATÉ O GOL DO OUTRO", BRANCO)],
         fala="Dois enxames de cinco. Leve a caixa até o gol do outro.")
    p0 = 1 - M["mexeu"][0]
    cena(tipo="ao_vivo", ger=0, grupo="g1",
         carimbo={"texto": f"CAIXA PARADA {pct(p0)}", "cor": "vermelho", "em": 0.5, "sub": "GERAÇÃO 1"},
         log=[(f"GER 001 · CAIXA NEM SE MEXE EM {pct(p0)}", VERMELHO)],
         fala=f"Na geração um, em {em_dez(p0)} jogos a caixa nem se mexe.")

    # ---------------------------------------------------------------- FASE 1: SÓ O A TREINA
    f = 0
    cena(tipo="ao_vivo", ger=fim[f], grupo="f1",
         carimbo={"texto": QUEM["A"][0], "cor": QUEM["A"][1], "em": 0.2, "sub": f"{FASES[f][2]} GERAÇÕES"},
         log=[(f"SÓ O A TREINA · {FASES[f][2]} GER", COR_A)],
         fala=f"Primeiro treino só o azul. Em {FASES[f][2]} gerações ele vence {pct(M['venc_a'][fim[f]])}.")
    # ---------------------------------------------------------------- FASE 2: SÓ O B TREINA
    f = 1
    cena(tipo="ao_vivo", ger=fim[f], grupo="f2",
         carimbo={"texto": QUEM["B"][0], "cor": QUEM["B"][1], "em": 0.2, "sub": f"{FASES[f][2]} GERAÇÕES"},
         log=[(f"SÓ O B TREINA · {FASES[f][2]} GER", COR_B)],
         fala=f"Agora só o rosa. Ele vai de {pct(M['venc_b'][fim[f - 1]])} para {pct(M['venc_b'][fim[f]])}.")

    # ---------------------------------------------------------------- DESCOBERTAS (os dois treinam)
    g2 = fim[1]
    # 1 · ENCOSTAR: robôs encostados na caixa
    gd1 = primeira(M["enc_a"], lambda v: v > 2.0, fim[1])
    e0, e1 = M["enc_a"][0], M["enc_a"][gd1]
    kd1 = luta(gd1, "mexeu", "vitoria")
    cena(tipo="ao_vivo", ger=gd1, grupo="d1",
         cartao={"numero": 1, "rotulo": "ENXAME A", "nome": "CHEGAR NA CAIXA", "cor": VERDE,
                 "stat": f"ROBÔS NA CAIXA {n1(e0)} → {n1(e1)} DE 5"},
         log=[("NOVO PADRÃO: ENCOSTAR", VERDE)],
         fala=f"Descoberta um: chegar na caixa. Eram {n1(e0)} robôs encostados. Agora, {n1(e1)}.")
    # 2 · EMPURRAR JUNTOS: pico de robôs encostados ao mesmo tempo
    gd2 = primeira(M["pico_a"], lambda v: v > 3.5, fim[1])
    q0, q1 = M["pico_a"][0], M["pico_a"][gd2]
    kd2 = luta(gd2, "junto_a", "vitoria_a", "vitoria")
    marcas2 = [{"tipo": "circulo", "em": 1.0, "alvo": "a", "segue": True, "texto": "TODOS JUNTOS", "rx": 90, "ry": 90}]
    cena(tipo="replay", ger=gd2, foco=kd2, grupo="d2", marcas=marcas2, inicio=0.0,
         cartao={"numero": 2, "rotulo": "ENXAME A", "nome": "EMPURRAR JUNTOS", "cor": VERDE,
                 "stat": f"ROBÔS AO MESMO TEMPO {n1(q0)} → {n1(q1)}"},
         log=[("NOVO PADRÃO: EMPURRAR_EM_GRUPO", VERDE)],
         fala=f"Descoberta dois: empurrar juntos. Cinco empurram o que um não move. O pico foi de {n1(q0)} para {n1(q1)}.")
    # 3 · FICAR ATRÁS DA CAIXA
    gd3 = G - 1
    t0, t1 = M["atras_a"][0], M["atras_a"][gd3]
    kd3 = luta(gd3, "disputa", "mexeu")
    cena(tipo="replay", ger=gd3, foco=kd3, grupo="d3", inicio=0.0,
         cartao={"numero": 3, "rotulo": "OS DOIS", "nome": "COMPORTAMENTO", "cor": VERDE,
                 "stat": f"ENCOSTADOS POR TRÁS {pct(t0)} → {pct(t1)}"},
         log=[("NOVO PADRÃO: EMPURRAR_POR_TRÁS", VERDE)],
         fala=f"Descoberta três: empurrar por trás da caixa. De {pct(t0)} para {pct(t1)}.")

    # ---------------------------------------------------------------- DISPUTA FINAL
    gf = G - 1
    ke = luta(gf, "disputa", "equilibrio")
    cena(tipo="ao_vivo", ger=gf, grupo="fim", log=[(f"GER {G:03d} · OS DOIS TREINADOS", BRANCO)],
         carimbo={"texto": QUEM["AB"][0], "cor": QUEM["AB"][1], "em": 0.2, "sub": f"{FASES[2][2]} GERAÇÕES"},
         fala=f"Agora os dois treinam juntos. Azul vence {pct(M['venc_a'][gf])}, rosa {pct(M['venc_b'][gf])}.")
    cena(tipo="replay", ger=gf, foco=ke, grupo="fim", inicio=0.0,
         fala=f"E {pct(M['empate'][gf])} dos jogos ficam empatados.")

    # ---------------------------------------------------------------- GRÁFICO
    ponto = M["venc_a"] + 0.5 * M["empate"]
    eras = [(L[f][0], L[f][1] + 1, {"A": "SÓ A", "B": "SÓ B", "AB": "OS DOIS"}[FASES[f][1]],
             {"A": COR_A, "B": COR_B, "AB": AMARELO}[FASES[f][1]]) for f in range(len(FASES))]
    cena(tipo="grafico", grupo="grafico", serie=ponto, eras=eras, titulo="PONTOS DO ENXAME AZUL (50% = EQUILÍBRIO)",
         rotulo_y="FAIXAS: QUEM ESTAVA TREINANDO", final=pct(ponto[-1]), log=[(f"GER {G:03d} · A {pct(ponto[-1])}", BRANCO)],
         fala="No gráfico: só o azul treina, sobe. Só o rosa, desce. Juntos, brigam pelo meio.")

    # ---------------------------------------------------------------- TORNEIO
    gA = G - 1
    ep = sorted(set([0, fim[0], fim[1], (fim[1] + G) // 2, G - 1]))
    res = {g: torneio(hist, gA, g, 600) for g in ep}
    itens = [(f"B GER {g + 1}", res[g][0], COR_A) for g in ep]
    sub = "vitórias do azul final · o resto é empate ou rosa"
    cena(tipo="barras", grupo="torneio", itens=itens, titulo="O AZUL FINAL × ROSAS DO PASSADO", sub=sub, revela=0.0,
         destaque=len(ep) - 1, cor_destaque="vermelho", rotulo_destaque="◀ O MAIS NOVO",
         log=[(f"CONTRA O B FINAL: {pct(res[ep[-1]][0])}", VERMELHO)],
         fala=f"O azul final contra rosas do passado: vence {pct(res[ep[0]][0])} da primeira, só {pct(res[ep[-1]][0])} da última.")
    cena(tipo="barras", grupo="torneio", itens=itens, titulo="O AZUL FINAL × ROSAS DO PASSADO", sub=sub, revela=0.0,
         destaque=len(ep) - 1, cor_destaque="vermelho", rotulo_destaque="◀ O MAIS NOVO",
         fala="Aprender ajuda. Mas o outro lado também aprende.")

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    cena(tipo="replay", ger=gh, foco=kh, inicio=0.0,
         escolha={"pergunta": "PRÓXIMO CABO DE GUERRA:", "opcoes": [("5 ROBÔS", COR_A), ("10 ROBÔS", COR_B)], "em": 0.2},
         destaques={"azul": COR_A, "rosa": COR_B},
         fala="Cinco robôs ou dez robôs? Porque tudo começou quando eu…")

    info = {
        "marca": "VÍDEO NEURAL",
        "serie": ponto,
        "serie_rotulo": "PONTOS DO AZUL POR GERAÇÃO",
        "marcos": [(L[f][0], {"A": "SÓ A", "B": "SÓ B", "AB": "OS DOIS"}[FASES[f][1]],
                    {"A": COR_A, "B": COR_B, "AB": AMARELO}[FASES[f][1]]) for f in (0, 1, 2)],
        "rotulo_vivo": "100 JOGOS",
        "rodape": f"POP 100×100 · REDES 14-10-2 · {G} GERAÇÕES · NADA FOI PROGRAMADO, SÓ SELEÇÃO",
    }
    post = (f"Cinco robôs, uma caixa pesada. Sozinho, nenhum move. Treinei dois enxames por seleção natural "
            f"({G} gerações) e eles descobriram sozinhos como chegar na caixa e empurrar juntos. Simulação real, "
            f"nenhum número inventado.\n"
            f"Próximo cabo de guerra: 5 ROBÔS ou 10 ROBÔS? Comenta 5 ou 10 👇\n\n#ia #inteligenciaartificial "
            f"#aprendizadodemaquina #simulacao #enxame #redesneurais #evolucao #tecnologia")
    return cenas, info, post, {"M": M, "L": L}
