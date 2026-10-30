"""Medidas de comportamento da queimada, tiradas das partidas da vitrine (re-simuladas) de cada geração.

vel   = velocidade média (m/s) de quem está em pé
lanc  = arremessos por partida que chegam a voar na quadra (os que não voam: bola encostada na parede ou acerto à queima-roupa)
mira  = fração dos arremessos que voam já apontados para um adversário em pé (a bola passaria a < 0,6 m dele)
nenhum= fração de partidas em que ninguém é queimado
"""
import os

import numpy as np

from ..desafios import queimada as Q


def medida(rod):
    reg = rod.reg
    bst, P, ang, vivo, dono = reg["bst"], reg["P"], reg["ang"], reg["vivo"], reg["bdono"]
    n = bst.shape[0]
    v = np.hypot(*(P[:, 1:] - P[:, :-1]).transpose(3, 0, 1, 2)) / Q.DT
    vel = float(v[vivo[:, 1:]].mean())
    lanc = mira = 0
    for b in range(2):
        ks, ts = np.where((bst[:, 1:, b] == Q.VOA) & (bst[:, :-1, b] != Q.VOA))
        for k, i in zip(ks, ts + 1):
            th = dono[k, i, b]
            d = np.array([np.cos(ang[k, i, th]), np.sin(ang[k, i, th])])
            alvo = False
            for p in range(6):
                if Q.EQUIPE[p] != Q.EQUIPE[th] and vivo[k, i - 1, p]:
                    rel = P[k, i - 1, p] - P[k, i, th]
                    if 0 < rel @ d < Q.ALCANCE and abs(rel[0] * d[1] - rel[1] * d[0]) < Q.HIT:
                        alvo = True
            lanc += 1
            mira += alvo
    return {"vel": vel, "lanc": lanc / n, "mira": mira / max(lanc, 1), "nenhum": float((rod.morte < 0).mean())}


def serie(A, passo=4, arq=None):
    """Séries (a cada `passo` gerações, interpoladas) das medidas; guarda em disco para não refazer."""
    G = A.total_ger
    if arq and os.path.exists(arq):
        d = dict(np.load(arq))
        if len(d["g"]) and d["G"] == G:
            return {k: d[k] for k in ("g", "vel", "lanc", "mira", "nenhum")}
    gs = sorted(set(list(range(0, G, passo)) + [G - 1]))
    out = {k: [] for k in ("vel", "lanc", "mira", "nenhum")}
    for g in gs:
        m = medida(A.rodada(g))
        A._cache.pop((g, False), None)
        for k in out:
            out[k].append(m[k])
    res = {"g": np.array(gs), **{k: np.array(v) for k, v in out.items()}}
    if arq:
        np.savez_compressed(arq, G=G, **res)
    return res
