"""Roteiro do episódio Pênalti: detecta os acontecimentos nos dados e escreve as cenas.

Regra de ouro: todo número falado sai do treino. Se um acontecimento não ocorrer
nesta semente, a cena correspondente simplesmente não entra.
"""
import numpy as np

from ..coevolucao import torneio
from ..adaptadores.penalti import AMARELO, AZUL

VERDE, VERMELHO, BRANCO = (0.3, 1.0, 0.62), (1.0, 0.3, 0.38), (0.92, 0.96, 1.0)
BAT, GOL = AMARELO, AZUL


def suave(x, k=7):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def pct(x):
    return f"{100 * x:.0f}%"


def em_dez(x):
    """0.42 -> 'quatro em cada dez'."""
    n = int(round(x * 10))
    nomes = ["nenhum", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"]
    return f"{nomes[n]} em cada dez"


def eventos(hist):
    M = {k[2:]: suave(v) for k, v in hist.items() if k.startswith("m_")}
    G = len(M["gol"])
    ev = {"G": G, "M": M}
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev["mira"] = primeiro(lambda g: M["fora"][g] <= 0.08)
    ev["paciente"] = primeiro(lambda g: M["pulo_antes"][g] <= 0.02)
    ini = max(ev["paciente"] or 0, ev["mira"] or 0) + 10
    ev["leitura"] = primeiro(lambda g: M["leitura"][g] >= 0.85 and M["pulo_antes"][g] >= 0.2, ini)
    if ev["leitura"] is not None:
        a = ev["leitura"]
        ev["queda"] = a + int(np.argmin(M["gol"][a:a + 15]))
        ev["finta"] = primeiro(lambda g: M["finta"][g] >= 0.45, a + 3)
    else:
        ev["queda"] = ev["finta"] = None
    if ev.get("finta") is not None:
        f = ev["finta"]
        ev["desaprende"] = f + int(np.argmin(M["leitura"][f:f + 15]))
    # quantas vezes a leitura voltou a ficar forte (ciclos)
    forte = M["leitura"] >= 0.8
    ev["ciclos"] = int(((forte[1:]) & (~forte[:-1])).sum())
    return ev


def melhor_lance(A, gens, tipo):
    for g in gens:
        if 0 <= g < A.total_ger:
            rod = A.rodada(g)
            k = A.busca(rod, tipo)
            if k is not None:
                return g, k
    return None, None


def lado(x):
    return "ESQUERDA" if x < 0 else "DIREITA"


def monta(hist, A):
    ev = eventos(hist)
    M, G = ev["M"], ev["G"]
    m = lambda chave, g: float(hist["m_" + chave][g])
    cenas = []
    marcos = []

    def cena(**kw):
        kw.setdefault("destaques", {})
        cenas.append(kw)
        return kw

    D = {"mentir": BAT, "corpo": BAT, "pênalti": BRANCO, "goleiro": GOL, "goleiros": GOL, "batedor": BAT, "batedores": BAT, "enganar": BAT, "mentindo": BAT,
         "ler": GOL, "lê": GOL, "espera": GOL, "fora": VERMELHO, "ninguém": VERDE}

    # 1-2 · GANCHO: o comportamento mais impressionante, já no primeiro segundo
    gf, kf = melhor_lance(A, [ev["finta"] + d for d in range(0, 30)] if ev["finta"] is not None else [], "finta")
    if gf is not None:
        rod = A.rodada(gf)
        j = rod.jogo
        tc, tp = float(j.chute_t[kf]), float(j.pulo_t[kf])
        marcas = [{"tipo": "seta", "em": max(tc - 0.45, 0.05), "alvo": "batedor", "ate": "frente_corpo",
                   "texto": f"CORPO: {lado(j.corpo_antes[kf])}", "desloca": (0, -40), "rotulo_no_fim": True},
                  {"tipo": "circulo", "em": tp, "alvo": "goleiro", "segue": True, "texto": "CAIU!"},
                  {"tipo": "circulo", "em": float(rod.fim[kf]), "alvo": "bola_fim", "rx": 60, "ry": 60,
                   "texto": "BOLA: " + lado(j.alvo[kf]), "desloca": (0, 110)}]
        cena(tipo="replay", ger=gf, foco=kf, grupo="gancho", marcas=marcas, destaques=D,
             fala="Coloquei duas IAs pra bater pênalti… e o batedor aprendeu a mentir com o corpo.")
        cena(tipo="replay", ger=gf, foco=kf, grupo="gancho", marcas=marcas, destaques=D,
             fala="Ninguém ensinou isso pra ele.", pausa=0.3)

    # 3-5 · PREMISSA + GERAÇÃO 1
    log1 = [("EXPERIMENTO 004 // PÊNALTI", BRANCO), ("100 BATEDORES × 100 GOLEIROS", BRANCO)]
    cena(tipo="ao_vivo", ger=0, grupo="g1", destaques=D, log=log1,
         fala="Dois times de IA. Cem batedores contra cem goleiros.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", destaques=D,
         fala="Cérebros aleatórios. Nenhum deles sabe o que é futebol.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", destaques=D, log=[(f"GER 001 · FORA {pct(m('fora', 0))}", VERMELHO)],
         fala=f"Geração um: {em_dez(m('fora', 0))} chutes vão pra fora.")

    # 6 · REGRA DO JOGO (seleção)
    cena(tipo="ao_vivo", ger=min(8, G - 1), destaques=D, log=[("SELEÇÃO: OS MELHORES TÊM FILHOS", BRANCO)],
         fala="A cada geração, só os melhores de cada lado têm filhos.")

    # 7-8 · PRIMEIRO APRENDIZADO DE CADA LADO (em ordem cronológica)
    numero = [0]

    def prox():
        numero[0] += 1
        return numero[0]

    blocos = []
    if ev["paciente"] is not None:
        g0 = ev["paciente"]
        gp, kp = melhor_lance(A, range(g0, g0 + 20), "paciente")
        if gp is not None:
            blocos.append((g0, "paciente", gp, kp))
    if ev["mira"] is not None:
        blocos.append((ev["mira"], "mira", None, None))
    for g0, tipo, gp, kp in sorted(blocos):
        if tipo == "paciente":
            rod = A.rodada(gp)
            antes, depois = M["pulo_antes"][:5].max(), M["pulo_antes"][g0]
            marcas = [{"tipo": "circulo", "em": float(rod.jogo.chute_t[kp]) - 0.25, "alvo": "goleiro", "segue": True,
                       "texto": "ESPERANDO..."}]
            cena(tipo="replay", ger=gp, foco=kp, marcas=marcas, destaques=D,
                 cartao={"numero": prox(), "rotulo": "GOLEIRO", "nome": "A PACIÊNCIA", "cor": GOL,
                         "stat": f"PULA ANTES DO CHUTE  {pct(antes)} → {pct(depois)}"},
                 log=[("NOVO PADRÃO: GOLEIRO_ESPERA", GOL)],
                 fala="O goleiro descobre que pular cedo não compensa. Ele espera.")
            marcos.append((g0, "PACIENTE", GOL))
        else:
            g = g0
            cena(tipo="ao_vivo", ger=g, destaques=D,
                 cartao={"numero": prox(), "rotulo": "BATEDOR", "nome": "A MIRA", "cor": BAT,
                         "stat": f"PRA FORA {pct(m('fora', 0))} → {pct(M['fora'][g])} · CHUTE EM {M['tempo_chute'][g]:.1f}s"},
                 log=[(f"GER {g + 1:03d} · FORA {pct(M['fora'][g])} · CHUTE {M['tempo_chute'][g]:.1f}s", BAT)],
                 fala=f"Geração {g + 1}: o batedor quase não chuta mais pra fora. E bate em um segundo.")
            marcos.append((g0, "MIRA", BAT))

    # 9-12 · CALMARIA... E A VIRADA DO GOLEIRO
    if ev["leitura"] is not None:
        gl = ev["leitura"]
        ini = (ev["mira"] or 0) + 5
        media = float(M["gol"][ini:gl].mean())
        meio = (ini + gl) // 2
        treinando = M["leitura"][meio] > M["leitura"][ini] + 0.1 or M["pulo_antes"][meio] > M["pulo_antes"][ini] + 0.1
        cena(tipo="ao_vivo", ger=meio, destaques=D,
             log=[(f"GER {ini + 1:03d}-{gl:03d} · GOLS ~{pct(media)} · PLACAR TRAVADO", BRANCO)] +
                 ([(f"GER {meio + 1:03d} · GOLEIRO PULA ANTES {pct(M['pulo_antes'][meio])}", GOL)] if treinando else []),
             fala=f"Daí pra frente, o placar trava. {em_dez(media).capitalize()} bolas entram."
                  + (" Mas o goleiro está treinando." if treinando else ""))
        cena(tipo="ao_vivo", ger=gl, destaques=D, pausa=0.45, fala=f"Até que, na geração {gl + 1}…")
        g2, k2 = melhor_lance(A, range(gl, gl + 15), "leitura")
        if g2 is not None:
            rod = A.rodada(g2)
            j = rod.jogo
            tc = float(j.chute_t[k2])
            marcas = [{"tipo": "seta", "em": max(tc - 0.45, 0.05), "alvo": "batedor", "ate": "frente_corpo",
                       "texto": f"CORPO: {lado(j.corpo_antes[k2])}", "desloca": (0, -40), "rotulo_no_fim": True},
                      {"tipo": "circulo", "em": float(j.pulo_t[k2]), "alvo": "goleiro", "segue": True,
                       "texto": "LEU!"}]
            cena(tipo="replay", ger=g2, foco=k2, marcas=marcas, destaques=D, grupo="leitura",
                 cartao={"numero": prox(), "rotulo": "GOLEIRO", "nome": "A LEITURA", "cor": GOL,
                         "stat": f"ACERTA O LADO EM {pct(M['leitura'][gl])} DOS PULOS"},
                 log=[("NOVO PADRÃO: LER_O_CORPO", GOL)],
                 fala="O goleiro aprende a ler o corpo do batedor.")
            cena(tipo="replay", ger=g2, foco=k2, marcas=marcas, destaques=D, grupo="leitura",
                 fala="O corpo aponta. Ele pula. O corpo aponta. Ele pula.")
            marcos.append((gl, "LEITURA", GOL))
        gq = ev["queda"]
        pior = float(M["gol"][gq])
        cena(tipo="ao_vivo", ger=gq, destaques=D, log=[(f"ALERTA · GOLS {pct(pior)}", VERMELHO)],
             fala=f"E o gol cai pra {pct(pior)}.")

    # 13-14 · A RESPOSTA DO BATEDOR
    if ev.get("finta") is not None and gf is not None:
        gfi = ev["finta"]
        cena(tipo="replay", ger=gf, foco=kf, destaques=D, grupo="finta2",
             cartao={"numero": prox(), "rotulo": "BATEDOR", "nome": "A FINTA", "cor": BAT,
                     "stat": f"FINTAS QUE VIRAM GOL  {pct(m('finta_gol', gf))}"},
             log=[("NOVO PADRÃO: FINTA_DE_CORPO", BAT)],
             marcas=cenas[0]["marcas"],
             fala=f"{gfi - ev['queda']} gerações depois, o batedor responde… mentindo.")
        cena(tipo="replay", ger=gf, foco=kf, destaques=D, grupo="finta2", marcas=cenas[0]["marcas"],
             fala="O corpo mostra um canto. A bola vai no outro.")
        marcos.append((gfi, "FINTA", BAT))
        gd = ev["desaprende"]
        parou = M["pulo_antes"][gd] < 0.5 * M["pulo_antes"][ev["queda"]]
        cena(tipo="ao_vivo", ger=gd, destaques=D,
             log=[(f"GER {gd + 1:03d} · ACERTA O LADO {pct(M['leitura'][gd])} · PULA ANTES {pct(M['pulo_antes'][gd])}", GOL)],
             fala="Agora, quem lê o corpo cai na mentira." + (" E o goleiro para de pular antes." if parou else ""))

    # 15-16 · O CICLO + EQUILÍBRIO
    final = float(M["gol"][-1])
    eras = []
    if ev["paciente"] is not None:
        eras.append((ev["paciente"], ev["leitura"] or G, "ESPERA", GOL))
    if ev["leitura"] is not None:
        eras.append((ev["leitura"], ev.get("finta") or G, "LEITURA", GOL))
    if ev.get("finta") is not None:
        eras.append((ev["finta"], ev.get("desaprende", G) + 1, "FINTA", BAT))
    cena(tipo="grafico", serie=M["gol"], eras=eras, titulo="% DE GOLS POR GERAÇÃO", rotulo_y="GOLS",
         log=[(f"CICLOS LEITURA ↔ FINTA: {ev['ciclos']}", BRANCO)], destaques=D,
         fala=f"E não para. Ler, mentir, desconfiar, ler de novo. A leitura apareceu {ev['ciclos']} vezes em {G} gerações.")
    cena(tipo="grafico", serie=M["gol"], eras=eras, titulo="% DE GOLS POR GERAÇÃO", rotulo_y="GOLS",
         destaques=D, log=[(f"GER {G:03d} · GOLS {pct(final)}", VERDE)],
         fala=f"No fim: {pct(final)} de gol." + (" A mesma faixa do futebol profissional." if 0.74 <= final <= 0.82 else ""))

    # 17-19 · TORNEIO: o final irônico
    gens = sorted(set(list(range(0, G, max(G // 15, 1))) + [G - 1]))
    taxas = [torneio(hist, G - 1, g, 1500) for g in gens]
    i_min = int(np.argmin(taxas[:-1]))
    itens = [(f"GOLEIRO G{g + 1:03d}", 1 - tx, GOL) for g, tx in zip(gens, taxas)]
    cena(tipo="barras", itens=itens, titulo="QUEM DEFENDE MAIS?", sub="contra o batedor final · 1.500 cobranças",
         destaques=D, log=[(f"TORNEIO: {len(gens)} GOLEIROS × BATEDOR FINAL", BRANCO)],
         fala="Aí eu coloquei o batedor final contra goleiros do passado. Quem defende melhor?",
         pausa=0.4)
    g_m, t_m, t_f = gens[i_min], taxas[i_min], taxas[-1]
    if t_m < t_f - 0.05:
        cena(tipo="barras", itens=itens, destaque=i_min, titulo="QUEM DEFENDE MAIS?", revela=0.0,
             sub="contra o batedor final · 1.500 cobranças", destaques=D,
             log=[(f"MELHOR: G{g_m + 1:03d} · GOLS SOFRIDOS {pct(t_m)} (ATUAL {pct(t_f)})", AMARELO)],
             fala=f"Não é o goleiro atual: contra ele, {pct(t_f)} de gol. É o da geração {g_m + 1}. Só {pct(t_m)}.")
        cena(tipo="barras", itens=itens, destaque=i_min, titulo="QUEM DEFENDE MAIS?", revela=0.0,
             sub="contra o batedor final · 1.500 cobranças", destaques=D,
             fala="O batedor aprendeu a vencer o goleiro de hoje. E esqueceu como vencer o de ontem.")
    # 20 · CHAMADA
    cena(tipo="final", pergunta="E AÍ, QUAL É O SEU TIME?", opcoes=[("TIME BATEDOR", BAT), ("TIME GOLEIRO", GOL)],
         destaques={"batedor": BAT, "goleiro": GOL, "mentiroso": BAT, "ler": GOL},
         fala="O mentiroso ou o que aprendeu a ler? Time batedor ou time goleiro?")

    serie = M["gol"]
    info = {
        "marca": "VÍDEO NEURAL",
        "serie": serie,
        "serie_rotulo": "% DE GOL POR GERAÇÃO",
        "marcos": marcos,
        "rodape": f"POP 100×100 · REDES 8-10-3 / 9-10-2 · {G} GERAÇÕES · NADA FOI PROGRAMADO, SÓ SELEÇÃO",
    }
    post = (f"Coloquei duas IAs pra bater pênalti uma contra a outra por {G} gerações. "
            f"O batedor aprendeu a fintar. Simulação real, nenhum número inventado.\n"
            f"Time batedor ou time goleiro? 👇\n\n#ia #futebol #penalti #inteligenciaartificial #machinelearning "
            f"#simulacao #goleiro #tecnologia")
    return cenas, info, post, ev
