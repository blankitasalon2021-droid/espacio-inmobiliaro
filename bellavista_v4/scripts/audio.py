# Voz de Dani limpia + efectos de sonido diseñados por código (uno por elemento que se mueve).
# Sin música. En la parte emocional (cierre de Dani en la terraza) no hay efectos. Master -14 LUFS / -1 dBTP.
import subprocess, numpy as np, wave, os, json
from edl import VOICE, SEGS, timeline, src_path
import overlay
os.makedirs('aud', exist_ok=True)
SR = 48000
tl, TOTAL = timeline(); N = int(TOTAL * SR)
rng = np.random.default_rng(7)
def run(c): subprocess.run(c, check=True)

VCHAIN = ("highpass=f=85,lowpass=f=14000,afftdn=nr=12:nf=-38:tn=1,"
          "equalizer=f=220:t=q:w=1.1:g=-2.5,equalizer=f=3200:t=q:w=1.3:g=2.5,equalizer=f=9000:t=h:w=0.7:g=1.0,"
          "acompressor=threshold=-24dB:ratio=3:attack=8:release=160:makeup=4dB,loudnorm=I=-16:TP=-2:LRA=7")
def load(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).T
def savewav(p, x):
    with wave.open(p, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1).T * 32767).astype('<i2').tobytes())

voice = np.zeros((2, N), np.float32)
for i, (clip, a, b, anc, off) in enumerate(VOICE):
    out = f'aud/v{i}.wav'
    run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a), '-t', f'{b - a:.3f}', '-i', src_path(clip), '-map', '0:a:0',
         '-af', VCHAIN + f",afade=t=in:d=0.08,afade=t=out:st={b - a - 0.15:.3f}:d=0.15,aresample={SR}",
         '-ac', '2', '-ar', str(SR), out])
    x = load(out); s = int((tl[anc][0] + off) * SR); e = min(N, s + x.shape[1]); voice[:, s:e] += x[:, :e - s]
savewav('aud/voice_bus.wav', voice)

fx = np.zeros((2, N), np.float32)
def put(sig, t, pan=0.0):
    if sig.ndim == 1:
        sig = np.stack([sig * np.sqrt((1 - pan) / 2), sig * np.sqrt((1 + pan) / 2)])
    i = int(t * SR)
    if i < 0: sig = sig[:, -i:]; i = 0
    j = min(N, i + sig.shape[1]); fx[:, i:j] += sig[:, :j - i]

def bandnoise(n, fc_curve, q=0.45):
    noise = rng.normal(0, 1, n); out = np.zeros(n); hop = 512; win = np.hanning(2 * hop)
    fr = np.fft.rfftfreq(2 * hop, 1 / SR)
    for s in range(0, n - 2 * hop, hop):
        X = np.fft.rfft(noise[s:s + 2 * hop] * win)
        fc = fc_curve((s + hop) / n)
        X *= np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / (2 * q ** 2))
        out[s:s + 2 * hop] += np.fft.irfft(X, 2 * hop)
    return out / (np.abs(out).max() + 1e-9)

def whoosh(t, dur=0.55, gain=0.30, lo=300, hi=5500, d=1):
    n = int(dur * SR); x = np.arange(n) / n
    s = bandnoise(n, lambda p: lo * (hi / lo) ** np.sin(np.pi * p))
    env = np.where(x < 0.55, (x / 0.55) ** 2, np.exp(-(x - 0.55) * 9))
    sig = s * env * gain
    put(np.stack([sig * np.sqrt((1 + d * (x * 1.2 - 0.6)) / 2 + 1e-9).clip(0, 1),
                  sig * np.sqrt((1 - d * (x * 1.2 - 0.6)) / 2 + 1e-9).clip(0, 1)]), t - 0.55 * dur)

def tone(f, dur, decay, gain, harm=((1, 1),)):
    tt = np.arange(int(dur * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * h * tt) for h, a in harm) * np.exp(-tt * decay) * np.minimum(1, tt / 0.003) * gain

def pop(t, gain=0.22, f=620):
    tt = np.arange(int(0.12 * SR)) / SR
    ff = f * (1 + 1.2 * np.exp(-tt * 60))
    sig = np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-tt * 38) * np.minimum(1, tt / 0.002) * gain
    put(sig, t, pan=rng.uniform(-0.2, 0.2))
def tick(t, gain=0.12):
    put(tone(2400, 0.06, 90, gain, ((1, 1), (2.7, 0.4))), t, pan=rng.uniform(-0.3, 0.3))
def check(t):
    put(tone(1320, 0.35, 14, 0.12, ((1, 1), (2, 0.3))), t, 0.1); put(tone(1980, 0.3, 16, 0.08), t + 0.06, -0.1)
def swipe(t): whoosh(t + 0.05, dur=0.25, gain=0.10, lo=1200, hi=7000)
def shutter(t):
    for dt, g in ((0, 0.25), (0.07, 0.18)):
        n = int(0.05 * SR); s = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 120) * g
        put(np.convolve(s, [1, -0.9], 'same'), t + dt)
def flash(t):
    whoosh(t, dur=0.5, gain=0.22, lo=900, hi=9000)
    put(tone(2093, 1.0, 5, 0.06, ((1, 1), (1.5, 0.5), (2, 0.3))), t)
def hit(t, gain=0.32):
    tt = np.arange(int(2.0 * SR)) / SR; f = 65 + 45 * np.exp(-tt * 8)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.4)
    shim = sum(np.sin(2 * np.pi * fr * tt) * np.exp(-tt * (1.8 + k * 0.4)) * 0.10 for k, fr in enumerate([880, 1320, 1760]))
    put((body * 0.9 + shim) * np.minimum(1, tt / 0.01) * gain, t)
def draw(t, dur=1.45):
    n = int(dur * SR); x = np.arange(n) / n
    s = bandnoise(n, lambda p: 2500 + 1500 * np.sin(2 * np.pi * p * 5), q=0.3)
    env = np.sin(np.pi * x) ** 0.6 * (0.7 + 0.3 * np.sin(2 * np.pi * x * 9) ** 2) * 0.10
    put(s * env, t)
def shimmer(t):
    for k, f in enumerate([1568, 2093, 2637, 3136]):
        put(tone(f, 1.4, 3.5, 0.045), t + k * 0.07, pan=-0.4 + k * 0.27)

FN = dict(pop=pop, tick=tick, check=check, swipe=swipe, shutter=shutter, flash=flash, hit=hit, draw=draw,
          shimmer=shimmer, whoosh_s=lambda t: whoosh(t + 0.15, dur=0.4, gain=0.16, lo=500, hi=6000))
# parte emocional: desde "Si deseas conocer esta casa" hasta que termina la voz → silencio de efectos
t0 = tl['t'][0]; EMO = (t0 + 0.2 + (3.48 - 0.75) - 0.2, t0 + 7.1)
events = list(overlay.EVENTS)
# barridos de transición
for k, s in enumerate(SEGS):
    if s.get('tr', '').startswith('whip'):
        whoosh(tl[s['id']][0] + s['xf'] / 2 + 0.05, gain=0.30, d=1 if s['tr'] == 'whipL' else -1)
kept = 0
for t, kind in events:
    if EMO[0] <= t <= EMO[1]: continue
    FN[kind](t); kept += 1
savewav('aud/fx.wav', fx)
print('sfx', kept, 'muted window', [round(x, 2) for x in EMO])

run(['ffmpeg', '-v', 'error', '-y', '-i', 'aud/voice_bus.wav', '-i', 'aud/fx.wav', '-filter_complex',
     "[1:a]volume=-2dB[f];[0:a][f]amix=inputs=2:normalize=0,alimiter=limit=0.95:attack=5:release=60",
     '-ar', str(SR), 'aud/premaster.wav'])
r = subprocess.run(['ffmpeg', '-i', 'aud/premaster.wav', '-af', 'loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json',
                    '-f', 'null', '-'], capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
ln = (f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
run(['ffmpeg', '-v', 'error', '-y', '-i', 'aud/premaster.wav', '-af', ln + ',aresample=48000', '-ar', '48000', 'aud/master.wav'])
print('audio ok', round(TOTAL, 2))
