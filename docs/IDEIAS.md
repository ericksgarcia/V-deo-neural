# Fila de temas (fonte única — o PRIMEIRO "pendente" é o próximo vídeo)

**Fila REINICIADA em 31/out/2026 a pedido do dono** (a antiga foi excluída; tudo o que ela tinha foi feito ou descartado). Os temas abaixo
passaram por `analista-tema` em lote; o pedido do dono é um "super tema" que prenda até o final.

**Como usar (qualquer sessão; leia também `docs/ROTEIRO.md`):** ao pedir "um novo vídeo", pegue o primeiro **pendente**, rode a triagem de novo
(§16.1) e implemente. Ao entregar, troque o estado para **feito (EPxx)** e registre em `docs/EPISODIOS.md`. Só proponha temas novos se a fila acabar.

## Identidade do canal (o que a fila precisa respeitar)
Pelos 18 episódios e pelo `docs/ANALISE_REFERENCIAS.md`, o que segura gente até o fim: (1) **situação do dia a dia** que qualquer leigo entende em
1 frase (porta, sofá, fila, chão é lava); (2) **caos engraçado na geração 1** (todos fazem a coisa errada juntos); (3) uma **descoberta com apelido**
que "ninguém ensinou"; (4) **twist verdadeiro** no teste final (o preguiçoso/antigo vence, o campeão piora); (5) **pergunta com dois lados**;
(6) **ação legível em 1 s no celular**, arena em pé. Evitar: regra longa, campo invisível (feromônio), coevolução instável, repetir porta/lava/torreta.

| # | Tema | Vista | Dois lados? | Esforço | Estado | Ideia (nota da triagem) |
|---|---|---|---|---|---|---|
| 1 | **Dança das Cadeiras** | de cima | sim (empurrar x esperar) | médio | pendente | **18/20 GO.** 12 IAs, 11 cadeiras, a música para e quem fica em pé sai. G1: todas em cima de 1 cadeira. Descobertas prováveis: ficar colado numa cadeira, empurrar, "o preguiçoso que vence". Recompensa: sobreviver à rodada + pequeno bônus por proximidade (rodapé exato). Risco: converge em poucas gerações? Pergunta: "empurrar é esperteza ou trapaça?" |
| 2 | **Cardume x Tubarão** | de cima | sim (tubarão de regra fixa, dificuldade crescente) | médio | pendente | **16/20 GO.** Peixes aprendem a formar a bola e se dividir. Só os peixes evoluem; currículo no tubarão. Falta virada: procurar twist nos dados (a bola grande vence a solitária?). |
| 3 | **Chuva de Meteoros** | de cima | não (sobrevivência) | baixo | pendente | **15/20 AJUSTAR.** Sombra vermelha avisa 2 s antes (a rede lê a sombra), poucos abrigos. Ironia: chegou no abrigo e foi empurrado. Ângulo: não parecer a torreta. Medir empurrão antes de afirmar. |
| 4 | **Metrô Lotado** | de lado ou de cima | sim (quem sai x quem entra) | alto | pendente | **15/20 AJUSTAR.** Só vale se o corredor aparecer ("deixar sair primeiro é mais rápido"). Currículo: porta larga → estreita; ângulo diferente da porta giratória (EP13). |
| 5 | **Travessia de Rio** | de cima | sim (só a manada evolui; crocodilos de regra fixa) | médio | pendente | **15/20 AJUSTAR.** Manada x crocodilos com correnteza; "atravessar junto ou esperar?". |
| 6 | **Evacuação de incêndio** | de cima | não | alto (CPU) | pendente | **15/20 AJUSTAR.** 40 IAs, uma porta, fogo neon (não lava). Ironia: o pânico trava a porta. |
| 7 | **Pique-Bandeira 2x2** | de cima | sim | alto (converge mal) | pendente | **13/20 AJUSTAR (abaixo de 14: só com ângulo novo na triagem).** Roubar a bandeira e voltar sem ser pego; por último, para dar tempo de ajustar a recompensa. |

Descartados da fila nova (não propor): **Formigas** (11/20, precisa explicar feromônio), **Fila do Supermercado** (12/20, pouco drama), e a lista antiga:
vôlei 2x2, tag team, ponte humana, pinball, enxame construtor, espelhos com laser, jogo da velha, Tetris, pistas falsas, Snake, monociclo, pega-pega.
Ideias antigas fora da fila e não aproveitadas (podem voltar com ângulo novo): defesa de torre, guerra de preços, duelo de canhões, guerra de pintura,
bolinha no labirinto inclinado, queimada 3x3 (parecida com EP17), blefe/truco.

## Já feitos (arquivo; não repetir)
Pênalti (rascunho), foguete (rascunho), baliza, robô andador, drone, corrida de carrinhos, sumô, polícia e ladrão, cabo de guerra, cruzamento,
ambulância, sofá, porta giratória, escolta VIP, chão é lava, esconde-esconde no escuro, paciente zero, fuga com cobertura, queimada, cão pastor.
Gravados pelo dono fora do repositório: goleiro x atacante, basquete. Detalhes em `docs/EPISODIOS.md`.

## Fórmula de roteiro (vale para todos) — resumo; o guia completo é `docs/ROTEIRO.md` (obrigatório)

1. **0–3 s, gancho:** verbo "-ei" + premissa + número REAL da geração 1 (≤ 16 palavras). Nunca o resultado final.
2. **3–9 s:** premissa e regra numa cena só (seleção + mutação em 2 frases).
3. **Geração 1:** o caos, com um número; o campeão da geração 1 falha.
4. **Até 3 descobertas**, ~7 s cada, com cartão "DESCOBERTA #n" (antes → depois) e o campeão em foco.
5. **Re-gancho** entre 40% e 60% do tempo (calmaria enganosa / pegadinha) e resposta antes do fim.
6. **Final irônico tirado dos dados** (torneio entre gerações, situação nova ou o pior vence o melhor), com o **CHUTE**
   antes do número final ("Chuta aí… <long pause>", resposta na cena seguinte, a 70-88% do vídeo).
6b. **Diversão + suspense (§14):** riso nas falhas e depois dos números; silêncio antes deles. 2-3 piadas curtas e verdadeiras.
7. **CTA = UMA pergunta sobre o que se passou** (sem voto, sem prometer próximo vídeo) + **laço falado** ("Porque
   tudo começou quando eu…") + último quadro fundindo no primeiro.
8. Vídeo de **40–55 s (teto 60 s)**, 100–140 palavras, ≤ 6 dados falados.

**Regra mantida:** o gancho NÃO mostra o resultado final; abra na geração 1 e mostre a melhora aos poucos.

Use `--so-roteiro`, `python ferramentas/confere_roteiro.py` e os analistas antes de renderizar (ver `CLAUDE.md`).
