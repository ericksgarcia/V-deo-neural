# Fila de temas (fonte única — o PRIMEIRO "pendente" é o próximo vídeo)

**Como usar (para qualquer sessão; leia também `docs/ROTEIRO.md`):** ao pedir "um novo vídeo", pegue o primeiro item com estado **pendente** na
ordem da tabela e implemente direto. Só proponha temas novos se a fila acabar. Ao entregar, troque o estado para
**feito (EPxx)** aqui e registre em `docs/EPISODIOS.md`. Ordem da tabela = prioridade definida pelo dono do canal
(1 a 10 primeiro, depois A a J).

Critério dos temas: a ação principal tem que ficar óbvia em 1 segundo no celular, sem som; melhor ainda com
**dois lados** (co-evolução) ou uma "descoberta" com nome. As descobertas das fichas são **hipóteses**: o roteiro só
afirma o que o treino real mostrar. Itens "parecido com X" são variações aceitas pelo dono; ao fazer um, ajuste o
ângulo para não repetir o outro.

| # | Tema | Vista | Dois lados? | Esforço | Estado | Ideia |
|---|---|---|---|---|---|---|
| 1 | **Paciente Zero (quarentena)** | de cima | sim | baixo | **feito (EP10)** | Um ponto contagioso numa cidade de IAs: elas fogem e se juntam. Triagem 13/20 (AJUSTAR) → treino curado (verde mais lento). |
| 2 | **O Dilema da Ambulância** | de cima | sim (assimétrico) | médio | **feito (EP11)** | Carros aprendem (ou não) a dar passagem; o "malandrinho" pega o vácuo. Parecido com a ambulância sugerida no CTA do EP05 (cruzamento). |
| 3 | **Mudança de Sofá** | de cima | não (cooperativo) | médio | **feito (EP12)** | Duas IAs presas pelas pontas de um sofá numa quina em L; humor pastelão. |
| 4 | **A Porta Giratória** | de cima | não | alto | **feito (EP13)** | 100 IAs, uma catraca: engarrafamento, fila e dança sincronizada. Parecido com A (evacuação). |
| 5 | **Escolta VIP** | de cima | sim | baixo | **feito (EP14)** | Seguranças x assassinos; escudo humano e prensa na parede. Parecido com C (torre). |
| 6 | **O Chão é Lava** | de lado | não | baixo | **feito (EP15)** | Plataformas e lava subindo; IAs usam as outras como degrau. |
| 7 | **Esconde-Esconde no Escuro** | de cima | sim | médio | **feito (EP16)** | Cones de lanterna: o fugitivo vira estátua ou cola nas costas do caçador. |
| 8 | **Queimada de IAs** | de cima | sim | alto | **feito (EP17)** | Azul x vermelho. Triagem 17/20 (GO). A "cera" não apareceu; o vídeo conta "largar a bola" e "acertar mais". Parecido com J (queimada 3x3), que fica como variação. |
| 9 | **Fuga com Cobertura** | de cima | sim | médio | **feito (EP11)** | Atravessar a zona de tiro de uma torreta atrás de blocos móveis. |
| 10 | **Cão Pastor** | de cima | sim | alto | pendente | 1 cão x 15 ovelhas rebeldes. Parecido com F (cão pastor). |
| A | **Evacuação de incêndio** | de cima | não | baixo | pendente | 100 IAs num prédio em chamas com uma só porta. |
| B | **Travessia de rio (gnus x crocodilos)** | de cima | sim | médio | pendente | Manada atravessa rio com correnteza e predadores. |
| C | **Defesa de torre** | de cima | sim | médio | pendente | 5 guardas com escudo x 50 invasores. |
| D | **Tempestade de meteoros** | de cima | não | baixo | pendente | Sombra vermelha avisa o impacto em 2 s. |
| E | **Guerra de preços dinâmica** | de cima | sim | médio | pendente | 50 IAs vendendo o mesmo produto. |
| F | **Cão pastor e ovelhas** | de cima | um lado | médio | pendente | 50 ovelhas medrosas para dentro do cercado. |
| G | **Duelo de canhões com vento** | de lado | sim | baixo/médio | pendente | Dois tanques atirando por cima de uma montanha. |
| H | **Guerra de pintura (Paint War)** | de cima | sim | médio/baixo | pendente | Duas populações pintando o chão. |
| I | **Bolinha no labirinto inclinado** | de cima | não | baixo/médio | pendente | A IA inclina o chão para guiar a bolinha. |
| J | **Queimada 3x3** | de cima | sim | médio | pendente | Desviar ou pegar a bola no ar. |

Inéditos que ainda não entraram na fila: blefe (truco), formigas (trilha e guerra), cardume contra tubarão.

## Fichas dos temas 1 a 10

Formato: gancho · cérebro · descobertas · virada · pergunta · esforço · risco. Atenção: o "gancho" e a "pergunta" das fichas
são só sementes. No vídeo, o gancho segue o `docs/ROTEIRO.md` (verbo "-ei" + número real da geração 1) e a pergunta final
é sobre o que aconteceu no treino, sem votação.

**1. Paciente Zero.** Gancho: "Soltei um 'vírus' numa cidade de IAs para ver se elas aprenderiam a fazer quarentena sozinhas." 100 pontos azuis e 1 verde-tóxico; encostar contagia. Infectados (ganham infectando) x saudáveis (ganham sobrevivendo). Entradas: distância/ângulo ao infectado mais próximo, distância às paredes; saídas: andar e girar. Descobertas: O Pânico (correm para o canto e morrem juntos); O Distanciamento (raio de espaço pessoal); Prisão Humana (cercam o infectado). Virada: a muralha funciona até um guarda ser infectado e ela virar bomba-relógio. Pergunta: "A muralha humana foi corajosa ou a ideia mais burra possível?" Esforço: baixo. Risco: centro da tela vazio, todos nas bordas.

**2. O Dilema da Ambulância.** Gancho: "Coloquei uma ambulância numa avenida de IAs para ver se elas aprenderiam a dar passagem." Rodovia de cima, carros roxos e ambulância piscando (vermelho/azul) cruzando de baixo para cima. Carros perdem pontos se bloqueiam a emergência. Entradas: raycasts para carros e ambulância; saídas: acelerar/frear, virar. Descobertas: Fuga Desesperada (bater no muro); Efeito Maré (corredor central perfeito); O Malandrinho (pegar o vácuo da ambulância). Virada: os malandrinhos criam um engarrafamento pior quando ela precisa frear. Pergunta: "O 'Malandrinho' foi falha no meu código ou genialidade da IA?" Esforço: médio (tráfego de fundo contínuo, peso da punição). Risco: os carros aprendem a andar pelo acostamento desde a geração 1.

**3. Mudança de Sofá.** Gancho: "Amarrei duas IAs pelas pontas de um sofá e mandei elas passarem por uma porta." Dois círculos ligados por retângulo rígido; corredor com quina em L. Cooperativo (ganham ou perdem juntas). Entradas: raycasts locais da ponta e tensão do sofá; saídas: frente/trás, virar. Descobertas: Cabo de Guerra; O Rebocador (uma de ré arrastando a outra); O Pivô. Virada: na geração mil aprendem a bater o sofá na parede até a física bugar e atravessar. Pergunta: "Na mudança, você pensa e gira ou só é arrastado?" Esforço: médio (junta rígida). Risco: difícil sincronizar duas mentes sem comunicação.

**4. A Porta Giratória.** Gancho: "Coloquei 100 IAs desesperadas para passar por uma porta giratória sem travar o mecanismo." Duas salas, porta em cruz no meio. Sem lados. Entradas: posição das pás, distância ao objetivo, raycasts de outras IAs; saídas: frente/trás, girar. Descobertas: O Engarrafamento; A Fila; Dança Sincronizada. Virada: uma mutação que corta caminho trava tudo na geração 500. Pergunta: "Você empurra a porta ou tem paciência de esperar?" Esforço: alto (dobradiça com dezenas de corpos, glitches). Risco: nunca achar a dança.

**5. Escolta VIP.** Gancho: "Dei um alvo VIP para 3 IAs protegerem, enquanto outras 3 aprenderam a ser assassinas." Ponto dourado (VIP lento), azuis (seguranças), vermelhos (assassinos). Entradas: distância/ângulo ao VIP, raycasts ao inimigo; saídas: acelerar, virar. Descobertas: Kamikaze; Escudo Humano; A Distração. Virada: seguranças prensam o VIP no canto para ninguém atacar por trás. Pergunta: "Você torceu pela defesa ou pelo ataque?" Esforço: baixo. Risco: calibrar velocidades (um lado ganha sempre).

**6. O Chão é Lava.** Gancho: "As IAs têm 10 segundos para subir nas plataformas antes que a lava suba." Vista lateral 2D, lava neon subindo, plataformas aleatórias. Sem lados. Entradas: altura da lava, distância à plataforma acima; saídas: andar, pular. Descobertas: Pulo de Fé; A Escadinha; A Traição (pular na cabeça das outras). Virada: empilham umas nas outras, sacrificando a de baixo como degrau. Pergunta: "O sacrifício pela geração futura foi cruel ou prático?" Esforço: baixo. Risco: baixíssimo.

**7. Esconde-Esconde no Escuro.** Gancho: "Dei lanternas limitadas para IAs caçadoras tentarem achar fugitivos num mapa escuro." Fundo preto, cones neon dos caçadores (vermelhos), fugitivos (verdes) só aparecem iluminados. Fugitivos só sabem se estão iluminados e a distância; caçadores só veem dentro do cone; saídas: andar e girar. Descobertas: O Farol (girar sem parar); Estátua; Ponto Cego (colar nas costas do caçador). Virada: os fugitivos passam a perseguir os caçadores por trás. Pergunta: "Teria coragem de se esconder colado nas costas do caçador?" Esforço: médio (raycast em cone). Risco: fugitivos ficam parados nos cantos.

**8. Queimada de IAs.** Gancho: "Ensinei redes neurais a jogar queimada e a evolução tática foi assustadora." Quadra dividida, 3 azuis x 3 vermelhas, bola neon. Entradas: raycasts da bola, distância do inimigo; saídas: andar, girar, arremessar. Descobertas: O Fominha; O Gandula; Linha de Passe. Virada: a campeã pega a bola, recua e nunca arremessa, vencendo pelo tempo. Pergunta: "Prefere o time que ataca sem parar ou o que faz cera?" Esforço: alto (estado "com a bola"). Risco: dezenas de milhares de gerações para ligar soltar a bola a eliminar.

**9. Fuga com Cobertura.** Gancho: "As IAs precisam atravessar a zona de tiro de uma torreta, usando apenas blocos móveis como proteção." Torreta vermelha no centro, IAs azuis à esquerda, blocos verdes lentos. Torreta: ângulo da IA mais próxima; IAs: raycast da bala e do bloco; saídas: girar/atirar, cima/baixo/frente. Descobertas: O Suicida; Zigue-Zague; O Carona (atrás do bloco). Virada: a torreta passa a atirar nos blocos para desproteger as IAs. Pergunta: "Zigue-Zague ou Carona medroso?" Esforço: médio (projéteis). Risco: torreta imbatível já na geração 2.

**10. Cão Pastor.** Gancho: "Coloquei uma IA no papel de cão pastor para ver se ela domava um rebanho de IAs rebeldes." 1 cão laranja, 15 ovelhas brancas, curral quadrado. Cão: direção do centro do rebanho e da ovelha mais distante; ovelhas: raycast do cão; saídas: andar e girar. Descobertas: Espalha-Rodas; O Abraço (círculos amplos); O Sacrifício. Virada: o cão empurra as ovelhas para os cantos em vez de mirar no curral. Pergunta: "O cão foi genial ou as ovelhas desistiram rápido demais?" Esforço: alto (boids). Risco: o cão gira em volta de uma ovelha só se a pontuação for mal feita.


## Fichas dos temas A a E

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


## Notas dos temas F a J

Notas rápidas:
- **F:** descobertas prováveis: contornar por trás, cercar. Métrica: ovelhas no cercado. Risco: levar muitas gerações para achar o "contornar".
- **G:** entradas: ângulo, força, vento, onde caiu o tiro anterior. O vento precisa variar para a virada "usou o vento a favor".
- **H:** métrica: % do chão pintado. Precisa de regra que gere estratégia (pintar por cima do rival, bordas).
- **I:** descoberta provável: usar a parede para frear. Apelo mais visual (um lado só).
- **J:** tema bem brasileiro. Descobertas prováveis: finta e mirar à frente. Não fazer 6x6 (complica demais).

Descartadas da lista de 50 (não propor): vôlei 2x2, tag team, ponte humana, pinball, enxame construtor, espelhos com laser, jogo da velha, Tetris, pistas falsas, Snake multiplayer, equilíbrio de monociclo; e as repetidas: polícia (já feito), estádio (= evacuação A), pedestres (= cruzamento EP05), basquete (já feito).


## Já feitos (arquivo; não repetir)

Pênalti (rascunho), foguete (rascunho), baliza, robô andador, drone na tempestade, corrida de carrinhos, sumô de IAs,
polícia e ladrão, cabo de guerra de enxames, cruzamento sem semáforo. Gravados pelo dono fora do repositório:
goleiro x atacante 1 contra 1, arremesso de basquete. Detalhes e arquivos em `docs/EPISODIOS.md`.

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
