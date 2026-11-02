"""Publica um episódio pronto no TikTok pelo Buffer (dono, 02/nov/2026).

    python luz_da_palavra/publicar.py luz_da_palavra/roteiros/ep05_doze.json --aprovados fatos,imagens,tela,som,post
    python luz_da_palavra/publicar.py <roteiro> --aprovados ... --fila                   # entra na fila do Buffer
    python luz_da_palavra/publicar.py <roteiro> --aprovados ... --quando 2026-11-03T21:00:00-03:00
    python luz_da_palavra/publicar.py <roteiro> --status                                 # como está o post já enviado

O que faz:
  1. trava: o vídeo precisa estar APROVADO nos analistas automáticos (saida/luz/<slug>_analise.txt) e nos 5 analistas Claude
     (--aprovados com os 5 nomes; o Claude só passa isso depois de ler os 5 relatórios com APROVADO); e não pode já ter sido
     postado (luz_da_palavra/publicados.json);
  2. sobe o .mp4 para o Cloudflare R2 (bucket público) e confere que o link abre (o Buffer só aceita vídeo por link);
  3. cria o post no canal do TikTok: texto = legenda do post; capa = o quadro da capa (thumbnailOffset em ms, porque as redes
     não aceitam imagem de capa avulsa); rótulo de conteúdo de IA DESMARCADO (isAiGenerated false, decisão do dono);
  4. registra em publicados.json e acompanha o status por até 3 min.

Chaves (nunca no git): .cache/r2.env (R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_URL) e
.cache/buffer.env (BUFFER_API_KEY), ou variáveis de ambiente. Rede: api.buffer.com, *.r2.cloudflarestorage.com, *.r2.dev.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PUBLICADOS = os.path.join(AQUI, "publicados.json")
ANALISTAS = ["fatos", "imagens", "tela", "som", "post"]
BUFFER = "https://api.buffer.com"
REDE = "tiktok"
IA_GERADO = False          # dono, 02/nov/2026: deixar o rótulo "gerado por IA" desmarcado


def carrega_env():
    for nome in ("r2.env", "buffer.env"):
        arq = os.path.join(RAIZ, ".cache", nome)
        if os.path.exists(arq):
            for linha in open(arq, encoding="utf-8"):
                if "=" in linha and not linha.strip().startswith("#"):
                    k, v = linha.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    os.environ.setdefault("R2_BUCKET", "xlaudebuffer")
    falta = [k for k in ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_PUBLIC_URL", "BUFFER_API_KEY")
             if not os.environ.get(k)]
    if falta:
        sys.exit(f"[publicar] faltam chaves: {', '.join(falta)} (.cache/r2.env e .cache/buffer.env)")


def gql(query, variaveis=None):
    corpo = json.dumps({"query": query, "variables": variaveis or {}}).encode()
    req = urllib.request.Request(BUFFER, corpo, {"Content-Type": "application/json",
                                                 "Authorization": "Bearer " + os.environ["BUFFER_API_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"[buffer] HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:400]}")
    if resp.get("errors"):
        sys.exit(f"[buffer] {resp['errors']}")
    return resp["data"]


def canal_tiktok():
    org = gql("{ account { organizations { id } } }")["account"]["organizations"][0]["id"]
    canais = gql("query($o: OrganizationId!) { channels(input: {organizationId: $o}) { id name service isDisconnected } }",
                 {"o": org})["channels"]
    tk = [c for c in canais if c["service"] == REDE and not c["isDisconnected"]]
    if not tk:
        sys.exit(f"[buffer] nenhum canal {REDE} conectado: {canais}")
    return tk[0]


def sobe_r2(mp4, chave):
    import boto3
    s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"], region_name="auto",
                      aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                      aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])
    s3.upload_file(mp4, os.environ["R2_BUCKET"], chave, ExtraArgs={"ContentType": "video/mp4"})
    url = os.environ["R2_PUBLIC_URL"].rstrip("/") + "/" + chave
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        tam = int(r.headers.get("Content-Length", 0))
        tipo = r.headers.get("Content-Type", "")
    if tam != os.path.getsize(mp4) or "video/mp4" not in tipo:
        sys.exit(f"[r2] o link público não devolve o vídeo certo ({tam} bytes, {tipo})")
    return url


def le_publicados():
    return json.load(open(PUBLICADOS, encoding="utf-8")) if os.path.exists(PUBLICADOS) else []


def status(post_id):
    return gql("query($i: PostId!) { post(input: {id: $i}) { id status sentAt dueAt externalLink error { message } } }",
               {"i": post_id})["post"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("--aprovados", default="", help="os 5 analistas Claude que deram APROVADO: " + ",".join(ANALISTAS))
    ap.add_argument("--fila", action="store_true", help="entra na fila do Buffer em vez de publicar agora")
    ap.add_argument("--quando", help="data/hora ISO 8601 para agendar (ex.: 2026-11-03T21:00:00-03:00)")
    ap.add_argument("--status", action="store_true", help="só mostra o status do post já enviado")
    a = ap.parse_args()
    carrega_env()
    rot = json.load(open(a.roteiro, encoding="utf-8"))
    slug = rot["slug"]
    pub = le_publicados()
    feitos = [p for p in pub if p["slug"] == slug and p["rede"] == REDE]
    if a.status:
        if not feitos:
            sys.exit(f"[publicar] {slug} ainda não foi enviado")
        print(json.dumps(status(feitos[-1]["post_id"]), ensure_ascii=False, indent=1))
        return

    # 1. travas
    if feitos:
        sys.exit(f"[publicar] {slug} já foi enviado ao {REDE} ({feitos[-1]['quando']}, post {feitos[-1]['post_id']}): não duplico")
    mp4 = os.path.join(RAIZ, "saida", "luz", slug + ".mp4")
    analise = mp4[:-4] + "_analise.txt"
    legenda_arq = mp4[:-4] + "_legenda.txt"
    rend_arq = os.path.join(RAIZ, ".cache", "luz", slug, "render.json")
    for arq in (mp4, analise, legenda_arq, rend_arq):
        if not os.path.exists(arq):
            sys.exit(f"[publicar] falta {arq}: gere o vídeo antes")
    if "APROVADO nos automáticos" not in open(analise, encoding="utf-8").read():
        sys.exit("[publicar] o vídeo não está APROVADO nos analistas automáticos")
    if os.path.getmtime(analise) < os.path.getmtime(mp4) - 5:
        sys.exit("[publicar] a análise automática é mais velha que o vídeo: rode o gerador de novo")
    ok = {x.strip() for x in a.aprovados.split(",") if x.strip()}
    if set(ANALISTAS) - ok:
        sys.exit(f"[publicar] faltam analistas Claude APROVADO: {', '.join(sorted(set(ANALISTAS) - ok))}")
    legenda = open(legenda_arq, encoding="utf-8").read().strip()
    rend = json.load(open(rend_arq))
    capa_ms = int(round(rend["capa_t"] * 1000))

    # 2. vídeo no R2
    url = sobe_r2(mp4, f"luz/{slug}.mp4")
    print(f"[r2] vídeo no ar: {url}")

    # 3. post no Buffer
    canal = canal_tiktok()
    modo = "customScheduled" if a.quando else ("addToQueue" if a.fila else "shareNow")
    entrada = {
        "channelId": canal["id"],
        "text": legenda,
        "assets": [{"video": {"url": url, "metadata": {"thumbnailOffset": capa_ms}}}],
        "metadata": {"tiktok": {"isAiGenerated": IA_GERADO}},
        "mode": modo,
        "schedulingType": "automatic",
        "needsApproval": False,
        "source": "luz_da_palavra",
    }
    if a.quando:
        entrada["dueAt"] = a.quando
    r = gql("""mutation($e: CreatePostInput!) { createPost(input: $e) {
                 __typename
                 ... on PostActionSuccess { post { id status dueAt } }
                 ... on InvalidInputError { message }
                 ... on LimitReachedError { message }
                 ... on UnauthorizedError { message }
                 ... on UnexpectedError { message }
                 ... on RestProxyError { message }
                 ... on NotFoundError { message } } }""", {"e": entrada})["createPost"]
    if r["__typename"] != "PostActionSuccess":
        sys.exit(f"[buffer] post recusado ({r['__typename']}): {r.get('message')}")
    post = r["post"]
    print(f"[buffer] post criado no {canal['name']} ({REDE}): {post['id']} · {post['status']} · modo {modo}")

    # 4. registro e acompanhamento
    pub.append({"slug": slug, "rede": REDE, "canal": canal["name"], "post_id": post["id"], "modo": modo,
                "quando": time.strftime("%Y-%m-%d %H:%M"), "video_url": url, "capa_ms": capa_ms,
                "ia_gerado": IA_GERADO, "legenda_linha1": legenda.splitlines()[0]})
    json.dump(pub, open(PUBLICADOS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if modo != "shareNow":
        return
    for _ in range(18):
        time.sleep(10)
        st = status(post["id"])
        if st["status"] in ("sent", "error") or st.get("error"):
            break
    print(f"[buffer] status: {st['status']}" + (f" · erro: {st['error']['message']}" if st.get("error") else "")
          + (f" · {st['externalLink']}" if st.get("externalLink") else ""))
    if st["status"] == "error" or st.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
