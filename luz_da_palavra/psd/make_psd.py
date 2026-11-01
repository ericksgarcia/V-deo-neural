"""SVG de frente (T-pose) -> PSD em camadas nomeadas para o Character Animator.
Estrutura: Jesus > [Head, Body, Left Arm, Right Arm, Left Leg, Right Leg] (esquerda/direita = do PERSONAGEM; ele olha para o espectador)."""
import sys,re,subprocess,os
sys.path.insert(0,'poc2')
import numpy as np
from PIL import Image
import meshlib as M
from psd_tools import PSDImage
P=[p for p in M.load_paths('gen3/frente.svg') if p[0] not in ('#f8f5f0','#f5f3ee')]
def isred(h):
    r,g,b=int(h[1:3],16),int(h[3:5],16),int(h[5:7],16);return r>100 and g<70 and b<55 and r>g*2.2
# região de cada parte (px do SVG 2048); T-pose: tela-esquerda = mão DIREITA do personagem
def part(bb,col):
    x0,y0,x1,y1=bb
    if y1-y0>1500: return 'SIL'
    if y1<560 and x0>=700 and x1<=1320: return 'Head'
    if isred(col) and y1<1850 and x0>700 and x1<1400: return 'Body'
    if x1<880 and y0>430 and y1<950: return 'Right Arm'
    if x0>1150 and y0>430 and y1<950: return 'Left Arm'
    if y0>1850: return 'Left Leg' if (x0+x1)/2>1020 else 'Right Leg'
    if y0>1050: return 'Body'
    return 'Body'
def render(paths):
    body=''.join(f'<path fill="{c}" d="{d}"/>' for c,d in paths)
    open('psd/_t.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2048 2048" width="2048" height="2048">{body}</svg>')
    subprocess.run(['node','poc/svg2png_t.js',os.path.abspath('psd/_t.svg'),os.path.abspath('psd/_t.png'),'2048'],check=True)
    return Image.open('psd/_t.png').convert('RGBA')
full=render(P)
# retângulos (px do SVG 2048). Esquerda/Direita = do PERSONAGEM (de frente, ele está espelhado na tela)
R={'Head':(700,0,1320,545),'Right Arm':(0,430,800,960),'Left Arm':(1235,430,2048,960),'Right Leg':(0,1855,1020,2048),'Left Leg':(1020,1855,2048,2048)}
def crop(im,r):
    m=Image.new('L',im.size,0);ImageDraw.Draw(m).rectangle(r,fill=255);o=im.copy();o.putalpha(Image.fromarray(np.minimum(np.array(im.split()[-1]),np.array(m))));return o
from PIL import ImageDraw
imgs={k:crop(full,r) for k,r in R.items()}
hole=Image.new('L',full.size,255);d=ImageDraw.Draw(hole)
for k in ('Right Arm','Left Arm','Right Leg','Left Leg'): d.rectangle(R[k],fill=0)
bo=full.copy();bo.putalpha(Image.fromarray(np.minimum(np.array(full.split()[-1]),np.array(hole))));imgs['Body']=bo
psd=PSDImage.new('RGBA',(2048,2048))
root=psd.create_group(name='Jesus')
order=['Body','Right Leg','Left Leg','Right Arm','Left Arm','Head']           # de baixo para cima
for k in order:
    g=root.create_group(name=k)
    g.append(g.create_pixel_layer(imgs[k],name=k+' Art'))
psd.save('psd/jesus_charanimator.psd')
comp=Image.new('RGBA',(2048,2048),(255,255,255,255))
for k in order: comp=Image.alpha_composite(comp,imgs[k])
comp.convert('RGB').resize((1024,1024)).save('psd/_preview.png')
for k in order: print(k,imgs[k].split()[-1].getbbox())
