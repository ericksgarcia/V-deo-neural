const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
pg.on('pageerror',e=>console.log('ERR',e.message));
await pg.goto('file://'+process.argv[2]);await pg.waitForFunction('window.READY===true',{timeout:60000});
const out=process.argv[3],fps=24;fs.mkdirSync(out,{recursive:true});const total=await pg.evaluate(()=>TOTAL);const n=Math.ceil(total*fps);
for(let i=0;i<n;i++){await pg.evaluate(t=>seek(t),i/fps);await pg.screenshot({path:`${out}/f${String(i).padStart(4,'0')}.png`})}
console.log('frames',n,'total',total);await b.close()})();
