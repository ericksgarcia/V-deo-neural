# Luz da Palavra — teste de personagem SVG riggado (Replicate → rig → animação)

Resultado: `saida/jesus_v2.mp4` (20,8 s, 1280x720, fundo branco). Fonte interativa: `anim3.html` (`setT(t)`).

## Pipeline
1. `gen_pro.py` + `prompts_pro.py` → `recraft-ai/recraft-v4-styles-pro-svg` (folhas de peças em `gen2/pro_*.svg`).
2. `slice2.py` fatia a folha em peças por clusters de subpaths → `rig3/<folha>/pN.svgfrag`.
3. `build3.py` + `rig3.js` montam o rig (pivôs, hierarquia, ciclo de caminhada, viradas, braço, dedos) → `anim3.html`.
4. `frames.js` (Playwright) + ffmpeg → mp4.

## Aprendizados (recraft-v4-styles-pro-svg)
- `style_reference_images` é OBRIGATÓRIO (1-10 PNG/JPG/WEBP); `style_id` sozinho dá 422. A saída devolve `style_id`.
- Saída vem como data-URI SVG em `output.image`. Tamanhos até 2048² / 3072x1536.
- Referências com peças de corpo contaminam folhas diferentes (a folha de mãos veio com miniaturas de figura).
- Pedir "separado" em linhas funciona; o modelo troca vistas (pediu frente, veio costas) e raramente separa braço/antebraço.
- Conta Replicate < US$5: 6 req/min, burst 1.
- Mãos: dedos do modelo + palma desenhada em código; flexão por foreshortening (scaleY).
