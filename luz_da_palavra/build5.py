"""build5.py -> anim5.html
Dados: SVGs do recraft-v4-styles-pro-svg (gen3/*.svg) -> JSON de paths com cor sólida.
Remove do braço animado a "luva" fundida do desenho original e prepara o ponto de inserção do módulo de mão.
Motor de skinning (LBS) em engine5.js, técnica do Pose Animator (Apache-2.0); linha do tempo em GSAP."""
import re,json

def bbox(d):
    n=[float(x) for x in re.findall(r'-?\d+\.?\d*(?:e-?\d+)?',d)]
    xs,ys=n[0::2],n[1::2]; return min(xs),min(ys),max(xs),max(ys)

def load(name):
    s=re.sub(r'<metadata>.*?</metadata>','',open(f'gen3/{name}.svg').read(),flags=re.S)
    grads={}
    for m in re.finditer(r'<linearGradient id="([^"]+)".*?</linearGradient>',s,flags=re.S):
        st=re.findall(r'stop-color="rgb\((\d+),(\d+),(\d+)\)"',m.group(0))
        if st: grads[m.group(1)]=tuple(sum(int(x[i]) for x in st)//len(st) for i in range(3))
    out=[]
    for p in re.findall(r'<path\b[^>]*/>',s):
        d=re.search(r'\bd="([^"]*)"',p).group(1); f=re.search(r'fill="([^"]*)"',p).group(1)
        m=re.match(r'rgb\((\d+),(\d+),(\d+)\)',f)
        if m: col=tuple(int(x) for x in m.groups())
        else:
            g=re.search(r'#([^)]+)\)',f); col=grads.get(g.group(1),(128,128,128)) if g else (128,128,128)
        out.append([col,d])
    return out

def drop_bg(paths):
    b=bbox(paths[0][1])
    return paths[1:] if (b[2]-b[0])>2000 and (b[3]-b[1])>2000 else paths

# ---- remapa as cores pálidas dos módulos de mão para o tom de pele do personagem
REMAP_PALMA={(249,230,208):(245,185,137),(246,220,190):(241,177,128),(228,179,141):(214,142,94),(235,196,159):(239,172,123),(105,48,35):(150,80,52)}
REMAP_DORSO={(231,183,146):(245,185,137),(231,187,150):(244,182,133),(242,179,131):(240,172,123),(243,151,96):(226,134,88),(237,171,124):(240,176,127),(165,118,89):(214,142,94),(118,69,51):(66,18,14)}
def remap(paths,mp):
    return [[mp.get(tuple(c),tuple(c)),d] for c,d in paths]

V={}
for n in ['frente','costas','perfil']: V[n]=drop_bg(load(n))
H={}

# ---- remove a mão fundida do braço que será animado (esquerda da tela) e guarda o ponto de inserção
# remendos (cor do manto) atrás do braço: o desenho tem "buracos" onde o braço cobria o corpo
def patch(name,idx,col,d): V[name].insert(idx,[col,d])
patch('perfil',2,(250,228,202),'M 985 1060 L 1185 1060 L 1185 1430 L 985 1430 z')
patch('frente',2,(248,227,200),'M 790 520 L 905 520 L 905 840 L 790 840 z')
patch('frente',2,(248,227,200),'M 1115 520 L 1235 520 L 1235 840 L 1115 840 z')
patch('costas',2,(254,252,250),'M 790 510 L 905 510 L 905 830 L 790 830 z')
patch('costas',2,(254,252,250),'M 1115 510 L 1235 510 L 1235 830 L 1115 830 z')
for i,(c,d) in enumerate(V['perfil']):
    n=[float(v) for v in re.findall(r'-?\d+\.?\d*',d)]
    if len(n)>8 and 880<min(n[0::2])<900 and max(n[0::2])>1215 and min(n[1::2])>1980:
        V['perfil'][i:i+1]=[[c,'M 891 1991 L 1108 1991 L 1108 2027 L 891 2027 z'],[c,'M 1012 1991 L 1223 1991 L 1223 2027 L 1012 2027 z']]
        print('sola dividida',i); break
ins={}
print({n:len(V[n]) for n in V})
data={'V':{k:[['#%02x%02x%02x'%tuple(c),d] for c,d in v] for k,v in V.items()},
      'H':{k:[['#%02x%02x%02x'%tuple(c),d] for c,d in v] for k,v in H.items()},'ins':ins}
html=f'''<!doctype html><meta charset="utf-8"><body style="margin:0;background:#fff;overflow:hidden">
<svg id="s" xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#fff"/><g id="cam"></g></svg>
<script>{open('gsap.min.js').read()}</script>
<script>const DATA={json.dumps(data,separators=(',',':'))};</script>
<script>{open('engine5.js').read()}</script>'''
open('anim5.html','w').write(html); print('anim5.html',len(html)//1024,'KB')
