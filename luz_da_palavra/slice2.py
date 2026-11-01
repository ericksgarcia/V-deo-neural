"""slice2.py <sheet.svg> <outdir> : separa o SVG em peças por clusters de bbox (subpaths sobrepostos) -> outdir/pN.svgfrag + info.json + contato.svg"""
import re,sys,json,os
src=open(sys.argv[1]).read(); out=sys.argv[2]; os.makedirs(out,exist_ok=True)
vb=[float(v) for v in re.search(r'viewBox="([^"]*)"',src).group(1).split()]
src=re.sub(r'<metadata>.*?</metadata>','',src,flags=re.S)
dm=re.search(r'<defs>.*?</defs>',src,flags=re.S); defs=dm.group(0) if dm else '<defs></defs>'
paths=re.findall(r'<path\b[^>]*/>',src)
def bbox(d):
    n=[float(x) for x in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?',d)]
    xs,ys=n[0::2],n[1::2]; return [min(xs),min(ys),max(xs),max(ys)]
items=[]  # (pathidx, attrs, sub, bbox)
for i,p in enumerate(paths):
    d=re.search(r'\bd="([^"]*)"',p).group(1); attrs=re.sub(r'\s*\bd="[^"]*"','',p)[:-2].rstrip()
    subs=[('M'+s).strip() for s in d.split('M') if s.strip()]
    b=[bbox(s) for s in subs]
    if len(subs)==1 and b[0][2]-b[0][0]>vb[2]*0.95 and b[0][3]-b[0][1]>vb[3]*0.95: continue  # fundo
    for s,bb in zip(subs,b): items.append((i,attrs,s,bb))
par=list(range(len(items)))
def f(x):
    while par[x]!=x: par[x]=par[par[x]]; x=par[x]
    return x
PAD=-5
for a in range(len(items)):
    for c in range(a+1,len(items)):
        A,B=items[a][3],items[c][3]
        if A[0]-PAD<=B[2] and B[0]-PAD<=A[2] and A[1]-PAD<=B[3] and B[1]-PAD<=A[3]: par[f(a)]=f(c)
cl={}
for k,it in enumerate(items): cl.setdefault(f(k),[]).append(it)
rules=[r.split(':') for r in sys.argv[3:]]
groups=list(cl.values())
for r in rules:   # divisão manual: <idx por esquerda>:<x|y>:<valor>
    pass
def bb_of(ms): return [min(m[3][0] for m in ms),min(m[3][1] for m in ms),max(m[3][2] for m in ms),max(m[3][3] for m in ms)]
groups.sort(key=lambda g:(bb_of(g)[0]+bb_of(g)[2])/2)
for r in sorted(rules,key=lambda r:-int(r[0])):
    i,ax,val=int(r[0]),r[1],float(r[2]); g=groups.pop(i); k=0 if ax=='x' else 1
    a=[m for m in g if (m[3][k]+m[3][k+2])/2<val]; b=[m for m in g if (m[3][k]+m[3][k+2])/2>=val]
    groups[i:i]=[a,b]
res=[]
for members in groups:
    bb=[min(m[3][0] for m in members),min(m[3][1] for m in members),max(m[3][2] for m in members),max(m[3][3] for m in members)]
    if (bb[2]-bb[0])*(bb[3]-bb[1])<2500: continue   # sujeira
    res.append((bb,members))
res.sort(key=lambda r:(r[0][0]+r[0][2])/2)   # esquerda -> direita
info=[];cells='';
for n,(bb,members) in enumerate(res):
    byp={}
    for m in members: byp.setdefault(m[0],[m[1],[]])[1].append(m[2])
    frag=''.join(f'{a} d="{" ".join(ss)}"/>' for _,(a,ss) in sorted(byp.items()))
    open(f'{out}/p{n}.svgfrag','w').write(frag)
    info.append({'id':n,'bbox':[round(v,1) for v in bb]})
    cells+=f'<g>{frag}</g><text x="{bb[0]}" y="{bb[1]-8}" font-size="34" fill="red">{n}</text>'
open(f'{out}/defs.txt','w').write(defs)
json.dump({'viewBox':vb,'parts':info},open(f'{out}/info.json','w'),indent=1)
open(f'{out}/contato.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" width="1600">{defs}<rect width="{vb[2]}" height="{vb[3]}" fill="#dfe"/>{cells}</svg>')
print(vb,[(i['id'],[round(v) for v in i['bbox']]) for i in info])
