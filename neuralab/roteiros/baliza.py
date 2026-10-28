"""Roteiro do episódio Baliza: uma IA aprende a estacionar de ré entre dois carros.

Todo número falado sai do treino. O teste de estresse do final (trocar a posição inicial) é
uma simulação extra, medida aqui mesmo, e só entra no vídeo se o resultado for notável.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.baliza import Baliza as DesafioBaliza
from ..desafios.foguete import SUCESSO
from ..rede import Arquitetura

BRANCO, MAGENTA = (0.92, 0.96, 1.0), (1.0, 0.3, 0.8)
DESTAQUES = {"baliza": VERDE, "ré": AMARELO, "bateu": VERMELHO, "vezes": VERMELHO, "bate": VERMELHO,
             "vaga": MAGENTA, "ninguém": VERDE, "sozinhos": VERDE, "autoescola": VERDE, "estaciona": VERDE,
             "melhores": VERDE, "fácil": AMARELO, "metro": AMARELO, "falham": VERMELHO}

NOMES = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"]


def pct(x):
    return f"{100 * x:.0f}%"


def em_dez(x):
    """0.87 -> 'quase nove em cada dez'; 0.60 -> 'seis em cada dez'."""
    n = int(round(x * 10))
    quase = "quase " if x * 10 < n - 0.15 else ""
    return f"{quase}{NOMES[n]} em cada dez"


def erro_txt(e):
    """Fração de erro em linguagem falada (só frações que a fala consegue dizer com fidelidade)."""
    if 0.6 <= e < 0.72:
        return "quase dois em cada três"
    if 0.45 <= e < 0.55:
        return "metade das vezes"
    return f"{pct(e)} das vezes"


def milhar(x):
    return f"{int(x):,}".replace(",", ".")


def suave(x, k=5):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def eventos(hist):
    s = suave(hist["sucessos"].astype(float))
    perto = suave(hist["m_perto"])
    G = len(s)
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev = {"G": G, "s": s, "perto": perto}
    ev["chega"] = primeiro(lambda g: perto[g] >= 0.5)                       # metade já chega perto da vaga
    ev["gs"] = int(np.argmax(hist["sucessos"] > 0)) if (hist["sucessos"] > 0).any() else None
    ev["dez"] = primeiro(lambda g: s[g] >= 0.1 * hist["genes"].shape[1])    # 1 em cada 10 estaciona
    ev["gf"] = int(np.argmax(s))                                            # a melhor geração (suavizada)
    ev["gf"] = int(min(max(ev["gf"], 1), G - 1))
    ev["final_g"] = G - 1
    return ev


def nota_historia(hist):
    """Quanto a curva conta uma boa história: aprende cedo o bastante, chega alto e depois não desaba."""
    suc = hist["sucessos"].astype(float)
    n = hist["genes"].shape[1]
    if not (suc > 0).any():
        return -1.0
    sm = suave(suc)
    G = len(suc)
    gs = int(np.argmax(suc > 0))
    return float(sm.max() / n + 0.4 * max(1 - abs(gs / G - 0.3) * 2, 0) + 0.3 * (sm[-1] / max(sm.max(), 1)))


def teste_estresse(hist, g, n=400, ruido=1.4, semente=11):
    """O melhor carro da geração g, em n partidas com posição inicial muito mais variada."""
    D = DesafioBaliza
    arq = Arquitetura(D.camadas)
    genes = hist["genes"][g]
    # o melhor da geração = o que mais estacionou nas partidas de treino
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
    def taxa(r):
        a = D(n, np.random.default_rng(semente), ruido=r)
        p = arq.desempacota(clones)
        for t in range(D.passos):
            sa, _ = arq.avalia(p, a.observa())
            a.passo(sa, t)
            if (a.estado != 0).all():
                break
        return float((a.estado == SUCESSO).mean())
    return taxa(0.3), taxa(ruido)


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], hist["genes"].shape[1]
    gs = ev["gs"]
    if gs is None:
        raise RuntimeError("Nenhum carro estacionou: treine mais gerações ou troque a semente.")
    suc = hist["sucessos"]
    batidas = hist["m_bateu"] * n                      # carros que bateram de verdade (não conta tempo esgotado)
    falhas_ate = int(round(batidas.sum()))
    f_gs = int(round(batidas[:gs + 1].sum()))
    melhor_g = int(np.argmax(suave(suc.astype(float))))
    fin_s = int(suc[melhor_g])
    base, duro = teste_estresse(hist, melhor_g)
    tem_virada = base - duro >= 0.15
    cenas, marcos = [], []
    D = DESTAQUES

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO: o carro perfeito + a virada plantada
    rod_h = A.rodada(melhor_g)
    heroi = A.busca(rod_h, "primeiro")
    m_h = float(rod_h.morte[heroi]) * rod_h.dt
    marcas = [{"tipo": "circulo", "em": max(m_h - 0.6, 0), "alvo": "alvo", "texto": "NA VAGA!", "rx": 90, "ry": 60,
               "desloca": (0, -80)}]
    cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas,
         titulo_gancho=[("A IA APRENDEU", BRANCO), ("A FAZER BALIZA", VERDE)],
         fala="Esse carro aprendeu a fazer baliza sozinho.")
    if tem_virada:
        cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas, pausa=0.2,
             fala=f"Mas se eu mudo o ponto de partida, ele erra {erro_txt(1 - duro)}.")
    else:
        cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="gancho", marcas=marcas, pausa=0.2,
             fala="Ninguém ensinou como.")

    # ---------------------------------------------------------------- PREMISSA + GERAÇÃO 1 (com batidas de verdade)
    b0 = float(hist["m_bateu"][0])
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"{n} CARROS", BRANCO), ("CADA UM COM UMA IA QUE NÃO SABE NADA", BRANCO)],
         fala=f"No começo, são {n} carros. Cada um é guiado por uma IA que não sabe nada: ela acelera e vira o volante ao acaso.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · BATERAM {pct(b0)}", VERMELHO)],
         carimbo={"texto": f"BATERAM {pct(b0)}", "cor": VERMELHO, "em": 0.5, "sub": "GERAÇÃO 1"},
         fala=f"Resultado: {em_dez(b0)} batem." if b0 < 0.97 else "Resultado: todo mundo bate.")
    r0 = A.rodada(0)
    est0 = r0.reg["estado"][:, -1]
    caiu = [k for k in np.argsort(r0.morte) if r0.morte[k] >= 0 and est0[k] == 2]    # FALHA = 2
    if len(caiu) >= 3:
        pick = [caiu[int(i)] for i in np.linspace(len(caiu) * 0.15, len(caiu) * 0.85, 3)]
        cena(tipo="montagem", clipes=[(0, int(k)) for k in pick], destaques=D,
             log=[("BATEU. BATEU. BATEU.", VERMELHO)], fala="Bateu. Bateu. Bateu.")

    # ---------------------------------------------------------------- A REGRA DO JOGO (explicada com calma)
    g_sel = min(5, G - 1)
    cena(tipo="ao_vivo", ger=g_sel, log=[("OS MELHORES SÃO COPIADOS", VERDE), ("OS PIORES SAEM", VERMELHO),
                                         ("CADA RODADA = 1 GERAÇÃO", BRANCO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": VERDE, "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="Aí vem a regra: a cada rodada, os carros que vão melhor são copiados, com pequenas mudanças. "
              "Os piores saem. Cada rodada é uma geração.")

    # ---------------------------------------------------------------- CHEGA PERTO, MAS NINGUÉM ESTACIONA
    if ev["chega"] is not None and gs - ev["chega"] > 3:
        g = ev["chega"]
        pe = float(hist["m_perto"][g])
        ninguem = int(suc[g]) == 0
        cena(tipo="ao_vivo", ger=g,
             log=[(f"GER {g + 1:03d} · CHEGAM PERTO {pct(pe)}", AMARELO)],
             carimbo={"texto": f"{pct(pe)} CHEGAM PERTO", "cor": AMARELO, "em": 0.4,
                      "sub": "MAS NINGUÉM ESTACIONA" if ninguem else f"MAS {int(suc[g])} ESTACIONAM"},
             fala=f"Rodada após rodada, eles melhoram. Na geração {g + 1}, {em_dez(pe)} já chegam perto da vaga… "
                  + ("mas nenhum consegue estacionar." if ninguem else f"mas só {int(suc[g])} conseguem estacionar."))
        marcos.append((g, "PERTO", AMARELO))

    # ---------------------------------------------------------------- O PRIMEIRO SUCESSO
    r_s = A.rodada(gs)
    k_s = A.busca(r_s, "primeiro")
    m_s = float(r_s.morte[k_s]) * r_s.dt
    marcas_s = [{"tipo": "circulo", "em": max(m_s - 0.9, 0), "alvo": "alvo", "texto": "PAROU!", "rx": 90, "ry": 60,
                 "desloca": (0, -80)}]
    cena(tipo="replay", ger=gs, foco=k_s, marcas=marcas_s,
         cartao={"numero": 1, "rotulo": "PRIMEIRO SUCESSO", "nome": f"GERAÇÃO {gs + 1}", "cor": VERDE,
                 "stat": f"DEPOIS DE {milhar(f_gs)} BATIDAS"},
         log=[(f"GER {gs + 1:03d} · PRIMEIRO SUCESSO", VERDE)],
         fala=f"Geração {gs + 1}. Depois de {milhar(f_gs)} batidas, o primeiro carro dá ré… ajeita… e para na vaga.")
    marcos.append((gs, "1º", VERDE))

    # ---------------------------------------------------------------- COPIAR, MISTURAR, MELHORAR (montagem real)
    gens = sorted(set([gs] + list(np.linspace(gs, melhor_g, 5).astype(int)[1:])))
    clipes = []
    for g in gens:
        k = A.busca(A.rodada(g), "primeiro")
        if k is not None:
            clipes.append((g, k))
    if len(clipes) >= 3:
        cena(tipo="montagem", clipes=clipes[:4], log=[("OS PRÓXIMOS COPIAM ESSE JEITO", BRANCO)],
             fala="Os próximos carros copiam esse jeito, e vão melhorando.")

    # ---------------------------------------------------------------- O NÚMERO FINAL + O GRÁFICO
    cena(tipo="ao_vivo", ger=melhor_g, log=[(f"GER {melhor_g + 1:03d} · {fin_s}/{n} NA VAGA", VERDE)],
         carimbo={"texto": f"{fin_s} DE {n}", "cor": VERDE, "em": 0.5, "sub": "ESTACIONAM SOZINHOS"},
         fala=f"Na geração {melhor_g + 1}, {fin_s} de {n} carros estacionam sozinhos." + (" Mais da metade." if fin_s > n / 2 else ""))
    serie = suc / n
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% QUE ESTACIONA",
         eras=[(gs, G - 1, "APRENDENDO", VERDE)], rotulo_y="CARROS NA VAGA POR GERAÇÃO",
         final=pct(float(serie[melhor_g])), log=[(f"{milhar(falhas_ate)} BATIDAS NO TOTAL", VERMELHO)],
         fala=f"Do zero, sem nenhuma aula. Só tentativa e erro: foram {milhar(falhas_ate)} batidas.")

    # ---------------------------------------------------------------- A VIRADA: o teste de estresse
    if tem_virada:
        itens = [("TREINO", base, VERDE), ("NOVO LUGAR", duro, VERMELHO)]
        sub = "o melhor carro · 400 tentativas · % que estaciona"
        cena(tipo="barras", grupo="estresse", ger=melhor_g, itens=itens, titulo="E SE MUDAR O PONTO DE PARTIDA?", sub=sub,
             log=[("TESTE: OUTRO PONTO DE PARTIDA", AMARELO)], pausa=0.25,
             fala="Mas será que ele aprendeu a dirigir de verdade? Peguei o melhor carro e mudei só o ponto de partida.")
        cena(tipo="barras", grupo="estresse", ger=melhor_g, itens=itens, titulo="E SE MUDAR O PONTO DE PARTIDA?", sub=sub,
             destaque=1, cor_destaque="vermelho", revela=0.0, rotulo_destaque=f"▼ -{(base - duro) * 100:.0f} pts",
             log=[(f"ESTACIONA {pct(base)} → {pct(duro)}", VERMELHO)],
             fala=f"No treino, ele acertava {pct(base)}. Agora, só {pct(duro)}. "
                  "Ele aprendeu o trajeto do treino. Em outra situação, se perde.")

    # ---------------------------------------------------------------- CHAMADA + LAÇO (volta ao replay do gancho)
    cena(tipo="replay", ger=melhor_g, foco=heroi, grupo="fim", inicio=max(m_h - 1.4, 0),
         escolha={"pergunta": "O QUE DERRUBA ELE?", "opcoes": [("LADEIRA", AMARELO), ("CHUVA", CIANO)], "em": 0.2},
         destaques={"ladeira": AMARELO, "chuva": CIANO, "votado": VERDE},
         fala="O que derruba ele primeiro: uma ladeira ou a chuva? Comenta! O mais votado vira o próximo vídeo.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% QUE ESTACIONA POR GERAÇÃO",
            "marcos": marcos, "rotulo_vivo": f"{n} CARROS",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, A.Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    virada = f" Aí mudei UM detalhe e ela caiu de {pct(base)} para {pct(duro)}. 🚗💥" if tem_virada else ""
    post = (f"Esses carros bateram {milhar(falhas_ate)} vezes e aprenderam a estacionar sozinhos.{virada}\n"
            f"Simulação real: {n} carros, {G} gerações, zero aula. Uma série em que a IA aprende sozinha.\n"
            f"Qual derruba ela primeiro: LADEIRA ou CHUVA? O mais votado vira o próximo vídeo 👇\n\n"
            f"#ia #inteligenciaartificial #aprendizadodemaquina #baliza #autoescola #curiosidades #tecnologia #carro")
    return cenas, info, post, ev
