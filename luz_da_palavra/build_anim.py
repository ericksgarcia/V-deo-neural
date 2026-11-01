"""Monta anim.html (SVG riggado + ciclo de caminhada) a partir de rig/*.svgfrag"""
import re,json
def frag(k):
    t=open(f'rig/{k}.svgfrag').read()
    d=re.search(r'<defs>.*?</defs>',t,flags=re.S)
    return (d.group(0) if d else ''), re.sub(r'<defs>.*?</defs>','',t,flags=re.S)
defs,_=frag('body')
G={k:frag(k)[1] for k in ['body','arm_near','hand_near','arm_far','hand_far','thigh','shin']}
defs=defs.replace('<defs>','').replace('</defs>','')
SYM=''.join(f'<g id="p_{k}">{v}</g>' for k,v in G.items())
html=f'''<!doctype html><meta charset="utf-8"><body style="margin:0;background:#fff">
<svg id="s" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1280" height="720" viewBox="0 0 1280 720">
<defs>{defs}{SYM}</defs>
<rect width="1280" height="720" fill="#fff"/>
<ellipse id="sombra" cx="0" cy="654" rx="120" ry="12" fill="#000" opacity=".10"/>
<g id="char">
 <g id="arm_far" style="filter:brightness(.93)"><use href="#p_arm_far"/><g id="hand_far"><use href="#p_hand_far"/></g></g>
 <g id="leg_far" style="filter:brightness(.93)"><g id="sh_far"><use href="#p_shin"/></g><g id="th_far" transform="translate(0,-110)"><use href="#p_thigh"/></g></g>
 <g id="body"><use href="#p_body"/></g>
 <g id="leg_near"><g id="sh_near"><use href="#p_shin"/></g><g id="th_near" transform="translate(0,-110)"><use href="#p_thigh"/></g></g>
 <g id="arm_near"><use href="#p_arm_near"/><g id="hand_near"><use href="#p_hand_near"/></g></g>
</g></svg>
<script>
const S=0.27, GROUND=654, FOOT_Y=1872, CX=460;      // escala, chão (px) e pés/centro no sistema da folha
const A=28*Math.PI/180, K=34, SW=18, V=240, W=2.21; // amplitude, joelho, balanço dos braços, px/s, rad/s
const X0=1090, X1=190, DUR=(X0-X1)/V, PAUSA=0.6, LEAD=0.4, TOTAL=LEAD+DUR+PAUSA+DUR+LEAD;
const deg=r=>r*180/Math.PI, el=id=>document.getElementById(id);
const HIP=[455,1090], KNEE=[480,1330], SHO_N=[492,405], SHO_F=[520,392];
function rot(id,a,p,extra=''){{el(id).setAttribute('transform',`${{extra}} rotate(${{a}} ${{p[0]}} ${{p[1]}})`)}}
function setT(t){{
  let x,dir,walking=true,ph;
  if(t<LEAD){{x=X0;dir=1;walking=false}}
  else if(t<LEAD+DUR){{x=X0-V*(t-LEAD);dir=1;ph=W*(t-LEAD)}}
  else if(t<LEAD+DUR+PAUSA){{x=X1;dir=1;walking=false}}
  else if(t<LEAD+DUR+PAUSA+DUR){{const u=t-LEAD-DUR-PAUSA;x=X1+V*u;dir=-1;ph=W*u}}
  else {{x=X0;dir=-1;walking=false}}
  let sn=0,sf=0,kn=0,kf=0,bob=0,an=0,af=0;
  if(walking){{
    sn=A*Math.sin(ph); sf=-sn;
    kn=-K*Math.max(0,Math.cos(ph)); kf=-K*Math.max(0,-Math.cos(ph));
    bob=-14*(Math.cos(2*ph)+1)/2; an=-SW*Math.sin(ph)*Math.PI/180; af=-an;
    sn=deg(sn);sf=deg(sf);an=deg(an);af=deg(af);
  }}
  const fy=-FOOT_Y, c=el('char');
  c.setAttribute('transform',`translate(${{x}},${{GROUND}}) scale(${{S*dir}},${{S}}) translate(${{-CX}},${{fy}})`);
  rot('leg_near',sn,HIP); rot('leg_far',sf,HIP);
  // canela: junta no joelho, gira junto com a coxa (grupo pai) + dobra do joelho
  el('sh_near').setAttribute('transform',`translate(0,-150) rotate(${{kn}} ${{KNEE[0]}} ${{KNEE[1]+150}})`);
  el('sh_far').setAttribute('transform',`translate(0,-150) rotate(${{kf}} ${{KNEE[0]}} ${{KNEE[1]+150}})`);
  rot('arm_near',an,SHO_N); rot('arm_far',af,SHO_F);
  el('body').setAttribute('transform',`translate(0,${{bob}})`);
  el('arm_near').setAttribute('transform',`translate(0,${{bob}}) rotate(${{an}} ${{SHO_N[0]}} ${{SHO_N[1]}})`);
  el('arm_far').setAttribute('transform',`translate(0,${{bob}}) rotate(${{af}} ${{SHO_F[0]}} ${{SHO_F[1]}}) translate(-282,52)`);
  const sh=el('sombra'); sh.setAttribute('cx',x);
}}
setT(0);
</script>'''
open('anim.html','w').write(html)
print('ok')
