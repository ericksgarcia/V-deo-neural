# Vídeo Neural

Fábrica de vídeos verticais (TikTok/Reels) de **IA aprendendo sozinha**. Cada vídeo é uma
simulação real: redes neurais evoluem por seleção natural, e o vídeo conta o que aconteceu,
**sem inventar nenhum número**.

```
treino real  ->  roteiro tirado dos dados  ->  narração + legenda sincronizada  ->  holograma 2D + HUD  ->  MP4
                         ^                                                                         |
                         +------------------------ analistas (Claude) <--------------------------- +
```

## Episódios prontos

> Lista completa e atual em `docs/EPISODIOS.md`; próximos temas (em ordem) em `docs/IDEIAS.md`. A tabela abaixo é só um resumo dos primeiros.

| comando | o que é |
|---|---|
| `python gerar.py penalti` | **EP 04 · Pênalti**: 100 batedores x 100 goleiros co-evoluindo. Surgem paciência, leitura de corpo e finta. |
| `python gerar.py foguete` | EP 01 · Foguete: de 0 a 84 de 150 pousos. |
| `python gerar.py baliza` | EP 02 · Baliza: estacionar em paralelo entre dois carros. |

**Narração:** uma única chamada ao TTS por episódio (mesmo timbre do início ao fim). A voz gerada acelera
nas frases longas e arrasta nas curtas, então cada fala é ajustada para ~2,6 palavras/s (`ritmo` em
`audio.narra_lote`) e o motor confere com o Whisper local se a voz disse o que estava escrito e se nenhuma
fala ficou rápida demais, refazendo a narração até 3 vezes se precisar. Escreva frases curtas: elas saem
mais naturais e dão respiro à legenda.

Opções úteis: `--rascunho` (meia resolução, rápido), `--sem-voz` (só legenda), `--so-roteiro`,
`--sementes 3,5,7` (treina várias e escolhe a melhor história), `--voz Achird` (a voz do canal é SEMPRE Achird no Gemini TTS 3.8; travado em `audio.py`, veja `docs/NARRACAO.md`).

Saída em `saida/`: o vídeo, `*_legenda.txt` (texto do post) e `*_analise/` (roteiro com tempos,
checagem da voz, quadros-chave e mosaico, que são o material dos analistas).

## Instalação

```bash
sudo apt install ffmpeg libcairo2-dev   # ffmpeg + cairo (+ fontes Inter e JetBrains Mono)
pip install -r requirements.txt
export GEMINI_API_KEY=...                # só para a narração (TTS); sem ela o vídeo sai só com legenda
```

**Custos:** a única API usada é o **TTS do Gemini**, só para a voz. Transcrição e sincronia da legenda
usam o **Whisper local** (faster-whisper, grátis). A análise dos vídeos é feita pelos analistas do Claude Code.

## Treino e visual (desde o EP03)

- **Treino robusto** (`evolucao.treina`): cada indivíduo é testado em 4 largadas (a 1ª é a padrão, as outras cada vez
  mais variadas) e a nota é 80% média + 20% pior caso. O melhor aprende a regra, não decora a largada. Medido na baliza
  (semente 5): 51%/20% (largada normal/difícil) no treino clássico contra 100%/66% no robusto. `hist["robusto"]` guarda o
  acerto nas largadas extras e entra na escolha da semente. `treina(..., robusto=False)` volta ao clássico.
- **Multidão de fantasmas** (`AdaptadorPopulacao.fantasmas/aparencia`): até 90 indivíduos ao mesmo tempo, quase
  transparentes (a soma aditiva de luz vira uma névoa que mostra por onde a turma passa). Quem erra pisca vermelho e
  se dissolve em ~1 s; quem acerta fica verde e nítido, sempre incluído. Poucos acertos aparecem com força.

## Layout v3 e retenção automática (out/2026)

A ação ocupa a tela (sem a fileira de log/rede, ilegível no celular), a legenda fica dentro da cena e longe dos botões do
TikTok, e o motor faz sozinho: **trilha de descobertas** (casas "? ? ?" que abrem a cada cartão até o TESTE FINAL),
**revelação em cada `<long pause>`** (música some, riser, impacto + zoom-soco; barra do vencedor do teste escondida até a voz
revelar), zoom lento nas cenas ao vivo, simulação ao fundo das telas de dados, números da legenda em amarelo e trilha
sonora que cresce. O que o roteiro precisa fornecer está em `docs/ROTEIRO.md` §13 (o conferidor avisa).

## Como a base funciona (para fazer QUALQUER vídeo)

```
neuralab/
  rede.py, evolucao.py, coevolucao.py   redes neurais + algoritmo genético (1 ou 2 populações)
  desafios/        simulações: foguete, baliza, penalti (física simples, vetorizada em numpy)
  palco/           MOTOR 2D HOLOGRÁFICO + HUD (genéricos, não sabem qual é o desafio)
    holo.py          câmera 2D (zoom, giro, tremida) + primitivas neon: linha, forma, rastro, cone,
                     pulso, partículas, brilho; mistura aditiva e bloom real
    arte.py          artes prontas: avatar (pessoa vista de cima, pose em pé <-> mergulho), bola,
                     carro de cima, foguete de lado, explosão, placa holográfica, cotas, poeira,
                     aberração cromática e varredura
    kit.py           HUD: painéis de vidro, medidores, linha do tempo, console, rede neural,
                     moldura de câmera, cartão de descoberta, replay, telestrador, legenda, gráficos
  adaptadores/     a ÚNICA parte específica de cada vídeo: "o que desenhar no instante t"
  roteiros/        cenas + falas montadas a partir dos dados (com checagens de honestidade)
  video.py         MOTOR DE VÍDEO: narração, sincronia, câmera lenta, HUD, áudio, exportação
  audio.py         voz (Gemini TTS em uma chamada só), trilha, efeitos (torcida, chute, rede...)
  fala.py          Whisper local: alinhamento palavra a palavra e checagem da pronúncia
ferramentas/ver_video.py   "assiste" qualquer vídeo: quadros, mosaico, cortes, transcrição
.claude/agents/            analistas (roteiro, narração, visual, retenção, engajamento, diretor)
```

### Receita para um vídeo novo

1. **Simulação** em `neuralab/desafios/` (uma classe com `observa()`, `passo()`, `aptidao()`).
   Para dois lados, siga `penalti.py` + `coevolucao.py`.
2. **Adaptador** em `neuralab/adaptadores/` herdando de `AdaptadorPopulacao` (ou `Adaptador`):
   `camera()` (uma `Camera2D`), `desenha()` (monte a cena com `h.linha`, `h.forma`, `R.avatar`,
   `R.veiculo_topo`, `R.foguete_lado`...),
   `ponto()` (alvos do telestrador). O resto (HUD, medidores, rede, som) já vem pronto.
   `adaptadores/baliza.py` tem ~95 linhas.
3. **Roteiro** em `neuralab/roteiros/`: uma lista de cenas (dicionários).
   ```python
   dict(tipo="replay", ger=126, foco=1, fala="O corpo mostra um canto. A bola vai no outro.",
        cartao={"numero": 4, "rotulo": "BATEDOR", "nome": "A FINTA", "stat": "FINTAS QUE VIRAM GOL 89%", "cor": AMARELO})
   ```
   Tipos: `ao_vivo` (geração inteira), `replay` (um lance em câmera lenta), `grafico`, `barras`, `final`.
   O motor ajusta durações pela voz, a velocidade da simulação e a câmera lenta automaticamente.
   **Sem círculos/marcações na cena** (telestrador desligado; nada de anel "CAMPEÃO"): ver `CLAUDE.md`.
4. Registre em `gerar.py`.

## Analistas (Claude Code)

Ficam em `.claude/agents/` e rodam com o seu plano do Claude (sem API extra):

| analista | quando | olha |
|---|---|---|
| `analista-tema` | ANTES de implementar | triagem do tema (nota ≥ 14/20, ineditismo na web, potencial no nicho) |
| `analista-roteiro` | antes de renderizar | gancho, loops abertos, viradas, clareza, honestidade dos números |
| `analista-narracao` | depois do áudio | voz x roteiro (Whisper), ritmo, pausas, pronúncia |
| `analista-visual` | rascunho | legibilidade, zonas seguras do TikTok, clareza da ação, acabamento |
| `analista-retencao` | rascunho | curva de retenção estimada, pontos de deslize, cortes |
| `analista-engajamento` | antes da voz e de publicar | se o vídeo é visto ATÉ O FINAL (mapa de loops abertos), comentar/compartilhar, legenda e hashtags |
| `diretor` | tudo | orquestra os cinco e só aprova com todas as notas >= 8 |

No Claude Code: *"use o diretor para revisar o episódio do pênalti"*.

**Roteiro:** o guia v2 (`docs/ROTEIRO.md`) é obrigatório; `python ferramentas/confere_roteiro.py` confere seus limites (duração, números, CTA sem votação, laço) a partir da saída de `--so-roteiro`.

Veja também `docs/ANALISE_REFERENCIAS.md` (o que os vídeos de referência ensinam) e `docs/IDEIAS.md` (próximos episódios).
