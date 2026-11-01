// ===== page.js: 3 rigs DragonBones (malha densa) + linha do tempo GSAP + molas =====
PIXI.ticker.shared.autoStart=false;PIXI.ticker.shared.stop();
const app=new PIXI.Application({width:1280,height:720,backgroundColor:0xffffff,antialias:(window.AA!==false),autoStart:false});
document.body.style.margin=0;document.body.appendChild(app.view);app.ticker.stop();
const factory=dragonBones.PixiFactory.factory;
const S=0.29,GROUND=662,RAD=Math.PI/180;
const lerp=(a,b,u)=>a+(b-a)*u,clamp=(x,a,b)=>Math.max(a,Math.min(b,x)),sm=u=>{u=clamp(u,0,1);return u*u*(3-2*u)};
const V={},ANCH={front:[1010,2030],back:[1010,2030],side:[1030,2030]};
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
const st={x:-120,view:0,sq:1,rF:0,wF:0,rB:0,wB:0};
const VEL=100,X0=-120,X1=560,X2=640;
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
function poseSide(t,walking,dist,dt){
  const ph=dist*0.045,s=Math.sin(ph),c=Math.cos(ph),A=120,LIFT=30;
  if(walking){
    setB('side','ankF',-10*Math.max(0,c)+0*s,-A*s,-LIFT*Math.max(0,c));setB('side','ankB',-10*Math.max(0,-c),A*s,-LIFT*Math.max(0,-c));
    setB('side','pelvis',0,0,-16*(Math.cos(2*ph)+1)/2);setB('side','chest',1.1*Math.sin(2*ph));
    setB('side','sho',-11*s);setB('side','elb',-3*Math.max(0,-s));setB('side','fore1',-4*Math.max(0,-s));setB('side','hand',2*s);
    setB('side','neck',-1.1*Math.sin(2*ph));
    const hd=sp.head.step(1.2*Math.sin(2*ph+0.6),dt);setB('side','head',hd);
    setB('side','skirt',sp.skirt.step(-3.5*Math.sin(ph+0.6),dt));
  }else{
    setB('side','ankF',0,0,0);setB('side','ankB',0,0,0);setB('side','pelvis',0,0,Math.sin(t*1.7)*2);setB('side','chest',0.35*Math.sin(t*1.7));
    setB('side','sho',sp.hair.step(0,dt));setB('side','elb',0);setB('side','fore1',0);setB('side','hand',0);setB('side','neck',0);
    setB('side','head',sp.head.step(0,dt));setB('side','skirt',sp.skirt.step(0,dt));
  }
}
function seek(t){
  const dt=1/240;
  if(t<lastT){lastT=-1;for(const k in sp){sp[k].x=0;sp[k].v=0}}
  let cur=Math.max(0,lastT<0?0:lastT);
  // avança as molas em subpassos até t (sequencial)
  const names=['side','front','back'],nm=names[st.view];
  while(cur<t-1e-9){cur=Math.min(t,cur+dt);tl.time(Math.min(cur,tl.duration()));stepPose(cur,dt)}
  lastT=t;tl.time(Math.min(t,tl.duration()));finish(t);
}
function stepPose(t,dt){const nm=['side','front','back'][st.view];
  if(nm==='side')poseSide(t,st.x<X2-0.5,Math.max(0,st.x-X0),dt);else if(nm==='front')poseT('front',t,st.rF,st.wF,dt);else poseT('back',t,st.rB,st.wB,dt)}
function finish(t){
  const idx=st.view,nm=['side','front','back'][idx];
  for(const k of ['front','back','side'])V[k].h.visible=(k===nm);
  stepPose(t,0.0001);
  const v=V[nm];v.a.invalidUpdate(null,true);v.a.advanceTime(0);
  const dir=nm==='side'?-1:1;v.h.position.set(st.x,GROUND);v.h.scale.set(S*st.sq*dir,S);
  shadow.clear();shadow.beginFill(0x000000,0.1);shadow.drawEllipse(st.x,GROUND+6,Math.max(18,120*st.sq*(nm==='side'?0.9:1.25)),11);shadow.endFill();
  app.renderer.render(app.stage);
}
