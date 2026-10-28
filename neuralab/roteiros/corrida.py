"""Roteiro do episódio Corrida: baterias de 4 carros-IA aprendem a correr, ultrapassar e defender.

Todo número falado sai do treino (métricas medidas dentro da simulação). Só entra no vídeo o
que os dados mostram: as "descobertas" são detectadas na curva, nunca presumidas.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.foguete import SUCESSO
from .baliza import BRANCO, MAGENTA, em_dez, milhar, pct, suave

ESTILO_VOZ = (
    "You are a gripping, charismatic Brazilian Portuguese (pt-BR) storyteller narrating a short vertical video, "
    "talking to one person like a friend who just discovered something amazing. Natural spoken Brazilian rhythm; "
    "pace brisk and conversational, about three words per second, never rushed, never dragging. Emotional arc: "
    "open intrigued and confident, then conspiratorial; explain the rules calmly with a hint of dry humor and say "
    "'Eliminados' coldly; ask the viewer questions and leave a beat before the answer; build tension before the "
    "first finish and let it land triumphant; sound proud and a little shocked on the big numbers; finish playful "
    "and provocative, inviting the viewer to pick a side.")
DESTAQUES = {"corrida": VERDE, "corre": VERDE, "carros": CIANO, "bateram": VERMELHO, "parede": VERMELHO,
             "ultrapassa": AMARELO, "ultrapassagens": AMARELO, "porta": MAGENTA, "fecha": MAGENTA,
             "ninguém": VERDE, "sozinhos": VERDE, "óleo": AMARELO, "chuva": CIANO, "eliminados": VERMELHO}


def eventos(hist):
    s = suave(hist["sucessos"].astype(float))
    n = hist["genes"].shape[1]
    G = len(s)
    ult = suave(hist["m_ultra"])
    blo = suave(hist["m_bloqueio"])
    par = suave(hist["m_parede"])
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev = {"G": G, "s": s}
    ev["gs"] = int(np.argmax(hist["sucessos"] > 0)) if (hist["sucessos"] > 0).any() else None
    ev["metade"] = primeiro(lambda g: s[g] >= 0.5 * n)
    ev["ultra"] = primeiro(lambda g: ult[g] >= 2 * max(ult[:3].mean(), 0.5) and ult[g] >= 1.5)
    ev["bloq"] = primeiro(lambda g: blo[g] >= 5 * max(blo[:3].mean(), 0.05))
    ev["gf"] = int(min(max(np.argmax(s), 1), G - 1))
    return ev


def nota_historia(hist):
    suc = hist["sucessos"].astype(float)
    n = hist["genes"].shape[1]
    if not (suc > 0).any():
        return -1.0
    sm = suave(suc)
    G = len(suc)
    gs = int(np.argmax(suc > 0))
    ev = eventos(hist)
    return float(sm.max() / n + 0.4 * max(1 - abs(gs / G - 0.3) * 2, 0) + 0.3 * (sm[-1] / max(sm.max(), 1))
                 + 0.2 * (ev["ultra"] is not None) + 0.2 * (ev["bloq"] is not None))


def ultrapassagens(rod):
    """(n,) ultrapassagens de cada carro na rodada (a partir da posição gravada)."""
    ordem = rod.reg["extra"][:, :, 2]
    vivo = rod.reg["estado"][:, 1:] == 0
    return ((ordem[:, 1:] < ordem[:, :-1]) & vivo).sum(1)


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], hist["genes"].shape[1]
    gs = ev["gs"]
    if gs is None:
        raise RuntimeError("Nenhum carro terminou: treine mais gerações ou troque a semente.")
    suc = hist["sucessos"]
    gf = ev["gf"]
    cenas, marcos = [], []
    D = DESTAQUES

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    # herói: na melhor geração, o vencedor da bateria com mais ultrapassagens
    rod_h = A.rodada(gf)
    ult_h = ultrapassagens(rod_h)
    cand = [k for k in range(n) if rod_h.reg["estado"][k, -1] == SUCESSO]
    heroi = max(cand, key=lambda k: (ult_h[k], -rod_h.morte[k]))
    mates_h = rod_h.mates[heroi]
    b0, bf = float(hist["m_parede"][0]), float(suave(hist["m_parede"])[gf])
    ult0, ultf = float(hist["m_ultra"][:3].mean()), float(suave(hist["m_ultra"])[gf])
    blo0, blof = float(hist["m_bloqueio"][:3].mean()), float(suave(hist["m_bloqueio"])[gf])
    t0 = [float(x) for x in hist["m_tempo"] if x > 0]
    t_ini, t_fim = (t0[0], float(hist["m_tempo"][gf])) if t0 and hist["m_tempo"][gf] > 0 else (None, None)
    batidas_ate = int(round((hist["m_parede"] * n).sum()))

    # ------------------------------------------------ GANCHO
    marcas = [{"tipo": "circulo", "em": 5.0, "alvo": "agente", "texto": "OLHA ESSE", "rx": 90, "ry": 60,
               "desloca": (0, -80)}]
    cena(tipo="replay", ger=gf, foco=heroi, grupo="gancho", marcas=marcas,
         titulo_gancho=[("A IA APRENDEU", BRANCO), ("A CORRER", VERDE)],
         fala="Quatro carros. Nenhuma regra de corrida. <short pause> Olha o que eles aprenderam sozinhos.")
    cena(tipo="replay", ger=gf, foco=heroi, grupo="gancho", marcas=marcas, pausa=0.2,
         fala="Um deles aprendeu até a fechar a porta. <short pause> E ninguém ensinou isso.")

    # ------------------------------------------------ GERAÇÃO 1
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"{n} CARROS · BATERIAS DE 4", BRANCO)],
         fala=f"Tudo começou assim: {n} carros, em baterias de quatro. Cada um com um cérebro vazio. "
              "<short pause> Acelera e vira o volante… ao acaso.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · SAÍRAM DA PISTA {pct(b0)}", VERMELHO)],
         carimbo={"texto": f"{pct(b0)} BATERAM NA PAREDE", "cor": VERMELHO, "em": 0.5, "sub": "GERAÇÃO 1"},
         fala="E aí? Quantos você acha que terminaram a corrida? <long pause> Nenhum.")

    # ------------------------------------------------ REGRA
    cena(tipo="ao_vivo", ger=min(8, G - 1), log=[("QUEM ANDA MAIS LONGE FICA", VERDE), ("QUEM FICA ATRÁS SAI", VERMELHO),
                                                 ("ANDAR À FRENTE DOS RIVAIS VALE EXTRA", AMARELO)],
         carimbo={"texto": "OS MELHORES FICAM", "cor": VERDE, "em": 0.4, "sub": "OS PIORES SAEM"},
         fala="A regra é cruel. Quem anda mais longe e passa os rivais é copiado. <short pause> Os outros? Eliminados.")

    # ------------------------------------------------ PRIMEIRO A TERMINAR
    r_s = A.rodada(gs)
    k_s = A.busca(r_s, "primeiro")
    cena(tipo="replay", ger=gs, foco=k_s,
         cartao={"numero": 1, "rotulo": "PRIMEIRO A TERMINAR", "nome": f"GERAÇÃO {gs + 1}", "cor": VERDE,
                 "stat": f"DEPOIS DE {milhar(int(round((hist['m_parede'][:gs + 1] * n).sum())))} BATIDAS NA PAREDE"},
         log=[(f"GER {gs + 1:03d} · PRIMEIRO A TERMINAR", VERDE)],
         fala=f"Geração {gs + 1}. Depois de {milhar(int(round((hist['m_parede'][:gs + 1] * n).sum())))} batidas na parede… "
              "<long pause> um carro termina as duas voltas.")
    marcos.append((gs, "1º", VERDE))

    # ------------------------------------------------ ULTRAPASSAGEM
    if ev["ultra"] is not None and ultf > 1.5 * ult0:
        g = ev["ultra"]
        ru = A.rodada(g)
        ku = int(np.argmax(np.where(ru.reg["estado"][:, -1] == SUCESSO, ultrapassagens(ru), -1)))
        cena(tipo="replay", ger=g, foco=ku,
             cartao={"numero": 2, "rotulo": "ULTRAPASSAGEM", "nome": f"GERAÇÃO {g + 1}", "cor": AMARELO,
                     "stat": f"ULTRAPASSAGENS POR CARRO {ult0:.1f} → {ultf:.1f}".replace(".", ",")},
             log=[(f"GER {g + 1:03d} · APRENDEU A ULTRAPASSAR", AMARELO)],
             fala="Depois, descobriram a ultrapassagem. <short pause> Eles passam uns pelos outros, "
                  "em plena curva.")
        marcos.append((g, "ULTRAPASSA", AMARELO))

    # ------------------------------------------------ FECHAR A PORTA
    if ev["bloq"] is not None and blof > 4 * max(blo0, 0.05):
        g = ev["bloq"]
        rb = A.rodada(g)
        kb = rb.lider
        cena(tipo="replay", ger=g, foco=kb,
             cartao={"numero": 3, "rotulo": "FECHAR A PORTA", "nome": f"GERAÇÃO {g + 1}", "cor": MAGENTA,
                     "stat": f"SEGUNDOS SE JOGANDO NA FRENTE {blo0:.1f} → {blof:.1f}".replace(".", ",")},
             log=[(f"GER {g + 1:03d} · APRENDEU A DEFENDER", MAGENTA)],
             fala="E a maior virada: eles aprenderam a defender. <short pause> Se alguém tenta passar, "
                  "o da frente se joga na frente dele.")
        marcos.append((g, "DEFENDE", MAGENTA))

    # ------------------------------------------------ NÚMERO FINAL + GRÁFICO
    cena(tipo="ao_vivo", ger=gf, log=[(f"GER {gf + 1:03d} · {int(suc[gf])}/{n} TERMINAM", VERDE)],
         carimbo={"texto": f"{int(suc[gf])} DE {n}", "cor": VERDE, "em": 0.5, "sub": "TERMINAM A CORRIDA"},
         fala=f"Geração {gf + 1}. De {n} carros, {int(suc[gf])} terminam a corrida.")
    serie = suc / n
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% QUE TERMINA",
         eras=[(gs, G - 1, "APRENDENDO", VERDE)], rotulo_y="CARROS QUE TERMINAM POR GERAÇÃO",
         final=pct(float(serie[gf])), log=[(f"{milhar(batidas_ate)} BATIDAS NA PAREDE", VERMELHO)],
         fala=f"Começou do zero. Sem aula, sem piloto. Só tentativa e erro… <short pause> e {milhar(batidas_ate)} batidas.")

    if t_ini and t_fim and t_ini - t_fim > 1.0:
        itens = [("1º TERMINAR", t_ini, VERMELHO), ("GERAÇÃO FINAL", t_fim, VERDE)]
        cena(tipo="barras", grupo="tempo", ger=gf, itens=itens, titulo="MELHOR TEMPO · 2 VOLTAS",
             sub="segundos do carro mais rápido", log=[(f"{t_ini:.1f}s → {t_fim:.1f}s".replace(".", ","), VERDE)],
             fala=f"E o carro mais rápido? Baixou de {t_ini:.1f} para {t_fim:.1f} segundos.".replace(".", ","))

    # ------------------------------------------------ CHAMADA + LAÇO
    cena(tipo="replay", ger=gf, foco=heroi, grupo="fim", inicio=0.0,
         escolha={"pergunta": "O QUE ELES ENFRENTAM?", "opcoes": [("ÓLEO", AMARELO), ("CHUVA", CIANO)], "em": 0.2},
         destaques={"óleo": AMARELO, "chuva": CIANO, "votado": VERDE},
         fala="Agora você decide. O que derruba eles primeiro? Óleo na pista ou chuva? <short pause> "
              "Comenta seu lado. O mais votado vira o próximo vídeo.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% QUE TERMINA POR GERAÇÃO",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} CARROS",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, A.Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"{n} carros, zero regras de corrida. {milhar(batidas_ate)} batidas na parede depois, eles ultrapassam e "
            f"até fecham a porta. 🏎️\n"
            f"Simulação real: {G} gerações, nada foi programado. Uma série em que a IA aprende sozinha.\n"
            f"Óleo ou chuva: o que derruba eles primeiro? O mais votado vira o próximo vídeo 👇\n\n"
            f"#ia #inteligenciaartificial #aprendizadodemaquina #corrida #carros #curiosidades #tecnologia")
    return cenas, info, post, ev
