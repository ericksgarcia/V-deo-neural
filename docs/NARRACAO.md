# Tom da narração (decidido em out/2026, voz **Achird**)

Recomeçamos do zero. Antes a voz era de "locutor de trailer" (Charon, ritmo de 3 palavras/s, suspense
anunciado). Agora é **um amigo curioso assistindo ao experimento junto com você**.

## Quem fala
- Um amigo no telefone, perto do microfone, contando algo que mal acredita ter visto. Nunca locutor, nunca YouTuber gritando.
- Fala em primeira pessoa quando ajuda: "Eu comecei com 150 carros." "Eu mudei a largada."
- Reage como gente: "Bateu. De novo." "Chuta aí: quantos bateram?" Humor seco nas falhas, emoção contida nos acertos.

## Humor e humanização (decidido pelo dono em 30/out/2026)
- Fale como gente contando um "causo" para um amigo: gírias leves ("gente", "aí", "olha só", "não é possível"), zoar as IAs com
  carinho (como bichinhos desastrados), comentar a própria reação ("eu ri sozinho", "juro que eu não esperava").
- Pelo menos 3 momentos de humor no vídeo (uma piada de falha, um comentário de bastidor, uma comparação do dia a dia).
- **Onde fica a graça (receita v4, `docs/ROTEIRO.md` §14):** piada nas falhas e logo DEPOIS de uma revelação (alívio);
  silêncio e voz baixa antes dos números. Nunca piada entre a pergunta e a resposta. No teste final, o "Chuta aí… <long pause>"
  é dito baixinho, como quem desafia um amigo; a resposta vem seca, na cena seguinte.
- Sem exagero: a piada nunca esconde o número nem a regra do jogo. Os limites do guia v2 (palavras, números, duração) continuam.
- A voz padrão é **Achird** (`--voz` só se o dono pedir outra).

## Regras do texto
1. **Frases curtas** (até ~9 palavras), uma ideia por frase. Contraste em vez de adjetivo.
2. **Um número por frase, no fim dela**, depois de uma pausa (`<long pause>`): o número aterrissa sozinho. No vídeo
   inteiro, no máximo 6 dados falados (guia v2, `docs/ROTEIRO.md`); o resto vai para o visual.
3. **Nada de palavras de hype** ("incrível", "chocante", "você não vai acreditar"). A surpresa vem do fato.
4. **Pergunta de verdade ao espectador** com silêncio antes da resposta ("Chuta aí… <long pause> sete em cada dez").
5. Regras do jogo explicadas como para um amigo esperto: "Quem vai melhor vira pai da próxima turma. Quem bate sai do jogo."
6. Quando finalmente dá certo, o tom é de **alívio emocionado**, não de comemoração.
7. Final leve e provocador: **UMA pergunta sobre o que se passou** (sem votação, sem prometer próximo vídeo; nunca só
   "comenta aí"), seguida de `<short pause>` e da frase cortada que fecha o laço: **"Porque tudo começou quando eu…"**
   (sem ponto final; completa o gancho, que começa com verbo "-ei").
8. Gancho: primeira frase em 1ª pessoa do passado ("Tirei…", "Treinei…"), com o número da geração 1; ≤ 16 palavras.
9. Fale do **campeão** ("o campeão da geração 47"): a linhagem é real, o corpo muda a cada geração.

## Direção de voz (vai em `speechMetadata.style`, nunca no texto)
Fica em `neuralab/audio.py` (`ESTILO_PADRAO`): voz Achird, suave, perto do microfone, ~2,6 palavras/s,
silêncios reais, pequenas reações humanas (respiro, meio sorriso, riso baixo), sem gritar.
Cada roteiro pode ter o próprio `info["estilo_voz"]`, mas só se o arco emocional do episódio exigir.

## Técnica
- **UMA requisição por vídeo** (cota de 10 por voz a cada 24 h, ledger em `.cache/tts/uso.json`). Sem fallback automático de voz:
  se a cota de Achird acabar, o vídeo sai só com legenda até liberar (trocar de voz exige licença do dono do canal).
- Ritmo e pausas são ajustados localmente (Whisper + ffmpeg): `--ritmo 3.4` é o teto de palavras/s enquanto fala.
- Tags de pausa: `<short pause>` (~0,15 s depois do ajuste) e `<long pause>` (~0,55 s).
