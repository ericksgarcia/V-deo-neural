"""Motor de vídeo genérico: lista de cenas + adaptador -> MP4 vertical narrado.

Uma cena é um dicionário. Campos comuns:
  tipo      "ao_vivo" (geração inteira), "replay" (um lance, câmera lenta), "grafico", "barras", "final"
  fala      texto narrado (vira legenda palavra a palavra)
  ger       geração mostrada (0-based)
  foco      índice do lance/indivíduo no replay
  grupo     cenas com o mesmo grupo continuam o mesmo trecho da simulação
  vel       velocidade fixa (s de simulação por s de vídeo); se omitida, o motor ajusta
  pausa     segundos de silêncio depois da fala (suspense)
  marcas    (IGNORADO desde out/2026: o telestrador saía no lugar errado e foi desligado)
  cartao    {"numero", "rotulo", "nome", "stat", "cor"}
  log       linhas para o console: [(texto, cor)]
  destaques {palavra: cor} para colorir palavras da legenda
  teste     True na cena do teste final (casa "TESTE" da trilha); sem ele, vale a 1ª cena "barras"

Retenção automática (layout v3): cada <long pause> da fala vira uma REVELAÇÃO (a música some, sobe um riser,
e a palavra seguinte entra com impacto + zoom na cena); cenas ao vivo têm um zoom lento contínuo; a trilha de
descobertas no topo mostra as casas ainda fechadas; telas de dados mostram a simulação ao fundo.
Campos de telas de dados: eras/serie/titulo (grafico), itens/destaque/titulo/sub (barras),
pergunta/opcoes (final).
"""
import json
import math
import os
import re
import subprocess
import time

import cairo
import numpy as np

from . import audio, fala
from .palco import arte as R, kit as K
from .palco.holo import Holo

FPS = 30
MIN_DUR = {"ao_vivo": 1.6, "replay": 2.0, "montagem": 2.4, "grafico": 2.4, "barras": 2.2, "final": 3.5}


class Video:
    def __init__(self, adaptador, cenas, info, voz="Achird", escala=1.0, narrar=True, cache=".cache/tts",
                 log=print, estilo=None, ritmo=4.0):
        self.A, self.cenas, self.info = adaptador, cenas, info
        self.voz, self.escala, self.narrar, self.cache, self.log = voz, escala, narrar, cache, log
        self.estilo, self.ritmo = estilo or info.get("estilo_voz"), ritmo
        for c in self.cenas:   # tags de pausa (<short pause>) vão só para a voz, nunca para a legenda
            if "<" in c["fala"]:
                c["fala_tts"] = c["fala"]
                c["fala"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c["fala"])).strip()
        self.fundo = K.Fundo()
        self.eventos = []

    # ------------------------------------------------------------------ preparo
    def prepara(self):
        textos = [c["fala"] for c in self.cenas]
        vozes, ouvidos = self._narracao(textos) if self.narrar else (None, None)
        t = 0.0
        self.relatorio_fala = []
        for k, c in enumerate(self.cenas):
            a = vozes[k] if vozes else None
            c["audio"] = a
            if a is not None:
                ws = ouvidos[k]
                dur_fala = len(a) / audio.SR
                ouvido = " ".join(w[2] for w in ws)
                nota = fala.confere(c["fala"], ouvido)
                self.relatorio_fala.append({"cena": k, "fala": c["fala"], "ouvido": ouvido, "semelhanca": round(nota, 3)})
                if nota < 0.85:
                    self.log(f"  [atenção] narração da cena {k} difere do roteiro ({nota:.0%}): '{ouvido}'")
            else:
                dur_fala = len(c["fala"].split()) / 2.8
                ws = []
            c["palavras"] = fala.alinha(c["fala"], audio.falavel(c["fala"]), ws, dur_fala)
            c["fala_dur"] = dur_fala
            c["dur"] = max(dur_fala + c.get("pausa", 0.22), MIN_DUR.get(c["tipo"], 2.0))
            c["ini"] = t
            t += c["dur"]
        self.dur = t + 0.5
        self._tempos()
        self._legendas()
        self._console()
        self._revelacoes()
        self._trilha()

    def _revelacoes(self):
        """Cada <long pause> = suspense: (início do silêncio, instante da revelação). A revelação é a palavra
        depois da pausa ou, se a pausa fecha a fala, o começo da cena seguinte (corte em suspense)."""
        self.revelacoes = []
        for k, c in enumerate(self.cenas):
            tts = c.get("fala_tts", "")
            pos = 0
            while "<long pause>" in tts[pos:]:
                j = tts.index("<long pause>", pos)
                pos = j + 1
                n = len(re.sub(r"<[^>]+>", " ", tts[:j]).split())
                ps = c["palavras"]
                base = c["ini"] + 0.05
                t0 = base + ps[n - 1][1] if 0 < n <= len(ps) else c["ini"]
                if n < len(ps):
                    t1 = base + ps[n][0]
                elif k + 1 < len(self.cenas):
                    t1 = self.cenas[k + 1]["ini"]
                else:
                    continue
                t1 = max(t1, t0 + 0.25)
                self.revelacoes.append((t0, t1))
                if c["tipo"] == "barras" and n < len(ps) and "revela" not in c:
                    c["revela"] = t1 - c["ini"]   # o destaque (o vencedor) só aparece quando a voz revela

    def _trilha(self):
        """Casas da trilha de descobertas: uma por cartão + o teste final."""
        pts = [(c["ini"], c["cartao"]["nome"], c["cartao"]["cor"], False) for c in self.cenas if c.get("cartao")]
        teste = next((c for c in self.cenas if c.get("teste")), None) or \
            next((c for c in self.cenas if c["tipo"] == "barras"), None)
        if teste is not None and pts:
            pts.append((teste["ini"], self.info.get("nome_teste", "TESTE FINAL"), "verde", True))
        self.pontos_trilha = pts

    def _zoom(self, c, t, tl):
        """Zoom da cena: lento e contínuo nas cenas ao vivo (nunca fica parada) + soco curto em cada revelação."""
        z = 1.0 + (0.06 * min(tl / max(c["dur"], 0.1), 1.0) if c["tipo"] == "ao_vivo" else 0.0)
        for _, t1 in getattr(self, "revelacoes", []):
            if 0 <= t - t1 < 0.6:
                u = (t - t1) / 0.6
                z += 0.09 * (1 - u) ** 2
        return z

    def _narracao(self, textos):
        """Voz do episódio inteiro com UMA requisição ao TTS (sem tentativas: cada chamada gasta cota).
        Depois, tudo é local: o Whisper confere cada fala e o motor só AVISA o que saiu torto."""
        vozes = audio.narra_lote(
            textos, self.cache, voz=self.voz, estilo=self.estilo, ritmo=self.ritmo,
            antes=[c.get("antes", "") for c in self.cenas],
            tts_textos=[c.get("fala_tts", c["fala"]) for c in self.cenas])
        if vozes is None:
            return None, None
        ouvidos = [fala.transcreve(fala.para16k(a, audio.SR), idioma="pt")[1] for a in vozes]
        notas = [fala.confere(tx, " ".join(w[2] for w in ws)) for tx, ws in zip(textos, ouvidos)]
        rit = audio.ritmo_das_falas(textos, vozes)
        self.log(f"  narração: pior fala {min(notas):.0%} (cena {int(np.argmin(notas))}), "
                 f"ritmo {min(rit):.1f}-{max(rit):.1f} palavras/s")
        return vozes, ouvidos

    def _tempos(self):
        """Converte tempo de vídeo em tempo de simulação para cada cena (com câmera lenta)."""
        grupos = {}
        for k, c in enumerate(self.cenas):
            grupos.setdefault(c.get("grupo", f"_{k}"), []).append(c)
        for cs in grupos.values():
            c0 = cs[0]
            if c0["tipo"] not in ("ao_vivo", "replay"):
                continue
            rod = self.A.rodada(c0["ger"])
            total = sum(c["dur"] for c in cs)
            if c0["tipo"] == "replay":
                D = self.A.duracao_foco(rod, c0["foco"])
                chaves = self.A.chaves_lento(rod, c0["foco"])
                mapa = _mapa_lento(D, chaves, total * 0.96, c0.get("lento", 0.7), inicio=c0.get("inicio", 0.0))
            else:
                D = rod.duracao
                vel = c0.get("vel") or float(np.clip(D / (0.9 * total), 0.6, 3.0))
                mapa = lambda tv, vel=vel: tv * vel
            off = 0.0
            for c in cs:
                c["mapa"], c["off"] = mapa, off
                off += c["dur"]

    def tempo_sim(self, c, tl):
        return float(c["mapa"](c["off"] + tl))

    def tempo_grupo(self, c, t):
        """Tempo desde o início do grupo de cenas (gráficos/barras não reanimam a cada cena)."""
        c0 = self._primeira_do_grupo(c)
        cs = [x for x in self.cenas if x is c0 or (c.get("grupo") and x.get("grupo") == c.get("grupo"))]
        return t - c0["ini"], sum(x["dur"] for x in cs)

    def _estado(self, c, tl):
        """(rodada, tempo de simulação, modo, foco) do que a cena mostra agora."""
        if c["tipo"] == "montagem":   # vários replays curtos em sequência, um a cada pedaço da cena
            clipes = c["clipes"]
            sd = c["dur"] / len(clipes)
            j = min(int(tl / sd), len(clipes) - 1)
            g, foco = clipes[j]
            rod = self.A.rodada(g)
            a, b = self.A.janela_lance(rod, foco)
            u = (tl - j * sd) / sd
            return rod, a + (b - a) * u, "replay", foco
        g = c.get("ger", self.A.total_ger - 1)
        rod = self.A.rodada(g)
        if c["tipo"] in ("ao_vivo", "replay"):
            return rod, self.tempo_sim(c, tl), c["tipo"], (c.get("foco") if c["tipo"] == "replay" else None)
        return rod, rod.duracao, c["tipo"], None

    def _legendas(self):
        blocos = []
        for c in self.cenas:
            ws = [(c["ini"] + 0.05 + a, c["ini"] + 0.05 + b, p) for a, b, p in c["palavras"]]
            for b in K.blocos_de_palavras(ws):
                blocos.append((b[0], min(b[1], c["ini"] + c["dur"]), b[2], c.get("destaques", {})))
        self.blocos = blocos

    def _console(self):
        self.linhas_log = []
        for c in self.cenas:
            for j, (s, cor) in enumerate(c.get("log", [])):
                self.linhas_log.append((c["ini"] + 0.3 + 0.55 * j, s, cor))   # (log fora da tela desde o layout v3)

    # ------------------------------------------------------------------ quadro
    def cena_em(self, t):
        for c in self.cenas:
            if c["ini"] <= t < c["ini"] + c["dur"]:
                return c
        return self.cenas[-1]

    def quadro(self, t, sons=False):
        sup = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(K.W * self.escala), int(K.H * self.escala))
        ctx = cairo.Context(sup)
        ctx.scale(self.escala, self.escala)
        ctx.set_source_surface(self.fundo.sup, 0, 0)
        ctx.paint()
        c = self.cena_em(t)
        tl = t - c["ini"]
        info = self.info
        K.cabecalho(ctx, info["marca"], self.A.experimento, self.A.titulo, t)
        rod, ts, modo, foco = self._estado(c, tl)
        sim = modo in ("ao_vivo", "replay")
        g = rod.g
        if c["tipo"] == "grafico":   # o contador acompanha a ponta da curva
            tg, dg = self.tempo_grupo(c, t)
            g = int((self.A.total_ger - 1) * min(tg / (dg * 0.6), 1))
        # fileira de cima
        K.contador_geracao(ctx, 30, K.TOPO[0], 330, K.TOPO[1], g + 1, self.A.total_ger, info["serie"],
                           info.get("marcos", []), info.get("serie_rotulo", ""))
        for j, (tit, rot, val, cor) in enumerate(self.A.medidores(self.A.rodada(g) if c["tipo"] == "grafico" else rod,
                                                                   ts, foco)[:2]):
            x = 375 + j * 345
            K.painel(ctx, x, K.TOPO[0], 330, K.TOPO[1], tit, c=cor, indice=2 + j)
            K.medidor_anel(ctx, x + 165, K.TOPO[0] + 80, 44, val, cor, rot)
        # cena
        ctx.save()
        K.recorte_cena(ctx)
        palco = None
        if sim:
            x0, y0, w0, h0 = K.CENA
            cam = self.A.camera(rod, ts, modo, foco)
            h = Holo(w0, h0, cam)
            self.A.desenha(h, rod, ts, modo, foco)
            cena_sup = h.finaliza(bloom=0.8)
            R.cromatica(cena_sup)
            R.varredura(h, t)
            z = self._zoom(c, t, tl)
            cx, cy = x0 + w0 / 2, y0 + h0 / 2
            ctx.save()
            ctx.translate(cx, cy)
            ctx.scale(z, z)
            ctx.translate(-cx, -cy)
            ctx.set_source_surface(cena_sup, x0, y0)
            ctx.paint()
            ctx.restore()
            palco = lambda p, h=h, x0=x0, y0=y0, z=z, cx=cx, cy=cy: tuple(
                (float(v) + o - m) * z + m for v, o, m in zip(h.tela(*p), (x0, y0), (cx, cy)))
        else:
            self._tela_dados(ctx, c, tl)
        for _, t1 in getattr(self, "revelacoes", []):   # clarão curto na revelação
            if 0 <= t - t1 < 0.25:
                x0, y0, w0, h0 = K.CENA
                K.cor(ctx, "branco", 0.22 * (1 - (t - t1) / 0.25))
                ctx.rectangle(x0, y0, w0, h0)
                ctx.fill()
        ctx.restore()
        vel = None
        if sim:
            dt = 0.05
            vel = (self._estado(c, tl + dt)[1] - ts) / dt
        if modo == "replay":
            rot_cam = f"◀◀ REPLAY · GER {rod.g + 1:03d}"
        elif modo == "ao_vivo":
            rot_cam = f"AO VIVO · GER {rod.g + 1:03d} · {self.info.get('rotulo_vivo', 'GERAÇÃO INTEIRA')}"
        else:
            rot_cam = "ANÁLISE"
        K.moldura_cena(ctx, t, rot_cam, vel if sim and vel > 0 else None)
        if modo == "replay":
            ini_clip = tl if c["tipo"] == "replay" else (tl % (c["dur"] / len(c["clipes"])))
            if c["tipo"] != "replay" or c is self._primeira_do_grupo(c):
                K.selo_replay(ctx, ini_clip)
            # telestrador (círculos/setas/rótulos de `marcas`) desligado a pedido do dono: o lugar e o instante
            # das marcas nem sempre batiam com a ação. `marcas` nos roteiros é ignorado.
        if c.get("titulo_gancho"):   # o título some quando entra o carimbo (não se sobrepõem)
            fim = c["carimbo"].get("em", 0.2) if c.get("carimbo") else None
            K.titulo_gancho(ctx, c["titulo_gancho"], tl if fim is None else max(tl, tl + 2.0 - fim))
        if c.get("carimbo"):
            k = c["carimbo"]
            K.carimbo(ctx, k["texto"], k["cor"], tl - k.get("em", 0.2), sub=k.get("sub"))
        if c.get("cartao"):
            k = c["cartao"]
            K.cartao_descoberta(ctx, tl, c["dur"], k["cor"], k["numero"], k["rotulo"], k["nome"], k["stat"])
            if sons and abs(tl) < 1 / FPS:
                self.eventos.append((t, "glitch", 1))
        if c.get("escolha"):
            k = c["escolha"]
            K.faixa_escolha(ctx, tl - k.get("em", 0.0), k["pergunta"], k["opcoes"])
        K.legenda(ctx, [(a, b, w) for a, b, w, _ in self.blocos], t,
                  next((d for a, b, w, d in self.blocos if a <= t < b), {}))
        K.trilha_descobertas(ctx, t, self.pontos_trilha if t > 2.0 else [])
        K.rodape(ctx, info.get("rodape", ""))
        K.scanlines(ctx, t)
        if sons and sim:
            r0, ts0, _, f0 = self._estado(c, max(tl - 1 / FPS, 0))
            if tl <= 0 or r0 is not rod or f0 != foco:
                ts0 = ts - 1 / FPS
            for te, tipo, inten in self.A.sons(rod, ts0, ts, modo, foco):
                self.eventos.append((t, tipo, inten))
        if t > self.dur - 0.4 and getattr(self, "primeiro", None) is not None:  # laço perfeito
            ctx.identity_matrix()
            ctx.set_source_surface(self.primeiro, 0, 0)
            ctx.paint_with_alpha(min((t - (self.dur - 0.4)) / 0.4, 1))
        return sup

    def _primeira_do_grupo(self, c):
        gr = c.get("grupo")
        if gr is None:
            return c
        return next(x for x in self.cenas if x.get("grupo") == gr)

    def _telestrador(self, ctx, palco, rod, c, ts, tl):
        if palco is None:
            return
        foco = c["foco"]
        for m in c.get("marcas", []):
            dura = m.get("dura", 0.7 if m["tipo"] == "seta" else 99)
            if ts < m["em"] or ts > m["em"] + dura:
                continue
            # progresso pelo tempo de vídeo desde que a marca começou (aprox. pela taxa local)
            prog = min((ts - m["em"]) / 0.25, 1.0)
            x0, y0, w0, h0 = K.CENA
            dentro = lambda q: (min(max(q[0], x0 + 60), x0 + w0 - 60), min(max(q[1], y0 + 120), y0 + h0 - 60))
            p = dentro(palco(self.A.ponto(rod, foco, m["alvo"], max(ts, m["em"]) if m.get("segue") else m["em"])))
            if m["tipo"] == "circulo":
                K.tele_circulo(ctx, p[0], p[1], m.get("rx", 95), m.get("ry", 115), prog)
            elif m["tipo"] == "seta":
                q = dentro(palco(self.A.ponto(rod, foco, m["ate"], m["em"])))
                K.tele_seta(ctx, p[0], p[1], q[0], q[1], prog, curva=m.get("curva", 0.2))
            if m.get("texto"):
                dx, dy = m.get("desloca", (0, -150))
                base = q if (m["tipo"] == "seta" and m.get("rotulo_no_fim")) else p
                bx = min(max(base[0] + dx, x0 + 170), x0 + w0 - 170)
                by = min(max(base[1] + dy, y0 + 150), y0 + h0 - 190)   # longe da legenda
                K.tele_rotulo(ctx, m["texto"], bx, by, min(prog * 1.5, 1))

    def _tela_dados(self, ctx, c, tl):
        x, y, w, h = K.CENA
        if c.get("ger") is not None:   # a simulação continua viva ao fundo (tela de dados nunca é tela parada)
            rod = self.A.rodada(c["ger"])
            ts = (tl * 1.0) % max(rod.duracao, 0.1)
            hb = Holo(w, h, self.A.camera(rod, ts, "ao_vivo", None))
            self.A.desenha(hb, rod, ts, "ao_vivo", None)
            ctx.set_source_surface(hb.finaliza(bloom=0.5), x, y)
            ctx.paint_with_alpha(0.7)
            ctx.set_source_rgba(0.01, 0.02, 0.035, 0.66)
        else:
            ctx.set_source_rgba(0.01, 0.02, 0.035, 0.94)
        ctx.paint()
        tg, dg = self.tempo_grupo(c, c["ini"] + tl)
        if c["tipo"] == "grafico":
            K.grafico_eras(ctx, K.CENA, c["serie"], self.A.total_ger, c.get("eras", []),
                           self.A.total_ger * min(tg / (dg * 0.6), 1), c["titulo"], c.get("rotulo_y", ""),
                           faixa_ref=c.get("faixa_ref"), final=c.get("final"))
        elif c["tipo"] == "barras":
            K.barras(ctx, K.CENA, c["itens"], c["titulo"], c.get("sub", ""), tg / 1.6,
                     c.get("destaque") if tl > c.get("revela", 0) else None,
                     oculta=c.get("destaque") if tl <= c.get("revela", 0) else None,
                     atual=c.get("atual") if tl > c.get("revela", 0) else None,
                     cor_destaque=c.get("cor_destaque", "vermelho"),
                     rotulo_destaque=c.get("rotulo_destaque", "◀ MELHOR"))
        elif c["tipo"] == "final":
            K.tela_final(ctx, K.CENA, tl, c["pergunta"], c["opcoes"])

    # ------------------------------------------------------------------ exportação
    def renderiza(self, saida, pacote=True):
        self.prepara()
        w, h = int(K.W * self.escala) // 2 * 2, int(K.H * self.escala) // 2 * 2
        os.makedirs(os.path.dirname(os.path.abspath(saida)) or ".", exist_ok=True)
        tmp_v = saida + ".video.mp4"
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{w}x{h}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                               "-pix_fmt", "yuv420p", tmp_v], stdin=subprocess.PIPE)
        self.primeiro = None
        self.primeiro = self.quadro(0.0)
        for c in self.cenas[1:]:
            self.eventos.append((c["ini"], "whoosh", 1))
        n = int(self.dur * FPS)
        ini = time.time()
        for f in range(n):
            sup = self.quadro(f / FPS, sons=True)
            buf = np.ndarray((sup.get_height(), sup.get_stride() // 4, 4), np.uint8, sup.get_data())
            ff.stdin.write(np.ascontiguousarray(buf[:h, :w]).tobytes())
            if f % 300 == 0:
                self.log(f"  quadro {f}/{n} ({time.time() - ini:.0f}s)")
        ff.stdin.close()
        ff.wait()
        falas = [(c["ini"] + 0.05, c["audio"]) for c in self.cenas if c["audio"] is not None]
        for t0, t1 in self.revelacoes:
            self.eventos += [(t0, "riser", t1 - t0), (t1, "impacto", 1)]
        amb = self.A.ambiente(self.dur)
        mix = audio.mixa(self.dur, falas, self.eventos, ambiente=amb, silencios=self.revelacoes)
        tmp_a = saida + ".audio.f32"
        mix.tofile(tmp_a)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp_v, "-f", "f32le", "-ar", str(audio.SR), "-ac", "2",
                        "-i", tmp_a, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags",
                        "+faststart", saida], check=True)
        os.remove(tmp_v)
        os.remove(tmp_a)
        if pacote:
            self.pacote(os.path.splitext(saida)[0] + "_analise")
        return saida

    def pacote(self, pasta):
        """Material para os analistas: roteiro com tempos, checagem da voz, quadros-chave."""
        os.makedirs(pasta, exist_ok=True)
        for velho in os.listdir(pasta):      # nada de quadros de renders anteriores no mosaico
            if velho.endswith((".png", ".jpg", ".md", ".json")):
                os.remove(os.path.join(pasta, velho))
        linhas = ["# Pacote de análise", "", f"duração: {self.dur:.1f}s · {len(self.cenas)} cenas", "",
                  "| # | início | dur | tipo | ger | fala |", "|---|---|---|---|---|---|"]
        for k, c in enumerate(self.cenas):
            linhas.append(f"| {k} | {c['ini']:.1f}s | {c['dur']:.1f}s | {c['tipo']} | {c.get('ger', '-')} | "
                          f"{c['fala']} |")
        if self.revelacoes:
            linhas += ["", "## Revelações (<long pause>: música some, riser, impacto + zoom)", ""]
            linhas += [f"- {t0:.1f}s → {t1:.1f}s" for t0, t1 in self.revelacoes]
        if self.relatorio_fala:
            linhas += ["", "## Voz x roteiro (Whisper)", ""]
            linhas += [f"- cena {r['cena']}: {r['semelhanca']:.0%} — ouvido: \"{r['ouvido']}\"" for r in self.relatorio_fala]
        with open(os.path.join(pasta, "roteiro.md"), "w") as f:
            f.write("\n".join(linhas) + "\n")
        dados = [{k: v for k, v in c.items() if k not in ("audio", "mapa", "palavras")} for c in self.cenas]
        with open(os.path.join(pasta, "roteiro.json"), "w") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
        # um quadro no meio e um no fim de cada cena + mosaico
        qs = []
        for k, c in enumerate(self.cenas):
            for nome, tt in (("a", c["ini"] + 0.35), ("b", c["ini"] + c["dur"] * 0.8)):
                arq = os.path.join(pasta, f"cena{k:02d}{nome}_{tt:05.1f}s.png")
                sup = self.quadro(tt)
                sup.write_to_png(arq)
                qs.append(arq)
        cols = 6
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", os.path.join(pasta, "cena*.png"),
                        "-filter_complex", f"scale=300:-1,tile={cols}x{math.ceil(len(qs) / cols)}:padding=4",
                        "-frames:v", "1", os.path.join(pasta, "mosaico.jpg")], check=False)


def _mapa_lento(D, chaves, total_video, forca=0.7, largura=0.28, inicio=0.0):
    """Função tempo_de_video -> tempo_de_simulação que desacelera perto das chaves.

    inicio: pula o começo do lance (s de simulação) para entrar direto na ação."""
    ts = np.linspace(min(inicio, D * 0.9), D, 600)
    taxa = np.ones_like(ts)
    for k in chaves:
        taxa = np.minimum(taxa, 1 - forca * np.exp(-((ts - k) ** 2) / (2 * largura ** 2)))
    custo = np.concatenate([[0], np.cumsum((1 / taxa[:-1]) * np.diff(ts))])  # tempo de vídeo a vel. 1
    fator = custo[-1] / total_video                                          # acelera o resto para caber
    tv = custo / fator
    return lambda t: np.interp(t, tv, ts, right=D)
