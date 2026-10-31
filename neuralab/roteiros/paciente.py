"""Roteiro do episódio Paciente Zero (guia v2 + v3 + v4 + v5): 1 ponto verde contagia uma cidade de 29 IAs azuis.

Curadoria autorizada (docs/ROTEIRO.md §16.2): vírus mais lento que os saudáveis (2,2 contra 3,0 m/s), 30 agentes, 4 sementes
testadas e fica a que conta a melhor história. Todo número falado sai das cidades da vitrine (métricas do treino) ou de um teste
em 300 cidades novas contra os vírus finais. "O campeão" = o melhor cérebro azul da geração (torneio em cidades novas).
"""
import numpy as np

from ..coevolucao_paciente import ARQ, campeao_sau, cidades
from ..desafios import paciente as P
from ..palco.holo import AMARELO, CIANO, VERMELHO

BRANCO = (0.92, 0.96, 1.0)
VERDE = (0.3, 1.0, 0.62)
TOXICO = (0.62, 1.0, 0.12)

DESTAQUES = {"campeão": AMARELO, "verde": TOXICO, "verdes": TOXICO, "azuis": CIANO, "azul": CIANO, "juntaram": AMARELO,
             "fugir": CIANO, "coitado": VERMELHO}


def suave(x, k=5):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def dec(x):
    """9.6 -> '9,6'; 1.0 -> '1' (a voz lê 'um vírgula zero' estranho)."""
    s = f"{x:.1f}".replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


def eventos(hist):
    G = len(hist["m_saudaveis"])
    sau, dist, nn = suave(hist["m_saudaveis"]), suave(hist["m_dist_inf"]), suave(hist["m_nn"])
    ev = {"G": G, "sau": sau, "dist": dist, "nn": nn, "fugir": None, "juntar": None}
    d0, n0 = dist[:3].mean(), nn[:3].mean()
    ev["fugir"] = next((g for g in range(3, G) if dist[g] >= d0 + 1.0 and sau[g] >= sau[:3].mean() + 0.1), None)
    if ev["fugir"] is not None:
        ev["juntar"] = next((g for g in range(ev["fugir"] + 3, G) if nn[g] <= 0.75 * n0), None)
    return ev


def nota_historia(hist):
    """Boa história: começa ruim, melhora muito e a descoberta 'se juntar' aparece depois da 'fugir'."""
    ev = eventos(hist)
    if ev["fugir"] is None or ev["juntar"] is None:
        return 0.0
    sau = ev["sau"]
    return float(min(sau[-10:].mean() - sau[:3].mean(), 0.5) * 6 + (1 - hist["m_saudaveis"][0]) + (ev["juntar"] > ev["fugir"]))


def duelo(hist, g, n=300, semente=77):
    """Campeão azul da geração g em n cidades novas contra os vírus FINAIS: fração de azuis no fim (0-1)."""
    c = campeao_sau(hist, g)
    rng = np.random.default_rng(semente)
    gv = hist["vir"][-1]
    j, _ = cidades(hist["sau"][g], gv, np.full(n, c), rng.integers(0, len(gv), n), semente)
    return float((1 - j.curva[:, -1] / P.A).mean())


def pct(x):
    return f"{100 * x:.0f}"


def monta(hist, A):
    ev = eventos(hist)
    G = ev["G"]
    if ev["fugir"] is None or ev["juntar"] is None:
        raise RuntimeError("Esta semente não tem a história completa (fugir, depois se juntar): troque a semente.")
    gf, gj = ev["fugir"], ev["juntar"]
    n = P.A
    d0, d1 = float(hist["m_dist_inf"][:3].mean()), float(ev["dist"][gf])
    v0, v1 = float(hist["m_nn"][:3].mean()), float(ev["nn"][gj])
    inf0 = int(round(n * float(hist["m_infectados"][:3].mean())))
    s_um, s_fin = duelo(hist, 0), duelo(hist, G - 1)
    C = G                                              # ger >= G pede a cidade do CAMPEÃO da geração (ger - G)
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ------------------------------------------------------------ GANCHO
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("1 PONTO VERDE CONTAGIA", BRANCO), (f"EM 30 SEGUNDOS: {inf0} DE {n}", TOXICO)],
         log=[(f"{n} IAs · 1 CONTAGIADA", TOXICO), ("NINGUÉM SABE O QUE FAZER", AMARELO)],
         carimbo={"texto": f"{inf0} DE {n}", "cor": TOXICO, "em": 1.4, "sub": "VIRARAM VERDES · GERAÇÃO 1"},
         fala=f"Soltei 1 ponto verde entre {n - 1} azuis. <short pause> Em 30 segundos, {inf0} já eram verdes.")
    # ------------------------------------------------------------ PREMISSA + REGRA + PROMESSA
    cena(tipo="ao_vivo", ger=min(3, G - 1), grupo="g1b",
         log=[("ENCOSTAR NO VERDE CONTAGIA", TOXICO), ("QUEM ESCAPA VIRA PAI DA PRÓXIMA TURMA", VERDE)],
         fala="Quem escapa vira pai da próxima turma. <short pause> No fim, testo o campeão em cidades novas.")
    # ------------------------------------------------------------ GERAÇÃO 1: o campeão falha
    r0 = A.rodada(C)
    k0 = A.busca(r0, "primeiro")
    cena(tipo="replay", ger=C, foco=k0, grupo="g1c", log=[("CAMPEÃO DA GER 001 · PEGO", TOXICO)],
         fala="É tipo escolher o time mais forte. <short pause> Mas o campeão da geração 1 foi pego.")
    # ------------------------------------------------------------ DESCOBERTA 1: fugir do verde
    r1 = A.rodada(C + gf)
    k1 = A.busca(r1, "ileso")
    cena(tipo="replay", ger=C + gf, foco=k1,
         cartao={"numero": 1, "rotulo": "AZUIS", "nome": "FUGIR DO VERDE", "cor": CIANO,
                 "stat": f"DISTÂNCIA DO VERDE {dec(d0)} → {dec(d1)} m"},
         log=[(f"GER {gf + 1:03d} · DISTÂNCIA {dec(d0)} → {dec(d1)} m", CIANO)],
         fala=f"Aí, na geração {gf + 1}, o campeão aprendeu a fugir. <long pause> De {dec(d0)} para {dec(d1)} metros do verde. "
              "<short pause> Coitado.")
    marcos.append((gf, "1", CIANO))
    # ------------------------------------------------------------ RE-GANCHO
    cena(tipo="ao_vivo", ger=gf,
         log=[(f"GER {gf + 1:03d} · OS AZUIS ESCAPAM MAIS", CIANO)],
         carimbo={"texto": "UMA PEGADINHA", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {gf + 1}"},
         fala="Só que tem uma pegadinha. <long pause>")
    # ------------------------------------------------------------ DESCOBERTA 2: eles se juntam
    r2 = A.rodada(C + gj)
    k2 = A.busca(r2, "ileso")
    cena(tipo="replay", ger=C + gj, foco=k2,
         cartao={"numero": 2, "rotulo": "AZUIS", "nome": "SE JUNTAR", "cor": AMARELO,
                 "stat": f"VIZINHO MAIS PERTO {dec(v0)} → {dec(v1)} m"},
         log=[(f"GER {gj + 1:03d} · VIZINHO {dec(v0)} → {dec(v1)} m", AMARELO)],
         fala=f"Eles não se afastaram: se juntaram. <long pause> De {dec(v0)} para {dec(v1)} metro do vizinho. "
              "<short pause> Ninguém ensinou isso.")
    marcos.append((gj, "2", AMARELO))
    # ------------------------------------------------------------ TESTE
    itens = [("CAMPEÃO 1", s_um, CIANO), (f"CAMPEÃO {G}", s_fin, VERDE)]
    kw = dict(tipo="barras", grupo="teste", ger=G - 1, itens=itens, titulo="CAMPEÃO AZUL x VERDES FINAIS",
              sub="300 cidades novas · azuis no fim", destaque=1, cor_destaque="verde", rotulo_destaque="▲ MELHOR",
              log=[("TESTE: 300 CIDADES NOVAS", AMARELO), (f"AZUIS NO FIM {pct(s_um)}% → {pct(s_fin)}%", AMARELO)])
    cena(teste=True, **kw,
         fala=f"Hora do teste. <short pause> O campeão da geração 1 mantém {pct(s_um)} em 100 azuis. Chuta aí: e o final? <long pause>")
    cena(**kw, fala=f"{pct(s_fin)} em 100. <short pause> Juro, eu fiquei olhando.")
    # ------------------------------------------------------------ CTA + LAÇO
    rf = A.rodada(C + G - 1)
    kf = A.busca(rf, "ileso")
    cena(tipo="replay", ger=C + G - 1, foco=kf, grupo="fim",
         escolha={"pergunta": "FUGIU OU SE ESCONDEU?", "opcoes": [("FUGIU", CIANO), ("SE ESCONDEU", AMARELO)], "em": 0.2},
         destaques={"fugir": CIANO, "esconder": AMARELO, "campeão": AMARELO},
         fala="O campeão fugiu ou só se escondeu na parede? <short pause> Porque tudo começou quando eu…")

    info = {"marca": "VÍDEO NEURAL", "serie": suave(hist["m_saudaveis"], 5), "serie_rotulo": "% AZUIS NO FIM",
            "marcos": marcos, "rotulo_vivo": f"{n} IAs", "nome_teste": "TESTE FINAL",
            "rodape": f"{n} IAs · VERDE MAIS LENTO (2,2 x 3,0 m/s) · REDES {'-'.join(map(str, P.CAMADAS))} · {G} GERAÇÕES · "
                      "NINGUÉM PROGRAMOU FUGIR: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"1 ponto verde entre 29 IAs: em 30 segundos, {inf0} já tinham mudado de cor. O que elas fizeram depois? 🟢\n"
            f"IA aprendendo sozinha por seleção natural (rede neural + algoritmo genético). Simulação real: {n} IAs por cidade, {G} gerações, "
            "números medidos no treino.\n"
            "Manda pra quem sempre foge quando alguém espirra 👇\n\n"
            "#inteligenciaartificial #ia #aprendizadodemaquina #simulacao #pacientezero")
    ev["teste"] = {"um": s_um, "fin": s_fin, "dist": (d0, d1), "viz": (v0, v1), "inf0": inf0}
    return cenas, info, post, ev
