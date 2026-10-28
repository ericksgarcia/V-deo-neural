"""Treino do sumô em fases: só A aprende, só B aprende, ou os dois (o outro lado fica congelado)."""
import numpy as np

from .desafios.sumo import EM_JOGO, EMPATE, PASSOS, Sumo, VENCE_A, VENCE_B
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(Sumo.camadas)

# (nome, quem treina, gerações). "A", "B" ou "AB". Pouco treino primeiro, depois cada vez mais.
FASES = [("A", "A", 6), ("B", "B", 6), ("AB", "AB", 6),
         ("A", "A", 14), ("B", "B", 14), ("AB", "AB", 20),
         ("A", "A", 30), ("B", "B", 30), ("AB", "AB", 60)]


def partidas(gA, gB, ia, ib, semente, gravar=False):
    rng = np.random.default_rng(semente)
    jogo = Sumo(len(ia), rng)
    pa, pb = ARQ.desempacota(gA[ia]), ARQ.desempacota(gB[ib])
    reg = {"pos": [], "vel": [], "cd": [], "estado": [], "ativ_a": [], "ativ_b": []}
    for k in range(Sumo.passos):
        sa, aa = ARQ.avalia(pa, jogo.obs(0, k * jogo.dt))
        sb, ab = ARQ.avalia(pb, jogo.obs(1, k * jogo.dt))
        jogo.passo(sa, sb, k)
        if gravar:
            reg["pos"].append(jogo.pos.copy())
            reg["vel"].append(jogo.vel.copy())
            reg["cd"].append(jogo.cd.copy())
            reg["estado"].append(jogo.estado.copy())
            reg["ativ_a"].append(np.concatenate(aa, 1))
            reg["ativ_b"].append(np.concatenate(ab, 1))
        if jogo.acabou():
            break
    jogo.tempo_esgotou()
    if gravar:
        reg = {"pos": np.stack(reg["pos"], 2), "vel": np.stack(reg["vel"], 2), "cd": np.stack(reg["cd"], 2),
               "estado": np.stack(reg["estado"], 1), "ativ_a": np.stack(reg["ativ_a"], 1),
               "ativ_b": np.stack(reg["ativ_b"], 1)}
    return jogo, reg


def metricas(j):
    ven_a, ven_b, emp = j.estado == VENCE_A, j.estado == VENCE_B, j.estado == EMPATE
    contato = j.t_contato >= 0
    # contato antes do fim = houve empurrão; sem contato = o perdedor caiu sozinho
    decisivo = ~emp
    sozinho = decisivo & (~contato | (j.t_contato * 30 > j.t_fim))
    def investida(lado):
        d = j.p1[1 - lado] - j.p1[lado]
        n = d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
        return (np.sum(j.v1[lado] * n, 1) > 2.5).mean()

    def espera(lado):   # parado perto do centro depois de 2 s
        return (np.linalg.norm(j.p2[lado], axis=1) < 1.0).mean()

    return {
        "invest_a": investida(0), "invest_b": investida(1), "espera_a": espera(0), "espera_b": espera(1),
        "venc_a": ven_a.mean(), "venc_b": ven_b.mean(), "empate": emp.mean(),
        "sozinho": sozinho.mean(),
        "empurrao": (decisivo & ~sozinho).mean(),
        "contato": contato.mean(),
        "choque": float(j.v_contato[contato].mean()) if contato.any() else 0.0,
        "arranc_a": float(j.arrancadas[0].mean()), "arranc_b": float(j.arrancadas[1].mean()),
        "duracao": float(np.mean(np.where(j.t_fim >= 0, j.t_fim, PASSOS)) / 30),
    }


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
            if log and (g % 10 == 0):
                log(f"ger {g + 1:3d} [{quem:>2}] A {m['venc_a']:.0%} B {m['venc_b']:.0%} emp {m['empate']:.0%} "
                    f"sozinho {m['sozinho']:.0%} empurrão {m['empurrao']:.0%} choque {m['choque']:.1f} "
                    f"arr A {m['arranc_a']:.1f} B {m['arranc_b']:.1f} dur {m['duracao']:.1f}s")
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
    """Média móvel que olha só para trás e nunca atravessa o início de uma fase de treino."""
    x, fase = np.asarray(x, float), np.asarray(fase)
    out = np.empty(len(x))
    for g in range(len(x)):
        a = g
        while a > 0 and g - a < k - 1 and fase[a - 1] == fase[g]:
            a -= 1
        out[g] = x[a:g + 1].mean()
    return out


def limites_fases(fases=FASES):
    """[(primeira, última)] geração de cada fase."""
    out, g = [], 0
    for _, _, n in fases:
        out.append((g, g + n - 1))
        g += n
    return out
