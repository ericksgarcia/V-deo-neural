"""Roteiro do episódio Escolta VIP (guia v2): 3 seguranças x 3 assassinos, o VIP anda sozinho até a saída.

Todo número falado sai do treino (as partidas da vitrine) ou de um teste medido aqui (campeões contra os assassinos
da última geração, em partidas novas). O campeão é a melhor equipe de seguranças da geração.
"""
import numpy as np

from ..adaptadores.escolta import CIANO, MAGENTA, VERDE, VERMELHO, campeao_da_geracao
from ..coevolucao_escolta import partidas
from ..desafios import escolta as E
from ..palco.holo import AMARELO

BRANCO = (0.92, 0.96, 1.0)

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend watching an experiment unfold live. Natural spoken Brazilian rhythm; "
    "brisk and conversational, about three words per second, never rushed, never dragging. Open intrigued and "
    "deadpan; let each discovery land with quiet surprise, as if you did not expect it either; finish with a "
    "playful, provocative question and trail off on the last unfinished sentence.")

DESTAQUES = {"vip": AMARELO, "campeão": AMARELO, "segurança": CIANO, "seguranças": CIANO, "assassinos": MAGENTA,
             "assassino": MAGENTA, "escudo": VERDE, "mortes": VERMELHO, "morreu": VERMELHO, "salvava": VERDE,
             "caminho": VERDE, "colam": CIANO}


def pct(x):
    return f"{100 * x:.0f}"


def suave(x, k=7):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def eventos(hist):
    G = len(hist["m_vip_vivo"])
    mor, cola, esc = suave(1 - hist["m_vip_vivo"]), suave(hist["m_cola"]), suave(hist["m_escudo"])
    ev = {"G": G, "mor": mor, "cola": cola, "esc": esc, "vai": None, "colam": None, "escudo": None}
    ev["vai"] = next((g for g in range(G) if mor[g] >= 0.6), None)
    if ev["vai"] is None:
        return ev
    ev["colam"] = next((g for g in range(ev["vai"], G) if cola[g] <= 4.5), None)
    if ev["colam"] is None:
        return ev
    ev["escudo"] = next((g for g in range(ev["colam"], G) if esc[g] >= 0.85), None)
    return ev


def nota_historia(hist):
    """Boa história: o VIP quase não morre no início, os assassinos aprendem, os seguranças colam, o escudo aparece
    e o placar fica parado entre as duas viradas."""
    ev = eventos(hist)
    if ev["escudo"] is None:
        return float((ev["vai"] is not None) + 0.5 * (ev["colam"] is not None))
    G = ev["G"]
    ini = 1 - float(hist["m_vip_vivo"][0])
    tarde = min(ev["escudo"] / G, 0.9)
    return float(3 + 2 * (1 - min(ini / 0.3, 1)) + tarde + float(hist["m_escudo"][-5:].mean()))


def duelo(hist, g, ga, n=600, semente=77):
    """O campeão da geração g contra os assassinos da geração ga em n partidas novas: fração em que o VIP sai vivo."""
    c = campeao_da_geracao(hist["seg"][g], hist["ass"][g], int(hist["semente"][g]))
    rng = np.random.default_rng(semente)
    j, _ = partidas(hist["seg"][g][[c]], hist["ass"][ga], np.zeros(n, int), rng.integers(0, len(hist["ass"][ga]), n), semente)
    return float((j.estado != E.MORTO).mean())


def numero(n):
    from ..audio import por_extenso
    return por_extenso(int(n))


def monta(hist, A):
    ev = eventos(hist)
    G = ev["G"]
    if ev["escudo"] is None:
        raise RuntimeError("Esta semente não tem a história completa (assassinos, colar, escudo): troque a semente.")
    g1, g2, g3 = ev["vai"], ev["colam"], ev["escudo"]
    n = hist["seg"].shape[1]
    morte = lambda g: int(round(100 * (1 - hist["m_vip_vivo"][g])))
    esc = lambda g: int(round(100 * hist["m_escudo"][g]))
    cola = lambda g: int(round(float(hist["m_cola"][g])))
    g_ref = (g2 + g3) // 2
    s_um, s_ref, s_fin = duelo(hist, 0, G - 1), duelo(hist, g_ref, G - 1), duelo(hist, G - 1, G - 1)
    if s_ref >= s_um or s_fin - s_ref < 0.2:
        raise RuntimeError("O campeão final não supera o do meio do treino em partidas novas: troque a semente.")
    C = G                                    # ger >= G pede a rodada do campeão (ver Escolta.rodada)
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    def marca(rod, foco, alvo, texto, quando=None, **kw):
        j = rod.jogo
        em = float(quando) if quando is not None else max(float(j.t_fim[foco]) * E.DT - 0.7, 0.0)
        return [dict({"tipo": "circulo", "em": em, "alvo": alvo, "texto": texto, "rx": 85, "ry": 85,
                      "desloca": (0, -110)}, **kw)]

    # ------------------------------------------------------------ GANCHO
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("3 IAs PROTEGEM UM VIP", BRANCO), ("3 QUEREM MATÁ-LO", MAGENTA)],
         log=[(f"{n} PARTIDAS AO MESMO TEMPO", BRANCO), ("SEGURANÇAS x ASSASSINOS · 0 REGRAS", CIANO)],
         carimbo={"texto": f"{morte(0)} DE {n}", "cor": VERMELHO, "em": 1.4, "sub": "VIPs MORTOS · GERAÇÃO 1"},
         fala=f"Coloquei três IAs para proteger um VIP. <short pause> Na geração um, ele morreu em {morte(0)} de cem.")
    # ------------------------------------------------------------ PREMISSA + REGRA
    cena(tipo="ao_vivo", ger=min(2, G - 1), grupo="g1b",
         log=[("OS ASSASSINOS QUEREM TOCAR NO VIP", MAGENTA), ("QUEM VAI MELHOR VIRA PAI DA PRÓXIMA TURMA", VERDE)],
         fala="Outras três querem matá-lo. O VIP só anda reto. <short pause> Quem vai melhor vira pai da próxima turma.")
    # ------------------------------------------------------------ GERAÇÃO 1: o campeão falha
    r0 = A.rodada(C)
    k0 = A.busca(r0, "morto")
    cena(tipo="replay", ger=C, foco=k0, grupo="g1c", marcas=marca(r0, k0, "assassino", "TOCOU!"),
         log=[("CAMPEÃO DA GER 001 · VIP MORTO", VERMELHO)],
         fala="O campeão da geração um. <short pause> Dessa vez, falhou.")
    # ------------------------------------------------------------ DESCOBERTA 1: assassinos vão direto
    r1 = A.rodada(C + g1)
    k1 = A.busca(r1, "morto")
    cena(tipo="replay", ger=C + g1, foco=k1, marcas=marca(r1, k1, "assassino", "TOCOU!"),
         cartao={"numero": 1, "rotulo": "ASSASSINOS", "nome": "CHEGAM NO VIP", "cor": MAGENTA,
                 "stat": f"VIPs MORTOS {morte(0)} → {morte(g1)} DE {n}"},
         log=[(f"GER {g1 + 1:03d} · VIPs MORTOS {morte(g1)}/{n}", MAGENTA)],
         fala=f"Os assassinos aprendem a chegar no VIP. <long pause> De {numero(morte(0))} para {numero(morte(g1))}.")
    marcos.append((g1, "1", MAGENTA))
    # ------------------------------------------------------------ DESCOBERTA 2: seguranças colam
    r2 = A.rodada(C + g2)
    k2 = A.busca(r2, "morto_tarde")
    cena(tipo="replay", ger=C + g2, foco=k2, marcas=marca(r2, k2, "seguranca", "PERTO", quando=0.8),
         cartao={"numero": 2, "rotulo": "SEGURANÇAS", "nome": "FICAM PERTO", "cor": CIANO,
                 "stat": f"DISTÂNCIA AO VIP {cola(0)} m → {cola(g2)} m"},
         log=[(f"GER {g2 + 1:03d} · DISTÂNCIA {cola(0)} m → {cola(g2)} m", CIANO)],
         fala=f"Aí os seguranças reagem. Chegam perto do VIP. <long pause> De {numero(cola(0))} metros para {numero(cola(g2))}.")
    marcos.append((g2, "2", CIANO))
    # ------------------------------------------------------------ RE-GANCHO: o placar trava
    g_calma = (g2 + g3) // 2
    cena(tipo="ao_vivo", ger=g_calma,
         log=[(f"GER {g_calma + 1:03d} · VIPs MORTOS {morte(g_calma)}/{n}", AMARELO), ("O PLACAR TRAVA", AMARELO)],
         carimbo={"texto": "O PLACAR TRAVA", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {g_calma + 1}"},
         fala="Parado por dezenas de gerações. <short pause> Será que acabou? <long pause>")
    # ------------------------------------------------------------ DESCOBERTA 3: o escudo humano
    r3 = A.rodada(C + g3)
    k3 = A.busca(r3, "salvo")
    cena(tipo="replay", ger=C + g3, foco=k3, marcas=marca(r3, k3, "seguranca", "ESCUDO", quando=1.6),
         cartao={"numero": 3, "rotulo": "SEGURANÇAS", "nome": "ESCUDO HUMANO", "cor": VERDE,
                 "stat": f"SEGURANÇA NO CAMINHO {esc(0)}% → {esc(g3)}%"},
         log=[(f"GER {g3 + 1:03d} · ESCUDO {esc(0)}% → {esc(g3)}%", VERDE)],
         fala=f"Escudo humano: <short pause> alguém entra na frente do assassino. "
              f"<long pause> De {numero(esc(0))} para {numero(esc(g3))} por cento dos perigos.")
    marcos.append((g3, "3", VERDE))
    # ------------------------------------------------------------ TESTE
    itens = [("CAMPEÃO 1", s_um, CIANO), (f"CAMPEÃO {g_ref + 1}", s_ref, CIANO), (f"CAMPEÃO {G}", s_fin, VERDE)]
    cena(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="VIP SALVO CONTRA OS ASSASSINOS FINAIS",
         sub="600 partidas novas · campeão de cada geração", destaque=2, cor_destaque="verde", revela=4.0,
         rotulo_destaque="▲ MELHOR",
         log=[("TESTE: 600 PARTIDAS NOVAS", AMARELO), (f"VIP SALVO {pct(s_um)}% → {pct(s_ref)}% → {pct(s_fin)}%", AMARELO)],
         fala=f"Partidas novas. <short pause> O campeão da geração um salvava {numero(round(100 * s_um))} em cem. "
              f"O da {numero(g_ref + 1)}, só {numero(round(100 * s_ref))}. O da {numero(G)}… {numero(round(100 * s_fin))}.")
    # ------------------------------------------------------------ CTA + LAÇO
    rf = A.rodada(C + G - 1)
    kf = A.busca(rf, "salvo")
    cena(tipo="replay", ger=C + G - 1, foco=kf, grupo="fim",
         escolha={"pergunta": f"O CAMPEÃO DA {g_ref + 1} PIOROU?", "opcoes": [("PIOROU", VERMELHO), ("SE ESPECIALIZOU", VERDE)], "em": 0.2},
         destaques={"piorou": VERMELHO, "especializou": VERDE, "campeão": AMARELO},
         fala=f"O campeão da {numero(g_ref + 1)} piorou ou só se especializou? <short pause> Porque tudo começou quando eu…")

    info = {"marca": "VÍDEO NEURAL", "serie": suave(1 - hist["m_vip_vivo"], 5), "serie_rotulo": "% VIPs MORTOS",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} PARTIDAS",
            "rodape": f"{n} PARTIDAS · REDE {'-'.join(map(str, E.CAMADAS))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"Três IAs, um VIP e três assassinos. Na geração 1, ele morreu em {morte(0)} de {n}. 🕶️\n"
            f"IA aprendendo sozinha por seleção natural. Simulação real: {n} partidas por geração, {G} gerações, "
            "números medidos no treino.\n"
            "Marca o amigo que gruda em você na festa e não sai de perto 👇\n\n"
            "#inteligenciaartificial #ia #aprendizadodemaquina #simulacao #selecaonatural")
    ev["duelo"] = {"ref": (g_ref, s_ref), "fin": (G - 1, s_fin)}
    return cenas, info, post, ev
