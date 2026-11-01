"""Fatia o SVG da folha de peças em peças riggáveis (body, arm, hand, thigh, shin) -> rig/<peça>.svg + rig/partes.json"""
import re,json,sys
src=open(sys.argv[1]).read()
src=re.sub(r'<metadata>.*?</metadata>','',src,flags=re.S)
defs=re.findall(r'<defs>.*?</defs>',src,flags=re.S)
defs=defs[0] if defs else '<defs></defs>'
ARM='M 390 380 L 600 380 L 600 915 L 390 915 z M 385 915 L 570 915 L 570 1165 L 385 1165 z'
defs=defs.replace('</defs>',f'<clipPath id="cutIn"><path d="{ARM}"/></clipPath><clipPath id="cutBody"><path clip-rule="evenodd" d="M 0 0 L 1100 0 L 1100 2100 L 0 2100 z {ARM}"/></clipPath></defs>')
paths=re.findall(r'<path\b[^>]*/>',src)
# retângulos (viewBox 1024x2048) das peças soltas; o resto é "body"
R={'arm_near':(390,375,595,915),'hand_near':(385,920,570,1160),
   'arm_far':(690,330,900,900),'hand_far':(690,910,900,1160),
   'thigh':(363,1170,544,1424),'shin':(130,1425,600,2040)}
def bbox(d):
    n=[float(x) for x in re.findall(r'-?\d+\.?\d*',d)]
    xs,ys=n[0::2],n[1::2]
    return min(xs),min(ys),max(xs),max(ys)
def dono(b,m=18):
    best=None
    for k,(x0,y0,x1,y1) in R.items():
        if b[0]>=x0-m and b[1]>=y0-m and b[2]<=x1+m and b[3]<=y1+m:
            a=(x1-x0)*(y1-y0)
            if best is None or a<best[0]: best=(a,k)
    return best[1] if best else 'body'
parts={k:[] for k in list(R)+['body']}
for p in paths[1:]:  # 0 = fundo
    d=re.search(r'\bd="([^"]*)"',p).group(1)
    attrs=re.sub(r'\s*\bd="[^"]*"','',p)[:-2].rstrip()
    subs=[('M'+s).strip() for s in d.split('M') if s.strip()]
    # agrupa subpaths por dono preservando a ordem
    grp={}
    for s in subs:
        b=bbox(s)
        if b[2]-b[0]>450 and b[3]-b[1]>1000 and 'rgb(48,31,25)' in attrs:   # contorno fundido
            parts['body'].append(f'{attrs} clip-path="url(#cutBody)" d="{s}"/>')
            parts['body'].append(attrs.replace('rgb(48,31,25)','rgb(252,252,252)')+f' clip-path="url(#cutIn)" d="{s}"/>')
            continue
        grp.setdefault(dono(b,18),[]).append(s)
    for k,ss in grp.items():
        parts[k].append(f'{attrs} d="{" ".join(ss)}"/>')
for k in ('thigh','shin'):   # tira a "boca" preta do topo dos tubos
    top=min(bbox(re.search(r'd="([^"]*)"',x).group(1))[1] for x in parts[k])
    parts[k]=[x for x in parts[k] if not ('rgb(12,11,11)' in x and bbox(re.search(r'd="([^"]*)"',x).group(1))[1]<top+40)]
    parts[k]=[x for x in parts[k] if not ('rgb(48,31,25)' in x and bbox(re.search(r'd="([^"]*)"',x).group(1))[1]<top+3 and bbox(re.search(r'd="([^"]*)"',x).group(1))[3]-bbox(re.search(r'd="([^"]*)"',x).group(1))[1]<25)]
for k in ('arm_near','hand_near'):
    under=[]
    for x in parts[k]:
        if 'rgb(252,252,252)' in x and 'clip-path' not in x:
            under.append(x.replace('rgb(252,252,252)','rgb(48,31,25)').replace('<path','<path stroke="rgb(48,31,25)" stroke-width="12" stroke-linejoin="round"',1))
    parts[k]=under+parts[k]
import os;os.makedirs('rig',exist_ok=True)
info={}
for k,v in parts.items():
    if not v: continue
    # bbox da peça
    bs=[bbox(re.search(r'd="([^"]*)"',x).group(1)) for x in v]
    bb=[min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs)]
    info[k]=bb
    open(f'rig/{k}.svgfrag','w').write(defs+'\n'.join(v))
json.dump(info,open('rig/partes.json','w'),indent=1)
print({k:(len(v),[round(x) for x in info.get(k,[])]) for k,v in parts.items()})
