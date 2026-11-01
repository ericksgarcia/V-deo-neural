"""meshlib.py: SVG -> camadas raster -> malha densa -> pesos por difusão (Dirichlet nas cápsulas dos ossos) -> displays do DragonBones."""
import re,json,subprocess,os
import numpy as np,cv2
from scipy.spatial import Delaunay,cKDTree
import scipy.sparse as sp,scipy.sparse.linalg as spl
from PIL import Image
W=H=2048

# ---------- leitura do SVG (paths como lista [(cor_hex, d)]) ----------
def load_paths(svgfile):
    s=re.sub(r'<metadata>.*?</metadata>','',open(svgfile).read(),flags=re.S)
    grads={}
    for m in re.finditer(r'<linearGradient id="([^"]+)".*?</linearGradient>',s,flags=re.S):
        st=re.findall(r'stop-color="rgb\((\d+),(\d+),(\d+)\)"',m.group(0))
        if st: grads[m.group(1)]=tuple(sum(int(x[i]) for x in st)//len(st) for i in range(3))
    out=[]
    for p in re.findall(r'<path\b[^>]*/>',s):
        d=re.search(r'\bd="([^"]*)"',p).group(1);f=re.search(r'fill="([^"]*)"',p).group(1)
        m=re.match(r'rgb\((\d+),(\d+),(\d+)\)',f)
        if m: c=tuple(int(x) for x in m.groups())
        else:
            g=re.search(r'#([^)]+)\)',f);c=grads.get(g.group(1),(128,128,128)) if g else (128,128,128)
        out.append(('#%02x%02x%02x'%c,d))
    b=bbox(out[0][1])
    if (b[2]-b[0])>2000 and (b[3]-b[1])>2000: out=out[1:]
    return out
def bbox(d):
    n=[float(x) for x in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?',d)];xs,ys=n[0::2],n[1::2]
    return min(xs),min(ys),max(xs),max(ys)
def rasterize(paths,out_png):
    body=''.join(f'<path fill="{p[0]}" d="{p[1]}" {p[2] if len(p)>2 else ""}/>' for p in paths)
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2048 2048" width="2048" height="2048"><defs><clipPath id="c"><rect width="2048" height="1790"/></clipPath></defs>'+body+'</svg>'
    tmp=out_png+'.svg';open(tmp,'w').write(svg)
    subprocess.run(['node','poc/svg2png_t.js',os.path.abspath(tmp),os.path.abspath(out_png),'2048'],check=True);os.remove(tmp)
    bleed(out_png)

def bleed(png):
    """propaga a cor dos pixels opacos para os transparentes (evita franja branca no filtro bilinear)"""
    from scipy import ndimage
    a=np.array(Image.open(png).convert('RGBA'))
    # remove o halo quase branco que a arte tem fora do contorno escuro (conectado ao fundo, até 16 px)
    nw=(a[...,:3].min(2)>=232)&((a[...,:3].max(2)-a[...,:3].min(2))<=22)&(a[...,3]>0)
    reach=a[...,3]==0
    for _ in range(16): reach=reach|(ndimage.binary_dilation(reach)&nw)
    a[...,3]=np.where(reach,0,a[...,3])
    a[...,3]=np.where(a[...,3]>110,255,0).astype(np.uint8)   # alfa binário: sem frestas entre triângulos
    op=a[...,3]>200
    if op.all() or not op.any(): return
    idx=ndimage.distance_transform_edt(~op,return_distances=False,return_indices=True)
    rgb=a[...,:3][idx[0],idx[1]];a[...,:3]=np.where(op[...,None],a[...,:3],rgb)
    # pixels semitransparentes de borda também ganham a cor do vizinho opaco
    Image.fromarray(a).save(png)

def dseg(p,a,b):
    a=np.array(a,float);b=np.array(b,float);ab=b-a;t=np.clip(((p-a)@ab)/(ab@ab),0,1);return np.linalg.norm(p-(a+t[:,None]*ab),axis=1)

# ---------- malha ----------
def make_mesh(png,dense_pts=(),h_base=34,h_fine=15,fine_r=150):
    rgba=np.array(Image.open(png));m=(rgba[...,3]>40).astype(np.uint8)
    m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8));m_in=m.copy()
    m=cv2.dilate(m,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(13,13)))     # borda 6 px além do desenho
    cs,_=cv2.findContours(m,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE);pts=[]
    for c in cs:
        c=c[:,0,:].astype(float)
        if len(c)<12: continue
        d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(c,axis=0),axis=1))];n=max(4,int(d[-1]/11));s=np.linspace(0,d[-1],n,endpoint=False)
        pts+=list(np.c_[np.interp(s,d,c[:,0]),np.interp(s,d,c[:,1])])
    pts=np.array(pts);er=cv2.erode(m_in,np.ones((9,9),np.uint8))
    def grid(h,sel=None):
        g=np.mgrid[0:H:h,0:W:h].reshape(2,-1).T[:,::-1].astype(float)+h/2
        g=g[er[g[:,1].astype(int).clip(0,H-1),g[:,0].astype(int).clip(0,W-1)]>0]
        return g[sel(g)] if sel is not None else g
    def dense(g):
        ok=np.zeros(len(g),bool)
        for (x,y,r) in dense_pts: ok|=np.hypot(g[:,0]-x,g[:,1]-y)<r
        return ok
    parts=[pts,grid(h_base)]
    if dense_pts: parts.append(grid(h_fine,dense))
    allp=np.vstack(parts);keep=np.ones(len(allp),bool);tr=cKDTree(allp[:len(pts)])
    for i in range(len(pts),len(allp)): keep[i]=tr.query(allp[i])[0]>7
    allp=allp[keep];sel=np.ones(len(allp),bool);tr=cKDTree(allp)
    for i in range(len(pts),len(allp)):
        if not sel[i]: continue
        for j in tr.query_ball_point(allp[i],10.0):
            if j>i: sel[j]=False
    allp=allp[sel];T=Delaunay(allp).simplices
    def inm(q): return m[q[:,1].round().astype(int).clip(0,H-1),q[:,0].round().astype(int).clip(0,W-1)]>0
    A,B,C=allp[T[:,0]],allp[T[:,1]],allp[T[:,2]]
    ok=inm((A+B+C)/3)&inm((A+B)/2)&inm((B+C)/2)&inm((C+A)/2)
    ar=np.abs((B[:,0]-A[:,0])*(C[:,1]-A[:,1])-(C[:,0]-A[:,0])*(B[:,1]-A[:,1]))/2
    T=T[ok&(ar>1.0)];used=np.unique(T);rm=-np.ones(len(allp),int);rm[used]=np.arange(len(used))
    return allp[used],rm[T]

def diffuse_weights(V,T,bone_names,caps,rigid=None):
    """caps: [(osso,p0,p1,raio)]. rigid: nome do osso (peso 1 para tudo)"""
    N=len(V);nb=len(bone_names);idx={b:i for i,b in enumerate(bone_names)};Wt=np.zeros((N,nb))
    if rigid: Wt[:,idx[rigid]]=1;return Wt
    E=np.vstack([T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]]);E=np.unique(np.sort(E,axis=1),axis=0)
    ln=np.linalg.norm(V[E[:,0]]-V[E[:,1]],axis=1);w=1/np.maximum(ln,1.0)
    Wm=sp.coo_matrix((np.r_[w,w],(np.r_[E[:,0],E[:,1]],np.r_[E[:,1],E[:,0]])),shape=(N,N)).tocsr();L=sp.diags(np.asarray(Wm.sum(1)).ravel())-Wm
    own=-np.ones(N,int);best=np.full(N,1e9)
    for b,p0,p1,r in caps:
        d=dseg(V,p0,p1);ins=(d<r)&(d<best);own[ins]=idx[b];best[ins]=d[ins]
    con=own>=0;free=~con;Wt[con,own[con]]=1
    if free.any():
        Luu=L[free][:,free]+sp.eye(free.sum())*1e-9;Luc=L[free][:,con];lu=spl.splu(Luu.tocsc());Wt[free]=lu.solve(-(Luc@Wt[con]))
    bad=Wt.sum(1)<0.5
    for i in np.where(bad)[0]:
        ds=[dseg(V[i:i+1],p0,p1)[0] for _,p0,p1,_ in caps];Wt[i]=0;Wt[i,idx[caps[int(np.argmin(ds))][0]]]=1
    Wt=np.clip(Wt,0,None)
    for i in range(N): Wt[i,np.argsort(-Wt[i])[4:]]=0
    Wt[Wt<0.02]=0;return Wt/Wt.sum(1,keepdims=True)

def display(name,V,T,Wt,bones):
    """bones: [(nome,pai,x,y)] -> display mesh DragonBones"""
    used=sorted({int(j) for i in range(len(V)) for j in np.nonzero(Wt[i])[0]});weights=[]
    for i in range(len(V)):
        nz=[int(j) for j in np.nonzero(Wt[i])[0]];weights.append(len(nz))
        for j in nz: weights+=[j,round(float(Wt[i,j]),5)]
    bp=[];[bp.extend([j,1,0,0,1,bones[j][2],bones[j][3]]) for j in used]
    return {'type':'mesh','name':name,'width':W,'height':H,'vertices':[round(float(v),2) for v in V.ravel()],
      'uvs':[round(float(v),5) for v in (V/np.array([W,H])).ravel()],'triangles':[int(t) for t in T.ravel()],
      'weights':weights,'slotPose':[1,0,0,1,0,0],'bonePose':bp}

def bone_json(bones):
    out=[];pos={b[0]:(b[2],b[3]) for b in bones}
    for n,p,x,y in bones:
        d={'name':n}
        if p: d['parent']=p;d['transform']={'x':x-pos[p][0],'y':y-pos[p][1]}
        else: d['transform']={'x':x,'y':y}
        out.append(d)
    return out

def build_view(dbname,bones,layers,outdir,fps=60):
    """layers: [{name,paths,caps|rigid,dense}] na ordem de desenho. Escreve <outdir>/<dbname>_ske.json e atlas por camada."""
    names=[b[0] for b in bones];slots=[];skin=[];atlases=[];stats={}
    for L in layers:
        png=f"{outdir}/{dbname}_{L['name']}.png";rasterize(L['paths'],png)
        V,T=make_mesh(png,L.get('dense',()));Wt=diffuse_weights(V,T,names,L.get('caps',[]),L.get('rigid'))
        slots.append({'name':L['name'],'parent':'root'});skin.append({'name':L['name'],'display':[display(L['name'],V,T,Wt,bones)]})
        atlases.append({'name':dbname,'imagePath':f"{dbname}_{L['name']}.png",'width':W,'height':H,'SubTexture':[{'name':L['name'],'x':0,'y':0,'width':W,'height':H}]})
        stats[L['name']]=(len(V),len(T))
    ske={'name':dbname,'version':'5.5','compatibleVersion':'5.5','frameRate':fps,'armature':[{'type':'Armature','name':'jesus','frameRate':fps,
      'aabb':{'x':0,'y':0,'width':W,'height':H},'bone':bone_json(bones),'slot':slots,'skin':[{'name':'','slot':skin}],'animation':[],'defaultActions':[]}]}
    json.dump(ske,open(f'{outdir}/{dbname}_ske.json','w'),separators=(',',':'));json.dump(atlases,open(f'{outdir}/{dbname}_atlas.json','w'))
    return stats
