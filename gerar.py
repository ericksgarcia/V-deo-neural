#!/usr/bin/env python3
"""Gera um episódio: treina a IA de verdade e renderiza o vídeo vertical narrado.

Exemplos:
  python gerar.py penalti                  # episódio final 1080x1920 com narração
  python gerar.py foguete --rascunho       # prévia rápida 540x960
  python gerar.py baliza --sem-voz         # só legendas (sem chamar a API de voz)
  python gerar.py penalti --so-roteiro     # imprime o roteiro e os fatos, sem renderizar

Depois de gerar, rode os analistas (ver README) sobre a pasta saida/<episodio>_analise/.
"""
import argparse
import os

import numpy as np

from neuralab.video import Video

# Para um desafio novo: uma linha aqui + adaptador + desafio + roteiro (ver README).
# gera = gerações; pop = tamanho da população; ep = número do arquivo; nota/monta = módulo de roteiro
CFG = {
    "penalti": dict(gera=300, ep=4),
    "foguete": dict(gera=160, ep=1, roteiro="simples"),
    "baliza": dict(gera=260, ep=2, roteiro="baliza"),
    "andador": dict(gera=70, ep=3, roteiro="andador", nota="baliza"),
    "drone": dict(gera=340, ep=3, roteiro="drone", sementes="5,11,17"),
    "corrida": dict(gera=240, ep=3, roteiro="corrida", pop=160),
    "sumo": dict(gera=186, ep=5),
    "policia": dict(gera=250, ep=5),
    "cabo": dict(gera=150, ep=9),
    "cruzamento": dict(gera=300, ep=5, roteiro="cruzamento"),
}
DESAFIOS = tuple(CFG)
GERACOES = {k: v["gera"] for k, v in CFG.items()}
EPISODIO = {k: v["ep"] for k, v in CFG.items()}


def treino_penalti(G, sementes):
    from neuralab.coevolucao import treina
    from neuralab.roteiros.penalti import eventos
    melhor = None
    for s in sementes:
        arq = os.path.join(".cache", f"penalti_{G}_{s}.npz")
        if os.path.exists(arq):
            hist = dict(np.load(arq))
        else:
            print(f"treinando pênalti (semente {s}, {G} gerações)…")
            hist = treina(G, semente=s, log=None)
            np.savez_compressed(arq, **hist)
        ev = eventos(hist)
        nota = sum(ev[k] is not None for k in ("mira", "paciente", "leitura", "finta")) + 0.1 * ev["ciclos"]
        print(f"  semente {s}: acontecimentos detectados {nota:.1f}")
        if melhor is None or nota > melhor[0]:
            melhor = (nota, s, hist)
    return melhor[1], melhor[2]


def treino_sumo(sementes):
    from neuralab.coevolucao_sumo import FASES, treina
    from neuralab.roteiros.sumo import nota_historia
    melhor = None
    for s in sementes:
        arq = os.path.join(".cache", f"sumo_{s}.npz")
        if os.path.exists(arq):
            hist = dict(np.load(arq))
        else:
            print(f"treinando sumô (semente {s}, {sum(f[2] for f in FASES)} gerações em fases)…")
            hist = treina(semente=s, log=None)
            np.savez_compressed(arq, **hist)
        nota = nota_historia(hist)
        print(f"  semente {s}: nota da história {nota:.1f}")
        if melhor is None or nota > melhor[0]:
            melhor = (nota, s, hist)
    return melhor[1], melhor[2]


def treino_cabo(sementes):
    from neuralab.coevolucao_cabo import FASES, treina
    from neuralab.roteiros.cabo import nota_historia
    melhor = None
    for s in sementes:
        arq = os.path.join(".cache", f"cabo_{s}.npz")
        if os.path.exists(arq):
            hist = dict(np.load(arq))
        else:
            print(f"treinando cabo de guerra (semente {s}, {sum(f[2] for f in FASES)} gerações em fases)…")
            hist = treina(semente=s, log=print)
            np.savez_compressed(arq, **hist)
        nota = nota_historia(hist)
        print(f"  semente {s}: nota da história {nota:.1f}")
        if melhor is None or nota > melhor[0]:
            melhor = (nota, s, hist)
    return melhor[1], melhor[2]


def treino_policia(G, sementes):
    from neuralab.coevolucao_policia import treina
    from neuralab.roteiros.policia import nota_historia
    melhor = None
    for s in sementes:
        arq = os.path.join(".cache", f"policia_{G}_{s}.npz")
        if os.path.exists(arq):
            hist = dict(np.load(arq))
        else:
            print(f"treinando polícia e ladrão (semente {s}, {G} gerações)…")
            hist = treina(G, semente=s, log=None)
            np.savez_compressed(arq, **hist)
        nota = nota_historia(hist)
        print(f"  semente {s}: nota da história {nota:.2f}")
        if melhor is None or nota > melhor[0]:
            melhor = (nota, s, hist)
    return melhor[1], melhor[2]


def treino_simples(nome, G, sementes):
    from neuralab.desafios import DESAFIOS as D
    from neuralab.evolucao import treina
    from neuralab.roteiros.simples import nota_historia
    cfg = CFG[nome]
    if cfg["roteiro"] != "simples":
        import importlib
        nota_historia = importlib.import_module(f"neuralab.roteiros.{cfg.get('nota', cfg['roteiro'])}").nota_historia
    pop = cfg.get("pop", 150)
    melhor = None
    for s in sementes:
        arq = os.path.join(".cache", f"treino_{nome}_{G}_{pop}_{s}_v3.npz")
        if os.path.exists(arq):
            hist = dict(np.load(arq))
        else:
            print(f"treinando {nome} (semente {s}, {G} gerações)…")
            hist = treina(D[nome], G, pop, s, log=None)
            np.savez_compressed(arq, **hist)
        nota = nota_historia(hist)
        print(f"  semente {s}: final {hist["sucessos"].max()}/{len(hist["genes"][0])}, nota da história {nota:.2f}")
        if melhor is None or nota > melhor[0]:
            melhor = (nota, s, hist)
    return melhor[1], melhor[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("desafio", choices=DESAFIOS)
    ap.add_argument("--geracoes", type=int)
    ap.add_argument("--sementes", default=None, help="ex.: 3,5,7 — testa várias e fica com a melhor história")
    ap.add_argument("--voz", default="Charon", help="voz do Gemini TTS (Charon, Achird, Fenrir, Orus, Kore...)")
    ap.add_argument("--sem-voz", action="store_true")
    ap.add_argument("--rascunho", action="store_true", help="metade da resolução, para revisar rápido")
    ap.add_argument("--so-roteiro", action="store_true")
    ap.add_argument("--so-voz", action="store_true",
                    help="gera/carrega só a narração (1 requisição, depois cache) e mostra o relatório de ritmo")
    ap.add_argument("--ritmo", type=float, default=3.4, help="teto de palavras/s enquanto fala, sem contar pausas (ajuste local, sem API)")
    ap.add_argument("--saida", default="saida")
    a = ap.parse_args()
    os.makedirs(".cache", exist_ok=True)
    os.makedirs(a.saida, exist_ok=True)
    G = a.geracoes or GERACOES[a.desafio]

    if a.desafio == "sumo":
        from neuralab.adaptadores.sumo import Sumo
        from neuralab.roteiros.sumo import monta
        s, hist = treino_sumo([int(x) for x in (a.sementes or "10").split(",")])
        A = Sumo(hist)
        cenas, info, post, _ = monta(hist, A)
    elif a.desafio == "cabo":
        from neuralab.adaptadores.cabo import Cabo
        from neuralab.roteiros.cabo import monta
        s, hist = treino_cabo([int(x) for x in (a.sementes or "3").split(",")])
        A = Cabo(hist)
        cenas, info, post, _ = monta(hist, A)
    elif a.desafio == "penalti":
        from neuralab.adaptadores.penalti import Penalti
        from neuralab.roteiros.penalti import monta
        sementes = [int(x) for x in (a.sementes or "3").split(",")]
        s, hist = treino_penalti(G, sementes)
        A = Penalti(hist)
        cenas, info, post, _ = monta(hist, A)
    elif a.desafio == "policia":
        from neuralab.adaptadores.policia import Policia
        from neuralab.roteiros.policia import monta
        sementes = [int(x) for x in (a.sementes or "3,5,7").split(",")]
        s, hist = treino_policia(G, sementes)
        A = Policia(hist)
        cenas, info, post, _ = monta(hist, A)
    else:
        import importlib
        cfg = CFG[a.desafio]
        classe = {"foguete": "Foguete", "baliza": "Baliza", "andador": "Andador", "drone": "Drone", "corrida": "Corrida", "cruzamento": "Cruzamento"}[a.desafio]
        Adap = getattr(importlib.import_module(f"neuralab.adaptadores.{a.desafio}"), classe)
        sementes = [int(x) for x in (a.sementes or cfg.get("sementes", "3,5,7,11")).split(",")]
        s, hist = treino_simples(a.desafio, G, sementes)
        A = Adap(hist)
        monta = importlib.import_module(f"neuralab.roteiros.{cfg['roteiro']}").monta
        if cfg["roteiro"] == "simples":
            cenas, info, post, _ = monta(a.desafio, hist, A)
        else:
            cenas, info, post, _ = monta(hist, A)
    print(f"usando semente {s}\nroteiro:")
    for k, c in enumerate(cenas):
        cartao = f"  [CARTÃO {c['cartao']['numero']}]" if c.get("cartao") else ""
        print(f"  {k:2d} {c['tipo']:<8} {c['fala']}{cartao}")
    print("legenda:")
    print(post)
    if a.so_roteiro:
        return
    nome = f"ep{EPISODIO[a.desafio]:02d}_{a.desafio}{'_rascunho' if a.rascunho else ''}"
    with open(os.path.join(a.saida, nome + "_legenda.txt"), "w") as f:
        f.write(post + "\n")
    v = Video(A, cenas, info, voz=a.voz, escala=0.5 if a.rascunho else 1.0, narrar=not a.sem_voz, ritmo=a.ritmo)
    if a.so_voz:
        v.prepara()
        for k, c in enumerate(v.cenas):
            print(f"  {k:2d} {c['dur']:5.1f}s  {c['fala']}")
        print(f"duração prevista: {v.dur:.1f}s")
        return
    out = v.renderiza(os.path.join(a.saida, nome + ".mp4"))
    print(f"pronto: {out}  ({v.dur:.1f}s)\nanálise: {os.path.join(a.saida, nome + '_analise')}/")


if __name__ == "__main__":
    main()
