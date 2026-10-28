# Episódios gerados

Atualize esta tabela a cada vídeo entregue. Ao propor temas novos, **não repita nenhum desta lista**.

| EP | Tema | Comando | Estado | Duração | Resultado-chave | CTA final |
|---|---|---|---|---|---|---|
| 01 | Foguete (pouso) | `python gerar.py foguete` | só rascunho; roteiro simples antigo, precisa portar ao estilo novo | — | de 0 a 84 de 150 pousos | — |
| 02 | **Baliza** (estacionar entre dois carros) | `python gerar.py baliza` | **entregue**, 1080x1920, voz Charon 3.8 | 83,8 s | 16.068 batidas até aprender; 86% -> 35% no teste de estresse | LADEIRA ou CHUVA? (o mais votado vira o próximo) |
| 03 | **Robô andador** (aprender a andar, vista de lado) | `python gerar.py andador --sementes 11` | **entregue**, 1080x1920, voz Charon 3.8 (3ª requisição do dia; 1ª e 2ª foram de versões anteriores do roteiro) | 51,2 s | semente 11, 150 robôs, 70 gerações; 149/150 caem na ger. 1; 1º a chegar na ger. 2 (296 quedas); 24% alternam as pernas na ger. 36; 103/150 chegam na ger. 48; 5.140 quedas; gelo: 99% -> 26% | ESCADA ou LADEIRA? (o mais votado vira o próximo) |
| 04 | Pênalti (100 batedores x 100 goleiros) | `python gerar.py penalti` | só rascunho; usuário mandou deixar de lado | — | finta, leitura de corpo | — |

## Pendências conhecidas

- EP02: 84 s (analistas recomendavam ~40 s); pico de volume 0 dB nos efeitos.
- Portar o foguete ao roteiro/estilo da baliza; pênalti sem render final.
- EP03: câmera segue o líder; vista geral ainda mostra poucos robôs ao mesmo tempo; cena de queda repete o mesmo robô.
- Sequência natural do EP03: escada ou ladeira, conforme os votos.
- Sequência natural do EP02: baliza na LADEIRA ou na CHUVA, conforme os votos.

## Ideias ainda não feitas

Ver `docs/IDEIAS.md` (itens 4 a 10: robô andando, drone na tempestade, sumô de IAs, 1x1 goleiro x atacante,
polícia e ladrão, basquete, corrida de carrinhos).
