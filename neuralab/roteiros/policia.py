"""Roteiro do episódio Polícia e Ladrão: 100 ladrões x 100 policiais evoluindo juntos numa arena com paredes.

Todo número falado sai do treino (as partidas da vitrine, as mesmas que o vídeo mostra). O "mesmo lado" do
policial é medido aqui mesmo, re-simulando a geração, e só vira fala se o número sustentar a frase.
"""
import numpy as np

from ..adaptadores.policia import CIANO, MAGENTA, VERDE, VERMELHO
from ..desafios import policia as P

AMARELO, BRANCO = (1.0, 0.74, 0.12), (0.92, 0.96, 1.0)
DESTAQUES = {"ladrão": CIANO, "ladrões": CIANO, "ladrao": CIANO, "polícia": MAGENTA, "policiais": MAGENTA,
             "policial": MAGENTA, "cofre": AMARELO, "pego": VERMELHO, "presos": VERMELHO, "fogem": VERDE,
             "escapam": VERDE, "caminho": VERDE, "lado": AMARELO, "cima": AMARELO, "troca": AMARELO}


def pct(x):
    return f"{100 * x:.0f}%"


def suave(x, k=5):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def mesmo_lado(A, g):
    """Fração das partidas em que o policial está do mesmo lado do quarteirão que o ladrão quando ele passa do meio."""
    r = A.rodada(g)
    j = r.jogo
    idx = np.where(j.cruzou)[0]
    if not len(idx):
        return 0.0
    i = np.minimum((j.t_cruza[idx] / P.DT).astype(int), r.T - 1)
    ly = r.reg["l"][idx, i, 1] > P.ALT / 2
    py = r.reg["p"][idx, i, 1] > P.ALT / 2
    return float((ly == py).mean())


def eventos(hist):
    """Os quatro momentos da corrida armamentista (None se a semente não os tem)."""
    f, p = suave(hist["m_fuga"]), suave(hist["m_pego"])
    cima, baixo = suave(hist["m_rota_cima"]), suave(hist["m_rota_baixo"])
    G = len(f)
    ev = {"G": G, "f": f, "p": p, "caminho": None, "cerco": None, "fundo": None, "troca": None, "pico": None}
    ev["caminho"] = next((g for g in range(G) if f[g] >= 0.5), None)
    if ev["caminho"] is None:
        return ev
    ev["cerco"] = next((g for g in range(ev["caminho"], G) if p[g] >= 0.45 and f[g] <= 0.5), None)
    if ev["cerco"] is None:
        return ev
    fim = G - 15
    ev["fundo"] = int(ev["cerco"] + np.argmin(f[ev["cerco"]:fim])) if fim > ev["cerco"] else None
    if ev["fundo"] is None:
        return ev
    lado_antes = np.sign(cima - baixo)[ev["fundo"]]
    ev["troca"] = next((g for g in range(ev["fundo"], fim) if np.sign(cima - baixo)[g] == -lado_antes
                        and abs(cima[g] - baixo[g]) >= 0.15 and f[g] > f[ev["fundo"]] + 0.1), None)
    if ev["troca"] is not None:
        ev["pico"] = int(ev["troca"] + np.argmax(f[ev["troca"]:min(ev["troca"] + 40, G)]))
    return ev


def nota_historia(hist):
    """Quanto a curva conta uma boa corrida armamentista: ladrão acha o caminho, polícia reage e o ladrão se recupera."""
    ev = eventos(hist)
    if ev["troca"] is None:
        return float((ev["caminho"] is not None) + 0.5 * (ev["cerco"] is not None) + 0.3 * (ev["fundo"] is not None))
    f = ev["f"]
    return float(3 + (f[ev["pico"]] - f[ev["fundo"]]) * 2 + (f[ev["caminho"]] - f[ev["fundo"]]) + 0.5 * f[ev["pico"]])


def numero(n):
    from ..audio import por_extenso
    return por_extenso(int(n))


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], hist["lad"].shape[1]
    if ev["troca"] is None:
        raise RuntimeError("Esta semente não tem a corrida completa (caminho, cerco, troca): troque a semente.")
    g1, g2, g3, g4, g5 = ev["caminho"], ev["cerco"], ev["fundo"], ev["troca"], ev["pico"]
    fuga = lambda g: int(round(hist["m_fuga"][g] * n))
    pego = lambda g: int(round(hist["m_pego"][g] * n))
    parado0 = int(round(hist["m_tempo_esgotado"][0] * n))
    ml2, ml5, mlfim = mesmo_lado(A, g2), mesmo_lado(A, g5), mesmo_lado(A, G - 1)
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    def marca(rod, foco, alvo, texto, quando=None, **kw):
        j = rod.jogo
        em = float(quando) if quando is not None else max(float(j.t_fim[foco]) * P.DT - 0.7, 0.0)
        return [dict({"tipo": "circulo", "em": em, "alvo": alvo, "texto": texto, "rx": 85, "ry": 85,
                      "desloca": (0, -110)}, **kw)]

    # ------------------------------------------------------------ GANCHO: o ladrão que descobriu o caminho
    r5 = A.rodada(g5)
    heroi = A.busca(r5, "cima") or A.busca(r5, "escapa")
    cena(tipo="replay", ger=g5, foco=heroi, grupo="gancho", marcas=marca(r5, heroi, "cofre", "NO COFRE!"),
         titulo_gancho=[("A IA APRENDEU", BRANCO), ("A FUGIR DA POLÍCIA", CIANO)],
         fala="Esse ladrão nunca viu um cofre. <short pause> Ninguém ensinou o caminho. <long pause> Olha o que ele faz.")
    cena(tipo="replay", ger=g5, foco=heroi, grupo="gancho", marcas=marca(r5, heroi, "cofre", "NO COFRE!"), pausa=0.2,
         fala="Mas tem uma polícia aprendendo junto.")

    # ------------------------------------------------------------ PREMISSA + GERAÇÃO 1
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"{n} LADRÕES x {n} POLICIAIS", BRANCO),
                                                  ("TODOS COM O CÉREBRO VAZIO", BRANCO)],
         fala=f"Eu comecei com {numero(n)} ladrões e {numero(n)} policiais. Cérebros vazios. <short pause> "
              "Os ladrões querem o cofre. Os policiais querem os ladrões.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · FUGIRAM {fuga(0)}/{n}", VERMELHO)],
         carimbo={"texto": f"FUGIRAM {fuga(0)}", "cor": VERMELHO, "em": 0.6, "sub": f"DE {n} · GERAÇÃO 1"},
         fala=f"Chuta aí: quantos escapam? <long pause> Só {numero(fuga(0))}. "
              + ("<short pause> E a maioria só anda sem rumo até o tempo acabar." if parado0 >= n * 0.5 else ""))

    # ------------------------------------------------------------ A REGRA (curta)
    cena(tipo="ao_vivo", ger=min(4, G - 1), log=[("QUEM VAI MELHOR VIRA PAI DA PRÓXIMA TURMA", VERDE),
                                                ("QUEM ERRA SAI", VERMELHO), ("OS DOIS LADOS EVOLUEM JUNTOS", BRANCO)],
         fala="A regra é simples. Quem vai melhor vira pai da próxima turma. <short pause> Quem erra, sai. "
              "E os dois lados evoluem juntos.")

    # ------------------------------------------------------------ DESCOBERTA 1: o ladrão acha o caminho
    rg1 = A.rodada(g1)
    k1 = A.busca(rg1, "escapa")
    cena(tipo="replay", ger=g1, foco=k1, marcas=marca(rg1, k1, "cofre", "NO COFRE!"),
         cartao={"numero": 1, "rotulo": "LADRÃO", "nome": "O CAMINHO", "cor": CIANO,
                 "stat": f"FUGAS {fuga(0)} → {fuga(g1)} DE {n}"},
         log=[(f"GER {g1 + 1:03d} · FUGIRAM {fuga(g1)}/{n}", VERDE)],
         fala=f"Geração {g1 + 1}. Os ladrões descobrem o caminho. <short pause> Contornam o quarteirão… e chegam ao cofre. "
              f"<long pause> De {numero(fuga(0))}… para {numero(fuga(g1))}.")
    marcos.append((g1, "1", CIANO))

    # ------------------------------------------------------------ DESCOBERTA 2: a polícia escolhe o mesmo lado
    rg2 = A.rodada(g2)
    k2 = A.busca(rg2, "pego")
    t_cr = float(rg2.jogo.t_cruza[k2]) if k2 is not None and rg2.jogo.cruzou[k2] else None
    lado_ok = ml2 >= 0.85
    cena(tipo="replay", ger=g2, foco=k2,
         marcas=marca(rg2, k2, "policia", "MESMO LADO", quando=t_cr) if (lado_ok and t_cr is not None) else
         marca(rg2, k2, "ladrao", "PEGO!"),
         cartao={"numero": 2, "rotulo": "POLÍCIA", "nome": "O MESMO LADO" if lado_ok else "O CERCO", "cor": MAGENTA,
                 "stat": f"PRESOS {pego(g1)} → {pego(g2)} DE {n}"},
         log=[(f"GER {g2 + 1:03d} · PRESOS {pego(g2)}/{n}", VERMELHO)],
         fala=(f"Aí a polícia aprende. <short pause> Ela passa a escolher o mesmo lado do quarteirão que o ladrão. "
               f"<long pause> Presos: de {numero(pego(g1))}… para {numero(pego(g2))}."
               if lado_ok else
               f"Aí a polícia aprende. <short pause> Presos: de {numero(pego(g1))}… para {numero(pego(g2))}."))
    marcos.append((g2, "2", MAGENTA))

    # ------------------------------------------------------------ CALMARIA ENGANOSA + DESCOBERTA 3: a troca de lado
    cena(tipo="ao_vivo", ger=g3, log=[(f"GER {g3 + 1:03d} · FUGIRAM {fuga(g3)}/{n}", AMARELO)],
         carimbo={"texto": f"SÓ {fuga(g3)} FOGEM", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {g3 + 1}"},
         fala=f"Geração {g3 + 1}. Só {numero(fuga(g3))} ladrões fogem. <short pause> Parece o fim dos ladrões.")
    rg4 = A.rodada(g4)
    k4 = A.busca(rg4, "cima" if hist["m_rota_cima"][g4] >= hist["m_rota_baixo"][g4] else "baixo") or A.busca(rg4, "escapa")
    lado_novo = "por cima" if hist["m_rota_cima"][g4] >= hist["m_rota_baixo"][g4] else "por baixo"
    t4 = float(rg4.jogo.t_cruza[k4]) if k4 is not None and rg4.jogo.cruzou[k4] else None
    falou_erro = ml5 < ml2 - 0.15
    cena(tipo="replay", ger=g4, foco=k4,
         marcas=marca(rg4, k4, "ladrao", lado_novo.upper(), quando=t4) if t4 is not None else marca(rg4, k4, "cofre", "NO COFRE!"),
         cartao={"numero": 3, "rotulo": "LADRÃO", "nome": "A TROCA", "cor": CIANO,
                 "stat": f"FUGAS {fuga(g3)} → {fuga(g5)} DE {n}"},
         log=[(f"GER {g4 + 1:03d} · TROCA DE LADO", CIANO)],
         fala=f"Até que um ladrão muda o jogo. <short pause> Troca de lado. <long pause> Vai {lado_novo}. "
              + (f"E a polícia erra o lado: em {pct(1 - ml5)} das partidas." if falou_erro else
                 f"E as fugas sobem para {numero(fuga(g5))}."))
    marcos.append((g4, "3", CIANO))

    # ------------------------------------------------------------ O GRÁFICO
    serie = hist["m_fuga"]
    cena(tipo="grafico", grupo="grafico", serie=suave(serie, 5), titulo="% QUE FOGE",
         eras=[(g1 - 6 if g1 > 6 else 0, g2, "LADRÃO ACHA O CAMINHO", CIANO), (g2, g4, "POLÍCIA REAGE", MAGENTA),
               (g4, G - 1, "TROCA DE LADO", AMARELO)],
         rotulo_y="LADRÕES QUE ESCAPAM POR GERAÇÃO", final=pct(float(suave(serie, 5)[-1])),
         log=[(f"{G} GERAÇÕES · NENHUMA REGRA PROGRAMADA", BRANCO)],
         fala=f"Dois cérebros. Zero regras. <short pause> Um perseguindo o outro por {numero(G)} gerações.")

    # ------------------------------------------------------------ FINAL + CHAMADA (volta ao gancho)
    cena(tipo="ao_vivo", ger=G - 1, log=[(f"GER {G:03d} · FUGIRAM {fuga(G - 1)}/{n} · PRESOS {pego(G - 1)}/{n}", AMARELO)],
         fala=(f"E a corrida não acaba. <short pause> Na geração {numero(G)}, a polícia já escolhe o mesmo lado de novo. "
               f"<short pause> Em {pct(mlfim)} das partidas." if mlfim >= 0.85 else
               f"E a corrida não acaba. <short pause> Na geração {numero(G)}, "
               f"{numero(fuga(G - 1))} ladrões ainda fogem."))
    cena(tipo="replay", ger=g5, foco=heroi, grupo="fim", inicio=max(float(r5.jogo.t_fim[heroi]) * P.DT - 1.4, 0),
         escolha={"pergunta": "QUEM GANHA UM MOTOR MAIS RÁPIDO?", "opcoes": [("TIME LADRÃO", CIANO), ("TIME POLÍCIA", MAGENTA)],
                  "em": 0.2},
         destaques={"ladrão": CIANO, "polícia": MAGENTA, "votado": VERDE},
         fala="Agora é com você. No próximo vídeo, um lado ganha um motor mais rápido. <short pause> "
              "Time ladrão… ou time polícia? <long pause> Comenta o seu lado. O mais votado ganha.")

    info = {"marca": "VÍDEO NEURAL", "serie": suave(serie, 5), "serie_rotulo": "% LADRÕES QUE FUGIRAM",
            "marcos": marcos, "rotulo_vivo": f"{n} LADRÕES x {n} POLICIAIS",
            "rodape": f"{n} x {n} · REDE {'-'.join(map(str, P.CAMADAS))} · {G} GERAÇÕES · NADA FOI PROGRAMADO: "
                      "SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"Coloquei {n} ladrões contra {n} policiais, todos com IA e cérebro vazio. Na geração 1, só {fuga(0)} fugiram. "
            f"Depois: o caminho, o cerco da polícia e uma troca de lado que virou o jogo. 🚔💨\n"
            f"Simulação real: {G} gerações, zero regras programadas. Uma série em que a IA aprende sozinha.\n"
            f"Quem merece um motor mais rápido no próximo: TIME LADRÃO ou TIME POLÍCIA? Comenta 👇\n\n"
            f"#ia #inteligenciaartificial #aprendizadodemaquina #policiaeladrao #curiosidades #tecnologia #simulacao")
    return cenas, info, post, ev
