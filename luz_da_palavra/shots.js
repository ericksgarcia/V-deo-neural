const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
pg.on('pageerror',e=>console.log('ERR',e.message));pg.on('console',m=>console.log('LOG',m.text()));
await pg.goto('file://'+process.argv[2]);
const info=await pg.evaluate(()=>({TOTAL,T_STAND,T_F0,A_RAISE1,A_OPEN0,A_OPEN1,T_B0,B_OPEN1}));console.log(JSON.stringify(info));
const ts=process.argv.slice(4).map(Number);
for(const t of ts){await pg.evaluate(t=>setT(t),t);await pg.screenshot({path:`${process.argv[3]}/s_${t.toFixed(2)}.png`});}
await b.close()})();
