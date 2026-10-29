"""Base para desafios de UMA população (foguete, baliza, ...): re-simulação e HUD comuns."""
import numpy as np

from ..desafios.foguete import FALHA, SUCESSO
from ..evolucao import simula
from ..rede import Arquitetura
from .base import Adaptador, Rodada

from ..palco.holo import AMARELO, CIANO, VERDE, VERMELHO  # noqa: E402,F401


class RodadaPop(Rodada):
    def __init__(self, D, hist, g):
        self.g, self.dt = g, D.dt
        genes = hist["genes"][g]
        amb, self.reg = simula(D, genes, int(hist["semente"][g]), gravar=True)
        self.amb = amb   # o ambiente re-simulado (clima, raios...) para o adaptador desenhar
        self.apt = amb.aptidao()
        self.mates = getattr(amb, "mates", None)
        self.lider = int(np.argmax(self.apt))
        est = self.reg["estado"]
        self.T = est.shape[1]
        feito = est != 0
        self.morte = np.where(feito.any(1), feito.argmax(1), -1)
        self.duracao = self.T * D.dt
        self.genes = genes
        self.n = len(genes)

    def i(self, t):
        return int(min(max(t / self.dt, 0), self.T - 1))

    def contagem(self, t):
        e = self.reg["estado"][:, self.i(t)]
        return int((e == SUCESSO).sum()), int((e == FALHA).sum())


class AdaptadorPopulacao(Adaptador):
    Desafio = None
    saidas = ()
    rotulos = ("SUCESSO", "FALHAS")

    def __init__(self, hist):
        self.hist = hist
        self.total_ger = len(hist["genes"])
        self.arq = Arquitetura(self.Desafio.camadas)
        self._cache = {}

    def rodada(self, g):
        if g not in self._cache:
            self._cache[g] = RodadaPop(self.Desafio, self.hist, g)
        return self._cache[g]

    def duracao_foco(self, rod, foco):
        m = rod.morte[foco]
        return (m + 1) * rod.dt + 1.0 if m >= 0 else rod.duracao

    def chaves_lento(self, rod, foco):
        m = rod.morte[foco]
        return [m * rod.dt] if m >= 0 else []

    def janela_lance(self, rod, foco):
        """Trecho essencial de um lance (para montagens): do começo até 0,5 s depois do fim."""
        m = rod.morte[foco]
        return 0.0, ((m + 1) * rod.dt + 0.5) if m >= 0 else rod.duracao

    def busca(self, rod, tipo):
        """Índice de um lance da geração: 'primeiro' (sucesso mais rápido), 'lento' (sucesso mais demorado),
        'quase' (falha que terminou mais perto do alvo), 'falha' (falha qualquer)."""
        est = rod.reg["estado"][:, -1]
        suc = np.where(est == SUCESSO)[0]
        fal = np.where(est == FALHA)[0]
        if tipo == "primeiro" and len(suc):
            return int(suc[np.argmin(rod.morte[suc])])
        if tipo == "lento" and len(suc):
            return int(suc[np.argmax(rod.morte[suc])])
        if tipo in ("quase", "falha") and len(fal):
            if tipo == "quase":
                return int(fal[np.argmax(rod.apt[fal])])
            return int(fal[0])
        return None

    # ------------------------------------------------------------ multidão de "fantasmas"
    def fantasmas(self, rod, maxn=90):
        """Índices dos indivíduos desenhados na multidão: TODOS os que acertaram (o público tem que ver os
        poucos que dão certo) e uma amostra uniforme dos demais, até `maxn` no total."""
        chave = ("fantasmas", maxn)
        if chave not in rod.__dict__:
            ok = np.where(rod.reg["estado"][:, -1] == SUCESSO)[0][: maxn // 2]
            resto = np.setdiff1d(np.arange(rod.n), ok)
            passo = max(1, int(np.ceil(len(resto) / max(maxn - len(ok), 1))))
            rod.__dict__[chave] = sorted(set(ok.tolist()) | set(resto[::passo].tolist()) | {rod.lider})
        return rod.__dict__[chave]

    def aparencia(self, rod, k, i, lider=False):
        """(cor, alfa_corpo, alfa_rastro) de um fantasma no passo i; None = já sumiu da tela.

        Ainda tentando: azul quase transparente (muitos juntos viram uma névoa de luz, que mostra por onde a
        turma passa). Errou: pisca vermelho e se dissolve em ~1 s (a tela não acumula destroços). Acertou:
        verde nítido e permanente, que ganha destaque justamente por ser raro."""
        m = rod.morte[k]
        e = rod.reg["estado"][k, i]
        if lider:
            return (VERDE if e == SUCESSO else VERMELHO if e == FALHA else AMARELO, 1.0, 0.85)
        if e == 0 or m < 0 or i < m:
            return (CIANO, 0.10, 0.06)
        idade = (i - m) * rod.dt
        if e == SUCESSO:
            return (VERDE, min(0.35 + idade * 1.5, 0.9), 0.45)
        if idade > 1.1:
            return None
        sobra = 1 - idade / 1.1
        return (VERMELHO, 0.5 * sobra ** 1.5 + (0.25 if idade < 0.12 else 0.0), 0.18 * sobra)

    def medidores(self, rod, t, foco):
        if foco is not None:   # replay de 1 lance: o HUD mostra o saldo da geração inteira
            t = rod.duracao
        s, f = rod.contagem(t)
        return [(self.rotulos[0], f"{s}/{rod.n}", s / rod.n, VERDE),
                (self.rotulos[1], f"{f}/{rod.n}", f / rod.n, VERMELHO)]

    def cerebro(self, rod, t, foco):
        k = rod.lider if foco is None else foco
        pesos = [(W[0], b[0]) for W, b in self.arq.desempacota(rod.genes[k:k + 1])]
        return dict(camadas=self.Desafio.camadas, pesos=pesos, ativ=rod.reg["ativ"][k, rod.i(t)],
                    saidas=self.saidas, titulo="CÉREBRO // LÍDER", cor=CIANO)

    def estado_cor(self, rod, k, i):
        e = rod.reg["estado"][k, i]
        return VERDE if e == SUCESSO else (VERMELHO if e == FALHA else CIANO)

    def sons(self, rod, t0, t1, modo, foco):
        ev = []
        ks = [foco] if (modo == "replay" and foco is not None) else range(rod.n)
        novos_f = novos_s = 0
        for k in ks:
            m = rod.morte[k]
            if m >= 0 and t0 <= m * rod.dt < t1:
                if rod.reg["estado"][k, m] == SUCESSO:
                    novos_s += 1
                else:
                    novos_f += 1
        if novos_f:
            ev.append((t0, self.som_falha, min(0.5 + 0.15 * novos_f, 1.3)))
        if novos_s:
            ev.append((t0, "ding", 2 if modo == "replay" else 1))
        return ev
