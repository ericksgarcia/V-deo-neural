"""Algoritmo genético: seleção dos melhores, cruzamento e pequenas mutações."""
import numpy as np

from .rede import Arquitetura
from .desafios.foguete import SUCESSO


def simula(Desafio, genes, semente, gravar=False, **kw):
    arq = Arquitetura(Desafio.camadas)
    params = arq.desempacota(genes)
    amb = Desafio(len(genes), np.random.default_rng(semente), **kw)
    reg = {"s": [], "estado": [], "acel": [], "ativ": []}
    for t in range(Desafio.passos):
        saida, ativ = arq.avalia(params, amb.observa())
        amb.passo(saida, t)
        if gravar:
            reg["s"].append(amb.s.copy())
            reg["estado"].append(amb.estado.copy())
            reg["acel"].append(amb.acel.copy())
            reg["ativ"].append(np.concatenate(ativ, -1))
        if (amb.estado != 0).all():
            break
    amb.finaliza(t)
    if gravar:
        reg = {k: np.stack(v, 1) for k, v in reg.items()}  # (P, T, ...)
    return amb, reg


def proxima_geracao(genes, aptidao, rng, elite=8, taxa=0.1, forca=0.15):
    n, d = genes.shape
    ordem = np.argsort(-aptidao)
    pais = genes[ordem[: n // 2]]
    filhos = [genes[ordem[:elite]]]
    m = n - elite
    a = pais[np.minimum(rng.integers(0, len(pais), (m, 3)).min(1), len(pais) - 1)]
    b = pais[rng.integers(0, len(pais), m)]
    mistura = rng.random((m, d)) < 0.5
    f = np.where(mistura, a, b)
    muta = rng.random((m, d)) < taxa
    f = f + muta * rng.normal(0, forca, (m, d))
    filhos.append(f.astype(np.float32))
    return np.concatenate(filhos)


def treina(Desafio, geracoes=150, populacao=150, semente=7, log=print):
    rng = np.random.default_rng(semente)
    arq = Arquitetura(Desafio.camadas)
    genes = arq.aleatoria(populacao, rng)
    hist = {"genes": [], "sucessos": [], "falhas": [], "quase": [], "melhor": [], "semente": []}
    for g in range(geracoes):
        sem = semente * 100_000 + g
        amb, _ = simula(Desafio, genes, sem)
        apt = amb.aptidao()
        K = getattr(Desafio, "cenarios", 1)
        if K > 1:   # nota de seleção = média em K trânsitos diferentes (evita decorar um único cenário)
            ambs, _ = simula(Desafio, np.tile(genes, (K, 1)), sem + 1, por_mundo=True)
            apt = ambs.aptidao().reshape(K, -1).mean(0)
        suc = int((amb.estado == SUCESSO).sum())
        hist["genes"].append(genes.copy())
        hist["sucessos"].append(suc)
        hist["falhas"].append(populacao - suc)
        hist["quase"].append(amb.chegou_mas_bateu())
        hist["melhor"].append(float(apt.max()))
        hist["semente"].append(sem)
        if hasattr(amb, "metricas"):
            for k, v in amb.metricas().items():
                hist.setdefault("m_" + k, []).append(v)
        if log and (g % 10 == 0 or g == geracoes - 1):
            log(f"geração {g + 1:3d}: {suc:3d}/{populacao} sucesso | quase {hist['quase'][-1]:3d} | melhor {apt.max():.2f}")
        genes = proxima_geracao(genes, apt, rng, **getattr(Desafio, "ga", {}))
    return {k: np.array(v) for k, v in hist.items()}
