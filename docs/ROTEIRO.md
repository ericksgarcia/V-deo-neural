# Guia de roteiro v2 (OBRIGATÓRIO para todo vídeo novo)

Decidido pelo dono do canal em out/2026 depois de uma análise de retenção. Vale para os **próximos** vídeos
(os já publicados não são refeitos). Se qualquer regra daqui conflitar com `IDEIAS.md` ou `EPISODIOS.md`, vale esta.
Regras antigas que continuam valendo: nunca mostrar o resultado final no início, tudo 2D neon, todo número vem do
treino real, uma única requisição de TTS por vídeo, efeitos sonoros baixos (ver `CLAUDE.md`).

**Atualização v3 (retenção, out/2026):** leia também a **seção 13** (promessa do teste final, números em algarismos,
revelações com `<long pause>`, cenas curtas, arena em pé). O motor novo (layout v3) já faz sozinho a trilha de descobertas,
o suspense das revelações, o zoom contínuo e a simulação ao fundo das telas de dados; o roteiro só precisa dar o material.

O que mudou: **(1)** CTA sem votação, **(2)** vídeo curto, **(3)** gancho com número da geração 1, **(4)** poucos
números falados, **(5)** um herói, **(6)** re-gancho no meio, **(7)** laço falado, **(9)** legenda do post nova.
Cada regra tem um limite medível; `python ferramentas/confere_roteiro.py` confere os que dá para medir.

---------------------------------------------------------------------------------------------------------------

## 1. Duração e tamanho (regra 2)

- **Alvo 40–55 s. Teto 60 s** (o render final não pode passar de 60,0 s; se passar, corte cenas, não acelere a voz).
- **100 a 140 palavras faladas** no total (a ~2,6 palavras/s + pausas). Acima de 150 palavras: cortar.
- **No máximo 3 descobertas** (3 cartões "DESCOBERTA"). Se o treino achou mais, mostre as 3 mais fáceis de entender
  e deixe o resto de fora.
- **Premissa e regra do jogo numa cena só**, em 2 frases curtas, juntas, no mesmo bloco falado. Exemplo:
  "Cada carro tem um cérebro vazio. Quem vai melhor vira pai da próxima turma; quem bate sai."
  Proibido ter uma cena separada só para "a regra cruel".
- Fases de treino repetitivas (ex.: "só A / só B / os dois" três vezes) viram **uma** frase ou **uma** barra, nunca
  uma cena por fase. Mostre no máximo 2 fases de treino.
- Orçamento por tempo (some ≈ 50 s):

| tempo | bloco | conteúdo |
|---|---|---|
| 0–3 s | **GANCHO** | 1 cena, ≤ 16 palavras: premissa + número da geração 1 + estranheza (ver seção 2) |
| 3–9 s | PREMISSA + REGRA + PROMESSA | 1 cena, ≤ 16 palavras (seção 1) + a **promessa do teste final** (seção 13), sem resultado |
| 9–15 s | GERAÇÃO 1 | o caos, um único número, ex.: "De 150, só uma passa." + 1 montagem de falhas (≤ 3 s) |
| 15–38 s | **3 DESCOBERTAS** | ~7 s cada; "calmaria enganosa" antes da última; **re-gancho** na metade (seção 6) |
| 38–46 s | TESTE / IRONIA | situação nova ou torneio entre gerações; o dado irônico do final |
| 46–52 s | CTA + LAÇO | 1 pergunta sobre o que se passou (seção 8) + a frase que fecha o laço (seção 7) |

## 2. Gancho (regra 3) — cena 0, primeiros 3 segundos

Fórmula: **[verbo no passado, 1ª pessoa] + [premissa em ≤ 8 palavras] + [número REAL da geração 1 ou da primeira
falha] + [estranheza/pergunta]**. Tem que dar vontade de ver o que acontece depois SEM mostrar o resultado final.

- A frase de abertura começa com verbo em 1ª pessoa do passado terminado em "-ei" (Tirei, Treinei, Coloquei, Soltei,
  Deixei, Amarrei, Dei…). Isso é necessário para o laço da seção 7.
- Contém **um número** da geração 1 (ex.: "de 150, só uma passou sem bater") OU uma impossibilidade concreta
  ("em 92% dos jogos, a caixa nem se mexe").
- ≤ 16 palavras no total. Sem "olha", sem "você não vai acreditar", sem hype ("incrível", "chocante").
- Sem apresentação ("Oi, esse é o canal…"). Sem pergunta genérica ("Será que ela consegue?").
- Na tela, no segundo 0, já há movimento e o `titulo_gancho` com 2 linhas curtas.
- NUNCA o resultado final (ex.: "82% passam"). Só o começo ruim. Honestidade: o número tem de sair de `hist`/medida.
- Exemplos (já com fatos reais do passado, só para ilustrar o formato):
  - Cruzamento: "Tirei o semáforo de um cruzamento. De 150 tentativas, só uma passou sem bater."
  - Cabo: "Coloquei cinco robôs diante de uma caixa pesada. Em 92% dos jogos, ela nem se mexeu."
  - Baliza: "Mandei 150 carros estacionarem sem ensinar nada. Nenhum conseguiu na primeira geração." (só se `hist` confirmar)
- Escreva 3 candidatos de gancho; o `analista-roteiro` escolhe/rescreve; só então siga.

## 3. Poucos números (regra 4)

- **Máx. 6 dados falados no vídeo inteiro** (números de treino/medida; o número da geração, "Geração 47", NÃO conta).
  Máx. **1 número "herói" por cena**; um "antes → depois" do mesmo dado conta como 1.
- O restante dos números vai para o **visual** (cartão, barra, log, gráfico), não para a voz.
- Fale em "X em cada dez" ("quase nove em cada dez") em vez de "87%" quando possível; arredonde sem mentir.
- **Escreva o número em ALGARISMOS na fala** (`"73 de 100"`, `"1,8"`, vírgula decimal): a legenda mostra o número grande,
  em amarelo e com pulo; a voz lê por extenso sozinha (`audio.falavel`). Não use `por_extenso()`/`numero()` na fala
  (a legenda fica "setenta e três" em três blocos e o conferidor não conta o dado). Unidades por extenso ("metros por segundo").
- O número vem sempre **no fim da frase**, depois de `<long pause>` ou `<short pause>`.
- Cada cartão "DESCOBERTA" tem o formato `antes → depois` (mesmo dado). Cartão e voz repetem o MESMO número.

## 4. O herói: "o campeão" (regra 5)

Personagem recorrente em TODO vídeo. Honestidade importante: o algoritmo copia os 8 melhores de cada geração
(`elite=8` em `evolucao.proxima_geracao`), então a **linhagem** do campeão é real, mas o corpo muda a cada geração.
Portanto:

- Chame-o sempre de **"o campeão"** (ou "a campeã", conforme o tema: o carro campeão, o drone campeão).
  Diga "o campeão da geração 47", NUNCA "o mesmo carro desde o começo".
- Em cada replay de descoberta, use como `foco` o melhor da geração (`A.busca(rodada, "primeiro")`) e deixe a câmera
  nele. O campeão aparece em **pelo menos 3 cenas** e a palavra "campeão"/"campeã" é dita em **pelo menos 2** falas.
- Momento emocional obrigatório: **1 queda/erro do campeão** (replay lento, "Bateu." ou "Caiu.") e **1 acerto** dele.
- No gancho ou na geração 1, mostre o campeão da geração 1 falhando (ele é o "azarão" que a gente quer ver melhorar).
- Em temas de dois lados, haja um campeão por lado; a fala escolhe um para torcer, o outro é o rival.

## 5. Estrutura de cada descoberta (7–8 s)

1. **Quebra de padrão visual** a cada cena (≥ 1 mudança de câmera/vista/cartão a cada 4–5 s). Cena parada > 5 s: cortar.
2. Frase de contexto ≤ 8 palavras com "Mas…", "Aí…", "Até que…".
3. O truque com **nome** curto (2–3 palavras), no cartão.
4. O número antes → depois no fim da fala.
5. A cada descoberta, abra uma dúvida pequena que a próxima resolve ("Mas tem um problema.").

## 6. Re-gancho no meio (regra 6)

Entre **40% e 60%** do tempo total, uma frase que reabre a curiosidade E que será respondida antes do fim.
Padrões: "Mas aqui aparece a parte que eu não esperava." / "Só que tem uma pegadinha. Eu conto já." /
"O placar trava… Será que acabou?" (a calmaria enganosa já conta se estiver nessa janela).
- Precisa terminar em suspense (pausa longa) e ser **paga** (resposta) antes do teste final.
- Proibido prometer algo que o treino não entregou.

## 7. Laço falado (regra 7)

A última frase falada do vídeo é **cortada de propósito** e completa a primeira.
- Gancho começa com um verbo "-ei" (seção 2): "**Tirei** o semáforo de um cruzamento…".
- A última fala termina exatamente assim: **"Porque tudo começou quando eu…"** (ou "E tudo isso começou quando eu…").
  Ela vem DEPOIS da pergunta do CTA, na mesma cena final, depois de `<short pause>`. Texto sem ponto final, só reticências.
- O último quadro do vídeo funde no primeiro (isso o motor já faz).
- O Whisper/legenda aceita reticências finais; não coloque nada depois delas.

## 8. CTA sem votação (regra 1)

**Proibido** pedir voto, prometer ou condicionar o próximo vídeo. Palavras/expressões PROIBIDAS no vídeo e na legenda:
"mais votado", "vira o próximo", "próximo vídeo", "próximo episódio", "você escolhe o próximo", "vote", "votar",
"qual você quer ver", "comenta (A/B/número) para escolher", "quem ganhar ganha…", "motor mais rápido" (promessa).
(O conferidor barra essas expressões.)

O CTA é **UMA pergunta sobre o que se passou no vídeo** — uma dúvida real que o próprio resultado deixa aberta,
com dois lados defensáveis tirados dos dados (a "ironia" do final). ≤ 16 palavras, termina em "?", vem logo antes da
frase do laço.
Modelos (escolha o que cabe e preencha com o fato real do vídeo):
- Esperteza ou sorte: "O campeão aprendeu a regra ou só decorou aquela pista?"
- Por quê: "Por que o Y piorou justamente quando o X melhorou? Qual a sua teoria?"
- Justo ou trapaça: "Esperar o outro passar é inteligência ou preguiça?"
- Previsão sobre o dado: "Se eu dobrar o vento, o campeão ainda pousa? Chuta aí."
- Quem merece: "O azul final é mesmo o melhor? Ou só ganhou porque o rosa parou de treinar?"
Regras: sem "comenta aí" solto; sem dois pedidos na mesma fala; sem tema futuro; pode (e deve) citar o número
irônico do final para a pergunta ter assunto. Pode terminar com "Responde aqui embaixo."

## 9. Legenda do post (regra 9) — arquivo `saida/<ep>_legenda.txt`

Formato fixo, 4 partes:
1. **Linha 1 = curiosidade, não resumo** (≤ 120 caracteres, 1 emoji no máximo): o fato estranho da geração 1 ou o
   twist, sem entregar o final. Ex.: "De 150 carros, só 1 passou sem bater. Depois de 300 gerações… 🚦"
2. Linha 2: o que é, com termos pesquisáveis em português: "IA aprendendo sozinha por seleção natural.
   Simulação real: X indivíduos, Y gerações, nenhum número inventado."
3. Linha 3: **gatilho de compartilhar** (≠ pergunta do vídeo): "Manda pra quem ainda acha que …" / "Marca quem …".
4. **3 a 5 hashtags** (não mais): `#inteligenciaartificial #ia #aprendizadodemaquina #simulacao` + 1 do tema.
Proibido na legenda: pedir voto, prometer próximo vídeo, as expressões da seção 8.
O `post` é montado em `monta()` do roteiro (retorno `cenas, info, post, ev`); escreva nesse formato.

## 10. Checklist final de aprovação (todos os itens)

- [ ] `python ferramentas/confere_roteiro.py <arquivo>` sem nenhum `FALHA` (ver `CLAUDE.md` passo a passo)
- [ ] gancho com número da geração 1, verbo "-ei", ≤ 16 palavras, sem resultado final
- [ ] ≤ 3 descobertas, ≤ 6 dados falados, 100–140 palavras, duração real final ≤ 60 s
- [ ] "o campeão" em ≥ 2 falas e ≥ 3 cenas; 1 queda e 1 acerto do campeão
- [ ] re-gancho entre 40% e 60% e respondido antes do fim
- [ ] CTA = 1 pergunta sobre o que se passou; zero palavras proibidas; laço "…quando eu…" no fim
- [ ] legenda no formato da seção 9
- [ ] seção 13: promessa do teste nas 3 primeiras cenas, números em algarismos, 2-4 `<long pause>`, nenhuma cena > 18 palavras
- [ ] analistas sem nota < 8 (roteiro, engajamento antes; retenção, visual no rascunho; diretor no fim)

---------------------------------------------------------------------------------------------------------------

## 11. Prompts prontos dos analistas (copie, preencha `<...>` e envie)

Passe SEMPRE só texto: o roteiro (saída de `--so-roteiro`) + os fatos (números do treino/medidas). Nunca o código.
Peça resposta curta. Cada prompt já inclui as regras do guia v2.

**analista-roteiro** (antes da voz):
```
Analise o roteiro do vídeo "<tema>" (TikTok, pt-BR) segundo o guia v2 do canal. Use este critério, nesta ordem:
(1) GANCHO (cena 0): começa com verbo em 1ª pessoa "-ei"? ≤ 16 palavras? traz número real da geração 1? NÃO mostra o resultado final?
sem hype? Dê 3 alternativas verdadeiras. (2) DURAÇÃO/TAMANHO: 100-140 palavras, 40-55 s, ≤ 3 descobertas, premissa e regra
na MESMA cena. Aponte o que cortar. (3) NÚMEROS: ≤ 6 dados falados, 1 por cena (antes→depois conta 1), número no fim da frase.
(4) HERÓI "o campeão": aparece em ≥ 3 cenas e é dito em ≥ 2 falas? tem 1 queda e 1 acerto? nunca "o mesmo carro desde o começo"?
(5) RE-GANCHO entre 40% e 60% do tempo, e é respondido antes do fim? (6) CTA: UMA pergunta sobre o que se passou, ≤ 16 palavras,
SEM voto e SEM promessa de próximo vídeo; sugira 2 perguntas melhores tiradas do dado irônico do final. (7) LAÇO: última fala termina
"Porque tudo começou quando eu…" e completa o gancho? (8) CLAREZA: alguém que nunca ouviu falar de IA entende cada frase?
(9) HONESTIDADE: cada número bate com os FATOS abaixo? Aponte qualquer exagero.
Responda em português: nota 0-10 por critério e geral; os 3 maiores problemas; reescrita linha a linha só do que melhora
(formato `cena N: "antiga" -> "nova"`, mantendo exatamente os mesmos números e fatos); veredito APROVADO (todas as notas ≥ 8) ou REPROVADO.
ROTEIRO:
<cole a saída de --so-roteiro, só a parte das cenas>
FATOS REAIS DO TREINO:
<cole os números: geração 1, cada descoberta antes→depois, teste final, total de quedas/batidas>
```

**analista-engajamento** (antes da voz e de novo antes de publicar):
```
Avalie o potencial de comentários, compartilhamentos e seguidores do vídeo "<tema>" segundo o guia v2. Regras: o CTA NÃO pode pedir voto
nem prometer próximo vídeo/tema; deve ser UMA pergunta sobre o que se passou, com dois lados defensáveis tirados dos dados.
Legenda do post: linha 1 = curiosidade (≤ 120 caracteres, sem resumo e sem entregar o final), linha 2 = o que é com termos pesquisáveis em português
("IA aprendendo sozinha"), linha 3 = gatilho de compartilhar (diferente da pergunta do vídeo), 3 a 5 hashtags. Avalie: (1) qual comentário a maioria
vai escrever? a pergunta rende debate real ou resposta de uma palavra? (2) motivo para compartilhar e para salvar; (3) o vídeo parece parte de uma série
sem prometer nada?; (4) riscos de soar falso/clickbait/"isso é fake". Entregue: nota 0-10, 3 opções de pergunta para o CTA (≤ 16 palavras),
a legenda reescrita no formato acima e 3 ideias de comentário fixado do criador.
ROTEIRO + LEGENDA:
<cole a saída de --so-roteiro, inclusive a parte "legenda:">
```

**analista-retencao** (no rascunho; passe `saida/<ep>_rascunho_analise/roteiro.md` e `mosaico.jpg`):
```
Preveja a retenção segundo a segundo do vídeo "<tema>" (alvo 40-55 s, teto 60 s). Entregue a curva em 0, 1, 3, 5, 10, 20, 30, 45 s e fim, com o motivo de
cada queda. Confira: (a) gancho cria dúvida nos 3 primeiros segundos? (b) há mudança visual/sonora a cada ≤ 5 s (liste as cenas paradas)?
(c) existe re-gancho entre 40% e 60% e ele segura? (d) o campeão aparece e dá para torcer por ele? (e) o laço falado ("…quando eu…") +
fusão do último quadro com o primeiro dá vontade de rever? (f) quais cenas cortar para ficar ≤ 55 s, em ordem de ganho. Dê os 3 maiores riscos de deslize.
```

**analista-visual** (no rascunho): usar o prompt padrão de `.claude/agents/analista-visual.md`, mais: "o campeão está destacado na tela
em todos os replays? o `titulo_gancho` aparece no segundo 0 dentro das zonas seguras do TikTok? o cartão mostra o MESMO número que a voz fala?"

**analista-narracao** (depois da voz): padrão do agente, mais: "alguma palavra de risco foi lida errado (nomes, 'Caiu', 'sumô', números)?
A pergunta do CTA e a frase 'Porque tudo começou quando eu…' ficaram naturais, com a pausa antes? Duração final ≤ 60 s?"

**diretor** (uma vez, no fim): "Revise o episódio `<ep>` com TODOS os analistas e o conferidor (`python ferramentas/confere_roteiro.py`). Só aprove com
todas as notas ≥ 8, zero FALHA no conferidor, duração ≤ 60 s e o checklist da seção 10 de `docs/ROTEIRO.md` completo. Liste o que aceitou e recusou."

## 12. Esqueleto de `monta()` no formato v2 (copie a ordem das cenas)

```python
def monta(hist, A):
    ...
    # 0 GANCHO (≤16 palavras, verbo -ei, número da geração 1, sem resultado final)
    cena(tipo="ao_vivo", ger=0, grupo="g1", titulo_gancho=[("TIREI O SEMÁFORO", BRANCO), ("E DEIXEI UMA IA NO COMANDO", AMARELO)],
         fala=f"Tirei o semáforo de um cruzamento. <short pause> De {n} tentativas, só {s0} passou sem bater.")
    # 1 PREMISSA + REGRA + PROMESSA (≤ 16 palavras; promessa do teste final SEM o resultado — seção 13)
    cena(tipo="ao_vivo", ger=min(4, G - 1), grupo="g1b",
         fala="Quem vai melhor vira pai da próxima turma. <short pause> No fim, eu testo o campeão num cruzamento que ele nunca viu.")
    # 2 GERAÇÃO 1: o campeão da geração 1 falha (replay lento) + montagem curta de falhas
    cena(tipo="replay", ger=0, foco=A.busca(A.rodada(0), "quase") ..., fala="O campeão da geração um. <short pause> Bateu.")
    # 3-5 até 3 DESCOBERTAS (cartão antes→depois; foco = A.busca(rodada, "primeiro") = campeão da geração)
    cena(tipo="replay", ger=g1, foco=k1, cartao={...}, fala=f"Geração {g1+1}. O campeão descobre ... <long pause> De {x} para {y}.")
    # RE-GANCHO a 40-60% do tempo (calmaria enganosa ou pegadinha), respondido depois
    cena(tipo="ao_vivo", ger=g_calma, fala="O placar trava. <short pause> Será que acabou? <long pause>")
    # TESTE / IRONIA tirada dos dados (situação nova ou torneio entre gerações); ger= faz a simulação rodar ao fundo
    cena(tipo="barras", teste=True, ger=G - 1, ..., fala=f"... O campeão da {G}… <long pause> {pct_final}%.")
    # FINAL (última cena): UMA pergunta sobre o que se passou + laço cortado
    cena(tipo="replay", ger=G - 1, foco=campeao, grupo="fim",
         fala="O campeão aprendeu a regra ou só decorou este cruzamento? <short pause> Porque tudo começou quando eu…")
    post = (f"{curiosidade_linha1}\\n"
            f"IA aprendendo sozinha por seleção natural. Simulação real: {n} indivíduos, {G} gerações, nenhum número inventado.\\n"
            f"Manda pra quem ainda acha que ... 👇\\n\\n#inteligenciaartificial #ia #aprendizadodemaquina #simulacao #<tema>")
```
Notas: `escolha=` só pode mostrar as DUAS RESPOSTAS da pergunta do CTA (ex.: pergunta "O CAMPEÃO APRENDEU OU DECOROU?", opções "APRENDEU" / "DECOROU"); nunca temas de vídeos futuros.
Se um cartão/gráfico antigo repete o mesmo número que a voz já disse, mantenha só no visual.

## 13. Retenção v3: o que segura até o fim (vale para todo vídeo novo)

Diagnóstico dos EP13-16 (analistas de retenção, todos os rascunhos): a queda grande vem (a) da cena 1, longa e parada,
(b) de telas sem movimento (barras/gráfico em fundo preto), (c) de números ditos por extenso, que o olho não pega na legenda,
(d) de não haver motivo explícito para ficar até o fim, e (e) de HUD ilegível no celular. O motor resolve (b) e (e); o roteiro
precisa dar (a), (c) e (d).

**O que o motor faz sozinho (layout v3, `neuralab/video.py` + `palco/kit.py`):**
- **Ação maior**: a fileira de baixo (log + rede) saiu; a cena vai de y=362 a 1392 e a legenda fica dentro dela, deslocada
  para longe dos botões do TikTok. O rodapé fica acima da descrição do post.
- **Trilha de descobertas** (faixa logo acima da cena, a partir de 2 s): uma casa por cartão + a casa **TESTE FINAL**. As
  fechadas pulsam "? ? ?"; cada uma abre com clarão quando a cena chega. É a promessa visível: "faltam 2 descobertas e o teste".
  A casa do teste é a cena com `teste=True` (ou a 1ª `barras`); nome em `info["nome_teste"]`.
- **Revelação automática em cada `<long pause>`**: a música quase some, sobe um riser no silêncio, e a palavra seguinte entra
  com impacto grave + zoom-soco + clarão. Se a pausa fecha a fala, a revelação cai no corte para a cena seguinte (suspense).
  A lista de revelações sai em `*_analise/roteiro.md`.
- **Nada parado**: cenas ao vivo têm um zoom lento contínuo; telas `barras`/`grafico` com `ger=` mostram a simulação ao fundo.
- **Números em algarismos na legenda** saem amarelos e pulam mais. A trilha sonora abre (filtro e volume) do começo ao fim.
- O título do gancho some quando o carimbo entra (não se sobrepõem mais).

**O que o roteiro precisa dar (o conferidor avisa):**
1. **Promessa do teste final nas 3 primeiras cenas**, sem o resultado: "No fim, eu testo o campeão num lugar que ele nunca viu."
   / "No fim, o campeão enfrenta o da geração 1." É o laço aberto que paga o vídeo inteiro; o teste precisa existir e vir no fim.
2. **Números em algarismos** na `fala` (seção 3). Decimais com vírgula ("1,8"); unidades por extenso.
3. **2 a 4 `<long pause>`**, sempre logo antes do número/da virada que importa (o re-gancho conta). Mais que 5 cansa.
4. **Cenas curtas**: nenhuma fala com mais de 18 palavras (≈ 7 s); a premissa (cena 1) com ≤ 16. Se o conteúdo não cabe,
   ele não é essencial.
5. **Close antes de plano geral**: o primeiro segundo precisa de movimento grande; prefira abrir num replay do campeão da
   geração 1 falhando (ou `ao_vivo` com `vel` alta) a uma vista geral calma.
6. **Teste com suspense**: na cena do teste, diga o número do campeão final por último, depois de `<long pause>`. O motor
   deixa a barra do vencedor (`destaque`) vazia com "?" até esse instante e revela com o impacto (não precisa de `revela=`).
7. **Simulações novas: arena em pé.** A tela útil é ~1020x1030 px. Mundo mais alto que largo (ou quadrado) e câmera de
   replay perto (agente ≥ 60 px na tela). Arena deitada desperdiça metade da cena.
8. Termine em ação (replay do campeão), nunca em tela de dados: o último quadro funde no primeiro (laço).

