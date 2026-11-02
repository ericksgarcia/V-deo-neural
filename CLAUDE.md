# Instruções do projeto (leia primeiro)

Canal de TikTok **Luz da Palavra**: vídeos verticais que revelam um detalhe escondido da Bíblia, com fundo de fotografia
ultra realista (Replicate) e narração no Gemini TTS. Leia `luz_da_palavra/README.md` (regras, receita de ganchos, episódios).
Este repositório contém SÓ esse canal (o antigo canal de simulações de IA foi removido em 02/nov/2026).

## Quando o usuário pedir "um novo vídeo"

1. `python luz_da_palavra/temas.py` e leia `luz_da_palavra/README.md`. **Cada tema vale 2 meses: não repita** tema nem
   passagem (livro + capítulo) ainda no prazo. Escolha um tema NOVO, com fato verificável no texto bíblico (versículos),
   e confirme que não está na lista (`temas.py --checa "palavras"`). Avise em uma linha o tema escolhido.
2. Crie `luz_da_palavra/roteiros/epNN_nome.json` no formato do README: `tema_id`, `tema`, `ref`, `titulo`, `fatos`,
   **`ganchos` (3 candidatos)**, `imagens` (8 prompts em inglês), `cenas` com cartões de re-gancho, `revelacao`, `cta`, `legenda`.
3. **Ganchos com apelação máxima, é obrigatório:** gancho inicial <= 12 palavras com nome bíblico + choque/contradição/número,
   escrito grande na tela em 0 s; 2ª fala abre um laço; um gancho/re-gancho (cartão, "…" ou pergunta) a cada <= 5,5 s; revelação
   entre 40% e 60%; virada pessoal, CTA e última fala que retoma o gancho.
4. `python luz_da_palavra/conferir.py <roteiro>`: **corrija até zero FALHA** (o gerador também se recusa a rodar com FALHA).
5. `python luz_da_palavra/gerar.py <roteiro>`: gera as imagens (flux-schnell, ~4 min por causa do limite do Replicate),
   **UMA** requisição de voz (Achird) e o vídeo, e registra o tema na lista. Mudar o texto falado depois = nova requisição de voz
   (peça licença ao dono). Mudar cartões, título, destaques, legenda ou imagens não gasta voz.
6. Confira visualmente os quadros (mosaico com ffmpeg). Entregue **juntos** o `.mp4` e a legenda (`saida/luz/<slug>_legenda.txt`)
   e cole a legenda no chat. Atualize a tabela de episódios do `luz_da_palavra/README.md`, faça commit e push.

## Regras do dono (não mude sem licença)

- **Voz: SEMPRE Achird** (Gemini TTS `gemini-3.8-flash-tts`). **UMA requisição de voz por vídeo** (trava em `gerar.py`).
- **Imagens: SEMPRE `black-forest-labs/flux-schnell`** no Replicate, fotografia **ultra realista** (nada de ilustração/pintura/3D),
  natureza e lugares reais, cores vivas porém verdadeiras. Sem rosto de Jesus, sem texto na imagem.
- **Transições:** fusão suave entre imagens (dissolve de 1 s com desfoque/brilho leve). **Sem soco de zoom** e sem corte seco.
- Tom: amigo cristão caloroso, reverente, assombro e suspense amigável; nunca pregador gritando nem sombrio.
- Honestidade: toda afirmação bíblica precisa estar em `fatos` com o versículo. Nada inventado.
- Língua: português do Brasil, frases curtas, 100-145 palavras, 40-55 s (teto 60 s).
- **Chaves nunca vão para o git.** Ficam em `.cache/luz.env` (`REPLICATE_API_TOKEN`, `GEMINI_API_KEY`) ou nas variáveis de ambiente.
  Se uma chave aparecer no chat, avise o dono para revogá-la.

## Branches (a plataforma cria um `claude/<nome>` por conversa)

O tronco é **`claude/cool-gauss-mg0fhk`** (branch padrão). No começo da conversa: `git fetch origin && git merge origin/claude/cool-gauss-mg0fhk`.
No fim: commit + push no branch da conversa e `git push origin HEAD:claude/cool-gauss-mg0fhk` (se recusado: fetch, merge e repita).
Nunca deixe um vídeo só no branch da conversa. Não crie outros branches de propósito.
