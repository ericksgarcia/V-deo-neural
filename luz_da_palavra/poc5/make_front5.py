import sys,json
sys.path.insert(0,'poc2')
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage
import meshlib as M
OUT='poc5/out'
im=Image.open('base/front.png').convert('RGBA');a=np.array(im);R,G,B=[a[...,i].astype(int) for i in range(3)]
op=a[...,3]>0;red=(R>95)&(G<80)&(B<70)&(R>G*1.9)
yy,xx=np.mgrid[0:2048,0:2048]
armL=op&(xx<830)&(yy>430)&(yy<965)&~red                # braço esquerdo da tela = mão DIREITA do personagem
armR=op&(xx>1195)&(yy>430)&(yy<965)&~red
def biggest(m):
    l,k=ndimage.label(m);sz=ndimage.sum(m,l,range(1,k+1));return l==(1+int(np.argmax(sz)))
armL=biggest(armL);armR=biggest(armR)
bd=a.copy();rem=armL|armR
keep=(((xx-806)**2+(yy-509)**2)<90**2)|(((xx-1219)**2+(yy-514)**2)<90**2)      # ombro duplicado no corpo (sem frestas)
bd[rem&~keep,3]=0
Image.fromarray(bd).save(f'{OUT}/_fbody.png')
for n,m in (('armL',armL),('armR',armR)):
    o=a.copy();o[~m,3]=0;Image.fromarray(o).save(f'{OUT}/_f{n}.png')
cx=1012
PB=[('root',None,0,0),('pelvis','root',cx,1040),('skirt','pelvis',cx,1100),('chest','pelvis',cx,780),('neck','chest',cx,466),('head','neck',cx,466),
 ('shoL','chest',806,509),('elbL','shoL',572,540),('handL','elbL',339,594),
 ('shoR','chest',1219,514),('elbR','shoR',1463,546),('handR','elbR',1696,594)]
BC=[('root',(cx,1160),(cx,1760),240),('skirt',(cx,1700),(cx,1830),250),('pelvis',(cx,1100),(cx,800),110),('chest',(cx,800),(cx,540),120),('neck',(cx,540),(cx,440),50),('head',(cx,440),(cx,110),215),
 ('shoL',(806,509),(830,520),30),('shoR',(1219,514),(1195,520),30)]
AL=[('shoL',(830,509),(572,540),80),('elbL',(572,540),(339,594),82),('handL',(339,594),(60,600),58)]
AR=[('shoR',(1195,514),(1463,546),80),('elbR',(1463,546),(1696,594),82),('handR',(1696,594),(1990,600),58)]
st=M.build_view_png('jesus_front',PB,[
 {'name':'body','png':f'{OUT}/_fbody.png','caps':BC,'h_base':30,'h_fine':13,'dense':[(cx,470,150),(806,509,110),(1219,514,110)]},
 {'name':'armL','png':f'{OUT}/_farmL.png','caps':AL,'dense':[(806,509,130),(572,540,170),(339,594,220),(160,600,200)]},
 {'name':'armR','png':f'{OUT}/_farmR.png','caps':AR,'dense':[(1219,514,130),(1463,546,170),(1696,594,220),(1880,600,200)]}],OUT)
print(json.dumps(st))
