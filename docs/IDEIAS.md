# Próximos episódios (todos pensados para 2D neon)

Critério: a ação principal tem que ficar óbvia em 1 segundo no celular, sem som. Melhor ainda se
houver **dois lados** (co-evolução gera viradas sozinha) ou uma "descoberta" com nome.

| # | Ideia | Vista | Por que prende | Dois lados? |
|---|---|---|---|---|
| 1 | **Paciente Zero (quarentena)** | de cima | um vírus numa cidade de IAs: elas descobrem o distanciamento sozinhas | sim |
| 2 | **O Dilema da Ambulância** | de cima | carros aprendem (ou não) a dar passagem; o "malandrinho" pega o vácuo | sim (assimétrico) |
| 3 | **Mudança de Sofá** | de cima | duas IAs presas pelas pontas de um sofá numa quina em L; humor pastelão | não (cooperativo) |
| 4 | **A Porta Giratória** | de cima | 100 IAs, uma catraca: engarrafamento, fila e dança sincronizada | não (tragédia dos comuns) |
| 5 | **Escolta VIP** | de cima | seguranças x assassinos; o escudo humano e a prensa na parede | sim |
| 6 | **O Chão é Lava** | de lado | plataformas e lava subindo; IAs usam as outras como degrau | não |
| 7 | **Esconde-Esconde no Escuro** | de cima | cones de lanterna: o fugitivo vira estátua ou cola nas costas do caçador | sim |
| 8 | **Queimada de IAs** | de cima | azul x vermelho; vence quem descobre que não arremessar também ganha | sim |
| 9 | **Fuga com Cobertura** | de cima | atravessar a zona de tiro de uma torreta atrás de blocos móveis | sim |
| 10 | **Cão Pastor** | de cima | 1 cão x 15 ovelhas rebeldes até o curral | sim |
| 11 | **Pênalti** (feito) | de cima | finta, leitura de corpo, torneio irônico | sim |
| 12 | **Foguete** (feito) | de lado | explosões, primeiro pouso | não |
| 13 | **Baliza** (feito) | de cima | todo mundo sofreu na autoescola | não |
| 14 | **Robô aprendendo a andar** (feito) | de lado | quedas engraçadas, jeitos esquisitos de andar que surgem | não |
| 15 | **Drone na tempestade** (feito, EP03) | de lado | vento, raios, "aprendeu a usar o vento a favor" | não |
| 16 | **Sumô de IAs** | de cima | empurra-empurra, truque de desviar no último segundo | sim |
| 17 | **Goleiro x atacante 1 contra 1** | de cima | drible vs saída do goleiro | sim |
| 18 | **Polícia e ladrão num labirinto** | de cima | emboscadas, atalhos, esconderijos | sim |
| 19 | **Arremesso de basquete** | de lado | trajetória, "descobriu o arremesso de tabela" | não |
| 20 | **Corrida de carrinhos** | de cima | ultrapassagem, fechar a porta, batidas | sim (todos contra todos) |


## Fichas dos temas 1 a 10 (propostas novas, na ordem do ranking)

Formato: gancho · cérebro · descobertas · virada · pergunta · esforço · risco.

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

## Fórmula de roteiro (vale para todos)

1. **0–3 s:** o comportamento mais surpreendente, em replay. "Coloquei X… e ele aprendeu a Y."
2. **3–10 s:** quem são os lados e a regra (seleção + mutação) em duas frases.
3. **Geração 1:** o caos, com um número ("quatro em cada dez...").
4. **Uma virada a cada 8–12 s**, cada uma com um cartão "DESCOBERTA #n" e o número antes → depois.
5. **Calmaria enganosa** ("o placar trava… mas…") antes da maior virada.
6. **Final irônico tirado dos dados** (torneio entre gerações, ou o pior vence o melhor).
7. **Chamada com escolha de lado** ("time X ou time Y?"), nunca só "comenta aí".
8. **Laço:** o último quadro funde no primeiro.

Use `--so-roteiro` e rode o `analista-roteiro` antes de renderizar.
