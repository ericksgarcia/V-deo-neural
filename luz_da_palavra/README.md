# Luz da Palavra

Canal separado do de IA. Formato: vídeo vertical 1080x1920, **imagem de fundo gerada no Replicate** (flux-1.1-pro,
9:16) com zoom lento, **narração no Gemini TTS** (`gemini-3.8-flash-tts`, voz Charon), referência bíblica no topo,
legenda em serifa creme com palavra-chave dourada, cartões de re-gancho e botão "Comente: AMÉM".

```bash
python luz_da_palavra/gerar.py luz_da_palavra/roteiros/ep01_fogo.json --so-texto     # texto + tempo previsto
python luz_da_palavra/gerar.py luz_da_palavra/roteiros/ep01_fogo.json --sem-imagens  # rascunho (fundo provisório)
python luz_da_palavra/gerar.py luz_da_palavra/roteiros/ep01_fogo.json                # final, com Replicate
```

Saída: `saida/luz/<slug>.mp4` e `saida/luz/<slug>_legenda.txt`.

- **Chaves** em `.cache/luz.env` (fora do git): `REPLICATE_API_TOKEN=` e `GEMINI_API_KEY=`. Nunca comitar.
- **Rede:** o ambiente precisa liberar `api.replicate.com` e `replicate.delivery` (imagens) e
  `generativelanguage.googleapis.com` (voz).
- **Custo:** 1 requisição de voz e 1 imagem por prompt; tudo fica em `.cache/luz/<slug>/`. Mudar o texto de
  qualquer fala (ou o estilo/voz) = nova requisição de voz. Mudar `card`, `titulo`, `cta`, `*destaques*`,
  `legenda`, `velocidade` ou `teto_pausa` NÃO gasta nada.
- **Ritmo:** ajustado localmente (pausas cortadas para `teto_pausa`, pausa de suspense = o dobro; `velocidade`
  via atempo, sem mudar o tom). Alvo 40-55 s.

## Roteiro (`roteiros/<slug>.json`)

`ref` (topo), `titulo` (3 linhas, a última em dourado), `imagens` (prompts em inglês, sem rosto de Jesus, sem texto),
`cenas` (`fala` com `*destaque*`, `img`, opcional `card`, `cta`, `titulo`), `fatos` (fonte de cada afirmação),
`legenda` do post.

## Receita de retenção (pedido do dono, nov/2026)

1. **0-3 s, gancho que para o dedo:** afirmação chocante e verdadeira, concreta, com um nome bíblico
   ("Jesus acendeu o mesmo fogo onde Pedro o negou"). Título grande na tela ao mesmo tempo. Nunca começar com
   "Olá"/"Você sabia".
2. **3-6 s, laço aberto:** "e quase ninguém percebe esse detalhe" / "a maioria lê errado".
3. **A cada ~5 s um re-gancho**, falado E visual (cartão dourado grande com som de impacto suave):
   "Mas presta atenção…", "A segunda… vai te arrepiar", "E quando ele chega…", "Não uma vez. Três.".
   Antes de cada revelação use "…" (vira pausa de suspense) e responda na cena seguinte.
4. **Uma pista "escondida" verificável** (palavra no hebraico/grego, número, paralelo entre passagens). Toda
   afirmação precisa estar em `fatos` com o versículo. Nada inventado.
5. **Virada pessoal** perto do fim: "Se você carrega um erro antigo, isso é pra você."
6. **CTA curto** ("Curte e comenta amém") ANTES da última frase, para quem ainda está vendo.
7. **Última frase** fecha a mensagem e ecoa o gancho (dá vontade de rever).
8. Cenas de até ~14 palavras; 120-140 palavras no total.

## Episódios

| Ep | Tema | Ref | Duração | Linha 1 da legenda | Estado |
|----|------|-----|---------|--------------------|--------|
| 01 | O mesmo fogo (anthrakia: Jo 18:18 e 21:9) | JOÃO 21:9 | 53 s | Jesus acendeu o MESMO fogo onde Pedro o negou 🔥 | voz pronta; falta gerar as imagens no Replicate |
