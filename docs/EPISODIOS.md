# Episódios gerados

Atualize esta tabela a cada vídeo entregue. Ao propor temas novos, **não repita nenhum desta lista**.

| EP | Tema | Comando | Estado | Duração | Resultado-chave | CTA final |
|---|---|---|---|---|---|---|
| 01 | Foguete (pouso) | `python gerar.py foguete` | só rascunho; roteiro simples antigo, precisa portar ao estilo novo | — | de 0 a 84 de 150 pousos | — |
| 02 | **Baliza** (estacionar entre dois carros) | `python gerar.py baliza` | **entregue**, 1080x1920, voz Charon 3.8 | 83,8 s | 16.068 batidas até aprender; 86% -> 35% no teste de estresse | LADEIRA ou CHUVA? (o mais votado vira o próximo) |
| 03 | **Drone na tempestade** (pousar com vento) | `python gerar.py drone --sementes 13` (semente 13, 150 drones, 160 gerações) | **entregue**, 1080x1920, voz Charon 3.8 (1 req. válida) | 88,5 s | 1º pouso na ger. 27 após 4.049 quedas; ger. 158: 62/150 pousam; bateria que sobra 14% -> 40%; melhor drone 100% -> 52% com vento 40% mais forte | SUMÔ DE IAs ou POLÍCIA E LADRÃO? (o mais votado vira o próximo) |
| 04 | Pênalti (100 batedores x 100 goleiros) | `python gerar.py penalti` | só rascunho; usuário mandou deixar de lado | — | finta, leitura de corpo | — |

## Pendências conhecidas

- EP02: 84 s (analistas recomendavam ~40 s); pico de volume 0 dB nos efeitos.
- EP03: 88 s (analistas recomendam ~60-70 s; cortar cena 9 e repetição de quedas exigiria nova voz); ledger registra 1 requisição falha (chave inválida) além da válida.
- Portar o foguete ao roteiro/estilo da baliza; pênalti sem render final.
- O robô andando já foi feito (fora deste repositório/branch). Sequência natural do EP02: baliza na LADEIRA ou na CHUVA, conforme os votos.

## Ideias ainda não feitas

Ver `docs/IDEIAS.md`: itens 1 a 10 são as propostas novas (próximo da fila: **1. Paciente Zero**); depois vêm
sumô de IAs (16), 1x1 goleiro x atacante (17), polícia e ladrão (18), basquete (19) e corrida de carrinhos (20).
Robô (14) e drone (15) já foram feitos.
