"""Roteiro do episódio Cruzamento: sem semáforo, uma IA aprende a passar oito carros sem bater.

O vídeo conta a história NA ORDEM em que ela aconteceu (geração 1 caótica, uma descoberta de cada vez);
nada do resultado final aparece no começo. Todo número falado sai do treino ou de um teste medido aqui.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.cruzamento import Cruzamento as Desafio
from ..desafios.foguete import SUCESSO
from ..rede import Arquitetura

BRANCO, MAGENTA = (0.92, 0.96, 1.0), (1.0, 0.3, 0.8)

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend who is watching an experiment unfold live and cannot look away. "
    "Natural spoken Brazilian rhythm; pace brisk and conversational, about three words per second, never rushed, "
    "never dragging. Emotional arc: open intrigued with a teasing question, then deadpan and amused as the cars "
    "crash, say 'Eliminados' coldly; build real curiosity before each discovery and let each one land with quiet "
    "awe, as if you did not expect it either; sound a little worried at the twist where faster means riskier; "
    "finish playful and provocative, inviting the viewer to pick a side.")

DESTAQUES = {"semáforo": AMARELO, "bateram": VERMELHO, "bateu": VERMELHO, "batida": VERMELHO, "batidas": VERMELHO,
             "frear": CIANO, "frenar": CIANO, "esperar": CIANO, "espera": CIANO, "rua": MAGENTA, "ruas": MAGENTA,
             "inventou": VERDE, "ninguém": VERDE, "sozinha": VERDE, "rápida": AMARELO, "segura": CIANO,
             "mais": BRANCO}

NOMES = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"]


def pct(x):
    return f"{100 * x:.0f}%"


def em_dez(x):
    """0.87 -> 'quase nove em cada dez'; 0.60 -> 'seis em cada dez'."""
    n = int(round(x * 10))
    quase = "quase " if x * 10 < n - 0.15 else ""
    return f"{quase}{NOMES[n]} em cada dez"


def milhar(x):
    return f"{int(x):,}".replace(",", ".")


def seg(x):
    """Segundos em fala: 7.4 -> '7,4'."""
    return f"{x:.1f}".replace(".", ",")


def suave(x, k=9):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def eventos(hist):
    n = hist["genes"].shape[1]
    G = len(hist["sucessos"])
    s = suave(hist["sucessos"].astype(float))
    bat = suave(hist["m_bateu"])
    par = suave(hist["m_parou"])
    tem = suave(hist["m_tempo"])
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev = {"G": G, "n": n, "s": s, "bat": bat, "par": par, "tem": tem}
    ev["sobe"] = primeiro(lambda g: s[g] >= 0.25 * n)
    ev["meio"] = primeiro(lambda g: s[g] >= 0.6 * n)
    if ev["meio"] is None:
        ev["meio"] = int(np.argmax(s))
    m = ev["meio"]
    # "parar menos": a espera cai bastante e o cruzamento fica mais rápido
    ev["rapida"] = primeiro(lambda g: par[g] <= par[m] - 0.12 and tem[g] <= tem[m] - 0.5, m + 5)
    if ev["rapida"] is None:
        ev["rapida"] = primeiro(lambda g: par[g] <= par[m] - 0.08, m + 5)
    # a geração mais segura entre o meio e a "rápida" (ou o fim)
    fim = ev["rapida"] if ev["rapida"] is not None else G
    ev["segura"] = int(m + np.argmin(bat[m:fim])) if fim > m else m
    return ev


def _trava(ev, n):
    """Entre as descobertas 2 e 3 o placar quase não sobe (no máximo 10% de n em média) por 20+ gerações."""
    s, m, r = ev["s"], ev["meio"], ev["rapida"]
    return bool(r - m >= 20 and s[r] - s[m] <= 0.1 * n)


def nota_historia(hist):
    """Boa história: começa baixo, sobe cedo, e depois a espera cai (nova descoberta) com o placar firme."""
    n = hist["genes"].shape[1]
    if (hist["sucessos"] == 0).all() and hist["sucessos"].max() == 0:
        return -1.0
    ev = eventos(hist)
    if ev["sobe"] is None or ev["rapida"] is None:
        return -0.5
    G = ev["G"]
    s = ev["s"]
    if not _trava(ev, n):
        return -0.25
    comeca_baixo = 1.0 - min(hist["sucessos"][0] / (0.1 * n), 1.0)
    cedo = max(1 - abs(ev["sobe"] / G - 0.07) * 6, 0)
    queda = float(ev["par"][ev["meio"]] - ev["par"][-1])
    trava = max(1 - ev["rapida"] / G * 2, 0)   # a 3ª descoberta não pode demorar demais
    return float(s.max() / n + 0.3 * comeca_baixo + 0.3 * cedo + 0.8 * queda + 0.4 * (s[-1] / max(s.max(), 1)) + 0.5 * trava)


def duelo(hist, g, n=600, semente=21):
    """O melhor cruzamento da geração g, clonado em n trânsitos NOVOS (todos diferentes):
    (fração sem batida, tempo médio até liberar o cruzamento em s, fração que bateu)."""
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
    return float(suc.mean()), float(a.t_fim[suc].mean() * a.dt) if suc.any() else 0.0, float(a.bateu.mean())


def _primeira_espera(rod, k):
    """Instante (s) em que um carro do cruzamento k fica quase parado antes do cruzamento."""
    s = rod.reg["s"][k]
    esp = ((s[..., 1] < 0.8) & (s[..., 0] < -3.5) & (s[..., 0] > -13)).any(1)
    return float(np.argmax(esp)) * rod.dt if esp.any() else 1.0


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], ev["n"]
    if ev["sobe"] is None or ev["rapida"] is None:
        raise RuntimeError("A história não tem as duas viradas: treine mais gerações ou troque a semente.")
    suc = hist["sucessos"]
    b0, s0 = float(hist["m_bateu"][0]), int(suc[0])
    sobe, meio, rap, segu = ev["sobe"], ev["meio"], ev["rapida"], ev["segura"]
    bateram_tot = int(round((hist["m_bateu"] * n).sum()))
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO: a pergunta (nada de resultado)
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("TIREI O SEMÁFORO", BRANCO), ("E DEIXEI UMA IA NO COMANDO", AMARELO)],
         log=[(f"{n} CRUZAMENTOS AO MESMO TEMPO", BRANCO), ("8 CARROS · 4 RUAS · 0 SEMÁFOROS", AMARELO)],
         fala="Tirei o semáforo. <short pause> Oito carros, quatro ruas, um cruzamento. "
              "Quantos você acha que passam sem bater?")
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         log=[("MESMO CÉREBRO EM TODOS OS CARROS", BRANCO), ("SÓ DECIDE: ACELERAR OU FREAR", CIANO)],
         fala="Cada carro tem um cérebro de computador, vazio. <short pause> Ele só escolhe: acelerar… ou frear.")
    cena(tipo="ao_vivo", ger=0, grupo="g1b",
         log=[(f"GER 001 · {s0} DE {n} SEM BATER", VERMELHO)],
         carimbo={"texto": f"{s0} DE {n}" if s0 else "NENHUM", "cor": VERMELHO, "em": 0.5, "sub": "PASSAM SEM BATER"},
         fala=(f"Geração um. Só {NOMES[s0] if s0 < 11 else s0} de {n} cruzamentos termina sem batida."
               if s0 else f"Geração um. Nenhum dos {n} cruzamentos termina sem batida."))
    r0 = A.rodada(0)
    est0 = r0.reg["estado"][:, -1]
    caiu = [k for k in np.argsort(r0.morte) if r0.morte[k] >= 0 and est0[k] == 2 and r0.reg["s"][k, r0.morte[k], :, 0].max() > -2]
    if len(caiu) >= 3:
        pick = [caiu[int(i)] for i in np.linspace(len(caiu) * 0.15, len(caiu) * 0.85, 3)]
        cena(tipo="montagem", clipes=[(0, int(k)) for k in pick], log=[("BATEU. BATEU. BATEU.", VERMELHO)],
             fala="Bateu. <short pause> Bateu. <short pause> Bateu.")

    # ---------------------------------------------------------------- A REGRA
    g_sel = min(5, G - 1)
    cena(tipo="ao_vivo", ger=g_sel, log=[("OS MELHORES SÃO COPIADOS", VERDE), ("OS PIORES SAEM", VERMELHO),
                                         ("CADA RODADA = 1 GERAÇÃO", BRANCO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": VERDE, "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="A regra é cruel. Os melhores cruzamentos são copiados, com pequenas mudanças. "
              "Os piores? <short pause> Eliminados.")

    # ---------------------------------------------------------------- DESCOBERTA 1: FREAR E ESPERAR
    rs = A.rodada(sobe)
    ks = A.busca(rs, "primeiro")
    k1 = ks if ks is not None else A.busca(rs, "lento")
    em1 = _primeira_espera(rs, k1)
    cena(tipo="replay", ger=sobe, foco=k1,
         marcas=[{"tipo": "circulo", "em": em1, "alvo": "espera", "texto": "FREOU!", "rx": 100, "ry": 55,
                  "desloca": (0, -90)}],
         cartao={"numero": 1, "rotulo": "DESCOBERTA", "nome": "FREAR E ESPERAR", "cor": CIANO,
                 "stat": f"SEM BATER {s0} → {int(suc[sobe])} DE {n}"},
         log=[(f"GER {sobe + 1:03d} · {int(suc[sobe])}/{n} SEM BATER", CIANO)],
         fala=f"Geração {sobe + 1}. Um carro percebe uma coisa. <short pause> "
              "Se tem outro chegando, dá para frear. E esperar ele passar.")
    marcos.append((sobe, "FREAR", CIANO))
    gens = sorted(set(np.linspace(sobe, meio, 4).astype(int)))
    clipes = [(g, k) for g in gens for k in [A.busca(A.rodada(g), "primeiro")] if k is not None]
    if len(clipes) >= 3:
        cena(tipo="montagem", clipes=clipes[:4], log=[("OS PRÓXIMOS COPIAM O JEITO", BRANCO)],
             fala="Os cruzamentos seguintes copiam o truque. <short pause> E o placar dispara.")

    # ---------------------------------------------------------------- DESCOBERTA 2: UMA RUA DE CADA VEZ
    rm = A.rodada(meio)
    km = A.busca(rm, "primeiro")
    uma_rua = float(hist["m_alterna"][meio]) < 0.2     # só uma troca de rua em cada cruzamento sem batida
    n_ok = int(suc[meio])
    if km is not None and uma_rua:
        em2 = _primeira_espera(rm, km)
        cena(tipo="replay", ger=meio, foco=km,
             marcas=[{"tipo": "circulo", "em": em2, "alvo": "espera", "texto": "ESPERA", "rx": 100, "ry": 55,
                      "desloca": (0, -90)}],
             cartao={"numero": 2, "rotulo": "DESCOBERTA", "nome": "UMA RUA DE CADA VEZ", "cor": MAGENTA,
                     "stat": f"{n_ok} DE {n} SEM BATER"},
             log=[(f"GER {meio + 1:03d} · {n_ok}/{n} SEM BATER", MAGENTA)],
             fala=f"Geração {meio + 1}. Aparece um padrão. <short pause> Uma rua passa inteira. "
                  f"Só depois, a outra. Em todos os {n_ok} que passaram. <short pause> "
                  "Ninguém programou isso. Eles inventaram o semáforo.")
        marcos.append((meio, "1 RUA", MAGENTA))
    else:
        cena(tipo="ao_vivo", ger=meio, log=[(f"GER {meio + 1:03d} · {n_ok}/{n} SEM BATER", VERDE)],
             carimbo={"texto": f"{n_ok} DE {n}", "cor": VERDE, "em": 0.5, "sub": "SEM BATER"},
             fala=f"Geração {meio + 1}. {n_ok} de {n} cruzamentos passam sem bater.")

    # ---------------------------------------------------------------- CALMARIA ENGANOSA
    g_calma = int(np.clip((meio + rap) // 2, meio + 1, G - 1))
    # a calmaria só entra no roteiro se os dados confirmam: o placar não passa de ~10% acima do que já tinha
    if not _trava(ev, n):
        raise RuntimeError("O placar não trava entre as descobertas 2 e 3: escolha outra semente.")
    cena(tipo="ao_vivo", ger=g_calma, log=[(f"GER {g_calma + 1:03d} · {int(suc[g_calma])}/{n}", AMARELO),
                                          ("O PLACAR TRAVA", AMARELO)],
         carimbo={"texto": "O PLACAR TRAVA", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {g_calma + 1}"},
         fala=f"Aí o placar trava. <short pause> Em {rap - meio} gerações, ele sai de {int(round(ev['s'][meio]))} "
              f"para só {int(round(ev['s'][rap]))}, em média. Será que acabou?")

    # ---------------------------------------------------------------- DESCOBERTA 3: PARAR MENOS
    rr = A.rodada(rap)
    kr = A.busca(rr, "primeiro") or A.busca(rr, "lento")
    p_m, p_r = float(hist["m_parou"][meio]), float(hist["m_parou"][rap])
    t_m, t_r = float(hist["m_tempo"][meio]), float(hist["m_tempo"][rap])
    cena(tipo="replay", ger=rap, foco=kr,
         cartao={"numero": 3, "rotulo": "DESCOBERTA", "nome": "PARAR MENOS", "cor": AMARELO,
                 "stat": f"CARROS PARADOS {pct(p_m)} → {pct(p_r)}"},
         log=[(f"GER {rap + 1:03d} · ESPERA {pct(p_m)} → {pct(p_r)}", AMARELO),
              (f"TEMPO {seg(t_m)} s → {seg(t_r)} s", AMARELO)],
         fala=f"Geração {rap + 1}. Eles descobrem outra coisa: parar menos. <short pause> "
              f"Antes, {em_dez(p_m)} carros paravam esperando. Agora, {em_dez(p_r)}.")
    marcos.append((rap, "PARA MENOS", AMARELO))

    # ---------------------------------------------------------------- GRÁFICO
    serie = suc / n
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% SEM BATIDA",
         eras=[(sobe, meio, "APRENDE A FREAR", CIANO), (meio, rap, "TRAVA", AMARELO),
               (rap, G - 1, "PARA MENOS", VERDE)],
         rotulo_y="CRUZAMENTOS SEM BATIDA POR GERAÇÃO", final=pct(float(serie[-1])),
         log=[(f"{milhar(bateram_tot)} CRUZAMENTOS COM BATIDA NO CAMINHO", VERMELHO)],
         fala=f"Tudo isso sem aula, sem regra de trânsito. Só tentativa, erro… e {milhar(bateram_tot)} batidas.")

    # ---------------------------------------------------------------- O TESTE: 1ª geração que funcionou x a última
    s_a, t_a, b_a = duelo(hist, meio)
    s_f, t_f, b_f = duelo(hist, G - 1)
    ganhou = s_f - s_a >= 0.1
    itens = [(f"GER {meio + 1}", s_a, CIANO), (f"GER {G}", s_f, VERDE)]
    sub = "o melhor cruzamento de cada geração · 600 trânsitos novos · % sem batida"
    cena(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="E EM TRÂNSITO NOVO?", sub=sub,
         log=[("TESTE: 600 TRÂNSITOS NOVOS", AMARELO)], pausa=0.25,
         fala=f"Mas será que ela aprendeu de verdade? <short pause> Peguei a geração {meio + 1} e a {G}, "
              "e joguei as duas em seiscentos trânsitos novos.")
    cena(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="E EM TRÂNSITO NOVO?", sub=sub,
         destaque=1, cor_destaque="verde", revela=0.0,
         rotulo_destaque=f"▲ +{(s_f - s_a) * 100:.0f} pts" if ganhou else "◀ MELHOR",
         log=[(f"SEM BATER {pct(s_a)} → {pct(s_f)}", VERDE), (f"TEMPO {seg(t_a)} s → {seg(t_f)} s", AMARELO)],
         fala=f"A geração {meio + 1} passa sem bater {pct(s_a)}. A {G}, {pct(s_f)}. <short pause> "
              + (f"E libera o cruzamento {seg(t_a - t_f)} segundo mais rápido. " if t_a - t_f >= 0.3 else "")
              + f"Mesmo assim, ainda bate em {pct(b_f)} dos trânsitos novos.")

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    rf = A.rodada(G - 1)
    kf = A.busca(rf, "primeiro") or A.busca(rf, "lento")
    cena(tipo="replay", ger=G - 1, foco=kf, grupo="fim",
         escolha={"pergunta": "O QUE ENTRA NO CRUZAMENTO?", "opcoes": [("AMBULÂNCIA", VERMELHO), ("PEDESTRE", CIANO)],
                  "em": 0.2},
         destaques={"ambulância": VERMELHO, "pedestre": CIANO, "votado": VERDE},
         fala="Agora você decide. <short pause> O que atrapalha mais essa IA? Uma ambulância, ou um pedestre? "
              "Comenta seu lado. O mais votado vira o próximo vídeo.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% SEM BATIDA POR GERAÇÃO",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} CRUZAMENTOS",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    virada = f" Em trânsito novo, a geração {meio + 1} passava sem bater {pct(s_a)}; a {G}, {pct(s_f)}. 🚦"
    post = (f"Tirei o semáforo e deixei uma IA resolver o cruzamento. Foram {milhar(bateram_tot)} batidas até ela "
            f"aprender a esperar e a revezar as ruas.{virada}\n"
            f"Simulação real: {n} cruzamentos, {G} gerações, zero regra de trânsito. Uma série em que a IA aprende sozinha.\n"
            f"O que atrapalha mais essa IA: AMBULÂNCIA ou PEDESTRE? O mais votado vira o próximo vídeo 👇\n\n"
            f"#ia #inteligenciaartificial #aprendizadodemaquina #transito #semaforo #curiosidades #tecnologia #simulacao")
    ev["duelo"] = {"meio": (meio, s_a, t_a, b_a), "fin": (G - 1, s_f, t_f, b_f)}
    return cenas, info, post, ev
