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
    return f"{NOMES[int(round(x * 10))]} em cada dez"


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
    gs, gf = ev["gs"], ev["final_g"]
    if gs is None:
        raise RuntimeError("Nenhum carro estacionou: treine mais gerações ou troque a semente.")
    suc = hist["sucessos"]
    falhas_ate = int(hist["falhas"].sum())
    final = int(suc[gf])
    cenas, marcos = [], []
    D = DESTAQUES

    def cena(**kw):
        kw.setdefault("destaques", D)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO: o carro perfeito, já no 1º quadro
    g_h = int(np.argmax(suave(suc.astype(float))))
    rod_h = A.rodada(g_h)
    heroi = A.busca(rod_h, "primeiro")
    marcas = [{"tipo": "circulo", "em": max(float(rod_h.morte[heroi]) * rod_h.dt - 0.6, 0), "alvo": "alvo",
               "texto": "NA VAGA!", "rx": 90, "ry": 60, "desloca": (0, -80)}]
    cena(tipo="replay", ger=g_h, foco=heroi, grupo="gancho", marcas=marcas,
         titulo_gancho=[("A IA APRENDEU", BRANCO), ("A FAZER BALIZA", VERDE)],
         fala=f"Essa IA bateu {milhar(falhas_ate)} vezes… até aprender a fazer baliza.")
    cena(tipo="replay", ger=g_h, foco=heroi, grupo="gancho", marcas=marcas, fala="Ninguém ensinou como.", pausa=0.25)

    # ---------------------------------------------------------------- PREMISSA + GERAÇÃO 1
    b0 = float(hist["m_bateu"][0])
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"POPULAÇÃO: {n} CARROS", BRANCO), ("CÉREBROS ALEATÓRIOS", BRANCO)],
         fala=f"{n} carros. Cérebros aleatórios. Só os melhores têm filhos.")
    cena(tipo="ao_vivo", ger=0, grupo="g1", log=[(f"GER 001 · BATERAM {pct(b0)}", VERMELHO)],
         carimbo={"texto": f"BATERAM {pct(b0)}", "cor": VERMELHO, "em": 0.5, "sub": "GERAÇÃO 1"},
         fala=f"Geração um: {em_dez(b0)} batem em alguma coisa." if b0 < 0.95 else "Geração um: todo mundo bate.")

    # ---------------------------------------------------------------- CHEGA PERTO, MAS BATE
    if ev["chega"] is not None and gs - ev["chega"] > 3:
        g = ev["chega"]
        cena(tipo="ao_vivo", ger=g,
             log=[(f"GER {g + 1:03d} · CHEGAM PERTO {pct(hist['m_perto'][g])}", AMARELO)],
             carimbo={"texto": f"{pct(hist['m_perto'][g])} CHEGAM PERTO", "cor": AMARELO, "em": 0.4,
                      "sub": f"MAS {int(suc[g])} ESTACIONAM"},
             fala=f"Geração {g + 1}: metade já acha a vaga… mas ainda bate em tudo.")
        marcos.append((g, "ACHA", AMARELO))

    # ---------------------------------------------------------------- O PRIMEIRO SUCESSO
    r_s = A.rodada(gs)
    k_s = A.busca(r_s, "primeiro")
    m_s = float(r_s.morte[k_s]) * r_s.dt
    marcas_s = [{"tipo": "circulo", "em": max(m_s - 0.9, 0), "alvo": "alvo", "texto": "PAROU!", "rx": 90, "ry": 60,
                 "desloca": (0, -80)}]
    f_gs = int(hist["falhas"][:gs + 1].sum())
    cena(tipo="replay", ger=gs, foco=k_s, marcas=marcas_s,
         cartao={"numero": 1, "rotulo": "PRIMEIRO SUCESSO", "nome": f"GERAÇÃO {gs + 1}", "cor": VERDE,
                 "stat": f"DEPOIS DE {milhar(f_gs)} BATIDAS"},
         log=[(f"GER {gs + 1:03d} · PRIMEIRO SUCESSO", VERDE)],
         fala=f"Geração {gs + 1}: um único carro dá ré, endireita… e para.")
    marcos.append((gs, "1º", VERDE))

    # ---------------------------------------------------------------- COPIAR, MISTURAR, MELHORAR (montagem real)
    marcas_g = sorted(set([gs] + list(np.linspace(gs, gf, 5).astype(int)[1:])))
    clipes = []
    for g in marcas_g:
        k = A.busca(A.rodada(g), "primeiro")
        if k is not None:
            clipes.append((g, k))
    if len(clipes) >= 3:
        cena(tipo="montagem", clipes=clipes[:4], log=[("ESSE CÉREBRO É COPIADO E MELHORADO", BRANCO)],
             fala="Esse cérebro é copiado, misturado e melhorado.")

    # ---------------------------------------------------------------- PLATÔ OU AVANÇO: o número final
    melhor_g = int(np.argmax(suave(suc.astype(float))))
    fin_s = int(suc[melhor_g])
    cena(tipo="ao_vivo", ger=melhor_g, log=[(f"GER {melhor_g + 1:03d} · {fin_s}/{n} NA VAGA", VERDE)],
         carimbo={"texto": f"{fin_s} DE {n}", "cor": VERDE, "em": 0.5, "sub": "ESTACIONAM SOZINHOS"},
         fala=f"Geração {melhor_g + 1}: {fin_s} de {n} estacionam sozinhos.")

    # ---------------------------------------------------------------- GRÁFICO: a jornada
    serie = suc / n
    cena(tipo="grafico", grupo="grafico", serie=serie, titulo="% QUE ESTACIONA",
         eras=[(gs, G - 1, "APRENDENDO", VERDE)], rotulo_y="CARROS NA VAGA POR GERAÇÃO",
         final=pct(float(serie[melhor_g])),
         log=[(f"{milhar(falhas_ate)} BATIDAS NO TOTAL", VERMELHO)],
         fala=f"De zero a {pct(float(serie[melhor_g]))}. {milhar(falhas_ate)} batidas. Nenhuma aula.")

    # ---------------------------------------------------------------- A REVIRAVOLTA: o teste de estresse
    base, duro = teste_estresse(hist, melhor_g)
    if base - duro >= 0.15:
        cena(tipo="barras", grupo="estresse", itens=[("COMO TREINOU", base, VERDE), ("POSIÇÃO NOVA", duro, VERMELHO)],
             titulo="TESTE DE ESTRESSE", sub="o melhor carro · 400 partidas por teste · % que estaciona",
             log=[("TESTE: MUDAR A POSIÇÃO INICIAL", AMARELO)], pausa=0.3,
             fala="Aí eu mudei só um detalhe: a posição inicial do carro.")
        cena(tipo="barras", grupo="estresse", itens=[("COMO TREINOU", base, VERDE), ("POSIÇÃO NOVA", duro, VERMELHO)],
             titulo="TESTE DE ESTRESSE", sub="o melhor carro · 400 partidas por teste · % que estaciona",
             destaque=1, cor_destaque="vermelho", revela=0.0,
             log=[(f"ESTACIONA {pct(base)} → {pct(duro)}", VERMELHO)],
             fala=f"Era {pct(base)}. Caiu pra {pct(duro)}. Ele decorou o caminho. Não aprendeu a dirigir.")
    # ---------------------------------------------------------------- CHAMADA + LAÇO
    cena(tipo="replay", ger=g_h, foco=heroi, grupo="fim", escolha={
        "pergunta": "PRÓXIMO DESAFIO?", "opcoes": [("LADEIRA", AMARELO), ("CHUVA", CIANO)], "em": 0.2},
         destaques={"ladeira": AMARELO, "chuva": CIANO},
         fala="Baliza na ladeira, ou de ré na chuva? Você escolhe.")

    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% QUE ESTACIONA POR GERAÇÃO",
            "marcos": marcos, "rotulo_vivo": f"{n} CARROS",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, A.Desafio.camadas))} · {G} GERAÇÕES · NADA FOI PROGRAMADO"}
    post = (f"Essa IA bateu {milhar(falhas_ate)} vezes até aprender a fazer baliza. Na geração {melhor_g + 1}, "
            f"{fin_s} de {n} estacionavam sozinhos. Simulação real, nenhum número inventado.\n"
            f"Baliza na ladeira ou de ré na chuva? 👇\n\n#ia #baliza #autoescola #inteligenciaartificial "
            f"#machinelearning #simulacao #carro #tecnologia")
    return cenas, info, post, ev
