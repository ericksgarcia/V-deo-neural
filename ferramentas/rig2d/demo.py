"""Demo do rig: caminha -> para -> gesticula e fala (boca sincronizada). Uso:
   python ferramentas/rig2d/demo.py saida.mp4 [--seg 9] [--audio fala.wav] [--ss 2] [--fps 30]"""
import sys, os, math, subprocess, argparse, wave
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import heroi
from motor import Camera

def envelope_audio(wav, fps, dur):
    """RMS por quadro (0..1) de um áudio qualquer (via ffmpeg) -> abertura da boca."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = int(16000 / fps); k = len(x) // n
    r = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1))
    r = r / (np.percentile(r, 95) + 1e-9)
    r = np.clip(r, 0, 1) ** 0.8
    out = np.zeros(int(dur * fps)); out[:min(len(out), len(r))] = r[:len(out)]
    # suaviza (fala não abre/fecha em 1 quadro)
    return np.convolve(out, [0.25, 0.5, 0.25], mode="same")

def envelope_sintetico(fps, dur, ini):
    t = np.arange(int(dur * fps)) / fps
    s = np.maximum(0, np.sin(2 * math.pi * 4.4 * t + 1.7 * np.sin(2 * math.pi * 0.8 * t))) ** 0.7
    s *= 0.55 + 0.45 * np.sin(2 * math.pi * 1.3 * t + 1.0)
    porta = 1 / (1 + np.exp(-8 * (np.sin(2 * math.pi * 0.33 * t) + 0.25)))
    return np.where(t > ini, s * porta, 0.0)

def fundo(W, H):
    y = np.linspace(0, 1, H)[:, None, None]
    topo = np.array([40, 22, 12], np.float32); meio = np.array([92, 52, 28], np.float32)  # BGR
    img = topo * (1 - y) + meio * y
    return np.repeat(img, W, axis=1).astype(np.float32)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("saida"); ap.add_argument("--seg", type=float, default=9.0)
    ap.add_argument("--audio"); ap.add_argument("--ss", type=int, default=2); ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    W, H, fps, dur = 1080, 1920, a.fps, a.seg
    ch = heroi.construir(); cam = Camera(0.8, -180, 130, ss=a.ss)
    nfr = int(dur * fps)
    env = envelope_audio(a.audio, fps, dur) if a.audio else envelope_sintetico(fps, dur, 3.6)
    bg0 = fundo(W, H)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17", "-preset", "medium", a.saida]
    if a.audio:
        cmd = cmd[:-1] + ["-i", a.audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-shortest", a.saida]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    fase = 0.0; solo = 0.0
    for i in range(nfr):
        t = i / fps
        # roteiro do demo: 0-3.0 s andando; 3.0-3.8 desacelera; depois parado, gesticulando e falando
        vel = 1.0 if t < 3.0 else max(0.0, 1.0 - (t - 3.0) / 0.9)
        # mantém o ritmo dos passos ao desacelerar
        fase += 2 * math.pi / 1.0 / fps * vel
        gesto = float(np.clip((t - 3.6) / 0.6, 0, 1)) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.45 * (t - 3.6)) ** 2) if t > 3.6 else 0.0
        fal = float(np.clip((t - 3.6) / 0.3, 0, 1))
        heroi.pose(ch, t, fase, vel, falando=fal, gesto=gesto)
        ch.params["olho"] = heroi.piscar(t)
        ch.params["boca"] = float(env[i]) if t > 3.4 else 0.0
        ch.params["boca_larg"] = 1.0 + 0.25 * math.sin(2 * math.pi * 2.1 * t)
        solo += 7.0 * 2.2 * vel * a.ss / a.ss     # rolagem do chão (px/quadro)
        fr = bg0.copy()
        # chão neon que rola para a direita (personagem caminha para a esquerda)
        gy = int(130 + 0.8 * 1905)
        cv2.rectangle(fr, (0, gy), (W, H), (70, 36, 20), -1)
        cv2.line(fr, (0, gy), (W, gy), (255, 220, 80), 3, cv2.LINE_AA)
        for k in range(-2, 14):
            x = int((k * 120 + solo) % (W + 240)) - 120
            cv2.line(fr, (x, gy), (int(540 + (x - 540) * 2.6), H), (170, 110, 30), 2, cv2.LINE_AA)
        # sombra suave sob os pés
        sh = np.zeros((H, W), np.float32)
        bob = abs(math.sin(fase)) * 6 * vel
        cv2.ellipse(sh, (int(540 + 10), gy + 18), (int(260 - bob), int(26 - bob * 0.3)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        sh = cv2.GaussianBlur(sh, (0, 0), 14)[..., None] * 0.55
        fr = fr * (1 - sh)
        c = ch.render(cam, W, H)
        al = c[..., 3:4]
        fr = c[..., :3] * 255 + fr * (1 - al)
        pr.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if i % 30 == 0: print(f"  {i}/{nfr}", file=sys.stderr, flush=True)
    pr.stdin.close(); pr.wait()

if __name__ == "__main__":
    main()
