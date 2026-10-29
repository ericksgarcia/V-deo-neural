"""Roteiro do episódio Dilema da Ambulância: 24 carros com o mesmo cérebro aprendem a dar passagem (ou não).

A ambulância é programada (só dirige); quem evolui são os carros. O vídeo conta a história na ordem em que ela
aconteceu, sem mostrar o resultado final no começo. Todo número falado sai do treino ou de um teste medido aqui.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios import ambulancia as M
from ..desafios.ambulancia import Ambulancia as Desafio
from ..desafios.foguete import SUCESSO
from ..rede import Arquitetura

BRANCO, MAGENTA = (0.92, 0.96, 1.0), (1.0, 0.3, 0.8)

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend watching an experiment unfold live. Natural spoken Brazilian rhythm; "
    "pace brisk and conversational, about three words per second, never rushed, never dragging. Open intrigued "
    "with a teasing question, deadpan and amused while the cars crash, build curiosity before each discovery and "
    "let it land with quiet awe, sound a little worried at the twist, and finish playful, inviting the viewer to "
    "pick a side.")

DESTAQUES = {"ambulância": BRANCO, "ambulancia": BRANCO, "carros": CIANO, "passagem": VERDE, "bateram": VERMELHO,
             "bater": VERMELHO, "batem": VERMELHO, "batida": VERMELHO, "presa": AMARELO, "trava": AMARELO,
             "chega": VERDE, "chegou": VERDE, "prazo": AMARELO, "sozinhos": VERDE, "ninguém": VERDE}


def pct(x):
    return f"{100 * x:.0f}%"


def ext(x):
    """0.77 -> 'setenta e sete por cento' (a voz lê melhor por extenso)."""
    return f"{numero(round(100 * x))} por cento"


def seg(x):
    return f"{x:.1f}".replace(".", ",")


def numero(n):
    from ..audio import por_extenso
    return por_extenso(int(n))


def suave(x, k=9):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def eventos(hist):
    n = hist["genes"].shape[1]
    s = suave(hist["sucessos"].astype(float))
    l, c = suave(hist["m_lenta"]), suave(hist["m_carros_bateram"])
    G = len(s)
    ev = {"G": G, "n": n, "s": s, "lenta": l, "cb": c, "d1": None, "d2": None, "d3": None}
    ev["d1"] = next((g for g in range(G) if l[g] <= 0.55 * l[0]), None)
    if ev["d1"] is None:
        return ev
    ev["d2"] = next((g for g in range(ev["d1"], G) if c[g] <= 0.25), None)
    if ev["d2"] is None:
        return ev
    ev["d3"] = next((g for g in range(ev["d2"], G) if s[g] >= 0.88 * n), None)
    return ev


def _trava(ev):
    """Entre as descobertas 1 e 2 o placar quase não sobe (no máximo 12% de n) por 12+ gerações."""
    n, s, a, b = ev["n"], ev["s"], ev["d1"], ev["d2"]
    return bool(b - a >= 12 and s[b] - s[a] <= 0.12 * n)


def nota_historia(hist):
    ev = eventos(hist)
    if ev["d1"] is None or ev["d2"] is None or ev["d3"] is None:
        return -1.0
    n, s = ev["n"], ev["s"]
    if not _trava(ev):
        return -0.5
    cedo = max(1 - ev["d3"] / ev["G"] * 2, 0)
    return float((s[-1] - s[0]) / n + 0.5 * (ev["lenta"][0] - ev["lenta"][ev["d1"]]) + 0.5 * cedo
                 + (ev["cb"][0] - ev["cb"][ev["d2"]]))


def duelo(hist, g, n=600, semente=21):
    """O melhor cérebro da geração g, clonado em n avenidas NOVAS: (chegou, bateu a ambulância, carros batidos, tempo)."""
    arq = Arquitetura(Desafio.camadas)
    genes = hist["genes"][g]
    amb = Desafio(len(genes), np.random.default_rng(int(hist["semente"][g])))
    p = arq.desempacota(genes)
    for t in range(Desafio.passos):
        sa, _ = arq.avalia(p, amb.observa())
        amb.passo(sa, t)
    amb.finaliza(t)
    melhor = int(np.argmax(amb.aptidao()))
    a = Desafio(n, np.random.default_rng(semente), por_mundo=True)
    pc = arq.desempacota(np.repeat(genes[melhor:melhor + 1], n, 0))
    for t in range(Desafio.passos):
        sa, _ = arq.avalia(pc, a.observa())
        a.passo(sa, t)
    a.finaliza(t)
    m = a.metricas()
    return m["chegou"], m["bateu"], m["carros_bateram"], m["tempo"]


def medidas(A, g):
    """(velocidade média dos carros que não bateram em m/s, fração dos carros à frente da ambulância (<25 m) que estão
    fora da faixa dela), medidas re-simulando a geração g (as mesmas avenidas do vídeo)."""
    C = M.Ambulancia.C
    r = A.rodada(g)
    e = r.reg["extra"]
    xs, ys, bat = e[..., :C], e[..., C:2 * C], e[..., 2 * C:3 * C] > 0.5
    ax, ay = e[..., 3 * C], e[..., 3 * C + 1]
    frente = (xs > ax[..., None]) & (xs - ax[..., None] < 25) & ~bat
    fora = ((np.abs(ys - ay[..., None]) >= 2.2) & frente).sum() / max(frente.sum(), 1)
    vel = (xs[:, -1] - xs[:, 0]) / (r.T * r.dt)
    return float(vel[~bat[:, -1]].mean()), float(fora)


def _primeira_trava(rod, k):
    """Instante (s) em que a ambulância passa a andar devagar (presa atrás de um carro)."""
    v = rod.reg["extra"][k, :, 3 * M.Ambulancia.C + 2]
    lento = np.where((v < 0.6 * M.V_AMB) & (np.arange(len(v)) > 10))[0]
    return float(lento[0]) * rod.dt if len(lento) else 3.0


def _limpa(A, rod):
    """Avenida em que a ambulância chegou e nenhum carro bateu em outro (a mais rápida)."""
    C = M.Ambulancia.C
    est = rod.reg["estado"][:, -1]
    sem = rod.reg["extra"][:, -1, 2 * C:3 * C].sum(1) == 0
    ok = np.where((est == SUCESSO) & sem)[0]
    return int(ok[np.argmin(rod.morte[ok])]) if len(ok) else A.busca(rod, "primeiro")


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], ev["n"]
    if ev["d1"] is None or ev["d2"] is None or ev["d3"] is None or not _trava(ev):
        raise RuntimeError("A história não tem as duas descobertas e a calmaria: troque a semente.")
    d1, d2, d3 = ev["d1"], ev["d2"], ev["d3"]
    suc = hist["sucessos"]
    s0, cb0 = int(suc[0]), float(hist["m_carros_bateram"][0])
    l0, l1 = float(hist["m_lenta"][0]), float(hist["m_lenta"][d1])
    cb1, cb2 = float(hist["m_carros_bateram"][d1]), float(hist["m_carros_bateram"][d2])
    sd1, sd2 = int(suc[d1]), int(suc[d2])
    v0, _ = medidas(A, 0)
    v1, _ = medidas(A, d1)
    _, fora_fim = medidas(A, G - 1)
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO (nada de resultado)
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("UMA AMBULÂNCIA, 10 SEGUNDOS", BRANCO), ("E 24 CARROS NO CAMINHO", AMARELO)],
         log=[(f"{n} AVENIDAS AO MESMO TEMPO", BRANCO), ("24 CARROS · 3 FAIXAS · 10 SEGUNDOS", AMARELO)],
         fala="Vinte e quatro carros. Uma ambulância com dez segundos para chegar. <short pause> "
              "E nenhum carro sabe o que é uma sirene.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         log=[("A AMBULÂNCIA SÓ SABE DIRIGIR", BRANCO), ("OS CARROS: CÉREBRO VAZIO", CIANO)],
         fala="A ambulância só sabe dirigir. Os carros não sabem nada. <short pause> Todos têm o mesmo cérebro, em branco. "
              "Cada avenida é um teste novo.")
    r0 = A.rodada(0)
    kf = A.busca(r0, "quase")
    cena(tipo="replay", ger=0, foco=kf, grupo="g1b",
         marcas=[{"tipo": "circulo", "em": _primeira_trava(r0, kf), "alvo": "bloqueio", "texto": "PRESA!", "rx": 100,
                  "ry": 70, "desloca": (0, -100)}],
         log=[(f"GER 001 · CHEGOU {s0}/{n}", VERMELHO)],
         carimbo={"texto": f"CHEGA EM {s0} DE {n}", "cor": VERMELHO, "em": 0.5, "sub": "GERAÇÃO 1"},
         fala=f"Geração um. Em {numero(n)} avenidas, a ambulância chega a tempo em só {numero(s0)}. <short pause> "
              f"E em {ext(cb0)} delas, os carros batem uns nos outros.")

    # ---------------------------------------------------------------- A REGRA
    cena(tipo="ao_vivo", ger=min(5, G - 1), log=[("OS MELHORES SÃO COPIADOS", VERDE), ("OS PIORES SAEM", VERMELHO),
                                                  ("CADA RODADA = 1 GERAÇÃO", BRANCO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": VERDE, "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="A regra é cruel. Os melhores são copiados, com pequenas mudanças. Os piores? <short pause> Eliminados. Será que isso basta?")

    # ---------------------------------------------------------------- DESCOBERTA 1: DAR PASSAGEM
    r1 = A.rodada(d1)
    k1 = A.busca(r1, "primeiro")
    cena(tipo="replay", ger=d1, foco=k1,
         marcas=[{"tipo": "circulo", "em": 3.0, "alvo": "ambulancia", "texto": "SEM FREAR", "rx": 100, "ry": 60,
                  "desloca": (0, -100)}],
         cartao={"numero": 1, "rotulo": "DESCOBERTA", "nome": "FUGIR PRA FRENTE", "cor": VERDE,
                 "stat": f"CARROS {v0:.0f} → {v1:.0f} m/s · AMBULÂNCIA PRESA {seg(l0)} → {seg(l1)} s"},
         log=[(f"GER {d1 + 1:03d} · CARROS {v0:.0f} → {v1:.0f} m/s", VERDE),
              (f"PRESA {seg(l0)} s → {seg(l1)} s · CHEGOU {s0} → {sd1}/{n}", VERDE)],
         fala=f"Geração {numero(d1 + 1)}. Os carros descobrem que podem acelerar. <short pause> "
              f"A velocidade média dobra: de {numero(round(v0))} para {numero(round(v1))} metros por segundo. "
              f"E a ambulância chega em {numero(sd1)} de {numero(n)}.")
    marcos.append((d1, "ACELERAR", VERDE))

    # ---------------------------------------------------------------- CALMARIA ENGANOSA
    g_calma = int(np.clip((d1 + d2) // 2, d1 + 1, G - 1))
    cena(tipo="ao_vivo", ger=g_calma,
         log=[(f"GER {d1 + 1}→{d2 + 1} · CHEGOU {sd1}→{sd2}/{n}", AMARELO),
              (f"AVENIDAS COM BATIDA: {pct(cb1)}", VERMELHO)],
         carimbo={"texto": "O PLACAR TRAVA", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {g_calma + 1}"},
         fala=f"Mas aí, trava. <short pause> Da geração {numero(d1 + 1)} à {numero(d2 + 1)}, quase nada muda. "
              f"E em {ext(cb1)} das avenidas… os carros ainda batem. Por que não melhoram?")

    # ---------------------------------------------------------------- DESCOBERTA 2: PARAR DE SE BATER
    r2 = A.rodada(d2)
    k2 = _limpa(A, r2)
    cena(tipo="replay", ger=d2, foco=k2,
         marcas=[{"tipo": "circulo", "em": 3.5, "alvo": "corredor", "texto": "NINGUÉM BATE", "rx": 110, "ry": 70,
                  "desloca": (0, -100)}],
         cartao={"numero": 2, "rotulo": "DESCOBERTA", "nome": "SEM SE BATER", "cor": CIANO,
                 "stat": f"AVENIDAS COM BATIDA {pct(cb1)} → {pct(cb2)}"},
         log=[(f"GER {d2 + 1:03d} · BATIDAS {pct(cb1)} → {pct(cb2)}", CIANO)],
         fala=f"Geração {numero(d2 + 1)}. De repente, eles aprendem a se desviar sem bater. <short pause> "
              f"As avenidas com batida caem de {ext(cb1)} para {ext(cb2)}.")
    marcos.append((d2, "SEM BATER", CIANO))

    # ---------------------------------------------------------------- GRÁFICO
    serie = suc / n
    bat_tot = int(round((hist["m_carros_bateram"] * n).sum()))
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% QUE A AMBULÂNCIA CHEGA A TEMPO",
         eras=[(d1, d2, "ACELERA", VERDE), (d2, G - 1, "SEM BATER", CIANO)],
         rotulo_y="AVENIDAS EM QUE ELA CHEGA, POR GERAÇÃO", final=pct(float(serie[-1])),
         log=[(f"{bat_tot} AVENIDAS COM BATIDA NO CAMINHO", VERMELHO)],
         fala=f"Geração {numero(G)}. Ninguém ensinou nada a eles. <short pause> E {ext(fora_fim)} dos carros à frente "
              "da ambulância já estão fora da faixa dela.")

    # ---------------------------------------------------------------- O TESTE: avenidas novas
    c1, b1, k1b, t1 = duelo(hist, 0)
    c2, b2, k2b, t2 = duelo(hist, d1)
    c3, b3, k3b, t3 = duelo(hist, G - 1)
    virada = (k2b - k3b) >= 0.3 and c2 >= c1
    itens = [("GER 1", c1, CIANO), (f"GER {d1 + 1}", c2, AMARELO), (f"GER {G}", c3, VERDE)]
    fala_t = (f"Agora, seiscentas avenidas novas. Geração um: a ambulância chega em {ext(c1)}. "
              f"Geração {numero(d1 + 1)}: {ext(c2)}. <short pause> Mas em {ext(k2b)}, os carros batem uns nos outros. "
              f"Geração {numero(G)}: {ext(c3)} chegam. E só {ext(k3b)} têm batida." if virada else
              f"Agora, seiscentas avenidas novas. Geração um: a ambulância chega em {ext(c1)}. "
              f"Geração {numero(G)}: {ext(c3)}.")
    cena(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="E EM AVENIDAS NOVAS?",
         sub="600 avenidas inéditas · melhor cérebro de cada geração", destaque=2, cor_destaque="verde", revela=4.0,
         rotulo_destaque=f"▲ +{(c3 - c1) * 100:.0f} pts" if c3 - c1 >= 0.1 else "◀ MELHOR",
         log=[("TESTE: 600 AVENIDAS NOVAS", AMARELO), (f"CHEGOU {pct(c1)} → {pct(c2)} → {pct(c3)}", VERDE),
              (f"CARROS BATIDOS {pct(k1b)} → {pct(k2b)} → {pct(k3b)}", VERMELHO)],
         fala=fala_t)

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    rf = A.rodada(G - 1)
    kf2 = _limpa(A, rf)
    cena(tipo="replay", ger=G - 1, foco=kf2, grupo="fim",
         escolha={"pergunta": "SIRENE ATRÁS DE VOCÊ...", "opcoes": [("ENCOSTO", CIANO), ("FICO NA FAIXA", AMARELO)],
                  "em": 0.2},
         destaques={"encosto": CIANO, "fico": AMARELO, "votado": VERDE},
         fala="Eles aprenderam a abrir caminho sozinhos. <short pause> E você, com a sirene atrás? "
              "Comenta ENCOSTO ou FICO. E marca quem nunca dá passagem.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% EM QUE A AMBULÂNCIA CHEGA",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} AVENIDAS",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO NOS CARROS: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"Uma ambulância, 10 segundos e 24 carros no caminho. 🚑 Na geração 1, ela chegava a tempo em só {s0} de {n} "
            f"avenidas, e em {pct(cb0)} delas os carros batiam uns nos outros. Depois eles descobriram a passagem… e só "
            f"mais tarde a fazer isso sem se bater.\n"
            f"Simulação real: {n} avenidas, {G} gerações. A ambulância é programada; quem aprende é o cérebro dos 24 carros, "
            f"só por seleção e mutação. Uma série em que a IA aprende sozinha.\n"
            f"Com a sirene atrás de você: ENCOSTO ou FICO NA FAIXA? Comenta 👇 e marca quem nunca dá passagem.\n\n"
            f"#ia #inteligenciaartificial #simulacao #ambulancia #transito #curiosidades #tecnologia")
    ev["vel"], ev["fora_fim"] = (v0, v1), fora_fim
    ev["duelo"] = {"g1": (c1, b1, k1b, t1), "d1": (c2, b2, k2b, t2), "fim": (c3, b3, k3b, t3)}
    return cenas, info, post, ev
