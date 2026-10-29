"""Co-evolução escolta VIP: seguranças x assassinos (duas populações que só melhoram uma contra a outra).

Cada indivíduo joga `jogos` partidas; parte delas é contra o "museu" (melhores de gerações passadas) para a evolução
não girar em círculos. O vídeo re-simula as partidas da vitrine com a mesma regra e a mesma semente do treino.
"""
import numpy as np

from .desafios import escolta as E
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(E.CAMADAS)


def partidas(gs, ga, isg, ia, semente, gravar=False):
    """Joga len(isg) partidas: seguranças gs[isg[k]] contra assassinos ga[ia[k]]."""
    jogo = E.Escolta(len(isg), np.random.default_rng(semente))
    ps, pa = ARQ.desempacota(gs[isg]), ARQ.desempacota(ga[ia])
    reg = {"g": [], "a": [], "vip": [], "estado": [], "ativ_g": [], "ativ_a": []}
    for k in range(E.PASSOS):
        sg, ag = ARQ.avalia(ps, jogo.obs_seguranca())
        sa, aa = ARQ.avalia(pa, jogo.obs_assassino())
        jogo.passo(sg, sa, k)
        if gravar:
            reg["g"].append(jogo.g.copy())
            reg["a"].append(jogo.a.copy())
            reg["vip"].append(jogo.vip.copy())
            reg["estado"].append(jogo.estado.copy())
            reg["ativ_g"].append(np.concatenate([x[:, 0] for x in ag], 1))
            reg["ativ_a"].append(np.concatenate([x[:, 0] for x in aa], 1))
        if jogo.acabou():
            break
    jogo.finaliza(k)
    if gravar:
        reg = {c: np.stack(v, 1) for c, v in reg.items()}
    return jogo, reg


def metricas(j):
    """Comportamentos medidos (o roteiro só conta o que aparece aqui)."""
    morto = j.estado == E.MORTO
    perto = np.maximum(j.perto, 1)
    return {"vip_vivo": 1 - morto.mean(), "vip_morto": morto.mean(),
            "t_morte": float(j.t_fim[morto].mean() * E.DT) if morto.any() else 0.0,
            "escudo": float((j.escudo / perto)[j.perto > 0].mean()) if (j.perto > 0).any() else 0.0,
            "pinca": float((j.abre / np.maximum(j.passos_vivo, 1)).mean()),
            "cola": float((j.cola / np.maximum(j.passos_vivo, 1)).mean()),
            "contato": float((j.contatos / np.maximum(j.passos_vivo, 1)).mean()),
            "min_vip": float(np.minimum(j.min_vip, 12).mean())}


def partidas_vitrine(pop, semente):
    return np.arange(pop), np.random.default_rng(semente).permutation(pop)


def treina(geracoes=200, pop=100, jogos=6, semente=3, log=print, museu_cada=10, do_museu=2):
    rng = np.random.default_rng(semente)
    gs, ga = ARQ.aleatoria(pop, rng), ARQ.aleatoria(pop, rng)
    mus_s, mus_a = [], []
    hist = {"seg": [], "ass": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        isg, ia = partidas_vitrine(pop, sem)
        jv, _ = partidas(gs, ga, isg, ia, sem)
        m = metricas(jv)
        hist["seg"].append(gs.copy())
        hist["ass"].append(ga.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        isg = np.repeat(np.arange(pop), jogos)
        ia = np.concatenate([rng.permutation(pop) for _ in range(jogos)])
        ia2, pool_a = ia.copy(), ga
        if mus_a and do_museu:
            todos_a = np.concatenate([ga] + mus_a)
            blocos = np.arange(len(isg)) % jogos >= jogos - do_museu
            ia2 = np.where(blocos, pop + rng.integers(0, len(todos_a) - pop, len(isg)), ia)
            pool_a = todos_a
        jg, _ = partidas(gs, pool_a, isg, ia2, sem + 1)
        fg, fa = jg.aptidoes()
        apt_s = np.zeros(pop)
        np.add.at(apt_s, isg, fg)
        apt_a = np.zeros(pop)
        atual = ia2 < pop
        np.add.at(apt_a, ia2[atual], fa[atual])
        if mus_s and do_museu:                      # assassinos atuais x seguranças do museu
            todos_s = np.concatenate([gs] + mus_s)
            ia3 = np.repeat(np.arange(pop), do_museu)
            is3 = pop + rng.integers(0, len(todos_s) - pop, pop * do_museu)
            j3, _ = partidas(todos_s, ga, is3, ia3, sem + 2)
            _, fa3 = j3.aptidoes()
            np.add.at(apt_a, ia3, fa3)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  vip vivo {m['vip_vivo']:.0%} t_morte {m['t_morte']:.1f}s escudo {m['escudo']:.0%} "
                f"pinça {m['pinca']:.0%} cola {m['cola']:.1f}m contato {m['contato']:.0%} min {m['min_vip']:.1f}")
        if g % museu_cada == museu_cada - 1:
            mus_s.append(gs[np.argsort(-apt_s)[:5]].copy())
            mus_a.append(ga[np.argsort(-apt_a)[:5]].copy())
        gs = proxima_geracao(gs, apt_s, rng)
        ga = proxima_geracao(ga, apt_a, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"seg": np.array(hist["seg"]), "ass": np.array(hist["ass"]), "semente": np.array(hist["semente"]),
            **{"m_" + k: v for k, v in met.items()}}
