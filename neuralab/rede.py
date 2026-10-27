"""Rede neural densa avaliada em lote para a população inteira de uma vez."""
import numpy as np


class Arquitetura:
    def __init__(self, camadas):
        self.camadas = list(camadas)
        self.formas = [(a, b) for a, b in zip(self.camadas[:-1], self.camadas[1:])]
        self.tamanho = sum(a * b + b for a, b in self.formas)

    def aleatoria(self, n, rng):
        return rng.normal(0.0, 1.0, (n, self.tamanho)).astype(np.float32)

    def desempacota(self, genes):
        """genes (P, tamanho) -> lista de (W (P,a,b), b (P,b))."""
        out, i = [], 0
        for a, b in self.formas:
            W = genes[:, i:i + a * b].reshape(-1, a, b)
            i += a * b
            out.append((W, genes[:, i:i + b]))
            i += b
        return out

    def avalia(self, params, x):
        """x (P, entradas) -> (saida (P, saidas), ativacoes por camada)."""
        ativ = [x]
        h = x
        for k, (W, b) in enumerate(params):
            h = np.einsum("pa,pab->pb", h, W) + b
            h = np.tanh(h)
            ativ.append(h)
        return h, ativ
