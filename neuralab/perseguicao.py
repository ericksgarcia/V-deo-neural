"""Co-evolução polícia x ladrão: 100 ladrões contra 100 duplas de policiais, num labirinto."""
import numpy as np

from .desafios.policia import ESCAPOU, PASSOS, PILARES, PRESO, Policia
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ_LAD = Arquitetura(Policia.camadas_lad)
ARQ_POL = Arquitetura(Policia.camadas_pol)


def partidas(genes_lad, genes_pol, il, ip, semente, gravar=False):
    """Joga len(il) perseguições: ladrão genes_lad[il[k]] contra a dupla genes_pol[ip[k]]
    (os dois policiais da dupla têm o mesmo cérebro; uma entrada de 'papel' diz quem é quem)."""
    rng = np.random.default_rng(semente)
    jogo = Policia(len(il), rng)
    pl = ARQ_LAD.desempacota(genes_lad[il])
    pp = ARQ_POL.desempacota(genes_pol[ip])
    reg = {"pl": [], "pp": [], "ve": [], "visto": [], "estado": [], "cofre": [], "dia": [], "ativ_l": [], "ativ_p": []}
    if gravar:
        reg["pl"].append(jogo.pl.copy())
        reg["pp"].append(jogo.pp.copy())
        reg["ve"].append(jogo.ve_lad.copy())
        reg["visto"].append(jogo.visto_pol.copy())
        reg["estado"].append(jogo.estado.copy())
        reg["cofre"].append(jogo.cofre.copy())
        reg["dia"].append(jogo.diamantes.copy())
    k = 0
    for k in range(PASSOS):
        t = k * Policia.dt
        sl, al = ARQ_LAD.avalia(pl, jogo.obs_ladrao(t))
        s0, a0 = ARQ_POL.avalia(pp, jogo.obs_policia(t, 0))
        s1, _ = ARQ_POL.avalia(pp, jogo.obs_policia(t, 1))
        jogo.passo(sl, np.stack([s0, s1], 1), k)
        if gravar:
            reg["pl"].append(jogo.pl.copy())
            reg["pp"].append(jogo.pp.copy())
            reg["ve"].append(jogo.ve_lad.copy())
            reg["visto"].append(jogo.visto_pol.copy())
            reg["estado"].append(jogo.estado.copy())
            reg["cofre"].append(jogo.cofre.copy())
            reg["dia"].append(jogo.diamantes.copy())
            reg["ativ_l"].append(np.concatenate(al, 1))
            reg["ativ_p"].append(np.concatenate(a0, 1))
        if jogo.acabou():
            break
    jogo.finaliza(k)
    if gravar:
        reg["ativ_l"].insert(0, reg["ativ_l"][0])
        reg["ativ_p"].insert(0, reg["ativ_p"][0])
        reg = {c: np.stack(v, 1) for c, v in reg.items()}
    return jogo, reg


def metricas(j):
    """Comportamentos medidos nas perseguições (para o roteiro detectar 'descobertas')."""
    preso = j.estado == PRESO
    escapou = j.estado == ESCAPOU
    voltas = np.abs(j.ang).max(1) / (2 * np.pi)          # maior número de voltas em torno de um pilar
    laco = voltas >= 1.0
    return {
        "preso": preso.mean(),
        "escapou": escapou.mean(),
        "t_prisao": float(np.mean(np.where(preso, j.t_fim + 1, PASSOS))) * j.dt,
        "oculto": float(j.oculto.sum() / max(j.vivo.sum(), 1)),
        "laco": laco.mean(),
        "laco_escapa": (laco & escapou).sum() / max(laco.sum(), 1),
        "diamantes": float(j.diamantes.mean()),
        "dia_escapou": float(j.diamantes[escapou].mean()) if escapou.any() else 0.0,
        "rouba_oculto": float(j.rouba_oculto.sum() / max(j.diamantes.sum(), 1)),
        "vigia": float(j.vigia.sum() / max(j.vivo.sum(), 1)),
        "pego_cofre": j.pego_cofre.sum() / max(preso.sum(), 1),
        "cerco": j.cerco.mean(),
        "cerco_frac": j.cerco.sum() / max(preso.sum(), 1),
        "dist_par": float(j.dist_par.sum() / max(j.vivo.sum(), 1)),
        "n": j.n,
    }


def treina(geracoes=250, pop=100, jogos=4, semente=3, log=print):
    rng = np.random.default_rng(semente)
    gl, gp = ARQ_LAD.aleatoria(pop, rng), ARQ_POL.aleatoria(pop, rng)
    hist = {"lad": [], "pol": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        il = np.repeat(np.arange(pop), jogos)
        ip = np.random.default_rng(sem).permutation(np.tile(np.arange(pop), jogos))
        jogo, _ = partidas(gl, gp, il, ip, sem)
        fl, fp = jogo.aptidoes()
        apt_l, apt_p = np.zeros(pop), np.zeros(pop)
        np.add.at(apt_l, il, fl)
        np.add.at(apt_p, ip, fp)
        m = metricas(jogo)
        hist["lad"].append(gl.copy())
        hist["pol"].append(gp.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  presos {m['preso']:.0%} (em {m['t_prisao']:.1f}s) diam {m['diamantes']:.2f} "
                f"(oculto {m['rouba_oculto']:.0%}) vigia {m['vigia']:.0%} pego_cofre {m['pego_cofre']:.0%} | "
                f"oculto {m['oculto']:.0%} "
                f"laço {m['laco']:.0%} (escapa {m['laco_escapa']:.0%}) | cerco {m['cerco']:.0%} "
                f"({m['cerco_frac']:.0%} das prisões) dist dupla {m['dist_par']:.1f} m")
        gl = proxima_geracao(gl, apt_l, rng)
        gp = proxima_geracao(gp, apt_p, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"lad": np.array(hist["lad"]), "pol": np.array(hist["pol"]), "semente": np.array(hist["semente"]),
            **{"m_" + k: v for k, v in met.items()}}


def torneio(hist, ger_lad, ger_pol, jogos=400, semente=99):
    """Fração de ladrões presos: ladrões da geração ger_lad contra policiais da geração ger_pol."""
    gl, gp = hist["lad"][ger_lad], hist["pol"][ger_pol]
    pop = len(gl)
    rng = np.random.default_rng(semente)
    il, ip = rng.integers(0, pop, jogos), rng.integers(0, pop, jogos)
    jogo, _ = partidas(gl, gp, il, ip, semente)
    return float((jogo.estado == PRESO).mean())


__all__ = ["treina", "partidas", "metricas", "torneio", "PILARES"]
