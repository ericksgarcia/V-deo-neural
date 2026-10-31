"""Roteiro do episódio Fuga com Cobertura (guia v2-v5 + trava de retenção §17): 12 IAs azuis atravessam a zona de tiro de uma torreta.

Curadoria autorizada (docs/ROTEIRO.md §16.2): torreta rápida (1 tiro a cada 0,13 s, bala de 11 m/s, alvo sorteado entre os azuis ao alcance),
blocos largos que deslizam e absorvem tiros; só os azuis evoluem. O treino NÃO achou "carona atrás do bloco": os azuis passaram a se
esconder MENOS e a correr reto. O roteiro conta só isso. Todo número falado sai das cidades da vitrine ou de 300 cidades novas.
"""
import numpy as np

from ..coevolucao_fuga import campeao, cidades
from ..desafios import fuga as F
from ..palco.holo import AMARELO, CIANO, VERMELHO

BRANCO = (0.92, 0.96, 1.0)
VERDE = (0.3, 1.0, 0.62)

DESTAQUES = {"campeão": AMARELO, "azuis": CIANO, "torreta": VERMELHO, "reto": CIANO, "zigue-zaguear": AMARELO, "bloco": VERDE}


def suave(x, k=5):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def dec(x):
    s = f"{x:.1f}".replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


def eventos(hist):
    G = len(hist["m_chegou"])
    ch, lat, at = suave(hist["m_chegou"]), suave(hist["m_lat"]), suave(hist["m_atras"])
    ev = {"G": G, "ch": ch, "lat": lat, "at": at, "reto": None, "esconde": None}
    ch0, lat0, at0 = ch[:3].mean(), lat[:3].mean(), at[:3].mean()
    ev["reto"] = next((g for g in range(3, G) if ch[g] >= ch0 + 0.12 and lat[g] <= 0.6 * lat0), None)
    if ev["reto"] is not None:
        ev["esconde"] = next((g for g in range(ev["reto"] + 2, G) if at[g] <= 0.82 * at0), None)
    return ev


def nota_historia(hist):
    ev = eventos(hist)
    if ev["reto"] is None or ev["esconde"] is None:
        return 0.0
    ch = ev["ch"]
    return float(min(ch[-10:].mean() - ch[:3].mean(), 0.5) * 6 + hist["m_zero"][:3].mean() + min(ev["esconde"] - ev["reto"], 25) / 10)


def duelo(hist, g, rodadas=5, semente=77):
    """A TURMA inteira da geração g (todos os cérebros) em cidades novas: fração de azuis que chega (0-1)."""
    genes = hist["genes"][g]
    pop = len(genes)
    j, _ = cidades(genes, np.repeat(np.arange(pop), rodadas), semente + g)
    return float(j.chegou.mean())


def pct(x):
    return f"{100 * x:.0f}"


def monta(hist, A):
    ev = eventos(hist)
    G = ev["G"]
    if ev["reto"] is None or ev["esconde"] is None:
        raise RuntimeError("Esta semente não tem a história completa (correr reto e se esconder menos): troque a semente.")
    gr, ge = ev["reto"], ev["esconde"]
    n = F.A
    zero = int(round(100 * float(hist["m_zero"][:3].mean())))
    a0, a1 = int(round(100 * float(hist["m_atras"][:3].mean()))), int(round(100 * float(ev["at"][ge])))
    l0, l1 = float(hist["m_lat"][:3].mean()), float(ev["lat"][gr])
    s_um, s_fin, s_gr = duelo(hist, 0), duelo(hist, G - 1), duelo(hist, gr)   # mesma medida (cidades novas) em todo o vídeo
    c0, c1 = int(round(100 * s_um)), int(round(100 * s_gr))
    C = G
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    vezes = int(round(s_fin / max(s_um, 0.005)))
    reacao_vis = "MAIS DE DEZ VEZES MAIS" if vezes >= 10 else f"{vezes} VEZES MAIS" if vezes >= 2 else "MELHOROU"
    # ------------------------------------------------------------ GANCHO
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("1 TORRETA x 12 IAs", BRANCO), (f"NINGUÉM PASSOU EM {zero} DE 100", AMARELO)],
         log=[(f"{n} IAs · 1 TORRETA", VERMELHO), ("NINGUÉM SABE O QUE FAZER", AMARELO)],
         carimbo={"texto": f"{zero} DE 100", "cor": AMARELO, "em": 0.5, "sub": "CIDADES ONDE NINGUÉM CHEGOU · GERAÇÃO 1"},
         fala=f"Coloquei uma torreta atirando em IAs. <short pause> Em {zero} de 100 cidades, ninguém passou.")
    # ------------------------------------------------------------ PREMISSA + REGRA + PROMESSA (sem números)
    cena(tipo="ao_vivo", ger=min(3, G - 1), grupo="g1b",
         log=[("A TORRETA ATIRA E OS BLOCOS DESLIZAM", VERMELHO), ("QUEM PASSA VIRA PAI DA PRÓXIMA TURMA", VERDE)],
         fala="Aí quem passa vira pai da próxima turma, igual escolher o time.")
    # ------------------------------------------------------------ GERAÇÃO 1: o campeão cai
    r0 = A.rodada(C)
    k0 = A.busca(r0, "caiu")
    cena(tipo="replay", ger=C, foco=k0, grupo="g1c", log=[("CAMPEÃO DA GER 001 · ATINGIDO", VERMELHO)],
         fala="É tipo atravessar um campo cheio de bolas. <short pause> O campeão levou bolada. No fim, testo em cidades novas.")
    # ------------------------------------------------------------ DESCOBERTA 1: correr reto
    r1 = A.rodada(C + gr)
    k1 = A.busca(r1, "chegou")
    cena(tipo="replay", ger=C + gr, foco=k1,
         cartao={"numero": 1, "rotulo": "AZUIS", "nome": "CORRER RETO", "cor": CIANO,
                 "stat": f"PASSAM {c0}% → {c1}%"},
         log=[(f"GER {gr + 1:03d} · PASSAM {c0}% → {c1}%", CIANO)],
         fala=f"Aí o campeão foi parando de zigue-zaguear. <long pause> A turma passou de {c0} para {c1} em 100. <short pause> Só que ficou estranho.")
    marcos.append((gr, "1", CIANO))
    # ------------------------------------------------------------ RE-GANCHO + DESCOBERTA 2 numa cena só (o número fica no cartão)
    cena(tipo="ao_vivo", ger=ge,
         cartao={"numero": 2, "rotulo": "AZUIS", "nome": "SE ESCONDER MENOS", "cor": VERDE,
                 "stat": f"ESCONDIDOS {a0}% → {a1}% DO TEMPO"},
         log=[(f"GER {ge + 1:03d} · ATRÁS DO BLOCO {a0}% → {a1}%", VERDE)],
         fala="Aí olhei os esconderijos. <long pause> Ficaram menos tempo escondidos. <short pause> Será que esconder atrapalhava?")
    marcos.append((ge, "2", VERDE))
    # ------------------------------------------------------------ TESTE (a turma inteira)
    itens = [("TURMA 1", s_um, CIANO), (f"TURMA {G}", s_fin, VERDE)]
    kw = dict(tipo="barras", grupo="teste", ger=G - 1, fundo_escuro=0.35, fundo_vivo=0.9, fundo_vel=2.0, itens=itens, titulo="TURMA AZUL x TORRETA",
              sub="cidades novas · azuis que chegam", destaque=1, cor_destaque="verde", rotulo_destaque="",
              log=[("TESTE: CIDADES NOVAS", AMARELO), (f"CHEGAM {pct(s_um)}% → {pct(s_fin)}%", AMARELO)])
    cena(teste=True, **kw,
         fala=f"Só que faltava o teste. <short pause> A turma da geração 1 passava {pct(s_um)}. Chuta aí: e a final? <long pause>")
    cena(**dict(kw, sub=f"azuis que chegam · {reacao_vis}"), fala=f"{pct(s_fin)} em 100. <short pause> Juro, ninguém ensinou ela a correr reto.")
    # ------------------------------------------------------------ CTA + LAÇO
    rf = A.rodada(C + G - 1)
    kf = A.busca(rf, "chegou")
    cena(tipo="replay", ger=C + G - 1, foco=kf, grupo="fim",
         destaques={"reto": CIANO, "campeão": AMARELO},
         fala="Correr reto é coragem ou burrice? <short pause> Porque tudo começou quando eu…")

    info = {"marca": "VÍDEO NEURAL", "serie": suave(hist["m_chegou"], 5), "serie_rotulo": "% AZUIS QUE CHEGAM",
            "marcos": marcos, "rotulo_vivo": f"{n} IAs", "nome_teste": "TESTE FINAL",
            "rodape": f"{n} IAs · TORRETA E BLOCOS PROGRAMADOS: SÓ OS AZUIS EVOLUEM · {G} GERAÇÕES · "
                      "NINGUÉM PROGRAMOU CORRER: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"{zero} de 100 cidades, e ninguém passou pela torreta. Aí as IAs mudaram de plano... 🎯\n"
            f"IA aprendendo sozinha por seleção natural. Simulação real: {n} IAs por cidade, {G} gerações, números medidos no treino.\n"
            "Marca quem acha que esconder é sempre o plano mais seguro 👇\n\n"
            "#inteligenciaartificial #ia #aprendizadodemaquina #simulacao #selecaonatural")
    ev["teste"] = {"um": s_um, "fin": s_fin, "ch": (c0, c1), "atras": (a0, a1), "lat": (l0, l1), "zero": zero}
    return cenas, info, post, ev
