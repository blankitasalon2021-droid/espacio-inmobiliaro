# Joins graded segments (cuts + dissolves), overlays animated graphics, muxes the master audio.
import subprocess, json, sys
from edl import SEGS, timeline, FPS
tl, TOTAL = timeline()
cues = json.load(open('cues.json'))['cues']
OUT = sys.argv[1] if len(sys.argv) > 1 else 'final.mp4'

inputs = []; fc = []
for s in SEGS:
    inputs += ['-i', f"seg/{s['id']}.mp4"]
# --- video chain
cur = '[0:v]'; curlen = SEGS[0]['dur']
fc.append(f"[0:v]settb=1/{FPS},setpts=PTS-STARTPTS[s0]"); cur = '[s0]'
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
# --- overlays
base = len(SEGS)
for i, c in enumerate(cues):
    inputs += ['-loop', '1', '-framerate', str(FPS), '-t', f"{c['dur']:.3f}", '-i', c['png']]
    st, d = c['start'], c['dur']
    fo_st = max(0, d - c['fout'])
    fc.append(f"[{base + i}:v]format=rgba,fade=t=in:st=0:d={c['fin']}:alpha=1,"
              f"fade=t=out:st={fo_st:.3f}:d={c['fout']}:alpha=1,setpts=PTS-STARTPTS+{st:.3f}/TB[g{i}]")
    rise = c['rise']; dur_r = max(c['fin'] * 1.2, 0.01)
    y = f"'{rise}*pow(1-min(1\\,max(0\\,(t-{st:.3f})/{dur_r:.3f}))\\,3)'" if rise else '0'
    fc.append(f"{cur}[g{i}]overlay=x=0:y={y}:eof_action=pass:eval=frame[o{i}]")
    cur = f'[o{i}]'
# final 0.35 s fade to black at the very end
fc.append(f"{cur}fade=t=out:st={TOTAL - 0.35:.3f}:d=0.35,format=yuv420p[vout]")
inputs += ['-i', 'aud/master.wav']
cmd = ['ffmpeg', '-v', 'error', '-stats', '-y'] + inputs + [
    '-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', f'{base + len(cues)}:a',
    '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.2', '-preset', 'slow', '-crf', '17', '-maxrate', '14M', '-bufsize', '24M',
    '-pix_fmt', 'yuv420p', '-r', str(FPS), '-g', '60', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
    '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-movflags', '+faststart', '-t', f'{TOTAL:.3f}', OUT]
open('assemble_cmd.txt', 'w').write(' '.join(cmd))
subprocess.run(cmd, check=True)
print('done', OUT, TOTAL)
