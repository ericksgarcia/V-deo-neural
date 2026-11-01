import sys, os, time, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import heroi
from motor import Camera
saida = sys.argv[1]
t0 = time.time(); ch = heroi.construir(); print("construir %.1fs" % (time.time() - t0), {n: (len(p.V), len(p.tris)) for n, p in ch.pecas.items()})
W, H = 1080, 1920
cam = Camera(0.8, -180, 130, ss=1)
def frame(c, fundo=(150, 130, 110)):
    img = np.full((H, W, 3), fundo, np.float32)
    a = c[..., 3:4]; img = c[..., :3] * 255 + img * (1 - a)
    return img.astype(np.uint8)
# repouso (sem pose)
ch.esq.zerar(); ch.params.clear(); ch.esq.fk()
t0 = time.time(); r = frame(ch.render(cam, W, H)); print("render %.2fs" % (time.time() - t0))
orig = cv2.imread("personagem/arte_caminhando.png", cv2.IMREAD_UNCHANGED)
cv2.imwrite(saida + "/repouso.png", r)
# folha de 8 fases
cel = []
for k in range(8):
    t = k / 8.0
    for _ in range(30): heroi.pose(ch, t + 5.0, 2*3.14159265*(t+5.0), 1.0)   # aquece a física
    heroi.pose(ch, t, 2*3.14159265*t, 1.0)
    f = frame(ch.render(cam, W, H))[100:1700, 120:1000]
    cel.append(cv2.resize(f, (440, 800)))
folha = np.vstack([np.hstack(cel[:4]), np.hstack(cel[4:])])
cv2.imwrite(saida + "/folha_andar.png", folha)
