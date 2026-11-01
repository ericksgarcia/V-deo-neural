const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
pg.on('pageerror',e=>console.log('ERR',e.message));pg.on('console',m=>console.log('LOG',m.text()));
await pg.goto('file://'+process.argv[2]);await pg.waitForFunction('window.READY===true',{timeout:30000});
const out=process.argv[3],fps=24,total=+process.argv[4]||5.4;fs.mkdirSync(out,{recursive:true});
await pg.evaluate(()=>step(0));
for(let i=0;i<Math.round(total*fps);i++){const ms=Date.now();await pg.evaluate(dt=>step(dt),1/fps);
 await pg.screenshot({path:`${out}/f${String(i).padStart(4,'0')}.png`});if(i==5)console.log('ms/frame ~',Date.now()-ms)}
await b.close()})();
