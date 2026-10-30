"""Roteiro do episódio Queimada de IAs (guia v2 + retenção v3 + receita v4): 3 azuis x 3 vermelhos, duas bolas.

Todo número falado sai do treino (partidas da vitrine), de medidas feitas sobre essas mesmas partidas (`queimada_medidas`:
velocidade, arremessos que voam, mira) ou de um teste em partidas novas (campeão azul contra os vermelhos finais).
O campeão é a melhor equipe azul da geração. Vitória = mais jogadores em pé quando o tempo (30 s) acaba.

Candidatos de gancho (<= 16 palavras, "-ei", número real da geração 1):
  1. "Soltei seis IAs numa quadra de queimada. Em 91 de 100 jogos, ninguém foi queimado."   (escolhido)
  2. "Ensinei seis IAs a jogar queimada. Na geração 1, só 9 de 100 jogos tiveram um queimado."
  3. "Pus três IAs contra três numa quadra. Na geração 1, quase ninguém acertou ninguém."
"""
import os

import numpy as np

from ..adaptadores.queimada import campeao_da_geracao
from ..coevolucao_queimada import partidas
from ..desafios import queimada as Q
from ..palco.holo import AMARELO, AZUL, VERDE, VERMELHO
from .queimada_medidas import medida, serie

BRANCO = (0.92, 0.96, 1.0)

ESTILO_VOZ = (
    "You are a charismatic, playful Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend watching a silly sports experiment with robots. Natural spoken Brazilian "
    "rhythm; brisk and conversational, about three words per second, never rushed, never dragging. Open deadpan and "
    "amused; let each discovery land with quiet surprise, as if you did not expect it either; finish with a "
    "playful, provocative question and trail off on the last unfinished sentence.")

DESTAQUES = {"campeão": AMARELO, "azuis": AZUL, "azul": AZUL, "vermelhos": VERMELHO, "vermelho": VERMELHO,
             "bola": AMARELO, "bolas": AMARELO, "queimado": VERMELHO, "queimada": VERMELHO}


def RESPOSTA_TESTE(v_um, v_fin):
    r = v_fin / max(v_um, 0.01)
    return "Os vermelhos evoluíram junto." if r >= 3 else "Melhorou, mas eles também."


def suave(x, k=5):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def dec(x):
    return f"{x:.1f}".replace(".", ",")


def pct1(x):
    return int(round(x))


def pct(x):
    return int(round(100 * x))


def _serie(A):
    arq = os.path.join(".cache", f"queimada_serie_{int(A.hist['semente'][0])}.npz")
    return serie(A, arq=arq)


def _full(r, k, G):
    return suave(np.interp(np.arange(G), r["g"], r[k]), 5)


def eventos(hist, A=None):
    G = len(hist["m_pegos_a"])
    ev = {"G": G, "corre": None, "mira": None, "chuva": None}
    if A is None:
        return ev
    r = _serie(A)
    vel, mira_a, mira_b, nen = (_full(r, k, G) for k in ("vel", "mira_a", "mira_b", "nenhum"))
    ev.update(vel=vel, mira_a=mira_a, mira_b=mira_b, nenhum=nen)
    ev["corre"] = next((g for g in range(G) if vel[g] >= vel[0] + 1.0), None)
    if ev["corre"] is not None:
        ev["mira"] = next((g for g in range(ev["corre"] + 3, G) if mira_b[g] >= max(0.18, mira_b[0] + 0.12)), None)
    if ev["mira"] is not None:
        ev["chuva"] = next((g for g in range(ev["mira"] + 15, G) if nen[g] <= 0.4), None)
    return ev


def nota_historia(hist):
    """Boa história: o campeão azul fica muito melhor e os jogos sem queimado diminuem muito."""
    vit = hist["m_vit_a"]
    sem_queimado = 1 - np.maximum(hist["m_vit_a"] + hist["m_vit_b"] + 0 * hist["m_empate"], 0)
    sobe = float(suave(vit, 15)[-10:].mean() - suave(vit, 15)[:10].mean())
    return float(min(sobe, 0.5) * 6 + (1 - hist["m_empate"][0]) * 0 + min(1 - hist["m_empate"][-10:].mean(), 0.8))


def duelo(hist, g, gf, n=600, semente=77):
    """Campeão azul da geração g contra os vermelhos da geração gf em n partidas novas: (vitórias, derrotas)."""
    c = campeao_da_geracao(hist, g, "a")
    rng = np.random.default_rng(semente)
    j, _ = partidas(hist["a"][g], hist["b"][gf], np.full(n, c), rng.integers(0, len(hist["b"][gf]), n), semente)
    pl = j.placar()
    return float((pl[:, 0] > pl[:, 1]).mean()), float((pl[:, 0] < pl[:, 1]).mean())


def monta(hist, A):
    ev = eventos(hist, A)
    G = ev["G"]
    if ev["chuva"] is None:
        raise RuntimeError("Esta semente não tem a história completa (corre-corre, mira, chuva de bolas): troque a semente.")
    g1, g2, g3 = ev["corre"], ev["mira"], ev["chuva"]
    n = hist["a"].shape[1]
    med = A.__dict__.setdefault("_med", {})
    medg = lambda g: med.setdefault(g, medida(A.rodada(g)))
    m0, m1, m2, m3 = medg(0), medg(g1), medg(g2), medg(g3)
    for g in (g1, g2, g3):                       # libera memória das rodadas usadas só nas medidas
        A._cache.pop((g, False), None)
    v_um, d_um = duelo(hist, 0, G - 1)
    v_pico, d_pico = duelo(hist, g2, G - 1)
    v_fin, d_fin = duelo(hist, G - 1, G - 1)
    C = G
    cenas, marcos = [], []
    nen0 = pct(m0["nenhum"])

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ------------------------------------------------------------ GANCHO
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("SOLTEI 2 TIMES DE IAs", BRANCO), (f"{nen0} DE {n} JOGOS: NINGUÉM QUEIMADO", AMARELO)],
         log=[(f"{n} PARTIDAS AO MESMO TEMPO", BRANCO), ("AZUL x VERMELHO · 0 REGRAS", AMARELO)],
         carimbo={"texto": f"{nen0} DE {n}", "cor": AMARELO, "em": 1.4, "sub": "JOGOS SEM NINGUÉM QUEIMADO · GERAÇÃO 1"},
         fala=f"Soltei dois times de IAs na queimada. <short pause> Em {nen0} de 100 jogos, ninguém foi queimado.")
    # ------------------------------------------------------------ PREMISSA + REGRA + PROMESSA
    cena(tipo="ao_vivo", ger=min(2, G - 1), grupo="g1b",
         log=[("QUEM VAI MELHOR VIRA PAI DA PRÓXIMA TURMA", AMARELO), ("AZUL x VERMELHO · UM CÉREBRO POR TIME", BRANCO)],
         fala="Quem vai melhor vira pai da próxima turma. <short pause> No fim, o campeão azul enfrenta os vermelhos.")
    # ------------------------------------------------------------ GERAÇÃO 1: o campeão falha
    r0 = A.rodada(C)
    k0 = A.busca(r0, "livre") or A.busca(r0, "campeao")
    cena(tipo="replay", ger=C, foco=k0, grupo="g1c", log=[("CAMPEÃO AZUL DA GER 001 · NINGUÉM QUEIMADO", AMARELO)],
         fala="O campeão azul da geração 1. <short pause> Não queimou ninguém. <short pause> Nem sem querer.")
    # ------------------------------------------------------------ DESCOBERTA 2: a mira
    r2 = A.rodada(C + g2)
    k2 = A.busca(r2, "acerta") or A.busca(r2, "campeao")
    cena(tipo="replay", ger=C + g2, foco=k2,
         cartao={"numero": 1, "rotulo": "VERMELHOS", "nome": "A MIRA", "cor": VERMELHO,
                 "stat": f"ARREMESSOS NO ALVO {pct(m0['mira_b'])}% → {pct(m2['mira_b'])}%"},
         log=[(f"GER {g2 + 1:03d} · MIRA VERMELHA {pct(m0['mira_b'])}% → {pct(m2['mira_b'])}%", VERMELHO)],
         fala=f"Geração {g2 + 1}. Os vermelhos começam a mirar. <short pause> De {pct(m0['mira_b'])} para {pct(m2['mira_b'])} em 100 arremessos, direto num adversário.")
    marcos.append((g2, "1", VERMELHO))
    # ------------------------------------------------------------ RE-GANCHO
    cena(tipo="ao_vivo", ger=g2,
         log=[(f"GER {g2 + 1:03d} · OS VERMELHOS MIRAM. E OS AZUIS?", AZUL), (f"AZUIS CORREM {dec(m0['vel'])} → {dec(m1['vel'])} m/s", AMARELO)],
         carimbo={"texto": "E OS AZUIS?", "cor": AZUL, "em": 0.4, "sub": f"GERAÇÃO {g2 + 1}"},
         fala="Só que o azul quase não aprendeu a mirar. Só correu mais. <short pause> Alguém vai se queimar? <long pause>")
    # ------------------------------------------------------------ DESCOBERTA 3: o bombardeio
    r3 = A.rodada(C + g3)
    k3 = A.busca(r3, "azul_acerta") or A.busca(r3, "acerta") or A.busca(r3, "campeao")
    cena(tipo="replay", ger=C + g3, foco=k3,
         cartao={"numero": 2, "rotulo": "OS DOIS TIMES", "nome": "O JOGO ESQUENTA", "cor": AMARELO,
                 "stat": f"JOGOS SEM NINGUÉM QUEIMADO {pct(m0['nenhum'])}% → {pct(m3['nenhum'])}%"},
         log=[(f"GER {g3 + 1:03d} · SEM QUEIMADO {pct(m0['nenhum'])}% → {pct(m3['nenhum'])}%", AMARELO)],
         fala=f"Geração {g3 + 1}. Jogos sem ninguém queimado. <long pause> De {pct(m0['nenhum'])} para {pct(m3['nenhum'])} em 100. "
              "<short pause> Agora a bola acha alguém.")
    marcos.append((g3, "2", AMARELO))
    # ------------------------------------------------------------ TESTE (o CHUTE fecha a fala; a resposta abre a cena seguinte)
    itens = [("CAMPEÃO 1", v_um, AZUL), (f"CAMPEÃO {g2 + 1}", v_pico, AZUL), (f"CAMPEÃO {G}", v_fin, VERDE)]
    duelo_kw = dict(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="CAMPEÃO AZUL x VERMELHOS FINAIS",
                    sub="600 jogos novos · vitória = mais gente em pé aos 30 s", destaque=2, cor_destaque="verde", rotulo_destaque="▲ MELHOR",
                    log=[("TESTE: 600 JOGOS NOVOS", AMARELO), (f"VITÓRIAS {pct(v_um)}% → {pct(v_pico)}% → {pct(v_fin)}%", AMARELO)])
    cena(teste=True, **duelo_kw,
         fala=f"Contra os vermelhos finais. <short pause> O campeão da geração 1 vence {pct(v_um)} em 100. "
              "Chuta aí: e o campeão final? <long pause>")
    cena(**dict(duelo_kw, sub=f"vitórias do azul · o final também perde {pct(d_fin)}"), fala=f"{pct(v_fin)} em 100. <short pause> Quase sem mirar. Juro, eu ri sozinho.")
    # ------------------------------------------------------------ CTA + LAÇO
    rf = A.rodada(C + G - 1)
    kf = A.busca(rf, "acerta") or A.busca(rf, "campeao")
    cena(tipo="replay", ger=C + G - 1, foco=kf, grupo="fim",
         escolha={"pergunta": "O QUE O CAMPEÃO APRENDEU?", "opcoes": [("APRENDEU A JOGAR", AZUL), ("SÓ A CORRER", VERMELHO)], "em": 0.2},
         destaques={"azul": AZUL, "vermelho": VERMELHO, "campeão": AMARELO},
         fala="O campeão aprendeu a jogar ou só a correr? <short pause> Porque tudo começou quando eu…")

    serie_ger = 1 - ev["nenhum"]
    info = {"marca": "VÍDEO NEURAL", "serie": serie_ger, "serie_rotulo": "% JOGOS COM ALGUÉM QUEIMADO",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} PARTIDAS",
            "rodape": f"{n} PARTIDAS · REDE {'-'.join(map(str, Q.CAM))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"Em {nen0} de 100 jogos, ninguém foi queimado. Aí a seleção natural entrou na quadra. 🏐\n"
            f"IA aprendendo sozinha por seleção natural (rede neural + algoritmo genético). Simulação real: {n} partidas por geração, {G} gerações, "
            "números medidos no treino.\n"
            "Manda pra quem sempre foi o último escolhido na queimada 👇\n\n"
            "#inteligenciaartificial #ia #redeneural #algoritmogenetico #queimada")
    ev["duelo"] = {"um": (v_um, d_um), "pico": (g2, v_pico, d_pico), "fin": (G - 1, v_fin, d_fin), "med": (m0, m1, m2, m3)}
    return cenas, info, post, ev
