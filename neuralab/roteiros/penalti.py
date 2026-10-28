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


def segmentos(cond, minimo=3):
    """[(ini, fim)] dos trechos em que cond é verdadeira por pelo menos `minimo` gerações."""
    out, ini = [], None
    for g, v in enumerate(list(cond) + [False]):
        if v and ini is None:
            ini = g
        elif not v and ini is not None:
            if g - ini >= minimo:
                out.append((ini, g))
            ini = None
    return out


def monta(hist, A):
    ev = eventos(hist)
    M, G = ev["M"], ev["G"]
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    D = {"mentir": BAT, "corpo": BAT, "goleiro": GOL, "goleiros": GOL, "batedor": BAT, "batedores": BAT,
         "mentindo": BAT, "ler": GOL, "lê": GOL, "espera": GOL, "fora": VERMELHO, "ninguém": VERDE,
         "melhores": VERDE, "treinando": GOL}
    numero = [0]

    def prox():
        numero[0] += 1
        return numero[0]

    # ---------------------------------------------------------------- 0-1 · GANCHO (o resultado, já no 1º quadro)
    gf, kf = melhor_lance(A, [ev["finta"] + d for d in range(0, 30)] if ev["finta"] is not None else [], "finta")
    marcas_finta = []
    if gf is not None:
        rod = A.rodada(gf)
        j = rod.jogo
        tc, tp = float(j.chute_t[kf]), float(j.pulo_t[kf])
        marcas_finta = [
            {"tipo": "seta", "em": max(tc - 0.45, 0.05), "alvo": "batedor", "ate": "frente_corpo",
             "texto": f"CORPO: {lado(j.corpo_antes[kf])}", "desloca": (0, -40), "rotulo_no_fim": True},
            {"tipo": "circulo", "em": tp, "alvo": "goleiro", "segue": True, "texto": "CAIU!", "rx": 80, "ry": 70},
            {"tipo": "circulo", "em": float(rod.fim[kf]), "alvo": "bola_fim", "rx": 50, "ry": 50,
             "texto": "BOLA: " + lado(j.alvo[kf]), "desloca": (0, 100)}]
        inicio = max(tc - 1.1, 0.0)
        gancho = [("A IA APRENDEU", BRANCO), ("A MENTIR", BAT)]
        cena(tipo="replay", ger=gf, foco=kf, grupo="gancho", marcas=marcas_finta, inicio=inicio, titulo_gancho=gancho,
             fala="Coloquei duas IAs pra bater pênalti… e o batedor aprendeu a mentir com o corpo.")
        cena(tipo="replay", ger=gf, foco=kf, grupo="gancho", marcas=marcas_finta, inicio=inicio,
             fala="Ninguém ensinou isso pra ele.", pausa=0.25)

    # ---------------------------------------------------------------- 2-3 · PREMISSA + GERAÇÃO 1 (curta)
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[("100 BATEDORES × 100 GOLEIROS", BRANCO), ("CÉREBROS ALEATÓRIOS", BRANCO)],
         fala="Cem batedores contra cem goleiros. Cérebros aleatórios. Só os melhores têm filhos.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · FORA {pct(M['fora'][0])}", VERMELHO)],
         carimbo={"texto": f"FORA {pct(M['fora'][0])}", "cor": "vermelho", "em": 0.6, "sub": "GERAÇÃO 1"},
         fala=f"Geração um: {em_dez(M['fora'][0])} vão pra fora.")

    # ---------------------------------------------------------------- 4-5 · PRIMEIROS APRENDIZADOS (cronológico)
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
                       "texto": "ESPERANDO...", "rx": 80, "ry": 70}]
            cena(tipo="replay", ger=gp, foco=kp, marcas=marcas, inicio=max(float(rod.jogo.chute_t[kp]) - 1.0, 0),
                 cartao={"numero": prox(), "rotulo": "GOLEIRO", "nome": "A PACIÊNCIA", "cor": GOL,
                         "stat": f"PULA ANTES DO CHUTE  {pct(antes)} → {pct(depois)}"},
                 log=[("NOVO PADRÃO: GOLEIRO_ESPERA", GOL)],
                 fala="O goleiro descobre que pular cedo não compensa. Ele espera.")
            marcos.append((g0, "PACIENTE", GOL))
        else:
            g = g0
            cena(tipo="ao_vivo", ger=g,
                 cartao={"numero": prox(), "rotulo": "BATEDOR", "nome": "A MIRA", "cor": BAT,
                         "stat": f"PRA FORA {pct(M['fora'][0])} → {pct(M['fora'][g])} · CHUTE EM {M['tempo_chute'][g]:.1f}s"},
                 carimbo={"texto": f"{M['tempo_chute'][g]:.1f} s".replace(".", ","), "cor": "amarelo", "em": 1.6,
                          "sub": "ATÉ O CHUTE"},
                 log=[(f"GER {g + 1:03d} · FORA {pct(M['fora'][g])}", BAT)],
                 fala=f"Geração {g + 1}: o batedor quase não chuta mais pra fora. E bate em um segundo.")
            marcos.append((g0, "MIRA", BAT))

    # ---------------------------------------------------------------- 6-11 · CALMARIA ENGANOSA → VIRADA DO GOLEIRO
    if ev["leitura"] is not None:
        gl = ev["leitura"]
        ini = (ev["mira"] or 0) + 5
        media = float(M["gol"][ini:gl].mean())
        m0 = (ini + gl) // 2   # segunda metade do platô: é quando o goleiro já está treinando
        meio = m0 + int(np.argmin(np.abs(M["gol"][m0:gl] - media)))   # e o HUD mostra o número falado
        treinando = M["leitura"][meio] > M["leitura"][ini] + 0.1 or M["pulo_antes"][meio] > M["pulo_antes"][ini] + 0.1
        cena(tipo="ao_vivo", ger=meio,
             carimbo={"texto": f"GOLS {pct(M['gol'][meio])}", "cor": "texto", "em": 0.3, "sub": "PLACAR TRAVADO"},
             log=[(f"GER {ini + 1:03d}-{gl:03d} · GOLS ~{pct(media)}", BRANCO)] +
                 ([(f"GOLEIRO PULA ANTES {pct(M['pulo_antes'][meio])}", GOL)] if treinando else []),
             fala=f"{em_dez(media).capitalize()} entram." + (" Mas o goleiro está treinando…" if treinando else ""))
        cena(tipo="ao_vivo", ger=gl, pausa=0.4, fala=f"Até que, na geração {gl + 1}…")
        g2, k2 = melhor_lance(A, range(gl, gl + 15), "leitura")
        if g2 is not None:
            rod = A.rodada(g2)
            j = rod.jogo
            tc = float(j.chute_t[k2])
            marcas = [{"tipo": "seta", "em": max(tc - 0.45, 0.05), "alvo": "batedor", "ate": "frente_corpo",
                       "texto": f"CORPO: {lado(j.corpo_antes[k2])}", "desloca": (0, -40), "rotulo_no_fim": True},
                      {"tipo": "circulo", "em": float(j.pulo_t[k2]), "alvo": "goleiro", "segue": True,
                       "texto": "LEU!", "rx": 80, "ry": 70}]
            cena(tipo="replay", ger=g2, foco=k2, marcas=marcas, grupo="leitura", inicio=max(tc - 1.0, 0),
                 cartao={"numero": prox(), "rotulo": "GOLEIRO", "nome": "A LEITURA", "cor": GOL,
                         "stat": f"ACERTA O LADO EM {pct(M['leitura'][gl])} DOS PULOS"},
                 log=[("NOVO PADRÃO: LER_O_CORPO", GOL)],
                 fala="O goleiro aprende a ler o corpo do batedor.")
            cena(tipo="replay", ger=g2, foco=k2, marcas=marcas, grupo="leitura", inicio=max(tc - 1.0, 0),
                 fala="O corpo aponta. Ele pula. O corpo aponta. Ele pula.")
            marcos.append((gl, "LEITURA", GOL))
        gq = ev["queda"]
        cena(tipo="ao_vivo", ger=gq, log=[(f"ALERTA · GOLS {pct(M['gol'][gq])}", VERMELHO)],
             carimbo={"texto": f"GOLS {pct(M['gol'][gq])}", "cor": GOL, "em": 0.5, "sub": "A MENOR EM 80 GERAÇÕES"
                      if gq > 80 and M["gol"][gq - 80:gq].min() >= M["gol"][gq] else None},
             fala=f"E o gol cai pra {pct(M['gol'][gq])}.")

    # ---------------------------------------------------------------- 12-14 · A RESPOSTA DO BATEDOR
    if ev.get("finta") is not None and gf is not None:
        gfi = ev["finta"]
        rod = A.rodada(gf)
        cena(tipo="replay", ger=gf, foco=kf, grupo="finta2", marcas=marcas_finta,
             inicio=max(float(rod.jogo.chute_t[kf]) - 1.1, 0),
             cartao={"numero": prox(), "rotulo": "BATEDOR", "nome": "A FINTA", "cor": BAT,
                     "stat": f"FINTAS QUE VIRAM GOL  {pct(M['finta_gol'][gf])}"},
             log=[("NOVO PADRÃO: FINTA_DE_CORPO", BAT)],
             fala=f"{gfi - ev['queda']} gerações depois, o batedor responde… mentindo.")
        cena(tipo="replay", ger=gf, foco=kf, grupo="finta2", marcas=marcas_finta,
             inicio=max(float(rod.jogo.chute_t[kf]) - 1.1, 0),
             fala="O corpo mostra um canto. A bola vai no outro.")
        marcos.append((gfi, "FINTA", BAT))
        # montagem: o ciclo se repete (lances reais de ciclos posteriores, alternando leitura e finta)
        ciclos_l = segmentos(M["leitura"] >= 0.8)
        ciclos_f = segmentos(M["finta"] >= 0.45)
        clipes = []
        for (la, lb), fa in zip(ciclos_l[1:], ciclos_f[1:] + [None] * 4):
            gl2, kl2 = melhor_lance(A, range(la, lb + 3), "leitura")
            if gl2 is not None:
                clipes.append((gl2, kl2))
            if fa:
                gf2, kf2 = melhor_lance(A, range(fa[0], fa[1] + 3), "finta")
                if gf2 is not None:
                    clipes.append((gf2, kf2))
        if len(clipes) >= 2:
            cena(tipo="montagem", clipes=clipes[:4], log=[(f"CICLOS LEITURA ↔ FINTA: {ev['ciclos']}", BRANCO)],
                 fala="E não para. Ler, mentir, desconfiar, ler de novo.")

    # ---------------------------------------------------------------- 15 · O GRÁFICO DA CORRIDA ARMAMENTISTA
    final = float(M["gol"][-1])
    eras = [(a, b, "LEITURA", GOL) for a, b in segmentos(M["leitura"] >= 0.8)]
    eras += [(a, b, "FINTA", BAT) for a, b in segmentos(M["finta"] >= 0.45)]
    pro = 0.74 <= final <= 0.82
    cena(tipo="grafico", grupo="grafico", serie=M["gol"], eras=eras, titulo="% DE GOLS POR GERAÇÃO",
         rotulo_y="CADA FAIXA = UMA DESCOBERTA", faixa_ref=(0.75, 0.80, "FUTEBOL PROFISSIONAL ~75-80%") if pro else None,
         final=pct(final), log=[(f"GER {G:03d} · GOLS {pct(final)}", VERDE)],
         fala=f"A leitura apareceu {ev['ciclos']} vezes em {G} gerações. No fim: {pct(final)} de gol."
              + (" A mesma faixa do futebol profissional." if pro else ""))

    # ---------------------------------------------------------------- 16-17 · TORNEIO: o final irônico
    grade = sorted(set(list(range(0, G, 10)) + [G - 1]))
    taxas = {g: torneio(hist, G - 1, g, 1500) for g in grade}
    g_m = min((g for g in grade if g != G - 1), key=lambda g: taxas[g])
    t_m, t_f = taxas[g_m], taxas[G - 1]
    outros = [g for g in grade if g not in (g_m, G - 1)]
    mostra = sorted(set([outros[int(i)] for i in np.linspace(0, len(outros) - 1, 6)] + [g_m, G - 1]))
    itens = [(f"G{g + 1:03d}", taxas[g], GOL) for g in mostra]
    sub = "gols sofridos contra o batedor final · menor = melhor"
    cena(tipo="barras", grupo="torneio", itens=itens, titulo="QUEM DEFENDE MELHOR?", sub=sub,
         log=[(f"TORNEIO: {len(grade)} GOLEIROS × BATEDOR FINAL", BRANCO)], pausa=0.3,
         fala="Aí eu coloquei o batedor final contra goleiros do passado. Quem defende melhor?")
    if t_m < t_f - 0.05:
        cena(tipo="barras", grupo="torneio", itens=itens, titulo="QUEM DEFENDE MELHOR?", sub=sub, revela=0.0,
             destaque=mostra.index(g_m), atual=mostra.index(G - 1), cor_destaque=GOL,
             log=[(f"MELHOR: G{g_m + 1:03d} · {pct(t_m)} (ATUAL {pct(t_f)})", GOL)],
             fala=f"Não é o goleiro atual: {pct(t_f)} de gol. É o da geração {g_m + 1}. Só {pct(t_m)}.")
        cena(tipo="barras", grupo="torneio", itens=itens, titulo="QUEM DEFENDE MELHOR?", sub=sub, revela=0.0,
             destaque=mostra.index(g_m), atual=mostra.index(G - 1), cor_destaque=GOL,
             fala="O batedor aprendeu a vencer o goleiro de hoje. E esqueceu o de ontem.")

    # ---------------------------------------------------------------- 18 · CHAMADA + LAÇO (emenda na 1ª fala)
    if gf is not None:
        rod = A.rodada(gf)
        cena(tipo="replay", ger=gf, foco=kf, inicio=max(float(rod.jogo.chute_t[kf]) - 1.1, 0),
             escolha={"pergunta": "QUAL É O SEU TIME?", "opcoes": [("BATEDOR", BAT), ("GOLEIRO", GOL)], "em": 0.2},
             destaques={"batedor": BAT, "goleiro": GOL},
             fala="Time batedor ou time goleiro? Porque tudo começou quando eu…")

    info = {
        "marca": "VÍDEO NEURAL",
        "serie": M["gol"],
        "serie_rotulo": "% DE GOL POR GERAÇÃO",
        "marcos": marcos,
        "rotulo_vivo": "100 COBRANÇAS",
        "rodape": f"POP 100×100 · REDES 8-10-3 / 9-10-2 · {G} GERAÇÕES · NADA FOI PROGRAMADO, SÓ SELEÇÃO",
    }
    post = (f"Coloquei duas IAs pra bater pênalti uma contra a outra por {G} gerações. "
            f"O batedor aprendeu a mentir com o corpo. Simulação real, nenhum número inventado.\n"
            f"Time batedor ou time goleiro? 👇\n\n#ia #futebol #penalti #inteligenciaartificial #machinelearning "
            f"#simulacao #goleiro #tecnologia")
    return cenas, info, post, ev
