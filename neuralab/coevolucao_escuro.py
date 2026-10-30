"""Co-evolução do esconde-esconde no escuro: caçadores x fugitivos (duas populações, um cérebro por lado).

Cada indivíduo joga `jogos` partidas; parte delas é contra o "museu" (melhores de gerações passadas). O vídeo re-simula
as partidas da vitrine com a mesma regra e a mesma semente do treino.
"""
import numpy as np

from .desafios import escuro as E
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ_C, ARQ_F = Arquitetura(E.CAM_C), Arquitetura(E.CAM_F)


def partidas(gc, gf, ic, iff, semente, gravar=False):
    """Joga len(ic) partidas: caçadores gc[ic[k]] contra fugitivos gf[iff[k]]."""
    jogo = E.Escuro(len(ic), np.random.default_rng(semente))
    pc, pf = ARQ_C.desempacota(gc[ic]), ARQ_F.desempacota(gf[iff])
    reg = {"c": [], "f": [], "ang": [], "estado": [], "luz": [], "ativ_c": [], "ativ_f": []}
    for k in range(E.PASSOS):
        sc, ac = ARQ_C.avalia(pc, jogo.obs_cacador())
        sf, af = ARQ_F.avalia(pf, jogo.obs_fugitivo())
        jogo.passo(sc, sf, k)
        if gravar:
            reg["c"].append(jogo.c.copy())
            reg["f"].append(jogo.f.copy())
            reg["ang"].append(jogo.ang.copy())
            reg["estado"].append(jogo.estado.copy())
            reg["luz"].append(jogo._luz.any(1).copy())
            reg["ativ_c"].append(np.concatenate([x[:, 0] for x in ac], 1))
            reg["ativ_f"].append(np.concatenate([x[:, 0] for x in af], 1))
        if jogo.acabou():
            break
    jogo.finaliza(k)
    if gravar:
        reg = {c: np.stack(v, 1) for c, v in reg.items()}
    return jogo, reg


def metricas(j):
    """Comportamentos medidos (o roteiro só conta o que aparece aqui)."""
    pegos = (j.estado == E.PEGO)
    vivo = np.maximum(j.vivo_f, 1)
    return {"pegos": float(pegos.mean()), "todos": float(pegos.all(1).mean()), "nenhum": float((~pegos.any(1)).mean()),
            "aceso": float((j.aceso / vivo).mean()),
            "giro": float((j.giro_cego / np.maximum(j.cego_c, 1)).mean()),
            "parado": float((j.parado / np.maximum(j.perto9, 1))[j.perto9 > 0].mean()) if (j.perto9 > 0).any() else 0.0,
            "costas": float((j.costas / np.maximum(j.perto3, 1))[j.perto3 > 0].mean()) if (j.perto3 > 0).any() else 0.0,
            "luz": float((j.luz_c / np.maximum(j.luz_c + j.cego_c, 1)).mean()),
            "dur": float((j.t_ult + 1).mean() * E.DT)}


def partidas_vitrine(pop, semente):
    return np.arange(pop), np.random.default_rng(semente).permutation(pop)


def treina(geracoes=160, pop=100, jogos=6, semente=3, log=print, museu_cada=10, do_museu=2):
    rng = np.random.default_rng(semente)
    gc, gf = ARQ_C.aleatoria(pop, rng), ARQ_F.aleatoria(pop, rng)
    mus_c, mus_f = [], []
    hist = {"cac": [], "fug": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        ic, iff = partidas_vitrine(pop, sem)
        jv, _ = partidas(gc, gf, ic, iff, sem)
        m = metricas(jv)
        hist["cac"].append(gc.copy())
        hist["fug"].append(gf.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        ic = np.repeat(np.arange(pop), jogos)
        iff = np.concatenate([rng.permutation(pop) for _ in range(jogos)])
        iff2, pool_f = iff.copy(), gf
        if mus_f and do_museu:
            todos_f = np.concatenate([gf] + mus_f)
            blocos = np.arange(len(ic)) % jogos >= jogos - do_museu
            iff2 = np.where(blocos, pop + rng.integers(0, len(todos_f) - pop, len(ic)), iff)
            pool_f = todos_f
        jc, _ = partidas(gc, pool_f, ic, iff2, sem + 1)
        fc, ff = jc.aptidoes()
        apt_c = np.zeros(pop)
        np.add.at(apt_c, ic, fc)
        apt_f = np.zeros(pop)
        atual = iff2 < pop
        np.add.at(apt_f, iff2[atual], ff[atual])
        if mus_c and do_museu:                      # fugitivos atuais x caçadores do museu
            todos_c = np.concatenate([gc] + mus_c)
            if3 = np.repeat(np.arange(pop), do_museu)
            ic3 = pop + rng.integers(0, len(todos_c) - pop, pop * do_museu)
            j3, _ = partidas(todos_c, gf, ic3, if3, sem + 2)
            _, ff3 = j3.aptidoes()
            np.add.at(apt_f, if3, ff3)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  pegos {m['pegos']:.0%} aceso {m['aceso']:.0%} giro {m['giro']:.2f} parado {m['parado']:.0%} "
                f"costas {m['costas']:.0%} luz {m['luz']:.0%} dur {m['dur']:.1f}s")
        if g % museu_cada == museu_cada - 1:
            mus_c.append(gc[np.argsort(-apt_c)[:5]].copy())
            mus_f.append(gf[np.argsort(-apt_f)[:5]].copy())
        gc = proxima_geracao(gc, apt_c, rng)
        gf = proxima_geracao(gf, apt_f, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"cac": np.array(hist["cac"]), "fug": np.array(hist["fug"]), "semente": np.array(hist["semente"]),
            **{"m_" + k: v for k, v in met.items()}}
