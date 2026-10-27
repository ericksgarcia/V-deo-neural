"""Roteiro para desafios de UMA população (foguete, baliza): do zero ao domínio.

Mesmos princípios do pênalti: gancho com o resultado, conflito (a IA contra o desafio),
viradas com geração e número reais, cartão no primeiro sucesso, chamada com escolha.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO

BRANCO = (0.92, 0.96, 1.0)

TEXTOS = {
    "foguete": {
        "agentes": "foguetes", "verbo": "pousar", "falha": "explodiu", "falhas": "explosões",
        "gancho": "Essa IA explodiu {f} foguetes… até aprender a pousar.",
        "missao": "{n} foguetes. Cérebros aleatórios. A missão: pousar inteiro nessa plataforma.",
        "zero": "Geração um: zero pousos.",
        "quase": "Geração {g}: já acha a plataforma… mas ninguém ensinou a frear.",
        "primeiro": "Geração {g}: um único foguete desacelera… e pousa.",
        "final": "Geração {g}: {s} de {n} pousam sozinhos.",
        "opcoes": [("DRONE NA TEMPESTADE", AMARELO), ("POUSO EM MARTE", CIANO)],
        "cta": "Próximo: drone na tempestade ou pouso em Marte? Comenta A ou B.",
        "destaques": {"explodiu": VERMELHO, "pousar": VERDE, "pousa": VERDE, "frear": VERMELHO, "sozinhos": VERDE},
    },
    "baliza": {
        "agentes": "carros", "verbo": "estacionar", "falha": "bateu", "falhas": "batidas",
        "gancho": "Essa IA bateu {f} vezes… até aprender a fazer baliza.",
        "missao": "{n} carros. Cérebros aleatórios. A missão: fazer baliza bem aqui.",
        "zero": "Geração um: ninguém para na vaga.",
        "quase": "Geração {g}: já acha a vaga… mas ainda bate em tudo.",
        "primeiro": "Geração {g}: um único carro dá ré, endireita… e para.",
        "final": "Geração {g}: {s} de {n} passariam na autoescola.",
        "opcoes": [("BALIZA NA LADEIRA", AMARELO), ("VAGA DE RÉ NA CHUVA", CIANO)],
        "cta": "Próximo: baliza na ladeira ou vaga de ré na chuva? Comenta A ou B.",
        "destaques": {"bateu": VERMELHO, "baliza": VERDE, "para": VERDE, "tudo": VERMELHO, "autoescola": VERDE},
    },
}


def geracoes_chave(hist):
    suc, quase = hist["sucessos"], hist["quase"]
    if not (suc > 0).any():
        return None
    gs = int(np.argmax(suc > 0))
    gf = int(len(suc) - 1 - np.argmax(suc[::-1]))
    gq = None
    if gs >= 3:
        a = max(1, gs // 3)
        gq = a + int(np.argmax(quase[a:gs]))
    return {"gs": gs, "gf": gf, "gq": gq}


def nota_historia(hist):
    g = geracoes_chave(hist)
    if g is None:
        return -1
    G = len(hist["sucessos"])
    frac = hist["sucessos"][g["gf"]] / hist["genes"].shape[1]
    return frac + 0.5 * max(1 - abs(g["gs"] / G - 0.3) * 2, 0) + (0.2 if g["gq"] is not None else 0)


def milhar(x):
    return f"{int(x):,}".replace(",", ".")


def monta(nome, hist, A):
    T = TEXTOS[nome]
    g = geracoes_chave(hist)
    if g is None:
        raise RuntimeError("Nenhum indivíduo conseguiu: treine mais gerações ou troque a semente.")
    n = hist["genes"].shape[1]
    gs, gf, gq = g["gs"], g["gf"], g["gq"]
    s_final = int(hist["sucessos"][gf])
    f_ate = int(hist["falhas"][: gs + 1].sum())
    D = T["destaques"]
    rod = A.rodada(gs)
    heroi = int(np.where((rod.reg["estado"][:, -1] == 1))[0][np.argmin(rod.morte[rod.reg["estado"][:, -1] == 1])])
    marcas = [{"tipo": "circulo", "em": max(rod.morte[heroi] * rod.dt - 0.1, 0), "alvo": "agente", "segue": True,
               "texto": "PRIMEIRO!"}]
    cenas = [
        dict(tipo="replay", ger=gs, foco=heroi, grupo="gancho", marcas=marcas, destaques=D,
             fala=T["gancho"].format(f=milhar(f_ate))),
        dict(tipo="replay", ger=gs, foco=heroi, grupo="gancho", marcas=marcas, destaques=D,
             fala="Ninguém ensinou como.", pausa=0.3),
        dict(tipo="ao_vivo", ger=0, grupo="g1", destaques=D, log=[(f"POPULAÇÃO: {n} {T['agentes'].upper()}", BRANCO)],
             fala=T["missao"].format(n=n)),
        dict(tipo="ao_vivo", ger=0, grupo="g1", destaques=D, log=[("GER 001 · SUCESSO 0", VERMELHO)], fala=T["zero"]),
        dict(tipo="ao_vivo", ger=min(5, len(hist["genes"]) - 1), destaques=D,
             log=[("SELEÇÃO: OS MELHORES TÊM FILHOS", BRANCO)],
             fala="A cada geração, só os melhores têm filhos. Com pequenas mutações."),
    ]
    if gq is not None:
        cenas.append(dict(tipo="ao_vivo", ger=gq, destaques=D, fala=T["quase"].format(g=gq + 1),
                          log=[(f"GER {gq + 1:03d} · CHEGAM PERTO {int(hist['quase'][gq])}", AMARELO)]))
    cenas.append(dict(tipo="replay", ger=gs, foco=heroi, marcas=marcas, destaques=D,
                      cartao={"numero": 1, "rotulo": "PRIMEIRO SUCESSO", "nome": f"GERAÇÃO {gs + 1}", "cor": VERDE,
                              "stat": f"DEPOIS DE {milhar(f_ate)} {T['falhas'].upper()}"},
                      log=[(f"GER {gs + 1:03d} · PRIMEIRO SUCESSO", VERDE)], fala=T["primeiro"].format(g=gs + 1)))
    cenas.append(dict(tipo="ao_vivo", ger=gf, destaques=D, log=[(f"GER {gf + 1:03d} · {s_final}/{n}", VERDE)],
                      fala=T["final"].format(g=gf + 1, s=s_final, n=n)))
    serie = hist["sucessos"] / n
    cenas.append(dict(tipo="grafico", serie=serie, eras=[(gs, gf, "APRENDENDO", VERDE)], titulo="% QUE CONSEGUE",
                      rotulo_y="SUCESSO", destaques=D,
                      fala=f"De zero a {100 * s_final / n:.0f}%. Sem nenhuma aula. Só tentativa, erro e seleção."))
    cenas.append(dict(tipo="final", pergunta="PRÓXIMO DESAFIO?", opcoes=T["opcoes"], destaques=D, fala=T["cta"]))
    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% QUE CONSEGUE POR GERAÇÃO",
            "marcos": [(gs, "1º", VERDE)],
            "rodape": f"POP {n} · REDE {'-'.join(map(str, A.Desafio.camadas))} · {len(serie)} GERAÇÕES · NADA FOI PROGRAMADO"}
    post = (f"Essa IA {T['falha']} {milhar(f_ate)} vezes até aprender a {T['verbo']}. Na geração {gf + 1}, "
            f"{s_final} de {n} conseguiram sozinhos. Simulação real.\nA ou B pro próximo? 👇\n\n"
            f"#ia #inteligenciaartificial #machinelearning #simulacao #tecnologia #{nome}")
    return cenas, info, post, g
