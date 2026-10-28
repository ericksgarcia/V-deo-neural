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

DESAFIOS = ("penalti", "foguete", "baliza", "andador")
GERACOES = {"penalti": 300, "foguete": 160, "baliza": 260, "andador": 70}
EPISODIO = {"foguete": 1, "baliza": 2, "penalti": 4, "andador": 3}


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


def treino_simples(nome, G, sementes):
    from neuralab.desafios import DESAFIOS as D
    from neuralab.evolucao import treina
    from neuralab.roteiros.simples import nota_historia
    if nome in ("baliza", "andador"):
        from neuralab.roteiros.baliza import nota_historia
    melhor = None
    for s in sementes:
        arq = os.path.join(".cache", f"treino_{nome}_{G}_150_{s}_v2.npz")
        if os.path.exists(arq):
            hist = dict(np.load(arq))
        else:
            print(f"treinando {nome} (semente {s}, {G} gerações)…")
            hist = treina(D[nome], G, 150, s, log=None)
            np.savez_compressed(arq, **hist)
        nota = nota_historia(hist)
        print(f"  semente {s}: final {hist['sucessos'].max()}/150, nota da história {nota:.2f}")
        if melhor is None or nota > melhor[0]:
            melhor = (nota, s, hist)
    return melhor[1], melhor[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("desafio", choices=DESAFIOS)
    ap.add_argument("--geracoes", type=int)
    ap.add_argument("--sementes", default=None, help="ex.: 3,5,7 — testa várias e fica com a melhor história")
    ap.add_argument("--voz", default="Charon", help="voz do Gemini TTS (Charon, Fenrir, Orus, Kore...)")
    ap.add_argument("--sem-voz", action="store_true")
    ap.add_argument("--rascunho", action="store_true", help="metade da resolução, para revisar rápido")
    ap.add_argument("--so-roteiro", action="store_true")
    ap.add_argument("--so-voz", action="store_true",
                    help="gera/carrega só a narração (1 requisição, depois cache) e mostra o relatório de ritmo")
    ap.add_argument("--ritmo", type=float, default=4.0, help="teto de palavras/s enquanto fala, sem contar pausas (ajuste local, sem API)")
    ap.add_argument("--saida", default="saida")
    a = ap.parse_args()
    os.makedirs(".cache", exist_ok=True)
    os.makedirs(a.saida, exist_ok=True)
    G = a.geracoes or GERACOES[a.desafio]

    if a.desafio == "penalti":
        from neuralab.adaptadores.penalti import Penalti
        from neuralab.roteiros.penalti import monta
        sementes = [int(x) for x in (a.sementes or "3").split(",")]
        s, hist = treino_penalti(G, sementes)
        A = Penalti(hist)
        cenas, info, post, _ = monta(hist, A)
    else:
        from neuralab.adaptadores.andador import Andador
        from neuralab.adaptadores.baliza import Baliza
        from neuralab.adaptadores.foguete import Foguete
        sementes = [int(x) for x in (a.sementes or "3,5,7,11").split(",")]
        s, hist = treino_simples(a.desafio, G, sementes)
        A = {"foguete": Foguete, "baliza": Baliza, "andador": Andador}[a.desafio](hist)
        if a.desafio == "andador":
            from neuralab.roteiros.andador import monta
            cenas, info, post, _ = monta(hist, A)
        elif a.desafio == "baliza":
            from neuralab.roteiros.baliza import monta
            cenas, info, post, _ = monta(hist, A)
        else:
            from neuralab.roteiros.simples import monta
            cenas, info, post, _ = monta(a.desafio, hist, A)
    print(f"usando semente {s}\nroteiro:")
    for k, c in enumerate(cenas):
        print(f"  {k:2d} {c['tipo']:<8} {c['fala']}")
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
