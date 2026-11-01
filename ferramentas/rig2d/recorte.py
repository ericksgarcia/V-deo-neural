"""Remove fundo (branco + sombra) de uma arte de personagem e devolve RGBA com alfa suave."""
import numpy as np, cv2

def remover_fundo(rgb, tol=16):
    h, w = rgb.shape[:2]
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    # 1) preenche o fundo a partir das bordas (o contorno escuro do desenho fecha a silhueta)
    hsv0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sombra = (hsv0[..., 1] < 45) & (hsv0[..., 2] > 150) & (np.arange(h)[:, None] > h * 0.85)
    mask = np.zeros((h + 2, w + 2), np.uint8)
    flood = bgr.copy()
    flood[sombra] = (255, 255, 255)
    for seed in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        cv2.floodFill(flood, mask, seed, (0, 0, 0), (tol,) * 3, (tol,) * 3, 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
    fundo = mask[1:-1, 1:-1] > 0
    # 2) sombra do chão: cinza-lilás pouco saturado, perto da base
    fundo |= sombra
    alfa = (~fundo).astype(np.uint8) * 255
    alfa = cv2.morphologyEx(alfa, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # mantém só o maior componente (personagem)
    n, lab, st, _ = cv2.connectedComponentsWithStats(alfa, connectivity=8)
    alfa = np.where(lab == 1 + np.argmax(st[1:, 4]), 255, 0).astype(np.uint8)
    # buracos internos que são fundo (entre braço e corpo) ficam transparentes via passo 1; borda suave:
    alfa = cv2.GaussianBlur(alfa, (0, 0), 0.8)
    # defringe: pixels de borda recebem a cor do miolo mais próximo (sem halo branco)
    core = cv2.erode((alfa >= 250).astype(np.uint8), np.ones((3, 3), np.uint8))
    dist, lab = cv2.distanceTransformWithLabels((core == 0).astype(np.uint8), cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.where(core > 0)
    tabela = np.zeros((lab.max() + 1, 3), np.uint8)
    tabela[lab[ys, xs]] = rgb[ys, xs]
    rgb2 = np.where((core == 0)[..., None] & (alfa > 0)[..., None], tabela[lab], rgb)
    return np.dstack([rgb2, alfa])
