"""Roteiro do episódio "O Chão é Lava" (guia v2 + tom humano/divertido): 8 IAs por torre, lava subindo.

Conta a história NA ORDEM em que aconteceu. Todo número falado sai do treino ou de um teste medido aqui.
"""
import numpy as np

from ..adaptadores.populacao import AMARELO, CIANO, VERDE, VERMELHO
from ..desafios.foguete import SUCESSO
from ..desafios.lava import Lava as Desafio
from ..rede import Arquitetura

BRANCO, MAGENTA, LARANJA = (0.92, 0.96, 1.0), (1.0, 0.3, 0.8), (1.0, 0.55, 0.15)

ESTILO_VOZ = (
    "Voice: Achird. You are a warm, funny Brazilian Portuguese (pt-BR) friend telling a story you still can't "
    "believe, on the phone, close to the microphone. Natural, relaxed spoken Brazilian rhythm, about 2.7 words per "
    "second, with real silences. Tease the little AIs like clumsy pets; laugh quietly at the disasters ('ai, ai, "
    "ai…'); sound genuinely proud when something finally works; go quiet and slow before a number, then say it "
    "simply. Never shout, never sound like an announcer or a trailer. Finish with a playful, curious question and "
    "trail off on the last unfinished sentence.")

DESTAQUES = {"lava": LARANJA, "campeã": AMARELO, "pular": CIANO, "pisa": MAGENTA, "cabeça": MAGENTA, "degrau": MAGENTA,
             "topo": VERDE, "churrasquinho": LARANJA, "decorou": VERMELHO, "subir": VERDE}

NOMES = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze"]
NOMES_F = ["nenhuma", "uma", "duas", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez"]


def pct(x):
    return f"{100 * x:.0f}%"


def em_dez(x):
    n = int(round(x * 10))
    return f"{NOMES_F[n]} em cada dez"


def metros(x):
    return f"{x:.1f}".replace(".", ",")


def suave(x, k=9):
    return np.convolve(np.pad(x, (k // 2, k // 2), mode="edge"), np.ones(k) / k, "valid")


def janela(x, g, w=3):
    """Média da série bruta em volta da geração g (os números das descobertas não dependem de uma geração só)."""
    return float(np.mean(x[max(0, g - w): g + w + 1]))


def eventos(hist):
    G = len(hist["sucessos"])
    alt, sub, topo = (suave(hist[k].astype(float)) for k in ("m_alt", "m_subiu", "m_topo"))
    primeiro = lambda cond, ini=0: next((g for g in range(ini, G) if cond(g)), None)
    ev = {"G": G, "n": hist["genes"].shape[1], "alt": alt, "sub": sub, "topo": topo}
    ev["pula"] = primeiro(lambda g: alt[g] >= 2.5)
    ev["degrau"] = primeiro(lambda g: sub[g] >= 0.15, (ev["pula"] or 0) + 5)
    ev["topo_g"] = primeiro(lambda g: topo[g] >= 0.8, (ev["degrau"] or 0) + 20)
    return ev


def nota_historia(hist):
    """Boa história: ninguém escapa na geração 1; sobem cedo; surge o pulo da cabeça de outra; chegam ao topo bem
    depois; o final é forte (salva gente) e sobra margem entre as descobertas para o re-gancho."""
    ev = eventos(hist)
    if None in (ev["pula"], ev["degrau"], ev["topo_g"]):
        return -1.0
    G = ev["G"]
    v = suave(hist["m_vivas"].astype(float))
    comeca = 1.0 - min(float(hist["m_vivas"][0]) / 0.5, 1.0)
    margem = min((ev["topo_g"] - ev["degrau"]) / 40, 1.0)
    return float(v[-20:].mean() / 2 + comeca + 0.6 * margem + 0.5 * ev["sub"][-1] + 0.3 * ev["topo"][-1]
                 - 0.3 * abs(ev["topo_g"] / G - 0.55))


def duelo(hist, g, n=600, semente=21, ruido=1.0):
    """O melhor cérebro da geração g, clonado em n torres NOVAS com as plataformas em outros lugares
    (`ruido`; o treino usa 0,25 na torre padrão). Devolve (fração de torres salvas, IAs vivas por torre)."""
    arq = Arquitetura(Desafio.camadas)
    genes = hist["genes"][g]
    amb = Desafio(len(genes), np.random.default_rng(int(hist["semente"][g])))
    p = arq.desempacota(genes)
    for t in range(Desafio.passos):
        sa, _ = arq.avalia(p, amb.observa())
        amb.passo(sa, t)
    amb.finaliza(t)
    melhor = int(np.argmax(amb.aptidao()))
    clones = np.repeat(genes[melhor:melhor + 1], n, 0)
    a = Desafio(n, np.random.default_rng(semente), ruido=ruido, por_mundo=True)
    pc = arq.desempacota(clones)
    for t in range(Desafio.passos):
        sa, _ = arq.avalia(pc, a.observa())
        a.passo(sa, t)
    a.finaliza(t)
    return float((a.estado == SUCESSO).mean()), float(a.viva.sum(1).mean())


def monta(hist, A):
    ev = eventos(hist)
    G, n = ev["G"], ev["n"]
    if None in (ev["pula"], ev["degrau"], ev["topo_g"]):
        raise RuntimeError("A história não tem todas as viradas: treine mais gerações ou troque a semente.")
    N = Desafio.n_ag
    pula, degrau, topo_g = ev["pula"], ev["degrau"], ev["topo_g"]
    cenas, marcos = [], []

    def cena(**kw):
        kw.setdefault("destaques", DESTAQUES)
        cenas.append(kw)
        return kw

    # ---------------------------------------------------------------- GANCHO
    salvas = int(round(float(hist["m_vivas"][0]) * n))
    quantas = "nenhuma escapou" if salvas == 0 else ("só uma escapou" if salvas == 1 else f"só {NOMES_F[salvas]} escaparam")
    cena(tipo="ao_vivo", ger=0, grupo="g1", vel=1.0,
         titulo_gancho=[("BOTEI LAVA", BRANCO), (f"EMBAIXO DE {N} IAs", LARANJA)],
         log=[(f"{n} TORRES AO MESMO TEMPO", BRANCO), (f"{N} IAs · 1 LAVA · 0 REGRAS", LARANJA)],
         carimbo={"texto": f"{salvas} DE {n * N}", "cor": VERMELHO, "em": 1.8, "sub": "IAs QUE ESCAPARAM"},
         fala=f"Botei lava embaixo de {NOMES_F[N]} IAs. <short pause> Em {n} torres, {quantas}.")
    # ---------------------------------------------------------------- PREMISSA + REGRA
    cena(tipo="ao_vivo", ger=min(3, G - 1), grupo="g1b",
         log=[("MESMO CÉREBRO EM TODAS AS IAs", BRANCO), ("QUEM FICA MAIS TEMPO VIVO VIRA PAI", VERDE)],
         fala="Cérebro vazio, zero aula. <short pause> Quem dura mais vira pai da próxima turma.")
    # ---------------------------------------------------------------- GERAÇÃO 1: a campeã falha
    r0 = A.rodada(0)
    k0 = r0.lider
    cena(tipo="replay", ger=0, foco=k0, grupo="g1c",
         log=[("CAMPEÃ DA GER 001 · CAIU NA LAVA", VERMELHO)],
         fala="A campeã da geração um. <short pause> Ai, ai, ai… virou churrasquinho.")
    # ---------------------------------------------------------------- DESCOBERTA 1: PULAR
    a0, a1 = float(hist["m_alt"][0]), janela(hist["m_alt"], pula)
    rs = A.rodada(pula)
    k1 = A.busca(rs, "primeiro")
    cena(tipo="replay", ger=pula, foco=k1,
         cartao={"numero": 1, "rotulo": "DESCOBERTA", "nome": "PULAR", "cor": CIANO,
                 "stat": f"ALTURA MÉDIA {metros(a0)} → {metros(a1)} m"},
         log=[(f"GER {pula + 1:03d} · ALTURA {metros(a0)} → {metros(a1)} m", CIANO)],
         fala=f"Geração {pula + 1}. A campeã descobre o pulo. <short pause> Genial, né? <long pause> "
              f"A altura média vai de {metros(a0)} para {metros(a1)} metros.")
    marcos.append((pula, "PULA", CIANO))
    # ---------------------------------------------------------------- DESCOBERTA 2: PISAR NA CABEÇA
    d0, d1 = float(hist["m_subiu"][0]), janela(hist["m_subiu"], degrau)
    rd = A.rodada(degrau)
    k2 = A.busca(rd, "primeiro")
    cena(tipo="replay", ger=degrau, foco=k2,
         cartao={"numero": 2, "rotulo": "DESCOBERTA", "nome": "A CABEÇA DO COLEGA", "cor": MAGENTA,
                 "stat": f"SOBEM PISANDO EM OUTRA {round(d0 * 10)} EM 10 → {round(d1 * 10)} EM 10"},
         log=[(f"GER {degrau + 1:03d} · SOBEM PISANDO NA CABEÇA {round(d0 * 10)} → {round(d1 * 10)} EM 10", MAGENTA)],
         fala=f"Geração {degrau + 1}. Aí uma pisa na cabeça da outra. <short pause> Sem pedir licença. <long pause> "
              f"De {NOMES_F[round(d0 * 10)]} para {em_dez(d1)}.")
    marcos.append((degrau, "DEGRAU", MAGENTA))
    # ---------------------------------------------------------------- RE-GANCHO
    g_meio = int(np.clip((degrau + topo_g) // 2, degrau + 1, G - 1))
    cena(tipo="ao_vivo", ger=g_meio,
         log=[(f"GER {g_meio + 1:03d} · A LAVA AINDA GANHA DE MUITA GENTE", AMARELO)],
         carimbo={"texto": "AINDA NÃO", "cor": AMARELO, "em": 0.4, "sub": f"GERAÇÃO {g_meio + 1}"},
         fala="Só que a lava ainda ganha. <short pause> Dá pra chegar no topo? <long pause>")
    # ---------------------------------------------------------------- DESCOBERTA 3: CHEGAR NO TOPO
    t0, t1 = float(hist["m_topo"][0]), janela(hist["m_topo"], topo_g)
    rt = A.rodada(topo_g)
    k3 = A.busca(rt, "primeiro")
    cena(tipo="replay", ger=topo_g, foco=k3,
         cartao={"numero": 3, "rotulo": "DESCOBERTA", "nome": "O TOPO", "cor": VERDE,
                 "stat": f"TORRES COM ALGUÉM NO TOPO {round(t0 * 10)} EM 10 → {round(t1 * 10)} EM 10"},
         log=[(f"GER {topo_g + 1:03d} · ALGUÉM NO TOPO {round(t0 * 10)} → {round(t1 * 10)} EM 10 TORRES", VERDE)],
         fala=f"Geração {topo_g + 1}. Dá! A campeã chega no topo. <long pause> "
              f"Em {NOMES[round(t1 * 10)]} de cada dez torres.")
    marcos.append((topo_g, "TOPO", VERDE))
    # ---------------------------------------------------------------- O TESTE: torre nova
    s_t, _ = duelo(hist, G - 1, ruido=0.25)
    s_n, _ = duelo(hist, G - 1, ruido=1.0)
    itens = [("TORRE DE TREINO", s_t, CIANO), ("TORRE NOVA", s_n, AMARELO)]
    cena(tipo="barras", grupo="duelo", ger=G - 1, itens=itens, titulo="E EM TORRE NOVA?",
         sub="600 torres de cada · salva = 4 ou mais IAs vivas · campeã da última geração", destaque=1, cor_destaque="amarelo", revela=4.0,
         rotulo_destaque=f"▼ {(s_t - s_n) * 100:.0f} pts" if s_t - s_n >= 0.1 else "◀ SEGUROU",
         log=[("TESTE: 600 TORRES COM PLATAFORMAS NOVAS", AMARELO), (f"TORRES SALVAS {pct(s_t)} → {pct(s_n)}", AMARELO)],
         fala=f"Teste: mudei as plataformas de lugar. <short pause> Na torre de treino, a turma se salva "
              f"em {NOMES[round(s_t * 10)]} de cada dez. Na nova, só em {NOMES_F[round(s_n * 10)]}.")
    # ---------------------------------------------------------------- CTA + LAÇO
    rf = A.rodada(G - 1)
    kf = A.busca(rf, "primeiro")
    cena(tipo="replay", ger=G - 1, foco=kf, grupo="fim",
         escolha={"pergunta": "SUBIR OU DECOROU?", "opcoes": [("APRENDEU", VERDE), ("DECOROU", VERMELHO)], "em": 0.2},
         destaques={"aprendeu": VERDE, "decorou": VERMELHO},
         fala="A campeã aprendeu a subir ou só decorou a torre? <short pause> Porque tudo começou quando eu…")

    serie = np.clip(suave(hist["m_vivas"].astype(float)) / N, 0, 1)
    info = {"marca": "VÍDEO NEURAL", "serie": serie, "serie_rotulo": "% DAS IAs QUE ESCAPAM DA LAVA",
            "estilo_voz": ESTILO_VOZ, "marcos": marcos, "rotulo_vivo": f"{n} TORRES",
            "rodape": f"POP {n} · REDE {'-'.join(map(str, Desafio.camadas))} · {G} GERAÇÕES · "
                      "NADA FOI PROGRAMADO: SÓ SELEÇÃO, CRUZAMENTO E MUTAÇÃO"}
    post = (f"{n} torres, lava subindo e {N} IAs em cada uma: na geração 1, {quantas.replace('só ', 'só ')}. 🌋\n"
            f"IA aprendendo sozinha por seleção natural (algoritmo genético). Simulação real: {n} torres de {N} IAs, "
            f"{G} gerações, nenhum número inventado.\n"
            "Manda pra quem sobe em cima dos outros pra não se queimar 👇\n\n"
            "#inteligenciaartificial #ia #algoritmogenetico #curiosidades #tecnologia")
    ev["duelo"] = {"treino": s_t, "novo": s_n}
    return cenas, info, post, ev
