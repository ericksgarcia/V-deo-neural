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
