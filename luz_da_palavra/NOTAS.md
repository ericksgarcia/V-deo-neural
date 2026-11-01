# Teste Luz da Palavra — recraft-v4-svg (Replicate) → rig → animação

Pipeline: `gen.py` (Replicate) → `gen/partes.svg` → `build_rig.py` (fatia em peças) → `build_anim.py` (rig + ciclo de caminhada em HTML/SVG) → `frames.js` (Playwright) → ffmpeg → `saida/jesus_walk_teste.mp4`.

Aprendizados
- O modelo é só texto→SVG (inputs: prompt, size, aspect_ratio). Não aceita imagem de referência: "girar" o personagem a partir da imagem anterior NÃO é possível; identidade só por prompt.
- Funcionou muito bem pedir uma "rig sheet" de perfil DESMONTADA numa única geração (identidade consistente, peças separadas).
- Saída = pilha plana de <path> (sem grupos); contornos vêm fundidos/compostos, então é preciso fatiar por subpath + clip.
- Conta Replicate com < US$5 de crédito: 6 req/min, burst 1 (gen.py trata o 429).
