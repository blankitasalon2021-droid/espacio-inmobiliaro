# Version without background music: cleaned voice + designed transition SFX only. -14 LUFS / -1 dBTP.
import subprocess, numpy as np, wave, json
from edl import timeline
SR = 48000
tl, TOTAL = timeline(); N = int(TOTAL * SR)
rng = np.random.default_rng(11)

def load(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).T
def savewav(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1).T * 32767).astype('<i2').tobytes())

fx = np.zeros((2, N), np.float32)
def put(sig, t):
    i = int(t * SR); j = min(N, i + sig.shape[1])
    if i < 0: sig = sig[:, -i:]; i = 0
    fx[:, i:j] += sig[:, :j - i]

def whoosh(t_cut, dur=0.9, gain=0.22, f_lo=350, f_hi=5000, pan_dir=1):
    """Air whoosh: band-pass noise whose centre sweeps up then down, peaking at the cut."""
    n = int(dur * SR); tt = np.arange(n) / SR; x = tt / dur
    noise = rng.normal(0, 1, n)
    out = np.zeros(n)
    hop = 1024; win = np.hanning(2 * hop)
    for s in range(0, n - 2 * hop, hop):
        seg = noise[s:s + 2 * hop] * win
        X = np.fft.rfft(seg); fr = np.fft.rfftfreq(2 * hop, 1 / SR)
        p = (s + hop) / n
        fc = f_lo * (f_hi / f_lo) ** (np.sin(np.pi * min(p / 0.7, 1) * 0.5) if p < 0.7 else 1 - (p - 0.7) / 0.3 * 0.6)
        X *= np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / (2 * 0.45 ** 2))
        out[s:s + 2 * hop] += np.fft.irfft(X, 2 * hop)
    env = np.where(x < 0.7, (x / 0.7) ** 2.2, np.exp(-(x - 0.7) * 14))
    out = out / (np.max(np.abs(out)) + 1e-9) * env * gain
    pan = np.clip(-0.6 + 1.2 * x, -0.6, 0.6) * pan_dir
    st = np.stack([out * np.sqrt((1 - pan) / 2), out * np.sqrt((1 + pan) / 2)])
    put(st, t_cut - 0.7 * dur)

def soft_hit(t, gain=0.30):
    """Warm low 'bloom' accent (sine drop + filtered noise tail) for reveals."""
    n = int(2.2 * SR); tt = np.arange(n) / SR
    f = 70 + 40 * np.exp(-tt * 8)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.2)
    shimmer = sum(np.sin(2 * np.pi * fr * tt + rng.uniform(0, 6)) * np.exp(-tt * (1.6 + k * 0.4)) * 0.12
                  for k, fr in enumerate([880, 1320, 1760, 2640]))
    sig = (body * 0.9 + shimmer) * np.minimum(1, tt / 0.01) * gain
    put(np.stack([sig, sig]), t)

# whooshes on scene changes and key cuts (alternating direction)
cuts = ['c', 'd', 'f', 'h', 'j', 'm', 'r', 't', 'u']
for k, c in enumerate(cuts):
    whoosh(tl[c][0] + (0.2 if c in ('c', 'r', 'u') else 0.0), gain=0.20 if c in ('c', 'f', 'j', 'm', 'r', 'u') else 0.12,
           pan_dir=1 if k % 2 == 0 else -1)
whoosh(tl['v'][0] + 0.45, dur=1.2, gain=0.22)
soft_hit(tl['v'][0] + 0.85)          # price reveal
soft_hit(tl['v'][0] + 3.95, 0.26)   # brand / logo reveal
# gentle intro swell under the title
whoosh(1.1, dur=1.8, gain=0.12, f_lo=250, f_hi=3000)
savewav('aud/fx2.wav', fx)

subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'aud/voice_bus.wav', '-i', 'aud/fx2.wav', '-filter_complex',
                "[0:a][1:a]amix=inputs=2:normalize=0[m];[m]alimiter=limit=0.95:attack=5:release=60",
                '-ar', str(SR), 'aud/premaster_nm.wav'], check=True)
r = subprocess.run(['ffmpeg', '-i', 'aud/premaster_nm.wav', '-af', 'loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json',
                    '-f', 'null', '-'], capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
ln = (f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'aud/premaster_nm.wav', '-af', ln + ',aresample=48000',
                '-ar', '48000', 'aud/master_nomusic.wav'], check=True)
print('ok')
