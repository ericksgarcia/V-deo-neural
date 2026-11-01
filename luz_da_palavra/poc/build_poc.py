import base64,json
img='data:image/png;base64,'+base64.b64encode(open('poc/out/tex.png','rb').read()).decode()
ske=open('poc/out/ske.json').read();tex=open('poc/out/tex.json').read()
js='''
PIXI.ticker.shared.autoStart=false;PIXI.ticker.shared.stop();
const app=new PIXI.Application({width:1280,height:720,backgroundColor:0xffffff,antialias:true,autoStart:false});
document.body.style.margin=0;document.body.appendChild(app.view);app.ticker.stop();
const factory=dragonBones.PixiFactory.factory;
factory.parseDragonBonesData(SKE);
const tx=PIXI.Texture.fromImage(IMG);
function init(){
  factory.parseTextureAtlasData(TEX,tx);
  const d=factory.buildArmatureDisplay('jesus');window.D=d;
  const s=0.29;d.scale.set(s);d.x=640-1010*s;d.y=662-2025*s;app.stage.addChild(d);
  d.animation.play('wave',0);
  window.READY=true;
}
if(tx.baseTexture.hasLoaded)init();else tx.baseTexture.on('loaded',init);
window.step=function(dt){factory.clock.advanceTime(dt);app.renderer.render(app.stage)};
'''
html=f'<!doctype html><meta charset="utf-8"><body><script>{open("poc/pixi.min.js").read()}</script><script>{open("poc/dragonBones.js").read()}</script><script>const SKE={ske},TEX={tex},IMG="{img}";{js}</script>'
open('poc/poc.html','w').write(html);print('poc.html',len(html)//1024,'KB')
