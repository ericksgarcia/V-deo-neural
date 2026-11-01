"""Mocap BVH -> esqueleto 2D (ideia do Meta AnimatedDrawings, reescrita: casamento de orientação dos segmentos + IK dos pés).

Fluxo: lê o BVH, calcula as posições 3D de cada junta (FK), projeta num plano de vista (lado), e para cada osso 2D casa a direção
do segmento correspondente ("orientation matching"). Pés: alvo de IK relativo ao quadril, na escala do personagem, com o chão
fixo. Resultado: `ClipeBVH` (compatível com `animacao.Maquina`), sem animar à mão. Qualquer BVH com os nomes do MAPA (ou o seu mapa) serve:
CMU, Mixamo-BVH, rokoko, os de `mocap/` gerados por `gerar_bvh.py`.
"""
import math, os, sys
import numpy as np
from scipy.ndimage import gaussian_filter1d
sys.path.insert(0, os.path.dirname(__file__))
from animacao import Clipe, Pose


# ------------------------------------------------------------------ leitura
class BVH:
    def __init__(s, caminho):
        s.nomes, s.pai, s.off, s.canais = [], [], [], []
        s.fps = 30.0; s.n = 0
        txt = open(caminho).read().split()
        i = 0; pilha = []
        def novo(nome, pai, canais=()):
            s.nomes.append(nome); s.pai.append(pai); s.off.append(np.zeros(3)); s.canais.append(list(canais)); return len(s.nomes) - 1
        atual = None
        while i < len(txt):
            w = txt[i]
            if w in ("ROOT", "JOINT"):
                atual = novo(txt[i + 1], pilha[-1] if pilha else -1); i += 2
            elif w == "End":
                atual = novo(s.nomes[pilha[-1]] + "_End", pilha[-1]); i += 2
            elif w == "{": pilha.append(atual); i += 1
            elif w == "}": pilha.pop(); i += 1
            elif w == "OFFSET":
                s.off[pilha[-1]] = np.array([float(x) for x in txt[i + 1:i + 4]]); i += 4
            elif w == "CHANNELS":
                k = int(txt[i + 1]); s.canais[pilha[-1]] = txt[i + 2:i + 2 + k]; i += 2 + k
            elif w == "MOTION":
                s.n = int(txt[i + 2]); s.fps = 1.0 / float(txt[i + 5]); i += 6
                dados = np.array(txt[i:i + s.n * sum(len(c) for c in s.canais)], float)
                s.dados = dados.reshape(s.n, -1); break
            else: i += 1
        s.idx = {n: k for k, n in enumerate(s.nomes)}
        s.pos = s._fk()
        s.rest = s._repouso()

    @staticmethod
    def _rot(eixo, a):
        c, sn = np.cos(a), np.sin(a); z, u = np.zeros_like(a), np.ones_like(a)
        if eixo == "X": m = [[u, z, z], [z, c, -sn], [z, sn, c]]
        elif eixo == "Y": m = [[c, z, sn], [z, u, z], [-sn, z, c]]
        else: m = [[c, -sn, z], [sn, c, z], [z, z, u]]
        return np.array(m).transpose(2, 0, 1)            # (n,3,3)

    def _fk(s):
        n = s.n; Rw = [None] * len(s.nomes); P = np.zeros((n, len(s.nomes), 3)); col = 0
        for j, nome in enumerate(s.nomes):
            ch = s.canais[j]; loc = np.tile(np.eye(3), (n, 1, 1)); tr = np.tile(s.off[j], (n, 1))
            for k, c in enumerate(ch):
                v = s.dados[:, col + k]
                if c.endswith("position"): tr[:, "XYZ".index(c[0])] += v
                else: loc = loc @ s._rot(c[0], np.deg2rad(v))
            col += len(ch)
            if s.pai[j] < 0: Rw[j] = loc; P[:, j] = tr
            else:
                p = s.pai[j]; Rw[j] = Rw[p] @ loc; P[:, j] = P[:, p] + np.einsum("nij,nj->ni", Rw[p], tr)
        return P

    def _repouso(s):
        P = np.zeros((len(s.nomes), 3))
        for j in range(len(s.nomes)):
            P[j] = s.off[j] + (P[s.pai[j]] if s.pai[j] >= 0 else 0)
        return {n: P[k] for k, n in enumerate(s.nomes)}

    def p(s, nome): return s.pos[:, s.idx[nome]]


# ------------------------------------------------------------------ mapa herói
MAPA_HEROI = {
    "ossos": {   # osso 2D: (junta de início, junta de fim) no BVH
        "espinha": ("Hips", "Chest"), "peito": ("Chest", "Neck"), "cabeca": ("Neck", "Head_End"),
        "bl_sup": ("LeftArm", "LeftForeArm"), "bl_ant": ("LeftForeArm", "LeftHand"), "bl_mao": ("LeftHand", "LeftHand_End"),
        "br_sup": ("RightArm", "RightForeArm"), "br_ant": ("RightForeArm", "RightHand"), "br_mao": ("RightHand", "RightHand_End"),
    },
    "pernas": {"lb": ("LeftUpLeg", "LeftLeg", "LeftFoot", "LeftFoot_End"), "lf": ("RightUpLeg", "RightLeg", "RightFoot", "RightFoot_End")},
    "chao_y": {"lb": 1778.0, "lf": 1752.0}, "centro_x": 1043.0, "perna_arte": 678.0,
    "frente": -1,      # o herói anda para a ESQUERDA da tela
}


class ClipeBVH(Clipe):
    """Pré-computa os ângulos/pés dos quadros e amostra por tempo (com interpolação). `ossos`: subconjunto (ex.: só braço) ou None = todos."""
    def __init__(s, caminho, esq, mapa=MAPA_HEROI, ossos=None, pes=True, loop=True, ao_terminar=None, vel_x=1.0,
                 ini=0.0, fim=None, suavizar=1.1, tempo=1.0, relativo=True):
        s.bvh = BVH(caminho); s.loop, s.ao_terminar, s.t, s.vel_x, s.tempo = loop, ao_terminar, 0.0, vel_x, tempo
        b = s.bvh; f0 = int(ini * b.fps); f1 = b.n if fim is None else int(fim * b.fps)
        sl = slice(f0, f1); n = f1 - f0
        s.dur = n / b.fps / tempo; s.fps = b.fps
        # tela: x = frente * Z (frente=-1: o personagem olha para a esquerda), y = -Y
        P2 = lambda nome: np.c_[mapa["frente"] * b.p(nome)[sl][:, 2], -b.p(nome)[sl][:, 1]]
        info = {o.nome: (o.pai.nome if o.pai else None, o.ang) for o in esq.ossos}
        ordem = [o.nome for o in esq.ossos]
        quer = set(ossos) if ossos else set(mapa["ossos"])
        ang = {}
        for osso, (a, c) in mapa["ossos"].items():
            if osso not in quer: continue
            v = P2(c) - P2(a); L3 = np.linalg.norm(b.p(c)[sl] - b.p(a)[sl], axis=1); L2 = np.linalg.norm(v, axis=1)
            th = np.unwrap(np.arctan2(v[:, 1], v[:, 0]))
            ruim = L2 < 0.18 * L3.max()                       # segmento apontando para a câmera: ângulo instável -> segura o anterior
            for k in range(1, n):
                if ruim[k]: th[k] = th[k - 1]
            th = gaussian_filter1d(th, suavizar, mode="nearest") if suavizar else th
            if relativo:   # repouso do BVH (rotações zero, só offsets) <-> repouso da arte: a pose neutra do BVH vira a pose do desenho
                r = (b.rest[c] - b.rest[a]) * np.array([1.0, 1.0, 1.0]); rv = np.array([mapa["frente"] * r[2], -r[1]])
                th = th - math.atan2(rv[1], rv[0]) + info[osso][1] + (0.0)
            ang[osso] = th
        rot = {}
        acc = {}
        for k, osso in enumerate(ordem):
            pai = info[osso][0]; ap = acc.get(pai, np.zeros(n)) if pai else np.zeros(n)
            if osso in ang:
                acc[osso] = ang[osso] - info[osso][1]; rot[osso] = acc[osso] - ap
            else:
                acc[osso] = ap
        s.rot = rot
        # tronco: pescoço compensa um pouco a inclinação (como no andar procedural)
        if "pescoco" not in rot and "espinha" in rot and "peito" in rot and "cabeca" in rot:
            s.rot["pescoco"] = -0.25 * (rot["espinha"] + rot["peito"])
        s.pes = {}; s.tilt = {}; s.root_y = np.zeros(n)
        if pes:
            q = [b.p(j)[sl] for j in ("Hips",)][0]
            cm = {l: b.p(mapa["pernas"][l][0])[sl] for l in mapa["pernas"]}
            comp = np.mean([np.linalg.norm(b.p(v[0])[sl] - b.p(v[1])[sl], axis=1).mean() + np.linalg.norm(b.p(v[1])[sl] - b.p(v[2])[sl], axis=1).mean()
                            for v in mapa["pernas"].values()])
            esc = mapa["perna_arte"] / comp; s.escala = esc
            hip_ref = np.median(q[:, 1]); pe_min = min(b.p(v[2])[sl][:, 1].min() for v in mapa["pernas"].values())
            s.root_y = -(q[:, 1] - hip_ref) * esc
            for l, v in mapa["pernas"].items():
                f = b.p(v[2])[sl]; dz = f[:, 2] - q[:, 2]
                x = mapa["centro_x"] + mapa["frente"] * dz * esc
                y = mapa["chao_y"][l] - (f[:, 1] - pe_min) * esc
                s.pes[l] = np.c_[x, y]
                d = P2(v[3]) - P2(v[2])
                s.tilt[l] = np.unwrap(np.arctan2(d[:, 1], d[:, 0])) - (math.pi if mapa["frente"] < 0 else 0.0)
            # velocidade do chão: o pé mais baixo anda para trás relativo ao quadril
            vel = []
            for k in range(1, n):
                l = max(mapa["pernas"], key=lambda l: s.pes[l][k, 1])      # y maior = mais baixo
                vel.append(abs(s.pes[l][k, 0] - s.pes[l][k - 1, 0]) * b.fps)
            s.vel_chao = float(np.median(vel)) * tempo if vel else 0.0
        s.nq = n

    def pose(s):
        P = Pose()
        t = s.t * s.tempo
        x = (t % (s.nq / s.fps)) if s.loop else min(t, (s.nq - 1) / s.fps)
        f = x * s.fps; i0 = int(math.floor(f)) % s.nq; i1 = (i0 + 1) % s.nq if s.loop else min(i0 + 1, s.nq - 1); w = f - math.floor(f)
        L = lambda a: a[i0] * (1 - w) + a[i1] * w
        for o, a in s.rot.items(): P.rot[o] = float(L(a))
        if s.pes:
            P.pos["root"] = (0.0, float(L(s.root_y)) + 6.0)
            for l in s.pes: P.pes[l] = tuple(L(s.pes[l])); P.tilt[l] = float(L(s.tilt[l]))
        return P
