"""Treino Cão Pastor: só o cérebro do cão evolui; ovelhas e curral são programados."""
import numpy as np

from .desafios import pastor as P
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(P.CAMADAS)


def cidades(genes, idx, semente, gravar=False):
    jogo = P.Cidade(len(idx), np.random.default_rng(semente))
    ps = ARQ.desempacota(genes[idx])
    reg = {"c": [], "o": [], "ativ": []}
    for _ in range(P.PASSOS):
        obs = jogo.observa()
        a, at = ARQ.avalia(ps, obs)
        if gravar:
            reg["ativ"].append(np.concatenate(list(at), 1))
            reg["c"].append(jogo.c.copy())
            reg["o"].append(jogo.o.copy())
        jogo.passo(a)
    if gravar:
        reg = {k: np.stack(v, 1) for k, v in reg.items()}
    return jogo, reg


def metricas(j, n=None):
    s = slice(0, n or j.n)
    fora = np.maximum(j.s_fora[s], 1)
    dentro = j.dentro()[s].sum(1)
    return {"pen": float(dentro.mean() / P.N), "zero": float((dentro == 0).mean()), "todas": float((dentro == P.N).mean()),
            "atras": float((j.s_atras[s] / fora).mean()), "dist": float((j.s_dist[s] / fora).mean()),
            "perto": float((j.s_perto[s] / fora).mean()), "esp": float(j.s_esp[s].mean())}


def campeao(hist, g, rodadas=6, semente=4242):
    cache = hist.setdefault("_camp", {}) if isinstance(hist, dict) else {}
    if g not in cache:
        genes = hist["genes"][g]
        pop = len(genes)
        j, _ = cidades(genes, np.repeat(np.arange(pop), rodadas), semente + g)
        cache[g] = int(np.argmax(j.aptidoes().reshape(pop, rodadas).mean(1)))
    return cache[g]


def treina(geracoes=100, pop=60, jogos=2, semente=3, log=print):
    rng = np.random.default_rng(semente)
    genes = ARQ.aleatoria(pop, rng)
    hist = {"genes": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        idx = np.concatenate([np.arange(pop)] * jogos)
        jt, _ = cidades(genes, idx, sem)
        m = metricas(jt, pop)
        hist["genes"].append(genes.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        apt = jt.aptidoes().reshape(jogos, pop).mean(0)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  no curral {m['pen']:.0%}  zero {m['zero']:.0%}  atrás {m['atras']:.0%}  dist {m['dist']:.1f}  perto {m['perto']:.0%}  esp {m['esp']:.1f}")
        genes = proxima_geracao(genes, apt, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"genes": np.array(hist["genes"]), "semente": np.array(hist["semente"]), **{"m_" + k: v for k, v in met.items()}}


if __name__ == "__main__":
    import os
    import sys
    G, s = int(sys.argv[1]), int(sys.argv[2])
    os.makedirs(".cache", exist_ok=True)
    np.savez_compressed(os.path.join(".cache", f"pastor_{G}_{s}.npz"), **treina(G, semente=s, log=lambda x: print(x, flush=True)))
