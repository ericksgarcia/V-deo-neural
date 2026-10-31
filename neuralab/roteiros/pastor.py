"""Roteiro do episódio Cão Pastor (guia v2-v5 + trava de retenção §17): 1 cão IA leva 15 ovelhas ao curral.

Curadoria autorizada (§16.2): ovelhas e curral PROGRAMADOS (ovelhas fogem do cão e tendem a ficar juntas); só o cérebro do cão evolui. Recompensa
guiada: ovelhas no curral no fim + um pouco por aproximar o rebanho da entrada (o rodapé diz isso). Nada premia "ir por trás" nem "juntar".
Descobertas medidas: achar o rebanho (distância cão-rebanho cai), ficar atrás do rebanho (lado oposto ao curral) e juntar o rebanho (espalhamento cai).
Todo número falado sai das cidades da vitrine ou de 300 cidades novas.
"""
import numpy as np

from ..coevolucao_pastor import campeao, cidades
from ..desafios import pastor as P
from ..palco.holo import AMARELO, CIANO

BRANCO = (0.92, 0.96, 1.0)
VERDE = (0.3, 1.0, 0.62)
LARANJA = (1.0, 0.55, 0.15)

DESTAQUES = {"campeão": AMARELO, "cão": LARANJA, "ovelhas": BRANCO, "curral": VERDE, "rebanho": BRANCO, "atrás": LARANJA}


def suave(x, k=5):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def eventos(hist):
    G = len(hist["m_pen"])
    pen, atr, dist, esp = (suave(hist["m_" + k]) for k in ("pen", "atras", "dist", "esp"))
    ev = {"G": G, "pen": pen, "atras": atr, "dist": dist, "esp": esp, "achar": None, "tras": None, "junto": None, "calma": None}
    d0, a0 = dist[:3].mean(), atr[:3].mean()
    ev["achar"] = next((g for g in range(3, G) if dist[g] <= 0.6 * d0), None)
    if ev["achar"] is None:
        return ev
    ev["tras"] = next((g for g in range(ev["achar"] + 2, G) if atr[g] >= a0 + 0.2 and atr[g] >= 0.75), None)
    if ev["tras"] is None:
        return ev
    pico = int(np.argmax(esp[:G * 2 // 3]))
    if pico <= ev["tras"]:
        return ev
    ev["junto"] = next((g for g in range(pico, G) if esp[g] <= 0.55 * esp[pico]), None)
    if ev["junto"] is not None:
        ev["calma"] = (ev["tras"] + ev["junto"]) // 2
    return ev


def nota_historia(hist):
    ev = eventos(hist)
    if None in (ev["achar"], ev["tras"], ev["junto"]):
        return 0.0
    pen = ev["pen"]
    return float(min(pen[-10:].mean(), 0.9) * 6 + (1.0 - hist["m_zero"][-10:].mean()) + min(abs(pen[ev["junto"]] - pen[ev["calma"]]), 0.2) * 5)


def duelo(hist, g, rodadas=300, semente=77):
    """O campeão da geração g em cidades novas: ovelhas no curral em cada 100 (média)."""
    genes = hist["genes"][g]
    j, _ = cidades(genes, np.full(rodadas, campeao(hist, g)), semente + g)
    return float(j.dentro().sum(1).mean() / P.N)


def pct(x):
    return f"{100 * x:.0f}"


def monta(hist, A):
    ev = eventos(hist)
    G = ev["G"]
    if None in (ev["achar"], ev["tras"], ev["junto"]):
        raise RuntimeError("Esta semente não tem a história completa (achar, ficar atrás, juntar): troque a semente.")
    g1, g2, g3, gc = ev["achar"], ev["tras"], ev["junto"], ev["calma"]
    n = P.N
    zero = int(round(100 * float(hist["m_zero"][:3].mean())))
    d0, d1 = float(hist["m_dist"][:3].mean()), float(ev["dist"][g1])
    a0, a1 = int(round(100 * float(hist["m_atras"][:3].mean()))), int(round(100 * float(ev["atras"][g2])))
    e0, e1 = float(ev["esp"][g2]), float(ev["esp"][g3])
    p0, p2, pc, p3 = (int(round(100 * float(ev["pen"][g]))) for g in (0, g2, gc, g3))
    s_um, s_fin = duelo(hist, 0), duelo(hist, G - 1)
    C = G
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ------------------------------------------------------------ GANCHO
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("1 CÃO IA x 15 OVELHAS", BRANCO), (f"NENHUMA ENTROU EM {zero} DE 100", AMARELO)],
         log=[(f"1 CÃO · {n} OVELHAS", LARANJA), ("NINGUÉM SABE PASTOREAR", AMARELO)],
         carimbo={"texto": f"{zero} DE 100", "cor": AMARELO, "em": 0.5, "sub": "CIDADES SEM NENHUMA OVELHA NO CURRAL · GERAÇÃO 1"},
         fala=f"Soltei um cão IA numa fazenda. <short pause> Em {zero} de 100 tentativas, nenhuma ovelha entrou no curral.")
    # ------------------------------------------------------------ PREMISSA + REGRA + PROMESSA + GERAÇÃO 1 (o campeão passeia)
    cena(tipo="replay", ger=C, foco=0, grupo="g1b", log=[("CAMPEÃO DA GER 001 · PASSEANDO", LARANJA), ("QUEM LEVA MAIS AO CURRAL VIRA PAI DA TURMA", VERDE)],
         fala="É tipo treinar cachorro: quem leva ao curral vira pai. No fim, tem teste. E o campeão? <long pause>")
    # ------------------------------------------------------------ DESCOBERTA 1: por trás (achar o rebanho vai na fala)
    cena(tipo="replay", ger=C + g2, foco=0,
         cartao={"numero": 1, "rotulo": "CÃO", "nome": "POR TRÁS", "cor": AMARELO, "stat": f"ATRÁS DO REBANHO {a0}% → {a1}% DO TEMPO"},
         log=[(f"GER {g2 + 1:03d} · ATRÁS {a0}% → {a1}%", AMARELO), (f"DISTÂNCIA DO REBANHO {d0:.0f} → {d1:.0f} m", LARANJA)],
         fala="Só passeava. Até achar as ovelhas. <short pause> Elas fugiam; ele foi para trás. <long pause> Ninguém ensinou isso.")
    marcos.append((g2, "1", AMARELO))
    # ------------------------------------------------------------ RE-GANCHO + DESCOBERTA 2: juntar
    cena(tipo="replay", ger=C + g3, foco=0,
         cartao={"numero": 2, "rotulo": "CÃO", "nome": "REBANHO JUNTO", "cor": VERDE, "stat": f"NO CURRAL {pc}% → {p3}% DAS OVELHAS"},
         log=[(f"GER {g3 + 1:03d} · NO CURRAL {pc}% → {p3}%", VERDE), (f"REBANHO MAIS JUNTO: ESPALHAMENTO {e0:.1f} → {e1:.1f}", VERDE)],
         fala=f"Mas elas quase pararam de entrar. <short pause> Será que acabou? <long pause> Ele juntou o rebanho sozinho. {p3} em cada 100.")
    marcos.append((g3, "2", VERDE))
    # ------------------------------------------------------------ TESTE
    itens = [("CAMPEÃO 1", s_um, LARANJA), (f"CAMPEÃO {G}", s_fin, VERDE)]
    kw = dict(tipo="barras", grupo="teste", ger=G - 1, fundo_escuro=0.35, fundo_vivo=0.9, fundo_vel=2.0, itens=itens, titulo="CÃO x CURRAL",
              sub="fazendas novas · ovelhas que entram", destaque=1, cor_destaque="verde", rotulo_destaque="",
              log=[("TESTE: FAZENDAS NOVAS", AMARELO), (f"NO CURRAL {pct(s_um)}% → {pct(s_fin)}%", AMARELO)])
    cena(teste=True, **kw,
         fala=f"Faltava o teste: fazendas novas. <short pause> O campeão inicial levava {pct(s_um)} em 100. Chuta aí: e o final? <long pause>")
    cena(**dict(kw, sub="ovelhas que entram no curral"), fala=f"{pct(s_fin)} em 100 entraram. <short pause> Coitadas das ovelhas.")
    # ------------------------------------------------------------ CTA + LAÇO
    cena(tipo="replay", ger=C + G - 1, foco=0, grupo="fim", destaques={"campeão": AMARELO, "cão": LARANJA},
         fala="Ele cuida das ovelhas ou só manda nelas? <short pause> Porque tudo começou quando eu…")

    info = {"marca": "VÍDEO NEURAL", "serie": suave(hist["m_pen"], 5), "serie_rotulo": "% OVELHAS NO CURRAL",
            "marcos": marcos, "rotulo_vivo": f"{n} OVELHAS", "nome_teste": "TESTE FINAL",
            "rodape": f"1 CÃO · {n} OVELHAS E CURRAL PROGRAMADOS: SÓ O CÃO EVOLUI · {G} GERAÇÕES · NOTA = OVELHAS NO CURRAL + REBANHO MAIS PERTO DA ENTRADA"}
    post = (f"{zero} de 100 tentativas sem uma ovelha no curral. Aí o cão fez algo que ninguém ensinou 🐑\n"
            f"IA aprendendo sozinha por seleção natural. Simulação real de um cão pastor: {n} ovelhas por fazenda, {G} gerações, números medidos no treino.\n"
            "Marca quem acha que o cachorro só manda no rebanho 👇\n\n"
            "#inteligenciaartificial #ia #aprendizadodemaquina #simulacao #caopastor")
    ev["teste"] = {"um": s_um, "fin": s_fin, "dist": (d0, d1), "atras": (a0, a1), "esp": (e0, e1), "pen": (p0, p2, pc, p3), "zero": zero}
    return cenas, info, post, ev
