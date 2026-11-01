"""build3.py -> anim3.html : rig a partir das folhas pro (recraft-v4-styles-pro-svg)"""
import re,json,collections
SRC={'pc':'pro_corpo1','pf':'pro_frente_costas','pm':'pro_maos'}
MAP={ # nome -> (folha, índice do cluster)
 'prof_head':('pc',1),'prof_torso':('pc',2),'prof_arm':('pc',4),'prof_leg':('pc',6),
 'front_head':('pc',0),'back_body':('pc',3),'back_arm':('pc',5),
 'front_body':('pf',0),'back_head':('pf',1),
 'f_thumb':('pm',2),'f_idx':('pm',4),'f_mid':('pm',6),'f_ring':('pm',8),
 'b_thumb':('pm',3),'b_idx':('pm',5),'b_mid':('pm',7),'b_ring':('pm',9)}
defs='';frags={};bbox={}
for key,name in SRC.items():
    d=open(f'rig3/{name}/defs.txt').read(); info=json.load(open(f'rig3/{name}/info.json'))
    ids=re.findall(r'id="([^"]+)"',d)
    def ren(t):
        for i in ids: t=t.replace(f'id="{i}"',f'id="{key}_{i}"').replace(f'#{i})',f'#{key}_{i})')
        return t
    defs+=re.sub(r'</?defs>','',ren(d))
    for n,(k,idx) in MAP.items():
        if k!=key: continue
        frags[n]=ren(open(f'rig3/{name}/p{idx}.svgfrag').read()); bbox[n]=info['parts'][idx]['bbox']
frags['prof_torso']=frags['prof_torso'].replace('fill="rgb(144,150,180)"','fill="rgb(255,255,255)"')
for n in list(frags):
    if n.split('_')[0] in('f','b') and n.split('_')[1] in('thumb','idx','mid','ring'):
        frags[n]=frags[n].replace('rgb(174,127,99)','rgb(211,152,107)')
for n in('prof_arm','prof_leg'): frags[n]=frags[n].replace('rgb(178,127,97)','rgb(211,152,107)')
frags['front_body']=frags['front_body'].replace('rgb(173,123,91)','rgb(211,152,107)')
# cores
def fills(t): return re.findall(r'fill="rgb\((\d+),(\d+),(\d+)\)"',t)
f=frags['b_mid']; cnt=collections.Counter(fills(f)); ink=None
first=re.search(r'fill="rgb\((\d+),(\d+),(\d+)\)"',f).groups(); ink='rgb(%s,%s,%s)'%first
skin='rgb(211,152,107)'
# engrossa só a silhueta (1º path escuro) dos dedos
def thick(t,W):
    return re.sub(r'<path ','<path stroke="%s" stroke-width="%s" stroke-linejoin="round" '%(ink,W),t,count=1)
for n in [x for x in frags if x[:2] in('f_','b_') and x!='b_body' and x not in('b_arm',)]:
    if n.startswith(('f_','b_')) and n.split('_')[1] in('thumb','idx','mid','ring'): frags[n]=thick(frags[n],60)
G=''.join(f'<g id="{n}">{frags[n]}</g>' for n in frags)
js=open('rig3.js').read()
html=f'''<!doctype html><meta charset="utf-8"><body style="margin:0;background:#fff;overflow:hidden">
<svg id="s" xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720"><defs>{defs}{G}</defs><rect width="1280" height="720" fill="#fff"/><g id="cam"></g></svg>
<script>const BB={json.dumps(bbox)},SKIN="{skin}",INK="{ink}";
{js}</script>'''
open('anim3.html','w').write(html); print('ok',skin,ink,len(html)//1024,'KB')
