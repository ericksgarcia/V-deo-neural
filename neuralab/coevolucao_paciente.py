"""Co-evolução Paciente Zero: cérebro saudável x cérebro do vírus, só melhoram um contra o outro.

O vídeo re-simula as cidades da vitrine com a mesma função (`cidades`) e a mesma semente do treino.
"""
import numpy as np

from .desafios import paciente as P
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(P.CAMADAS)


def cidades(gs, gv, isa, ivi, semente, gravar=False):
    """Joga len(isa) cidades: cérebro saudável gs[isa[k]] contra cérebro do vírus gv[ivi[k]]."""
    jogo = P.Cidade(len(isa), np.random.default_rng(semente))
    ps, pv = ARQ.desempacota(gs[isa]), ARQ.desempacota(gv[ivi])
    reg = {"p": [], "inf": [], "ativ_s": [], "ativ_v": []}
    for _ in range(P.PASSOS):
        obs = jogo.observa()
        a_s, at_s = ARQ.avalia(ps, obs)
        a_v, at_v = ARQ.avalia(pv, obs)
        if gravar:
            reg["ativ_s"].append(np.concatenate([x[:, 1] for x in at_s], 1))      # um saudável (agente 1)
            reg["ativ_v"].append(np.concatenate([x[:, 0] for x in at_v], 1))      # o paciente zero (agente 0)
            reg["p"].append(jogo.p.copy())
            reg["inf"].append(jogo.inf.copy())
        jogo.passo(a_s, a_v)
    jogo.finaliza()
    if gravar:
        reg = {c: np.stack(v, 1) for c, v in reg.items()}      # (P, T, A, ...)
    return jogo, reg


def metricas(j, n=None):
    """Comportamentos medidos nas primeiras `n` cidades (a vitrine); o roteiro só conta o que aparece aqui."""
    k = j.k
    n = n or j.n
    s = slice(0, n)
    curva = j.curva[s]
    final = curva[:, -1] / P.A
    metade = (curva >= P.A / 2)
    t50 = np.where(metade.any(1), metade.argmax(1), k) * P.DT
    return {"infectados": float(final.mean()), "saudaveis": float(1 - final.mean()),
            "t50": float(t50.mean()), "metade": float(metade.any(1).mean()),
            "todos": float((curva[:, -1] == P.A).mean()),
            "nn": float((j.s_nn[s] / k).mean()), "dist_inf": float((j.s_inf_d[s] / k).mean()),
            "parede": float((j.s_par[s] / k).mean()), "aglo": float((j.s_aglo[s] / k).mean())}


def campeao_sau(hist, g, rodadas=6, semente=4242):
    """Índice do melhor cérebro saudável da geração g: cada um joga `rodadas` cidades novas contra os vírus da mesma geração
    e fica o que mais saudáveis mantém no fim. Linhagem real do algoritmo (elitismo), corpo muda a cada geração."""
    cache = hist.setdefault("_camp", {}) if isinstance(hist, dict) else {}
    if g not in cache:
        gs, gv = hist["sau"][g], hist["vir"][g]
        pop = len(gs)
        rng = np.random.default_rng(semente + g)
        isa, ivi = np.repeat(np.arange(pop), rodadas), rng.integers(0, pop, pop * rodadas)
        j, _ = cidades(gs, gv, isa, ivi, semente + g)
        cache[g] = int(np.argmax((1 - j.curva[:, -1] / P.A).reshape(pop, rodadas).mean(1)))
    return cache[g]


def vitrine(pop, semente):
    """As cidades que o vídeo mostra e as métricas medem: saudável i x vírus sorteado."""
    return np.arange(pop), np.random.default_rng(semente).permutation(pop)


def treina(geracoes=100, pop=30, jogos=2, semente=3, log=print):
    rng = np.random.default_rng(semente)
    gs, gv = ARQ.aleatoria(pop, rng), ARQ.aleatoria(pop, rng)
    hist = {"sau": [], "vir": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        isa, ivi = vitrine(pop, sem)
        # a vitrine (as primeiras `pop` cidades) + (jogos-1) pareamentos extras, tudo num lote só
        isa_t = np.concatenate([isa] + [np.arange(pop)] * (jogos - 1))
        ivi_t = np.concatenate([ivi] + [rng.permutation(pop) for _ in range(jogos - 1)])
        jt, _ = cidades(gs, gv, isa_t, ivi_t, sem)
        m = metricas(jt, pop)
        hist["sau"].append(gs.copy())
        hist["vir"].append(gv.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        fs, fv = jt.aptidoes()
        apt_s, apt_v = np.zeros(pop), np.zeros(pop)
        np.add.at(apt_s, isa_t, fs)
        np.add.at(apt_v, ivi_t, fv)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  saudáveis no fim {m['saudaveis']:.0%}  metade infectada {m['metade']:.0%} "
                f"(t50 {m['t50']:.1f}s) | vizinho {m['nn']:.2f} m  dist. do infectado {m['dist_inf']:.1f} m  "
                f"parede {m['parede']:.0%}  aglom. {m['aglo']:.0%}")
        gs = proxima_geracao(gs, apt_s, rng)
        gv = proxima_geracao(gv, apt_v, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"sau": np.array(hist["sau"]), "vir": np.array(hist["vir"]), "semente": np.array(hist["semente"]),
            **{"m_" + k: v for k, v in met.items()}}


if __name__ == "__main__":      # treino avulso: python -m neuralab.coevolucao_paciente GERACOES SEMENTE
    import os
    import sys
    G, s = int(sys.argv[1]), int(sys.argv[2])
    os.makedirs(".cache", exist_ok=True)
    np.savez_compressed(os.path.join(".cache", f"paciente_{G}_{s}.npz"), **treina(G, semente=s, log=lambda x: print(x, flush=True)))
