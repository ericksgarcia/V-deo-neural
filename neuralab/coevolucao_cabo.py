"""Treino do cabo de guerra de enxames em fases: só A aprende, só B aprende, ou os dois."""
import numpy as np

from .desafios.cabo import (EM_JOGO, EMPATE, GOL, K, PASSOS, VENCE_A, VENCE_B, Cabo)
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(Cabo.camadas)

# (nome, quem treina, gerações): um enxame aprende sozinho contra o outro congelado, depois os dois juntos
FASES = [("A", "A", 15), ("B", "B", 15), ("AB", "AB", 120)]


def avalia(params, x):
    """x (n,K,entradas), params (n,...) -> saída (n,K,saídas) e ativações por camada."""
    ativ = [x]
    h = x
    for W, b in params:
        h = np.tanh(np.einsum("nka,nab->nkb", h, W) + b[:, None, :])
        ativ.append(h)
    return h, ativ


def partidas(gA, gB, ia, ib, semente, gravar=False):
    rng = np.random.default_rng(semente)
    jogo = Cabo(len(ia), rng)
    pa, pb = ARQ.desempacota(gA[ia]), ARQ.desempacota(gB[ib])
    reg = {"pos": [], "vel": [], "estado": [], "ativ_a": [], "ativ_b": []}
    for k in range(Cabo.passos):
        sa, aa = avalia(pa, jogo.obs(0))
        sb, ab = avalia(pb, jogo.obs(1))
        jogo.passo(sa, sb, k)
        if gravar:
            reg["pos"].append(jogo.pos.astype(np.float32))
            reg["vel"].append(jogo.vel.astype(np.float32))
            reg["estado"].append(jogo.estado.copy())
            reg["ativ_a"].append(np.concatenate(aa, 2).astype(np.float16))
            reg["ativ_b"].append(np.concatenate(ab, 2).astype(np.float16))
        if jogo.acabou():
            break
    jogo.tempo_esgotou()
    if gravar:
        reg = {k: np.stack(v, 1) for k, v in reg.items()}   # (n, T, ...)
    return jogo, reg


def metricas(j):
    ven_a, ven_b, emp = j.estado == VENCE_A, j.estado == VENCE_B, j.estado == EMPATE
    v = np.maximum(j.passos_vivos, 1)
    out = {"venc_a": ven_a.mean(), "venc_b": ven_b.mean(), "empate": emp.mean(),
           "mexeu": (j.t_mexeu >= 0).mean(),
           "duracao": float(np.mean(np.where(j.t_fim >= 0, j.t_fim, PASSOS)) / 30)}
    for lado, c in ((0, "a"), (1, "b")):
        out["enc_" + c] = float((j.enc[lado] / v).mean())                       # robôs encostados, em média
        out["pico_" + c] = float(j.enc_pico[lado].mean())                       # máx. de robôs encostados ao mesmo tempo
        out["atras_" + c] = float((j.atras[lado].sum() / max(j.enc[lado].sum(), 1e-6)))   # encostados do lado certo
        out["coesao_" + c] = float(j.coesao2[lado].mean())
    return out


def treina(fases=FASES, pop=100, jogos=6, semente=3, log=print):
    rng = np.random.default_rng(semente)
    gA, gB = ARQ.aleatoria(pop, rng), ARQ.aleatoria(pop, rng)
    h = {"A": [], "B": [], "semente": [], "fase": [], "treina": [], "met": []}
    g = 0
    for f, (nome, quem, n) in enumerate(fases):
        for _ in range(n):
            sem = semente * 1_000_003 + g
            ia = np.repeat(np.arange(pop), jogos)
            ib = np.random.default_rng(sem).permutation(np.tile(np.arange(pop), jogos))
            jogo, _r = partidas(gA, gB, ia, ib, sem)
            fa, fb = jogo.aptidoes()
            apt_a, apt_b = np.zeros(pop), np.zeros(pop)
            np.add.at(apt_a, ia, fa)
            np.add.at(apt_b, ib, fb)
            m = metricas(jogo)
            h["A"].append(gA.copy())
            h["B"].append(gB.copy())
            h["semente"].append(sem)
            h["fase"].append(f)
            h["treina"].append(quem)
            h["met"].append(m)
            if log and (g % 5 == 0):
                log(f"ger {g + 1:3d} [{quem:>2}] A {m['venc_a']:.0%} B {m['venc_b']:.0%} emp {m['empate']:.0%} "
                    f"mexeu {m['mexeu']:.0%} enc A {m['enc_a']:.1f} B {m['enc_b']:.1f} pico {m['pico_a']:.1f}/{m['pico_b']:.1f} "
                    f"atrás {m['atras_a']:.0%} coesão {m['coesao_a']:.1f} dur {m['duracao']:.1f}s")
            if "A" in quem:
                gA = proxima_geracao(gA, apt_a, rng)
            if "B" in quem:
                gB = proxima_geracao(gB, apt_b, rng)
            g += 1
    met = {k: np.array([m[k] for m in h["met"]]) for k in h["met"][0]}
    return {"A": np.array(h["A"]), "B": np.array(h["B"]), "semente": np.array(h["semente"]),
            "fase": np.array(h["fase"]), "treina": np.array(h["treina"]),
            **{"m_" + k: v for k, v in met.items()}}


def torneio(hist, ger_a, ger_b, jogos=600, semente=99):
    """Vitórias de A (geração ger_a) contra B (geração ger_b)."""
    gA, gB = hist["A"][ger_a], hist["B"][ger_b]
    pop = len(gA)
    rng = np.random.default_rng(semente)
    ia, ib = rng.integers(0, pop, jogos), rng.integers(0, pop, jogos)
    jogo, _ = partidas(gA, gB, ia, ib, semente)
    return float((jogo.estado == VENCE_A).mean()), float((jogo.estado == VENCE_B).mean())


def suave_fase(x, fase, k=5):
    x, fase = np.asarray(x, float), np.asarray(fase)
    out = np.empty(len(x))
    for g in range(len(x)):
        a = g
        while a > 0 and g - a < k - 1 and fase[a - 1] == fase[g]:
            a -= 1
        out[g] = x[a:g + 1].mean()
    return out


def limites_fases(fases=FASES):
    out, g = [], 0
    for _, _, n in fases:
        out.append((g, g + n - 1))
        g += n
    return out
