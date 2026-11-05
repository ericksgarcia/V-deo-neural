"""Publica um episódio pronto no TikTok pelo Buffer (dono, 02/nov/2026). Instagram só manual: --redes instagram (dono desligou o automático em 05/nov/2026).

    python luz_da_palavra/publicar.py <roteiro> --aprovados fatos,imagens,tela,som,post     # agenda no próximo horário livre
    python luz_da_palavra/publicar.py <roteiro> --aprovados ... --agora                     # publica já
    python luz_da_palavra/publicar.py <roteiro> --aprovados ... --quando 2026-11-03T20:30   # horário escolhido (Brasília)
    python luz_da_palavra/publicar.py --fila          # o que está agendado no Buffer e os próximos horários livres
    python luz_da_palavra/publicar.py --lista         # vídeos no Cloudflare: pendentes x enviados (cruzando com o Buffer)
    python luz_da_palavra/publicar.py --arruma        # move para luz/enviados/ os vídeos cujo post já saiu
    python luz_da_palavra/publicar.py <roteiro> --status

Horários fixos do dono (Brasília): 07:50, 11:50, 16:50 e 20:30. Sem --agora/--quando, o post vai para o primeiro desses
horários que vem DEPOIS do último post já agendado no canal (e depois de agora + 15 min).

O que faz ao publicar:
  1. trava: APROVADO nos analistas automáticos e nos 5 analistas Claude (--aprovados), e o slug ainda não postado;
  2. sobe o .mp4 para o Cloudflare R2 em luz/pendentes/<slug>.mp4 (API da Cloudflare) e confere o link público;
  3. cria o post no TikTok: texto = legenda; capa = quadro do título (thumbnailOffset em ms); rótulo de IA desmarcado;
  4. registra em luz_da_palavra/publicados.json (vai para o git: a próxima conversa sabe o que já foi enviado).

Chaves: NENHUMA no código nem no git. Na nuvem ficam como segredos do ambiente, injetadas pelo proxy:
  api.buffer.com      -> Authorization: Bearer <chave da API do Buffer>
  api.cloudflare.com  -> Authorization: Bearer <token da Cloudflare com permissão R2 Edit>
Localmente, use BUFFER_API_KEY e CLOUDFLARE_API_TOKEN (variáveis ou .cache/buffer.env / .cache/r2.env).
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PUBLICADOS = os.path.join(AQUI, "publicados.json")
ANALISTAS = ["fatos", "imagens", "tela", "som", "post"]
BUFFER = "https://api.buffer.com"
REDE = "tiktok"                           # canal que manda na fila de horários
REDES = ["tiktok", "instagram"]            # redes que o script sabe usar
REDES_PADRAO = ["tiktok"]                  # dono, 05/nov/2026: Instagram NÃO é mais automático (só com --redes instagram)
IA_GERADO = False                         # dono, 02/nov/2026: rótulo "gerado por IA" desmarcado
BRT = ZoneInfo("America/Sao_Paulo")
HORARIOS = [(7, 50), (11, 50), (16, 50), (20, 30)]     # dono, 02/nov/2026 (horário de Brasília)
FOLGA_MIN = 15                            # nunca agenda para menos de 15 min a partir de agora
# Cloudflare R2 (não são segredos: conta, bucket e domínio público)
CF_CONTA = "255764ef4414e924c3f8b3e571f7435e"
CF_BUCKET = "xlaudebuffer"
CF_PUBLICO = "https://pub-cd071ac800384b009eaf3ddab42583fe.r2.dev"
PASTA_PENDENTES, PASTA_ENVIADOS = "luz/pendentes/", "luz/enviados/"
UA = {"User-Agent": "luz-da-palavra/1.0"}  # a Cloudflare barra o User-Agent padrão do Python
SEM_CHAVE = "injetada-pelo-proxy"         # na nuvem o proxy troca isto pela chave real (segredo do ambiente)


def carrega_env():
    for nome in ("r2.env", "buffer.env"):
        arq = os.path.join(RAIZ, ".cache", nome)
        if os.path.exists(arq):
            for linha in open(arq, encoding="utf-8"):
                if "=" in linha and not linha.strip().startswith("#"):
                    k, v = linha.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    os.environ.setdefault("BUFFER_API_KEY", SEM_CHAVE)
    os.environ.setdefault("CLOUDFLARE_API_TOKEN", os.environ.get("CF_API_TOKEN", SEM_CHAVE))


# ---------------------------------------------------------------- HTTP
def _req(url, dados=None, metodo=None, cab=None, timeout=120):
    r = urllib.request.Request(url, dados, {**UA, **(cab or {})}, method=metodo)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read(), resp.headers
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", "ignore")[:400]
        if e.code in (401, 403) and os.environ.get("BUFFER_API_KEY") == SEM_CHAVE:
            corpo += " (chave não injetada? confira os segredos do ambiente: api.buffer.com / api.cloudflare.com)"
        raise SystemExit(f"[http] {metodo or 'GET'} {url.split('?')[0]} -> {e.code}: {corpo}")


def gql(query, variaveis=None):
    _, corpo, _ = _req(BUFFER, json.dumps({"query": query, "variables": variaveis or {}}).encode(), "POST",
                       {"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["BUFFER_API_KEY"]}, 60)
    resp = json.loads(corpo)
    if resp.get("errors"):
        sys.exit(f"[buffer] {resp['errors']}")
    return resp["data"]


def cf(caminho, dados=None, metodo=None, cab=None, timeout=600):
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_CONTA}/r2/buckets/{CF_BUCKET}/{caminho}"
    _, corpo, _ = _req(url, dados, metodo, {"Authorization": "Bearer " + os.environ["CLOUDFLARE_API_TOKEN"], **(cab or {})},
                       timeout)
    try:
        resp = json.loads(corpo) if corpo else {"success": True}
    except ValueError:
        return {"success": True, "raw": corpo}
    if not resp.get("success", True):
        sys.exit(f"[cloudflare] {resp.get('errors')}")
    return resp


# ---------------------------------------------------------------- Cloudflare R2
def r2_lista(prefixo="luz/"):
    itens, cursor = [], None
    while True:
        q = {"prefix": prefixo, "per_page": 1000, **({"cursor": cursor} if cursor else {})}
        resp = cf("objects?" + urllib.parse.urlencode(q))
        itens += resp.get("result") or []
        cursor = (resp.get("result_info") or {}).get("cursor")
        if not cursor or not (resp.get("result_info") or {}).get("is_truncated"):
            return itens


def r2_sobe(dados, chave, tipo="video/mp4"):
    try:
        cf("objects/" + urllib.parse.quote(chave), dados, "PUT", {"Content-Type": tipo})
    except (TimeoutError, OSError) as e:      # a Cloudflare às vezes grava e demora a responder: confere abaixo
        print(f"[r2] resposta demorou ({e}); conferindo se o arquivo chegou…")
    url = f"{CF_PUBLICO}/{chave}"
    for _ in range(12):
        try:
            st, _, h = _req(url, metodo="HEAD", timeout=60)
            if int(h.get("Content-Length", 0)) == len(dados):
                return url
        except SystemExit:
            pass
        time.sleep(5)
    sys.exit(f"[r2] o link público {url} não devolve o arquivo completo")


def r2_apaga(chave):
    cf("objects/" + urllib.parse.quote(chave), metodo="DELETE")


# ---------------------------------------------------------------- Buffer
def organizacao():
    return gql("{ account { organizations { id } } }")["account"]["organizations"][0]["id"]


def canal_da_rede(org, rede):
    canais = gql("query($o: OrganizationId!) { channels(input: {organizationId: $o}) { id name service isDisconnected } }",
                 {"o": org})["channels"]
    tk = [c for c in canais if c["service"] == rede and not c["isDisconnected"]]
    if not tk:
        sys.exit(f"[buffer] nenhum canal {rede} conectado: {canais}")
    return tk[0]


def canal_tiktok(org):
    return canal_da_rede(org, REDE)


def metadados(rede):
    if rede == "instagram":                  # Reel que também aparece no feed; rótulo de IA desmarcado
        return {"instagram": {"type": "reel", "shouldShareToFeed": True, "isAiGenerated": IA_GERADO}}
    return {"tiktok": {"isAiGenerated": IA_GERADO}}


def posts(org, canal_id, status):
    q = """query($i: PostsInput!, $c: String) { posts(first: 50, after: $c, input: $i) {
             edges { node { id status dueAt sentAt text error { message } assets { ... on VideoAsset { source } } } }
             pageInfo { hasNextPage endCursor } } }"""
    out, cursor = [], None
    while True:
        d = gql(q, {"i": {"organizationId": org, "filter": {"channelIds": [canal_id], "status": status}}, "c": cursor})["posts"]
        out += [e["node"] for e in d["edges"]]
        if not d["pageInfo"]["hasNextPage"]:
            return out
        cursor = d["pageInfo"]["endCursor"]


def _data(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")) if iso else None


def proximos_horarios(depois_de, n=1):
    """Os n primeiros horários do dono (Brasília) estritamente depois de `depois_de`."""
    d = depois_de.astimezone(BRT)
    out, dia = [], d.date()
    while len(out) < n:
        for h, m in HORARIOS:
            t = dt.datetime(dia.year, dia.month, dia.day, h, m, tzinfo=BRT)
            if t > d and len(out) < n:
                out.append(t)
        dia += dt.timedelta(days=1)
    return out


def proximo_livre(org, canal_id):
    agora = dt.datetime.now(dt.timezone.utc)
    fila = posts(org, canal_id, ["scheduled", "sending"])
    ultimo = max([_data(p["dueAt"]) for p in fila if p.get("dueAt")] or [None], key=lambda x: x or agora)
    base = max(agora + dt.timedelta(minutes=FOLGA_MIN), ultimo or agora)
    return proximos_horarios(base)[0], fila, ultimo


# ---------------------------------------------------------------- registro
def le_publicados():
    return json.load(open(PUBLICADOS, encoding="utf-8")) if os.path.exists(PUBLICADOS) else []


def grava_publicados(pub):
    json.dump(pub, open(PUBLICADOS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def status(post_id):
    return gql("query($i: PostId!) { post(input: {id: $i}) { id status sentAt dueAt externalLink error { message } } }",
               {"i": post_id})["post"]


# ---------------------------------------------------------------- comandos
def cmd_fila():
    org = organizacao()
    canal = canal_tiktok(org)
    prox, fila, ultimo = proximo_livre(org, canal["id"])
    agora = dt.datetime.now(BRT)
    print(f"Agora (Brasília): {agora:%a %d/%m/%Y %H:%M} · canal {canal['name']} ({REDE})")
    print(f"Agendados/enviando: {len(fila)}" + ("" if fila else " (fila vazia)"))
    for p in sorted(fila, key=lambda p: p.get("dueAt") or ""):
        print(f"  {_data(p['dueAt']).astimezone(BRT):%d/%m %H:%M} · {p['status']:9s} · {(p.get('text') or '')[:60]!r}")
    print(f"Próximo horário livre: {prox:%a %d/%m/%Y %H:%M} (Brasília)")


def cmd_lista():
    pub = {p.get("r2_chave") or p["video_url"].split(CF_PUBLICO + "/")[-1]: p for p in le_publicados()}
    org = organizacao()
    canal = canal_tiktok(org)
    por_url = {}
    for p in posts(org, canal["id"], ["scheduled", "sending", "sent", "error"]):
        for a in p.get("assets") or []:
            if a.get("source"):
                por_url[a["source"]] = p
    print(f"{'pasta':10s} {'arquivo':38s} {'MB':>6s}  post no Buffer")
    for o in r2_lista():
        k = o["key"]
        p = por_url.get(f"{CF_PUBLICO}/{k}")
        pasta = "enviados" if k.startswith(PASTA_ENVIADOS) else ("pendentes" if k.startswith(PASTA_PENDENTES) else "outra")
        if p:
            info = f"{p['status']}" + (f" em {_data(p.get('sentAt') or p['dueAt']).astimezone(BRT):%d/%m %H:%M}")
        else:
            info = "registrado em publicados.json" if k in pub else "sem post (órfão)"
        print(f"{pasta:10s} {k:38s} {o['size'] / 1e6:6.1f}  {info}")


def cmd_arruma():
    """Vídeos cujos posts (TikTok e Instagram) já saíram: copia de luz/pendentes/ para luz/enviados/ e apaga o pendente."""
    pub = le_publicados()
    mudou = False
    grupos = {}
    for p in pub:
        grupos.setdefault(p.get("r2_chave") or p["video_url"].split(CF_PUBLICO + "/")[-1], []).append(p)
    for chave, ps in grupos.items():
        if chave.startswith(PASTA_ENVIADOS):
            continue
        sts = [(p, status(p["post_id"])) for p in ps]
        pend = [f"{p['rede']}: {st['status']}" for p, st in sts if st["status"] != "sent"]
        if pend:
            print(f"  {ps[0]['slug']}: {', '.join(pend)} (fica em pendentes)")
            continue
        _, dados, _ = _req(ps[0]["video_url"], timeout=600)
        nova = PASTA_ENVIADOS + os.path.basename(chave)
        r2_sobe(dados, nova)
        r2_apaga(chave)
        for p, st in sts:
            p.update({"r2_chave": nova, "video_url": f"{CF_PUBLICO}/{nova}", "enviado_em": st.get("sentAt"),
                      "link": st.get("externalLink")})
        mudou = True
        print(f"  {ps[0]['slug']}: enviado -> {nova}")
    if mudou:
        grava_publicados(pub)


def cmd_publica(a, rot):
    slug = rot["slug"]
    pub = le_publicados()
    redes = [r.strip() for r in a.redes.split(",") if r.strip()]
    for r in redes:
        if r not in REDES:
            sys.exit(f"[publicar] rede desconhecida {r!r}: use {', '.join(REDES)}")
    feitas = {p["rede"]: p for p in pub if p["slug"] == slug}
    redes = [r for r in redes if r not in feitas]
    for r in set(a.redes.split(",")) - set(redes):
        if r in feitas:
            print(f"[publicar] {slug} já foi enviado ao {r} ({feitas[r]['quando']}, post {feitas[r]['post_id']}): pulo")
    if not redes:
        sys.exit(f"[publicar] nada a fazer para {slug}")
    ref = feitas.get(REDE)                    # TikTok já agendado: o Instagram usa o MESMO horário, vídeo e capa
    if ref:                                   # as travas e os analistas já passaram quando o TikTok foi agendado
        legenda, capa_ms = rot["legenda"].strip(), ref["capa_ms"]
    else:
        mp4 = os.path.join(RAIZ, "saida", "luz", slug + ".mp4")
        analise, legenda_arq = mp4[:-4] + "_analise.txt", mp4[:-4] + "_legenda.txt"
        rend_arq = os.path.join(RAIZ, ".cache", "luz", slug, "render.json")
        for arq in (mp4, analise, legenda_arq, rend_arq):
            if not os.path.exists(arq):
                sys.exit(f"[publicar] falta {arq}: gere o vídeo antes")
        if "APROVADO nos automáticos" not in open(analise, encoding="utf-8").read():
            sys.exit("[publicar] o vídeo não está APROVADO nos analistas automáticos")
        if os.path.getmtime(analise) < os.path.getmtime(mp4) - 5:
            sys.exit("[publicar] a análise automática é mais velha que o vídeo: rode o gerador de novo")
        falta = set(ANALISTAS) - {x.strip() for x in a.aprovados.split(",") if x.strip()}
        if falta:
            sys.exit(f"[publicar] faltam analistas Claude APROVADO: {', '.join(sorted(falta))}")
        legenda = open(legenda_arq, encoding="utf-8").read().strip()
        capa_ms = int(round(json.load(open(rend_arq))["capa_t"] * 1000))

    org = organizacao()
    canais = {r: canal_da_rede(org, r) for r in redes}
    if ref and ref.get("agendado_para") and not a.agora and not a.quando:
        quando = _data(ref["agendado_para"])
        if quando < dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
            sys.exit(f"[publicar] o horário do TikTok ({quando.astimezone(BRT):%d/%m %H:%M}) já passou ou está perto demais; "
                     "use --quando ou --agora")
        modo = "customScheduled"
        print(f"[agenda] mesmo horário do TikTok: {quando.astimezone(BRT):%a %d/%m %H:%M} (Brasília)")
    elif a.agora:
        modo, quando = "shareNow", None
    elif a.quando:
        quando = dt.datetime.fromisoformat(a.quando)
        quando = quando.replace(tzinfo=BRT) if quando.tzinfo is None else quando
        if quando < dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
            sys.exit(f"[publicar] {quando} já passou ou está perto demais")
        modo = "customScheduled"
    else:
        quando, fila, ultimo = proximo_livre(org, canal_tiktok(org)["id"])
        modo = "customScheduled"
        print(f"[agenda] agora {dt.datetime.now(BRT):%d/%m %H:%M}; último agendado: "
              f"{ultimo.astimezone(BRT).strftime('%d/%m %H:%M') if ultimo else 'nenhum'} ({len(fila)} na fila) "
              f"-> {quando:%a %d/%m %H:%M} (Brasília)")

    chave = (ref or {}).get("r2_chave") or PASTA_PENDENTES + slug + ".mp4"
    url = f"{CF_PUBLICO}/{chave}" if ref else r2_sobe(open(mp4, "rb").read(), chave)
    print(f"[r2] vídeo no ar: {url}")
    for rede in redes:
        entrada = {
            "channelId": canais[rede]["id"], "text": legenda, "mode": modo, "schedulingType": "automatic",
            "needsApproval": False, "source": "luz_da_palavra",
            "assets": [{"video": {"url": url, "metadata": {"thumbnailOffset": capa_ms}}}],
            "metadata": metadados(rede),
        }
        if quando:
            entrada["dueAt"] = quando.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
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
            print(f"[buffer] post no {rede} recusado ({r['__typename']}): {r.get('message')}  (vídeo em {chave})")
            continue
        post = r["post"]
        due = _data(post.get("dueAt"))
        print(f"[buffer] {rede}: post {post['id']} · {post['status']} · {modo}"
              + (f" · {due.astimezone(BRT):%a %d/%m %H:%M} (Brasília)" if due else ""))
        pub.append({"slug": slug, "rede": rede, "canal": canais[rede]["name"], "post_id": post["id"], "modo": modo,
                    "quando": time.strftime("%Y-%m-%d %H:%M"), "agendado_para": post.get("dueAt"), "video_url": url,
                    "r2_chave": chave, "capa_ms": capa_ms, "ia_gerado": IA_GERADO, "legenda_linha1": legenda.splitlines()[0]})
        grava_publicados(pub)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro", nargs="?")
    ap.add_argument("--aprovados", default="", help="os 5 analistas Claude com APROVADO: " + ",".join(ANALISTAS))
    ap.add_argument("--agora", action="store_true", help="publica já, em vez do próximo horário livre")
    ap.add_argument("--quando", help="data/hora (Brasília se sem fuso), ex.: 2026-11-03T20:30")
    ap.add_argument("--redes", default=",".join(REDES_PADRAO), help="redes: tiktok,instagram (padrão: só tiktok; instagram só se pedido)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--fila", action="store_true")
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--arruma", action="store_true")
    a = ap.parse_args()
    carrega_env()
    if a.fila:
        return cmd_fila()
    if a.lista:
        return cmd_lista()
    if a.arruma:
        return cmd_arruma()
    if not a.roteiro:
        ap.error("informe o roteiro")
    rot = json.load(open(a.roteiro, encoding="utf-8"))
    if a.status:
        feitos = [p for p in le_publicados() if p["slug"] == rot["slug"]]
        if not feitos:
            sys.exit(f"[publicar] {rot['slug']} ainda não foi enviado")
        print(json.dumps(status(feitos[-1]["post_id"]), ensure_ascii=False, indent=1))
        return
    cmd_publica(a, rot)


if __name__ == "__main__":
    main()
