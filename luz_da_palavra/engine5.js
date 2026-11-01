// ===== engine5.js : skinning (LBS) sobre SVG + esqueleto + linha do tempo GSAP =====
// Técnica de pesos por distância ao osso e normalização: Pose Animator (Apache-2.0). Linha do tempo: GSAP.
const NS='http://www.w3.org/2000/svg';
const E=(p,t,a={})=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e};
const RAD=Math.PI/180, I6=[1,0,0,1,0,0];
const mul=(m,n)=>[m[0]*n[0]+m[2]*n[1],m[1]*n[0]+m[3]*n[1],m[0]*n[2]+m[2]*n[3],m[1]*n[2]+m[3]*n[3],m[0]*n[4]+m[2]*n[5]+m[4],m[1]*n[4]+m[3]*n[5]+m[5]];
const lerp=(a,b,u)=>a+(b-a)*u;

// ---------- esqueleto ----------
class Skel{
  constructor(joints,bones){
    this.idx={}; this.J=joints.map((j,i)=>{this.idx[j.n]=i;return {...j,i,r:0,s:1,tx:0,ty:0}});
    this.J.forEach(j=>{j.p=j.p===undefined?-1:this.idx[j.p]});
    this.J.forEach(j=>{ // direção de escala: para o 1º filho
      const c=this.J.find(k=>k.p===j.i); let dx=0,dy=1;
      if(c){dx=c.x-j.x;dy=c.y-j.y;const l=Math.hypot(dx,dy)||1;dx/=l;dy/=l} j.d=[dx,dy]; });
    this.M=this.J.map(()=>I6);
    this.B=bones.map(b=>({n:b.n,a:b.a,b:b.b,j:this.idx[b.j],ymin:b.ymin}));
  }
  reset(){this.J.forEach(j=>{j.r=0;j.s=1;j.tx=0;j.ty=0})}
  j(n){return this.J[this.idx[n]]}
  update(){
    for(const j of this.J){
      const c=Math.cos(j.r*RAD),s=Math.sin(j.r*RAD),k=j.s-1,dx=j.d[0],dy=j.d[1];
      const RS=mul([c,s,-s,c,0,0],[1+k*dx*dx,k*dx*dy,k*dx*dy,1+k*dy*dy,0,0]);
      let L=mul([1,0,0,1,j.x,j.y],mul(RS,[1,0,0,1,-j.x,-j.y]));
      if(j.tx||j.ty) L=mul([1,0,0,1,j.tx,j.ty],L);
      this.M[j.i]=j.p>=0?mul(this.M[j.p],L):L;
    }
    this.BM=this.B.map(b=>this.M[b.j]);
  }
}

// ---------- vista = esqueleto + paths ----------
function parseD(d){
  const t=d.match(/[MLCz]|-?[\d.]+(?:e-?\d+)?/g),segs=[],pts=[];let i=0;
  while(i<t.length){const c=t[i++];
    if(c==='M'||c==='L'){segs.push(c);pts.push(+t[i++],+t[i++])}
    else if(c==='C'){segs.push('C');for(let k=0;k<6;k++)pts.push(+t[i++])}
    else segs.push('z');}
  return {segs,pts};
}
function distSeg(px,py,ax,ay,bx,by){const dx=bx-ax,dy=by-ay,l2=dx*dx+dy*dy;let u=l2?((px-ax)*dx+(py-ay)*dy)/l2:0;u=Math.max(0,Math.min(1,u));return Math.hypot(px-(ax+u*dx),py-(ay+u*dy))}

class View{
  constructor(name,skel,classify,opt={}){
    this.name=name;this.sk=skel;this.g=E(document.getElementById('cam'),'g',{style:'display:none'});
    const P=DATA.V[name];this.paths=[];
    const all=[];
    P.forEach(([f,d],k)=>{const el=E(this.g,'path',{fill:f});const pp=parseD(d);
      let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;for(let i=0;i<pp.pts.length;i+=2){x0=Math.min(x0,pp.pts[i]);x1=Math.max(x1,pp.pts[i]);y0=Math.min(y0,pp.pts[i+1]);y1=Math.max(y1,pp.pts[i+1])}
      pp.bb=[x0,y0,x1,y1];pp.el=el;pp.col=f;pp.k=k;this.paths.push(pp)});
    if(opt.clipY){const cp=E(this.g,'clipPath',{id:'clip_'+name});E(cp,'rect',{x:-200,y:-200,width:2600,height:opt.clipY+200});
      this.paths.forEach(p=>{if(p.bb[3]-p.bb[1]>1500)p.el.setAttribute('clip-path','url(#clip_'+name+')')})}
    this.computeWeights(classify);
  }
  computeWeights(classify){
    const sk=this.sk,B=sk.B,nb=B.length;
    // pontos globais
    let N=0;this.paths.forEach(p=>{p.off=N;N+=p.pts.length/2});
    this.N=N;this.bi=new Uint8Array(N*4);this.bw=new Float32Array(N*4);this.P0=new Float32Array(N*2);this.P=new Float32Array(N*2);
    const names=B.map(b=>b.n);
    for(const p of this.paths){
      let allow=classify(p.bb,p.col,p.k); const sil=(allow==='SIL'); if(sil)allow=null; const al=allow?allow.map(n=>names.indexOf(n)).filter(i=>i>=0):B.map((_,i)=>i);
      // índice do ponto âncora de cada ponto
      let pi=p.off*0,pt=0,lastA=0; const anchorOf=[];
      for(const s of p.segs){
        if(s==='M'||s==='L'){anchorOf.push(pt);lastA=pt;pt++}
        else if(s==='C'){anchorOf.push(lastA,pt+2,pt+2);lastA=pt+2;pt+=3}
      }
      const wCache=new Map();
      const sm=u=>u<=0?0:u>=1?1:u*u*(3-2*u);
      const norm=(set,n,x,y)=>{const ws=set.map(i=>{const b=B[i];const d=distSeg(x,y,b.a[0],b.a[1],b.b[0],b.b[1]);return [i,1/Math.pow(d+22,4)]});
        ws.sort((a,b)=>b[1]-a[1]);let top=ws.slice(0,n);const mx=top[0][1];top=top.filter(a=>a[1]>=0.15*mx);const tot=top.reduce((s,a)=>s+a[1],0);return top.map(a=>[a[0],a[1]/tot])};
      const legs=al.filter(i=>B[i].ymin!==undefined),non=al.filter(i=>B[i].ymin===undefined);
      const torsoIdx=TORSO.map(n=>names.indexOf(n)).filter(i=>i>=0).filter(i=>B[i].ymin===undefined);
      const wOf=(k)=>{ if(wCache.has(k))return wCache.get(k);
        const x=p.pts[k*2],y=p.pts[k*2+1];let r;
        if(sil&&this.name!=='perfil'&&((y>640&&x>770&&x<1330)||y>1000)) r=norm(torsoIdx,4,x,y);
        else if(!legs.length) r=norm(non,4,x,y);
        else{ const f=non.length?sm((y-B[legs[0]].ymin)/140):1;
          if(f<=0) r=norm(non,4,x,y); else if(f>=1||!non.length) r=norm(legs,4,x,y);
          else r=norm(non,2,x,y).map(([i,w])=>[i,w*(1-f)]).concat(norm(legs,2,x,y).map(([i,w])=>[i,w*f])); }
        wCache.set(k,r);return r};
      for(let k=0;k<pt;k++){
        const a=anchorOf[k];const r=wOf(a);const g=p.off+k;
        this.P0[g*2]=p.pts[k*2];this.P0[g*2+1]=p.pts[k*2+1];
        for(let u=0;u<4;u++){this.bi[g*4+u]=r[u]?r[u][0]:0;this.bw[g*4+u]=r[u]?r[u][1]:0}
      }
    }
  }
  skin(){
    const BM=this.sk.BM,P0=this.P0,P=this.P,bi=this.bi,bw=this.bw;
    for(let g=0;g<this.N;g++){
      const x=P0[g*2],y=P0[g*2+1];let ox=0,oy=0;
      for(let u=0;u<4;u++){const w=bw[g*4+u];if(!w)continue;const m=BM[bi[g*4+u]];
        ox+=w*(m[0]*x+m[2]*y+m[4]);oy+=w*(m[1]*x+m[3]*y+m[5])}
      P[g*2]=ox;P[g*2+1]=oy;
    }
    for(const p of this.paths){
      let s='',o=p.off*2;
      for(const c of p.segs){
        if(c==='z')s+='z';
        else if(c==='C'){s+='C'+P[o].toFixed(1)+' '+P[o+1].toFixed(1)+' '+P[o+2].toFixed(1)+' '+P[o+3].toFixed(1)+' '+P[o+4].toFixed(1)+' '+P[o+5].toFixed(1);o+=6}
        else{s+=c+P[o].toFixed(1)+' '+P[o+1].toFixed(1);o+=2}
      }
      p.el.setAttribute('d',s);
    }
  }
}

// ---------- esqueletos das 3 vistas ----------
const TJ=(o)=>[ // T-pose (frente/costas); o = deslocamentos por vista
 {n:'pelvis',x:1010,y:1060},{n:'chest',x:1010,y:780,p:'pelvis'},{n:'neck',x:1010,y:490,p:'chest'},
 {n:'shoL',x:800,y:o.sy,p:'chest'},{n:'elbL',x:560,y:o.ey,p:'shoL'},{n:'wrL',x:310,y:o.wy,p:'elbL'},
 {n:'shoR',x:1220,y:o.sy,p:'chest'},{n:'elbR',x:1460,y:o.ey,p:'shoR'},{n:'wrR',x:1735,y:o.wy+5,p:'elbR'},
 {n:'hipL',x:940,y:1090,p:'pelvis'},{n:'kneeL',x:890,y:1540,p:'hipL'},{n:'ankL',x:830,y:1950,p:'kneeL'},
 {n:'hipR',x:1090,y:1090,p:'pelvis'},{n:'kneeR',x:1150,y:1540,p:'hipR'},{n:'ankR',x:1210,y:1950,p:'kneeR'}];
const TB=(o)=>[
 {n:'spineLow',a:[1010,1060],b:[1010,780],j:'pelvis'},{n:'spineMid',a:[1010,780],b:[1010,490],j:'chest'},
 {n:'headB',a:[1010,490],b:[1005,60],j:'neck'},
 {n:'clavL',a:[1010,520],b:[800,o.sy],j:'chest'},{n:'clavR',a:[1010,520],b:[1220,o.sy],j:'chest'},
 {n:'upL',a:[800,o.sy],b:[560,o.ey],j:'shoL'},{n:'foreL',a:[560,o.ey],b:[310,o.wy],j:'elbL'},{n:'handL',a:[310,o.wy],b:[40,o.wy],j:'wrL'},
 {n:'upR',a:[1220,o.sy],b:[1460,o.ey],j:'shoR'},{n:'foreR',a:[1460,o.ey],b:[1735,o.wy+5],j:'elbR'},{n:'handR',a:[1735,o.wy+5],b:[2005,o.wy+5],j:'wrR'},
 {ymin:1760,n:'thL',a:[940,1090],b:[890,1540],j:'hipL'},{ymin:1760,n:'shL',a:[890,1540],b:[830,1950],j:'kneeL'},{ymin:1760,n:'ftL',a:[830,1950],b:[740,2015],j:'ankL'},
 {ymin:1760,n:'thR',a:[1090,1090],b:[1150,1540],j:'hipR'},{ymin:1760,n:'shR',a:[1150,1540],b:[1210,1950],j:'kneeR'},{ymin:1760,n:'ftR',a:[1210,1950],b:[1300,2015],j:'ankR'}];
const isRed=c=>{const r=parseInt(c.slice(1,3),16),g=parseInt(c.slice(3,5),16),b=parseInt(c.slice(5,7),16);return r>100&&g<70&&b<55&&r>g*2.2};
const TORSO=['spineMid','spineLow','clavL','clavR','headB'];
const ARML=['upL','foreL','handL','clavL'],ARMR=['upR','foreR','handR','clavR'];
const LOW=['spineLow','thL','thR','shL','shR','ftL','ftR'];
function classifyT(bb,col,k){
  const [x0,y0,x1,y1]=bb;
  if(y1-y0>1500) return 'SIL';
  if(col==='#f8e3c8'||col==='#fefcfa') return TORSO;
  if(y1<520&&x0>=770&&x1<=1260) return ['headB','spineMid'];
  if(isRed(col)&&y1<1850&&x0>700&&x1<1400) return TORSO;
  if(x1<880&&y0>430&&y1<950) return ARML;
  if(x0>1150&&y0>430&&y1<950) return ARMR;
  if(y0>1850) return ((x0+x1)/2<1020)?['ftL','shL']:['ftR','shR'];
  if(y0>1050) return LOW;
  return null;
}
const PJ=[ // perfil, olhando para a ESQUERDA
 {n:'pelvis',x:1060,y:1090},{n:'chest',x:1055,y:800,p:'pelvis'},{n:'neck',x:1010,y:470,p:'chest'},
 {n:'sho',x:1130,y:540,p:'chest'},{n:'elb',x:1115,y:830,p:'sho'},{n:'wr',x:1090,y:1100,p:'elb'},
 {n:'hipF',x:1040,y:1100,p:'pelvis'},{n:'kneeF',x:1040,y:1500,p:'hipF'},{n:'ankF',x:1030,y:1925,p:'kneeF'},
 {n:'hipB',x:1090,y:1100,p:'pelvis'},{n:'kneeB',x:1100,y:1500,p:'hipB'},{n:'ankB',x:1130,y:1925,p:'kneeB'},{n:'skirt',x:1060,y:1100,p:'pelvis'}];
const PB=[
 {n:'spineLow',a:[1060,1090],b:[1055,800],j:'pelvis'},{n:'spineMid',a:[1055,800],b:[1010,470],j:'chest'},{n:'headB',a:[1010,470],b:[1010,40],j:'neck'},
 {n:'clav',a:[1055,520],b:[1130,540],j:'chest'},{n:'up',a:[1130,540],b:[1115,830],j:'sho'},{n:'fore',a:[1115,830],b:[1090,1100],j:'elb'},{n:'hand',a:[1090,1100],b:[1075,1370],j:'wr'},
 {ymin:1760,n:'thF',a:[1040,1100],b:[1040,1500],j:'hipF'},{ymin:1760,n:'shF',a:[1040,1500],b:[1030,1925],j:'kneeF'},{ymin:1760,n:'ftF',a:[1030,1925],b:[840,2015],j:'ankF'},
 {ymin:1760,n:'thB',a:[1090,1100],b:[1100,1500],j:'hipB'},{ymin:1760,n:'shB',a:[1100,1500],b:[1130,1925],j:'kneeB'},{ymin:1760,n:'ftB',a:[1130,1925],b:[960,2015],j:'ankB'}];
function classifyP(bb,col,k){
  const [x0,y0,x1,y1]=bb;
  if(y1-y0>1500) return ['headB','spineMid','spineLow','skirt','clav'];   // contorno gigante
  if(y1<480) return ['headB','spineMid'];
  if(x0>985&&x1<1340&&y0>450&&y1<1400&&!isRed(col)) return ['up','fore','hand','clav'];
  if(y0>=1800&&y1>1860){const c=(x0+x1)/2;return c<1075?['ftF']:['ftB']}
  if(y1<1860) return ['spineLow','spineMid','skirt','clav','headB'];
  if(y0>1100) return ['spineLow','skirt','thF','thB','shF','shB'];
  return ['spineLow','spineMid','headB','clav','skirt','thF','thB','shF','shB'];   // resto: sem braço
}

// ---------- montagem ----------
const VW={};
VW.frente=new View('frente',new Skel(TJ({sy:545,ey:595,wy:605}),TB({sy:545,ey:595,wy:605})),classifyT);
VW.costas=new View('costas',new Skel(TJ({sy:530,ey:565,wy:570}),TB({sy:530,ey:565,wy:570})),classifyT);
VW.perfil=new View('perfil',new Skel(PJ,PB),classifyP,{clipY:1790});
const ANCH={frente:[1010,2030],costas:[1010,2030],perfil:[1030,2030]};
const shadow=E(document.getElementById('cam'),'ellipse',{cx:0,cy:668,rx:120,ry:12,fill:'#000',opacity:.1});
const S=0.29,GROUND=662;

// ---------- linha do tempo (GSAP, determinística: seek por tempo) ----------
const st={x:-220,view:0,sq:1,rF:0,wF:0,rB:0,wB:0};
const WALK_V=150, X0=-220, X1=560, X2=640;
const tl=gsap.timeline({paused:true});
let t0=0;
tl.to(st,{x:X1,duration:(X1-X0)/WALK_V,ease:'none'},0);
t0=(X1-X0)/WALK_V;                                   // ~3.9 s
tl.to(st,{x:X2,duration:1.0,ease:'power2.out'},t0);  // desacelera até o centro
t0+=1.0+0.25;
tl.to(st,{sq:0,duration:0.2,ease:'power2.in'},t0).set(st,{view:1},t0+0.2).to(st,{sq:1,duration:0.2,ease:'power2.out'},t0+0.2);
t0+=0.4+0.35;
const T_F=t0;                                          // frente: tchau
tl.to(st,{rF:-0.12,duration:0.18,ease:'power1.out'},t0)                 // antecipação
  .to(st,{rF:1.04,duration:0.62,ease:'power2.inOut'},t0+0.18)
  .to(st,{rF:1,duration:0.14,ease:'sine.out'},t0+0.80)
  .to(st,{wF:1,duration:0.3,ease:'sine.out'},t0+0.7);
t0+=0.95+2.4;
tl.to(st,{wF:0,duration:0.25,ease:'sine.in'},t0-0.1)
  .to(st,{rF:-0.05,duration:0.6,ease:'power2.inOut'},t0).to(st,{rF:0,duration:0.15,ease:'sine.out'},t0+0.6);
t0+=0.9;
tl.to(st,{sq:0,duration:0.2,ease:'power2.in'},t0).set(st,{view:2},t0+0.2).to(st,{sq:1,duration:0.2,ease:'power2.out'},t0+0.2);
t0+=0.4+0.35;
const T_B=t0;                                          // costas: tchau
tl.to(st,{rB:-0.12,duration:0.18,ease:'power1.out'},t0)
  .to(st,{rB:1.04,duration:0.62,ease:'power2.inOut'},t0+0.18)
  .to(st,{rB:1,duration:0.14,ease:'sine.out'},t0+0.80)
  .to(st,{wB:1,duration:0.3,ease:'sine.out'},t0+0.7);
t0+=0.95+2.4;
tl.to(st,{wB:0,duration:0.25,ease:'sine.in'},t0-0.1)
  .to(st,{rB:-0.05,duration:0.6,ease:'power2.inOut'},t0).to(st,{rB:0,duration:0.15,ease:'sine.out'},t0+0.6);
t0+=0.75+1.0;
const TOTAL=t0;

// ---------- pose ----------
const IDLE=48;
function tposeArms(sk,t,raise,wave,sideSign){
  // braço esquerdo da tela: levanta e dá tchau; direito fica relaxado
  const L=(a,b,u)=>a+(b-a)*u;
  const osc=Math.sin((t-0)*2*Math.PI*2.0);
  sk.j('shoL').r=L(-IDLE,-14,raise);
  sk.j('elbL').r=L(-6,98,raise)+osc*16*wave;
  sk.j('wrL').r=L(0,4,raise)+Math.sin(t*2*Math.PI*2.0-0.9)*9*wave;
  sk.j('shoR').r=IDLE; sk.j('elbR').r=6;
  sk.j('chest').r=-1.6*raise+Math.sin(t*1.7)*0.35;
  sk.j('neck').r=1.3*raise+osc*1.2*wave;
}
function pose(t){
  tl.time(Math.min(t,tl.duration()));
  const cam=document.getElementById('cam');
  let name=['perfil','frente','costas'][st.view];
  for(const k in VW)VW[k].g.style.display=(k===name)?'':'none';
  const V=VW[name],sk=V.sk;sk.reset();
  let dir=1,x=st.x;
  if(name==='perfil'){
    const dist=Math.max(0,x-X0), ph=dist*0.0315;  // fase ligada à distância
    const A=172,LIFT=38;
    const s=Math.sin(ph),c=Math.cos(ph);
    const walking=st.x<X2-0.5;
    if(walking){
      sk.j('ankF').tx=-A*s; sk.j('ankB').tx=A*s;
      sk.j('ankF').ty=-LIFT*Math.max(0,c); sk.j('ankB').ty=-LIFT*Math.max(0,-c);
      sk.j('ankF').r=-10*Math.max(0,c)*0; 
      sk.j('skirt').r=-3.5*Math.sin(ph+0.6); sk.j('pelvis').ty=-16*(Math.cos(2*ph)+1)/2; sk.j('chest').r=1.1*Math.sin(2*ph); sk.j('sho').r=-11*s; sk.j('elb').r=-5*Math.max(0,-s); sk.j('neck').r=-1.1*Math.sin(2*ph);
    } else {sk.j('pelvis').ty=Math.sin(t*1.7)*2;sk.j('chest').r=Math.sin(t*1.7)*0.35}
    dir=-1;
  } else if(name==='frente') tposeArms(sk,t,st.rF,st.wF);
  else tposeArms(sk,t,st.rB,st.wB);
  sk.update();V.skin();
  const [ax,ay]=ANCH[name];
  cam.setAttribute('transform','');
  V.g.setAttribute('transform',`translate(${x},${GROUND}) scale(${S*st.sq*dir},${S}) translate(${-ax},${-ay})`);
  shadow.setAttribute('cx',x);shadow.setAttribute('rx',Math.max(18,120*st.sq*(name==='perfil'?0.9:1.25)));
}
const setT=pose;
pose(0);
