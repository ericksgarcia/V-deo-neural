# Instruções do projeto (leia primeiro)

Canal de TikTok de vídeos verticais de **IA aprendendo sozinha** (simulações reais). Leia `README.md`
(como a base funciona) e `docs/EPISODIOS.md` (o que já foi feito + decisões do dono do canal).

## Quando o usuário pedir "um novo vídeo" (ou algo parecido)

1. Leia `docs/IDEIAS.md` (a **fila**, fonte única de temas) e `docs/EPISODIOS.md` (o que já foi feito).
2. **A fila tem prioridade e não se pergunta.** Pegue o PRIMEIRO item com estado **pendente** (na ordem da
   tabela) e implemente direto. Avise em uma linha qual tema foi escolhido e siga.
3. **Só se não houver item pendente:** proponha 3 a 5 temas NOVOS (gancho, vista 2D, dois lados?, descoberta,
   esforço; confirme na web que são inéditos; recomende um) e use `AskUserQuestion`. Depois implemente.
4. **Ordem obrigatória (analisar ANTES de renderizar):** `--so-roteiro` -> analistas de roteiro e engajamento
   (texto, gancho, retenção, CTA) -> ajustar -> **uma** voz (`--so-voz`) -> rascunho `--rascunho --sem-voz` só
   para conferir o visual -> corrigir -> render final. Nunca renderize o final antes de aprovar o roteiro.
5. Receita técnica de um tema novo: ver `README.md` (simulação, adaptador, roteiro e uma linha em `CFG` no `gerar.py`).

## Trabalho em sessões paralelas (leia)

- O repositório tem UM tronco. Antes de começar, faça `git fetch` e confirme que está no branch mais recente
  (o de maior histórico); não parta de um branch antigo. Se o dono pedir um branch específico, use-o e, ao
  terminar, garanta que o trabalho esteja integrado ao tronco (merge), para a próxima conversa enxergar tudo.
- Os prefixos `epNN` dos arquivos podem repetir; o que vale é o NOME do tema em `docs/EPISODIOS.md`.

## Economia de tokens (sem perder qualidade)

- Passe aos analistas só o roteiro (texto + fatos reais), não o código; peça resposta curta e objetiva.
- Rode só os analistas que o estágio precisa (roteiro/engajamento antes; visual/retenção no rascunho);
  `diretor` completo só no fim, uma vez.
- Não releia arquivos já lidos nem imprima logs longos (`tail`); treino e TTS ficam em `.cache/` (reuse).
- Renders longos em segundo plano, sem polling; um único rascunho por rodada de correções.

## Ao entregar QUALQUER vídeo

- Envie **juntos**, na mesma resposta: o `.mp4` e a legenda do TikTok (`saida/<ep>_legenda.txt`),
  e cole o texto da legenda também no chat, pronto para copiar.
- Atualize `docs/EPISODIOS.md` (nova linha na tabela, duração, semente, comando, escolha de CTA), **marque o tema
  como feito (EPxx) na fila de `docs/IDEIAS.md`** e faça commit + push no branch designado. Tudo que precisa
  persistir fica no repositório.

## Regras que o dono do canal já decidiu

- **Nunca mostrar o resultado final no início.** Abra na geração 1 (caos) e mostre a melhora aos poucos, uma
  descoberta por vez; o gancho é pergunta/tensão. O número final só perto do fim (ex.: teste em situação nova).

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
