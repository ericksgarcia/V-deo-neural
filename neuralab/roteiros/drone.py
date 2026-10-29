"""Roteiro do episódio Drone: uma IA aprende a cruzar uma tempestade (vento em rajadas + raios) e pousar.

Todo número falado sai do treino. O teste de estresse do final (vento 80% mais forte, 40 tempestades novas)
é uma simulação extra, medida aqui mesmo, e só entra no vídeo se o resultado for notável.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.drone import Drone as DesafioDrone
from ..desafios.foguete import SUCESSO
from ..rede import Arquitetura
from .baliza import em_dez, milhar, pct, suave

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
DESTAQUES = {"drone": VERDE, "tempestade": MAGENTA, "vento": CIANO, "raio": AMARELO, "raios": AMARELO,
             "fritados": VERMELHO, "fritou": VERMELHO, "caem": VERMELHO, "cai": VERMELHO, "pousou": VERDE,
             "pousam": VERDE, "pouso": VERDE, "sozinhos": VERDE, "melhores": VERDE, "pegadinha": AMARELO}


def eventos(hist):
    s = suave(hist["sucessos"].astype(float))
    perto = suave(hist["m_perto"])
    G = len(s)
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev = {"G": G, "s": s, "perto": perto}
    ev["chega"] = primeiro(lambda g: perto[g] >= 0.5)
    ev["gs"] = int(np.argmax(hist["sucessos"] > 0)) if (hist["sucessos"] > 0).any() else None
    ev["gf"] = int(min(max(np.argmax(s), 1), G - 1))
    # a geração em que a tempestade mais fritou drones (depois do começo do aprendizado)
    gs = ev["gs"] or 0
    fim = min(gs + 90, G)
    ev["g_raio"] = gs + int(np.argmax(hist["m_raio"][gs:fim]))
    return ev


def nota_historia(hist):
    """Boa história = aprende cedo o bastante e se mantém alto no fim (a tempestade muda a cada geração)."""
    suc = hist["sucessos"].astype(float)
    n = hist["genes"].shape[1]
    if not (suc > 0).any():
        return -1.0
    sm = suave(suc, 9)
    G = len(suc)
    gs = int(np.argmax(suc > 0))
    return float(sm.max() / n + 0.5 * sm[-40:].mean() / n + 0.3 * max(1 - abs(gs / G - 0.15) * 2, 0))


def teste_estresse(hist, g, tempestades=40, por=25, forte=1.8):
    """O melhor drone da geração g em 40 tempestades novas: normais x vento 80% mais forte."""
    D = DesafioDrone
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
    clones = np.repeat(genes[melhor:melhor + 1], por, 0)
    p = arq.desempacota(clones)

    def taxa(k):
        r = []
        for j in range(tempestades):
            a = D(por, np.random.default_rng(900_000 + j), ruido=k)
            for t in range(D.passos):
                sa, _ = arq.avalia(p, a.observa())
                a.passo(sa, t)
                if (a.estado != 0).all():
                    break
            r.append(float((a.estado == SUCESSO).mean()))
        return float(np.mean(r))
    return taxa(1.0), taxa(forte)


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], hist["genes"].shape[1]
    gs = ev["gs"]
    if gs is None:
        raise RuntimeError("Nenhum drone pousou: treine mais gerações ou troque a semente.")
    suc = hist["sucessos"]
    quedas_ate = int(round(hist["falhas"].sum()))
    f_gs = int(hist["falhas"][:gs + 1].sum())
    melhor_g = ev["gf"]
    fin_s = int(suc[melhor_g])
    base, duro = teste_estresse(hist, melhor_g)
    tem_virada = base - duro >= 0.15
    cenas, marcos = [], []
    D = DESTAQUES

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO: o drone que cruza a tempestade
    rod_h = A.rodada(melhor_g)
    heroi = A.busca(rod_h, "primeiro")
    m_h = float(rod_h.morte[heroi]) * rod_h.dt
    marcas = [{"tipo": "circulo", "em": max(m_h - 0.6, 0), "alvo": "alvo", "texto": "POUSOU!", "rx": 90, "ry": 60,
               "desloca": (0, -80)}]
    cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas,
         titulo_gancho=[("A IA APRENDEU", BRANCO), ("A VOAR NA TEMPESTADE", VERDE)],
         fala=f"Esses drones caíram {milhar(quedas_ate)} vezes. <short pause> E mesmo assim, um deles aprendeu a atravessar uma tempestade.")
    if tem_virada:
        cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas, pausa=0.2,
             fala="Mas tem uma pegadinha. <short pause> Eu conto no final.")
    else:
        cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas, pausa=0.2,
             fala="Mas tem uma pegadinha. <short pause> Ninguém ensinou como.")

    # ---------------------------------------------------------------- PREMISSA + GERAÇÃO 1
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"{n} DRONES", BRANCO), ("CADA UM COM UMA IA QUE NÃO SABE NADA", BRANCO)],
         fala=f"Tudo começou assim: {n} drones, cérebro vazio, vento em rajadas e raios caindo.")
    s0 = int(suc[0])
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · POUSARAM {s0}", VERMELHO)],
         carimbo={"texto": f"POUSARAM {s0}", "cor": VERMELHO, "em": 0.5, "sub": "GERAÇÃO 1"},
         fala="Quantos pousaram? <long pause> " + ("Nenhum." if s0 == 0 else f"Só {s0}."))
    r0 = A.rodada(0)
    est0 = r0.reg["estado"][:, -1]
    caiu = [k for k in np.argsort(r0.morte) if r0.morte[k] >= 0 and est0[k] == 2]
    if len(caiu) >= 3:
        pick = [caiu[int(i)] for i in np.linspace(len(caiu) * 0.15, len(caiu) * 0.85, 3)]
        cena(tipo="montagem", clipes=[(0, int(k)) for k in pick], log=[("CAIU. CAIU. CAIU.", VERMELHO)],
             fala="Caiu. <short pause> Caiu. <short pause> Caiu.")

    # ---------------------------------------------------------------- A REGRA DO JOGO
    g_sel = min(5, G - 1)
    cena(tipo="ao_vivo", ger=g_sel, log=[("OS MELHORES SÃO COPIADOS", VERDE), ("OS PIORES SAEM", VERMELHO),
                                         ("CADA RODADA = 1 GERAÇÃO", BRANCO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": VERDE, "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="Aí entra a regra cruel. Os melhores são copiados, com pequenas mudanças. "
              "Os piores? <short pause> Eliminados. Cada rodada é uma geração.")

    # ---------------------------------------------------------------- CHEGA PERTO, MAS NINGUÉM POUSA
    if ev["chega"] is not None and gs - ev["chega"] > 3:
        g = ev["chega"]
        pe = float(hist["m_perto"][g])
        ninguem = int(suc[g]) == 0
        cena(tipo="ao_vivo", ger=g, log=[(f"GER {g + 1:03d} · CHEGAM PERTO {pct(pe)}", AMARELO)],
             carimbo={"texto": f"{pct(pe)} CHEGAM PERTO", "cor": AMARELO, "em": 0.4,
                      "sub": "MAS NINGUÉM POUSA" if ninguem else f"MAS {int(suc[g])} POUSAM"},
             fala=f"Geração {g + 1}. {em_dez(pe).capitalize()} chegam perto da plataforma. "
                  + ("<short pause> Mas nenhum… <long pause> consegue pousar." if ninguem
                     else f"<short pause> Mas só {int(suc[g])}… <long pause> conseguem pousar."))
        marcos.append((g, "PERTO", AMARELO))

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
         fala=f"Geração {gs + 1}. Depois de {milhar(f_gs)} quedas… <long pause> um drone enfrenta o vento… e pousa.")
    marcos.append((gs, "1º", VERDE))

    # ---------------------------------------------------------------- COPIAR, MISTURAR, MELHORAR
    gens = sorted(set([gs] + list(np.linspace(gs, melhor_g, 5).astype(int)[1:])))
    clipes = []
    for g in gens:
        k = A.busca(A.rodada(g), "primeiro")
        if k is not None:
            clipes.append((g, k))
    if len(clipes) >= 3:
        cena(tipo="montagem", clipes=clipes[:4], log=[("OS PRÓXIMOS COPIAM ESSE JEITO", BRANCO)],
             fala="Os filhos herdam o jeito, e vão melhorando.")

    # ---------------------------------------------------------------- A TEMPESTADE FRITA (dado real)
    g = ev["g_raio"]
    fr = float(hist["m_raio"][g])
    if fr >= 0.4:
        cena(tipo="ao_vivo", ger=g, log=[(f"GER {g + 1:03d} · FRITADOS {pct(fr)}", AMARELO)],
             carimbo={"texto": f"{pct(fr)} FRITADOS", "cor": AMARELO, "em": 0.4, "sub": "POR RAIO"},
             fala=f"Mas o raio continua. <short pause> Na geração {g + 1}, {em_dez(fr)} foram fritados.")

    # ---------------------------------------------------------------- O NÚMERO FINAL + O GRÁFICO
    cena(tipo="ao_vivo", ger=melhor_g, log=[(f"GER {melhor_g + 1:03d} · {fin_s}/{n} POUSAM", VERDE)],
         carimbo={"texto": f"{fin_s} DE {n}", "cor": VERDE, "em": 0.5, "sub": "POUSAM SOZINHOS"},
         fala=f"Geração {melhor_g + 1}. <short pause> De {n} drones, {fin_s} pousam sozinhos."
              + (" <short pause> Quase todos." if fin_s > 0.85 * n else (" <short pause> Mais da metade." if fin_s > n / 2 else "")))
    serie = suc / n
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% QUE POUSA",
         eras=[(gs, G - 1, "APRENDENDO", VERDE)], rotulo_y="DRONES NA PLATAFORMA POR GERAÇÃO",
         final=pct(float(serie[melhor_g])), log=[(f"{milhar(quedas_ate)} QUEDAS NO TOTAL", VERMELHO)],
         fala="Sem aula, sem professor. Só tentativa e erro.")

    # ---------------------------------------------------------------- A VIRADA: o teste de estresse
    if tem_virada:
        itens = [("NORMAL", base, VERDE), ("VENTO +80%", duro, VERMELHO)]
        sub = "o melhor drone · 40 tempestades novas · % que pousa"
        cena(tipo="barras", grupo="estresse", ger=melhor_g, itens=itens, titulo="E SE O VENTO FICAR MAIS FORTE?", sub=sub,
             log=[("TESTE: VENTO 80% MAIS FORTE", AMARELO)], pausa=0.25,
             fala="Mas será que ele aprendeu a voar de verdade? <short pause> "
                  "Peguei o melhor drone e aumentei o vento em oitenta por cento.")
        cena(tipo="barras", grupo="estresse", ger=melhor_g, itens=itens, titulo="E SE O VENTO FICAR MAIS FORTE?", sub=sub,
             destaque=1, cor_destaque="vermelho", revela=0.0, rotulo_destaque=f"▼ -{(base - duro) * 100:.0f} pts",
             log=[(f"POUSA {pct(base)} → {pct(duro)}", VERMELHO)],
             fala=f"Em quarenta tempestades novas, ele pousava {pct(base)}. <long pause> Com vento forte? Só {pct(duro)}. "
                  "<short pause> Ele aprendeu aquela tempestade. Não qualquer uma.")

    # ---------------------------------------------------------------- CHAMADA + LAÇO
    cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="fim", inicio=max(m_h - 1.4, 0),
         escolha={"pergunta": "O PRÓXIMO VÍDEO?", "opcoes": [("SUMÔ DE IAs", AMARELO), ("POLÍCIA E LADRÃO", CIANO)],
                  "em": 0.2},
         destaques={"sumô": AMARELO, "polícia": CIANO, "ladrão": CIANO, "votado": VERDE},
         fala="Próximo vídeo: duas IAs, uma contra a outra. Sumô ou polícia e ladrão? <short pause> "
              "Comenta SUMÔ ou POLÍCIA. O mais votado vira o próximo.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% QUE POUSA POR GERAÇÃO",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} DRONES",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, A.Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    virada = f" Aí aumentei o vento e ele caiu de {pct(base)} para {pct(duro)}. 🌪️" if tem_virada else ""
    post = (f"Esses drones caíram {milhar(quedas_ate)} vezes e aprenderam a pousar em plena tempestade.{virada}\n"
            f"Simulação real: {n} drones, {G} gerações, zero aula. Uma série em que a IA aprende sozinha.\n"
            f"Qual vem agora: SUMÔ DE IAs ou POLÍCIA E LADRÃO? O mais votado vira o próximo vídeo 👇\n\n"
            f"#ia #inteligenciaartificial #aprendizadodemaquina #drone #tempestade #curiosidades #tecnologia")
    return cenas, info, post, ev
