// renderiza as 3 vistas (A-pose) do rig LBS em PNG transparente 1024x1024 -> 3d/in/{front,back,left}.png
const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1024,height:1024}});
await pg.goto('file://'+process.argv[2]);
await pg.evaluate(()=>{const s=document.getElementById('s');s.setAttribute('viewBox','0 0 2048 2048');s.setAttribute('width',1024);s.setAttribute('height',1024);
 s.querySelector('rect').remove();document.body.style.background='transparent';document.getElementById('cam').setAttribute('transform','');
 const sh=document.querySelector('#cam > ellipse');if(sh)sh.remove();});
for(const [name,file] of [['frente','front'],['costas','back'],['perfil','left']]){
 await pg.evaluate((name)=>{for(const k in VW)VW[k].g.style.display=(k===name)?'':'none';const V=VW[name],sk=V.sk;sk.reset();
   if(name!=='perfil'){sk.j('shoL').r=-48;sk.j('shoR').r=48;sk.j('elbL').r=-6;sk.j('elbR').r=6}
   sk.update();V.skin();V.g.setAttribute('transform','');},name);
 await pg.screenshot({path:process.argv[3]+'/'+file+'.png',omitBackground:true});}
await b.close()})();
