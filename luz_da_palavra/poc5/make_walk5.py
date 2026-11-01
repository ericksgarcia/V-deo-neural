import sys,json
sys.path.insert(0,'poc2')
import numpy as np
from PIL import Image,ImageDraw
import meshlib as M
OUT='poc5/out';K=1.06
im=Image.open('base/walk.png').convert('RGBA');a=np.array(im);R,G,B=a[...,0].astype(int),a[...,1].astype(int),a[...,2].astype(int)
def poly(pts):
    m=Image.new('L',(2048,2048),0);ImageDraw.Draw(m).polygon([(x*K,y*K) for x,y in pts],fill=255);return np.array(m)>0
def box(x0,y0,x1,y1):
    m=np.zeros((2048,2048),bool);m[int(y0*K):int(y1*K),int(x0*K):int(x1*K)]=True;return m
op=a[...,3]>0
red=(R>95)&(G<80)&(B<70)&(R>G*1.9)
cream=(R>225)&(G>210)&(B>188)&~red
# ---- braço da frente (para a direita) e de trás
armN=poly([(930,520),(1060,640),(1090,655),(1290,800),(1425,832),(1475,905),(1440,950),(1330,925),(1265,880),(1180,968),(1000,860),(900,780),(870,640)])&op
armK=poly([(755,530),(700,640),(655,705),(565,875),(580,905),(572,925),(540,985),(505,1050),(520,1090),(550,1085),(600,1060),(608,1040),(630,955),(715,948),(765,720),(755,560)])&op
from scipy import ndimage
cl,ck=ndimage.label(cream&op);csz=ndimage.sum(cream&op,cl,range(1,ck+1))
bigcream=np.isin(cl,[i+1 for i,v in enumerate(csz) if v>6000])          # túnica/barra (grandes); realces pequenos dos dedos ficam
bigcream=ndimage.binary_dilation(bigcream,iterations=3)
legMask=lambda b:b&op&~bigcream&~red
def biggest(m):
    l,k=ndimage.label(m)
    if k<2: return m
    sz=ndimage.sum(m,l,range(1,k+1));return l==(1+int(np.argmax(sz)))
def closeholes(m):
    return ndimage.binary_closing(m,iterations=3)|m
def clean(m):
    m=biggest(ndimage.binary_closing(m,iterations=4)|m)
    return ndimage.binary_fill_holes(m)&op
legB=clean(legMask(box(450,1690,735,1910)));legF=clean(legMask(box(1060,1712,1385,1910)))
def layer(mask,name,tone=1.0,extra=None):
    o=a.copy();o[~mask,3]=0
    if tone!=1.0:o[...,:3]=(o[...,:3]*tone).astype(np.uint8)
    img=Image.fromarray(o)
    if extra: img=Image.alpha_composite(extra,img)
    img.save(f'{OUT}/_{name}.png')
def tube(mask,ytop):
    ys,xs=np.where(mask);y0=ys.min();sel=(ys>=y0+4)&(ys<y0+30)
    col=tuple(int(v) for v in a[ys[sel],xs[sel],:3].mean(0))+(255,)
    x0,x1=int(np.percentile(xs[sel],10)),int(np.percentile(xs[sel],90))
    t=Image.new('RGBA',(2048,2048),(0,0,0,0));ImageDraw.Draw(t).rectangle((x0,ytop,x1,y0+8),fill=col);return t
layer(legB,'legB',0.86,tube(legB,1620));layer(legF,'legF',1.0,tube(legF,1700))
layer(armK,'armK');layer(armN,'armN')
# corpo: remove braços/pernas; o ombro e o tronco sob a manga da frente são preenchidos em creme
bd=a.copy();rem=armN|armK|legB|legF;cr=np.array([246,230,200],np.uint8)
fill=armN&poly([(760,520),(1010,520),(1010,830),(760,830)])&~red
keepK=armK&(((np.mgrid[0:2048,0:2048][1]-round(800*K))**2+(np.mgrid[0:2048,0:2048][0]-round(600*K))**2)<(110**2))   # ombro de trás duplicado no corpo (sem frestas)
bd[rem&~keepK,3]=0;bd[fill,:3]=cr;bd[fill,3]=255
Image.fromarray(bd).save(f'{OUT}/_body.png')
S=lambda x,y:(round(x*K),round(y*K))
PB=[('root',None,0,0),('pelvis','root',*S(880,950)),('skirt','pelvis',*S(880,990)),('chest','pelvis',*S(900,760)),('neck','chest',*S(950,430)),('head','neck',*S(950,430)),
 ('shoN','chest',*S(900,600)),('elbN','shoN',*S(1090,735)),('handN','elbN',*S(1270,865)),
 ('shoK','chest',*S(800,600)),('elbK','shoK',*S(680,760)),('handK','elbK',*S(630,940)),
 ('thighF','pelvis',950,1000),('shinF','thighF',1085,1500),('footF','shinF',1187,1908),('thighB','pelvis',950,1000),('shinB','thighB',760,1500),('footB','shinB',594,1897)]
Ar=lambda *p:[(round(x*K),round(y*K)) for x,y in p]
PC=[('pelvis',S(880,990),S(900,760),130),('chest',S(900,760),S(940,520),140),('neck',S(950,500),S(950,430),55),('head',S(950,430),S(900,60),170),
 ('root',(930,1180),(930,1550),200),('skirt',(900,1500),(900,1790),260),
 ('thighF',(950,1000),(1085,1500),55),('shinF',(1085,1500),(1170,1760),55),('thighB',(950,1000),(760,1500),55),('shinB',(760,1500),(640,1760),55)]
AN=[('shoN',S(900,600),S(1090,735),95),('elbN',S(1090,735),S(1270,865),85),('handN',S(1270,865),S(1470,930),60)]
AK=[('shoK',S(800,600),S(680,760),95),('elbK',S(680,760),S(630,940),85),('handK',S(630,940),S(520,1080),65)]
def robe_follow(V,Wt,names):
    ix=[names.index(n) for n in ['thighF','shinF','thighB','shinB']];pel=names.index('pelvis')
    f=0.08+0.14*np.clip((V[:,1]-1500)/330.0,0,1)
    for j in ix:
        mv=Wt[:,j]*(1-f);Wt[:,j]-=mv;Wt[:,pel]+=mv
    return Wt
st=M.build_view_png('jesus_walk',PB,[
 {'name':'legB','png':f'{OUT}/_legB.png','grad':('shinB','footB',1780,1880)},
 {'name':'legF','png':f'{OUT}/_legF.png','grad':('shinF','footF',1790,1890)},
 {'name':'armK','png':f'{OUT}/_armK.png','caps':AK,'dense':[(S(800,600)[0],S(800,600)[1],150),(S(680,760)[0],S(680,760)[1],160)]},
 {'name':'body','png':f'{OUT}/_body.png','caps':PC,'post':robe_follow},
 {'name':'armN','png':f'{OUT}/_armN.png','caps':AN,'dense':[(S(900,600)[0],S(900,600)[1],150),(S(1090,735)[0],S(1090,735)[1],170),(S(1270,865)[0],S(1270,865)[1],150)]}],OUT)
print(json.dumps(st))
# pré-visualização do recorte
from PIL import Image as I
pv=I.new('RGBA',(2048,2048),(255,255,255,255))
for n in ['legB','legF','armK','body','armN']: pv.alpha_composite(I.open(f'{OUT}/_{n}.png'))
pv.convert('RGB').resize((1000,1000)).save(f'{OUT}/_preview.png')
