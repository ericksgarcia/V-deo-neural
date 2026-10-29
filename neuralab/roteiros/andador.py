"""Roteiro do episódio Robô Andador: uma IA aprende a andar do zero.

Todo número falado sai do treino. O teste do gelo (trocar o atrito do chão) é uma simulação extra,
medida aqui mesmo, e só entra no vídeo se o resultado for notável.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.andador import META, MU, Andador as DesafioAndador
from ..desafios.foguete import FALHA, SUCESSO
from ..rede import Arquitetura
from .baliza import milhar, nota_historia, pct, suave  # noqa: F401

BRANCO = (0.92, 0.96, 1.0)
MU_GELO = 0.3

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend who just discovered something amazing. Natural spoken Brazilian rhythm; "
    "pace brisk and conversational, about three words per second, never rushed, never dragging. Emotional arc: "
    "open intrigued and confident, then conspiratorial, as if sharing a secret; explain the rules calmly and "
    "clearly with a hint of dry humor and say 'Eliminados' coldly; ask the viewer questions as if you really "
    "want their guess and leave a beat before the answer; build tension before the first success and let "
    "'Chegou' land triumphant and relieved; slow down and sound proud on the big numbers; deliver the drop "
    "on the ice with honest surprise; finish playful and provocative, inviting the viewer to pick a side.")
DESTAQUES = {"robô": AMARELO, "robôs": AMARELO, "andar": VERDE, "anda": VERDE, "chegou": VERDE, "linha": VERDE,
             "caiu": VERMELHO, "caem": VERMELHO, "caíram": VERMELHO, "quedas": VERMELHO, "cai": VERMELHO,
             "eliminados": VERMELHO, "gelo": CIANO, "pernas": AMARELO, "sozinhos": VERDE, "nunca": VERMELHO}


def corr_pernas(rod, k):
    """Correlação dos quadris do robô k na rodada (−1 pernas alternadas, +1 pernas juntas)."""
    m = rod.morte[k]
    s = rod.reg["s"][k, : (m + 1 if m >= 0 else rod.T), 3:5]
    if len(s) < 10 or s[:, 0].std() < 0.02 or s[:, 1].std() < 0.02:
        return 0.0
    return float(np.corrcoef(s[:, 0], s[:, 1])[0, 1])


def eventos(hist):
    s = suave(hist["sucessos"].astype(float))
    alt = suave(hist["m_alt"])
    G = len(s)
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev = {"G": G, "s": s, "alt": alt}
    ev["gs"] = int(np.argmax(hist["sucessos"] > 0)) if (hist["sucessos"] > 0).any() else None
    ev["g_alt"] = primeiro(lambda g: alt[g] >= 0.3)
    ev["gf"] = int(min(max(int(np.argmax(s)), 1), G - 1))
    return ev


def teste_gelo(hist, g, n=400, semente=11):
    """O melhor robô da geração g, em n partidas no chão normal e no gelo (atrito baixo)."""
    D = DesafioAndador
    arq = Arquitetura(D.camadas)
    genes = hist["genes"][g]
    amb = D(len(genes), np.random.default_rng(int(hist["semente"][g])))
    pb = arq.desempacota(genes)
    for t in range(D.passos):
        saida, _ = arq.avalia(pb, amb.observa())
        amb.passo(saida, t)
        if (amb.estado != 0).all():
            break
    amb.finaliza(t)
    melhor = int(np.argmax(amb.aptidao()))
    clones = np.repeat(genes[melhor:melhor + 1], n, 0)

    def taxa(mu):
        a = D(n, np.random.default_rng(semente), mu=mu)
        p = arq.desempacota(clones)
        for t in range(D.passos):
            sa, _ = arq.avalia(p, a.observa())
            a.passo(sa, t)
            if (a.estado != 0).all():
                break
        return float((a.estado == SUCESSO).mean())
    return taxa(MU), taxa(MU_GELO)


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], hist["genes"].shape[1]
    gs = ev["gs"]
    if gs is None:
        raise RuntimeError("Nenhum robô chegou: treine mais gerações ou troque a semente.")
    suc = hist["sucessos"]
    quedas = np.round(hist["m_cai"] * n)               # robôs que caíram de verdade em cada geração
    quedas_ate = int(quedas.sum())
    q_gs = int(quedas[:gs + 1].sum())
    melhor_g = int(np.argmax(suave(suc.astype(float))))
    fin_s = int(suc[melhor_g])
    base, gelo = teste_gelo(hist, melhor_g)
    tem_virada = base - gelo >= 0.15
    cenas, marcos = [], []
    D = DESTAQUES

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO
    rod_h = A.rodada(melhor_g)
    heroi = A.busca(rod_h, "primeiro")
    m_h = float(rod_h.morte[heroi]) * rod_h.dt
    marcas = [{"tipo": "circulo", "em": max(m_h - 0.6, 0), "alvo": "alvo", "texto": "CHEGOU!", "rx": 90, "ry": 110,
               "desloca": (0, -110)}]
    cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas,
         fala="Esse robô nunca andou. <short pause> Olha ele agora.")

    # ---------------------------------------------------------------- PREMISSA + GERAÇÃO 1
    c0 = int(quedas[0])
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"{n} ROBÔS", BRANCO), ("CADA UM COM UMA IA QUE NÃO SABE NADA", BRANCO)],
         fala=f"{n} robôs. Cérebro vazio. <short pause> Meta: {META:.0f} metros sem cair.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · CAÍRAM {c0}/{n}", VERMELHO)],
         carimbo={"texto": f"CAÍRAM {c0} DE {n}", "cor": VERMELHO, "em": 0.5, "sub": "GERAÇÃO 1"},
         fala=("Quantos caíram na primeira vez? <long pause> Todos." if c0 == n else
               f"Quantos caíram na primeira vez? <long pause> {c0} de {n}."))
    # ---------------------------------------------------------------- A REGRA
    g_sel = min(4, G - 1)
    cena(tipo="ao_vivo", ger=g_sel, log=[("OS QUE VÃO MAIS LONGE SÃO COPIADOS", VERDE), ("OS QUE CAEM CEDO SAEM", VERMELHO),
                                         ("CADA RODADA = 1 GERAÇÃO", BRANCO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": VERDE, "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="Regra cruel: quem vai mais longe é copiado. <short pause> Quem cai cedo, sai.")

    # ---------------------------------------------------------------- O PRIMEIRO A CHEGAR
    r_s = A.rodada(gs)
    k_s = A.busca(r_s, "primeiro")
    m_s = float(r_s.morte[k_s]) * r_s.dt
    c_s = corr_pernas(r_s, k_s)
    jeito = ("alternando as pernas" if c_s < -0.3 else "com as pernas quase juntas" if c_s > 0.5
             else "ainda sem alternar as pernas")
    marcas_s = [{"tipo": "circulo", "em": max(m_s - 0.8, 0), "alvo": "alvo", "texto": "CHEGOU!", "rx": 90, "ry": 110,
                 "desloca": (0, -110)}]
    cena(tipo="replay", ger=gs, foco=k_s, marcas=marcas_s,
         cartao={"numero": 1, "rotulo": "PRIMEIRO A CHEGAR", "nome": f"GERAÇÃO {gs + 1}", "cor": VERDE,
                 "stat": f"DEPOIS DE {milhar(q_gs)} QUEDAS"},
         log=[(f"GER {gs + 1:03d} · PRIMEIRO A CHEGAR", VERDE)],
         fala=f"Geração {gs + 1}. Depois de {milhar(q_gs)} quedas… <long pause> um robô cruza a linha. "
              f"<short pause> Mas {jeito}.")
    marcos.append((gs, "1º", VERDE))

    # ---------------------------------------------------------------- O PASSO (as pernas passam a alternar)
    g_alt = ev["g_alt"]
    if g_alt is not None and g_alt > gs + 2:
        r_a = A.rodada(g_alt)
        suc_a = np.where(r_a.reg["estado"][:, -1] == SUCESSO)[0]
        if len(suc_a):
            k_a = int(suc_a[np.argmin([corr_pernas(r_a, k) for k in suc_a])])
            pa = float(hist["m_alt"][g_alt])
            cena(tipo="replay", ger=g_alt, foco=k_a,
                 cartao={"numero": 2, "rotulo": "ROBÔ", "nome": "O PASSO", "cor": AMARELO,
                         "stat": f"{pct(pa)} ALTERNAM AS PERNAS"},
                 log=[(f"GER {g_alt + 1:03d} · {pct(pa)} ALTERNAM AS PERNAS", AMARELO)],
                 fala=f"Geração {g_alt + 1}. <short pause> {pct(pa)} já alternam as pernas.")
            marcos.append((g_alt, "PASSO", AMARELO))

    # ---------------------------------------------------------------- O NÚMERO FINAL + O GRÁFICO
    serie = suc / n
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% QUE CHEGA",
         eras=[(gs, G - 1, "APRENDENDO", VERDE)], rotulo_y="ROBÔS QUE CHEGAM POR GERAÇÃO",
         final=pct(float(serie[melhor_g])), log=[(f"GER {melhor_g + 1:03d} · {fin_s}/{n} CHEGAM", VERDE), (f"{milhar(quedas_ate)} QUEDAS NO TOTAL", VERMELHO)],
         fala=f"Geração {melhor_g + 1}: {fin_s} de {n} chegam sozinhos. <short pause> "
              f"Foram {milhar(quedas_ate)} quedas.")

    # ---------------------------------------------------------------- A VIRADA: o gelo
    if tem_virada:
        itens = [("CHÃO NORMAL", base, VERDE), ("GELO", gelo, VERMELHO)]
        sub = "o melhor robô · 400 tentativas · % que chega"
        cena(tipo="barras", grupo="gelo", ger=melhor_g, itens=itens, titulo="E SE O CHÃO FOR GELO?", sub=sub,
             log=[("TESTE: ATRITO DO CHÃO BAIXO", AMARELO)], pausa=0.25,
             fala="Mas ele aprendeu de verdade? <short pause> Troquei o chão por gelo.")
        cena(tipo="barras", grupo="gelo", ger=melhor_g, itens=itens, titulo="E SE O CHÃO FOR GELO?", sub=sub,
             destaque=1, cor_destaque="vermelho", revela=0.0, rotulo_destaque=f"▼ -{(base - gelo) * 100:.0f} pts",
             log=[(f"CHEGA {pct(base)} → {pct(gelo)}", VERMELHO)],
             fala=f"Melhor robô, chão normal: {pct(base)} chegam. <long pause> No gelo? "
                  f"{'Nenhuma.' if gelo == 0 else 'Só ' + pct(gelo) + '.'}")

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="fim", inicio=max(m_h - 1.4, 0),
         escolha={"pergunta": "O QUE DERRUBA ELE?", "opcoes": [("ESCADA", AMARELO), ("LADEIRA", CIANO)], "em": 0.2},
         destaques={"escada": AMARELO, "ladeira": CIANO, "votado": VERDE},
         fala="Ele nunca andou… e só sabe andar no chão que conhece. <short pause> "
              "Escada ou ladeira? Comenta. O mais votado vira o próximo episódio. Segue.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% QUE CHEGA POR GERAÇÃO",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} ROBÔS",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, A.Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    virada = " Aí troquei o chão por gelo e ele despencou. 🧊" if tem_virada else ""
    post = (f"Esse robô nunca andou na vida. Os robôs caíram {milhar(quedas_ate)} vezes e aprenderam sozinhos. 🤖{virada}\n"
            f"Simulação real: {n} robôs, {G} gerações, zero programação. Episódio 3 da série em que a IA aprende sozinha.\n"
            f"Escada ou ladeira, qual derruba ele primeiro? Comenta ESCADA ou LADEIRA. O mais votado vira o próximo vídeo 👇\n\n"
            f"#inteligenciaartificial #ia #robo #aprendizadodemaquina #curiosidades #tecnologia #simulacao #aprendeusozinho")
    return cenas, info, post, ev
