# Instruções do projeto (leia primeiro)

Canal de TikTok de vídeos verticais de **IA aprendendo sozinha** (simulações reais). Leia `README.md`
(como a base funciona) e `docs/EPISODIOS.md` (o que já foi feito + decisões do dono do canal).

## Quando o usuário pedir "um novo vídeo" (ou algo parecido)

1. **Não gere nada ainda.** Leia `docs/EPISODIOS.md` e `docs/IDEIAS.md`.
2. **Analise e proponha 3 a 5 temas NOVOS**, diferentes de todos os já gerados (tabela de episódios).
   Para cada um: gancho em uma frase, vista 2D, se tem dois lados, a "descoberta" que pode surgir,
   esforço (reaproveita adaptador existente ou exige simulação nova). Dê uma recomendação.
3. Use `AskUserQuestion` para o usuário escolher. Só então implemente (receita no README) e gere.
4. **Ordem obrigatória (analisar ANTES de renderizar):** `--so-roteiro` -> analistas de roteiro e engajamento
   (texto, gancho, retenção, CTA) -> ajustar -> **uma** voz (`--so-voz`) -> rascunho `--rascunho --sem-voz` só
   para conferir o visual -> corrigir -> render final. Nunca renderize o final antes de aprovar o roteiro.

## Economia de tokens (sem perder qualidade)

- Passe aos analistas só o roteiro (texto + fatos reais), não o código; peça resposta curta e objetiva.
- Rode só os analistas que o estágio precisa (roteiro/engajamento antes; visual/retenção no rascunho);
  `diretor` completo só no fim, uma vez.
- Não releia arquivos já lidos nem imprima logs longos (`tail`); treino e TTS ficam em `.cache/` (reuse).
- Renders longos em segundo plano, sem polling; um único rascunho por rodada de correções.

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
- **Efeitos sonoros baixos**: nunca competem com a voz. Cada efeito é limitado a pico ≈ -14 dBFS
  (`SFX_PICO` em `neuralab/audio.py`) e é abaixado enquanto a voz fala. Pico geral do mix bem abaixo de 0 dB.
