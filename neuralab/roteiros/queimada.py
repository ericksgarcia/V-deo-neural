"""Roteiro do episódio Queimada de IAs (guia v2-v5 + trava de retenção §17): 3 azuis x 3 vermelhas, uma bola.

Curadoria autorizada (docs/ROTEIRO.md §16.2): quadra pequena em pé; mira automática no adversário mais perto (com antecipação) — a IA decide QUANDO
soltar a bola e ainda corrige o ângulo; um "gandula" automático rola a bola parada até a jogadora mais perto; ponto por acerto e por pegar a bola; nas
20 primeiras gerações os adversários andam mais devagar (currículo); regra do relógio de 20 s (vence quem tem mais gente na quadra). A "cera" (segurar
a bola para ganhar no relógio) NÃO apareceu; o roteiro conta só o que foi medido: soltar a bola logo e acertar mais. Todo número falado sai das partidas
da vitrine (médias de 7 gerações) ou de 600 partidas novas (campeão de cada geração contra as vermelhas finais).
"""
import numpy as np

from ..adaptadores.queimada import campeao_da_geracao
from ..coevolucao_queimada import partidas
from ..desafios import queimada as Q
from ..palco.holo import AMARELO, CIANO, MAGENTA, VERDE, VERMELHO

BRANCO = (0.92, 0.96, 1.0)
DESTAQUES = {"campeão": AMARELO, "bola": AMARELO, "azuis": CIANO, "vermelhas": MAGENTA, "coitadas": MAGENTA, "largar": VERDE, "acertar": VERDE}


def suave(x, k=7):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def pct(x):
    return f"{100 * x:.0f}"


def eventos(hist):
    G = len(hist["m_acerto"])
    seg, ac = suave(hist["m_seg"]), suave(hist["m_acerto"])
    az, vm = suave(hist["m_azul_vence"]), suave(hist["m_verm_vence"])
    ev = {"G": G, "seg": seg, "ac": ac, "az": az, "vm": vm, "mao": None, "mira": None, "parelho": None}
    seg0, ac0 = float(hist["m_seg"][:3].mean()), float(hist["m_acerto"][:3].mean())
    ev["mao"] = next((g for g in range(3, G) if seg[g] <= 0.1 and seg[g] <= 0.25 * seg0), None)
    if ev["mao"] is None:
        return ev
    ev["mira"] = next((g for g in range(ev["mao"] + 25, G) if ac[g] >= max(0.40, ac0 + 0.2)), None)
    if ev["mira"] is None:
        return ev
    cand = [g for g in range(ev["mao"] + 8, ev["mira"] - 8) if vm[g] >= 0.3]
    ev["parelho"] = min(cand, key=lambda g: abs(az[g] - vm[g])) if cand else None
    return ev


def duelo(hist, g, ga, n=600, semente=77):
    """O campeão azul da geração g contra os vermelhos da geração ga em n partidas novas: fração de vitórias (mais gente na quadra)."""
    c = campeao_da_geracao(hist, g)
    rng = np.random.default_rng(semente + g)
    j, _ = partidas(hist["az"][g][[c]], hist["vm"][ga], np.zeros(n, int), rng.integers(0, len(hist["vm"][ga]), n), semente + g)
    return float((j.resultado() > 0).mean())


def nota_historia(hist):
    ev = eventos(hist)
    if ev["mira"] is None or ev["parelho"] is None:
        return 0.0
    G = ev["G"]
    s1, sf = duelo(hist, 0, G - 1), duelo(hist, G - 1, G - 1)
    if sf - s1 < 0.5:
        return 0.0
    zero = float(hist["m_zero"][:3].mean())
    return float(3 + 2 * (sf - s1) + zero + min(abs(ev["vm"][ev["parelho"]] - ev["az"][ev["parelho"]]) < 0.05, 1))


def monta(hist, A):
    ev = eventos(hist)
    G = ev["G"]
    if ev["mira"] is None or ev["parelho"] is None:
        raise RuntimeError("Esta semente não tem a história completa (soltar a bola, parelho, acertar): troque a semente.")
    gm, gp, gx = ev["mao"], ev["parelho"], ev["mira"]
    n = Q.NS * 2
    zero = int(round(100 * float(hist["m_zero"][:3].mean())))
    seg0, seg1 = int(round(100 * float(hist["m_seg"][:3].mean()))), int(round(100 * float(ev["seg"][gm])))
    ac0, ac1 = int(round(100 * float(hist["m_acerto"][:3].mean()))), int(round(100 * float(ev["ac"][gx])))
    az_p, vm_p = int(round(100 * float(ev["az"][gp]))), int(round(100 * float(ev["vm"][gp])))
    g_ref = 45
    s_um, s_ref, s_fin = duelo(hist, 0, G - 1), duelo(hist, g_ref, G - 1), duelo(hist, G - 1, G - 1)
    if s_fin - s_um < 0.5:
        raise RuntimeError("O campeão final não supera o da geração 1 em partidas novas: troque a semente.")
    C = G
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ------------------------------------------------------------ GANCHO
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.7,
         titulo_gancho=[("DUAS TURMAS DE IA NA QUEIMADA", BRANCO), (f"NINGUÉM ATINGIDO EM {zero} DE 100", AMARELO)],
         log=[(f"{n} IAs · QUEIMADA", BRANCO), ("AZUIS x VERMELHAS · 0 REGRAS DE COMO JOGAR", CIANO)],
         carimbo={"texto": f"{zero} DE 100", "cor": AMARELO, "em": 0.8, "sub": "JOGOS SEM NINGUÉM ATINGIDO · GERAÇÃO 1"},
         fala=f"Joguei seis IAs numa queimada: <short pause> em {zero} de 100 jogos, ninguém acertou ninguém.")
    # ------------------------------------------------------------ GERAÇÃO 1: o campeão leva bolada + promessa
    r0 = A.rodada(C)
    k0 = A.busca(r0, "levou")
    cena(tipo="replay", ger=C, foco=k0, grupo="g1c", log=[("ACERTOU: O OUTRO SAI · QUEM JOGA MELHOR VIRA PAI DA PRÓXIMA TURMA", AMARELO)],
         fala="Tipo na escola: acertou, sai. O campeão da geração 1 entrou e levou bolada. <short pause> No fim, testo ele.")
    # ------------------------------------------------------------ DESCOBERTA 1: mão quente
    r1 = A.rodada(C + gm)
    k1 = A.busca(r1, "acerto")
    cena(tipo="replay", ger=C + gm, foco=k1,
         cartao={"numero": 1, "rotulo": "AZUIS", "nome": "MÃO QUENTE", "cor": VERDE, "stat": f"BOLA NA MÃO {seg0}% → {seg1}% DO TEMPO"},
         log=[(f"GER {gm + 1:03d} · BOLA NA MÃO {seg0}% → {seg1}%", VERDE)],
         fala=f"Aí o campeão largou a bola. <long pause> Antes, {seg0}% do tempo com ela. Agora, {seg1}. <short pause> Batata quente.")
    marcos.append((gm, "1", VERDE))
    # ------------------------------------------------------------ RE-GANCHO: os vermelhos também aprendem
    cena(tipo="ao_vivo", ger=gp,
         log=[(f"GER {gp + 1:03d} · AZUIS VENCEM {az_p}% · VERMELHAS {vm_p}%", AMARELO), ("PARELHO", AMARELO)],
         carimbo={"texto": "PARELHO", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {gp + 1} · {az_p}% x {vm_p}%"},
         fala=f"Só que o time vermelho aprendia também. <short pause> Será que o jogo travou de vez? <long pause>")
    # ------------------------------------------------------------ DESCOBERTA 2: acertar mais
    r2 = A.rodada(C + gx)
    k2 = A.busca(r2, "acerto")
    cena(tipo="replay", ger=C + gx, foco=k2,
         cartao={"numero": 2, "rotulo": "AZUIS", "nome": "ARREMESSO CERTEIRO", "cor": CIANO, "stat": f"ARREMESSOS QUE ACERTAM {ac0}% → {ac1}%"},
         log=[(f"GER {gx + 1:03d} · ACERTOS {ac0}% → {ac1}%", CIANO)],
         fala=f"O campeão passou a acertar. <long pause> Mais que o dobro de acertos. <short pause> Ninguém mandou: dei pontos por acertar.")
    marcos.append((gx, "2", CIANO))
    # ------------------------------------------------------------ TESTE (CHUTE)
    itens = [("CAMPEÃO 1", s_um, CIANO), (f"CAMPEÃO {g_ref + 1}", s_ref, CIANO), (f"CAMPEÃO {G}", s_fin, VERDE)]
    kw = dict(tipo="barras", grupo="teste", ger=G - 1, fundo_escuro=0.35, fundo_vivo=0.9, fundo_vel=2.0, itens=itens,
              titulo="CAMPEÃO AZUL x VERMELHAS FINAIS", sub="600 partidas novas · vitórias do azul", destaque=2, cor_destaque="verde",
              rotulo_destaque="", log=[("TESTE: 600 PARTIDAS NOVAS", AMARELO), (f"VITÓRIAS {pct(s_um)}% → {pct(s_ref)}% → {pct(s_fin)}%", AMARELO)])
    cena(teste=True, **kw,
         fala="Agora o teste. <short pause> Chuta aí: quantos em 100 o campeão final vence? <long pause>")
    cena(**kw, fala=f"{round(100 * s_fin)} em 100. <short pause> Coitadas.")
    # ------------------------------------------------------------ CTA + LAÇO
    rf = A.rodada(C + G - 1)
    kf = A.busca(rf, "vence")
    cena(tipo="replay", ger=C + G - 1, foco=kf, grupo="fim", destaques={"larga": VERDE, "segura": CIANO, "campeão": AMARELO},
         fala="Largar a bola é esperteza ou fugir do jogo? <short pause> Porque tudo começou quando eu…")

    info = {"marca": "VÍDEO NEURAL", "serie": suave(hist["m_azul_vence"], 5), "serie_rotulo": "% VITÓRIAS DO AZUL",
            "marcos": marcos, "rotulo_vivo": f"{n} IAs", "nome_teste": "TESTE FINAL",
            "rodape": f"{n} IAs · MIRA AUTOMÁTICA, GANDULA E RELÓGIO DE 20 s PROGRAMADOS · PONTOS POR ACERTAR E PEGAR A BOLA · ADVERSÁRIAS MAIS LENTAS NAS 20 PRIMEIRAS GERAÇÕES"}
    post = (f"Em {zero} de 100 jogos, ninguém acertou ninguém. Aí as IAs aprenderam a jogar... 🏐\n"
            f"IA aprendendo sozinha por seleção natural. Simulação real: {n} IAs por jogo, {G} gerações, números medidos no treino.\n"
            "Marca quem na escola nunca largava a bola 👇\n\n"
            "#inteligenciaartificial #ia #aprendizadodemaquina #simulacao #queimada")
    ev["teste"] = {"um": s_um, "ref": s_ref, "fin": s_fin, "seg": (seg0, seg1), "ac": (ac0, ac1), "par": (az_p, vm_p), "zero": zero}
    return cenas, info, post, ev
