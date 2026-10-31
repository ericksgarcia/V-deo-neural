# Instruções do projeto (leia primeiro)

Canal de TikTok de vídeos verticais de **IA aprendendo sozinha** (simulações reais). Leia `README.md`
(como a base funciona) e `docs/EPISODIOS.md` (o que já foi feito + decisões do dono do canal).

## Quando o usuário pedir "um novo vídeo" (ou algo parecido)

1. Leia `docs/IDEIAS.md` (a **fila**, fonte única de temas) e `docs/EPISODIOS.md` (o que já foi feito).
2. **A fila tem prioridade e não se pergunta.** Pegue o PRIMEIRO item com estado **pendente** (na ordem da
   tabela) e implemente direto. Avise em uma linha qual tema foi escolhido e siga.
3. **Só se não houver item pendente:** proponha 3 a 5 temas NOVOS (gancho, vista 2D, dois lados?, descoberta,
   esforço; confirme na web que são inéditos; recomende um) e use `AskUserQuestion`. Depois implemente.
3b. **TRIAGEM DO TEMA (sempre, também para item da fila; antes de escrever código):** chame `analista-tema` (tabela e prompt em
   `docs/ROTEIRO.md` §16.1/§11). Só implemente com **GO** (≥ 14/20). Se vier AJUSTAR, aplique o ângulo sugerido; se vier NO-GO, avise o dono em
   uma linha, pegue o próximo pendente da fila e repita a triagem. Registre a nota em `docs/IDEIAS.md`.
4. **Leia `docs/ROTEIRO.md` INTEIRO antes de escrever uma linha de roteiro** (inclusive a **seção 13, retenção v3**: promessa do
   teste final no começo, números em ALGARISMOS na fala, 2-4 `<long pause>` antes das revelações, cenas ≤ 18 palavras, arena em pé;
   a **seção 15, receita v5: fluidez + leigos + assombro** (cenas costuradas por conectivos e pontes, zero jargão, comparação do dia a dia, 1 frase
   "ninguém ensinou isso", suspense amigável e NUNCA de terror) e a **seção 16** (triagem do tema e curadoria do treino);
   e a **seção 14, receita v4 diversão + suspense**: tensão → revelação → riso → nova tensão, piada só nas falhas e DEPOIS dos
   números, **o CHUTE** "Chuta aí… <long pause>" antes do número final com a resposta na cena seguinte, resposta do teste a 70-88%). É o guia v2 do canal (vídeo curto,
   gancho com número da geração 1, poucos números, herói "o campeão", re-gancho no meio, laço falado, CTA sem votação,
   legenda nova). Ele vale mais que qualquer roteiro antigo: **não copie o estilo de `roteiros/*.py` anteriores**
   (eles têm CTA de voto, 70-90 s e muitos números); copie só a parte técnica (treino, replays, `A.busca`).
5. **Ordem obrigatória (analisar ANTES de renderizar). Siga na sequência, sem pular:**
   1. Implemente simulação/adaptador/roteiro (receita no `README.md`) escrevendo o roteiro NO FORMATO do `docs/ROTEIRO.md`
      (3 candidatos de gancho, orçamento de tempo, `post` no formato da seção 9).
   2. `python gerar.py <tema> --so-roteiro > .cache/roteiro_<tema>.txt` (treino fica em `.cache/`, reutilize).
   3. `python ferramentas/confere_roteiro.py .cache/roteiro_<tema>.txt`. **Corrija até zero `FALHA`** (os `AVISO`
      devem ser resolvidos ou justificados). Repita 2-3 a cada ajuste de texto.
   4. Chame `analista-roteiro` e `analista-engajamento` (este agora mede se o vídeo é visto ATÉ O FINAL: duas notas, conclusão e engajamento) (prompts prontos em `docs/ROTEIRO.md`, seção 11). Aplique o
      que melhora mantendo os números reais; rode o conferidor de novo. Só avance com notas >= 8.
   5. **Uma** narração: `python gerar.py <tema> --so-voz` (1 requisição TTS, depois cache). Confira o relatório de
      ritmo/pronúncia e a duração prevista (**<= 60 s**; se passar, corte cenas do roteiro ANTES de gastar voz nova;
      lembre: mudar texto depois = nova requisição, peça licença).
   6. Rascunho `python gerar.py <tema> --rascunho --sem-voz` só para conferir o visual; `analista-visual` e
      `analista-retencao` (prompts na seção 11). Um único rascunho por rodada de correções.
   7. Render final em segundo plano; depois `analista-narracao` e `diretor` UMA vez (todas as notas >= 8).
   Nunca renderize o final antes de aprovar o roteiro.
6. Receita técnica de um tema novo: ver `README.md` (simulação, adaptador, roteiro e uma linha em `CFG` no `gerar.py`).

## Trabalho em sessões paralelas / branches (OBRIGATÓRIO, leia)

A plataforma cria um branch novo `claude/<nome>` para cada conversa; não dá para impedir isso. Por isso existe UM
**TRONCO: `claude/cool-gauss-mg0fhk`** (é o branch padrão do GitHub). Todo o trabalho tem que terminar nele.

**No começo de toda conversa (antes de qualquer coisa):**
```bash
git fetch origin
git merge origin/claude/cool-gauss-mg0fhk      # traz o guia v2, a fila e os vídeos feitos para o seu branch
```
Se o branch da conversa estiver vazio/antigo, esse merge basta. Confira que `docs/ROTEIRO.md` existe; se não existir, pare e avise.

**No fim de todo vídeo/mudança (depois do commit e do push no branch da conversa):**
```bash
git fetch origin
git merge origin/claude/cool-gauss-mg0fhk       # resolva conflitos (em docs/EPISODIOS.md e docs/IDEIAS.md mantenha as DUAS partes)
git push origin HEAD                              # branch da conversa
git push origin HEAD:claude/cool-gauss-mg0fhk     # atualiza o tronco; se for recusado, repita o fetch+merge e tente de novo
```
Nunca deixe um vídeo só no branch da conversa. Não crie outros branches de propósito. Se o dono pedir um branch específico, use-o e
integre ao tronco do mesmo jeito. Os prefixos `epNN` dos arquivos podem repetir; vale o NOME do tema em `docs/EPISODIOS.md`.

## Economia de tokens (sem perder qualidade)

- Passe aos analistas só o roteiro (texto + fatos reais), não o código; peça resposta curta e objetiva.
- Rode só os analistas que o estágio precisa (roteiro/engajamento antes; visual/retenção no rascunho);
  `diretor` completo só no fim, uma vez.
- Não releia arquivos já lidos nem imprima logs longos (`tail`); treino e TTS ficam em `.cache/` (reuse).
- Renders longos em segundo plano, sem polling; um único rascunho por rodada de correções.

## Ao entregar QUALQUER vídeo

- Envie **juntos**, na mesma resposta: o `.mp4` e a legenda do TikTok (`saida/<ep>_legenda.txt`),
  e cole o texto da legenda também no chat, pronto para copiar.
- Atualize `docs/EPISODIOS.md` (nova linha na tabela, duração, semente, comando, pergunta do CTA e a linha 1 da legenda), **marque o tema
  como feito (EPxx) na fila de `docs/IDEIAS.md`** e faça commit + push no branch da conversa **e integre ao tronco** (seção acima). Tudo que precisa
  persistir fica no repositório.

## Regras que o dono do canal já decidiu

- **Nunca mostrar o resultado final no início.** Abra na geração 1 (caos) e mostre a melhora aos poucos, uma
  descoberta por vez; o gancho é pergunta/tensão. O número final só perto do fim (ex.: teste em situação nova).

- Tudo **2D**, estilo **neon/holograma**, HUD tecnológico; nada de 3D.
- **Nenhum círculo/marcação na cena, em nenhum vídeo** (decidido em out/2026): sem telestrador (`marcas`: círculos, setas,
  rótulos tipo "PEGO!"; o motor já ignora), sem anel nem rótulo "CAMPEÃO" em volta de agente ou equipe, sem anéis pulsando
  em loop para apontar alguém. Destacar só de forma INDIVIDUAL e que siga o agente o tempo todo:
  `h.destaque(...)` (brilho + seta ▼ acima da cabeça), recalculado da posição daquele agente a cada quadro; numa equipe, um em
  cada membro. Ficam só círculos que SÃO o mundo (corpo do agente, arena, cofre) e o flash curto de um evento no ponto exato.
- **Curadoria do treino AUTORIZADA (31/out/2026):** pode manipular o treinamento para a história ficar melhor (sementes, população, mutação,
  currículo, recompensas, física/arena, escolha dos lances e da montagem). Limites: todo número vem da simulação que aparece no vídeo (nunca
  editar/inventar número), o replay mostra lance que aconteceu, não afirmar o que o treino não mostrou (rodapé exato se a recompensa guiou muito),
  e registrar o ajuste em `docs/EPISODIOS.md`. Detalhes: `docs/ROTEIRO.md` §16.2.
- Honestidade: todo número falado vem do treino real (checagens em `roteiros/`). Nada inventado.
- Narração: **SEMPRE a voz Achird no Gemini TTS 3.8** (`gemini-3.8-flash-tts`), travado em `neuralab/audio.py` (o log precisa mostrar
  "[voz] confirmado: Achird · gemini-3.8-flash-tts"; outra voz/modelo dá erro). Tom: humano, caloroso, assombro de quem descobriu algo
  muito legal e explica para leigos; suspense amigável, nunca de terror (`docs/NARRACAO.md`). **UMA requisição por vídeo**. Limite de 10
  requisições por voz a cada 24 h (ledger em `.cache/tts/uso.json`). Ajuste de ritmo/pausas é local
  (Whisper + ffmpeg), sem nova requisição. Mudar texto, estilo ou voz = nova requisição (peça licença).
- Do Gemini só o TTS (a menos que seja gratuito). Transcrição = Whisper local.
- Língua: português do Brasil, frases curtas, linguagem simples, gancho forte, pergunta ao espectador.
- **Regras do guia v2 (decididas em out/2026; detalhes e limites em `docs/ROTEIRO.md`):**
  - **CTA sem votação.** Nunca pedir voto nem prometer o próximo vídeo/tema ("mais votado", "vira o próximo", "próximo
    vídeo", "comenta A/B"). O CTA é UMA pergunta sobre o que se passou no próprio vídeo.
  - **Duração 40-55 s, teto 60 s**, 100-140 palavras, no máximo 3 descobertas; premissa e regra numa cena só.
  - **Gancho** começa com verbo em 1ª pessoa "-ei" (Tirei, Treinei, Coloquei…), <= 16 palavras, traz um número real
    da geração 1; nunca o resultado final.
  - **Poucos números:** <= 6 dados falados no vídeo, 1 por cena; o resto vai para o visual.
  - **Herói "o campeão"** (melhor da geração; linhagem real por elitismo, nunca "o mesmo carro"): em >= 3 cenas, dito em
    >= 2 falas, com 1 queda e 1 acerto.
  - **Re-gancho** entre 40% e 60% do tempo, respondido antes do fim.
  - **Laço falado:** a última fala termina em "Porque tudo começou quando eu…", completando o gancho.
  - **Legenda do post** no formato da seção 9 do `docs/ROTEIRO.md` (linha 1 = curiosidade, gatilho de compartilhar,
    3 a 5 hashtags, sem voto).
  - Dívida antiga com o público: no EP05 (polícia) foi prometido um "motor mais rápido" ao lado mais votado. Não
    repita promessas assim. Se o dono pedir uma sequência da polícia, pergunte a ele qual lado ganhou antes de cumprir.
- Não copiar vídeos de referência (@circuito_cero.1): entender a ideia e fazer melhor.
- **Efeitos sonoros baixos**: nunca competem com a voz. Cada efeito é limitado a pico ≈ -14 dBFS
  (`SFX_PICO` em `neuralab/audio.py`) e é abaixado enquanto a voz fala. Pico geral do mix bem abaixo de 0 dB.
