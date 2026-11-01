const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:1280,height:720}});
await pg.goto('file://'+process.argv[2]);await pg.waitForFunction('window.READY===true');
const ts=process.argv.slice(4).map(Number);
for(const t of ts){await pg.evaluate(t=>seek(t),t);const x=await pg.evaluate(()=>st.x);const cx=Math.max(40,Math.min(1100,x-110));
 await pg.screenshot({path:`${process.argv[3]}/ft_${t.toFixed(2)}.png`,clip:{x:cx,y:545,width:220,height:150}})}
await b.close()})();
