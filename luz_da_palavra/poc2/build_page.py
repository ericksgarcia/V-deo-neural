import json,base64
def png(p): return 'data:image/png;base64,'+base64.b64encode(open(p,'rb').read()).decode()
D={}
for k,layers in [('front',['body']),('back',['body']),('side',['legB','footB','legF','footF','body','arm'])]:
    D[k]={'ske':json.load(open(f'poc2/out/jesus_{k}_ske.json')),'atlas':json.load(open(f'poc2/out/jesus_{k}_atlas.json')),'png':{l:png(f'poc2/out/jesus_{k}_{l}.png') for l in layers}}
html=('<!doctype html><meta charset="utf-8"><body>'+''.join(f'<script>{open(f).read()}</script>' for f in ['poc/pixi.min.js','poc/dragonBones.js','gsap.min.js'])
 +f'<script>const DATA={json.dumps(D,separators=(",",":"))};</script><script>{open("poc2/page.js").read()}</script>')
open('poc2/page.html','w').write(html);print('page.html',len(html)//1024,'KB')
