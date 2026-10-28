"""Co-evolução polícia x ladrão: duas populações que só melhoram uma contra a outra.

Treino profissional: cada indivíduo joga `jogos` partidas contra adversários e largadas diferentes, e uma parte
delas é contra o "museu" (melhores de gerações passadas), para a evolução não girar em círculos esquecendo
truques antigos. O vídeo re-simula partidas com a mesma regra de `partidas` e a mesma semente do treino.
"""
import numpy as np

from .desafios import policia as P
from .evolucao import proxima_geracao
from .rede import Arquitetura

ARQ = Arquitetura(P.CAMADAS)


def partidas(gl, gp, il, ip, semente, gravar=False):
    """Joga len(il) partidas: ladrão gl[il[k]] contra policial gp[ip[k]]."""
    jogo = P.Policia(len(il), np.random.default_rng(semente))
    pl, pp = ARQ.desempacota(gl[il]), ARQ.desempacota(gp[ip])
    reg = {"l": [], "p": [], "estado": [], "ativ_l": [], "ativ_p": []}
    for k in range(P.PASSOS):
        sl, al = ARQ.avalia(pl, jogo.obs_ladrao())
        sp, ap = ARQ.avalia(pp, jogo.obs_policia())
        jogo.passo(sl, sp, k)
        if gravar:
            reg["l"].append(jogo.pl.copy())
            reg["p"].append(jogo.pp.copy())
            reg["estado"].append(jogo.estado.copy())
            reg["ativ_l"].append(np.concatenate(al, 1))
            reg["ativ_p"].append(np.concatenate(ap, 1))
        if jogo.acabou():
            break
    jogo.finaliza(k)
    if gravar:
        reg["estado"][-1] = jogo.estado.copy()                    # quem esgotou o tempo só é marcado agora
        reg = {c: np.stack(v, 1) for c, v in reg.items()}
    return jogo, reg


def metricas(j):
    """Comportamentos medidos (o roteiro só conta o que aparece aqui)."""
    esc, peg = j.estado == P.ESCAPOU, j.estado == P.PEGO
    cima, baixo = j.cruzou & (j.y_cruza > 9.5), j.cruzou & (j.y_cruza < 4.5)
    guarda = j.cruzou & (j.pol_cofre_cruza < 4.0)              # o policial já espera junto ao cofre
    recuou = (j.max_x - j.pl[:, 0]) > 3.0                      # o ladrão voltou atrás (isca)
    return {"fuga": esc.mean(), "pego": peg.mean(), "tempo_esgotado": (j.estado == P.TEMPO).mean(),
            "chega_meio": j.cruzou.mean(), "rota_cima": cima.mean(), "rota_baixo": baixo.mean(),
            "emboscada": guarda.mean(), "recua": recuou.mean(),
            "tempo_fuga": float(j.t_fim[esc].mean() * P.DT) if esc.any() else 0.0,
            "tempo_captura": float(j.t_fim[peg].mean() * P.DT) if peg.any() else 0.0}


def partidas_vitrine(gl, gp, semente):
    """As partidas que o vídeo mostra e que as métricas medem: ladrão i x policial sorteado."""
    pop = len(gl)
    il = np.arange(pop)
    ip = np.random.default_rng(semente).permutation(pop)
    return il, ip


def treina(geracoes=250, pop=100, jogos=6, semente=3, log=print, museu_cada=10, do_museu=2):
    rng = np.random.default_rng(semente)
    gl, gp = ARQ.aleatoria(pop, rng), ARQ.aleatoria(pop, rng)
    mus_l, mus_p = [], []
    hist = {"lad": [], "pol": [], "semente": [], "met": []}
    for g in range(geracoes):
        sem = semente * 1_000_003 + g
        # métricas da vitrine (mesma partida que o vídeo re-simula)
        il, ip = partidas_vitrine(gl, gp, sem)
        jv, _ = partidas(gl, gp, il, ip, sem)
        m = metricas(jv)
        hist["lad"].append(gl.copy())
        hist["pol"].append(gp.copy())
        hist["semente"].append(sem)
        hist["met"].append(m)
        # partidas de treino
        il = np.repeat(np.arange(pop), jogos)
        ip = np.concatenate([rng.permutation(pop) for _ in range(jogos)])
        pool_p, pool_l = gp, gl
        il2, ip2 = il.copy(), ip.copy()
        if mus_p and do_museu:
            todos_p, todos_l = np.concatenate([gp] + mus_p), np.concatenate([gl] + mus_l)
            # os últimos `do_museu` jogos de cada indivíduo são contra o museu
            blocos = np.arange(len(il)) % jogos >= jogos - do_museu
            ip2 = np.where(blocos, pop + rng.integers(0, len(todos_p) - pop, len(il)), ip)
            pool_p = todos_p
        jg, _ = partidas(gl, pool_p, il2, ip2, sem + 1)
        fl, fp_ = jg.aptidoes()
        apt_l = np.zeros(pop)
        np.add.at(apt_l, il2, fl)
        # os policiais: cada partida contra o museu de ladrões vale para o policial do museu (não treina ninguém);
        # então o policial só ganha nota nas partidas contra a população atual
        apt_p = np.zeros(pop)
        atual = ip2 < pop
        np.add.at(apt_p, ip2[atual], fp_[atual])
        if mus_l and do_museu:                      # partidas extras: policiais atuais x ladrões do museu
            todos_l = np.concatenate([gl] + mus_l)
            n_extra = pop * do_museu
            ip3 = np.repeat(np.arange(pop), do_museu)
            il3 = pop + rng.integers(0, len(todos_l) - pop, n_extra)
            j3, _ = partidas(todos_l, gp, il3, ip3, sem + 2)
            _, fp3 = j3.aptidoes()
            np.add.at(apt_p, ip3, fp3)
        if log and (g % 20 == 0 or g == geracoes - 1):
            log(f"ger {g + 1:3d}  fuga {m['fuga']:.0%} pego {m['pego']:.0%} tempo {m['tempo_esgotado']:.0%} | "
                f"meio {m['chega_meio']:.0%} cima {m['rota_cima']:.0%} baixo {m['rota_baixo']:.0%} "
                f"emboscada {m['emboscada']:.0%} recua {m['recua']:.0%}")
        if g % museu_cada == museu_cada - 1:
            mus_l.append(gl[np.argsort(-apt_l)[:5]].copy())
            mus_p.append(gp[np.argsort(-apt_p)[:5]].copy())
        gl = proxima_geracao(gl, apt_l, rng)
        gp = proxima_geracao(gp, apt_p, rng)
    met = {k: np.array([m[k] for m in hist["met"]]) for k in hist["met"][0]}
    return {"lad": np.array(hist["lad"]), "pol": np.array(hist["pol"]), "semente": np.array(hist["semente"]),
            **{"m_" + k: v for k, v in met.items()}}
