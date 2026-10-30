"""Roteiro do episódio Esconde-Esconde no Escuro (guia v2): 3 caçadores com lanterna x 3 fugitivos, tudo escuro.

Todo número falado sai do treino (as partidas da vitrine), de uma medida feita aqui sobre essas mesmas partidas
(velocidade dos fugitivos quando a luz bate) ou de um teste em partidas novas (campeões contra os fugitivos finais).
O campeão é a melhor equipe de caçadores da geração.
"""
import numpy as np

from ..adaptadores.escuro import campeao_da_geracao
from ..coevolucao_escuro import partidas
from ..desafios import escuro as E
from ..palco.holo import AMARELO, CIANO, MAGENTA, VERDE, VERMELHO

BRANCO = (0.92, 0.96, 1.0)

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend watching an experiment unfold live in the dark. Natural spoken Brazilian "
    "rhythm; brisk and conversational, about three words per second, never rushed, never dragging. Open intrigued and "
    "deadpan; let each discovery land with quiet surprise, as if you did not expect it either; finish with a "
    "playful, provocative question and trail off on the last unfinished sentence.")

DESTAQUES = {"campeão": AMARELO, "caçador": MAGENTA, "caçadores": MAGENTA, "lanterna": AMARELO, "luz": AMARELO,
             "farol": AMARELO, "fugitivos": CIANO, "fugitivo": CIANO, "correm": CIANO, "pego": VERMELHO,
             "pegos": VERMELHO, "escuro": CIANO}


def pct(x):
    return f"{100 * x:.0f}"


def suave(x, k=7):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def vel_luz(A, g):
    """Velocidade média (m/s) dos fugitivos vivos enquanto estão sob a luz, na vitrine da geração g."""
    cache = A.__dict__.setdefault("_vl", {})
    if g not in cache:
        r = A.rodada(g)
        f = r.reg["f"]
        v = np.hypot(f[:, 1:, :, 0] - f[:, :-1, :, 0], f[:, 1:, :, 1] - f[:, :-1, :, 1]) / E.DT
        m = r.reg["luz"][:, 1:] & (r.reg["estado"][:, 1:] == 0)
        cache[g] = float(v[m].mean()) if m.any() else 0.0
    return cache[g]


def eventos(hist, A=None):
    G = len(hist["m_pegos"])
    giro, peg = suave(hist["m_giro"]), suave(hist["m_pegos"])
    ev = {"G": G, "giro": giro, "peg": peg, "farol": None, "pico": None, "corre": None}
    ev["farol"] = next((g for g in range(G) if giro[g] >= 0.75), None)
    if ev["farol"] is None:
        return ev
    ev["pico"] = int(np.argmax(peg[: int(G * 0.7)]))
    if A is None or ev["pico"] <= ev["farol"] - 15:
        return ev
    base = vel_luz(A, ev["pico"])
    ev["corre"] = next((g for g in range(ev["pico"], G, 5) if vel_luz(A, g) >= 1.7 * base and peg[g] <= 0.7 * peg[ev["pico"]]), None)
    return ev


def nota_historia(hist):
    """Boa história: caçadores perdem no começo, o farol faz o placar subir bem, depois cai de novo."""
    ev = eventos(hist)
    if ev["farol"] is None:
        return 0.0
    peg = ev["peg"]
    sobe = float(peg[ev["pico"]] - peg[:10].mean())
    desce = float(peg[ev["pico"]] - peg[-10:].mean())
    return float(min(sobe, 0.5) * 4 + min(desce, 0.5) * 4 + (1 - hist["m_pegos"][0]))


def duelo(hist, g, gf, n=600, semente=77):
    """Campeão dos caçadores da geração g contra os fugitivos da geração gf em n partidas novas: fração de fugitivos pegos."""
    c = campeao_da_geracao(hist, g, "cac")
    rng = np.random.default_rng(semente)
    j, _ = partidas(hist["cac"][g], hist["fug"][gf], np.full(n, c), rng.integers(0, len(hist["fug"][gf]), n), semente)
    return float((j.estado == E.PEGO).mean())


def dec(x):
    """1.8 -> 'um vírgula oito' (para a voz)."""
    i, d = f"{x:.1f}".split(".")
    return f"{numero(int(i))} vírgula {numero(int(d))}"


def numero(n):
    from ..audio import por_extenso
    return por_extenso(int(n))


def monta(hist, A):
    ev = eventos(hist, A)
    G = ev["G"]
    if ev["corre"] is None:
        raise RuntimeError("Esta semente não tem a história completa (farol, pico, fugitivos correm): troque a semente.")
    gf, gp, gc = ev["farol"], ev["pico"], ev["corre"]
    n = hist["cac"].shape[1]
    peg = lambda g: int(round(100 * hist["m_pegos"][g]))
    nenhum = lambda g: int(round(100 * hist["m_nenhum"][g]))
    giro = lambda g: int(round(100 * hist["m_giro"][g]))
    s_um, s_pico, s_fin = duelo(hist, 0, G - 1), duelo(hist, gp, G - 1), duelo(hist, G - 1, G - 1)
    C = G
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    def marca(rod, foco, alvo, texto, quando=None, **kw):
        em = float(quando) if quando is not None else max(float(rod.morte[foco]) * E.DT - 0.7, 0.0)
        return [dict({"tipo": "circulo", "em": em, "alvo": alvo, "texto": texto, "rx": 85, "ry": 85,
                      "desloca": (0, -110)}, **kw)]

    # ------------------------------------------------------------ GANCHO
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("3 CAÇADORES NO ESCURO", BRANCO), (f"NINGUÉM PEGO EM {nenhum(0)} DE {n}", AMARELO)],
         log=[(f"{n} PARTIDAS AO MESMO TEMPO", BRANCO), ("LANTERNA x ESCURO · 0 REGRAS", AMARELO)],
         carimbo={"texto": f"{nenhum(0)} DE {n}", "cor": AMARELO, "em": 1.4, "sub": "PARTIDAS SEM NINGUÉM PEGO · GERAÇÃO 1"},
         fala=f"Dei lanternas a três caçadores. <short pause> Em {numero(nenhum(0))} de cem jogos, eles não pegaram ninguém.")
    # ------------------------------------------------------------ PREMISSA + REGRA
    cena(tipo="ao_vivo", ger=min(2, G - 1), grupo="g1b",
         log=[("CADA CAÇADOR SÓ VÊ O QUE A LANTERNA ILUMINA", AMARELO), ("QUEM VAI MELHOR VIRA PAI DA PRÓXIMA TURMA", VERDE)],
         fala="Eles só veem o que a lanterna ilumina. Três fugitivos se escondem. <short pause> Quem vai melhor vira pai da próxima turma.")
    # ------------------------------------------------------------ GERAÇÃO 1: o campeão falha
    r0 = A.rodada(C)
    k0 = A.busca(r0, "livre")
    cena(tipo="replay", ger=C, foco=k0, grupo="g1c", log=[("CAMPEÃO DA GER 001 · NINGUÉM PEGO", AMARELO)],
         fala="O campeão da geração um. <short pause> Não achou ninguém.")
    # ------------------------------------------------------------ DESCOBERTA 1: o farol
    r1 = A.rodada(C + gf)
    k1 = A.busca(r1, "todos") or A.busca(r1, "pego")
    cena(tipo="replay", ger=C + gf, foco=k1, marcas=marca(r1, k1, "fugitivo", "PEGO!"),
         cartao={"numero": 1, "rotulo": "CAÇADORES", "nome": "O FAROL", "cor": AMARELO,
                 "stat": f"GIRAM A LANTERNA {giro(0)}% → {giro(gf)}% DO TEMPO"},
         log=[(f"GER {gf + 1:03d} · GIRO {giro(0)}% → {giro(gf)}%", AMARELO)],
         fala=f"Geração {numero(gf + 1)}. O campeão descobre o farol: <short pause> gira a lanterna na maior parte do tempo.")
    marcos.append((gf, "1", AMARELO))
    # ------------------------------------------------------------ placar sobe
    r2 = A.rodada(C + gp)
    k2 = A.busca(r2, "todos") or A.busca(r2, "pego")
    cena(tipo="replay", ger=C + gp, foco=k2, marcas=marca(r2, k2, "fugitivo", "PEGO!"),
         log=[(f"GER {gp + 1:03d} · FUGITIVOS PEGOS {peg(0)}% → {peg(gp)}%", VERMELHO)],
         fala=f"Fugitivos pegos: <long pause> de {numero(peg(0))} para {numero(peg(gp))} em cada cem.")
    # ------------------------------------------------------------ RE-GANCHO
    cena(tipo="ao_vivo", ger=gp,
         log=[(f"GER {gp + 1:03d} · O PLACAR É DOS CAÇADORES", AMARELO)],
         carimbo={"texto": "FUGITIVOS SEM SAÍDA?", "cor": CIANO, "em": 0.4, "sub": f"GERAÇÃO {gp + 1}"},
         fala="Os caçadores dominam. <short pause> Mas os fugitivos têm uma resposta. <long pause>")
    # ------------------------------------------------------------ DESCOBERTA 2: correr quando a luz bate
    r3 = A.rodada(C + gc)
    k3 = A.busca(r3, "livre")
    vp, vc = vel_luz(A, gp), vel_luz(A, gc)
    cena(tipo="replay", ger=C + gc, foco=k3,
         cartao={"numero": 2, "rotulo": "FUGITIVOS", "nome": "CORRER DA LUZ", "cor": CIANO,
                 "stat": f"VELOCIDADE SOB A LUZ {vp:.1f} → {vc:.1f} m/s"},
         log=[(f"GER {gc + 1:03d} · SOB A LUZ {vp:.1f} → {vc:.1f} m/s", CIANO)],
         fala=f"Eles aprendem a correr da luz. <long pause> De {dec(vp)} para {dec(vc)} metros por segundo.")
    marcos.append((gc, "2", CIANO))
    # ------------------------------------------------------------ TESTE
    itens = [("CAMPEÃO 1", s_um, MAGENTA), (f"CAMPEÃO {gp + 1}", s_pico, MAGENTA), (f"CAMPEÃO {G}", s_fin, VERDE)]
    cena(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="CAMPEÃO x FUGITIVOS FINAIS",
         sub="600 partidas novas · fugitivos pegos", destaque=1, cor_destaque="verde", revela=4.0,
         rotulo_destaque="▲ MELHOR",
         log=[("TESTE: 600 PARTIDAS NOVAS", AMARELO), (f"PEGOS {pct(s_um)}% → {pct(s_pico)}% → {pct(s_fin)}%", AMARELO)],
         fala=f"Teste com partidas novas. <short pause> O campeão da geração um pegava {numero(round(100 * s_um))} em cem. "
              f"O campeão da {numero(G)}… {numero(round(100 * s_fin))}.")
    # ------------------------------------------------------------ CTA + LAÇO
    rf = A.rodada(C + G - 1)
    kf = A.busca(rf, "livre") or A.busca(rf, "campeao")
    cena(tipo="replay", ger=C + G - 1, foco=kf, grupo="fim",
         escolha={"pergunta": "QUEM EVOLUIU MAIS?", "opcoes": [("QUEM CAÇA", MAGENTA), ("QUEM CORRE", CIANO)], "em": 0.2},
         destaques={"caça": MAGENTA, "corre": CIANO, "campeão": AMARELO},
         fala=f"Quem evoluiu mais: quem caça ou quem corre? <short pause> Porque tudo começou quando eu…")

    info = {"marca": "VÍDEO NEURAL", "serie": suave(hist["m_pegos"], 5), "serie_rotulo": "% FUGITIVOS PEGOS",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} PARTIDAS",
            "rodape": f"{n} PARTIDAS · REDES {'-'.join(map(str, E.CAM_C))} / {'-'.join(map(str, E.CAM_F))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"Dei lanternas a três caçadores e a IA inventou o farol sozinha. 🔦\n"
            f"IA aprendendo sozinha por seleção natural (rede neural + algoritmo genético). Simulação real: {n} partidas por geração, {G} gerações, "
            "números medidos no treino.\n"
            "Marca o amigo que sempre se dá bem no esconde-esconde 👇\n\n"
            "#inteligenciaartificial #ia #redeneural #simulacao #escondeesconde")
    ev["duelo"] = {"um": s_um, "pico": (gp, s_pico), "fin": (G - 1, s_fin), "vel": (vp, vc)}
    return cenas, info, post, ev
