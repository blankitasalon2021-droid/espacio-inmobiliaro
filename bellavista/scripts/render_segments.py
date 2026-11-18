# Renders each EDL segment to a graded 1080x1920@30 intermediate (video only).
import subprocess, numpy as np, os, sys, math
from concurrent.futures import ThreadPoolExecutor
from edl import SEGS, FPS
os.makedirs('seg', exist_ok=True)
W, H = 1080, 1920

def stats(src, crop):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f'norm/{src}.mp4', '-vf', crop + 'fps=2,scale=108:192',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(float)
    m = a.mean(0); med = np.median(a.mean(1))
    return m, med

def grade(src):
    is_dani = src.startswith('Mi_')
    crop = 'crop=608:1080:656:0,' if is_dani else ''
    m, med = stats(src, crop)
    br = m[2] / m[0]
    exterior = br > 0.9
    # White balance: pull very orange clips partway toward a warm-neutral target, keep ochre walls authentic.
    target = 0.66
    rg = gg = bg = 1.0
    if not exterior and br < target:
        k = math.sqrt(target / br)          # half-way (in log) correction
        k = min(k, 1.32)
        rg = k ** -0.35; bg = k ** 0.65; gg = k ** 0.05
    # Exposure: bring median luma toward 150 (partial)
    # Exposure: bright, airy look. ffmpeg eq gamma > 1 brightens (out = in^(1/gamma)).
    tgt = 162.0 if is_dani else 160.0
    g = math.log(med / 255) / math.log(tgt / 255)
    g = 1 + (g - 1) * 0.85
    g = min(max(g, 0.85), 1.75 if is_dani else 1.3)
    sat = 1.22 if is_dani else 1.12
    if exterior: sat = 1.18
    if br < 0.45 and not is_dani: sat = 1.0
    curve = ("0/0 0.15/0.14 0.5/0.53 0.85/0.88 1/0.99" if is_dani else
             "0/0 0.15/0.135 0.5/0.51 0.85/0.87 1/0.99")
    f = (f"colorchannelmixer=rr={rg:.3f}:gg={gg:.3f}:bb={bg:.3f},"
         f"eq=gamma={g:.3f}:saturation={sat}:contrast=1.07,"
         f"curves=master='{curve}',"
         )
    return crop, f, dict(br=round(br, 2), med=round(med), gamma=round(g, 3), rg=round(rg, 3), bg=round(bg, 3))

def render(s):
    out = f"seg/{s['id']}.mp4"
    nfr = round(s['dur'] * FPS)
    if s['src'] == 'CARD':
        cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=0x5E1B18:s={W}x{H}:r={FPS}:d={s["dur"]}',
               '-vf', "vignette=angle=PI/3.2,noise=alls=3:allf=t,format=yuv420p", '-frames:v', str(nfr),
               '-c:v', 'libx264', '-crf', '12', '-preset', 'medium', out]
        subprocess.run(cmd, check=True); return s['id'], 'card'
    sp = s.get('speed', 1.0)
    srcdur = s['dur'] * sp + 0.2
    crop, gf, info = grade(s['src'])
    is_dani = s['src'].startswith('Mi_')
    vf = crop
    if s.get('freeze'):
        vf += f"select='eq(n\\,0)',loop=loop=-1:size=1:start=0,setpts=N/{FPS}/TB,"
    elif sp != 1.0:
        vf += f"setpts=PTS/{sp},minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
    else:
        vf += f"fps={FPS},"
    if is_dani:
        vf += f"scale={W}:{H}:flags=lanczos,hqdn3d=1.5:1.5:3:3,unsharp=5:5:0.8:5:5:0,"
    else:
        vf += f"scale={W}:{H}:flags=lanczos,hqdn3d=1:1:2:2,unsharp=5:5:0.4:5:5:0,"
    if s.get('closing'):
        # darker, softer plate for the price card
        vf += gf + "gblur=sigma=26,eq=brightness=-0.11:saturation=1.0:contrast=0.95,"
    else:
        vf += gf
    vf += "format=yuv420p"
    cmd = ['ffmpeg', '-v', 'error', '-y', '-ss', str(s['ss']), '-t', f'{srcdur:.3f}', '-i', f"norm/{s['src']}.mp4",
           '-vf', vf, '-frames:v', str(nfr), '-an', '-c:v', 'libx264', '-crf', '12', '-preset', 'medium',
           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', out]
    subprocess.run(cmd, check=True)
    return s['id'], info

only = sys.argv[1:]
todo = [s for s in SEGS if not only or s['id'] in only]
# slow (interpolated) segments first so they overlap with the fast ones
todo.sort(key=lambda s: -(s['dur'] if s.get('speed', 1) != 1 else 0))
with ThreadPoolExecutor(4) as ex:
    for sid, info in ex.map(render, todo):
        print(sid, info, flush=True)
