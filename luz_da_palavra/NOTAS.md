# Luz da Palavra — personagem SVG com skinning real (Replicate → LBS → animação)

Vídeo de teste: `saida/jesus_v3.mp4` (17,3 s). Interativo: `saida/anim5.html` (`setT(t)`).

## Pipeline
1. `gen_pro.py` + `prompts_t.py` → `recraft-ai/recraft-v4-styles-pro-svg` com as 2 imagens de referência (frente/costas T-pose): `gen3/frente|costas|perfil.svg` (+ `mao_palma|mao_dorso`, não usadas no teste do "tchau").
2. `build5.py`: SVG → dados (gradientes viram cor sólida), remendos de manto atrás do braço (o desenho tem "buracos" onde o braço cobria o corpo), sola dividida em duas.
3. `engine5.js`: esqueleto + **linear blend skinning** direto nos pontos dos paths (vetor, sem peças). Pesos por distância ao osso, normalizados, com corte de influências pequenas (técnica do Pose Animator, Apache-2.0). Linha do tempo com **GSAP** (seek determinístico).
4. `frames.js` (Playwright) + ffmpeg.

## Aprendizados
- Modelo exige `style_reference_images`; `style_id` sozinho dá 422.
- Contorno gigante (silhueta do corpo) e mangas fundidas ao torso são paths únicos: precisam de classificação por região/cor para não rasgar.
- Pernas giratórias sob túnica longa rasgam: pés como peças rígidas que deslizam e levantam sob a barra funcionam.
- Mão do desenho original tem dedos fundidos (não dá para abrir um a um); módulos de mão separados foram gerados mas ficaram fora do teste.

## POC: malha densa + DragonBones (poc/)
`poc/make_mesh.py` (PNG do SVG -> ~3000 vértices, pesos por difusão tipo BBW -> JSON DragonBones 5.5) + `poc/build_poc.py` (Pixi 4.8.9 + runtime DragonBones MIT) + `poc/frames.js`.
Resultado: `saida/poc_dragonbones.mp4`, comparativo `saida/poc_comparativo.mp4` (esq. rig por path, dir. malha).
Achados: manga dobra de forma contínua (antebraço em 3 ossos), sem rasgos nem fragmentos soltos. Pendências: entalhes claros na silhueta, textura é raster, uma malha só (sem camadas), virada de frente->costas ainda é troca de vista.

## Personagem completo em malha densa (poc2/)
`poc2/meshlib.py` (SVG -> camadas raster -> malha ~3000 vértices -> pesos por difusão -> displays DragonBones) · `poc2/make_rigs.py` (ossos/cápsulas/camadas de frente, costas e perfil) · `poc2/page.js` + `build_page.py` (Pixi 4 + runtime DragonBones + GSAP + molas) · `poc2/frames.js`.
Vídeo: `saida/jesus_v4.mp4` (17,5 s). Rodar: `mesh/bin/python poc2/make_rigs.py && python3 poc2/build_page.py && node poc2/frames.js $PWD/poc2/page.html poc2/_f`.
- Perfil em 4 camadas (corpo, pé de trás, pé da frente, braço): resolve o buraco atrás do braço e os pés sobrepostos.
- Aceno: o BVH `wave_hello` do AnimatedDrawings é um gesto para a frente (cotovelo no plano lateral) e projeta mal no plano frontal; não há caminhada nos dados. Animação autoral com GSAP (antecipação, overshoot, curvas) + molas (cabeça, saia).
- Correções de textura: halos da arte removidos (cores #f8f5f0/#f5f3ee), alfa binário, cor de borda propagada.
- Pendências: virada ainda é achatamento; entalhes minúsculos em poucos pontos do contorno; sem balanço de cabelo/manto além da saia e da cabeça.

### Correção dos pés (v5)
- Cada path dos pés agora é atribuído ao pé de trás ou da frente por índice (a divisão por posição separava peças do mesmo pé).
- Camadas do perfil: pé de trás, pé da frente, corpo, braço (o manto fica por cima das pernas; pele da perna estendida para cima, escondida sob a barra).
- Passada menor (±120) e velocidade 100 px/s para os pés não saírem do manto.
- Malha: anéis internos de pontos junto à borda eliminam as fendas brancas (triângulos longos removidos em concavidades).

### v6: malha 3x + andar refeito no DragonBones
- Densidade ~3x (frente 9.064 vértices, costas 8.826; perfil em 6 camadas: perna/pé de trás, perna/pé da frente, corpo, braço).
- Andar: ciclo único (pé plantado, rolagem calcanhar->ponta, pélvis, braço), IK analítico de 2 ossos (coxa/canela/pé) em `poc2/page.js`; fase ligada à distância percorrida (o pé não desliza ao frear); canela com pesos em gradiente (canela->pé).
- Pé de trás reconstruído (a arte escondia o antepé atrás do pé da frente): cópia do pé da frente deslocada e mais escura.
- Teste paralelo (poc3/): Blender (bpy 5.2.3, Cycles CPU ~0,8 s/quadro) montou a mesma malha com armadura+IK e confirmou o ciclo; o Inox2D (Inochi2D) compilou para WASM (poc3/inox_wasm). Comparação interrompida a pedido; ficou como referência.

### v7: manto e pernas deformam juntos
- Problema da v6: o manto tinha peso fixo na pelve e as pernas eram camadas rígidas; ao andar, a perna se movia e o tecido do joelho ficava parado (corte visível).
- Agora o manto da malha do perfil tem pesos por difusão com restrições também nas cápsulas da coxa/canela (esquerda segue o pé da frente, direita o de trás), mas com influência parcial (25% acima do joelho -> 55% na barra, função `robe_follow` em `poc2/make_rigs.py`), para a barra se dobrar em vez de esticar entre os pés.
- Pele da perna sobe até y=1650 escondida atrás do manto, então a perna nunca aparece cortada.
- Limites conhecidos: pé de trás é cópia do da frente; soles retangulares; franja fina na barra; arte original não tem coxa/joelho (se o crédito do Replicate voltar, pedir ao Recraft uma folha só da parte de baixo com pernas e pés separados).

### v8: pés redesenhados
Os fragmentos de sandália do SVG do Recraft (peças separadas, antepé escondido atrás do outro pé) foram descartados; `poc2/foot_art.py` desenha a sandália de perfil em vetor (sola, pé, dedos, tiras) e a mesma peça serve aos dois pés (o de trás mais escuro). Verificado em escala 4x em 4 instantes do ciclo.
