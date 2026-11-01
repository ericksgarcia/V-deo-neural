const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const pg=await b.newPage({viewport:{width:+process.argv[4],height:+process.argv[5]}});
await pg.goto('file://'+process.argv[2]);await pg.screenshot({path:process.argv[3]});await b.close()})();
