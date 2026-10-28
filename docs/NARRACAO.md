# Tom da narração (decidido em out/2026, voz **Achird**)

Recomeçamos do zero. Antes a voz era de "locutor de trailer" (Charon, ritmo de 3 palavras/s, suspense
anunciado). Agora é **um amigo curioso assistindo ao experimento junto com você**.

## Quem fala
- Um amigo no telefone, perto do microfone, contando algo que mal acredita ter visto. Nunca locutor, nunca YouTuber gritando.
- Fala em primeira pessoa quando ajuda: "Eu comecei com 150 carros." "Eu mudei a largada."
- Reage como gente: "Bateu. De novo." "Chuta aí: quantos bateram?" Humor seco nas falhas, emoção contida nos acertos.

## Regras do texto
1. **Frases curtas** (até ~9 palavras), uma ideia por frase. Contraste em vez de adjetivo.
2. **Um número por frase, no fim dela**, depois de uma pausa (`<long pause>`): o número aterrissa sozinho.
3. **Nada de palavras de hype** ("incrível", "chocante", "você não vai acreditar"). A surpresa vem do fato.
4. **Pergunta de verdade ao espectador** com silêncio antes da resposta ("Chuta aí… <long pause> sete em cada dez").
5. Regras do jogo explicadas como para um amigo esperto: "Quem vai melhor vira pai da próxima turma. Quem bate sai do jogo."
6. Quando finalmente dá certo, o tom é de **alívio emocionado**, não de comemoração.
7. Final leve e provocador, com escolha de lado (nunca só "comenta aí").

## Direção de voz (vai em `speechMetadata.style`, nunca no texto)
Fica em `neuralab/audio.py` (`ESTILO_PADRAO`): voz Achird, suave, perto do microfone, ~2,6 palavras/s,
silêncios reais, pequenas reações humanas (respiro, meio sorriso, riso baixo), sem gritar.
Cada roteiro pode ter o próprio `info["estilo_voz"]`, mas só se o arco emocional do episódio exigir.

## Técnica
- **UMA requisição por vídeo** (cota de 10 por voz a cada 24 h, ledger em `.cache/tts/uso.json`). Sem fallback automático de voz:
  se a cota de Achird acabar, o vídeo sai só com legenda até liberar (trocar de voz exige licença do dono do canal).
- Ritmo e pausas são ajustados localmente (Whisper + ffmpeg): `--ritmo 3.4` é o teto de palavras/s enquanto fala.
- Tags de pausa: `<short pause>` (~0,15 s depois do ajuste) e `<long pause>` (~0,55 s).
