import sys,json
sys.path.insert(0,'poc2')
import numpy as np
from PIL import Image
import meshlib as M
OUT='poc4/out';st={}
# ---------------- frente / costas (T-pose) ----------------
def tpose(sy,ey,wy,wyR,cx=1012):
    f1=((2*572+339)//3);f2=((572+2*339)//3)
    B=[('root',None,0,0),('pelvis','root',cx,1040),('skirt','pelvis',cx,1100),('chest','pelvis',cx,780),('neck','chest',cx,466),('head','neck',cx,466),
     ('shoL','chest',806,sy),('elbL','shoL',572,ey),('fore1L','elbL',f1,(2*ey+wy)//3),('fore2L','fore1L',f2,(ey+2*wy)//3),('handL','fore2L',339,wy),
     ('shoR','chest',1219,sy),('elbR','shoR',1463,ey),('wrR','elbR',1696,wyR)]
    C=[('root',(cx,1160),(cx,1760),240),('skirt',(cx,1700),(cx,1830),250),('pelvis',(cx,1100),(cx,800),110),('chest',(cx,800),(cx,540),120),('neck',(cx,540),(cx,440),50),('head',(cx,440),(cx,110),215),
     ('shoL',(770,sy),(572,ey),68),('elbL',(572,ey),(f1,(2*ey+wy)//3),75),('fore1L',(f1,(2*ey+wy)//3),(f2,(ey+2*wy)//3),80),('fore2L',(f2,(ey+2*wy)//3),(339,wy),80),('handL',(339,wy),(60,wy),55),
     ('shoR',(1262,sy),(1463,ey),68),('elbR',(1463,ey),(1696,wyR),75),('wrR',(1696,wyR),(1990,wyR),55)]
    dense=[(806,sy,170),(572,ey,170),(339,wy,230),(160,wy,200),(1219,sy,150),(1463,ey,150),(1696,wyR,200),(1880,wyR,200),(cx,470,150)]
    return B,C,dense
for view,png,args in [('front','base/front.png',(509,540,594,594)),('back','base/back.png',(509,540,594,594))]:
    B,C,dense=tpose(*args)
    st[view]=M.build_view_png('jesus_'+view,B,[{'name':'body','png':png,'caps':C,'dense':dense}],OUT)
# ---------------- perfil (olha para a DIREITA) ----------------
im=Image.open('base/side.png').convert('RGBA')
PB=[('root',None,0,0),('pelvis','root',1155,1060),('skirt','pelvis',1155,1100),('chest','pelvis',1160,800),('neck','chest',1102,424),('head','neck',1102,430),
 ('sho','chest',1040,565),('elb','sho',933,588),('fore1','elb',890,598),('hand','fore1',848,604),
 ('thighF','pelvis',1140,1100),('shinF','thighF',1135,1500),('footF','shinF',1071,1919),('thighB','pelvis',1140,1100),('shinB','thighB',1135,1500),('footB','shinB',1071,1919)]
# perna+pé: recorte da imagem (y>=1830) + tubo de pele escondido atrás da barra
a=np.array(im)
sk=a[1860:1870,1040:1060,:3].reshape(-1,3).mean(0).astype(int)
leg=Image.new('RGBA',(2048,2048),(0,0,0,0));crop=im.crop((900,1830,1380,2048));leg.alpha_composite(crop,(900,1830))
tube=Image.new('RGBA',(2048,2048),(0,0,0,0))
from PIL import ImageDraw
ImageDraw.Draw(tube).rectangle((1030,1700,1130,1850),fill=tuple(sk)+(255,))
leg=Image.alpha_composite(tube,leg);leg.save('poc4/out/_legF.png')
legB=leg.copy();px=np.array(legB).astype(float);px[...,:3]*=0.86;legB=Image.fromarray(px.astype(np.uint8));legB.save('poc4/out/_legB.png')
# braço = manga + mão (sem o manto vermelho); corpo = resto, com o ombro preenchido na cor da manga
ba=np.array(im);R,G,Bc=ba[...,0].astype(int),ba[...,1].astype(int),ba[...,2].astype(int)
red=(R>95)&(G<75)&(Bc<65)&(R>G*2.0)
yy,xx=np.mgrid[0:2048,0:2048]
armmask=(ba[...,3]>0)&(~red)&(xx>=640)&(xx<=1190)&(yy>=470)&(yy<=790)&~((xx>950)&(yy>770))
armmask&=~((xx<1000)&(yy<475))
armmask&=(xx<1040)
arm=ba.copy();arm[~armmask,3]=0;Image.fromarray(arm).save('poc4/out/_arm.png')
cream=ba[560:600,1100:1140,:3].reshape(-1,3).mean(0).astype(np.uint8)
bd=ba.copy();bd[1830:,:,3]=0
bd[armmask,3]=0
Image.fromarray(bd).save('poc4/out/_body.png')
PC=[('pelvis',(1160,1100),(1160,800),120),('chest',(1160,800),(1150,560),130),('neck',(1102,500),(1102,430),50),('head',(1102,430),(1100,110),150),
 ('root',(1160,1250),(1140,1700),170),('skirt',(1150,1700),(1130,1830),170),
 ('thighF',(1140,1100),(1135,1500),50),('shinF',(1135,1500),(1130,1760),50),('thighB',(1140,1100),(1135,1500),50),('shinB',(1135,1500),(1130,1760),50),
 ]
AC=[('sho',(1040,565),(933,588),95),('elb',(933,588),(890,598),95),('fore1',(890,598),(848,604),95),('hand',(848,604),(660,552),58)]
import numpy as np
def robe_follow(V,Wt,names):
    ix=[names.index(n) for n in ['thighF','shinF','thighB','shinB']];pel=names.index('pelvis')
    f=0.25+0.30*np.clip((V[:,1]-1500)/330.0,0,1)
    for j in ix:
        mv=Wt[:,j]*(1-f);Wt[:,j]-=mv;Wt[:,pel]+=mv
    return Wt
st['side']=M.build_view_png('jesus_side',PB,[
 {'name':'legB','png':'poc4/out/_legB.png','grad':('shinB','footB',1850,1930)},
 {'name':'legF','png':'poc4/out/_legF.png','grad':('shinF','footF',1850,1930)},
 {'name':'body','png':'poc4/out/_body.png','caps':PC,'post':robe_follow},
 {'name':'arm','png':'poc4/out/_arm.png','caps':AC,'dense':[(1040,565,150),(933,588,170),(800,590,200)]}],OUT)
print(json.dumps(st))
