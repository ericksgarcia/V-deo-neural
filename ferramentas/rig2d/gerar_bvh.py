"""Gera mocap BVH procedural (andar, acenar, apontar, pensar, pular) em `mocap/`, só para ter uma biblioteca de partida
sem depender de download. Troque/adicione BVHs reais (CMU, Mixamo, rokoko) com os mesmos nomes de junta: o retarget é o mesmo.
Convenção: Y para cima, Z para frente (o personagem olha para +Z). Rotação X negativa = membro para frente."""
import os, math, numpy as np

DIR = os.path.join(os.path.dirname(__file__), "mocap")
FPS = 30

# (nome, pai, offset) — unidades em cm; pontas "End" não têm canais
ESQ = [
    ("Hips", None, (0, 100, 0)), ("Spine", "Hips", (0, 12, 0)), ("Chest", "Spine", (0, 18, 0)), ("Neck", "Chest", (0, 26, 0)),
    ("Head", "Neck", (0, 10, 0)),
    ("LeftArm", "Chest", (9, 20, 0)), ("LeftForeArm", "LeftArm", (0, -28, 0)), ("LeftHand", "LeftForeArm", (0, -25, 0)),
    ("RightArm", "Chest", (-9, 20, 0)), ("RightForeArm", "RightArm", (0, -28, 0)), ("RightHand", "RightForeArm", (0, -25, 0)),
    ("LeftUpLeg", "Hips", (8, -5, 0)), ("LeftLeg", "LeftUpLeg", (0, -44, 0)), ("LeftFoot", "LeftLeg", (0, -42, 0)),
    ("RightUpLeg", "Hips", (-8, -5, 0)), ("RightLeg", "RightUpLeg", (0, -44, 0)), ("RightFoot", "RightLeg", (0, -42, 0)),
]
PONTAS = {"Head": (0, 18, 0), "LeftHand": (0, -9, 0), "RightHand": (0, -9, 0), "LeftFoot": (0, -5, 14), "RightFoot": (0, -5, 14)}
JUNTAS = [n for n, _, _ in ESQ]


def escreve(nome, quadros):
    """quadros: lista de dict {junta: ângulo X (rad), 'y': altura do quadril (cm), 'z': avanço (cm)}"""
    filhos = {}
    for n, p, o in ESQ: filhos.setdefault(p, []).append((n, o))
    L = ["HIERARCHY"]
    def junta(n, o, nivel):
        ind = "  " * nivel
        L.append(f"{ind}{'ROOT' if nivel == 0 else 'JOINT'} {n}"); L.append(ind + "{"); L.append(f"{ind}  OFFSET {o[0]} {o[1]} {o[2]}")
        L.append(f"{ind}  CHANNELS {6 if nivel == 0 else 3} " + ("Xposition Yposition Zposition " if nivel == 0 else "") + "Zrotation Xrotation Yrotation")
        for f, fo in filhos.get(n, []): junta(f, fo, nivel + 1)
        if n in PONTAS:
            e = PONTAS[n]; L.append(f"{ind}  End Site"); L.append(ind + "  {"); L.append(f"{ind}    OFFSET {e[0]} {e[1]} {e[2]}"); L.append(ind + "  }")
        L.append(ind + "}")
    junta("Hips", (0, 100, 0), 0)
    L += ["MOTION", f"Frames: {len(quadros)}", f"Frame Time: {1 / FPS:.6f}"]
    for q in quadros:
        v = [0.0, q.get("y", 100.0), q.get("z", 0.0)]
        for n in JUNTAS: v += [0.0, math.degrees(q.get(n, 0.0)), 0.0]     # Z, X, Y
        L.append(" ".join(f"{x:.4f}" for x in v))
    os.makedirs(DIR, exist_ok=True)
    open(os.path.join(DIR, nome + ".bvh"), "w").write("\n".join(L) + "\n")


def suave(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def por_chaves(chaves, dur, ease=suave):
    """chaves: [(t, {canal: valor})], interpola cada canal com ease entre chaves; canal ausente mantém."""
    qs = []
    canais = {c for _, d in chaves for c in d}
    for i in range(int(dur * FPS)):
        t = i / FPS; q = {}
        for c in canais:
            tr = [(tt, d[c]) for tt, d in chaves if c in d]
            v = tr[0][1]
            if t >= tr[-1][0]: v = tr[-1][1]
            else:
                for (t0, v0), (t1, v1) in zip(tr, tr[1:]):
                    if t0 <= t <= t1: v = v0 + (v1 - v0) * ease((t - t0) / (t1 - t0)); break
            q[c] = v
        qs.append(q)
    return qs


def andar():
    qs = []
    A = 0.30
    for i in range(FPS):
        w = 2 * math.pi * i / FPS; q = {}
        for lado, ph in (("Left", 0.0), ("Right", math.pi)):
            a = -A * math.sin(w + ph)                                 # coxa (negativo = para frente)
            sw = max(0.0, math.cos(w + ph + 0.35))                    # fase de balanço
            k = 0.12 + 0.95 * sw ** 1.3                               # joelho dobra no balanço
            q[lado + "UpLeg"] = a; q[lado + "Leg"] = k
            q[lado + "Foot"] = -(a + k) + 0.18 * math.cos(w + ph) * 0.0 - 0.10 * max(0.0, -math.sin(w + ph))
            q[lado + "Arm"] = 0.5 * A * math.sin(w + ph)              # braço oposto à perna
            q[lado + "ForeArm"] = -0.35 - 0.2 * math.sin(w + ph)
        q["Spine"] = 0.02 * math.sin(w); q["Chest"] = -0.02 * math.sin(w + 0.5); q["Head"] = 0.0
        q["y"] = 100 - 2.0 * (1 - math.cos(2 * w)) / 2; q["z"] = 130.0 * i / FPS
        qs.append(q)
    return qs


def acenar():
    # braço esquerdo sobe para frente/alto, mão balança 3x, desce
    ch = [(0.0, {"LeftArm": 0.0, "LeftForeArm": -0.3, "Head": 0.0, "Spine": 0.0}),
          (0.2, {"LeftArm": 0.18, "LeftForeArm": -0.1}), (0.8, {"LeftArm": -2.55, "LeftForeArm": -0.15, "Head": -0.05, "Spine": 0.04})]
    t = 0.8
    for i in range(3):
        ch += [(t + 0.2, {"LeftForeArm": -0.75}), (t + 0.4, {"LeftForeArm": 0.25})]; t += 0.4
    ch += [(t + 0.3, {"LeftForeArm": -0.15}), (t + 1.0, {"LeftArm": 0.0, "LeftForeArm": -0.3, "Head": 0.0, "Spine": 0.0})]
    return por_chaves(ch, t + 1.1)


def apontar():
    ch = [(0.0, {"LeftArm": 0.0, "LeftForeArm": -0.3, "Spine": 0.0, "Head": 0.0}), (0.25, {"LeftArm": 0.12}),
          (0.75, {"LeftArm": -1.45, "LeftForeArm": -0.05, "Spine": 0.05, "Head": -0.07}), (1.8, {"LeftArm": -1.5, "LeftForeArm": -0.02}),
          (2.5, {"LeftArm": 0.0, "LeftForeArm": -0.3, "Spine": 0.0, "Head": 0.0})]
    return por_chaves(ch, 2.5)


def pensar():
    # mão no queixo: braço dobrado para cima, cabeça levemente baixa, balanço sutil do peso
    ch = [(0.0, {"LeftArm": 0.0, "LeftForeArm": -0.3, "Head": 0.0}), (0.8, {"LeftArm": -0.75, "LeftForeArm": -2.05, "Head": 0.09, "Chest": 0.03}),
          (2.2, {"LeftArm": -0.78, "LeftForeArm": -2.1, "Head": 0.12}), (3.0, {"LeftArm": 0.0, "LeftForeArm": -0.3, "Head": 0.0, "Chest": 0.0})]
    return por_chaves(ch, 3.0)


def pular():
    base = {"LeftUpLeg": 0, "RightUpLeg": 0, "LeftLeg": 0, "RightLeg": 0, "LeftFoot": 0, "RightFoot": 0, "LeftArm": 0, "RightArm": 0, "y": 100}
    agach = {"LeftUpLeg": -0.95, "RightUpLeg": -0.95, "LeftLeg": 1.7, "RightLeg": 1.7, "LeftFoot": -0.75, "RightFoot": -0.75, "LeftArm": 0.55, "RightArm": 0.55,
             "Spine": 0.12, "y": 72}
    ar = {"LeftUpLeg": -0.35, "RightUpLeg": -0.35, "LeftLeg": 0.9, "RightLeg": 0.9, "LeftFoot": -0.45, "RightFoot": -0.45, "LeftArm": -1.8, "RightArm": -1.8,
          "Spine": -0.04, "y": 128}
    ch = [(0.0, base), (0.45, agach), (0.62, {"LeftUpLeg": 0.0, "RightUpLeg": 0.0, "LeftLeg": 0.0, "RightLeg": 0.0, "LeftFoot": 0.0, "RightFoot": 0.0, "LeftArm": -1.0,
                                             "RightArm": -1.0, "Spine": -0.06, "y": 104}), (0.85, ar), (1.15, ar),
          (1.4, {**agach, "y": 80, "LeftArm": 0.2, "RightArm": 0.2}), (1.9, {**base, "Spine": 0.0})]
    return por_chaves(ch, 1.9, ease=suave)


def main():
    for n, f in (("andar", andar), ("acenar", acenar), ("apontar", apontar), ("pensar", pensar), ("pular", pular)):
        escreve(n, f()); print("mocap/%s.bvh" % n)


if __name__ == "__main__": main()
