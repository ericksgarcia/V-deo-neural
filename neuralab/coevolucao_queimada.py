"""Co-evolução da Queimada: azuis x vermelhas (duas populações; cada indivíduo é UM cérebro para os 3 corpos do time).

Cada geração: a vitrine (pop partidas, cérebro i azul contra um vermelho sorteado, mesma semente que o vídeo re-simula) e o treino
(`jogos` partidas por indivíduo, parte contra o museu de campeões passados para a evolução não girar em círculos).
Currículo (§16.2): nas primeiras `fase1` gerações os adversários andam mais devagar (`lento`) e o ponto por acerto vale mais.
"""
import numpy as np

from .desafios import queimada as Q
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(Q.CAMADAS)


def partidas(ga, gb, ia, ib, semente, gravar=False, lento=0.0):
    jogo = Q.Queimada(len(ia), np.random.default_rng(semente), lento=lento)
    pa, pb = ARQ.desempacota(ga[ia]), ARQ.desempacota(gb[ib])
    reg = {"pa": [], "pb": [], "vivo": [], "bp": [], "est": [], "dono": [], "ativ_a": [], "ativ_b": []}
    for k in range(Q.PASSOS):
        sa, aa = ARQ.avalia(pa, jogo.obs(0))
        sb, ab = ARQ.avalia(pb, jogo.obs(1))
        if gravar:
            reg["pa"].append(jogo.p[0].copy())
            reg["pb"].append(jogo.p[1].copy())
            reg["vivo"].append(jogo.vivo.transpose(1, 0, 2).copy())
            reg["bp"].append(jogo.bp.copy())
            reg["est"].append(jogo.estado.copy())
            reg["dono"].append(np.stack([jogo.dono_t, jogo.dono_i], 1))
            reg["ativ_a"].append(np.concatenate([x[:, 0] for x in aa], 1))
            reg["ativ_b"].append(np.concatenate([x[:, 0] for x in ab], 1))
        jogo.passo(sa, sb)
        if jogo.acabou():
            break
    if gravar:
        reg = {c: np.stack(v, 1) for c, v in reg.items()}
    return jogo, reg


def metricas(j):
    r = j.resultado()
    arr = j.arremessos
    tot_arr = np.maximum(arr.sum(), 1)
    hits = j.acertos.sum()
    passos = np.maximum(j.t_fim, 1)
    lp = np.maximum(j.lider_passos, 1)
    return {"azul_vence": float((r > 0).mean()), "verm_vence": float((r < 0).mean()), "empate": float((r == 0).mean()),
            "arr": float(arr.sum() / j.n / 2), "acerto": float(hits / tot_arr), "hits": float(hits / j.n),
            "seg": float((j.seg_passos.sum(0) / passos).mean()),
            "cera": float(j.seg_lider.sum() / max(j.lider_passos.sum(), 1)),
            "arr_lider": float(j.arr_lider.sum() / max(j.lider_passos.sum() / 20.0, 1)),
            "zero": float((j.acertos.sum(0) == 0).mean()),
            "dist": float(np.mean(j.dist_arr[0] + j.dist_arr[1])) if (j.dist_arr[0] or j.dist_arr[1]) else 0.0,
            "vivos": float(j.vivos()[0].mean() / 3 + j.vivos()[1].mean() / 3) / 2}


def treina(geracoes=120, pop=60, jogos=4, semente=3, log=print, fase1=20, museu_cada=8, do_museu=1):
    rng = np.random.default_rng(semente)
    ga, gb = ARQ.aleatoria(pop, rng), ARQ.aleatoria(pop, rng)
    mus_a, mus_b = [], []
    hist = {"az": [], "vm": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        iv = np.arange(pop)
        ib = np.random.default_rng(sem).permutation(pop)
        jv, _ = partidas(ga, gb, iv, ib, sem)
        m = metricas(jv)
        hist["az"].append(ga.copy())
        hist["vm"].append(gb.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        lento = 0.45 if g < fase1 else 0.0
        acerto = 1.6 if g < fase1 else 1.0
        ia = np.repeat(np.arange(pop), jogos)
        ib2 = np.concatenate([rng.permutation(pop) for _ in range(jogos)])
        pool_b, ib3 = gb, ib2
        if mus_b:
            todos = np.concatenate([gb] + mus_b)
            blocos = np.arange(len(ia)) % jogos >= jogos - do_museu
            ib3 = np.where(blocos, pop + rng.integers(0, len(todos) - pop, len(ia)), ib2)
            pool_b = todos
        j1, _ = partidas(ga, pool_b, ia, ib3, sem + 1, lento=lento)
        fa, fb = j1.aptidoes(acerto)
        apt_a = np.zeros(pop)
        np.add.at(apt_a, ia, fa)
        apt_b = np.zeros(pop)
        at = ib3 < pop
        np.add.at(apt_b, ib3[at], fb[at])
        if mus_a:                                         # vermelhos atuais x azuis do museu
            todos_a = np.concatenate([ga] + mus_a)
            ib4 = np.repeat(np.arange(pop), do_museu)
            ia4 = pop + rng.integers(0, len(todos_a) - pop, pop * do_museu)
            j4, _ = partidas(todos_a, gb, ia4, ib4, sem + 2, lento=0.0)
            _, fb4 = j4.aptidoes(acerto)
            np.add.at(apt_b, ib4, fb4)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d} az {m['azul_vence']:.0%} vm {m['verm_vence']:.0%} emp {m['empate']:.0%} arr {m['arr']:.1f} "
                f"acerto {m['acerto']:.0%} hits {m['hits']:.2f} seg {m['seg']:.0%} cera {m['cera']:.0%} dist {m['dist']:.1f}")
        if g % museu_cada == museu_cada - 1:
            mus_a.append(ga[np.argsort(-apt_a)[:4]].copy())
            mus_b.append(gb[np.argsort(-apt_b)[:4]].copy())
        ga = proxima_geracao(ga, apt_a, rng)
        gb = proxima_geracao(gb, apt_b, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"az": np.array(hist["az"]), "vm": np.array(hist["vm"]), "semente": np.array(hist["semente"]),
            **{"m_" + k: v for k, v in met.items()}}


if __name__ == "__main__":      # python -m neuralab.coevolucao_queimada GERACOES SEMENTE
    import os
    import sys
    G, s = int(sys.argv[1]), int(sys.argv[2])
    os.makedirs(".cache", exist_ok=True)
    out = treina(G, semente=s, log=lambda x: print(x, flush=True))
    np.savez_compressed(os.path.join(".cache", f"queimada_{G}_{s}.npz"), **out)
