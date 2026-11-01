import sys,json,time,requests
def gerar(prompt,saida,size="768x1536"):
    while True:
        r=requests.post("https://api.replicate.com/v1/models/recraft-ai/recraft-v4-svg/predictions",
            headers={"Prefer":"wait=60"},json={"input":{"prompt":prompt,"size":size}},timeout=120)
        if r.status_code!=429: break
        time.sleep(r.json().get("retry_after",3)+1)
    p=r.json()
    while p.get("status") not in("succeeded","failed","canceled"):
        time.sleep(2);p=requests.get(p["urls"]["get"],timeout=60).json()
    if p["status"]!="succeeded": raise SystemExit(p)
    out=p["output"]; url=out[0] if isinstance(out,list) else out
    open(saida,"wb").write(requests.get(url,timeout=60).content); print(saida,p.get("metrics"))
if __name__=="__main__": gerar(sys.argv[2],sys.argv[1])
