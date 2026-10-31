"""Treino Fuga com Cobertura: só o cérebro azul evolui; torreta e blocos são programados.

O vídeo re-simula as cidades da vitrine com a mesma função (`cidades`) e a mesma semente do treino.
"""
import numpy as np

from .desafios import fuga as F
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(F.CAMADAS)


def cidades(genes, idx, semente, gravar=False):
    """Joga len(idx) cidades: o cérebro genes[idx[k]] controla os 12 azuis da cidade k."""
    jogo = F.Cidade(len(idx), np.random.default_rng(semente))
    ps = ARQ.desempacota(genes[idx])
    reg = {"p": [], "vivo": [], "chegou": [], "bp": [], "bvivo": [], "bx": [], "ativ": []}
    for _ in range(F.PASSOS):
        obs = jogo.observa()
        a, at = ARQ.avalia(ps, obs)
        if gravar:
            reg["ativ"].append(np.concatenate([x[:, 0] for x in at], 1))
            reg["p"].append(jogo.p.copy())
            reg["vivo"].append(jogo.vivo.copy())
            reg["chegou"].append(jogo.chegou.copy())
            reg["bp"].append(jogo.bp.copy())
            reg["bvivo"].append(jogo.bvivo.copy())
            reg["bx"].append(jogo.bx.copy())
        jogo.passo(a)
    jogo.finaliza()
    if gravar:
        reg = {c: np.stack(v, 1) for c, v in reg.items()}
    return jogo, reg


def metricas(j, n=None):
    k = j.k
    s = slice(0, n or j.n)
    zona = np.maximum(j.s_zona[s], 1e-6)
    return {"chegou": float(j.chegou[s].mean()), "vivos": float(j.vivo[s].mean()),
            "atras": float((j.s_atras[s] / zona).mean()), "lat": float((j.s_lat[s] / k).mean()),
            "ymax": float(j.ymax[s].mean()), "zero": float((j.chegou[s].sum(1) == 0).mean())}


def campeao(hist, g, rodadas=6, semente=4242):
    """Índice do melhor cérebro da geração g: cada um joga `rodadas` cidades novas; vence quem mais azuis faz chegar."""
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
            log(f"ger {g + 1:3d}  chegaram {m['chegou']:.0%}  vivos {m['vivos']:.0%}  atrás do bloco {m['atras']:.0%}  "
                f"lateral {m['lat']:.2f} m/s  nenhuma chegou {m['zero']:.0%}")
        genes = proxima_geracao(genes, apt, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"genes": np.array(hist["genes"]), "semente": np.array(hist["semente"]), **{"m_" + k: v for k, v in met.items()}}


if __name__ == "__main__":      # treino avulso: python -m neuralab.coevolucao_fuga GERACOES SEMENTE
    import os
    import sys
    G, s = int(sys.argv[1]), int(sys.argv[2])
    os.makedirs(".cache", exist_ok=True)
    np.savez_compressed(os.path.join(".cache", f"fuga_{G}_{s}.npz"), **treina(G, semente=s, log=lambda x: print(x, flush=True)))
