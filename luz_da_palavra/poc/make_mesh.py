"""make_mesh.py: PNG RGBA do personagem -> malha densa + pesos por difusão (estilo heat/BBW) -> JSON do DragonBones.
uso: mesh/bin/python poc/make_mesh.py   (lê poc/out/tex.png, escreve poc/out/{ske.json,tex.json,debug_*.png})"""
import json,math,sys
import numpy as np,cv2
from scipy.spatial import Delaunay,cKDTree
import scipy.sparse as sp,scipy.sparse.linalg as spl
from PIL import Image

W=H=2048
rgba=np.array(Image.open('poc/out/tex.png'))
mask=(rgba[...,3]>40).astype(np.uint8)
mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
mask_in=mask.copy()
mask=cv2.dilate(mask,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))   # borda da malha 4 px além do desenho
# ---------- esqueleto: (nome,pai,x,y)
BONES=[('root',None,0,0),('pelvis','root',1010,1060),('chest','pelvis',1010,780),('neck','chest',1010,490),('head','neck',1010,490),
 ('shoL','chest',800,545),('elbL','shoL',560,595),('fore1L','elbL',477,598),('fore2L','fore1L',393,602),('handL','fore2L',310,605),
 ('shoR','chest',1220,545),('elbR','shoR',1460,595),('wrR','elbR',1735,605)]
IDX={b[0]:i for i,b in enumerate(BONES)}
# cápsulas de restrição (osso, p0, p1, raio)
CAPS=[('root',(1010,1160),(1010,1900),235),('root',(930,1700),(840,1960),70),('root',(1090,1700),(1170,1960),70),
 ('pelvis',(1010,1100),(1010,800),95),('chest',(1010,800),(1010,520),95),('neck',(1010,520),(1010,440),40),('head',(1010,440),(1005,110),135),
 ('shoL',(800,545),(560,595),38),('elbL',(560,595),(477,598),38),('fore1L',(477,598),(393,602),38),('fore2L',(393,602),(310,605),38),('handL',(310,605),(45,605),48),
 ('shoR',(1220,545),(1460,595),38),('elbR',(1460,595),(1735,605),38),('wrR',(1735,605),(2000,605),48)]
def dseg(p,a,b):
    a=np.array(a,float);b=np.array(b,float);ab=b-a;t=np.clip(((p-a)@ab)/(ab@ab),0,1);return np.linalg.norm(p-(a+t[:,None]*ab),axis=1)

# ---------- pontos: contorno + grade adaptativa
cs,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
pts=[]
for c in cs:
    c=c[:,0,:].astype(float)
    if len(c)<12: continue
    d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(c,axis=0),axis=1))]
    n=max(4,int(d[-1]/11)); s=np.linspace(0,d[-1],n,endpoint=False)
    pts+=list(np.c_[np.interp(s,d,c[:,0]),np.interp(s,d,c[:,1])])
pts=np.array(pts)
er=cv2.erode(mask_in,np.ones((9,9),np.uint8))
def grid(h,sel=None):
    g=np.mgrid[0:H:h,0:W:h].reshape(2,-1).T[:,::-1].astype(float)+h/2
    g=g[er[g[:,1].astype(int).clip(0,H-1),g[:,0].astype(int).clip(0,W-1)]>0]
    if sel is not None: g=g[sel(g)]
    return g
# densidade alta nas juntas do braço esquerdo da tela e nas mãos
def dense(g):
    ok=np.zeros(len(g),bool)
    for (x,y,r) in [(800,545,150),(560,595,160),(310,605,200),(180,605,200),(1220,545,120),(1460,595,120),(1735,605,150),(1880,605,180),(1010,500,120)]:
        ok|=np.hypot(g[:,0]-x,g[:,1]-y)<r
    return ok
g30=grid(34); g14=grid(15,dense)
allp=np.vstack([pts,g30,g14])
# remove pontos de grade muito perto de outros (mantém contorno)
keep=np.ones(len(allp),bool);tree=cKDTree(allp[:len(pts)])
for i in range(len(pts),len(allp)):
    d,_=tree.query(allp[i]);keep[i]=d>7
allp=allp[keep]
# espaçamento mínimo entre pontos internos
order=np.arange(len(allp));kept=[];ptree=None
sel=np.ones(len(allp),bool)
tr=cKDTree(allp)
for i in range(len(pts),len(allp)):
    if not sel[i]: continue
    for j in tr.query_ball_point(allp[i],10.0):
        if j>i: sel[j]=False
allp=allp[sel]
tri=Delaunay(allp)
T=tri.simplices
def inmask(q): return mask[q[:,1].round().astype(int).clip(0,H-1),q[:,0].round().astype(int).clip(0,W-1)]>0
A=allp[T[:,0]];B=allp[T[:,1]];C=allp[T[:,2]]
ok=inmask((A+B+C)/3)&inmask((A+B)/2)&inmask((B+C)/2)&inmask((C+A)/2)
area=np.abs((B[:,0]-A[:,0])*(C[:,1]-A[:,1])-(C[:,0]-A[:,0])*(B[:,1]-A[:,1]))/2
T=T[ok&(area>1.0)]
used=np.unique(T);remap=-np.ones(len(allp),int);remap[used]=np.arange(len(used))
V=allp[used];T=remap[T];N=len(V)
print('vértices',N,'triângulos',len(T))

# ---------- pesos por difusão (Laplace com restrições de Dirichlet nas cápsulas)
E=np.vstack([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]);E=np.unique(np.sort(E,axis=1),axis=0)
ln=np.linalg.norm(V[E[:,0]]-V[E[:,1]],axis=1);w=1/np.maximum(ln,1.0)
Wm=sp.coo_matrix((np.r_[w,w],(np.r_[E[:,0],E[:,1]],np.r_[E[:,1],E[:,0]])),shape=(N,N)).tocsr()
L=sp.diags(np.asarray(Wm.sum(1)).ravel())-Wm
nb=len(BONES)
own=-np.ones(N,int);best=np.full(N,1e9)
for b,p0,p1,r in CAPS:
    d=dseg(V,p0,p1);inside=(d<r)&(d<best);own[inside]=IDX[b];best[inside]=d[inside]
con=own>=0;free=~con
Wt=np.zeros((N,nb))
Wt[con,own[con]]=1
Luu=L[free][:,free]+sp.eye(free.sum())*1e-9;Luc=L[free][:,con]
lu=spl.splu(Luu.tocsc())
Bc=Wt[con]
Wt[free]=lu.solve(-(Luc@Bc))
# ilhas sem restrição -> osso mais próximo
bad=Wt.sum(1)<0.5
if bad.any():
    ds=np.array([[dseg(V[bad],p0,p1)[k] for k in range(bad.sum())] for _,p0,p1,_ in CAPS]).T
    for k,i in enumerate(np.where(bad)[0]):
        j=int(np.argmin(ds[k]));Wt[i]=0;Wt[i,IDX[CAPS[j][0]]]=1
Wt=np.clip(Wt,0,None)
# top-4 e normaliza
for i in range(N):
    idx=np.argsort(-Wt[i])[4:];Wt[i,idx]=0
Wt[Wt<0.02]=0;Wt/=Wt.sum(1,keepdims=True)

# ---------- debug
ov=np.array(Image.open('poc/out/tex.png').convert('RGBA'))
bg=np.full((H,W,3),255,np.uint8)
for t in T:
    pp=V[t].astype(np.int32);cv2.polylines(bg,[pp.reshape(-1,1,2)],True,(90,120,200),1,cv2.LINE_AA)
cv2.imwrite('poc/out/debug_wire.png',cv2.resize(bg[...,::-1],(1024,1024),interpolation=cv2.INTER_AREA))
pal=np.array([[255,255,255],[120,120,120],[0,170,0],[200,120,0],[160,0,160],[230,0,0],[250,120,0],[255,200,0],[160,220,0],[0,200,200],[0,60,230],[0,130,255],[90,0,220]],float)
col=(Wt@pal[:nb]).clip(0,255)
hm=np.full((H,W,3),255,np.uint8)
for t in T:
    cv2.fillConvexPoly(hm,V[t].astype(np.int32),tuple(int(x) for x in col[t].mean(0)[::-1]))
cv2.imwrite('poc/out/debug_weights.png',cv2.resize(hm,(1024,1024),interpolation=cv2.INTER_AREA))

# ---------- DragonBones JSON
used_b=sorted({int(j) for i in range(N) for j in np.nonzero(Wt[i])[0]})
weights=[];
for i in range(N):
    nz=[int(j) for j in np.nonzero(Wt[i])[0]];weights.append(len(nz))
    for j in nz: weights+=[j,round(float(Wt[i,j]),5)]
bonePose=[]
for j in used_b:
    wx,wy=0,0;b=BONES[j]
    # posição de repouso no mundo = soma ao longo da cadeia (todas com rotação 0)
    bonePose+=[j,1,0,0,1,b[2],b[3]]
def local(b):
    par=b[1]
    if par is None: return (0,0)
    p=BONES[IDX[par]];return (b[2]-p[2],b[3]-p[3])
bone_json=[]
for b in BONES:
    d={'name':b[0]}
    if b[1]: d['parent']=b[1]
    lx,ly=local(b);d['transform']={'x':lx,'y':ly}
    bone_json.append(d)
disp={'type':'mesh','name':'body','width':W,'height':H,'vertices':[round(float(v),2) for v in V.ravel()],
 'uvs':[round(float(v),5) for v in (V/np.array([W,H])).ravel()],'triangles':[int(t) for t in T.ravel()],
 'weights':weights,'slotPose':[1,0,0,1,0,0],'bonePose':bonePose}
FR=60
def rot(frames,curve=(0.42,0,0.58,1)):
    out=[];prev=0
    for d,deg in frames: out.append({'duration':d,'curve':list(curve),'rotate':deg})
    return out
def anim():
    # tchau: levanta (curva suave), balança o antebraço distribuído em 3 ossos + punho, abaixa
    keys=[]
    t_idle=24;t_up=54;t_wave=180;t_down=60
    # ângulos (graus): shoulder / cotovelo total / punho   [rotação positiva = horário na tela]
    S0,S1=-48,-14;E0,E1=-6,98;Wr0,Wr1=0,4
    def seq(a0,a1,wave_amp,phase,share=1.0):
        fr=[(t_idle,a0*share),(t_up,a1*share)]
        n=int(t_wave/15)
        for k in range(n):
            s=(1 if k%2==0 else -1)
            fr.append((15,(a1+s*wave_amp)*share))
        fr.append((t_down,a0*share));fr.append((1,a0*share))
        return fr
    tl=[]
    tl.append({'name':'shoL','rotateFrame':rot(seq(S0,S1,1.5,0))})
    for nm,ph in [('elbL',0),('fore1L',0),('fore2L',0)]:
        amp={'elbL':3.5,'fore1L':5.5,'fore2L':6.5}[nm]
        tl.append({'name':nm,'rotateFrame':rot(seq(E0,E1,amp,ph,share=1/3))})
    tl.append({'name':'handL','rotateFrame':rot(seq(Wr0,Wr1,9,0))})
    tl.append({'name':'chest','rotateFrame':rot([(t_idle,0),(t_up,-1.6),(t_wave,-1.6),(t_down,0),(1,0)])})
    tl.append({'name':'neck','rotateFrame':rot([(t_idle,0),(t_up,1.2),(t_wave,1.2),(t_down,0),(1,0)])})
    tl.append({'name':'shoR','rotateFrame':rot([(t_idle+t_up+t_wave+t_down+1,48)])})
    tl.append({'name':'elbR','rotateFrame':rot([(t_idle+t_up+t_wave+t_down+1,6)])})
    total=t_idle+t_up+t_wave+t_down+1
    # a primeira chave (rotate no 1º frame) precisa de uma chave inicial: já vem de seq (idle)
    return {'name':'wave','duration':total,'playTimes':0,'bone':tl}
ske={'name':'jesus_poc','version':'5.5','compatibleVersion':'5.5','frameRate':FR,
 'armature':[{'type':'Armature','name':'jesus','frameRate':FR,'aabb':{'x':0,'y':0,'width':W,'height':H},
  'bone':bone_json,'slot':[{'name':'body','parent':'root'}],
  'skin':[{'name':'','slot':[{'name':'body','display':[disp]}]}],'animation':[anim()],'defaultActions':[{'gotoAndPlay':'wave'}]}]}
json.dump(ske,open('poc/out/ske.json','w'),separators=(',',':'))
json.dump({'name':'jesus_poc','imagePath':'tex.png','width':W,'height':H,'SubTexture':[{'name':'body','x':0,'y':0,'width':W,'height':H}]},open('poc/out/tex.json','w'))
print('ok  ske.json',round(len(json.dumps(ske))/1024),'KB; ossos usados',len(used_b))
