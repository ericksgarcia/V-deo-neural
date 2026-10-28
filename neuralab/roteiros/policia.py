"""Roteiro do episódio Polícia x Ladrão: detecta os acontecimentos nos dados e escreve as cenas.

Todo número falado sai do treino (curvas guardadas ou re-simulação medida aqui). Se um acontecimento
não ocorrer nesta semente, a cena correspondente simplesmente não entra.
"""
import numpy as np

from ..adaptadores.policia import LADRAO, POLICIA
from ..desafios.policia import PASSOS
from ..palco.holo import VERDE, VERMELHO
from ..perseguicao import partidas, torneio

BRANCO = (0.92, 0.96, 1.0)
LAD, POL = LADRAO, POLICIA

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend who just discovered something amazing. Natural spoken Brazilian rhythm; "
    "pace brisk and conversational, about three words per second, never rushed, never dragging. Emotional arc: "
    "open intrigued and confident, then conspiratorial, as if sharing a secret; explain the rules calmly with a "
    "hint of dry humor; say 'Preso' coldly; build tension before each discovery and let it land with honest "
    "surprise; slow down on the big numbers; sound a little suspicious at the stalled scoreboard; finish playful "
    "and provocative, inviting the viewer to pick a side.")
D = {"ladrão": LAD, "ladrões": LAD, "diamantes": LAD, "diamante": LAD, "roubar": LAD, "rouba": LAD,
     "polícia": POL, "policiais": POL, "preso": VERMELHO, "presos": VERMELHO, "cercam": POL, "cerco": POL,
     "ninguém": VERDE, "sozinha": VERDE, "escapou": VERDE}
NOMES = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"]


def pct(x):
    return f"{100 * x:.0f}%"


def em_dez(x):
    n = int(round(x * 10))
    quase = "quase " if x * 10 < n - 0.15 else ""
    return f"{quase}{NOMES[n]} em cada dez"


def vir(x):
    return f"{x:.1f}".replace(".", ",")


def suave(x, k=7):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def medidas(hist, g):
    """Comportamentos medidos re-simulando a geração g (mesmas partidas que o vídeo mostra)."""
    pop = len(hist["lad"][g])
    sem = int(hist["semente"][g])
    il = np.repeat(np.arange(pop), 4)
    ip = np.random.default_rng(sem).permutation(np.tile(np.arange(pop), 4))
    j, reg = partidas(hist["lad"][g], hist["pol"][g], il, ip, sem, gravar=True)
    viv = reg["estado"][:, 1:] == 0
    vl = np.linalg.norm(np.diff(reg["pl"], axis=1), axis=2) / j.dt
    vp = np.linalg.norm(np.diff(reg["pp"], axis=1), axis=3) / j.dt
    return {"corre": float(((vl > 2.0) & viv).sum() / viv.sum()),
            "parado": float(((vp < 0.5) & viv[..., None]).sum() / viv.sum() / 2),
            "rouba": float((j.diamantes > 0).mean()), "rouba2": float((j.diamantes > 1).mean()),
            "diam": float(j.diamantes.mean())}


def lance(A, gens, tipo):
    for g in gens:
        if 0 <= g < A.total_ger:
            rod = A.rodada(g)
            k = A.busca(rod, tipo)
            if k is not None:
                return g, k
    return None, None


def primeiro(cond, G, ini=0):
    return next((g for g in range(ini, G) if cond(g)), None)


def monta(hist, A):
    M = {k[2:]: suave(v) for k, v in hist.items() if k.startswith("m_")}
    G = len(M["preso"])
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    gp = primeiro(lambda g: M["preso"][g] >= 0.5, G)
    gr = primeiro(lambda g: M["diamantes"][g] >= 0.5, G)
    gc = primeiro(lambda g: M["cerco_frac"][g] >= 0.07 and M["cerco_frac"][:5].max() <= 0.04, G, (gp or 0) + 5)
    m0, mf = medidas(hist, 0), medidas(hist, G - 1)
    mp = medidas(hist, gp) if gp is not None else None
    final = float(M["preso"][-1])
    d0, df = float(M["diamantes"][0]), float(M["diamantes"][-1])

    def f(rod, k):
        return float(rod.fim[k])

    # ---------------------------------------------------------------- GANCHO: o ladrão rico que escapou
    gh, kh = lance(A, range(G - 1, G - 40, -1), "rico")
    if gh is None:
        gh, kh = lance(A, range(G - 1, 0, -1), "escapou")
    rod = A.rodada(gh)
    nd = int(rod.jogo.diamantes[kh])
    marcas_h = [{"tipo": "circulo", "em": max(f(rod, kh) - 1.0, 0.1), "alvo": "ladrao", "segue": True,
                 "texto": f"MELHOR LADRÃO · {nd} DIAMANTES", "rx": 80, "ry": 70}]
    cena(tipo="replay", ger=gh, foco=kh, grupo="gancho", marcas=marcas_h, inicio=max(f(rod, kh) - 8, 0),
         titulo_gancho=[("A IA APRENDEU", BRANCO), ("A ROUBAR E PRENDER", LAD)],
         fala="Dois policiais atrás de um ladrão. <short pause> Ninguém ensinou ninguém a correr nem a perseguir. Olha o que aprenderam sozinhos.")
    # ---------------------------------------------------------------- PREMISSA + GERAÇÃO 1
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[("100 LADRÕES × 100 DUPLAS DE POLÍCIA", BRANCO),
                                               ("CÉREBROS VAZIOS", BRANCO)],
         fala="Cem ladrões. Cem duplas de polícia. Cérebros vazios. <short pause> O ladrão quer diamantes. "
              "A polícia quer prender.")
    cena(tipo="ao_vivo", ger=min(5, G - 1), log=[("OS MELHORES TÊM FILHOS", VERDE), ("OS PIORES SAEM", VERMELHO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": "verde", "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="Quem rouba mais, ou prende mais, tem filhos. <short pause> Os outros? Eliminados.")

    achados = []   # (geração, cena) de cada descoberta; entram em ordem cronológica e numeradas de 1 a n

    def achado(g, **kw):
        achados.append((g, kw))

    cena(tipo="ao_vivo", ger=0, grupo="g1",
         log=[(f"GER 001 · PRESOS {pct(M['preso'][0])}", VERMELHO)],
         carimbo={"texto": f"PRESOS {pct(M['preso'][0])}", "cor": "vermelho", "em": 0.6, "sub": "GERAÇÃO 1"},
         fala=f"Geração um: só {em_dez(M['preso'][0])} são presos. <short pause> "
              f"E os policiais ficam parados {pct(m0['parado'])} do tempo.")
    # ---------------------------------------------------------------- DESCOBERTA: a polícia aprende a perseguir
    if gp is not None:
        g1, k1 = lance(A, range(gp, gp + 20), "preso")
        rod = A.rodada(g1)
        marcas = [{"tipo": "circulo", "em": max(f(rod, k1) - 0.5, 0.1), "alvo": "ladrao", "segue": True,
                   "texto": "PRESO!", "rx": 80, "ry": 70}]
        achado(gp, tipo="replay", ger=g1, foco=k1, marcas=marcas, inicio=max(f(rod, k1) - 7, 0),
             cartao={"numero": 0, "rotulo": "POLÍCIA", "nome": "A PERSEGUIÇÃO", "cor": POL,
                     "stat": f"PRESOS {pct(M['preso'][0])} → {pct(M['preso'][gp])} · PARADOS {pct(m0['parado'])} → {pct(mp['parado'])}"},
             log=[("NOVO PADRÃO: PERSEGUIR", POL)],
             fala=f"Geração {gp + 1}. <short pause> A polícia descobre que parado não prende. Ela corre atrás. "
                  f"E {em_dez(M['preso'][gp])} caem.")
        marcos.append((gp, "PERSEGUE", POL))

    # ---------------------------------------------------------------- DESCOBERTA 2: o ladrão aprende a roubar
    if gr is not None:
        g2, k2 = lance(A, range(gr, gr + 25), "rico")
        if g2 is None:
            g2, k2 = lance(A, range(gr, gr + 25), "escapou")
        rod = A.rodada(g2)
        marcas = [{"tipo": "circulo", "em": max(f(rod, k2) - 1.0, 0.1), "alvo": "ladrao", "segue": True,
                   "texto": "ESCAPOU!", "rx": 80, "ry": 70}]
        mr = medidas(hist, gr)
        achado(gr, tipo="replay", ger=g2, foco=k2, marcas=marcas, inicio=max(f(rod, k2) - 8, 0),
             cartao={"numero": 0, "rotulo": "LADRÃO", "nome": "O ROUBO", "cor": LAD,
                     "stat": f"ROUBAM PELO MENOS UM  {pct(m0['rouba'])} → {pct(mr['rouba'])}"},
             log=[("NOVO PADRÃO: IR_AO_DIAMANTE", LAD)],
             fala=f"O ladrão aprende primeiro. Geração {gr + 1}: ele vai direto ao diamante, "
                  f"e {em_dez(mr['rouba'])} já roubam pelo menos um.")
        marcos.append((gr, "ROUBA", LAD))

    # ---------------------------------------------------------------- DESCOBERTA 3: o cerco
    if gc is not None:
        g3, k3 = lance(A, range(gc, gc + 25), "cerco")
        if g3 is not None:
            rod = A.rodada(g3)
            marcas = [{"tipo": "circulo", "em": max(f(rod, k3) - 0.5, 0.1), "alvo": "ladrao", "segue": True,
                       "texto": "CERCADO!", "rx": 80, "ry": 70}]
            achado(gc, tipo="replay", ger=g3, foco=k3, marcas=marcas, inicio=max(f(rod, k3) - 7, 0),
                 cartao={"numero": 0, "rotulo": "POLÍCIA", "nome": "O CERCO", "cor": POL,
                         "stat": f"PRISÕES COM OS DOIS DE LADOS OPOSTOS  {pct(M['cerco_frac'][:5].mean())} → {pct(M['cerco_frac'][g3])}"},
                 log=[("NOVO PADRÃO: CERCAR", POL)],
                 fala="Depois, a polícia aprende a dividir. Um vem de cada lado. O ladrão fica no meio.")
            marcos.append((gc, "CERCO", POL))

    for n, (g, kw) in enumerate(sorted(achados, key=lambda a: a[0]), 1):
        kw["cartao"]["numero"] = n
        cena(**kw)

    # ---------------------------------------------------------------- CALMARIA ENGANOSA
    gm = min(max((gp or 0) + 40, G // 2), G - 1)
    if M["preso"][gm:].max() - M["preso"][gm:].min() < 0.12 and df > M["diamantes"][gm] + 0.1:
        cena(tipo="ao_vivo", ger=gm,
             carimbo={"texto": "PLACAR TRAVADO", "cor": "texto", "em": 0.3, "sub": "A POLÍCIA PAROU DE MELHORAR"},
             log=[(f"GER {gm + 1:03d}+ · PRESOS ~{pct(M['preso'][gm:].mean())}", BRANCO)],
             fala=f"O placar trava. Uns {em_dez(M['preso'][gm:].mean())} presos. <short pause> "
                  "A polícia parou… mas o ladrão não.")

    # ---------------------------------------------------------------- GRÁFICO
    eras = []
    if gp is not None:
        eras.append((0, gp, "POLÍCIA APRENDE", POL))
    if gr is not None:
        eras.append((gr, G - 1, "LADRÃO APRENDE", LAD))
    cena(tipo="grafico", grupo="grafico", serie=M["preso"], eras=eras, titulo="% DE LADRÕES PRESOS",
         rotulo_y="PRESOS POR GERAÇÃO", final=pct(final),
         log=[(f"GER {G:03d} · PRESOS {pct(final)} · {vir(df)} DIAMANTES", VERDE)],
         fala=f"No fim: {pct(final)} dos ladrões presos. <short pause> Mas cada ladrão rouba, em média, "
              f"{vir(df)} diamantes. No começo, {vir(d0)}.")

    # ---------------------------------------------------------------- TORNEIO: ladrões do passado x polícia final
    gens = [0, G // 4, G // 2, 3 * G // 4, G - 1]
    taxas = [torneio(hist, g, G - 1, 1500) for g in gens]
    if taxas[0] - taxas[-1] >= 0.05:
        itens = [(f"G{g + 1:03d}", t, LAD) for g, t in zip(gens, taxas)]
        sub = "preso pela polícia final · 1500 partidas por barra"
        cena(tipo="barras", grupo="torneio", itens=itens, titulo="LADRÕES x POLÍCIA DE HOJE", sub=sub,
             destaque=len(itens) - 1, cor_destaque="verde", rotulo_destaque="◀ ESCAPA MAIS", revela=2.2,
             log=[(f"PRESOS {pct(taxas[0])} → {pct(taxas[-1])}", VERDE)],
             fala=f"Ladrões do passado contra a polícia de hoje. O da geração um: preso {pct(taxas[0])}. "
                  f"O de hoje? Só {pct(taxas[-1])}.")

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    cena(tipo="replay", ger=gh, foco=kh, inicio=max(f(A.rodada(gh), kh) - 8, 0),
         escolha={"pergunta": "QUAL É O SEU TIME?", "opcoes": [("POLÍCIA", POL), ("LADRÃO", LAD)], "em": 0.2},
         destaques={"polícia": POL, "ladrão": LAD},
         fala="Time polícia ou time ladrão? Comenta. Porque tudo começou com…")

    info = {"marca": "VÍDEO NEURAL", "serie": M["preso"], "serie_rotulo": "% DE LADRÕES PRESOS",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": "100 PERSEGUIÇÕES",
            "rodape": f"POP 100×100 · REDES 20-12-2 · {G} GERAÇÕES · NADA FOI PROGRAMADO, SÓ SELEÇÃO"}
    post = (f"Dois policiais, um ladrão e zero instrução. Em {G} gerações, as prisões foram de {pct(M['preso'][0])} "
            f"para {pct(final)} e o ladrão foi de {vir(d0)} para {vir(df)} diamantes por tentativa. "
            f"Simulação real, nenhum número inventado. 🚔💎\n"
            f"Time polícia ou time ladrão? Comenta o seu 👇\n\n#ia #inteligenciaartificial "
            f"#aprendizadodemaquina #simulacao #policiaeladrao #redesneurais")
    return cenas, info, post, {"gp": gp, "gr": gr, "gc": gc, "taxas": taxas}
