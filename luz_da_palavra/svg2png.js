const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const [svg,png,w,h]=process.argv.slice(2);let s=fs.readFileSync(svg,'utf8').replace(/<metadata>[\s\S]*?<\/metadata>/,'');
s=s.replace(/width="\d+" height="\d+"/,`width="${w}" height="${h}"`);
const html=png+'.html';fs.writeFileSync(html,`<body style="margin:0;background:#fff">${s.replace(/<\?xml[^>]*>/,'')}`);
const b=await chromium.launch();const pg=await b.newPage({viewport:{width:+w,height:+h}});
await pg.goto('file://'+html);await pg.screenshot({path:png});await b.close();fs.unlinkSync(html)})();
