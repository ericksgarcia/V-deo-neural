# Personagem 2D com rig de malhas (`ferramentas/rig2d/`)

Objetivo: um personagem desenhado (arte do dono do canal) que faz **qualquer animação** sem perder o traço original.
Técnica escolhida: **boneco 2D por malhas com skinning** (a mesma ideia do Spine, Live2D e Moho), em Python
(numpy + OpenCV + scipy), para rodar direto no mesmo pipeline dos vídeos. Nada de 3D: o desenho original é o que aparece.

## Como funciona (equivalente ao que os programas profissionais fazem)

| Recurso | Programa de referência | Aqui |
|---|---|---|
| Peças em camadas com partes escondidas completadas | Live2D / Spine | `partes.py` (polígonos + inpaint só com pixels da própria peça) |
| Malha triangular por peça (contorno + pontos internos + anéis de refino nas juntas) | Spine "mesh" | `motor.gerar_malha` |
| Pesos de skinning automáticos por difusão de calor (suave nas juntas, até 4 ossos por vértice) | Blender "automatic weights" / Spine "auto-weights" | `motor.pesos_calor` |
| Esqueleto hierárquico (FK) + IK de 2 ossos (pés plantados no chão) | Spine / Moho | `motor.Esqueleto`, `ik2` |
| Física secundária (faixa, cinto, cabelo) com mola de volta à pose | Spine "physics constraint" / Live2D physics | `motor.Cadeia` (verlet) |
| Deformador livre (barra da túnica balançando, respiração) | Live2D "warp deformer" | função por peça (`heroi.onda_barra`) |
| Olhos (piscar) e boca (visemas) presos à cabeça | Live2D parâmetros / Toon Boom | `heroi._rosto` (vetor procedural) |
| Renderização com supersampling | — | `motor.Personagem.render` (`--ss 2`) |

## Arquivos

- `recorte.py` remove o fundo e faz *defringe* (sem halo branco na borda).
- `partes.py` divide a arte em peças (`personagem/caminhando/*.png` + `partes.json`) e completa o que fica escondido.
  Os polígonos (`POLIGONOS`) e a ordem de desenho (`ORDEM`) ficam no topo do arquivo.
- `motor.py` é o motor genérico (serve para qualquer personagem/vista).
- `heroi.py` define o esqueleto, os pesos, a física e a animação deste personagem (vista 3/4 caminhando).
- `demo.py` renderiza o vídeo de teste (anda, para, gesticula e fala). `--audio fala.wav` faz a boca seguir a voz real.
- `teste_folha.py` gera a folha com 8 fases da caminhada para conferir a pose.

## Rodar

```bash
pip install opencv-python-headless scipy
python ferramentas/rig2d/recorte.py            # (função) usada para gerar personagem/arte_caminhando.png
python ferramentas/rig2d/partes.py personagem/arte_caminhando.png personagem/caminhando
python ferramentas/rig2d/demo.py saida/rig_demo/teste.mp4 --seg 9 --ss 2
```

## Estado e limites (honesto)

- **Feito:** vista 3/4 andando (imagem de referência 6): 9 peças, 24 ossos, 5 cadeias de física, piscar e boca.
- **Limite da arte:** quem está *atrás* de outra peça (o miolo da túnica sob o braço, a canela sob a barra) é **preenchido por inpaint**,
  não desenhado. Movimentos pequenos/médios ficam limpos; um braço que cruza o corpo todo pode mostrar remendo.
  Para qualidade de produção, o ideal é ter a mesma arte **já desmontada em peças com as partes escondidas desenhadas**.
- **Uma vista = um rig.** Para virar de frente/costas/lado, cada vista (imagens 1–5) vira um rig com os mesmos nomes de osso e
  trocamos de vista com corte escondido por movimento (técnica do Live2D com "ângulos").
- **Rosto:** hoje só piscar e boca procedural (simples, no estilo do desenho). Para expressões de verdade
  (sobrancelhas, olhar, sorriso, boca com 8 visemas) precisamos de uma folha de rosto na mesma arte.

## Próximos passos sugeridos

1. Folha de **rosto** (olhos abertos/fechados/olhando para os lados, sobrancelhas, 8 bocas) e **mãos** (aberta, apontando, palma para cima).
2. Rigs das vistas **frente (imagem 4)**, **costas 3/4 (imagem 5)** e **lado (imagens 1 e 3)** com o mesmo esqueleto.
3. Biblioteca de animações (andar, parar, apontar, rezar, sentar) e uma função `cena(personagem, roteiro)` que liga o personagem ao roteiro/voz.


## Camada de animação v2 (nov/2026): o melhor de cada referência

Arquivos novos em `ferramentas/rig2d/`: `animacao.py` (genérico), `acoes.py` (ações do herói), `bvh.py` (mocap), `gerar_bvh.py` (+ `mocap/*.bvh`),
`demo2.py`, `teste_acoes.py`. Tudo reimplementado do zero (sem copiar código de terceiros; ver `docs/PESQUISA_ANIMACAO_2D.md`).

| Ideia | Origem | Onde |
|---|---|---|
| Parâmetros 1D/2D aditivos (`virar`, `inclinar`, `olhar_x/olhar_y`, `respirar_fundo`); `virar` também deforma a malha do rosto | Inochi2D / Live2D | `animacao.Parametro`, `acoes.PARAMETROS`, `heroi.virar_cabeca` |
| Máquina de estados com **camadas** (base = corpo todo, cima = braços/cabeça com máscara), transições com mistura e easing, regras automáticas | Rive, Spine tracks | `animacao.Maquina/Camada` |
| Curvas Bézier por segmento, antecipação e sobra (overshoot), "vida parada" (ruído) | Harmony / Spine / Moho | `animacao.Facil`, `ClipeChaves`, `com_antecipacao` |
| Follow-through (mola de 2ª ordem em cabeça, antebraços e mãos) | overlap do Harmony | `animacao.Seguidor` |
| Mocap BVH -> ossos 2D (orientação dos segmentos + IK dos pés com chão fixo, suavização) | Meta AnimatedDrawings | `bvh.ClipeBVH` |
| Rosto: viraria de olhar por parâmetro; bocas/expressões desenhadas ficam para a folha de rosto (abaixo) | Mesh Avatar Studio | pendente (arte) |

Usar: `m = acoes.criar_maquina(); m.entradas["vel"]=1; m.ir("cima","acenar"); pose=m.passo(1/30); heroi.aplicar(ch, pose)`.
Para variar a cada vídeo basta um roteiro de eventos (ver `demo2.ROTEIRO`) e/ou novos BVHs em `mocap/` (mesmos nomes de junta,
ou um `MAPA` próprio em `bvh.py`). Rode `python ferramentas/rig2d/gerar_bvh.py` para recriar a biblioteca procedural.

### Limites conhecidos (honesto)
- Continua **uma vista** (3/4 andando). Frente/costas/lado exigem o mesmo recorte de peças (`partes.py`) para as imagens 1, 3, 4 e 5.
- Mocap em vista lateral achata o que vai para a câmera; segmentos quase de frente seguram o ângulo anterior.
- Braço levantado acima de ~2,5 rad ou tronco muito inclinado mostram o remendo do inpaint; mantenha as ações dentro do que o desenho aguenta.
- Os BVHs de `mocap/` são procedurais (simples). Para movimento realista use mocap real (CMU, Mixamo-BVH); verifique a licença de cada um.
