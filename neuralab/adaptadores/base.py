"""Contrato entre uma simulação e o motor de vídeo.

Para fazer um vídeo novo, crie uma subclasse de Adaptador e implemente os métodos abaixo.
O motor (neuralab/video.py) cuida de narração, legenda, HUD, câmera lenta, telestrador,
áudio e exportação. O adaptador só responde "o que existe no mundo no instante t".
"""


class Rodada:
    """Uma geração re-simulada com gravação completa. Atributos mínimos:

    g        geração (0-based)
    dt       passo da simulação (s)
    duracao  duração total gravada (s)
    """


class Adaptador:
    titulo = "EXPERIMENTO"          # aparece no cabeçalho
    experimento = "000"
    total_ger = 1
    cores = {}                      # nome -> (r, g, b), usadas no roteiro e nos destaques da legenda

    # ---- dados
    def rodada(self, g):
        """Re-simula (com cache) a geração g e devolve uma Rodada."""
        raise NotImplementedError

    def duracao_foco(self, rod, foco):
        """Duração (s) do lance/indivíduo `foco` (usada no replay)."""
        return rod.duracao

    def chaves_lento(self, rod, foco):
        """Instantes (s de simulação) que merecem câmera lenta num replay."""
        return []

    # ---- desenho
    def camera(self, rod, t, modo, foco):
        raise NotImplementedError

    def desenha(self, palco, rod, t, modo, foco):
        """Desenha cenário e agentes no palco 2.5D (sem chamar palco.desenha())."""
        raise NotImplementedError

    def ponto(self, rod, foco, nome, t):
        """Posição 3D de algo com nome (para o telestrador): 'goleiro', 'bola', ..."""
        raise NotImplementedError

    # ---- HUD
    def medidores(self, rod, t, foco):
        """[(titulo_painel, rotulo, valor 0-1, cor), (..)] — os dois painéis de medidor."""
        raise NotImplementedError

    def cerebro(self, rod, t, foco):
        """dict(camadas, pesos, ativ, saidas, titulo, cor) da rede mostrada no painel."""
        raise NotImplementedError

    # ---- som
    def sons(self, rod, t0, t1, modo, foco):
        """Eventos [(t_sim, tipo, intensidade)] entre t0 e t1 (tempo de simulação)."""
        return []

    def ambiente(self, dur):
        """Áudio ambiente opcional (np.array mono 48 kHz) ou None."""
        return None
