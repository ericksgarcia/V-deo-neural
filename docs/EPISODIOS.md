# Episódios gerados

Atualize esta tabela a cada vídeo entregue. Ao propor temas novos, **não repita nenhum desta lista**.

| EP | Tema | Comando | Estado | Duração | Resultado-chave | CTA final |
|---|---|---|---|---|---|---|
| 01 | Foguete (pouso) | `python gerar.py foguete` | só rascunho; roteiro simples antigo, precisa portar ao estilo novo | — | de 0 a 84 de 150 pousos | — |
| 02 | **Baliza** (estacionar entre dois carros) | `python gerar.py baliza` | **entregue**, 1080x1920, voz Charon 3.8 | 83,8 s | 16.068 batidas até aprender; 86% -> 35% no teste de estresse | LADEIRA ou CHUVA? (o mais votado vira o próximo) |
| 05 | **Polícia e ladrão** (2 policiais x 1 ladrão que rouba diamantes, labirinto) | `python gerar.py policia` (semente 7, 200 gerações, treino cacheado em `.cache/policia_v3_200_7.npz`) | **entregue**, 1080x1920, voz Charon 3.8 | 67,3 s | prisões 9% -> 69%; ladrão 0,1 -> 1,2 diamantes; ladrão da ger. 1 preso 79% x 72% do final contra a mesma polícia | TIME POLÍCIA ou TIME LADRÃO? (laço: "...tudo começou com" emenda em "Dois policiais atrás de um ladrão") |
| 04 | Pênalti (100 batedores x 100 goleiros) | `python gerar.py penalti` | só rascunho; usuário mandou deixar de lado | — | finta, leitura de corpo | — |

## Pendências conhecidas

- EP02: 84 s (analistas recomendavam ~40 s); pico de volume 0 dB nos efeitos.
- Portar o foguete ao roteiro/estilo da baliza; pênalti sem render final.
- Sequência natural do EP02: baliza na LADEIRA ou na CHUVA, conforme os votos.

- EP05: sem polícia "cercando" nem "laço no quarteirão" fortes nos dados; o cerco (2% -> 6% das prisões) entra como descoberta pequena. Zonas seguras do TikTok (HUD de baixo/topo) não foram ajustadas.

## Ideias ainda não feitas

Ver `docs/IDEIAS.md` (itens 4 a 10: robô andando, drone na tempestade, sumô de IAs, 1x1 goleiro x atacante,
basquete, corrida de carrinhos).
