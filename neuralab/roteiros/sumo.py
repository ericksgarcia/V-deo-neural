"""Roteiro do episódio Sumô de IAs: treino só da A, só da B e dos dois, em rodadas curtas e longas.

Regra de ouro: todo número falado sai do treino. O HUD mostra a mesma média móvel (5 gerações,
sem atravessar o início de uma fase), então o número que aparece na tela é o número falado.
"""
import numpy as np

from ..adaptadores.sumo import COR_A, COR_B
from ..coevolucao_sumo import FASES, limites_fases, suave_fase, torneio

BRANCO = (0.92, 0.96, 1.0)
VERDE, VERMELHO, AMARELO = (0.3, 1.0, 0.62), (1.0, 0.3, 0.38), (1.0, 0.74, 0.12)
RODADA = ["CURTO", "MÉDIO", "LONGO"]
QUEM = {"A": ("SÓ A TREINA", COR_A), "B": ("SÓ B TREINA", COR_B), "AB": ("OS DOIS TREINAM", AMARELO)}


def pct(x):
    return f"{100 * x:.0f}%"


def em_dez(x):
    n = int(round(x * 10))
    nomes = ["nenhum", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"]
    return f"{nomes[n]} em cada dez"


def series(hist):
    f = hist["fase"]
    return {k[2:]: suave_fase(v, f) for k, v in hist.items() if k.startswith("m_")}


def nota_historia(hist):
    """Quão limpa é a história: quem treina sozinho sobe e o congelado cai; juntos, ficam parelhos."""
    M, L = series(hist), limites_fases()
    pts = 0.0
    for f, (_, quem, _) in enumerate(FASES):
        a0 = (L[f - 1][1] if f else 0)
        a1 = L[f][1]
        da = M["venc_a"][a1] - M["venc_a"][a0]
        db = M["venc_b"][a1] - M["venc_b"][a0]
        if quem == "A":
            pts += (da > 0.04) + (db < -0.04)
        elif quem == "B":
            pts += (db > 0.04) + (da < -0.04)
        else:
            pts += abs(M["venc_a"][a1] - M["venc_b"][a1]) < 0.12
    return pts + 0.5 * (M["empate"][-1] > 0.4) + 0.5 * (M["sozinho"][-1] < 0.05)


def monta(hist, A):
    M, L = series(hist), limites_fases()
    G = len(hist["A"])
    fim = [b for _, b in L]
    cenas = []

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    D = {"azul": COR_A, "rosa": COR_B, "A": COR_A, "B": COR_B, "só": AMARELO, "juntas": AMARELO,
         "congelada": BRANCO, "empate": VERDE, "empatam": VERDE, "espera": VERDE, "esperar": VERDE,
         "sozinho": VERMELHO, "cai": VERMELHO}

    def de(f, k):
        """valor antes -> depois da fase f."""
        return M[k][fim[f - 1]] if f else M[k][0], M[k][fim[f]]

    def luta(g, tipo, *alternativas):
        rod = A.rodada(g)
        for t in (tipo,) + alternativas:
            k = A.busca(rod, t)
            if k is not None:
                return k
        return None

    # ---------------------------------------------------------------- GANCHO: o auge do treino só-da-rosa
    gh = fim[7]
    kh = luta(gh, "empurrao_b", "rapida")
    marcas = [{"tipo": "circulo", "em": 0.2, "alvo": "b", "segue": True, "texto": "TREINADA", "rx": 110, "ry": 110},
              {"tipo": "circulo", "em": 0.2, "alvo": "a", "segue": True, "texto": "CONGELADA", "rx": 110, "ry": 110}]
    cena(tipo="replay", ger=gh, foco=kh, grupo="gancho", marcas=marcas, inicio=0.0,
         titulo_gancho=[("TREINEI SÓ", BRANCO), ("UM LADO", COR_B)],
         fala="Treinei só uma de duas IAs de sumô. Olha o que aconteceu.")
    # ---------------------------------------------------------------- PREMISSA + GERAÇÃO 1
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[("SUMÔ · A AZUL × B ROSA", BRANCO), ("QUEM SAIR DO CÍRCULO PERDE", BRANCO)],
         fala="A azul e a rosa. Quem sair do círculo perde. E ele vai fechando.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · CAEM SOZINHAS {pct(M['sozinho'][0])}", VERMELHO)],
         carimbo={"texto": f"SOZINHAS {pct(M['sozinho'][0])}", "cor": "vermelho", "em": 0.5, "sub": "GERAÇÃO 1"},
         fala=f"No começo, {em_dez(M['sozinho'][0])} lutas acabam com alguém caindo sozinho.")
    # ---------------------------------------------------------------- RODADA 1 · TREINO CURTO
    f = 0
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r1a", carimbo={"texto": QUEM["A"][0], "cor": QUEM["A"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO CURTO · SÓ A · {FASES[f][2]} GER", COR_A)],
         fala=f"Treino curto, só na azul. Ela sobe de {pct(a0)} para {pct(a1)}. A rosa cai para {pct(b1)}.")
    f = 1
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r1b", carimbo={"texto": QUEM["B"][0], "cor": QUEM["B"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO CURTO · SÓ B · {FASES[f][2]} GER", COR_B)],
         fala=f"Só na rosa: ela vai de {pct(b0)} para {pct(b1)}.")
    f = 2
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r1c", carimbo={"texto": QUEM["AB"][0], "cor": QUEM["AB"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO CURTO · OS DOIS · {FASES[f][2]} GER", AMARELO)],
         fala=f"As duas juntas: empate técnico. Azul {pct(a1)}, rosa {pct(b1)}.")

    # ---------------------------------------------------------------- RODADA 2 · TREINO MÉDIO
    f = 3
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r2a", carimbo={"texto": QUEM["A"][0], "cor": QUEM["A"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO MÉDIO · SÓ A · {FASES[f][2]} GER", COR_A)], pausa=0.15,
         fala=f"Treino médio. Só na azul: a rosa despenca de {pct(b0)} para {pct(b1)}.")
    f = 4
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r2b", carimbo={"texto": QUEM["B"][0], "cor": QUEM["B"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO MÉDIO · SÓ B · {FASES[f][2]} GER", COR_B)],
         fala=f"Só na rosa: a azul cai de {pct(a0)} para {pct(a1)}.")
    f = 5
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r2c", carimbo={"texto": QUEM["AB"][0], "cor": QUEM["AB"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO MÉDIO · OS DOIS · {FASES[f][2]} GER", AMARELO)],
         fala="Juntas, ficam parelhas de novo.")

    # ---------------------------------------------------------------- DESCOBERTAS (aparecem com treino longo)
    fs = fim[5]
    s0, s1 = M["sozinho"][0], M["sozinho"][fs]
    cena(tipo="ao_vivo", ger=fs, grupo="d1",
         cartao={"numero": 1, "rotulo": "AS DUAS", "nome": "NÃO CAIR SOZINHA", "cor": VERDE,
                 "stat": f"CAEM SOZINHAS {pct(s0)} → {pct(s1)}"},
         log=[("NOVO PADRÃO: FICAR_NA_ARENA", VERDE)],
         fala=f"Descoberta: não cair sozinha. De {pct(s0)} das lutas para {pct(s1)}.")

    # ---------------------------------------------------------------- RODADA 3 · TREINO LONGO
    f = 6
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r3a", carimbo={"texto": QUEM["A"][0], "cor": QUEM["A"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO LONGO · SÓ A · {FASES[f][2]} GER", COR_A)],
         fala=f"Treino longo. Só na azul: a rosa cai para {pct(b1)}.")
    f = 7
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r3b", carimbo={"texto": QUEM["B"][0], "cor": QUEM["B"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO LONGO · SÓ B · {FASES[f][2]} GER", COR_B)],
         fala=f"Só na rosa: ela sobe a {pct(b1)}. A azul cai para {pct(a1)}.")
    f = 8
    a0, a1 = de(f, "venc_a"); b0, b1 = de(f, "venc_b")
    e0, e1 = de(f, "empate")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r3c", carimbo={"texto": QUEM["AB"][0], "cor": QUEM["AB"][1], "em": 0.2,
                                                             "sub": f"{RODADA[f // 3]} · {FASES[f][2]} GERAÇÕES"},
         log=[(f"TREINO LONGO · OS DOIS · {FASES[f][2]} GER", AMARELO)],
         fala=f"As duas juntas por {FASES[f][2]} gerações:")
    cena(tipo="ao_vivo", ger=fim[f], grupo="r3c",
         cartao={"numero": 2, "rotulo": "AS DUAS", "nome": "O EMPATE", "cor": VERDE,
                 "stat": f"LUTAS EMPATADAS {pct(M['empate'][0])} → {pct(e1)}"},
         log=[(f"EMPATES {pct(e1)}", VERDE)],
         fala=f"metade das lutas empata. Eram só {pct(M['empate'][0])}.")

    # ---------------------------------------------------------------- A ESPERA (lance real, treino longo)
    esp = (M["espera_a"] + M["espera_b"]) / 2
    ge = fim[8]
    ke = luta(ge, "espera_b", "espera_a", "rapida")
    ladoe = "b" if A.rodada(ge).jogo.arrancadas[1][ke] == 0 else "a"
    marcas = [{"tipo": "circulo", "em": 0.8, "alvo": ladoe, "segue": True, "texto": "ESPERANDO", "rx": 80, "ry": 80}]
    cena(tipo="replay", ger=ge, foco=ke, grupo="esp", marcas=marcas, inicio=0.0,
         cartao={"numero": 3, "rotulo": "AS DUAS", "nome": "A ESPERA", "cor": VERDE,
                 "stat": f"PARADAS NO CENTRO {pct(esp[0])} → {pct(esp[ge])}"},
         log=[("NOVO PADRÃO: ESPERAR_NO_CENTRO", VERDE)],
         fala="Outro truque: esperar no centro.")
    cena(tipo="replay", ger=ge, foco=ke, grupo="esp", marcas=marcas, inicio=0.0,
         fala=f"Aos dois segundos, {pct(esp[ge])} estão paradas lá.")

    # ---------------------------------------------------------------- GRÁFICO: o ziguezague
    ponto = M["venc_a"] + 0.5 * M["empate"]
    eras = [(L[f][0], L[f][1] + 1, {"A": "SÓ A", "B": "SÓ B", "AB": "OS DOIS"}[FASES[f][1]],
             {"A": COR_A, "B": COR_B, "AB": AMARELO}[FASES[f][1]]) for f in range(len(FASES))]
    cena(tipo="grafico", grupo="grafico", serie=ponto, eras=eras, titulo="PONTOS DA IA AZUL (50% = EQUILÍBRIO)",
         rotulo_y="FAIXAS: QUEM ESTAVA TREINANDO", final=pct(ponto[-1]), log=[(f"GER {G:03d} · A {pct(ponto[-1])}", BRANCO)],
         fala="No gráfico: só a azul, sobe. Só a rosa, desce. Juntas, volta pro meio.")

    # ---------------------------------------------------------------- TORNEIO: a azul final contra rosas de cada época
    gA = G - 1
    ep = sorted(set([0, fim[1], fim[4], fim[6], fim[7], G - 1]))
    res = {g: torneio(hist, gA, g, 900) for g in ep}
    itens = [(f"ROSA GER {g + 1}", res[g][0], COR_A) for g in ep]
    sub = "vitórias da azul · o resto é empate ou rosa"
    cena(tipo="barras", grupo="torneio", itens=itens, titulo="A AZUL FINAL × ROSAS DO PASSADO", sub=sub, revela=0.0,
         destaque=len(ep) - 1, cor_destaque="vermelho", rotulo_destaque="◀ A MAIS NOVA",
         log=[(f"CONTRA A B FINAL: {pct(res[ep[-1]][0])}", VERMELHO)],
         fala=f"Azul final contra rosas do passado: vence {pct(res[ep[0]][0])} da primeira, só {pct(res[ep[-1]][0])} da final.")
    cena(tipo="barras", grupo="torneio", itens=itens, titulo="A AZUL FINAL × ROSAS DO PASSADO", sub=sub, revela=0.0,
         destaque=len(ep) - 1, cor_destaque="vermelho", rotulo_destaque="◀ A MAIS NOVA",
         fala="Treinar ajuda. Mas o outro lado também evolui.")

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    cena(tipo="replay", ger=gh, foco=kh, inicio=0.0,
         escolha={"pergunta": "TREINARIA QUAL LADO?", "opcoes": [("SÓ A AZUL", COR_A), ("SÓ A ROSA", COR_B), ("AS DUAS", AMARELO)], "em": 0.2},
         destaques={"azul": COR_A, "rosa": COR_B},
         fala="Você treinaria só a azul, só a rosa ou as duas? Porque tudo começou quando eu…")

    info = {
        "marca": "VÍDEO NEURAL",
        "serie": ponto,
        "serie_rotulo": "PONTOS DA AZUL POR GERAÇÃO",
        "marcos": [(L[f][0], {"A": "SÓ A", "B": "SÓ B", "AB": "OS DOIS"}[FASES[f][1]],
                    {"A": COR_A, "B": COR_B, "AB": AMARELO}[FASES[f][1]]) for f in (0, 1, 2)],
        "rotulo_vivo": "600 LUTAS",
        "rodape": f"POP 100×100 · REDES 9-10-3 · {G} GERAÇÕES · NADA FOI PROGRAMADO, SÓ SELEÇÃO",
    }
    post = (f"Treinei só UM lado de duas IAs de sumô. O outro lado nunca perdoou. Treinos curtos, médios e longos, "
            f"só a azul, só a rosa e as duas juntas ({G} gerações no total). Quem treina sozinho sobe, quem fica "
            f"congelado cai, e juntas elas empatam. Simulação real, nenhum número inventado.\n"
            f"Você treinaria só a azul, só a rosa ou as duas? Comenta A, B ou AB 👇\n\n#ia #inteligenciaartificial "
            f"#aprendizadodemaquina #simulacao #sumo #redesneurais #evolucao #tecnologia")
    return cenas, info, post, {"M": M, "L": L}
