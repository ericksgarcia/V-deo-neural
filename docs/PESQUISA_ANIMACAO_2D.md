# Pesquisa: o que copiar dos programas profissionais de animação 2D (nov/2026)

Objetivo: animar o personagem (imagens 1-5: costas, 3/4 andando, lado, costas T, lado T) de forma fluida e **sem quebrar o desenho**,
com uma ação diferente a cada vídeo. Base já existente: `ferramentas/rig2d/` (ver `PERSONAGEM_RIG.md`).

## 1. Repositórios abertos que valem estudo (e licença)

| Projeto | O que tem de melhor | Licença | Uso para nós |
|---|---|---|---|
| [Inochi2D](https://github.com/Inochi2D/inochi2d) / [Inox2D (Rust)](https://github.com/Inochi2D/inox2d) | Estilo Live2D aberto: malhas deformadas por **parâmetros** (eixos tipo "olhar X/Y", "virar cabeça"), z-sort, física | BSD-2 | Melhor modelo para **virar de vista** e expressões; ler como referência de formato |
| [Rive runtimes](https://rive.app/docs/runtimes) | **State machine** (transições entre ações), bones, constraints, bind de malha com pesos | MIT (runtimes) | Copiar a ideia de máquina de estados e mistura (blend) de ações |
| [Spine runtimes](https://raw.github.com/EsotericSoftware/spine-runtimes/master/LICENSE) | Referência de **IK, transform constraint, path constraint, physics, skins, malha FFD** | Licença própria: exige licença do editor Spine | **Só ler a documentação/algoritmos**; não copiar código |
| [Meta AnimatedDrawings](https://github.com/facebookresearch/AnimatedDrawings) | **Retarget de mocap BVH (3D) para rig 2D** por orientação de juntas (FK) | conferir `LICENSE` no repo | Biblioteca infinita de ações (andar, pular, acenar, sentar) sem animar à mão |
| [Creature (kestrelm)](https://github.com/kestrelm/Creature_UE4) | Deformação de malha + IK em runtime | Apache-2.0 (runtime) | Referência de malha/IK |
| [OpenToonz](https://github.com/orieg/opentoonz) | Pipeline de produção (Ghibli); mais quadro-a-quadro que rig | BSD modificada | Pouco útil para rig; ideia de FX e composição |
| Pencil2D, Synfig | Quadro-a-quadro / vetorial | GPL | Só inspiração (GPL contamina código) |
| DragonBones, SkelForm, Boner2D | Rig 2D com malha + IK | conferir cada repo | Segundo plano |

## 2. Sobre "engenharia reversa"

- **Toon Boom Harmony e Spine (editor) são proprietários.** Não encontrei repositório sério de engenharia reversa de nenhum dos dois, e copiar
  código/formato deles traz risco jurídico (EULA). Recomendo **replicar as técnicas** (que são públicas na literatura), não o código.
- Moho: o `.moho` é um zip com JSON (`.mohoproj`), segundo [fórum Lost Marble](https://lostmarble.com/forum/viewtopic.php?p=210190) e o
  [moho-template](https://github.com/definitelyokay/moho-template). Dá para inspecionar, mas **não há especificação oficial** e não precisamos disso.
- Não fiz download nem execução de nada de terceiros nesta rodada: é pesquisa de fontes.

## 3. Funções que mais importam (por programa) e situação no nosso rig

| Função | De onde vem | Dá o quê | Nosso estado |
|---|---|---|---|
| Malha + pesos automáticos | Spine, Moho, Live2D | Dobra suave sem quebrar o traço | FEITO (`motor.py`) |
| IK 2 ossos, pés plantados | Spine, Moho | Caminhada sem "patinar" | FEITO (`ik2`) |
| Física secundária (faixa, cabelo, barra) | Spine physics, Live2D | Naturalidade, "sobrar" movimento | FEITO (`Cadeia`) |
| **Smart bones / parâmetros** (eixo 0-1 que aciona várias deformações) | Moho smart bones, Live2D, Inochi2D | Virar cabeça, expressões, mãos com um só controle | FALTA |
| **Curvas de easing por canal** (Bézier) + overlap/follow-through | Harmony, Spine, Moho | Os 12 princípios: antecipação, arco, sobra | FALTA (maior ganho de fluidez) |
| **Máquina de estados + blend** (andar → parar → apontar) | Rive, Spine mix | Transição suave entre ações | FALTA |
| **Troca de desenho (swap)** para mãos/boca/olhos | Moho switch layers, Harmony drawing substitution | Mãos e visemas em estilo do desenho | FALTA (precisa arte) |
| **Rig por vista + troca escondida** | Live2D ângulos | Frente/costas/lado sem 3D | FALTA (imagens 1,3,4,5 já em mãos) |
| **Retarget de mocap BVH → ossos 2D** | AnimatedDrawings | Biblioteca enorme de ações grátis | FALTA (maior ganho de variedade) |
| Respiração/idle procedural (ruído suave) | Harmony/Moho cycles | Personagem "vivo" parado | PARCIAL |
| Clipping / camadas de oclusão (mão na frente do corpo) | Spine clipping, Harmony | Braço cruzando o corpo sem remendo | Limitado por inpaint |

## 4. Plano proposto (ordem de retorno)

1. **Sistema de animação por curvas** (keyframes com easing Bézier, antecipação e follow-through automáticos) em cima do `motor.py`.
2. **Máquina de estados** com mistura entre ações (andar, parar, apontar, gesticular, rezar, sentar).
3. **Rigs das demais vistas** (1, 3, 4, 5) com os mesmos nomes de osso + troca de vista escondida por movimento/corte.
4. **Retarget BVH → esqueleto 2D** (mocap livre, ex.: CMU) para gerar ações novas a cada vídeo; ajustar manualmente poses ruins.
5. **Folha de rosto e mãos** (peças trocáveis) — depende de o dono gerar essas artes na mesma linha do desenho.

## 5. Riscos honestos

- Uma imagem única por vista implica **partes ocultas inventadas por inpaint**: poses extremas (braço cruzando o corpo, sentar) mostram remendo.
  O que mais eleva a qualidade é **arte desmontada em peças com as áreas escondidas desenhadas** (pode ser gerada por IA de imagem, em camadas).
- Retarget de mocap 3D→2D em vista lateral/3/4 só funciona bem com movimentos no plano; braços em profundidade ficam achatados.
- Verificar a licença de cada repositório (`LICENSE`) antes de reutilizar código; as buscas acima não confirmaram todas.
