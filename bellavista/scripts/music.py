# Original score composed & synthesized in code for this production (no third-party samples).
# Usage: python3 music.py total_seconds out.wav
import numpy as np, sys, wave
SR = 48000
rng = np.random.default_rng(7)
TOTAL = float(sys.argv[1]); OUT = sys.argv[2]
N = int(TOTAL * SR) + SR * 2
L = np.zeros(N); R = np.zeros(N)

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)

def add(sig, t, pan=0.0, gain=1.0):
    i = int(t * SR); j = min(N, i + len(sig))
    if j <= i: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2); R[i:j] += s * np.sqrt((1 + pan) / 2)

def piano(m, dur, vel=0.6):
    f = mtof(m); n = int((dur + 2.5) * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    B = 0.0004
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + B * k * k)
        if fk > 16000: break
        dec = 1.2 + 0.9 * k + f / 400
        amp = (0.9 ** k) / k ** 0.6 * (1 + 0.3 * vel * (k > 2))
        s += amp * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t * dec / (1 + 1.5 * (1 - vel)))
    # damper release
    rel = np.ones(n); r0 = int(dur * SR)
    if r0 < n: rel[r0:] = np.exp(-(np.arange(n - r0) / SR) * 3.5)
    att = np.minimum(1, t / 0.004)
    ham = rng.normal(0, 1, n) * np.exp(-t * 90) * 0.05
    return (s * rel * att + ham) * vel * 0.22

def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); p = 0.0
    # vectorised one-pole via scipy-free cumulative approach (loop in chunks)
    import numpy as _n
    from numpy.lib.stride_tricks import sliding_window_view  # noqa
    for i in range(len(x)):
        p = (1 - a) * x[i] + a * p; y[i] = p
    return y

def lp_fast(x, fc):
    # FFT brickwall-ish smooth lowpass
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (fr / fc) ** 4)
    return np.fft.irfft(X, len(x))

def strings(m, dur, vel=0.5, att=1.2, rel=1.8, bright=2200):
    f = mtof(m); n = int((dur + rel) * SR); t = np.arange(n) / SR
    s = np.zeros(n)
    for d in (-6, -2, 2, 6):  # ensemble detune (cents)
        fd = f * 2 ** (d / 1200)
        vib = 1 + 0.003 * np.sin(2 * np.pi * (5 + rng.uniform(-.5, .5)) * t + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(fd * vib) / SR + rng.uniform(0, 6)
        saw = np.zeros(n)
        for k in range(1, 14):
            if f * k > 12000: break
            saw += np.sin(k * ph) / k
        s += saw
    s = lp_fast(s, bright)
    env = np.minimum(1, t / att)
    r0 = int(dur * SR); env[r0:] *= np.exp(-(np.arange(n - r0) / SR) * 4 / rel)
    return s * env * vel * 0.05

def reverb(x, secs=3.2, wet=0.35):
    n = int(secs * SR); t = np.arange(n) / SR
    ir = rng.normal(0, 1, n) * np.exp(-t * 6.9 / secs)
    ir = lp_fast(ir, 6000); ir[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
    ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return x * (1 - wet) + y * wet * 1.4

# ---------------- composition ----------------
# Key D major, 70 bpm. Progression (2 bars each chord = ~3.43 s per chord at 4/4? use 1 bar per chord)
BPM = 70; beat = 60 / BPM; bar = 4 * beat
# chords as (bass, [voicing])
I = (38, [62, 66, 69, 74])     # D
V6 = (37, [61, 64, 69, 73])    # A/C#
vi = (35, [59, 62, 66, 71])    # Bm
IV = (31, [59, 62, 67, 71])    # Gmaj7-ish
iii = (30, [57, 61, 66, 69])   # F#m
IVb = (31, [62, 67, 71, 74])
Vsus = (33, [62, 64, 69, 76])
prog = [I, V6, vi, IV, I, V6, IV, Vsus]
melA = [(0, 78), (1.5, 76), (2, 74), (3, 76)]
melB = [(0, 81), (1, 78), (2, 76), (3, 74)]

nbars = int(np.ceil(TOTAL / bar)) + 1
# section intensity curve by time (0..1): soft intro, progressive, emotional peak ~ bedroom, open terrace, finale
SECT = [float(v) for v in sys.argv[3].split(',')] if len(sys.argv) > 3 else [0, 12, 40, 55, 64]
def intensity(t):
    s0, s1, s2, s3, s4 = SECT
    if t < s1: return 0.25 + 0.15 * t / max(s1, 1)
    if t < s2: return 0.45 + 0.15 * (t - s1) / (s2 - s1)
    if t < s3: return 0.8
    if t < s4: return 0.7
    return 0.95

for b in range(nbars):
    t0 = b * bar
    if t0 > TOTAL: break
    bass, voic = prog[b % len(prog)]
    it = intensity(t0)
    final = t0 + bar > TOTAL - 0.01
    # piano arpeggio (8ths)
    arp = [bass + 24, voic[0], voic[1], voic[2], voic[3], voic[2], voic[1], voic[0]]
    for k, m in enumerate(arp):
        add(piano(m, beat * 1.5, 0.35 + 0.25 * it + rng.uniform(-.05, .05)), t0 + k * beat / 2 + rng.uniform(0, .012), pan=-0.3 + 0.08 * k, gain=0.9)
    add(piano(bass + 12, bar, 0.5 + 0.2 * it), t0, pan=-0.2)
    # melody from intensity 0.45
    if it >= 0.45:
        mel = melA if (b // 2) % 2 == 0 else melB
        for bt, m in mel:
            if (b % 2 == 1) and bt > 1: continue
            add(piano(m + (12 if it > 0.9 else 0) * 0, beat * 1.8, 0.45 + 0.3 * it), t0 + bt * beat, pan=0.25)
    # strings pad
    sg = 0.15 + 0.85 * max(0, it - 0.3) / 0.7
    for m in voic[:3]:
        add(strings(m, bar, sg, att=1.4), t0, pan=rng.uniform(-.5, .5))
    if it >= 0.6:
        add(strings(bass + 12, bar, 0.9 * sg, bright=900), t0, pan=0)  # cello
        add(strings(voic[3] + 12, bar, 0.35 * sg, att=2.0, bright=3500), t0, pan=0.4)  # violins high

# Final resolution chord ring-out
tf = TOTAL - 4.0
for m in [38, 50, 62, 66, 69, 74, 78]:
    add(piano(m, 4.0, 0.55), tf, pan=(m - 60) / 30)
for m in [50, 62, 66, 69, 81]:
    add(strings(m, 3.2, 0.7, att=0.8, rel=1.5), tf)

st = np.stack([L, R])
st = np.stack([reverb(st[0], 3.4, 0.38), reverb(st[1], 3.6, 0.38)])
st = st[:, : int(TOTAL * SR)]
fade = int(1.2 * SR); st[:, -fade:] *= np.linspace(1, 0, fade) ** 2
st[:, : int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
st = st / np.max(np.abs(st)) * 0.89
with wave.open(OUT, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st.T * 32767).astype('<i2').tobytes())
print('ok', OUT)
