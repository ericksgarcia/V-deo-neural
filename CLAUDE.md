# Instruções do projeto (leia primeiro)

Canal de TikTok de vídeos verticais de **IA aprendendo sozinha** (simulações reais). Leia `README.md`
(como a base funciona) e `docs/EPISODIOS.md` (o que já foi feito + decisões do dono do canal).

## Quando o usuário pedir "um novo vídeo" (ou algo parecido)

1. **Não gere nada ainda.** Leia `docs/EPISODIOS.md` (tabela de episódios **e** a seção "Temas já feitos fora do
   repositório") e `docs/IDEIAS.md` (inclui a **fila de próximos temas aprovados**, no fim do arquivo).
2. **Primeiro olhe a fila** (`docs/IDEIAS.md`, seções "Fila de próximos temas" e "Segunda leva"). Se houver temas
   nela que ainda não viraram episódio, **proponha esses** (até 5, os mais promissores), confirmando na web que
   continuam inéditos.
3. **Só se a fila estiver vazia (ou o usuário pedir outras opções):** confira o que já foi feito (tabela de episódios,
   "já feitos fora do repo" e as 10 ideias antigas do `IDEIAS.md`, todas já gravadas) e **proponha 3 a 5 temas NOVOS**
   fora de todas essas listas. Se tiver dúvida de que um tema é inédito, pesquise na web antes de propor.
   Para cada tema proposto: gancho em uma frase, vista 2D, se tem dois lados, a "descoberta" que pode surgir,
   esforço (reaproveita adaptador existente ou exige simulação nova). Dê uma recomendação.
4. Use `AskUserQuestion` para o usuário escolher. Só então implemente (receita no README) e gere.
5. Depois de gerar, rode os analistas (`diretor`) e corrija antes de entregar.

## Ao entregar QUALQUER vídeo

- Envie **juntos**, na mesma resposta: o `.mp4` e a legenda do TikTok (`saida/<ep>_legenda.txt`),
  e cole o texto da legenda também no chat, pronto para copiar.
- Atualize `docs/EPISODIOS.md` (nova linha na tabela, duração, semente, comando, escolha de CTA) e
  faça commit + push no branch designado. Tudo que precisa persistir fica no repositório.

## Regras que o dono do canal já decidiu

- **Nunca mostrar o resultado final no início.** O vídeo começa na geração 1 (caos) e mostra a melhora aos poucos,
  na ordem em que aconteceu, uma descoberta por vez. O gancho é uma pergunta/tensão, não o resultado. O número
  final só aparece perto do fim (ex.: teste em situação nova).
- Depois de entregar um vídeo, **registre o tema** em `docs/EPISODIOS.md` (é o que impede repetir) e **tire-o da fila**
  em `docs/IDEIAS.md`.

- Tudo **2D**, estilo **neon/holograma**, HUD tecnológico; nada de 3D.
- Honestidade: todo número falado vem do treino real (checagens em `roteiros/`). Nada inventado.
- Narração: **Gemini TTS 3.8** (`gemini-3.8-flash-tts`), **UMA requisição por vídeo**. Limite de 10
  requisições por voz a cada 24 h (ledger em `.cache/tts/uso.json`). Ajuste de ritmo/pausas é local
  (Whisper + ffmpeg), sem nova requisição. Mudar texto, estilo ou voz = nova requisição (peça licença).
- Do Gemini só o TTS (a menos que seja gratuito). Transcrição = Whisper local.
- Língua: português do Brasil, frases curtas, linguagem simples, gancho forte, pergunta ao espectador.
- Não copiar vídeos de referência (@circuito_cero.1): entender a ideia e fazer melhor.
