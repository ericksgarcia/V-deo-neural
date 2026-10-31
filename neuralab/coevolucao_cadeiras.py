"""Treino da Dança das Cadeiras: um cérebro por indivíduo, usado pelas 12 IAs da roda (população única)."""
import numpy as np

from .desafios import cadeiras as K
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(K.CAMADAS)


def rodadas(genes, idx, semente, gravar=False):
    jogo = K.Rodada(len(idx), np.random.default_rng(semente))
    ps = ARQ.desempacota(genes[idx])
    reg = {"p": [], "senta": [], "ativ": []}
    for _ in range(K.PASSOS):
        obs = jogo.observa()
        a, at = ARQ.avalia(ps, obs)
        if gravar:
            reg["p"].append(jogo.p.copy())
            reg["senta"].append(jogo.senta.copy())
            reg["ativ"].append(np.concatenate([x[:, 0] for x in at], 1))
        jogo.passo(a)
    jogo.finaliza()
    if gravar:
        reg = {k: np.stack(v, 1) for k, v in reg.items()}
    return jogo, reg


def metricas(j, n=None):
    s = slice(0, n or j.n)
    ch = j.cheias()[s]
    nm, nc = max(j.n_mus, 1), max(j.n_corre, 1)
    return {"cheias": float(ch.mean() / K.C), "perfeita": float((ch == K.C).mean()), "colado": float(j.m["colado"][s].mean() / nm),
            "vel_mus": float(j.m["vel_mus"][s].mean() / nm), "disputa": float(j.m["disputa"][s].mean()),
            "toque": float(j.m["toque"][s].mean() / nc),
            "giro": float((np.abs(j.m["gsum"][s]) / np.maximum(j.m["gabs"][s], 1e-6)).mean()),
            "tult": float(np.nanmax(np.where(np.isnan(j.t_senta), np.nan, j.t_senta), 1)[s][~np.isnan(np.nanmax(np.where(np.isnan(j.t_senta), -1, j.t_senta), 1)[s])].mean()) if False else float(np.where(np.isnan(j.t_senta), 0, j.t_senta).max(1)[s].mean()), "ruim": float((ch <= K.C // 2).mean())}


def campeao(hist, g, rodadas_=6, semente=4242):
    cache = hist.setdefault("_camp", {}) if isinstance(hist, dict) else {}
    if g not in cache:
        genes = hist["genes"][g]
        pop = len(genes)
        j, _ = rodadas(genes, np.repeat(np.arange(pop), rodadas_), semente + g)
        cache[g] = int(np.argmax(j.aptidoes().reshape(pop, rodadas_).mean(1)))
    return cache[g]


def treina(geracoes=100, pop=60, jogos=3, semente=3, log=print):
    rng = np.random.default_rng(semente)
    genes = ARQ.aleatoria(pop, rng)
    hist = {"genes": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        idx = np.concatenate([np.arange(pop)] * jogos)
        jt, _ = rodadas(genes, idx, sem)
        m = metricas(jt, pop)
        hist["genes"].append(genes.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        apt = jt.aptidoes().reshape(jogos, pop).mean(0)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  cheias {m['cheias']:.0%}  perfeita {m['perfeita']:.0%}  colado {m['colado']:.0%}  vel_mus {m['vel_mus']:.1f}  disputa {m['disputa']:.2f}  toque {m['toque']:.2f}  giro {m['giro']:.2f}  tult {m['tult']:.1f}")
        genes = proxima_geracao(genes, apt, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"genes": np.array(hist["genes"]), "semente": np.array(hist["semente"]), **{"m_" + k: v for k, v in met.items()}}


if __name__ == "__main__":
    import os
    import sys
    G, s = int(sys.argv[1]), int(sys.argv[2])
    os.makedirs(".cache", exist_ok=True)
    np.savez_compressed(os.path.join(".cache", f"cadeiras_{G}_{s}.npz"), **treina(G, semente=s, log=lambda x: print(x, flush=True)))
