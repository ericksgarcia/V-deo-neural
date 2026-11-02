# Instruções do projeto (leia primeiro)

Canal de TikTok **Luz da Palavra**: vídeos verticais que revelam um detalhe escondido da Bíblia, com fundo de fotografia
ultra realista (Replicate) e narração no Gemini TTS. Leia `luz_da_palavra/README.md` (regras, receita de ganchos, episódios).
Este repositório contém SÓ esse canal (o antigo canal de simulações de IA foi removido em 02/nov/2026).

## Quando o usuário pedir "um novo vídeo"

1. `python luz_da_palavra/temas.py` e leia `luz_da_palavra/README.md`. **Cada tema vale 2 meses: não repita** tema nem
   passagem (livro + capítulo) ainda no prazo. Escolha um tema NOVO, com fato verificável no texto bíblico (versículos),
   e confirme que não está na lista (`temas.py --checa "palavras"`). Avise em uma linha o tema escolhido.
2. Crie `luz_da_palavra/roteiros/epNN_nome.json` no formato do README: `tema_id`, `tema`, `ref`, `titulo`, `fatos`,
   **`ganchos` (3 candidatos)**, `imagens` (8 prompts em inglês), `cenas` com cartões de re-gancho, `revelacao`, `cta`, `emenda`, `legenda`.
3. **Ganchos com apelação máxima, é obrigatório:** gancho inicial <= 12 palavras com nome bíblico + choque/contradição/número,
   escrito grande na tela em 0 s; 2ª fala abre um laço; um gancho/re-gancho (cartão, "…" ou pergunta) a cada <= 5,5 s; revelação
   entre 40% e 60%; virada pessoal; **CTA = pergunta do episódio com resposta curta e comparável** (opções, SIM/NÃO, uma
   palavra, um nome; nunca "curte e comenta"), repetida na legenda; **última fala em aberto que EMENDA na 1ª** (loop invisível,
   mesma imagem da 1ª cena, campo `emenda`). Detalhes e fórmulas no README.
4. `python luz_da_palavra/conferir.py <roteiro>`: **corrija até zero FALHA** (o gerador também se recusa a rodar com FALHA).
   Em seguida rode o **`analista-fatos` no roteiro, ANTES da voz** (o erro de fato custa uma voz nova se achado depois;
   no ep03 o gancho "3 vezes Deus passou" saiu errado: em 1Rs 19:11 Deus passa uma vez). Só gere com ele APROVADO.
5. `python luz_da_palavra/gerar.py <roteiro>`: gera as imagens (flux-schnell, ~4 min por causa do limite do Replicate),
   **UMA** requisição de voz (Achird) e o vídeo, e registra o tema na lista. Mudar o texto falado depois = nova requisição de voz
   (peça licença ao dono). Mudar cartões, título, destaques, legenda ou imagens não gasta voz.
6. **Analistas antes de publicar (obrigatório; o dono NÃO revisa antes de postar, decisão de 02/nov/2026).** O `gerar.py` roda os
   9 analistas automáticos (`analistas.py`: técnico, zona segura, ritmo, emenda, som/música, contraste, ortografia, post/capa,
   integridade) e para com FALHA. Depois rode em paralelo os 5 analistas Claude (`.claude/agents/`), cada um com o slug:
   `analista-fatos` (de novo), `analista-imagens`, `analista-tela`, `analista-som` e `analista-post`. Qualquer FALHA: corrija
   (sem mudar a fala, se possível), gere de novo e repita até os 5 darem APROVADO. Leia os relatórios você mesmo; não publique
   na dúvida.
7. **Publicar:** `python luz_da_palavra/publicar.py <roteiro> --aprovados fatos,imagens,tela,som,post` sobe o vídeo no R2, posta
   no TikTok pelo Buffer (legenda do post, capa pelo quadro do título, rótulo de IA desmarcado) e registra em `publicados.json`.
   Envie ao dono o `.mp4`, a capa e a legenda, com o status do post. Atualize a tabela de episódios do README, faça commit e push.

## Regras do dono (não mude sem licença)

- **Voz: SEMPRE Achird** (Gemini TTS `gemini-3.8-flash-tts`). **UMA requisição de voz por vídeo** (trava em `gerar.py`).
- **Imagens: SEMPRE `black-forest-labs/flux-schnell`** (nunca cite marca no prompt: vira logo na foto) no Replicate, fotografia **ultra realista** (nada de ilustração/pintura/3D),
  natureza e lugares reais, cores vivas porém verdadeiras. Sem rosto de Jesus, sem texto na imagem.
- **Transições:** fusão suave entre imagens (dissolve de 1 s com desfoque/brilho leve). **Sem soco de zoom** e sem corte seco.
- **Música de fundo (02/nov/2026):** a trilha do dono (`luz_da_palavra/musica/trilha.m4a`, já cortada a partir de 3:55),
  BEM BAIXA: -18 dB da voz nas pausas e ~-24 dB debaixo da fala (o gerador mede e o analista de som cobra).
- **Publicação (02/nov/2026):** TikTok pelo Buffer (`publicar.py`), capa = quadro do título (as redes não aceitam imagem de capa
  avulsa), legenda do post = `legenda` do roteiro, **rótulo "gerado por IA" DESMARCADO**. Vídeo no Cloudflare R2 (bucket público).
- **Gemini só para a voz (TTS).** Roteiros, análises e revisões são feitos pelo Claude; imagens só no Replicate.
- **Área dos ícones do TikTok:** nenhum texto na coluna da direita (x > 940, y 760-1580), na faixa de baixo (y > 1500)
  nem no topo (y < 150). A contagem regressiva fica embaixo (y ~1415), DISCRETA (a legenda é o destaque).
- Tom: amigo cristão caloroso, reverente, assombro e suspense amigável; nunca pregador gritando nem sombrio.
- Honestidade: toda afirmação bíblica precisa estar em `fatos` com o versículo. Nada inventado.
- Língua: português do Brasil, frases curtas, 100-145 palavras, 40-55 s (teto 60 s).
- **Chaves nunca vão para o git.** Ficam em `.cache/luz.env` (`REPLICATE_API_TOKEN`, `GEMINI_API_KEY`), `.cache/r2.env` (R2) e
  `.cache/buffer.env` (`BUFFER_API_KEY`), ou nas variáveis de ambiente. Na nuvem o proxy injeta Replicate e Gemini: rode com valor fictício.
  Se uma chave aparecer no chat, avise o dono para revogá-la.

## Branches (a plataforma cria um `claude/<nome>` por conversa)

O tronco é **`claude/cool-gauss-mg0fhk`** (branch padrão). No começo da conversa: `git fetch origin && git merge origin/claude/cool-gauss-mg0fhk`.
No fim: commit + push no branch da conversa e `git push origin HEAD:claude/cool-gauss-mg0fhk` (se recusado: fetch, merge e repita).
Nunca deixe um vídeo só no branch da conversa. Não crie outros branches de propósito.
