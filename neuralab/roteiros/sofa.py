"""Roteiro do episódio Mudança de Sofá: duas IAs presas pelas pontas de um sofá aprendem a passar pela quina.

Conta a história NA ORDEM em que aconteceu (geração 1 caótica, uma descoberta de cada vez); o resultado final
só aparece perto do fim. Todo número falado sai do treino ou de um teste medido aqui.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.foguete import SUCESSO
from ..desafios.sofa import Sofa as Desafio, progresso, X_QUINA, X_INI
from ..rede import Arquitetura
from .cruzamento import BRANCO, MAGENTA, NOMES, milhar, pct, seg, suave

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend watching a funny experiment unfold live. Natural spoken Brazilian rhythm; "
    "pace brisk and conversational, about three words per second, never rushed, never dragging. Emotional arc: "
    "open amused and intrigued with a teasing question, then deadpan as the sofas scrape the walls, say "
    "'Eliminados' coldly; build curiosity before each discovery and let each one land with quiet awe, as if you "
    "did not expect it either; sound a little suspicious at the false calm; finish playful and provocative, "
    "inviting the viewer to pick a side.")

DESTAQUES = {"sofá": AMARELO, "sofás": AMARELO, "quina": AMARELO, "parede": VERMELHO, "brigar": VERMELHO,
             "brigam": VERMELHO, "brigavam": VERMELHO, "empurram": CIANO, "curva": MAGENTA, "inventou": VERDE,
             "ninguém": VERDE, "sozinhas": VERDE, "passa": VERDE, "passam": VERDE, "mais": BRANCO}


def eventos(hist):
    n = hist["genes"].shape[1]
    G = len(hist["sucessos"])
    s = suave(hist["sucessos"].astype(float))
    contra, quina = suave(hist["m_contra"]), suave(hist["m_quina"])
    bat, tem = suave(hist["m_bateu"]), suave(np.where(hist["m_tempo"] > 0, hist["m_tempo"], np.nan_to_num(hist["m_tempo"])))
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev = {"G": G, "n": n, "s": s, "contra": contra, "quina": quina, "bat": bat}
    ev["brig"] = primeiro(lambda g: contra[g] <= 0.12)
    ev["quina_g"] = primeiro(lambda g: quina[g] >= 0.6)
    ev["curva"] = primeiro(lambda g: s[g] >= 0.25 * n)
    ev["meio"] = primeiro(lambda g: s[g] >= 0.6 * n)
    if ev["meio"] is None:
        return ev
    m = ev["meio"]
    ev["rapida"] = primeiro(lambda g: bat[g] <= bat[m] - 1.5 and hist["m_tempo"][max(0, g - 4):g + 1].mean()
                            <= hist["m_tempo"][max(0, m - 4):m + 1].mean() - 0.8, m + 8)
    return ev


def _ordem(ev):
    ks = ("brig", "quina_g", "curva", "meio", "rapida")
    if any(ev.get(k) is None for k in ks):
        return False
    v = [ev[k] for k in ks]
    return all(a <= b for a, b in zip(v, v[1:])) and v[2] > v[0]


def nota_historia(hist):
    """Boa história: 4 viradas em ordem (parar de brigar, chegar à quina, fazer a curva, encostar menos), com o
    placar travado entre a curva e a última."""
    n = hist["genes"].shape[1]
    if hist["sucessos"].max() == 0:
        return -1.0
    ev = eventos(hist)
    if not _ordem(ev):
        return -0.5
    G, s = ev["G"], ev["s"]
    trava = ev["rapida"] - ev["meio"] >= 20 and s[ev["rapida"]] - s[ev["meio"]] <= 0.2 * n
    if not trava:
        return -0.25
    queda = float(ev["bat"][ev["meio"]] - ev["bat"][-1])
    cedo = max(1 - ev["rapida"] / G * 1.5, 0)
    return float(s.max() / n + 0.15 * queda + 0.5 * cedo + 0.3 * (1 - ev["brig"] / G))


def _clones(hist, g, ruido, n=600, semente=33):
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
    return arq, np.repeat(genes[melhor:melhor + 1], n, 0), semente


def duelo(hist, g, ruido=1.2, n=600):
    """Melhor sofá da geração g clonado em n largadas NOVAS: (fração que passa, tempo médio, s encostado)."""
    arq, clones, semente = _clones(hist, g, ruido, n)
    a = Desafio(n, np.random.default_rng(semente), ruido=ruido)
    pc = arq.desempacota(clones)
    for t in range(Desafio.passos):
        sa, _ = arq.avalia(pc, a.observa())
        a.passo(sa, t)
        if (a.estado != 0).all():
            break
    a.finaliza(t)
    suc = a.estado == SUCESSO
    return float(suc.mean()), float(a.t_fim[suc].mean() * a.dt) if suc.any() else 0.0, float(a.batidas.mean() * a.dt)


def _instante(rod, k, cond):
    """Primeiro instante (s) em que cond(x, y, th) vale para o sofá k."""
    s = rod.reg["s"][k]
    ok = cond(s[:, 0], s[:, 1], s[:, 2])
    return float(np.argmax(ok)) * rod.dt if ok.any() else 1.0


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], ev["n"]
    if not _ordem(ev):
        raise RuntimeError("A história não tem as 4 viradas em ordem: treine mais gerações ou troque a semente.")
    suc = hist["sucessos"]
    brig, quina_g, curva, meio, rap = ev["brig"], ev["quina_g"], ev["curva"], ev["meio"], ev["rapida"]
    b0 = float(hist["m_bateu"][0]) / (Desafio.passos * Desafio.dt)            # fração do tempo encostado na parede
    c0, cb = float(hist["m_contra"][0]), float(hist["m_contra"][brig])
    q0, qg = float(hist["m_quina"][0]), float(hist["m_quina"][quina_g])
    bateram_tot = int(round((hist["m_bateu"] * n).sum() / 1.0))
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO (nada de resultado)
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("PRENDI DUAS IAs", BRANCO), ("NAS PONTAS DE UM SOFÁ", AMARELO)],
         log=[(f"{n} SOFÁS AO MESMO TEMPO", BRANCO), ("2 IAs POR SOFÁ · 1 QUINA", AMARELO)],
         fala="Prendi duas IAs nas pontas de um sofá. <short pause> Elas precisam virar a quina. De 150 sofás, quantos passam?")
    cena(tipo="ao_vivo", ger=0, grupo="g1",
         log=[("CADA PONTA EMPURRA OU PUXA", CIANO), ("NINGUÉM COMBINA NADA", BRANCO)],
         fala="Cada ponta só sabe empurrar ou puxar. <short pause> Nenhuma sabe o que a outra quer.")
    cena(tipo="ao_vivo", ger=0, grupo="g1b",
         log=[(f"GER 001 · 0 DE {n} PASSAM", VERMELHO)],
         carimbo={"texto": f"0 DE {n}", "cor": VERMELHO, "em": 0.5, "sub": "PASSAM PELA QUINA"},
         fala=f"Geração um. De {n} sofás, nenhum passa. <short pause> "
              f"Eles passam {pct(b0)} do tempo raspando na parede.")
    r0 = A.rodada(0)
    quase = [k for k in np.argsort(-r0.apt)[:60]]
    if len(quase) >= 3:
        pick = [int(quase[i]) for i in (0, 20, 40)]
        cena(tipo="montagem", clipes=[(0, k) for k in pick], log=[("PRESO. PRESO. PRESO.", VERMELHO)],
             fala="Preso. <short pause> Preso. <short pause> Preso.")

    # ---------------------------------------------------------------- A REGRA
    g_sel = min(5, G - 1)
    cena(tipo="ao_vivo", ger=g_sel, log=[("OS MELHORES SÃO COPIADOS", VERDE), ("OS PIORES SAEM", VERMELHO),
                                         ("CADA RODADA = 1 GERAÇÃO", BRANCO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": VERDE, "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="A regra é cruel. Os sofás que vão mais longe são copiados, com pequenas mudanças. Os piores? <short pause> Eliminados.")

    # ---------------------------------------------------------------- DESCOBERTA 1: PARAR DE BRIGAR
    rb = A.rodada(brig)
    kb = rb.lider
    cena(tipo="replay", ger=brig, foco=kb,
         marcas=[{"tipo": "circulo", "em": 0.6, "alvo": "pontas", "texto": "MESMO LADO!", "rx": 120, "ry": 60,
                  "desloca": (0, -110)}],
         cartao={"numero": 1, "rotulo": "DESCOBERTA", "nome": "PARAR DE BRIGAR", "cor": VERMELHO,
                 "stat": f"PONTAS EM BRIGA {pct(c0)} → {pct(cb)}"},
         log=[(f"GER {brig + 1:03d} · BRIGA {pct(c0)} → {pct(cb)}", VERMELHO)],
         fala=f"Geração {brig + 1}. As duas pontas brigavam. Uma puxava pra cá, a outra pra lá. <short pause> "
              f"Antes, brigavam {pct(c0)} do tempo. Agora, {pct(cb)}.")
    marcos.append((brig, "SEM BRIGA", VERMELHO))

    # ---------------------------------------------------------------- DESCOBERTA 2: A QUINA
    rq = A.rodada(quina_g)
    kq = rq.lider
    em_q = _instante(rq, kq, lambda x, y, th: progresso(x, y) >= (X_QUINA - X_INI) - 0.5)
    cena(tipo="replay", ger=quina_g, foco=kq,
         marcas=[{"tipo": "circulo", "em": em_q, "alvo": "quina", "texto": "CHEGOU!", "rx": 100, "ry": 55,
                  "desloca": (0, -100)}],
         cartao={"numero": 2, "rotulo": "DESCOBERTA", "nome": "ATÉ A QUINA", "cor": AMARELO,
                 "stat": f"CHEGAM À QUINA {pct(q0)} → {pct(qg)}"},
         log=[(f"GER {quina_g + 1:03d} · NA QUINA {pct(q0)} → {pct(qg)}", AMARELO)],
         fala=f"Geração {quina_g + 1}. Agora eles andam reto. <short pause> "
              f"E chegam na quina: de {pct(q0)} para {pct(qg)}. Mas chegar não é passar.")
    marcos.append((quina_g, "QUINA", AMARELO))

    # ---------------------------------------------------------------- DESCOBERTA 3: A CURVA
    rc = A.rodada(curva)
    kc = A.busca(rc, "primeiro")
    kc = kc if kc is not None else rc.lider
    em_c = _instante(rc, kc, lambda x, y, th: np.abs(np.sin(th)) > 0.5)
    cena(tipo="replay", ger=curva, foco=kc,
         marcas=[{"tipo": "circulo", "em": em_c, "alvo": "pontas", "texto": "GIROU!", "rx": 110, "ry": 60,
                  "desloca": (0, -110)}],
         cartao={"numero": 3, "rotulo": "DESCOBERTA", "nome": "A CURVA", "cor": MAGENTA,
                 "stat": f"PASSAM PELA QUINA 0 → {int(suc[curva])} DE {n}"},
         log=[(f"GER {curva + 1:03d} · {int(suc[curva])}/{n} PASSAM", MAGENTA)],
         fala=f"Geração {curva + 1}. De repente, o sofá gira na quina. <short pause> "
              f"E passa. {int(suc[curva])} de {n}.")
    marcos.append((curva, "CURVA", MAGENTA))

    # ---------------------------------------------------------------- CALMARIA ENGANOSA
    if not (suc[rap] - suc[meio] <= 0.2 * n and rap - meio >= 20):
        raise RuntimeError("O placar não trava antes da última virada: escolha outra semente.")
    g_calma = int(np.clip((meio + rap) // 2, meio + 1, G - 1))
    s_m, s_r = int(round(ev["s"][meio])), int(round(ev["s"][rap]))
    cena(tipo="ao_vivo", ger=g_calma, log=[(f"GER {meio + 1}→{rap + 1} · MÉDIA {s_m}→{s_r}/{n}", AMARELO),
                                          ("O PLACAR TRAVA", AMARELO)],
         carimbo={"texto": "O PLACAR TRAVA", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {g_calma + 1}"},
         fala=f"Aí o placar trava. <short pause> Da geração {meio + 1} à {rap + 1}, o número quase não sobe. A IA chegou no limite?")

    # ---------------------------------------------------------------- DESCOBERTA 4: ENCOSTAR MENOS
    rr = A.rodada(rap)
    kr = A.busca(rr, "primeiro")
    kr = kr if kr is not None else rr.lider
    b_m, b_r = float(hist["m_bateu"][meio]), float(hist["m_bateu"][rap])
    t_m, t_r = float(hist["m_tempo"][meio]), float(hist["m_tempo"][rap])
    cena(tipo="replay", ger=rap, foco=kr,
         cartao={"numero": 4, "rotulo": "DESCOBERTA", "nome": "SEM RASPAR", "cor": VERDE,
                 "stat": f"NA PAREDE {seg(b_m)} s → {seg(b_r)} s"},
         log=[(f"GER {rap + 1:03d} · PAREDE {seg(b_m)} s → {seg(b_r)} s", VERDE), (f"TEMPO {seg(t_m)} s → {seg(t_r)} s", VERDE)],
         fala=f"Geração {rap + 1}. Uma mudança pequena. <short pause> "
              f"Menos tempo raspando na parede: de {seg(b_m)} para {seg(b_r)} segundos.")
    marcos.append((rap, "SEM RASPAR", VERDE))

    # ---------------------------------------------------------------- GRÁFICO
    serie = suc / n
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% QUE PASSA",
         eras=[(brig, quina_g, "PARAM DE BRIGAR", VERMELHO), (quina_g, meio, "A CURVA", MAGENTA),
               (meio, rap, "TRAVA", AMARELO), (rap, G - 1, "SEM RASPAR", VERDE)],
         rotulo_y="SOFÁS QUE PASSAM POR GERAÇÃO", final=pct(float(serie[-1])),
         log=[(f"{milhar(bateram_tot)} SEGUNDOS RASPANDO NA PAREDE", VERMELHO)],
         fala=f"{G} gerações. Nenhuma aula. Só tentativa, erro… e muita parede.")

    # ---------------------------------------------------------------- O TESTE
    s_a, t_a, w_a = duelo(hist, meio)
    s_f, t_f, w_f = duelo(hist, G - 1)
    ganhou = s_f - s_a >= 0.05
    itens = [(f"GER {meio + 1}", s_a, CIANO), (f"GER {G}", s_f, VERDE)]
    cena(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="E EM LARGADA NOVA?",
         sub="600 largadas novas · melhor sofá de cada geração", destaque=1, cor_destaque="verde", revela=4.0,
         rotulo_destaque=f"▲ +{(s_f - s_a) * 100:.0f} pts" if ganhou else "◀ MELHOR",
         log=[("TESTE: 600 LARGADAS NOVAS", AMARELO), (f"PASSAM {pct(s_a)} → {pct(s_f)}", VERDE),
              (f"TEMPO {seg(t_a)} s → {seg(t_f)} s", AMARELO)],
         fala=f"Teste final: seiscentos começos novos, que eles nunca viram. O melhor sofá da geração {meio + 1} e o da {G}. <short pause> "
              f"O da {meio + 1} passa em {pct(s_a)}. O da {G}, em {pct(s_f)}"
              + (f", {seg(t_a - t_f)} segundo mais rápido. " if t_a - t_f >= 0.3 else ". ")
              + f"Ainda falha em {pct(1 - s_f)}.")

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    rf = A.rodada(G - 1)
    kf = A.busca(rf, "primeiro")
    kf = kf if kf is not None else rf.lider
    cena(tipo="replay", ger=G - 1, foco=kf, grupo="fim",
         escolha={"pergunta": "O QUE APERTA MAIS?", "opcoes": [("SOFÁ MAIOR", AMARELO), ("CORREDOR MAIS ESTREITO", CIANO)],
                  "em": 0.2},
         destaques={"sofá": AMARELO, "corredor": CIANO, "votado": VERDE},
         fala="Time sofá maior ou time corredor mais estreito? Qual quebra essa IA primeiro? <short pause> "
              "Comenta seu time e segue. O mais votado vira o próximo vídeo.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% DOS SOFÁS QUE PASSAM POR GERAÇÃO",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} SOFÁS",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"Duas IAs presas num sofá. Na geração 1, nenhum dos {n} sofás passou a quina. 🛋️\n"
            f"Em {G} gerações elas aprenderam sozinhas: no teste com começos novos, {pct(s_f)} passam. "
            f"Simulação real, zero regra programada. Uma série em que a IA aprende sozinha.\n"
            f"O que quebra essa IA primeiro: SOFÁ MAIOR ou CORREDOR MAIS ESTREITO? Comenta seu time e segue 👇 "
            f"O mais votado vira o próximo vídeo.\n\n"
            f"#inteligenciaartificial #ia #aprendizadodemaquina #simulacao #tecnologia #curiosidades #desafio #aprendeusozinha")
    ev["duelo"] = {"meio": (meio, s_a, t_a, w_a), "fin": (G - 1, s_f, t_f, w_f)}
    return cenas, info, post, ev
