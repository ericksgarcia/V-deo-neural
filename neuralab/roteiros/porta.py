"""Roteiro do episódio Porta Giratória (guia v2): 16 IAs, uma porta que só gira se alguém empurrar.

Conta a história NA ORDEM em que aconteceu. Todo número falado sai do treino ou de um teste medido aqui.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.foguete import SUCESSO
from ..desafios.porta import Porta as Desafio
from ..rede import Arquitetura

BRANCO, MAGENTA = (0.92, 0.96, 1.0), (1.0, 0.3, 0.8)

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend watching an experiment unfold live. Natural spoken Brazilian rhythm; "
    "brisk and conversational, about three words per second, never rushed, never dragging. Open intrigued and "
    "deadpan, amused as the crowd jams the door; let each discovery land with quiet surprise, as if you did not "
    "expect it either; finish with a playful, provocative question and trail off on the last unfinished sentence.")

DESTAQUES = {"porta": MAGENTA, "giratória": MAGENTA, "campeão": AMARELO, "empurrar": CIANO, "empurra": CIANO,
             "mesmo": VERDE, "lado": VERDE, "travada": VERMELHO, "fila": CIANO, "passou": VERDE, "passam": VERDE}

NOMES = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
         "treze", "catorze", "quinze", "dezesseis"]


def pct(x):
    return f"{100 * x:.0f}%"


def em_dez(x):
    n = int(round(x * 10))
    return f"{NOMES[n]} em cada dez"


def milhar(x):
    return f"{int(x):,}".replace(",", ".")


def seg(x):
    return f"{x:.1f}".replace(".", ",")


def suave(x, k=9):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def eventos(hist):
    n = hist["genes"].shape[1]
    G = len(hist["sucessos"])
    s = suave(hist["sucessos"].astype(float))
    hor = suave(hist["m_horario"]) if "m_horario" in hist else np.zeros(G)
    tem = suave(hist["m_tempo"])
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev = {"G": G, "n": n, "s": s, "hor": hor, "tem": tem}
    ev["sobe"] = primeiro(lambda g: s[g] >= 0.25 * n)
    ev["meio"] = primeiro(lambda g: s[g] >= 0.6 * n)
    if ev["sobe"] is None or ev["meio"] is None:
        ev["mesmo"] = ev["rap"] = ev["plat"] = None
        return ev
    ev["mesmo"] = primeiro(lambda g: hor[g] >= 0.85, ev["sobe"])
    # o placar estaciona (85% das salas) e só depois as salas ficam mais rápidas
    ev["plat"] = primeiro(lambda g: s[g] >= 0.85 * n, ev["meio"])
    ev["rap"] = primeiro(lambda g: tem[g] <= tem[ev["plat"]] - 1.5, ev["plat"] + 12) if ev["plat"] is not None else None
    return ev


def nota_historia(hist):
    """Boa história: começa sem ninguém passando, sobe cedo, a porta passa a girar para um lado só, o placar
    estaciona e a porta ainda fica menos travada."""
    n = hist["genes"].shape[1]
    ev = eventos(hist)
    if ev["sobe"] is None or ev["meio"] is None or ev["mesmo"] is None or ev["rap"] is None:
        return -1.0
    G, s = ev["G"], ev["s"]
    p0 = float(hist["m_passaram"][0])
    comeca_baixo = 1.0 - min(p0 / 0.2, 1.0)
    cedo = max(1 - abs(ev["sobe"] / G - 0.2) * 3, 0)
    queda = float(ev["tem"][ev["plat"]] - ev["tem"][-1]) / 10
    return float(s.max() / n + 0.5 * comeca_baixo + 0.3 * cedo + 0.3 * queda + 0.3 * ev["hor"][-1])


def duelo(hist, g, n=600, semente=21):
    """O melhor cérebro da geração g, clonado em n salas NOVAS (posições e ângulo da porta diferentes):
    (fração de salas em que as 16 passam, tempo médio em s, média de IAs que passam por sala)."""
    arq = Arquitetura(Desafio.camadas)
    genes = hist["genes"][g]
    amb = Desafio(len(genes), np.random.default_rng(int(hist["semente"][g])))
    p = arq.desempacota(genes)
    for t in range(Desafio.passos):
        sa, _ = arq.avalia(p, amb.observa())
        amb.passo(sa, t)
        if (amb.estado != 0).all():
            break
    amb.finaliza(t)
    melhor = int(np.argmax(amb.aptidao()))
    clones = np.repeat(genes[melhor:melhor + 1], n, 0)
    a = Desafio(n, np.random.default_rng(semente), por_mundo=True)
    pc = arq.desempacota(clones)
    for t in range(Desafio.passos):
        sa, _ = arq.avalia(pc, a.observa())
        a.passo(sa, t)
        if (a.estado != 0).all():
            break
    a.finaliza(t)
    suc = a.estado == SUCESSO
    return float(suc.mean()), float(a.t_fim[suc].mean() * a.dt) if suc.any() else 0.0, float(a.passou.sum(1).mean())


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], ev["n"]
    if ev["sobe"] is None or ev["meio"] is None or ev["mesmo"] is None or ev["rap"] is None:
        raise RuntimeError("A história não tem todas as viradas: treine mais gerações ou troque a semente.")
    N = Desafio.n_ag
    suc = hist["sucessos"]
    p0 = float(hist["m_passaram"][0]) * N
    sobe, meio, mesmo, rap, plat = ev["sobe"], ev["meio"], ev["mesmo"], ev["rap"], ev["plat"]
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO
    menos = "menos de uma" if p0 < 1 else f"só {NOMES[int(round(p0))]}"
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("COLOQUEI 16 IAs", BRANCO), ("DIANTE DE UMA PORTA GIRATÓRIA", MAGENTA)],
         log=[(f"{n} SALAS AO MESMO TEMPO", BRANCO), (f"{N} IAs · 1 PORTA · 0 REGRAS", MAGENTA)],
         carimbo={"texto": f"{seg(p0)} DE {N}", "cor": VERMELHO, "em": 1.6, "sub": "PASSAM EM MÉDIA"},
         fala=(f"Coloquei {N} IAs diante de uma porta giratória. <short pause> Em {n} salas, nenhuma passou inteira."
               if int(suc[0]) == 0 else
               f"Coloquei {N} IAs diante de uma porta giratória. <short pause> Em cada sala, {menos} passou."))
    # ---------------------------------------------------------------- PREMISSA + REGRA
    cena(tipo="ao_vivo", ger=min(3, G - 1), grupo="g1b",
         log=[("MESMO CÉREBRO EM TODAS AS IAs", BRANCO), ("AS SALAS QUE PASSAM MAIS GENTE VIRAM PAIS", VERDE)],
         fala="Mesmo cérebro em todas. A porta só gira se empurrarem. <short pause> As melhores salas viram pais.")
    # ---------------------------------------------------------------- GERAÇÃO 1: o campeão falha
    r0 = A.rodada(0)
    k0 = r0.lider
    ficou = N - int((r0.reg["s"][k0, -1, :, 0] > 3.4).sum())
    cena(tipo="replay", ger=0, foco=k0, grupo="g1c",
         log=[(f"CAMPEÃO DA GER 001 · {ficou} FICARAM PARA TRÁS", VERMELHO)],
         fala=f"O campeão da geração um. <short pause> Deixou {NOMES[ficou]} para trás.")
    # ---------------------------------------------------------------- DESCOBERTA 1: EMPURRAR A PORTA
    pm_a, pm_b = p0, float(hist["m_passaram"][sobe]) * N
    rs = A.rodada(sobe)
    k1 = A.busca(rs, "primeiro")
    cena(tipo="replay", ger=sobe, foco=k1,
         cartao={"numero": 1, "rotulo": "DESCOBERTA", "nome": "EMPURRAR A PORTA", "cor": CIANO,
                 "stat": f"PASSAM POR SALA {seg(pm_a)} → {pm_b:.0f} DE {N}"},
         log=[(f"GER {sobe + 1:03d} · {pm_b:.0f} DE {N} PASSAM POR SALA", CIANO)],
         fala=f"Geração {sobe + 1}. O campeão aprende a empurrar. <long pause> "
              f"De {menos.replace('só ', '')} para {NOMES[int(round(pm_b))]} por sala.")
    marcos.append((sobe, "EMPURRA", CIANO))
    # ---------------------------------------------------------------- DESCOBERTA 2: O MESMO LADO
    h_a, h_b = float(hist["m_horario"][0]), float(hist["m_horario"][mesmo])
    rm = A.rodada(mesmo)
    k2 = A.busca(rm, "primeiro")
    cena(tipo="replay", ger=mesmo, foco=k2,
         cartao={"numero": 2, "rotulo": "DESCOBERTA", "nome": "O MESMO LADO", "cor": MAGENTA,
                 "stat": f"PORTA NO MESMO SENTIDO {pct(h_a)} → {pct(h_b)} DAS SALAS"},
         log=[(f"GER {mesmo + 1:03d} · SENTIDO ÚNICO {pct(h_a)} → {pct(h_b)}", MAGENTA)],
         fala=f"Geração {mesmo + 1}. A porta gira sempre para o mesmo lado. <long pause> "
              f"De {em_dez(h_a)} salas para {em_dez(h_b)}.")
    marcos.append((mesmo, "MESMO LADO", MAGENTA))
    # ---------------------------------------------------------------- RE-GANCHO: o placar trava
    s_m, s_r = float(ev["s"][plat]), float(ev["s"][rap])
    if abs(s_r - s_m) > 0.1 * n:
        raise RuntimeError("O placar não trava entre as descobertas 2 e 3: escolha outra semente.")
    g_calma = int(np.clip((plat + rap) // 2, plat, G - 1))
    cena(tipo="ao_vivo", ger=g_calma,
         log=[(f"GER {plat + 1}→{rap + 1} · MÉDIA {int(round(s_m))}→{int(round(s_r))}/{n}", AMARELO), ("O PLACAR TRAVA", AMARELO)],
         carimbo={"texto": "O PLACAR TRAVA", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {g_calma + 1}"},
         fala=f"Aí o placar trava. <short pause> Será que acabou? <long pause>")
    # ---------------------------------------------------------------- DESCOBERTA 3: MENOS PORTA TRAVADA
    t_a, t_b = float(ev["tem"][plat]), float(ev["tem"][rap])
    rr = A.rodada(rap)
    k3 = A.busca(rr, "primeiro")
    cena(tipo="replay", ger=rap, foco=k3,
         cartao={"numero": 3, "rotulo": "DESCOBERTA", "nome": "SEM TEMPO PERDIDO", "cor": AMARELO,
                 "stat": f"TEMPO PARA TODAS PASSAREM {t_a:.0f} s → {t_b:.0f} s"},
         log=[(f"GER {rap + 1:03d} · TEMPO {t_a:.0f} s → {t_b:.0f} s", AMARELO)],
         fala=f"Geração {rap + 1}. Não acabou: o campeão perde menos tempo. <long pause> "
              f"De {NOMES[int(round(t_a))]} para {NOMES[int(round(t_b))]} segundos.")
    marcos.append((rap, "MAIS RÁPIDO", AMARELO))
    # ---------------------------------------------------------------- O TESTE: salas novas
    g_ref = plat
    s_a, ta, _ = duelo(hist, g_ref)
    s_f, tf, _ = duelo(hist, G - 1)
    itens = [(f"GER {g_ref + 1}", s_a, CIANO), (f"GER {G}", s_f, AMARELO)]
    cena(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="E EM SALAS NOVAS?",
         sub="600 salas novas · melhor de cada geração", destaque=1, cor_destaque="amarelo", revela=4.0,
         rotulo_destaque=f"▼ {(s_a - s_f) * 100:.0f} pts" if s_a - s_f >= 0.1 else "◀ MELHOR",
         log=[("TESTE: 600 SALAS NOVAS", AMARELO), (f"TODAS PASSAM {pct(s_a)} → {pct(s_f)}", AMARELO),
              (f"TEMPO {seg(ta)} s → {seg(tf)} s", CIANO)],
         fala=f"Teste: salas novas. <short pause> O campeão da {g_ref + 1} acerta {pct(s_a)}. "
              f"O da {G}, só {pct(s_f)}, mas chega mais rápido.")
    # ---------------------------------------------------------------- CTA + LAÇO
    rf = A.rodada(G - 1)
    kf = A.busca(rf, "primeiro")
    nf = round((1 - s_f) * 10)
    falha = f"{'quase ' if (1 - s_f) * 10 < nf - 0.15 else ''}{NOMES[nf]} de cada dez salas"
    cena(tipo="replay", ger=G - 1, foco=kf, grupo="fim",
         escolha={"pergunta": "EVOLUIU OU PIOROU?", "opcoes": [("EVOLUIU", VERDE), ("PIOROU", VERMELHO)], "em": 0.2},
         destaques={"evoluiu": VERDE, "piorou": VERMELHO},
         fala=f"O campeão da {G} falha em {falha}. Evoluiu ou piorou? <short pause> Porque tudo começou quando eu…")

    serie = suc / n
    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% SALAS COM TODAS AS IAs PASSANDO",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} SALAS",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"Coloquei {N} IAs numa porta giratória e nenhuma sala passou inteira. O que mudou? 🚪\n"
            f"IA aprendendo sozinha por seleção natural (algoritmo genético). Simulação real: {n} salas de {N} IAs, "
            f"{G} gerações, nenhum número inventado.\n"
            "Manda pra quem empurra a porta do lado errado e atrasa a fila 👇\n\n"
            "#inteligenciaartificial #ia #algoritmogenetico #curiosidades #tecnologia")
    ev["duelo"] = {"ref": (g_ref, s_a, ta), "fin": (G - 1, s_f, tf)}
    return cenas, info, post, ev
