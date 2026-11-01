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
