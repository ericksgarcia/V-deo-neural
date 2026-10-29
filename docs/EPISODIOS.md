# Episódios gerados

Atualize esta tabela a cada vídeo entregue. Ao propor temas novos, **não repita nenhum desta lista**.

| EP | Tema | Comando | Estado | Duração | Resultado-chave | CTA final |
|---|---|---|---|---|---|---|
| 01 | Foguete (pouso) | `python gerar.py foguete` | só rascunho; roteiro simples antigo, precisa portar ao estilo novo | — | de 0 a 84 de 150 pousos | — |
| 02 | **Baliza** (estacionar entre dois carros) | `python gerar.py baliza` | **entregue**, 1080x1920, voz Charon 3.8 | 83,8 s | 16.068 batidas até aprender; 86% -> 35% no teste de estresse | LADEIRA ou CHUVA? (o mais votado vira o próximo) |
| 03 | **Robô andador** (aprender a andar, vista de lado) | `python gerar.py andador --sementes 11` | **entregue**, 1080x1920, voz Charon 3.8 (3ª requisição do dia; 1ª e 2ª foram de versões anteriores do roteiro) | 51,2 s | semente 11, 150 robôs, 70 gerações; 149/150 caem na ger. 1; 1º a chegar na ger. 2 (296 quedas); 24% alternam as pernas na ger. 36; 103/150 chegam na ger. 48; 5.140 quedas; gelo: 99% -> 26% | ESCADA ou LADEIRA? (o mais votado vira o próximo) |
| 03 | **Drone na tempestade** (vento em rajadas + raios, pouso na plataforma) | `python gerar.py drone` (semente 17, 340 gerações; sementes testadas 5,11,17) | **entregue**, 1080x1920, voz Charon 3.8 | 72,4 s | 32.857 quedas; 138/150 pousam na ger. 340; teste de estresse (40 tempestades novas): 65% -> 21% com vento +80% | SUMÔ DE IAs ou POLÍCIA E LADRÃO? (comentar SUMÔ ou POLÍCIA) |
| 03 | **Corrida de carrinhos** (baterias de 4, 2 voltas, todos contra todos) | `python gerar.py corrida --sementes 3,5` (semente 5, 240 ger., 160 carros) | **entregue**, 1080x1920, voz Charon 3.8 (1 requisição válida; 1 anterior falhou por chave inválida) | 71,2 s | 1º a terminar só na ger. 46 (2.485 batidas na parede); 127/160 terminam na ger. 230; melhor tempo 24,6 s -> 17,2 s; ultrapassagens por carro 0,4 -> 2,9 | ÓLEO ou CHUVA? (o mais votado vira o próximo) |
| 05 | **Sumô de IAs** (treino só A, só B e os dois, em rodadas curta/média/longa) | `python gerar.py sumo` (semente 10, 186 gerações em 9 fases) | **entregue**, 1080x1920, voz Charon 3.8 (1 requisição) | 82,9 s | 91% das lutas acabavam com alguém caindo sozinho -> 0%; quem treina sozinho sobe e o congelado cai (ex.: 43% -> 67%); juntas, 50% das lutas empatam; 60% esperam no centro aos 2 s; azul final vence 97% da rosa de G1, só 14% da rosa final | "Você treinaria só a azul, só a rosa ou as duas?" (comenta A, B ou AB) |
| 05 | **Polícia e ladrão** (100 x 100, arena com paredes) | `python gerar.py policia --sementes 5` | **entregue**, 1080x1920, voz **Achird** 3.8 (1 requisição) | 67,2 s | 3 → 56 fugas em 16 gerações; polícia escolhe o mesmo lado (97%); troca de lado do ladrão: fugas 37 → 77; 98% mesmo lado na ger. 250 | TIME LADRÃO ou TIME POLÍCIA? (o mais votado ganha um motor mais rápido no próximo vídeo: **promessa feita ao público**) |
| 04 | Pênalti (100 batedores x 100 goleiros) | `python gerar.py penalti` | só rascunho; usuário mandou deixar de lado | — | finta, leitura de corpo | — |

## Pendências conhecidas

- EP03: voz leu "Caiu" como "Caio" (cena 4) e "sumô" como "sumou" (CTA); corrigir exige nova requisição TTS (pedir licença). Visual: gráfico com espaço vazio, botões do CTA pequenos, barra do estresse sem animação. 72 s (meta 60 s).
- EP05: o Whisper médio ouve "muda o jogo" como "nudo do jogo", "erra o lado" como "é rolado" (cena 8) e "aprendendo junto" como "prendendo" (cena 1): a voz atropela essas falas. Regravar custa 1 requisição Achird (2ª das 10 do dia; pedir licença). Cofre ainda estoura em branco quando muitos ladrões se acumulam (gerações 102 e 250).
- EP05: cumprir o CTA: o lado mais votado ganha um motor mais rápido (`V_LAD`/`V_POL` em `neuralab/desafios/policia.py`) no EP06.

- EP02: 84 s (analistas recomendavam ~40 s); pico de volume 0 dB nos efeitos.
- Portar o foguete ao roteiro/estilo da baliza; pênalti sem render final.
- EP03: câmera segue o líder; vista geral ainda mostra poucos robôs ao mesmo tempo; cena de queda repete o mesmo robô.
- Sequência natural do EP03: escada ou ladeira, conforme os votos.
- EP03: a voz leu mal "Acelera e vira" (cena 2), "ultrapassagem" (cena 6) e "Óleo na pista" (cena 11); o dono manteve a voz atual (sem nova requisição). "Aprenderam a defender" (cena 7) vem de uma métrica de bloqueio (segundos se jogando na frente de quem vem atrás), inferência e não prova. Nota do diretor: visual e narração ~7,5 antes dos ajustes locais; barras já corrigidas. Se refizer a voz: trocar esses trechos.
- Dica de ambiente: o TTS funciona pelo proxy SEM definir `GEMINI_API_KEY` (uma chave falsa na URL falha e gasta o ledger).
- EP05: 83 s (mais longo que o ideal; pedido do dono por explicação). Voz do TTS errou nada de relevante; Whisper local confere. Render leva ~12 min a 1080x1920.
- Sequência natural do EP02: baliza na LADEIRA ou na CHUVA, conforme os votos.

## Ideias ainda não feitas

Ver `docs/IDEIAS.md` (itens 4 a 10: robô andando, drone na tempestade, sumô de IAs, 1x1 goleiro x atacante,
~~polícia e ladrão~~ (feito, EP05), basquete, corrida de carrinhos).
