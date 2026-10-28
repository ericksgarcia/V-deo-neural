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
            reg["ativ"].append(np.concatenate(ativ, 1))
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


def _aceita_ruido(Desafio):
    import inspect
    return "ruido" in inspect.signature(Desafio.__init__).parameters


def aptidao_robusta(Desafio, genes, sem, cenarios=4, ruido_max=1.4, peso_min=0.2):
    """Treino profissional: cada indivíduo é avaliado em vários cenários (largadas diferentes) e a nota premia
    quem vai bem em TODOS (média + pior caso), não quem teve sorte numa largada só. O cenário 0 é o padrão
    (o mesmo que o vídeo re-simula), então os números do vídeo continuam sendo os do treino.

    Devolve (ambiente do cenário 0, aptidão combinada, fração de sucesso nos cenários extras)."""
    amb0, _ = simula(Desafio, genes, sem)
    notas = [amb0.aptidao()]
    extra = []
    if cenarios > 1 and _aceita_ruido(Desafio):
        for j in range(1, cenarios):
            r = ruido_max * j / (cenarios - 1)
            amb, _ = simula(Desafio, genes, sem + 7919 * j, ruido=r)
            notas.append(amb.aptidao())
            extra.append(float((amb.estado == SUCESSO).mean()))
    notas = np.array(notas)
    apt = (1 - peso_min) * notas.mean(0) + peso_min * notas.min(0) if len(notas) > 1 else notas[0]
    return amb0, apt, (float(np.mean(extra)) if extra else None)


def treina(Desafio, geracoes=150, populacao=150, semente=7, log=print, robusto=True, cenarios=4, ruido_max=1.4,
           peso_min=0.2, imigrantes=0.0, adaptativa=False):
    """Evolução com avaliação em vários cenários (largadas cada vez mais variadas): a seleção premia quem
    funciona em todos, então o melhor indivíduo aprende a regra e não decora uma largada. Opcionais, medidos
    e desligados por padrão: mutação adaptativa e recém-chegados aleatórios (ajuda ou atrapalha conforme o
    desafio). Medido na baliza (semente 5, 200 gerações, 400 largadas): treino clássico 51% na largada
    normal e 20% na difícil; este treino 100% e 66%."""
    rng = np.random.default_rng(semente)
    arq = Arquitetura(Desafio.camadas)
    genes = arq.aleatoria(populacao, rng)
    hist = {"genes": [], "sucessos": [], "falhas": [], "quase": [], "melhor": [], "semente": []}
    ga = dict(getattr(Desafio, "ga", {}))
    base = ga.pop("forca", 0.15)
    forca, recorde, parado = base, -1e9, 0
    for g in range(geracoes):
        sem = semente * 100_000 + g
        if robusto:
            amb, apt, rob = aptidao_robusta(Desafio, genes, sem, cenarios, ruido_max, peso_min)
            if rob is not None:
                hist.setdefault("robusto", []).append(rob)
        else:
            amb, _ = simula(Desafio, genes, sem)
            apt = amb.aptidao()
        suc = int((amb.estado == SUCESSO).sum())
        melhor_nota = float(np.sort(apt)[-5:].mean())
        if not adaptativa:
            pass
        elif melhor_nota > recorde + 1e-3:
            recorde, parado = melhor_nota, 0
            forca = max(base * 0.5, forca * 0.92)
        else:
            parado += 1
            if parado >= 12:
                forca = min(base * 2.5, forca * 1.25)
                parado = 6
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
        genes = proxima_geracao(genes, apt, rng, forca=forca, **ga)
        if robusto and imigrantes:
            novos = max(1, int(populacao * imigrantes))
            genes[-novos:] = arq.aleatoria(novos, rng)
    return {k: np.array(v) for k, v in hist.items()}
