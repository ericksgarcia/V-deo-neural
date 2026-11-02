# Luz da Palavra

Canal de TikTok de vídeos verticais (1080x1920) que revelam um detalhe escondido da Bíblia: fundo de fotografia
ultra realista (Replicate, flux-schnell), narração no Gemini TTS (voz Achird) e ganchos fortes a cada ~5 s.

Tudo está em [`luz_da_palavra/`](luz_da_palavra/README.md). Vídeos prontos em `saida/luz/`.

```bash
pip install -r requirements.txt            # além do ffmpeg no sistema
python luz_da_palavra/temas.py             # temas já feitos e quando liberam de novo (2 meses)
python luz_da_palavra/conferir.py luz_da_palavra/roteiros/ep02_lazaro.json   # confere os ganchos
python luz_da_palavra/gerar.py luz_da_palavra/roteiros/ep02_lazaro.json      # gera o vídeo
```

O canal de simulações de IA que existia aqui foi removido em 02/nov/2026; continua no histórico do git
(commit `b0cdd99`, `git checkout b0cdd99 -- <caminho>` recupera qualquer arquivo).
