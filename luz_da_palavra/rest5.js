const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
await pg.goto('file://'+process.argv[2]);
for(const name of ['frente','perfil']){
 await pg.evaluate((name)=>{for(const k in VW)VW[k].g.style.display=(k===name)?'':'none';const V=VW[name];V.sk.reset();V.sk.update();V.skin();
  V.g.setAttribute('transform','translate(640,662) scale(0.29,0.29) translate(-1010,-2030)');},name);
 await pg.screenshot({path:process.argv[3]+'/rest_'+name+'.png'});}
await b.close()})();
