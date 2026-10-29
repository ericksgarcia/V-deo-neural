"""Roteiro do episódio Drone: uma IA aprende a atravessar uma tempestade e pousar.

Todo número falado sai do treino. Bateria e vento a favor são medidos nos drones que pousaram; o teste de
estresse (tempestade mais forte) é uma simulação extra, medida aqui, e só entra se o resultado for notável.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.drone import Drone as DesafioDrone
from ..desafios.foguete import SUCESSO
from ..rede import Arquitetura
from .baliza import em_dez, erro_txt, milhar, pct, suave

BRANCO, MAGENTA = (0.92, 0.96, 1.0), (1.0, 0.3, 0.8)

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend who just discovered something amazing. Natural spoken Brazilian rhythm; "
    "pace brisk and conversational, about three words per second, never rushed, never dragging. Emotional arc: "
    "open intrigued and confident, then conspiratorial, as if sharing a secret; explain the rules calmly and "
    "clearly with a hint of dry humor and say 'Eliminados' coldly; ask the viewer questions as if you really "
    "want their guess and leave a beat before the answer; build tension before the first success and let "
    "'Pousou' land triumphant and relieved; slow down and sound proud on the big numbers; deliver the drop in "
    "the stress test with honest surprise; finish playful and provocative, inviting the viewer to pick a side.")
DESTAQUES = {"drone": VERDE, "tempestade": AMARELO, "vento": CIANO, "caiu": VERMELHO, "caiu.": VERMELHO,
             "pousou": VERDE, "pousa": VERDE, "pousam": VERDE, "pousar": VERDE, "ninguém": VERDE,
             "sozinhos": VERDE, "bateria": AMARELO, "favor": VERDE, "quedas": VERMELHO, "cai": VERMELHO,
             "eliminados": VERMELHO, "sumô": MAGENTA, "polícia": MAGENTA}


def eventos(hist):
    s = suave(hist["sucessos"].astype(float))
    G = len(s)
    ev = {"G": G, "s": s}
    ev["gs"] = int(np.argmax(hist["sucessos"] > 0)) if (hist["sucessos"] > 0).any() else None
    ev["gf"] = int(min(max(int(np.argmax(s)), 1), G - 1))
    return ev


def nota_historia(hist):
    suc = hist["sucessos"].astype(float)
    n = hist["genes"].shape[1]
    if not (suc > 0).any():
        return -1.0
    sm = suave(suc)
    G = len(suc)
    gs = int(np.argmax(suc > 0))
    return float(sm.max() / n + 0.4 * max(1 - abs(gs / G - 0.3) * 2, 0) + 0.3 * (sm[-1] / max(sm.max(), 1)))


def _roda(genes, forca, n=400, semente=11):
    arq = Arquitetura(DesafioDrone.camadas)
    p = arq.desempacota(genes)
    a = DesafioDrone(len(genes), np.random.default_rng(semente), forca=forca)
    for t in range(DesafioDrone.passos):
        sa, _ = arq.avalia(p, a.observa())
        a.passo(sa, t)
        if (a.estado != 0).all():
            break
    a.finaliza(t)
    return a


def teste_estresse(hist, g, n=400, forca=1.4):
    """O melhor drone da geração g, em n partidas: tempestade do treino x tempestade mais forte."""
    genes = hist["genes"][g]
    amb = DesafioDrone(len(genes), np.random.default_rng(int(hist["semente"][g])))
    arq = Arquitetura(DesafioDrone.camadas)
    pb = arq.desempacota(genes)
    for t in range(DesafioDrone.passos):
        saida, _ = arq.avalia(pb, amb.observa())
        amb.passo(saida, t)
        if (amb.estado != 0).all():
            break
    amb.finaliza(t)
    melhor = int(np.argmax(amb.aptidao()))
    clones = np.repeat(genes[melhor:melhor + 1], n, 0)
    taxa = lambda f: float((_roda(clones, f).estado == SUCESSO).mean())
    return taxa(1.0), taxa(forca)


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], hist["genes"].shape[1]
    gs = ev["gs"]
    if gs is None:
        raise RuntimeError("Nenhum drone pousou: treine mais gerações ou troque a semente.")
    suc = hist["sucessos"]
    f_gs = int(hist["falhas"][: gs + 1].sum())
    falhas_ate = int(hist["falhas"].sum())
    melhor_g = int(np.argmax(suave(suc.astype(float))))
    fin_s = int(suc[melhor_g])
    base, duro = teste_estresse(hist, melhor_g)
    tem_virada = base - duro >= 0.15
    ini = slice(gs, min(gs + 5, G))
    bat0, bat1 = float(hist["m_bateria"][ini].mean()), float(suave(hist["m_bateria"])[melhor_g])
    ven0, ven1 = float(hist["m_vento_favor"][ini].mean()), float(suave(hist["m_vento_favor"])[melhor_g])
    tem_bateria = bat1 - bat0 >= 0.08
    tem_vento = ven1 - ven0 >= 0.4
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
    marcas = [{"tipo": "circulo", "em": max(m_h - 0.6, 0), "alvo": "alvo", "texto": "POUSOU!", "rx": 90, "ry": 60,
               "desloca": (0, -80)}]
    cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas,
         titulo_gancho=[("A IA APRENDEU", BRANCO), ("A VOAR NA TEMPESTADE", CIANO)],
         fala="Esse drone não sabia voar. <short pause> Ninguém ensinou nada. Olha ele cruzando a tempestade.")
    if tem_virada:
        cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=[], pausa=0.2,
             fala=f"Mas tem uma pegadinha. <short pause> Com o vento mais forte, ele cai {erro_txt(1 - duro)}.")
    else:
        cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas, pausa=0.2,
             fala="Mas tem uma pegadinha. <short pause> Ninguém ensinou como.")

    # ---------------------------------------------------------------- PREMISSA + GERAÇÃO 1
    r0 = A.rodada(0)
    est0 = r0.reg["estado"][:, -1]
    s0 = int((est0 == SUCESSO).sum())
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"{n} DRONES", BRANCO), ("CADA UM COM UMA IA QUE NÃO SABE NADA", BRANCO)],
         fala=f"Tudo começou assim: {n} drones. Cada um com um cérebro de computador vazio. <short pause> "
              "A missão: atravessar a tempestade e pousar ali.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · POUSARAM {s0}", VERMELHO)],
         carimbo={"texto": f"POUSARAM {s0}", "cor": VERMELHO, "em": 0.5, "sub": "GERAÇÃO 1"},
         fala="E aí? Quantos você acha que pousaram? <long pause> "
              + ("Nenhum." if s0 == 0 else f"Só {s0}."))
    caiu = [k for k in np.argsort(r0.morte) if r0.morte[k] >= 0 and est0[k] == 2]
    if len(caiu) >= 3:
        pick = [caiu[int(i)] for i in np.linspace(len(caiu) * 0.15, len(caiu) * 0.85, 3)]
        cena(tipo="montagem", clipes=[(0, int(k)) for k in pick], log=[("CAIU. CAIU. CAIU.", VERMELHO)],
             fala="Caiu. <short pause> Caiu. <short pause> Caiu.")

    # ---------------------------------------------------------------- A REGRA
    g_sel = min(5, G - 1)
    cena(tipo="ao_vivo", ger=g_sel, log=[("OS MELHORES SÃO COPIADOS", VERDE), ("OS PIORES SAEM", VERMELHO),
                                         ("CADA RODADA = 1 GERAÇÃO", BRANCO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": VERDE, "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="Aí entra a regra cruel. Os melhores são copiados e misturados, com pequenas mudanças. "
              "Os piores? <short pause> Eliminados. Cada rodada é uma geração.")

    # ---------------------------------------------------------------- CHEGA PERTO, MAS NINGUÉM POUSA
    quase = hist["quase"]
    if gs >= 4:
        a = max(1, gs // 3)
        gq = a + int(np.argmax(quase[a:gs]))
        if quase[gq] >= 5:
            cena(tipo="ao_vivo", ger=gq, log=[(f"GER {gq + 1:03d} · {int(quase[gq])} CHEGAM NA PLATAFORMA", AMARELO)],
                 carimbo={"texto": f"{int(quase[gq])} CHEGAM LÁ", "cor": AMARELO, "em": 0.4, "sub": "MAS NINGUÉM POUSA"},
                 fala=f"Geração {gq + 1}. {int(quase[gq])} drones já acham a plataforma. "
                      "<short pause> Mas nenhum consegue parar… <long pause> e todos se arrebentam.")
            marcos.append((gq, "PERTO", AMARELO))

    # ---------------------------------------------------------------- O PRIMEIRO POUSO
    r_s = A.rodada(gs)
    k_s = A.busca(r_s, "primeiro")
    m_s = float(r_s.morte[k_s]) * r_s.dt
    marcas_s = [{"tipo": "circulo", "em": max(m_s - 0.9, 0), "alvo": "alvo", "texto": "POUSOU!", "rx": 90, "ry": 60,
                 "desloca": (0, -80)}]
    cena(tipo="replay", ger=gs, foco=k_s, marcas=marcas_s,
         cartao={"numero": 1, "rotulo": "PRIMEIRO POUSO", "nome": f"GERAÇÃO {gs + 1}", "cor": VERDE,
                 "stat": f"DEPOIS DE {milhar(f_gs)} QUEDAS"},
         log=[(f"GER {gs + 1:03d} · PRIMEIRO POUSO", VERDE)],
         fala=f"Geração {gs + 1}. Depois de {milhar(f_gs)} quedas… <long pause> um drone finalmente "
              "<short pause> pousa.")
    marcos.append((gs, "1º", VERDE))

    # ---------------------------------------------------------------- DESCOBERTAS MEDIDAS (só se os dados mostram)
    n_desc = 2
    if tem_vento:
        cena(tipo="ao_vivo", ger=melhor_g, log=[(f"VENTO A FAVOR: {ven0:.1f} → {ven1:.1f} m/s", CIANO)],
             cartao={"numero": n_desc, "rotulo": "DESCOBERTA", "nome": "USAR O VENTO", "cor": CIANO,
                     "stat": f"VENTO A FAVOR {ven0:.1f} → {ven1:.1f} M/S"},
             fala=f"Depois, uma coisa estranha. <short pause> Os drones que pousam começam a pegar mais vento a favor. "
                  f"Em média, de {ven0:.1f} para {ven1:.1f} metros por segundo.".replace(".", ",", 0))
        n_desc += 1
    if tem_bateria:
        cena(tipo="ao_vivo", ger=melhor_g, log=[(f"BATERIA QUE SOBRA {pct(bat0)} → {pct(bat1)}", AMARELO)],
             cartao={"numero": n_desc, "rotulo": "DESCOBERTA", "nome": "GASTAR MENOS", "cor": AMARELO,
                     "stat": f"BATERIA QUE SOBRA {pct(bat0)} → {pct(bat1)}"},
             fala=f"E ficam mais econômicos. Nos primeiros pousos, sobravam só {pct(bat0)} da bateria. <short pause> "
                  f"Na geração {melhor_g + 1}, sobram {pct(bat1)}.")
        n_desc += 1

    gens = sorted(set([gs] + list(np.linspace(gs, melhor_g, 5).astype(int)[1:])))
    clipes = [(g, k) for g in gens if (k := A.busca(A.rodada(g), "primeiro")) is not None]
    if len(clipes) >= 3:
        cena(tipo="montagem", clipes=clipes[:4], log=[("OS PRÓXIMOS COPIAM ESSE JEITO", BRANCO)],
             fala="Os drones seguintes herdam esse jeito. <short pause> E vão melhorando, rodada após rodada.")

    # ---------------------------------------------------------------- O NÚMERO FINAL + O GRÁFICO
    cena(tipo="ao_vivo", ger=melhor_g, log=[(f"GER {melhor_g + 1:03d} · {fin_s}/{n} POUSAM", VERDE)],
         carimbo={"texto": f"{fin_s} DE {n}", "cor": VERDE, "em": 0.5, "sub": "POUSAM SOZINHOS"},
         fala=f"Geração {melhor_g + 1}. <short pause> De {n} drones, {fin_s} pousam sozinhos."
              + (" <short pause> Mais da metade." if fin_s > n / 2 else
                 f" <short pause> {em_dez(fin_s / n).capitalize()}." if fin_s / n >= 0.15 else ""))
    serie = suc / n
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% QUE POUSA",
         eras=[(gs, G - 1, "APRENDENDO", VERDE)], rotulo_y="DRONES QUE POUSAM POR GERAÇÃO",
         final=pct(float(serie[melhor_g])), log=[(f"{milhar(falhas_ate)} QUEDAS NO TOTAL", VERMELHO)],
         fala=f"Começou do zero. Sem aula, sem piloto. Só tentativa e erro… <short pause> e {milhar(falhas_ate)} quedas.")

    # ---------------------------------------------------------------- A VIRADA: tempestade mais forte
    if tem_virada:
        itens = [("TREINO", base, VERDE), ("VENTO +40%", duro, VERMELHO)]
        sub = "o melhor drone · 400 tentativas · % que pousa"
        cena(tipo="barras", grupo="estresse", ger=melhor_g, itens=itens, titulo="E SE O VENTO AUMENTAR?", sub=sub,
             log=[("TESTE: VENTO 40% MAIS FORTE", AMARELO)], pausa=0.25,
             fala="Mas será que ele aprendeu a voar de verdade? <short pause> "
                  "Peguei o melhor drone… e aumentei o vento em quarenta por cento.")
        cena(tipo="barras", grupo="estresse", ger=melhor_g, itens=itens, titulo="E SE O VENTO AUMENTAR?", sub=sub,
             destaque=1, cor_destaque="vermelho", revela=0.0, rotulo_destaque=f"▼ -{(base - duro) * 100:.0f} pts",
             log=[(f"POUSA {pct(base)} → {pct(duro)}", VERMELHO)],
             fala=f"Na tempestade do treino, ele pousava {pct(base)}. <long pause> Com mais vento? Só {pct(duro)}. "
                  "<short pause> Fora do que treinou, ele erra quase metade.")

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="fim", inicio=max(m_h - 1.4, 0),
         escolha={"pergunta": "QUAL O PRÓXIMO?", "opcoes": [("SUMÔ DE IAs", MAGENTA), ("POLÍCIA E LADRÃO", CIANO)], "em": 0.2},
         destaques={"sumô": MAGENTA, "polícia": CIANO, "votado": VERDE},
         fala="Agora você decide. Sumô de IAs ou polícia e ladrão? <short pause> "
              "Comenta seu lado. O mais votado vira o próximo vídeo.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% QUE POUSA POR GERAÇÃO",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} DRONES",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, A.Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    virada = f" Aí aumentei o vento e o melhor drone caiu de {pct(base)} para {pct(duro)}. 🌪️" if tem_virada else ""
    post = (f"Esses drones caíram {milhar(falhas_ate)} vezes e aprenderam a pousar na tempestade sozinhos.{virada}\n"
            f"Simulação real: {n} drones, {G} gerações, zero aula. Uma série em que a IA aprende sozinha.\n"
            f"Comenta SUMÔ ou POLÍCIA: o mais votado vira o próximo vídeo 👇\n\n"
            f"#ia #inteligenciaartificial #aprendizadodemaquina #drone #tempestade #simulacao #algoritmogenetico #tecnologia")
    return cenas, info, post, ev
