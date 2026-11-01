// ===== rig3.js : rig + animação (peças do recraft-v4-styles-pro-svg) =====
const NS='http://www.w3.org/2000/svg';
const E=(p,t,a={})=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e};
const T=(e,s)=>e.setAttribute('transform',s);
const sm=x=>x<=0?0:x>=1?1:x*x*(3-2*x);
const seg=(t,a,b)=>sm((t-a)/(b-a));
const lerp=(a,b,u)=>a+(b-a)*u;
const bbx=n=>BB[n];

// peça: pv = pivô nas coords da peça; tg = destino nas coords do pai. A rotação é feita em torno de tg.
function piece(parent,name,k,pv,tg,flip=false,extra=''){
  const o=E(parent,'g'); o._tg=tg;
  const i=E(o,'g',{transform:`translate(${tg[0]},${tg[1]}) scale(${flip?-k:k},${k}) translate(${-pv[0]},${-pv[1]})`});
  const u=E(i,'use',{href:'#'+name}); if(extra) o.setAttribute('style',extra); return o;}
const rot=(o,a,dx=0,dy=0)=>T(o,`translate(${dx},${dy}) rotate(${a} ${o._tg[0]} ${o._tg[1]})`);
const mid=(n)=>{const b=bbx(n);return (b[0]+b[2])/2};
const SHADE='filter:brightness(.92)';

// ---------------- MÃO procedural + dedos do modelo ----------------
function mkHand(parent,mode){          // origem = centro do pulso; dedos para cima (-y)
  const g=E(parent,'g'); const pre=mode==='front'?'f_':'b_';
  const W=64,H=62,FW=15, front=mode==='front';
  const dedos=[]; // [thumb, idx, mid, ring, pinky]
  const defs=[
    {n:'thumb',x:W/2-2,y:-H*0.30,len:0.80,ang:30,closedAng:-62,closedC:0.5},
    {n:'idx', x:22.5, y:-H+8,len:0.94},
    {n:'mid', x:7.5,  y:-H+6,len:1.00},
    {n:'ring',x:-7.5, y:-H+8,len:0.92},
    {n:'ring',x:-22.5,y:-H+11,len:0.74}];   // mindinho = anelar menor
  const palmD=`M ${-W/2} ${-H+14} Q ${-W/2} ${-H} ${-W/2+14} ${-H} L ${W/2-14} ${-H} Q ${W/2} ${-H} ${W/2} ${-H+14} L ${W/2-3} -8 Q ${W/2-5} 3 ${W/2-18} 3 L ${-W/2+18} 3 Q ${-W/2+5} 3 ${-W/2+3} -8 Z`;
  const layerBack=E(g,'g'), palmG=E(g,'g'), layerFront=E(g,'g');
  const palm=E(palmG,'path',{d:palmD,fill:SKIN,stroke:INK,'stroke-width':3.4,'stroke-linejoin':'round'});
  if(front){ E(palmG,'path',{d:`M ${-W/2+9} ${-H*0.45} Q ${-2} ${-H*0.33} ${W/2-10} ${-H*0.55}`,fill:'none',stroke:INK,'stroke-width':1.6,'stroke-linecap':'round','opacity':.55});
             E(palmG,'path',{d:`M ${-W/2+12} ${-H*0.25} Q ${0} ${-H*0.12} ${W/2-14} ${-H*0.3}`,fill:'none',stroke:INK,'stroke-width':1.6,'stroke-linecap':'round','opacity':.45}); }
  else { for(const kx of [-22.5,-7.5,7.5,22.5]) E(palmG,'path',{d:`M ${kx-6} ${-H+8} Q ${kx} ${-H+2} ${kx+6} ${-H+8}`,fill:'none',stroke:INK,'stroke-width':1.5,'stroke-linecap':'round','opacity':.6});
         E(palmG,'path',{d:`M -6 -8 L -4 -30 M 6 -8 L 5 -26`,fill:'none',stroke:INK,'stroke-width':1.3,'opacity':.35,'stroke-linecap':'round'}); }
  defs.forEach((d,i)=>{
    const nm=pre+d.n, b=bbx(nm), w=b[2]-b[0], k=FW*(d.n==='thumb'?1.12:1)/w;
    const par=(front||i===0&&!front&&false)?layerFront:layerBack;   // frente: dedos por cima da palma; costas: por trás
    const par2=front?layerFront:(i===0?layerBack:layerBack);
    const nodeOuter=E(par2,'g'); const node=E(nodeOuter,'g');
    const inner=E(node,'g',{transform:`scale(${k},${k*d.len}) translate(${-(b[0]+b[2])/2},${-(b[3]-6)})`}); E(inner,'use',{href:'#'+nm});
    dedos.push({outer:nodeOuter,node,d});
  });
  function setFlex(f){
    dedos.forEach((o,i)=>{
      const d=o.d, u=Math.max(0,Math.min(1,f[i])), e=u*u*(3-2*u);
      if(i===0){
        const ang=lerp(d.ang, front?d.closedAng:8, e), c=lerp(1, front?d.closedC:0.6, e);
        o.outer.setAttribute('transform',`translate(${d.x},${d.y}) rotate(${ang})`);
        o.node.setAttribute('transform',`scale(1,${c})`);
      } else {
        const cC=front?-0.42:0.30; let c=lerp(1,cC,e); if(Math.abs(c)<0.13) c=(c<0?-1:1)*0.13;
        o.outer.setAttribute('transform',`translate(${d.x},${d.y})`);
        o.node.setAttribute('transform',`scale(1,${c})`);
      }
    });
  }
  setFlex([0.4,0.4,0.4,0.4,0.4]);
  return {g,setFlex};
}

// ---------------- VISTAS ----------------
const V={};  // prof, front, back
function mkProf(root){
  const v=E(root,'g',{transform:'scale(0.86)'}); const o={v};
  const kb=0.92,kh=0.46,ka=0.48,kl=0.44;
  const t=bbx('prof_torso'), pvT=[(t[0]+t[2])/2,t[3]];
  const hip=[0,-318];
  const legPv=[1708,195];
  o.armFar=piece(v,'prof_arm',ka,[1394,150],[17+16,-599+8],false,SHADE);
  o.legFar=piece(v,'prof_leg',kl,legPv,hip,true,SHADE);
  o.legNear=piece(v,'prof_leg',kl,legPv,hip,true);
  o.torso=piece(v,'prof_torso',kb,pvT,[0,-45]);
  o.head=piece(v,'prof_head',kh,[377,615],[40,-723]);
  o.armNear=piece(v,'prof_arm',ka,[1394,150],[17,-599]);
  return o;
}
function mkFront(root){
  const v=E(root,'g'); const o={v};
  const b=bbx('front_body'), pv=[mid('front_body'),b[3]];
  o.armR=piece(v,'back_arm',0.40,[1620,1058],[150,-700]);       // viewer-right (pendurado)
  o.armL=piece(v,'back_arm',0.40,[1620,1058],[-150,-700]);      // viewer-left = mão direita do personagem
  attachHand(o,'armR','handR','front',0.40); attachHand(o,'armL','handL','front',0.40);
  o.body=piece(v,'front_body',0.6,pv,[0,0]);
  o.head=piece(v,'front_head',0.40,[379,1560],[0,-640]);
  return o;
}
function mkBack(root){
  const v=E(root,'g'); const o={v};
  o.armR=piece(v,'back_arm',0.40,[1620,1058],[135,-610]);
  o.armL=piece(v,'back_arm',0.40,[1620,1058],[-135,-610]);      // viewer-left = mão esquerda do personagem
  attachHand(o,'armR','handR','back',0.40); attachHand(o,'armL','handL','back',0.40);
  o.head=piece(v,'back_head',0.28,[2212,1000],[-4,-655]);
  const b=bbx('back_body'), pv=[mid('back_body'),b[3]];
  o.body=piece(v,'back_body',0.72,pv,[0,0]);
  return o;
}
function attachHand(o,armKey,handKey,mode,k){
  const a=o[armKey], pv=[1620,1058];
  const wx=1617,wy=1836;                                   // pulso (centro do toco) nas coords do braço
  const hx=a._tg[0]+k*(wx-pv[0]), hy=a._tg[1]+k*(wy-pv[1]);
  const hg=E(a,'g'); const H=mkHand(hg,mode); hg._pos=[hx,hy]; o[handKey]=H; H.holder=hg; H.set=(r)=>T(hg,`translate(${hx},${hy}) rotate(${r})`); H.set(180);
}

// ---------------- CENA ----------------
const S=0.5, GROUND=650, VEL=170;
const cam=document.getElementById('cam');
const shadow=E(cam,'ellipse',{cx:0,cy:GROUND+4,rx:110,ry:11,fill:'#000',opacity:.10});
const charG=E(cam,'g');
V.prof=mkProf(charG); V.front=mkFront(charG); V.back=mkBack(charG);
function show(n){for(const k in V)V[k].v.style.display=(k===n)?'':'none'}

const X0=-170,X1=640,WALK=(X1-X0)/VEL;
const T_STAND=WALK+0.45, T_TURN1=T_STAND, T_F0=T_TURN1+0.40;
const RAISE=0.9, ZOOM_IN=0.9, OPEN_STEP=0.6, OPEN_DUR=0.55;
const A_RAISE0=T_F0+0.5, A_RAISE1=A_RAISE0+RAISE, A_OPEN0=A_RAISE1+0.5, A_OPEN1=A_OPEN0+4*OPEN_STEP+OPEN_DUR, A_HOLD1=A_OPEN1+1.0, A_LOWER1=A_HOLD1+0.9;
const T_TURN2=A_LOWER1+0.25, T_B0=T_TURN2+0.40;
const B_RAISE0=T_B0+0.5, B_RAISE1=B_RAISE0+RAISE, B_OPEN0=B_RAISE1+0.5, B_OPEN1=B_OPEN0+4*OPEN_STEP+OPEN_DUR, B_HOLD1=B_OPEN1+1.0, B_LOWER1=B_HOLD1+0.9;
const TOTAL=B_LOWER1+1.0;
const ORDER=[0,1,2,3,4];     // polegar, indicador, médio, anelar, mindinho

function armPose(o,hand,t,r0,r1,open0,hold1,lower1){
  const up=seg(t,r0,r1), down=seg(t,hold1,lower1), p=up*(1-down);       // 0..1..0
  const th=125*p;
  rot(o.armL,th);
  hand.set(lerp(180,220,p));
  const f=[0,0,0,0,0];
  const close=seg(t,r0,r1);                // fecha o punho enquanto levanta
  for(let i=0;i<5;i++){
    const oi=ORDER.indexOf(i);
    const opened=seg(t,open0+oi*OPEN_STEP,open0+oi*OPEN_STEP+OPEN_DUR);
    f[i]=lerp(0.4,1,close)*(1-opened);
    if(down>0) f[i]=lerp(f[i],0.4,down);
  }
  hand.setFlex(f);
  return p;
}
function pose(t){
  let x=X1,dir=1,sx=1,view='prof',ph=0,walking=false;
  if(t<WALK){x=X0+VEL*t;walking=true;ph=2.35*t}
  // viradas
  let squash=1;
  if(t>=T_TURN1&&t<T_F0){const u=(t-T_TURN1)/0.40; squash=u<0.5?1-sm(u*2):sm(u*2-1); view=u<0.5?'prof':'front'}
  else if(t>=T_F0&&t<T_TURN2) view='front';
  else if(t>=T_TURN2&&t<T_B0){const u=(t-T_TURN2)/0.40; squash=u<0.5?1-sm(u*2):sm(u*2-1); view=u<0.5?'front':'back'}
  else if(t>=T_B0) view='back';
  else if(t>=WALK) view='prof';
  show(view);
  const idle=Math.sin(t*2.2)*0.004;
  // perfil
  const p=V.prof;
  if(view==='prof'){
    const A=26*Math.PI/180,KB=0;
    let sn=0,sf=0,bob=0,an=0,lift=[0,0];
    if(walking){
      const s=Math.sin(ph); sn=A*s*180/Math.PI; sf=-sn;
      lift=[-16*Math.max(0,Math.cos(ph)),-16*Math.max(0,-Math.cos(ph))];
      bob=-9*(Math.cos(2*ph)+1)/2; an=-17*Math.sin(ph);
    }
    rot(p.legNear,sn,0,lift[0]); rot(p.legFar,sf,0,lift[1]);
    T(p.torso,`translate(0,${bob})`); T(p.head,`translate(0,${bob}) rotate(${walking?1.2*Math.sin(2*ph):0} 40 -690)`);
    rot(p.armNear,an,0,bob); rot(p.armFar,-an,0,bob);
  }
  // frente
  const f=V.front;
  T(f.body,`scale(1,${1+idle})`);
  rot(f.armR,0); f.handR.set(180); f.handR.setFlex([0.4,0.4,0.4,0.4,0.4]);
  const pa=(t>=T_F0&&t<T_TURN2+0.2)?armPose(f,f.handL,t,A_RAISE0,A_RAISE1,A_OPEN0,A_HOLD1,A_LOWER1):0;
  if(!(t>=T_F0&&t<T_TURN2+0.2)){rot(f.armL,0);f.handL.set(180);f.handL.setFlex([0.4,0.4,0.4,0.4,0.4])}
  // costas
  const b=V.back;
  rot(b.armR,0); b.handR.set(180); b.handR.setFlex([0.4,0.4,0.4,0.4,0.4]);
  let pb=0;
  if(t>=T_B0) pb=armPose(b,b.handL,t,B_RAISE0,B_RAISE1,B_OPEN0,B_HOLD1,B_LOWER1); else {rot(b.armL,0);b.handL.set(180);b.handL.setFlex([0.4,0.4,0.4,0.4,0.4])}
  // personagem
  if(view==='prof')dir=-1;
  T(charG,`translate(${x},${GROUND}) scale(${S*squash*dir},${S})`);
  shadow.setAttribute('cx',x); shadow.setAttribute('rx',110*Math.max(0.15,squash)*(view==='prof'?1:0.8));
  // câmera
  const zin=(seg(t,A_RAISE0,A_RAISE1+0.4)-seg(t,A_HOLD1,A_LOWER1))+(seg(t,B_RAISE0,B_RAISE1+0.4)-seg(t,B_HOLD1,B_LOWER1));
  T(cam,'');
  let cx=640,cy=360,Z=1;
  if(zin>0.001){
    const H=(view==='front'?f:b).handL.holder, r=H.getBoundingClientRect();
    const hx=r.x+r.width/2, hy=r.y+r.height/2;
    Z=1+2.3*zin; cx=lerp(640,hx,zin); cy=lerp(360,hy+8,zin);
  }
  T(cam,`translate(640,360) scale(${Z}) translate(${-cx},${-cy})`);
}
pose(0);
const setT=pose;
