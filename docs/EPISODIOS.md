# Episódios gerados

Atualize esta tabela a cada vídeo entregue. Ao propor temas novos, **não repita nenhum desta lista**.

| EP | Tema | Comando | Estado | Duração | Resultado-chave | CTA final |
|---|---|---|---|---|---|---|
| 01 | Foguete (pouso) | `python gerar.py foguete` | só rascunho; roteiro simples antigo, precisa portar ao estilo novo | — | de 0 a 84 de 150 pousos | — |
| 02 | **Baliza** (estacionar entre dois carros) | `python gerar.py baliza` | **entregue**, 1080x1920, voz Charon 3.8 | 83,8 s | 16.068 batidas até aprender; 86% -> 35% no teste de estresse | LADEIRA ou CHUVA? (o mais votado vira o próximo) |
| 05 | **Sumô de IAs** (treino só A, só B e os dois, em rodadas curta/média/longa) | `python gerar.py sumo` (semente 10, 186 gerações em 9 fases) | **entregue**, 1080x1920, voz Charon 3.8 (1 requisição) | 82,9 s | 91% das lutas acabavam com alguém caindo sozinho -> 0%; quem treina sozinho sobe e o congelado cai (ex.: 43% -> 67%); juntas, 50% das lutas empatam; 60% esperam no centro aos 2 s; azul final vence 97% da rosa de G1, só 14% da rosa final | "Você treinaria só a azul, só a rosa ou as duas?" (comenta A, B ou AB) |
| 04 | Pênalti (100 batedores x 100 goleiros) | `python gerar.py penalti` | só rascunho; usuário mandou deixar de lado | — | finta, leitura de corpo | — |

## Pendências conhecidas

- EP02: 84 s (analistas recomendavam ~40 s); pico de volume 0 dB nos efeitos.
- Portar o foguete ao roteiro/estilo da baliza; pênalti sem render final.
- EP05: 83 s (mais longo que o ideal; pedido do dono por explicação). Voz do TTS errou nada de relevante; Whisper local confere. Render leva ~12 min a 1080x1920.
- Sequência natural do EP02: baliza na LADEIRA ou na CHUVA, conforme os votos.

## Ideias ainda não feitas

Ver `docs/IDEIAS.md` (itens 4 a 10: robô andando, drone na tempestade, sumô de IAs, 1x1 goleiro x atacante,
polícia e ladrão, basquete, corrida de carrinhos).
