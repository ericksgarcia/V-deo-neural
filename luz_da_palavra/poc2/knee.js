const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
await pg.goto('file://'+process.argv[2]);await pg.waitForFunction('window.READY===true');
for(const t of process.argv.slice(4).map(Number)){await pg.evaluate(t=>seek(t),t);const x=await pg.evaluate(()=>st.x);const cx=Math.max(0,Math.min(1060,x-110));
 await pg.screenshot({path:`${process.argv[3]}/k_${t.toFixed(2)}.png`,clip:{x:cx,y:430,width:220,height:260}})}
await b.close()})();
