# O que os vídeos de referência ensinam

Dois vídeos do canal @circuito_cero.1 (espanhol), assistidos quadro a quadro (ffmpeg) e transcritos
localmente (Whisper). A ideia aqui não é copiar, e sim entender **por que eles prendem**.

## Vídeo 1: "Esta IA no sabe manejar" (50 s, carros estacionando)

| tempo | o que acontece |
|---|---|
| 0–6 s | "Esta IA no sabe manejar. Y su misión es estacionarse aquí, entre dos autos." Missão concreta e visual. |
| 6–15 s | "150 autos, cerebros al azar. Los mejores sobreviven… con pequeñas mutaciones." Regra do jogo em 2 frases. |
| 15–20 s | "Generación 25: ya aprendió a llegar… pero nadie le enseñó a frenar." Primeira virada (com humor). |
| 20–26 s | "Generación 33: uno, solo uno, frena, se alinea y se estaciona." O herói aparece. |
| 27–38 s | "Generación 128: 128 de 150 se estacionan solos." O resultado. |
| 38–45 s | "Nadie le programó cómo estacionarse. Aprendió chocando. ¿Qué le enseño ahora?" Moral e pedido de comentário. |

Pontos fortes: missão clara, número da geração como "capítulo", herói único, laço (o último quadro volta ao primeiro).
Pontos fracos: arco previsível (só melhora), sem conflito, gancho fraco ("não sabe dirigir" não surpreende).

## Vídeo 2: "Atrapadas" (94 s, pega-pega entre duas IAs). É o mais forte.

Transcrição resumida, com as técnicas em negrito:

- 0–7 s: "Puse a dos IAs a jugar a las atrapadas… **y una aprendió a tenderle trampas a la otra**." → **gancho = o resultado mais surpreendente, logo de cara** (loop aberto: *como?*).
- 7–16 s: "El naranja persigue. El azul huye. En medio, una isla… 100 de cada lado." → **conflito com dois times** (dá para torcer).
- 20–26 s: "Generación 40: el naranja aprende a rodear la isla… y ya atrapa a casi la mitad."
- 26–38 s: "**Pero** el azul encuentra un truco. Da vueltas… y el naranja lo sigue. **Y lo sigue. Y lo sigue.**" → **virada + repetição como ritmo** + **truque com nome** ("El carrusel").
- 38–56 s: "Generación 200: el naranja deja de perseguir… se queda esperando… y el azul se mete solito en la trampa." → **contra-ataque**, com cartão "La emboscada: 76%".
- 56–67 s: "**Pero** el azul también aprende… frena, o mete reversa. Ahora funciona 4 de cada 100." → **corrida armamentista** (cada lado responde ao outro).
- 67–79 s: "Puse a pelear a todas las generaciones… ¿quién atrapa más seguido al azul final? **El naranja de la generación 1**, que ni sabe manejar." → **final irônico vindo dos dados** (torneio entre gerações).
- 79–89 s: "Nadie les enseñó… Lo inventaron jugando. **¿A cuál le vas?** Naranja o azul." → **chamada que obriga a escolher um lado** (comentário tribal).

## Regras que viraram parte da base

1. **Gancho = a coisa mais impressionante que aconteceu**, já nos 2 primeiros segundos, mostrada em replay.
2. **Dois lados** sempre que possível (co-evolução), ou a IA contra o desafio.
3. **Virada a cada ~8–12 s**: "mas…", "até que…", "dez gerações depois…".
4. **Truques com nome** + cartão de "DESCOBERTA #n" com o número antes/depois.
5. **Todo número sai do treino.** O roteiro só afirma o que os dados confirmam (há checagens no código e um analista só para isso).
6. **Final irônico tirado dos dados** (torneio entre gerações) e **chamada com escolha de lado**.
7. **Laço**: o último quadro funde no primeiro, para quem assistir de novo.

## O que fizemos melhor

- **Visual próprio**: maquete 2.5D flutuando num laboratório holográfico + HUD de vidro com medidores,
  linha do tempo com marcos das descobertas, console de eventos e rede neural com pulsos
  (os vídeos de referência usam um painel plano 2D).
- **Replay com telestrador**: câmera lenta automática nos momentos-chave, setas e círculos à mão
  ("CORPO: ESQUERDA", "CAIU!"), câmera que se aproxima do lance.
- **Legenda palavra a palavra sincronizada pela voz real** (Whisper), não por estimativa.
- **Analistas** que revisam roteiro, narração, visual, retenção e engajamento antes de publicar.
- **Tema brasileiro** (pênalti), com um fato que gera debate: a taxa de gol da IA cai na mesma faixa do futebol profissional.
