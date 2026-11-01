import json,base64
def png(p): return 'data:image/png;base64,'+base64.b64encode(open(p,'rb').read()).decode()
D={};O={'front':'poc5/out','back':'poc4/out','side':'poc5/out'}
for k,layers in [('front',['body','armL','armR']),('back',['body']),('side',['legB','legF','armK','body','armN'])]:
    D[k]={'ske':json.load(open(f'{O[k]}/jesus_{k if k!='side' else 'walk'}_ske.json')),'atlas':json.load(open(f'{O[k]}/jesus_{k if k!='side' else 'walk'}_atlas.json')),'png':{l:png(f'{O[k]}/jesus_{k if k!='side' else 'walk'}_{l}.png') for l in layers}}
html=('<!doctype html><meta charset="utf-8"><body>'+''.join(f'<script>{open(f).read()}</script>' for f in ['poc/pixi.min.js','poc/dragonBones.js','gsap.min.js'])
 +f'<script>const DATA={json.dumps(D,separators=(",",":"))};</script><script>{open("poc5/page.js").read()}</script>')
open('poc5/page.html','w').write(html);print('page.html',len(html)//1024,'KB')
