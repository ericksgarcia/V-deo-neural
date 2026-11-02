# Luz da Palavra

Canal separado do de IA. Formato: vídeo vertical 1080x1920, **imagem de fundo gerada no Replicate**
(**flux-schnell**, 9:16, ampliada 2x com nitidez) com zoom lento, **narração no Gemini TTS** (`gemini-3.8-flash-tts`, **voz Achird**), referência bíblica no topo,
legenda em serifa creme com palavra-chave dourada, cartões de re-gancho e botão "Comente: AMÉM".

```bash
python luz_da_palavra/temas.py                                          # temas feitos e quando liberam (2 meses)
python luz_da_palavra/temas.py --checa "lazaro chorou"                  # há algo parecido no prazo?
python luz_da_palavra/conferir.py luz_da_palavra/roteiros/ep02_lazaro.json   # confere ganchos (zero FALHA)
python luz_da_palavra/gerar.py luz_da_palavra/roteiros/ep02_lazaro.json --so-texto     # texto + tempo previsto
python luz_da_palavra/gerar.py luz_da_palavra/roteiros/ep02_lazaro.json --sem-imagens  # rascunho (fundo provisório)
python luz_da_palavra/gerar.py luz_da_palavra/roteiros/ep02_lazaro.json                # final
```

Saída: `saida/luz/<slug>.mp4` e `saida/luz/<slug>_legenda.txt`.

- **Chaves** (nunca no git): variáveis de ambiente `REPLICATE_API_TOKEN` (site permitido `api.replicate.com`) e `GEMINI_API_KEY`
  (site permitido `generativelanguage.googleapis.com`), cadastradas em Network secrets do ambiente; ou, local, `.cache/luz.env`.
  A chave do Gemini vai no cabeçalho `x-goog-api-key`, não na URL.
- **Rede:** o ambiente precisa liberar `api.replicate.com` e `replicate.delivery` (imagens) e
  `generativelanguage.googleapis.com` (voz).
- **Custo:** 1 requisição de voz e 1 imagem por prompt; tudo fica em `.cache/luz/<slug>/`. Mudar o texto de
  qualquer fala (ou o estilo/voz) = nova requisição de voz. Mudar `card`, `titulo`, `cta`, `*destaques*`,
  `legenda`, `velocidade` ou `teto_pausa` NÃO gasta nada.
- **Ritmo:** ajustado localmente (pausas cortadas para `teto_pausa`, pausa de suspense = o dobro; `velocidade`
  via atempo, sem mudar o tom). Alvo 40-55 s.

## Regras do dono (nov/2026)

- **Voz: SEMPRE Achird.** **UMA requisição de voz por vídeo**: o gerador trava (`.cache/luz/<slug>/uso_voz.json`);
  outra só com licença do dono (`--autorizo-nova-voz`).
- **Tom (identidade do canal):** amigo cristão caloroso revelando um detalhe escondido da Bíblia; reverente, cheio de
  assombro; suspense amigável antes de cada revelação; final terno e esperançoso. Nunca pregador gritando, trailer,
  sombrio ou robótico (`ESTILO_VOZ` em `gerar.py`).
- **Imagens (decisão de 02/nov/2026):** SEMPRE o modelo `black-forest-labs/flux-schnell` no Replicate, com pedido de
  fotografia **ultra realista** (câmera/lente reais, luz natural, textura real; nada de cara de ilustração, pintura,
  3D ou CGI; `ESTILO_IMG` é anexado a todo prompt). Natureza variada (montanhas, florestas, lagos, cachoeiras, céu,
  desertos, oliveiras) com cores vivas porém verdadeiras. Escreva os prompts de cena em inglês, descrevendo uma FOTO
  de um lugar real; sem rosto de Jesus, sem texto na imagem. Letra com halo escuro + contorno para ler em qualquer fundo.
- **Limite do Replicate:** conta com pouco crédito leva 429; o gerador espera e tenta de novo sozinho (~4 min por vídeo).
- **Voz por episódio:** `estilo_extra` no JSON acrescenta direção de voz específica do vídeo (ex.: onde sussurrar).
  `voz_cache` aponta um áudio antigo já pago (usado no EP01, que tem o estilo antigo).

## Transições entre imagens (decisão de 02/nov/2026)

Sem soco de zoom e sem corte seco. A troca é uma **fusão de cinema** de 1,0 s (curva ease in-out, começa 0,3 s antes da fala da
nova cena): as duas imagens continuam em movimento lento (Ken Burns), com leve desfoque e um brilho quente no meio da troca.
Está em `Fundo.quadro` (`gerar.py`); vale para todos os vídeos automaticamente.

## Layout e área dos ícones do TikTok (decisão de 02/nov/2026)

Nenhum texto embaixo da interface do TikTok: coluna de ícones à direita (x > 940, y 760-1580), faixa de nome/legenda/música
embaixo (y > 1500) e abas no topo (y < 150). Textos centralizados com no máximo 740 px de largura. Posições: referência y 230,
título y 380-720, cartão y 650, legenda y ~1040, botão "Comente" y 1300, **contagem regressiva embaixo em y 1415**, discreta (pílula
translúcida pequena, sem brilho nem pulso, barra fina que esvazia: a legenda é o destaque). O gerador grava a caixa real de cada elemento em `.cache/luz/<slug>/render.json`.

## Analistas (antes de entregar)

1. **Automáticos** (`analistas.py`, o gerador roda sozinho e para com FALHA): técnico (1080x1920, 30 fps, duração, quadros pretos,
   volume normalizado em -14 LUFS), zona segura do TikTok e ritmo (palavras/s, tempo de leitura dos cartões). Também monta o
   pacote `.cache/luz/<slug>/revisao/` (imagens.jpg, quadros_N.jpg com a interface do TikTok em vermelho, roteiro.txt).
2. **Analistas Claude** (`.claude/agents/`): `analista-fatos` (roda também ANTES da voz, no roteiro) (versículos e afirmações), `analista-imagens` (realismo, sem texto
   nem rosto, combina com a fala) e `analista-tela` (ortografia, legibilidade, sobreposição, área dos ícones). Rodam em paralelo;
   só entrega com os três APROVADO. Nenhum analista usa o Gemini (Gemini é só a voz).

## Roteiro (`roteiros/<slug>.json`)

`ref` (topo), `titulo` (3 linhas, a última em dourado), `imagens` (prompts em inglês, sem rosto de Jesus, sem texto),
`cenas` (`fala` com `*destaque*`, `img`, opcional `card`, `cta`, `titulo`), `emenda` (última fala + 1ª fala), `fatos` (fonte de cada afirmação),
`tema_id`/`tema` (para a lista de 2 meses), `ganchos` (3 candidatos), `revelacao` (índice da cena), `legenda` do post.

## Lista de temas (validade de 2 meses)

`temas.json` guarda cada vídeo feito (`tema_id`, `tema`, `ref`, data e `libera_em` = data + 60 dias). O conferidor e o gerador
**bloqueiam** um roteiro que repita, dentro do prazo, o mesmo `tema_id`, a mesma passagem (livro + capítulo) ou 3+ palavras-chave
do título/tema. O gerador registra o tema sozinho quando o vídeo final sai (rascunho não registra). Passados 60 dias o tema
libera, mas só repita com um ângulo novo.

## Receita de ganchos (apelação máxima; o `conferir.py` cobra isto)

**Gancho inicial (0-3 s), a coisa mais importante.** <= 12 palavras, nome bíblico + choque, escrito grande na tela em 0 s,
nunca começa com saudação/"você sabia"/"hoje", nunca entrega a resposta. Fórmulas que funcionam:
1. *Contradição concreta:* "Jesus chorou diante de um túmulo que Ele mesmo ia abrir."
2. *Pergunta-armadilha:* "Jesus sabia o final. Então por que chorou?"
3. *Número + nome:* "Pedro negou 3 vezes. Jesus perguntou 3 vezes."
4. *Identificação:* "Se você carrega um erro antigo, escuta isto."
Liste 3 candidatos em `ganchos` e marque o escolhido. Efeito na tela: clarão dourado curto + som de impacto (sem zoom no fundo).

**Laço aberto (3-6 s).** A 2ª fala promete recompensa: "quase ninguém percebe esse detalhe", "o motivo vai mexer com você".

**Re-gancho a cada <= 5,5 s** (cartão dourado grande, ou "…" com pausa de suspense, ou pergunta). Sempre abra o
próximo laço antes de fechar o anterior. Tipos: "MAS ESPERA…", "A 2ª VEZ…", número ("3 VEZES"), mini-revelação parcial,
pergunta sem resposta imediata. **Contagem regressiva:** marque `"revelacao": <índice da cena>` e a tela mostra
"A REVELAÇÃO VEM EM 12s" nos 16 s anteriores. O conferidor mede os intervalos pelos tempos reais da voz.

**Revelação** entre 40% e 60% do vídeo, com pausa antes. **Virada pessoal** (~80%): "isso é pra você".

**CTA que dá vontade de ler os comentários (decisão de 02/nov/2026).** Nada de "curte e comenta amém" genérico (o conferidor
dá FALHA). O CTA é uma **pergunta do próprio episódio com resposta curta e comparável**, para a pessoa comentar E voltar para ver
o que os outros responderam. Fórmulas:
1. *Escolha entre opções:* "Vento, terremoto ou sussurro: como Deus tem falado com você?" (botão "Comente: VENTO, FOGO OU SUSSURRO")
2. *Você teria percebido?:* "Você já tinha notado esse detalhe? Comenta SIM ou NÃO." (divide o público, todo mundo quer ver o placar)
3. *Uma palavra:* "Em uma palavra: o que você quer deixar nesse túmulo hoje?"
4. *Um nome:* "Escreve o nome de quem precisa ouvir isso." (gera marcação e compartilhamento)
5. *Lado do personagem:* "Se você fosse Pedro, voltaria pro fogo? Comenta."
O botão (`cta`) mostra o formato da resposta (<= 30 letras) e a **legenda do post repete a pergunta**. Dica: depois de postar,
o dono responde/fixa o primeiro comentário com a própria resposta (puxa a conversa).

**Emenda (loop invisível, decisão de 02/nov/2026).** A **última fala termina no meio de uma frase que a 1ª fala completa**, e o
vídeo acaba colado na última palavra: quem chega ao fim continua ouvindo a frase e revê o vídeo sem perceber (mais retenção e
replays). Regras (o conferidor e o analista automático cobram):
- `"emenda"` no roteiro = a frase inteira que o loop forma (última fala + 1ª fala).
- A última fala NÃO termina com ponto (`.`/`!`/`?`); termina em aberto ("…", "que", "porque", "quando", "foi aí que").
- A última cena usa a MESMA imagem da 1ª; o gerador faz o movimento dela terminar no enquadramento do 1º quadro, corta o silêncio
  final, tira o fade-out, esconde o botão "Comente" 1,5 s antes do fim e suaviza o clarão/"boom" do 0 s.
- O CTA vem ANTES da última fala (a última fala é a ponte de volta).
- Exemplos: última "E foi por isso que, naquele dia…" + 1ª "Jesus chorou diante de um túmulo que Ele mesmo ia abrir."; última
  "Porque, no monte, depois do fogo…" + 1ª "Deus falou com Elias num sussurro."

**Honestidade:** `fatos` com o versículo de cada afirmação; cenas de até ~14 palavras; 100-145 palavras no total.

## Episódios

| Ep | Tema | Ref | Duração | Linha 1 da legenda | Estado |
|----|------|-----|---------|--------------------|--------|
| 01 | O mesmo fogo (anthrakia: Jo 18:18 e 21:9) | JOÃO 21:9 | 53 s | Jesus acendeu o MESMO fogo onde Pedro o negou 🔥 | pronto (imagens flux-schnell; 2 requisições de voz: a 1ª Charon, descartada; logo National Geographic na cena da floresta, mantido) |
| 02 | Jesus chorou sabendo que ia ressuscitar Lázaro (Jo 11) | JOÃO 11:35 | 53 s | Jesus chorou diante de um túmulo que Ele mesmo ia abrir 😢 | pronto (flux-schnell; 1 requisição Achird) |
| 03 | Deus não estava no vento, terremoto nem fogo: falou num sussurro (1 Rs 19) | 1 REIS 19:12 | 48 s | 3 vezes Deus passou por Elias, e não estava lá 🌬️ | pronto (flux-schnell; 1 requisição Achird efetiva; a 1ª falhou com 401 por falta de chave, sem áudio). Analistas depois: gancho impreciso e logo na img 2; dono decidiu não refazer |
