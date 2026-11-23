"""Audio de la historia: canción + efectos de sonido sincronizados, master a -14 LUFS.
Uso: python3 audio.py <carpeta_trabajo> <video_musica.mp4|none> <salida.wav>
"""
import sys, subprocess, wave
import numpy as np

WORK, MUSIC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
SR = 44100
TOTAL = 28.4
B = 60 / 117.45; O = 0.43
def beat(k): return O + k * B
STARTS = [beat(4 + 8 * i) for i in range(4)]
T_TEASE, T_JOYA, T_END = beat(36), beat(39), beat(47)
rng = np.random.default_rng(7)
N = int(TOTAL * SR)

def t(d): return np.arange(int(d * SR)) / SR

def whoosh(d=0.45, f0=300, f1=4000):
    n = rng.standard_normal(int(d * SR))
    # filtro pasa-banda que barre (aproximado con un filtro de un polo variable)
    x = t(d); fc = f0 * (f1 / f0) ** (x / d)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(n); lp = 0; lp2 = 0
    for i in range(len(n)):
        lp = (1 - a[i]) * n[i] + a[i] * lp
        lp2 = (1 - a[i]) * lp + a[i] * lp2
        y[i] = lp - lp2 * 0.6
    env = np.sin(np.pi * np.clip(x / d, 0, 1)) ** 1.5
    return y * env / (np.abs(y).max() + 1e-9) * 0.9

def tick(f=1500, d=0.07):
    x = t(d)
    return (np.sin(2 * np.pi * f * x) * 0.7 + rng.standard_normal(len(x)) * 0.15) * np.exp(-x * 70)

def ding(base=1318.5, d=1.4, big=False):
    x = t(d); y = np.zeros_like(x)
    for m, a in ((1, 1), (2.0, 0.45), (3.01, 0.25), (4.2, 0.12)):
        y += a * np.sin(2 * np.pi * base * m * x) * np.exp(-x * (3.0 + m))
    if big:
        y += 0.6 * np.sin(2 * np.pi * base * 1.5 * x) * np.exp(-x * 2.5)
    return y / np.abs(y).max() * 0.8

def pop(d=0.09):
    x = t(d); f = 350 + 900 * x / d
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 40) * 0.9

def shimmer(d=1.1):
    x = t(d); y = np.zeros_like(x)
    for f in (2093, 2637, 3136, 3951, 4186):
        y += np.sin(2 * np.pi * f * x + rng.uniform(0, 6)) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(5, 11) * x))
    env = np.clip(x / (d * 0.7), 0, 1) * np.clip((d - x) / (d * 0.3), 0, 1)
    return y / np.abs(y).max() * env * 0.35

fx = np.zeros(N)
def add(sig, at, gain):
    i = int(at * SR); j = min(N, i + len(sig))
    if i < N:
        fx[i:j] += sig[:j - i] * gain

# gancho
add(whoosh(0.35, 500, 5000), 0.02, 0.35)
add(whoosh(0.35, 500, 5000), 0.52, 0.30)
add(pop(), 1.05, 0.6); add(whoosh(0.3, 200, 2500), 1.0, 0.35)
add(shimmer(0.6), 1.35, 0.6)
add(tick(2200, 0.05), 1.7, 0.4)
add(whoosh(0.4, 250, 6000), beat(4) - 0.2, 0.55)
# propiedades
for k, s in enumerate(STARTS + [T_JOYA]):
    last = k == 4
    if k > 0:
        add(whoosh(0.4, 250, 6000), s - 0.2, 0.55)
    for b in (1, 2, 3):
        add(tick(1500 if b < 3 else 1900), s + b * B, 0.55)
    add(ding(big=last), s + 4 * B, 0.55 if not last else 0.7)
    add(whoosh(0.25, 2000, 9000), s + 4 * B, 0.25)
# antesala (momento emocional): sin efectos
# cierre
add(shimmer(1.2), T_END + 0.15, 0.7)
add(ding(1760, 1.0), T_END + 1.0, 0.35)
for d_ in (1.45, 1.70, 1.95, 2.20):
    add(pop(), T_END + d_, 0.55)

if MUSIC != "none":
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", MUSIC, "-t", str(TOTAL), "-vn", "-ac", "2", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    m = np.frombuffer(raw, np.int16).astype(np.float64).reshape(-1, 2) / 32768
    m = np.pad(m, ((0, max(0, N - len(m))), (0, 0)))[:N]
    x = np.arange(N) / SR
    env = np.clip(x / 0.05, 0, 1) * np.clip((TOTAL - x) / 1.4, 0, 1)
    m *= env[:, None] * 0.8
else:
    m = np.zeros((N, 2))
mix = m + fx[:, None] * 0.6
mix /= max(1.0, np.abs(mix).max() / 0.95)
tmp = OUT + ".pre.wav"
with wave.open(tmp, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
# master -14 LUFS, -1 dBTP
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-af", "loudnorm=I=-14:TP=-1:LRA=11", "-ar", str(SR), OUT], check=True)
