# Banco de ideias (todas as 10 abaixo JÁ FORAM FEITAS)

> **Aviso:** o dono do canal já gravou vídeo de todas as ideias desta tabela. Não proponha nenhuma delas. Para um vídeo
> novo, crie temas fora desta lista e confira `docs/EPISODIOS.md`. Esta tabela serve só de referência de critério.
> Ideias ainda inéditas: blefe (truco), formigas (trilha e guerra), cardume contra tubarão.

# Critério dos episódios (todos pensados para 2D neon)

Critério: a ação principal tem que ficar óbvia em 1 segundo no celular, sem som. Melhor ainda se
houver **dois lados** (co-evolução gera viradas sozinha) ou uma "descoberta" com nome.

| # | Ideia | Vista | Por que prende | Dois lados? |
|---|---|---|---|---|
| 1 | **Pênalti** (feito) | de cima | finta, leitura de corpo, torneio irônico | sim |
| 2 | **Foguete** (feito) | de lado | explosões, primeiro pouso | não |
| 3 | **Baliza** (feito) | de cima | todo mundo sofreu na autoescola | não |
| 4 | **Robô aprendendo a andar** | de lado | quedas engraçadas, jeitos esquisitos de andar que surgem | não |
| 5 | **Drone na tempestade** | de lado | vento, raios, "aprendeu a usar o vento a favor" | não |
| 6 | **Sumô de IAs** | de cima | empurra-empurra, truque de desviar no último segundo | sim |
| 7 | **Goleiro x atacante 1 contra 1** | de cima | drible vs saída do goleiro | sim |
| 8 | **Polícia e ladrão num labirinto** | de cima | emboscadas, atalhos, esconderijos | sim |
| 9 | **Arremesso de basquete** | de lado | trajetória, "descobriu o arremesso de tabela" | não |
| 10 | **Corrida de carrinhos** | de cima | ultrapassagem, fechar a porta, batidas | sim (todos contra todos) |

## Fórmula de roteiro (vale para todos)

1. **0–3 s:** uma pergunta ou tensão sobre a geração 1, nunca o resultado final. "Coloquei X… quantos conseguem?"
2. **3–10 s:** quem são os lados e a regra (seleção + mutação) em duas frases.
3. **Geração 1:** o caos, com um número ("quatro em cada dez...").
4. **Uma virada a cada 8–12 s**, cada uma com um cartão "DESCOBERTA #n" e o número antes → depois.
5. **Calmaria enganosa** ("o placar trava… mas…") antes da maior virada.
6. **Final irônico tirado dos dados** (torneio entre gerações, ou o pior vence o melhor).
7. **Chamada com escolha de lado** ("time X ou time Y?"), nunca só "comenta aí".
8. **Laço:** o último quadro funde no primeiro.

**Regra nova:** o gancho NÃO mostra o resultado final; abra na geração 1 e mostre a melhora aos poucos.

Use `--so-roteiro` e rode o `analista-roteiro` antes de renderizar.

---

# Fila de próximos temas (aprovados pelo dono do canal; NÃO gerados ainda)

Ideias inéditas (fora das 10 acima e dos episódios feitos). Ao pedir "um novo vídeo", ofereça estas primeiro
(e confirme na web que ainda são inéditas). Sai da fila quando virar episódio em `docs/EPISODIOS.md`.
As "descobertas" abaixo são **hipóteses**: o roteiro só afirma o que o treino real mostrar.
Lembrete: não mostrar o resultado final no início; abrir na geração 1.

| # | Tema | Gancho (sem revelar o final) | Vista / lados | Esforço |
|---|---|---|---|---|
| A | **Evacuação de incêndio** (100 agentes, uma porta) | "Coloquei 100 IAs num prédio em chamas com uma só porta." | de cima, sem dois lados (contra o fogo e entre si) | baixo |
| B | **Travessia de rio** (gnus x crocodilos) | "Uma manada precisa atravessar um rio com correnteza e predadores." | de cima, dois lados | médio (correnteza; cuidar para a geração 1 não morrer 100%) |
| C | **Defesa de torre** (5 guardas com escudo x 50 invasores) | "Guardas só com escudos contra uma horda sem armas." | de cima, dois lados | médio |
| D | **Tempestade de meteoros** (sombra vermelha avisa o impacto em 2 s) | "Prever onde o próximo meteoro vai cair." | de cima, sem dois lados | baixo (empurrão entre agentes exige física simples de colisão) |
| E | **Guerra de preços dinâmica** (lojas neon x clientes) | "Deixei 50 IAs vendendo o mesmo produto para ver quem quebra quem." | de cima, dois lados (vendedores entre si) | baixo na conta, médio na arte |

## Detalhes por tema

**A. Evacuação.** Entradas: direção/distância da porta, distância do fogo, agente mais próximo, velocidade.
Saídas: aceleração X/Y. Hipóteses: efeito manada no gargalo; filas diagonais; fogo avança e muda a pressa.
Final possível: o grupo que se organiza sai mais rápido do que o que corre direto. Pergunta: "Fila ou empurrar?"

**B. Travessia.** Presa: vetor para a margem oposta, correnteza, predador mais próximo, aliados por perto; saídas:
direção e força do nado. Predador evolui junto (segundo cérebro). Hipóteses: linha reta fatal (a correnteza leva
todos); entrar contra a correnteza para sair no ponto certo; predadores passam a fechar a saída. Pergunta: "Presa ou predador?"

**C. Torre.** Dois cérebros (guarda: núcleo, horda, ângulo do escudo; invasor: posição dos escudos, núcleo).
Hipóteses: cada guarda persegue um e o núcleo fica livre; círculo fechado; invasores se dividem para enganar.
Pergunta: "Cerco ou ataque em massa?"

**D. Meteoros.** Entradas: zona de impacto mais próxima, tempo até o impacto, abrigo mais próximo, rivais por perto.
Saídas: movimento X/Y. Hipóteses: pânico cego; todos correm para o mesmo abrigo; empurrar o rival para fora.
Só afirmar "empurrão" se o treino mostrar de fato (medir contatos). Pergunta: "Salvar o colega ou empurrar?"

**E. Guerra de preços (dinâmica).** Para não ficar abstrato nem estático:
- **Cena viva:** lojas neon num mapa, clientes como partículas que fluem para a loja de melhor preço+distância.
  O preço de cada loja aparece flutuando sobre ela e muda ao vivo; um gráfico de preços por geração ao lado.
- **Mercado que muda no tempo:** a demanda tem picos (ondas de clientes, "dia de promoção") e o custo do produto
  sofre choques; o estoque acaba e reabastece. Assim o cérebro precisa reagir, não decorar um preço.
- **Entradas:** seu preço, média dos rivais, estoque, fila de clientes, fase da demanda. Saída: subir/descer o preço.
- **Hipóteses:** todos vendem abaixo do custo e quebram juntos; os preços passam a subir e cair em sincronia;
  alguém baixa o preço só nos picos para esgotar o rival. Sem cérebro compartilhado e sem canal de comunicação.
- **Honestidade:** medir (preço médio x custo, lucro, correlação entre preços). Só chamar de "cartel" se os números
  mostrarem preços sincronizados acima do custo; nunca afirmar que apps reais fazem isso. Dizer "parece um cartel".
- **Risco:** visual abstrato se os clientes não ficarem claros; calibrar para a geração 1 não ter lucro zero para todos.
