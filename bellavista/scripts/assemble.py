# Joins graded segments (cuts + dissolves), overlays the animated graphics track (piped RGBA), muxes master audio.
import subprocess, sys, threading
from edl import SEGS, timeline, FPS
import overlay
tl, TOTAL = timeline()
OUT = sys.argv[1] if len(sys.argv) > 1 else 'final.mp4'
AUD = sys.argv[2] if len(sys.argv) > 2 else 'aud/master.wav'
NF = round(TOTAL * FPS)

inputs = []; fc = []
for s in SEGS:
    inputs += ['-i', f"seg/{s['id']}.mp4"]
fc.append(f"[0:v]settb=1/{FPS},setpts=PTS-STARTPTS[s0]"); cur = '[s0]'; curlen = SEGS[0]['dur']
for k, s in enumerate(SEGS[1:], start=1):
    fc.append(f"[{k}:v]settb=1/{FPS},setpts=PTS-STARTPTS[s{k}]")
    xf = s.get('xf', 0)
    if xf:
        off = curlen - xf
        fc.append(f"{cur}[s{k}]xfade=transition=fade:duration={xf}:offset={off:.4f},settb=1/{FPS}[j{k}]")
        curlen = off + s['dur']
    else:
        fc.append(f"{cur}[s{k}]concat=n=2:v=1:a=0,settb=1/{FPS}[j{k}]")
        curlen += s['dur']
    cur = f'[j{k}]'
ov = len(SEGS); au = ov + 1
inputs += ['-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '1080x1920', '-r', str(FPS), '-i', 'pipe:0', '-i', AUD]
fc.append(f"[{ov}:v]settb=1/{FPS},setpts=PTS-STARTPTS[ovl]")
fc.append(f"{cur}[ovl]overlay=0:0:format=auto:shortest=0,fade=t=out:st={TOTAL - 0.4:.3f}:d=0.4,format=yuv420p[vout]")
cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + [
    '-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', f'{au}:a',
    '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.2', '-preset', 'slow', '-crf', '19', '-maxrate', '9M', '-bufsize', '18M',
    '-pix_fmt', 'yuv420p', '-r', str(FPS), '-g', '60', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
    '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-movflags', '+faststart', '-frames:v', str(NF), OUT]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for n in range(NF):
    p.stdin.write(overlay.frame(n / FPS).tobytes())
    if n % 300 == 0: print('frame', n, '/', NF, flush=True)
p.stdin.close(); p.wait()
assert p.returncode == 0
print('done', OUT, TOTAL)
