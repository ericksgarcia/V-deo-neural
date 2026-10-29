# Instruções do projeto (leia primeiro)

Canal de TikTok de vídeos verticais de **IA aprendendo sozinha** (simulações reais). Leia `README.md`
(como a base funciona) e `docs/EPISODIOS.md` (o que já foi feito + decisões do dono do canal).

## Quando o usuário pedir "um novo vídeo" (ou algo parecido)

1. Leia `docs/EPISODIOS.md` e `docs/IDEIAS.md`.
2. **A lista de `docs/IDEIAS.md` tem prioridade.** Pegue o PRÓXIMO item da lista que ainda não foi
   feito (na ordem; ignore os marcados "feito" e os que o dono mandou deixar de lado) e **implemente
   direto, sem perguntar**. Avise em uma linha qual tema foi escolhido.
3. **Só se a lista estiver esgotada**: analise e proponha 3 a 5 temas NOVOS (gancho, vista 2D, dois
   lados?, descoberta, esforço, recomendação) e use `AskUserQuestion`. Depois implemente (receita no
   README) e gere.
4. Depois de gerar, rode os analistas (`diretor`) e corrija antes de entregar.

## Ao entregar QUALQUER vídeo

- Envie **juntos**, na mesma resposta: o `.mp4` e a legenda do TikTok (`saida/<ep>_legenda.txt`),
  e cole o texto da legenda também no chat, pronto para copiar.
- Atualize `docs/EPISODIOS.md` (nova linha na tabela, duração, semente, comando, escolha de CTA) e
  faça commit + push no branch designado. Tudo que precisa persistir fica no repositório.

## Regras que o dono do canal já decidiu

- Tudo **2D**, estilo **neon/holograma**, HUD tecnológico; nada de 3D.
- Honestidade: todo número falado vem do treino real (checagens em `roteiros/`). Nada inventado.
- Narração: **Gemini TTS 3.8** (`gemini-3.8-flash-tts`), **UMA requisição por vídeo**. Limite de 10
  requisições por voz a cada 24 h (ledger em `.cache/tts/uso.json`). Ajuste de ritmo/pausas é local
  (Whisper + ffmpeg), sem nova requisição. Mudar texto, estilo ou voz = nova requisição (peça licença).
- Do Gemini só o TTS (a menos que seja gratuito). Transcrição = Whisper local.
- Língua: português do Brasil, frases curtas, linguagem simples, gancho forte, pergunta ao espectador.
- Não copiar vídeos de referência (@circuito_cero.1): entender a ideia e fazer melhor.
