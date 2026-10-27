"""Co-evolução: duas populações que só melhoram uma contra a outra (corrida armamentista)."""
import numpy as np

from .desafios.penalti import DEFESA, FORA, GOL, MEIO_GOL, Penalti
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ_BAT = Arquitetura(Penalti.camadas_bat)
ARQ_GOL = Arquitetura(Penalti.camadas_gol)


def partidas(genes_bat, genes_gol, ib, ig, semente, gravar=False):
    """Joga len(ib) cobranças: batedor genes_bat[ib[k]] contra goleiro genes_gol[ig[k]]."""
    rng = np.random.default_rng(semente)
    jogo = Penalti(len(ib), rng)
    pb = ARQ_BAT.desempacota(genes_bat[ib])
    pg = ARQ_GOL.desempacota(genes_gol[ig])
    reg = {"r": [], "corpo": [], "xg": [], "bola_x": [], "bola_p": [], "estado": [], "ativ_b": [], "ativ_g": []}
    for k in range(Penalti.passos):
        t = k * Penalti.dt
        sb, ab = ARQ_BAT.avalia(pb, jogo.obs_batedor(t))
        sg, ag = ARQ_GOL.avalia(pg, jogo.obs_goleiro(t))
        jogo.passo(sb, sg, k)
        if gravar:
            xb, p = jogo.bola(t)
            for chave, v in (("r", jogo.r), ("corpo", jogo.corpo), ("xg", jogo.xg),
                             ("bola_x", xb), ("bola_p", p), ("estado", jogo.estado)):
                reg[chave].append(np.array(v, copy=True))
            reg["ativ_b"].append(np.concatenate(ab, 1))
            reg["ativ_g"].append(np.concatenate(ag, 1))
        if jogo.acabou():
            break
    if gravar:
        reg = {k: np.stack(v, 1) for k, v in reg.items()}
    return jogo, reg


def metricas(j):
    """Comportamentos medidos nas cobranças (para o roteiro detectar 'truques')."""
    n = j.n
    pulou_antes = (j.pulo_t >= 0) & (j.pulo_t < j.chute_t + 0.05)
    lado_bola = np.sign(j.alvo)
    acertou_lado = pulou_antes & (j.pulo_dir == lado_bola)
    finta = (np.abs(j.corpo_antes) > 0.35) & (np.sign(j.corpo_antes) != np.sign(j.canto_pedido)) \
        & (np.abs(j.canto_pedido) > 0.25)
    gol = j.estado == GOL
    tarde = j.chute_t > 1.35
    return {
        "gol": gol.mean(),
        "defesa": (j.estado == DEFESA).mean(),
        "fora": (j.estado == FORA).mean(),
        "pulo_antes": pulou_antes.mean(),
        "leitura": acertou_lado.sum() / max(pulou_antes.sum(), 1),
        "finta": finta.mean(),
        "finta_gol": (finta & gol).sum() / max(finta.sum(), 1),
        "paradinha": (tarde & pulou_antes & gol).mean(),
        "tempo_chute": float(np.mean(j.chute_t)),
        "cavadinha": ((np.abs(j.alvo) < 1.0) & pulou_antes & gol).mean(),
        "canto": (np.abs(j.alvo) > 2.6).mean(),
        "espera": 1 - pulou_antes.mean(),
        "n": n,
    }


def treina(geracoes=300, pop=100, jogos=8, semente=3, log=print):
    rng = np.random.default_rng(semente)
    gb, gg = ARQ_BAT.aleatoria(pop, rng), ARQ_GOL.aleatoria(pop, rng)
    hist = {"bat": [], "gol": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        ib = np.repeat(np.arange(pop), jogos)
        ig = np.random.default_rng(sem).permutation(np.tile(np.arange(pop), jogos))
        jogo, _ = partidas(gb, gg, ib, ig, sem)
        fb, fg = jogo.aptidoes()
        apt_b = np.zeros(pop)
        apt_g = np.zeros(pop)
        np.add.at(apt_b, ib, fb)
        np.add.at(apt_g, ig, fg)
        m = metricas(jogo)
        hist["bat"].append(gb.copy())
        hist["gol"].append(gg.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        if log and (g % 20 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  gol {m['gol']:.0%} def {m['defesa']:.0%} fora {m['fora']:.0%} | "
                f"pula antes {m['pulo_antes']:.0%} (lê {m['leitura']:.0%}) finta {m['finta']:.0%} "
                f"paradinha {m['paradinha']:.0%} cavadinha {m['cavadinha']:.0%} chute {m['tempo_chute']:.2f}s")
        gb = proxima_geracao(gb, apt_b, rng)
        gg = proxima_geracao(gg, apt_g, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"bat": np.array(hist["bat"]), "gol": np.array(hist["gol"]), "semente": np.array(hist["semente"]),
            **{"m_" + k: v for k, v in met.items()}}


def torneio(hist, ger_bat, ger_gol, jogos=400, semente=99):
    """Taxa de gol do batedor de uma geração contra o goleiro de outra (melhores de cada)."""
    gb, gg = hist["bat"][ger_bat], hist["gol"][ger_gol]
    pop = len(gb)
    rng = np.random.default_rng(semente)
    ib, ig = rng.integers(0, pop, jogos), rng.integers(0, pop, jogos)
    jogo, _ = partidas(gb, gg, ib, ig, semente)
    return float((jogo.estado == GOL).mean())


__all__ = ["treina", "partidas", "metricas", "torneio", "MEIO_GOL"]
