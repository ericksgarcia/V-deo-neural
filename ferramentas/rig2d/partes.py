"""Divide a arte do personagem (RGBA) em camadas (peças) por polígonos, em coordenadas da imagem original.
Cada peça recebe também a parte escondida atrás das camadas da frente (inpaint), para poder se mover sem abrir buracos."""
import json, os, numpy as np, cv2
from PIL import Image

def P(*pts): return np.array(pts, np.int32)

# Ordem de desenho (de trás para frente)
EXT = {"tunica": 170, "cauda_faixa": 70, "braco_longe": 60}
# o preenchimento "por baixo" de cada peça só pode existir dentro destes polígonos (silhueta real do que fica atrás)
LIMITE = {
 "tunica": P((930,380),(1190,430),(1195,640),(1172,742),(1235,900),(1262,1100),(1290,1350),(1322,1600),(1340,1700),(700,1700),(700,380)),
}
ORDEM = ["braco_longe", "perna_tras", "perna_frente", "tunica", "cauda_faixa", "braco_perto", "faixa", "cinto", "cabeca"]

POLIGONOS = {
 "cabeca": P((780,0),(1200,0),(1200,340),(1165,376),(1105,376),(1060,368),(1010,425),(960,442),(905,408),(860,412),(835,406),(790,380)),
 "cinto": P((960,860),(1020,845),(1080,836),(1145,848),(1148,890),(1070,920),(1048,1000),(1045,1190),(1042,1258),(1000,1272),(978,1222),(968,920),(960,900)),
 "faixa": P((1050,372),(1120,366),(1190,393),(1228,442),(1170,458),(1118,500),(1080,580),(1020,690),(970,780),(970,858),(965,920),(925,1040),(880,1160),(850,1280),(830,1345),(812,1345),(805,1100),(806,830),(850,720),(900,600),(950,520),(1000,450)),
 "braco_perto": P((1070,505),(1175,425),(1235,470),(1280,590),(1355,765),(1408,985),(1405,1040),(1425,1060),(1425,1240),(1285,1240),(1285,1050),(1228,1052),(1210,880),(1135,742),(1090,640),(1075,545)),
 "cauda_faixa": P((1150,732),(1160,780),(1200,850),(1225,950),(1260,1060),(1320,1170),(1380,1300),(1330,1330),(1310,1380),(1260,1440),(1235,1425),(1230,1330),(1210,1260),(1150,1120),(1100,1000),(1062,915),(1148,880),(1150,800)),
 "braco_longe": P((700,400),(790,430),(820,470),(820,730),(808,800),(806,858),(668,1012),(380,1040),(380,420)),
 "perna_tras": P((470,1740),(760,1745),(850,1782),(885,1782),(885,1970),(470,1970)),
 "perna_frente": P((1100,1760),(1190,1740),(1260,1712),(1300,1700),(1345,1690),(1440,1690),(1440,1970),(1100,1970)),
}
FEATHER = {"braco_perto": ([(1075,545),(1090,640),(1135,742)], 36)}
LIMITE["cauda_faixa"] = POLIGONOS["cauda_faixa"]
LIMITE["braco_perto"] = POLIGONOS["braco_perto"]
LIMITE["braco_longe"] = POLIGONOS["braco_longe"]
PRIORIDADE = ["cabeca", "cinto", "faixa", "braco_perto", "cauda_faixa", "braco_longe", "perna_tras", "perna_frente"]  # o resto = tunica

def dono(rgba):
    h, w = rgba.shape[:2]
    own = np.full((h, w), -1, np.int8)
    names = PRIORIDADE + ["tunica"]
    for i, n in enumerate(PRIORIDADE):
        m = np.zeros((h, w), np.uint8); cv2.fillPoly(m, [POLIGONOS[n]], 1)
        own[(m > 0) & (own < 0)] = i
    own[own < 0] = len(PRIORIDADE)
    # pixels vermelhos que sobraram na túnica pertencem à faixa (ou à cauda): reatribui por componente conexa
    rgb = rgba[..., :3].astype(int)
    verm = (rgb[..., 0] > 100) & (rgb[..., 0] - rgb[..., 1] > 55) & (rgb[..., 0] - rgb[..., 2] > 45) & (rgba[..., 3] > 20)
    resto = verm & (own == len(PRIORIDADE))
    resto = cv2.dilate(resto.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    resto &= (own == len(PRIORIDADE)) & (rgba[..., 3] > 20)
    n, lab, st, cen = cv2.connectedComponentsWithStats(resto.astype(np.uint8), connectivity=8)
    for k in range(1, n):
        if st[k, 4] < 6: continue
        cx, cy = cen[k]
        alvo = "cauda_faixa" if (cx > 1040 and cy > 730) else "faixa"
        own[lab == k] = PRIORIDADE.index(alvo)
    return own, names

def classe_perna(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    pele_ou_couro = (hsv[..., 1] > 95) | (hsv[..., 2] < 120)
    return pele_ou_couro

def construir(arte_png, saida):
    os.makedirs(saida, exist_ok=True)
    rgba = np.array(Image.open(arte_png).convert("RGBA"))
    rgb, alfa = rgba[..., :3], rgba[..., 3]
    own, names = dono(rgba)
    h, w = alfa.shape
    base = alfa > 20
    masks = {}
    for i, n in enumerate(names):
        m = (own == i) & base
        if n.startswith("perna"):
            m &= classe_perna(rgb)
        masks[n] = m
    # pernas: remove manchas pequenas
    for n in ("perna_tras", "perna_frente"):
        k = cv2.connectedComponentsWithStats(masks[n].astype(np.uint8), connectivity=8)
        if k[0] > 1:
            keep = 1 + np.argmax(k[2][1:, 4]); masks[n] = k[1] == keep
    info = {}
    ordem_idx = {n: i for i, n in enumerate(ORDEM)}
    for n in ORDEM:
        vis = masks[n]
        # onde a camada fica escondida: pixels pertencentes a camadas desenhadas depois (na frente), dentro de uma faixa
        # em volta da peça -> serão preenchidos por inpaint para que a peça tenha "miolo" por baixo.
        frente = np.zeros((h, w), bool)
        for o in ORDEM:
            if ordem_idx[o] > ordem_idx[n]:
                frente |= masks[o]
        r_ext = EXT.get(n, 45)
        ext = cv2.dilate(vis.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*r_ext+1, 2*r_ext+1))) > 0
        escondido = frente & ext & ~vis & base
        if n in ("braco_longe", "braco_perto", "cauda_faixa", "faixa", "cinto", "cabeca"):
            # só estende quando a peça realmente está por baixo de outra (juntas); limita a faixa
            pass
        if n in LIMITE:
            lm = np.zeros((h, w), np.uint8); cv2.fillPoly(lm, [LIMITE[n]], 1)
            lm = cv2.dilate(lm, np.ones((13, 13), np.uint8))
            escondido &= lm > 0
        alvo = vis | escondido
        tex = rgb.copy()
        # inpaint: só os pixels VISÍVEIS da peça servem de fonte (o resto vira "buraco"), nunca o preto do fundo
        miolo = np.where(vis[..., None], rgb, 0).astype(np.uint8)
        if escondido.any():
            fonte = cv2.erode(vis.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            larga = cv2.dilate(vis.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*(r_ext+30)+1, 2*(r_ext+30)+1))) > 0
            buraco = (larga & ~fonte)
            y0, y1 = np.where(buraco.any(1))[0][[0, -1]]; x0, x1 = np.where(buraco.any(0))[0][[0, -1]]
            sub = miolo[y0:y1+1, x0:x1+1].copy(); bm = buraco[y0:y1+1, x0:x1+1].astype(np.uint8) * 255
            res = cv2.inpaint(sub, bm, 6, cv2.INPAINT_TELEA)
            esc = escondido[y0:y1+1, x0:x1+1]
            miolo[y0:y1+1, x0:x1+1] = np.where(esc[..., None], res, sub)
        a = (alfa.astype(np.float32) / 255.0)
        a_out = np.where(vis, a, 0.0)
        a_out = np.maximum(a_out, escondido.astype(np.float32))
        # suaviza borda do alfa onde encosta no que é de outra peça (mantém antialias original só na silhueta)
        if n in FEATHER:
            linha, larg = FEATHER[n]
            lm = np.full((h, w), 255, np.uint8); cv2.polylines(lm, [np.array(linha, np.int32)], False, 0, 2)
            dd = cv2.distanceTransform(lm, cv2.DIST_L2, 5)
            a_out = a_out * np.clip(dd / larg, 0, 1)
        out = np.dstack([miolo, (a_out * 255).astype(np.uint8)])
        if n.startswith("perna"):   # estende a canela para cima (fica escondida sob a barra da túnica)
            ys0 = np.where((out[..., 3] > 200).any(1))[0]; yt = ys0.min() + 10
            hsv = cv2.cvtColor(out[..., :3], cv2.COLOR_RGB2HSV)
            pele = (out[yt, :, 3] > 200) & (hsv[yt, :, 1] > 90) & (hsv[yt, :, 2] > 150)
            xs0 = np.where(pele)[0]
            if len(xs0):
                xa, xb = int(xs0.min()) + 5, int(xs0.max()) - 5
                for k in range(1, 161):
                    out[yt - k, :, :] = 0
                    out[yt - k, xa:xb] = out[yt, xa:xb]
            a_out = out[..., 3].astype(np.float32) / 255
        ys, xs = np.where(a_out > 0.02)
        if len(ys) == 0: continue
        box = (int(xs.min()) - 4, int(ys.min()) - 4, int(xs.max()) + 5, int(ys.max()) + 5)
        box = (max(0, box[0]), max(0, box[1]), min(w, box[2]), min(h, box[3]))
        Image.fromarray(out[box[1]:box[3], box[0]:box[2]]).save(f"{saida}/{n}.png")
        info[n] = {"bbox": box}
    json.dump({"ordem": ORDEM, "partes": info, "tam": [w, h]}, open(f"{saida}/partes.json", "w"), indent=1)
    return info

if __name__ == "__main__":
    import sys
    print(construir(sys.argv[1], sys.argv[2]))
