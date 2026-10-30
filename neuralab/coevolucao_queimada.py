"""Co-evolução da queimada: azul x vermelho (duas populações, um cérebro por time, três corpos cada).

Cada indivíduo joga `jogos` partidas; parte delas é contra o "museu" (melhores de gerações passadas). O vídeo re-simula
as partidas da vitrine com a mesma regra e a mesma semente do treino.
"""
import numpy as np

from .desafios import queimada as Q
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(Q.CAM)


def partidas(ga, gb, ia, ib, semente, gravar=False):
    """Joga len(ia) partidas: azuis ga[ia[k]] contra vermelhos gb[ib[k]]."""
    jogo = Q.Queimada(len(ia), np.random.default_rng(semente))
    pa, pb = ARQ.desempacota(ga[ia]), ARQ.desempacota(gb[ib])
    reg = {"P": [], "ang": [], "vivo": [], "bpos": [], "bst": [], "bdono": [], "ativ_a": [], "ativ_b": []}
    for k in range(Q.PASSOS):
        x = jogo.obs()
        sa, aa = ARQ.avalia(pa, x[:, :3])
        sb, ab = ARQ.avalia(pb, x[:, 3:])
        jogo.passo(sa, sb, k)
        if gravar:
            reg["P"].append(jogo.P.copy())
            reg["ang"].append(jogo.ang.copy())
            reg["vivo"].append(jogo.vivo.copy())
            reg["bpos"].append(jogo.bpos.copy())
            reg["bst"].append(jogo.bst.copy())
            reg["bdono"].append(jogo.bdono.copy())
            reg["ativ_a"].append(np.concatenate([q[:, 0] for q in aa], 1))
            reg["ativ_b"].append(np.concatenate([q[:, 0] for q in ab], 1))
        if jogo.acabou():
            break
    jogo.finaliza(k)
    if gravar:
        reg = {c: np.stack(v, 1) for c, v in reg.items()}
    return jogo, reg


def metricas(j):
    """Comportamentos medidos (o roteiro só conta o que aparece aqui). a = azul, b = vermelho."""
    pl = j.placar()
    arr = np.maximum(j.arremessos, 1)
    dur = (j.t_ult + 1) * Q.DT
    tempo = np.maximum(j.t_ult + 1, 1)[:, None]
    m = {"pegos_a": float((3 - pl[:, 0]).mean()), "pegos_b": float((3 - pl[:, 1]).mean()),
         "vit_a": float((pl[:, 0] > pl[:, 1]).mean()), "vit_b": float((pl[:, 1] > pl[:, 0]).mean()),
         "empate": float((pl[:, 0] == pl[:, 1]).mean()),
         "zero": float(((pl == 0).any(1)).mean()),
         "arr_a": float(j.arremessos[:, 0].mean()), "arr_b": float(j.arremessos[:, 1].mean()),
         "acerto_a": float(j.acertos[:, 0].sum() / max(j.arremessos[:, 0].sum(), 1)),
         "acerto_b": float(j.acertos[:, 1].sum() / max(j.arremessos[:, 1].sum(), 1)),
         "seg_a": float((j.segura[:, 0] / tempo[:, 0]).mean()), "seg_b": float((j.segura[:, 1] / tempo[:, 0]).mean()),
         "recuo_a": float((j.recuo[:, 0] / (3 * tempo[:, 0])).mean()), "recuo_b": float((j.recuo[:, 1] / (3 * tempo[:, 0])).mean()),
         "dur": float(dur.mean())}
    return m


def partidas_vitrine(pop, semente):
    return np.arange(pop), np.random.default_rng(semente).permutation(pop)


def treina(geracoes=140, pop=100, jogos=4, semente=3, log=print, museu_cada=10, do_museu=2):
    rng = np.random.default_rng(semente)
    ga, gb = ARQ.aleatoria(pop, rng), ARQ.aleatoria(pop, rng)
    mus_a, mus_b = [], []
    hist = {"a": [], "b": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        ia, ib = partidas_vitrine(pop, sem)
        jv, _ = partidas(ga, gb, ia, ib, sem)
        m = metricas(jv)
        hist["a"].append(ga.copy())
        hist["b"].append(gb.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        ia = np.repeat(np.arange(pop), jogos)
        ib = np.concatenate([rng.permutation(pop) for _ in range(jogos)])
        ib2, pool_b = ib.copy(), gb
        if mus_b and do_museu:
            todos_b = np.concatenate([gb] + mus_b)
            blocos = np.arange(len(ia)) % jogos >= jogos - do_museu
            ib2 = np.where(blocos, pop + rng.integers(0, len(todos_b) - pop, len(ia)), ib)
            pool_b = todos_b
        ja, _ = partidas(ga, pool_b, ia, ib2, sem + 1)
        fa, fb = ja.aptidoes()
        apt_a = np.zeros(pop)
        np.add.at(apt_a, ia, fa)
        apt_b = np.zeros(pop)
        atual = ib2 < pop
        np.add.at(apt_b, ib2[atual], fb[atual])
        if mus_a and do_museu:                      # vermelhos atuais x azuis do museu
            todos_a = np.concatenate([ga] + mus_a)
            ib3 = np.repeat(np.arange(pop), do_museu)
            ia3 = pop + rng.integers(0, len(todos_a) - pop, pop * do_museu)
            j3, _ = partidas(todos_a, gb, ia3, ib3, sem + 2)
            _, fb3 = j3.aptidoes()
            np.add.at(apt_b, ib3, fb3)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  pegos a {m['pegos_a']:.2f} b {m['pegos_b']:.2f}  vit {m['vit_a']:.0%}/{m['vit_b']:.0%} emp {m['empate']:.0%} "
                f"arr {m['arr_a']:.1f}/{m['arr_b']:.1f} acerto {m['acerto_a']:.0%}/{m['acerto_b']:.0%} seg {m['seg_a']:.0%}/{m['seg_b']:.0%} "
                f"recuo {m['recuo_a']:.0%}/{m['recuo_b']:.0%} dur {m['dur']:.1f}s")
        if g % museu_cada == museu_cada - 1:
            mus_a.append(ga[np.argsort(-apt_a)[:5]].copy())
            mus_b.append(gb[np.argsort(-apt_b)[:5]].copy())
        ga = proxima_geracao(ga, apt_a, rng)
        gb = proxima_geracao(gb, apt_b, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"a": np.array(hist["a"]), "b": np.array(hist["b"]), "semente": np.array(hist["semente"]),
            **{"m_" + k: v for k, v in met.items()}}
