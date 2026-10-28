# Episódios gerados

Atualize esta tabela a cada vídeo entregue. Ao propor temas novos, **não repita nenhum desta lista**.

| EP | Tema | Comando | Estado | Duração | Resultado-chave | CTA final |
|---|---|---|---|---|---|---|
| 01 | Foguete (pouso) | `python gerar.py foguete` | só rascunho; roteiro simples antigo, precisa portar ao estilo novo | — | de 0 a 84 de 150 pousos | — |
| 02 | **Baliza** (estacionar entre dois carros) | `python gerar.py baliza` | **entregue**, 1080x1920, voz Charon 3.8 | 83,8 s | 16.068 batidas até aprender; 86% -> 35% no teste de estresse | LADEIRA ou CHUVA? (o mais votado vira o próximo) |
| 03 | **Corrida de carrinhos** (baterias de 4, 2 voltas, todos contra todos) | `python gerar.py corrida --sementes 3,5` (semente 5, 240 ger., 160 carros) | **entregue**, 1080x1920, voz Charon 3.8 (1 requisição válida; 1 anterior falhou por chave inválida) | 71,2 s | 1º a terminar só na ger. 46 (2.485 batidas na parede); 127/160 terminam na ger. 230; melhor tempo 24,6 s -> 17,2 s; ultrapassagens por carro 0,4 -> 2,9 | ÓLEO ou CHUVA? (o mais votado vira o próximo) |
| 04 | Pênalti (100 batedores x 100 goleiros) | `python gerar.py penalti` | só rascunho; usuário mandou deixar de lado | — | finta, leitura de corpo | — |

## Pendências conhecidas

- EP02: 84 s (analistas recomendavam ~40 s); pico de volume 0 dB nos efeitos.
- Portar o foguete ao roteiro/estilo da baliza; pênalti sem render final.
- EP03: a voz leu mal "Acelera e vira" (cena 2), "ultrapassagem" (cena 6) e "Óleo na pista" (cena 11); o dono manteve a voz atual (sem nova requisição). "Aprenderam a defender" (cena 7) vem de uma métrica de bloqueio (segundos se jogando na frente de quem vem atrás), inferência e não prova. Nota do diretor: visual e narração ~7,5 antes dos ajustes locais; barras já corrigidas. Se refizer a voz: trocar esses trechos.
- Dica de ambiente: o TTS funciona pelo proxy SEM definir `GEMINI_API_KEY` (uma chave falsa na URL falha e gasta o ledger).
- Sequência natural do EP02: baliza na LADEIRA ou na CHUVA, conforme os votos.

## Ideias ainda não feitas

Ver `docs/IDEIAS.md` (itens 4 a 10: robô andando, drone na tempestade, sumô de IAs, 1x1 goleiro x atacante,
polícia e ladrão, basquete, corrida de carrinhos).
