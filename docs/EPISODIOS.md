# Episódios gerados

Atualize esta tabela a cada vídeo entregue. Ao propor temas novos, **não repita nenhum desta lista**.

| EP | Tema | Comando | Estado | Duração | Resultado-chave | CTA final |
|---|---|---|---|---|---|---|
| 01 | Foguete (pouso) | `python gerar.py foguete` | só rascunho; roteiro simples antigo, precisa portar ao estilo novo | — | de 0 a 84 de 150 pousos | — |
| 02 | **Baliza** (estacionar entre dois carros) | `python gerar.py baliza` | **entregue**, 1080x1920, voz Charon 3.8 | 83,8 s | 16.068 batidas até aprender; 86% -> 35% no teste de estresse | LADEIRA ou CHUVA? (o mais votado vira o próximo) |
| 05 | **Polícia e ladrão** (100 x 100, arena com paredes) | `python gerar.py policia --sementes 5` | **entregue**, 1080x1920, voz **Achird** 3.8 (1 requisição) | 67,2 s | 3 → 56 fugas em 16 gerações; polícia escolhe o mesmo lado (97%); troca de lado do ladrão: fugas 37 → 77; 98% mesmo lado na ger. 250 | TIME LADRÃO ou TIME POLÍCIA? (o mais votado ganha um motor mais rápido no próximo vídeo: **promessa feita ao público**) |
| 04 | Pênalti (100 batedores x 100 goleiros) | `python gerar.py penalti` | só rascunho; usuário mandou deixar de lado | — | finta, leitura de corpo | — |

## Pendências conhecidas

- EP05: o Whisper médio ouve "muda o jogo" como "nudo do jogo", "erra o lado" como "é rolado" (cena 8) e "aprendendo junto" como "prendendo" (cena 1): a voz atropela essas falas. Regravar custa 1 requisição Achird (2ª das 10 do dia; pedir licença). Cofre ainda estoura em branco quando muitos ladrões se acumulam (gerações 102 e 250).
- EP05: cumprir o CTA: o lado mais votado ganha um motor mais rápido (`V_LAD`/`V_POL` em `neuralab/desafios/policia.py`) no EP06.

- EP02: 84 s (analistas recomendavam ~40 s); pico de volume 0 dB nos efeitos.
- Portar o foguete ao roteiro/estilo da baliza; pênalti sem render final.
- Sequência natural do EP02: baliza na LADEIRA ou na CHUVA, conforme os votos.

## Ideias ainda não feitas

Ver `docs/IDEIAS.md` (itens 4 a 10: robô andando, drone na tempestade, sumô de IAs, 1x1 goleiro x atacante,
~~polícia e ladrão~~ (feito, EP05), basquete, corrida de carrinhos).
