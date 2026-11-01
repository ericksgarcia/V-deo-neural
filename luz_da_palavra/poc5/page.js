// ===== page.js: 3 rigs DragonBones (malha densa) + linha do tempo GSAP + molas =====
PIXI.ticker.shared.autoStart=false;PIXI.ticker.shared.stop();
const app=new PIXI.Application({width:1280,height:720,backgroundColor:0xffffff,antialias:(window.AA!==false),autoStart:false});
document.body.style.margin=0;document.body.appendChild(app.view);app.ticker.stop();
const factory=dragonBones.PixiFactory.factory;
const S=0.29,GROUND=662,RAD=Math.PI/180;
const lerp=(a,b,u)=>a+(b-a)*u,clamp=(x,a,b)=>Math.max(a,Math.min(b,x)),sm=u=>{u=clamp(u,0,1);return u*u*(3-2*u)};
const V={},ANCH={front:[1012,2030],back:[1012,2030],side:[930,2030]};
const shadow=new PIXI.Graphics();app.stage.addChild(shadow);
let pending=0;
for(const k of ['front','back','side']){
  const D=DATA[k];factory.parseDragonBonesData(D.ske,'jesus_'+k);
  D.atlas.forEach(a=>{pending++;const t=PIXI.Texture.fromImage(D.png[a.SubTexture[0].name]);
    const go=()=>{factory.parseTextureAtlasData(a,t,'jesus_'+k);if(--pending===0)boot()};
    if(t.baseTexture.hasLoaded)go();else t.baseTexture.on('loaded',go)});
}
function boot(){
  for(const k of ['front','back','side']){
    const d=factory.buildArmatureDisplay('jesus','jesus_'+k);const h=new PIXI.Container();h.addChild(d);h.pivot.set(...ANCH[k]);h.visible=false;
    app.stage.addChild(h);V[k]={h,d,a:d.armature};
  }
  window.READY=true;
}
const B=(v,n)=>V[v].a.getBone(n);
function setB(v,n,rot,x=0,y=0){const b=B(v,n);if(!b)return;b.offset.rotation=rot*RAD;b.offset.x=x;b.offset.y=y;b.invalidUpdate()}

// ---------- molas (movimento secundário) ----------
class Spring{constructor(k,c){this.k=k;this.c=c;this.x=0;this.v=0}
  step(target,dt){const a=this.k*(target-this.x)-this.c*this.v;this.v+=a*dt;this.x+=this.v*dt;return this.x}}
const sp={head:new Spring(120,11),skirt:new Spring(60,5),hair:new Spring(90,8)};
let lastT=-1;

// ---------- linha do tempo ----------
const st={x:-260,view:0,sq:1,rF:0,wF:0,rB:0,wB:0,cF:0,cK:0,cT0:0};
const VEL=2*250/(0.6*1.25)*0.29,X0=-260,X1=560,X2=640;
const tl=gsap.timeline({paused:true});let t0=0;
tl.to(st,{x:X1,duration:(X1-X0)/VEL,ease:'none'},0);t0=(X1-X0)/VEL;
tl.to(st,{x:X2,duration:1.0,ease:'power2.out'},t0);t0+=1.25;
tl.to(st,{sq:0,duration:0.2,ease:'power2.in'},t0).set(st,{view:1},t0+0.2).to(st,{sq:1,duration:0.2,ease:'power2.out'},t0+0.2);t0+=0.75;
const T_F=t0;
function waveBlock(r,w,t0){
  tl.to(st,{[r]:-0.12,duration:0.18,ease:'power1.out'},t0).to(st,{[r]:1.04,duration:0.62,ease:'power2.inOut'},t0+0.18).to(st,{[r]:1,duration:0.14,ease:'sine.out'},t0+0.80).to(st,{[w]:1,duration:0.3,ease:'sine.out'},t0+0.7);
  const e=t0+0.95+2.4;
  tl.to(st,{[w]:0,duration:0.25,ease:'sine.in'},e-0.1).to(st,{[r]:-0.05,duration:0.6,ease:'power2.inOut'},e).to(st,{[r]:0,duration:0.15,ease:'sine.out'},e+0.6);
  return e+0.9;
}
t0=waveBlock('rF','wF',t0);
const T_CLAP=t0;tl.to(st,{cF:1,duration:0.9,ease:'power2.inOut'},t0).set(st,{cK:1,cT0:t0+0.9},t0+0.9);t0+=0.9+3.0;tl.set(st,{cK:0},t0).to(st,{cF:0,duration:0.8,ease:'power2.inOut'},t0);t0+=1.0;
tl.to(st,{sq:0,duration:0.2,ease:'power2.in'},t0).set(st,{view:2},t0+0.2).to(st,{sq:1,duration:0.2,ease:'power2.out'},t0+0.2);t0+=0.75;
const T_B=t0;t0=waveBlock('rB','wB',t0);t0+=1.0;
const TOTAL=t0;

// ---------- pose por vista ----------
const IDLE=48;
function poseT(v,t,r,w,dt){
  const osc=Math.sin(t*2*Math.PI*2.0),lag=(d)=>Math.sin(t*2*Math.PI*2.0-d);
  const e=sm(r<0?0:r>1?1:r)*0+r;  // r já vem suavizado pelo GSAP (com antecipação e overshoot)
  const sho=lerp(-IDLE,-14,e),E=lerp(-6,98,e);
  setB(v,'shoL',sho);
  setB(v,'elbL',E/3+3.5*lag(0)*w);setB(v,'fore1L',E/3+5.5*lag(0.25)*w);setB(v,'fore2L',E/3+6.5*lag(0.5)*w);
  setB(v,'handL',4*e+9*lag(0.9)*w);
  setB(v,'shoR',IDLE+0.6*Math.sin(t*1.7));setB(v,'elbR',6);
  const ch=-1.6*e+0.35*Math.sin(t*1.7);setB(v,'chest',ch);setB(v,'pelvis',0);
  setB(v,'neck',1.3*e+1.2*osc*w);
  const hd=sp.head.step(-0.9*ch+0.8*osc*w,dt);setB(v,'head',hd);
  const sk=sp.skirt.step(0.9*osc*w-0.8*ch,dt);setB(v,'skirt',sk);
}
const LEG={F:{H:[950,1000],K:[1085,1500],A:[1187,1908]},B:{H:[950,1000],K:[760,1500],A:[594,1897]}};
function ik2(Hm,H,K0,A0,T){
  const L1=Math.hypot(K0[0]-H[0],K0[1]-H[1]),L2=Math.hypot(A0[0]-K0[0],A0[1]-K0[1]);
  const dx=T[0]-Hm[0],dy=T[1]-Hm[1];let d=Math.hypot(dx,dy);d=Math.min(d,L1+L2-1e-3);d=Math.max(d,Math.abs(L1-L2)+1e-3);
  const a=Math.atan2(dy,dx),A=Math.acos(clamp((L1*L1+d*d-L2*L2)/(2*L1*d),-1,1));
  const k1=[Hm[0]+L1*Math.cos(a-A),Hm[1]+L1*Math.sin(a-A)],k2=[Hm[0]+L1*Math.cos(a+A),Hm[1]+L1*Math.sin(a+A)];
  const K=k1[0]>k2[0]?k1:k2;
  const th0=Math.atan2(K0[1]-H[1],K0[0]-H[0]),sh0=Math.atan2(A0[1]-K0[1],A0[0]-K0[0]);
  const th=Math.atan2(K[1]-Hm[1],K[0]-Hm[0]),sh=Math.atan2(T[1]-K[1],T[0]-K[0]);
  return {thigh:th-th0,shinAbs:sh-sh0,shin:(sh-sh0)-(th-th0)};
}
const WA=250,WT=1.25,WST=0.6,WL=60,MIDX=890,GY=1903;
const V_PX=2*WA/(WST*WT)*0.29;
const wsm=u=>{u=clamp(u,0,1);return u*u*(3-2*u)};
function wfoot(phi){const u=((phi%1)+1)%1;let dx,up,pitch;
  if(u<WST){const s=u/WST;dx=1-2*s;up=0;pitch=12*(1-wsm(s/0.18))+(-26*wsm((s-0.78)/0.22))}   // dx>0 = pé à frente
  else{const s=(u-WST)/(1-WST),e=wsm(s)*0.85+s*0.15;dx=-1+2*e;up=WL*Math.pow(Math.sin(Math.PI*s),0.8);pitch=-26+38*wsm(s*1.2)}
  return [dx*WA,up,pitch]}
let prevX=null;
function poseSide(t,dt){
  const dist=Math.max(0,st.x-X0),phi=dist/(V_PX*WT);
  const spd=prevX===null?0:Math.abs(st.x-prevX)/Math.max(dt,1e-6);prevX=st.x;
  const G=clamp(spd/V_PX,0,1),I=1-G,r=a=>a/RAD,c=Math.cos(2*Math.PI*phi),c2=Math.sin(4*Math.PI*phi);
  const bob=14*(1+Math.cos(4*Math.PI*phi))/2*G;                       // pélvis sobe no apoio? (cos2 máx no apoio = mais alto)
  const lift=-bob+Math.sin(t*1.7)*2*I;setB('side','pelvis',0,0,lift);
  for(const [s,off] of [['F',0],['B',0.5]]){
    const L=LEG[s],f=wfoot(phi+off),T=[L.A[0]+(MIDX+f[0]-L.A[0])*G,L.A[1]+(GY-f[1]-L.A[1])*G],Hm=[L.H[0],L.H[1]+lift];
    const k=ik2(Hm,L.H,L.K,L.A,T);
    setB('side','thigh'+s,r(k.thigh));setB('side','shin'+s,r(k.shin));setB('side','foot'+s,-f[2]*G-r(k.shinAbs));
  }
  setB('side','chest',(1.2*c2+0.3)*G+0.35*Math.sin(t*1.7)*I);setB('side','neck',-1.2*c2*G);
  setB('side','head',sp.head.step(1.4*Math.sin(4*Math.PI*phi+0.6)*G,dt));
  setB('side','skirt',sp.skirt.step(-3*Math.sin(2*Math.PI*phi+0.6)*G,dt));
  // braços alternados: o da frente (N) vai com a perna de trás
  setB('side','shoN',-24*c*G);setB('side','elbN',-6*(1+c)*G);setB('side','handN',6*c*G);
  setB('side','shoK',24*c*G);setB('side','elbK',4*(1-c)*G);setB('side','handK',-4*c*G);
}

// ---------- frente: tchau (braço L = esquerda da tela) e PALMAS ----------
const FR={L:{S:[806,509],E:[572,540],T:[85,599]},R:{S:[1219,514],E:[1463,546],T:[1961,600]}};
const L1=Math.hypot(FR.L.S[0]-FR.L.E[0],FR.L.S[1]-FR.L.E[1]),LF=Math.hypot(FR.L.E[0]-FR.L.T[0],FR.L.E[1]-FR.L.T[1]);
function clapPose(gap){                                    // devolve {sho,elb,k} do braço esquerdo para a ponta da mão ir a (1012-gap,585)
  const s=-26,d1=(180+s)*RAD,E=[FR.L.S[0]+L1*Math.cos(d1),FR.L.S[1]+L1*Math.sin(d1)];
  const Tg=[1012-gap,590],v=[Tg[0]-E[0],Tg[1]-E[1]],d2=Math.atan2(v[1],v[0]),dist=Math.hypot(v[0],v[1]);
  let e=(d2-d1)/RAD;e=((e%360)+540)%360-180;
  return {sho:s,elb:e,k:clamp(dist/LF,0.8,1.05)};
}
function poseFront(t,dt){
  const v='front',e=st.rF,w=st.wF,c=sm(st.cF);
  const osc=Math.sin(t*2*Math.PI*2.0),lag=d=>Math.sin(t*2*Math.PI*2.0-d);
  const wave={sho:lerp(-48,-14,e),elb:lerp(-6,98,e)+4.5*lag(0.2)*w,hand:4*e+9*lag(0.9)*w};
  // palmas
  const ph=t-st.cT0,beat=st.cK>0?0.5+0.5*Math.cos(2*Math.PI*2.4*ph):1;      // 1 = mãos afastadas
  const gap=lerp(8,95,beat)*c+ (1-c)*400;
  const cp=clapPose(Math.max(6,gap));
  // braço esquerdo da tela (L)
  const sL=lerp(wave.sho,cp.sho,c),eL=lerp(wave.elb,cp.elb,c),kL=lerp(1,cp.k,c);
  setB(v,'shoL',sL);setB(v,'elbL',eL);setB(v,'handL',lerp(wave.hand,10,c));
  const bl=B(v,'elbL');if(bl){bl.offset.scaleX=kL;bl.invalidUpdate()}
  // braço direito (R) espelha o clap; repouso: caído
  const sR=lerp(48,-cp.sho,c),eR=lerp(6,-cp.elb,c);
  setB(v,'shoR',sR+0.6*Math.sin(t*1.7)*(1-c));setB(v,'elbR',eR);setB(v,'handR',lerp(0,-10,c));
  const br=B(v,'elbR');if(br){br.offset.scaleX=lerp(1,cp.k,c);br.invalidUpdate()}
  const ch=-1.6*e+0.35*Math.sin(t*1.7)+2.0*c*Math.sin(2*Math.PI*2.4*ph)*(st.cK>0?1:0)*0.3;setB(v,'chest',ch);setB(v,'pelvis',0);
  setB(v,'neck',1.3*e+1.2*osc*w);setB(v,'head',sp.head.step(-0.9*ch+0.8*osc*w,dt));setB(v,'skirt',sp.skirt.step(0.9*osc*w-0.8*ch,dt));
}
function seek(t){
  const dt=1/240;
  if(t<lastT){lastT=-1;for(const k in sp){sp[k].x=0;sp[k].v=0}}
  if(lastT<0){prevX=null;tl.time(0);stepPose(0,1/240)}
  let cur=Math.max(0,lastT<0?0:lastT);
  // avança as molas em subpassos até t (sequencial)
  const names=['side','front','back'],nm=names[st.view];
  while(cur<t-1e-9){cur=Math.min(t,cur+dt);tl.time(Math.min(cur,tl.duration()));stepPose(cur,dt)}
  lastT=t;tl.time(Math.min(t,tl.duration()));finish(t);
}
function stepPose(t,dt){const nm=['side','front','back'][st.view];
  if(nm==='side')poseSide(t,dt);else if(nm==='front')poseFront(t,dt);else poseT('back',t,st.rB,st.wB,dt)}
function finish(t){
  const idx=st.view,nm=['side','front','back'][idx];
  for(const k of ['front','back','side'])V[k].h.visible=(k===nm);
  const v=V[nm];v.a.invalidUpdate(null,true);v.a.advanceTime(0);
  const dir=1;v.h.position.set(st.x,GROUND);v.h.scale.set(S*st.sq*dir,S);
  shadow.clear();shadow.beginFill(0x000000,0.1);shadow.drawEllipse(st.x,GROUND+6,Math.max(18,120*st.sq*(nm==='side'?0.9:1.25)),11);shadow.endFill();
  app.renderer.render(app.stage);
}
