const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
await pg.goto('file://'+process.argv[2]);
const total=await pg.evaluate(()=>TOTAL);const fps=24,n=Math.ceil(total*fps);
fs.mkdirSync(process.argv[3],{recursive:true});
const only=process.argv[4]?process.argv[4].split(',').map(Number):null;
for(let i=0;i<n;i++){ if(only&&!only.includes(i))continue;
 await pg.evaluate(t=>setT(t),i/fps);await pg.screenshot({path:`${process.argv[3]}/f${String(i).padStart(4,'0')}.png`});}
console.log('frames',n,'total',total);await b.close()})();
