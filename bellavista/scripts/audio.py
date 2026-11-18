# Voice cleanup + original score + soft transition accents + ducking + loudness
import subprocess, numpy as np, wave, os
from edl import VOICE, timeline
os.makedirs('aud', exist_ok=True)
SR = 48000
tl, TOTAL = timeline()
TOTAL = round(TOTAL, 3)

def run(c): subprocess.run(c, check=True)

# 1) Voice clips: clean, EQ, compress, normalise each to -16 LUFS
VCHAIN = ("highpass=f=85,lowpass=f=14000,afftdn=nr=12:nf=-38:tn=1,"
          "equalizer=f=220:t=q:w=1.1:g=-2.5,equalizer=f=3200:t=q:w=1.3:g=2.5,equalizer=f=9000:t=h:w=0.7:g=1.0,"
          "acompressor=threshold=-24dB:ratio=3:attack=8:release=160:makeup=4dB,"
          "loudnorm=I=-16:TP=-2:LRA=7")
placed = []
for i, (clip, a, b, anc, off) in enumerate(VOICE):
    out = f'aud/v{i}.wav'
    run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a), '-t', f'{b - a:.3f}', '-i', f'norm/{clip}.mp4',
         '-af', VCHAIN + f",afade=t=in:d=0.08,afade=t=out:st={b - a - 0.15:.3f}:d=0.15,aresample={SR}",
         '-ac', '2', '-ar', str(SR), out])
    placed.append((out, tl[anc][0] + off))

def load(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).T
def savewav(p, x):
    x = np.clip(x, -1, 1)
    with wave.open(p, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x.T * 32767).astype('<i2').tobytes())

N = int(TOTAL * SR)
voice = np.zeros((2, N), np.float32)
for p, t in placed:
    x = load(p); i = int(t * SR); j = min(N, i + x.shape[1]); voice[:, i:j] += x[:, :j - i]
savewav('aud/voice_bus.wav', voice)

# 2) Original score with section markers matching the edit
sect = [0, tl['c'][0], tl['m'][0], tl['r'][0], tl['u'][0]]
run(['python3', 'music.py', str(TOTAL), 'aud/music_raw.wav', ','.join(f'{s:.2f}' for s in sect)])

# 3) Soft "air" swells at key transitions (filtered noise, very discreet)
rng = np.random.default_rng(3)
fx = np.zeros((2, N), np.float32)
def swell(t_center, dur=1.1, gain=0.06, f0=600, f1=4500):
    n = int(dur * SR); tt = np.arange(n) / SR
    noise = rng.normal(0, 1, (2, n))
    X = np.fft.rfft(noise, axis=1); fr = np.fft.rfftfreq(n, 1 / SR)
    fc = (f0 + f1) / 2
    X *= np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / (2 * 0.6 ** 2))
    y = np.fft.irfft(X, n, axis=1)
    env = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 2.5
    y = y / np.max(np.abs(y)) * env * gain
    i = int((t_center - dur * 0.6) * SR); j = min(N, i + n); fx[:, i:j] += y[:, :j - i]
for key in ['c', 'r', 'u', 'w']:
    swell(tl[key][0] + 0.2)
savewav('aud/fx.wav', fx)

# 4) Mix: music ducked by voice (sidechain), + voice + fx, master to -14 LUFS / -1 dBTP
run(['ffmpeg', '-v', 'error', '-y', '-i', 'aud/music_raw.wav', '-i', 'aud/voice_bus.wav', '-i', 'aud/fx.wav',
     '-filter_complex',
     "[0:a]volume=-3dB[m];[1:a]asplit=2[v][key];"
     "[m][key]sidechaincompress=threshold=0.05:ratio=4:attack=80:release=600:makeup=1[md];"
     "[md][v][2:a]amix=inputs=3:normalize=0:weights='1 1 1'[mix];"
     "[mix]alimiter=limit=0.95:attack=5:release=60",
     '-ar', '48000', '-ac', '2', 'aud/premaster.wav'])
import json, re
r = subprocess.run(['ffmpeg', '-i', 'aud/premaster.wav', '-af', 'loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
ln = (f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
run(['ffmpeg', '-v', 'error', '-y', '-i', 'aud/premaster.wav', '-af', ln + ',aresample=48000', '-ar', '48000', 'aud/master.wav'])
print('audio done', TOTAL)
