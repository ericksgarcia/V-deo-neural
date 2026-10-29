# Episódios gerados

Atualize esta tabela a cada vídeo entregue. Ao propor temas novos, **não repita nenhum desta lista**.

| EP | Tema | Comando | Estado | Duração | Resultado-chave | CTA final |
|---|---|---|---|---|---|---|
| 01 | Foguete (pouso) | `python gerar.py foguete` | só rascunho; roteiro simples antigo, precisa portar ao estilo novo | — | de 0 a 84 de 150 pousos | — |
| 02 | **Baliza** (estacionar entre dois carros) | `python gerar.py baliza` | **entregue**, 1080x1920, voz Charon 3.8 | 83,8 s | 16.068 batidas até aprender; 86% -> 35% no teste de estresse | LADEIRA ou CHUVA? (o mais votado vira o próximo) |
| 05 | **Cruzamento sem semáforo** (8 carros, 4 ruas, mesmo cérebro) | `python gerar.py cruzamento` (semente 7, 300 gerações) | **entregue**, 1080x1920, voz Charon 3.8 | 76,9 s | de 1 em 150 sem bater (ger. 1) a 82% em 600 trânsitos novos (ger. 300); descobertas: frear e esperar (ger. 10), uma rua de cada vez (ger. 15), parar menos (ger. 66, espera 43% → 29%) | AMBULÂNCIA ou PEDESTRE? (o mais votado vira o próximo) |
| 04 | Pênalti (100 batedores x 100 goleiros) | `python gerar.py penalti` | só rascunho; usuário mandou deixar de lado | — | finta, leitura de corpo | — |

## Temas já feitos fora do repositório

O dono do canal já publicou vídeo de TODAS estas ideias (sem arquivos aqui). **Não propor de novo:**
robô aprendendo a andar, drone na tempestade, sumô de IAs, goleiro x atacante 1 contra 1, polícia e ladrão num
labirinto, arremesso de basquete, corrida de carrinhos. (Se o dono citar outros, acrescente aqui.)

## Pendências conhecidas

- EP02: 84 s (analistas recomendavam ~40 s); pico de volume 0 dB nos efeitos.
- Portar o foguete ao roteiro/estilo da baliza; pênalti sem render final.
- Sequência natural do EP02: baliza na LADEIRA ou na CHUVA, conforme os votos.

- EP05: 77 s (meta ~55 s); texto do HUD pequeno; o ritmo da voz varia de 1,8 a 3,5 palavras/s. Pedido do dono: não mostrar o resultado no início, mostrar a melhora ao longo do vídeo (aplicado aqui, vale para os próximos).

## Ideias ainda não feitas

Nenhuma pendente em `docs/IDEIAS.md` (todas já feitas, ver seção acima). Descartadas ao propor o EP05 mas ainda
inéditas: blefe (truco), formigas (trilha e guerra), cardume contra tubarão.
