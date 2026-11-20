# Renders each EDL segment to a graded 1080x1920@30 intermediate (video only).
# Extras v4: push-in on the magazine freeze, day→dusk transformation on the terrace, blurred dusk plate for the card.
import subprocess, numpy as np, os, sys, math
from concurrent.futures import ThreadPoolExecutor
from edl import SEGS, FPS, src_path
os.makedirs('seg', exist_ok=True)
W, H = 1080, 1920

def stats(src, crop):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src_path(src), '-vf', crop + 'fps=2,scale=108:192',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(float)
    return a.mean(0), np.median(a.mean(1))

def grade(src):
    is_dani = src.startswith('Mi_')
    crop = 'crop=608:1080:656:0,' if is_dani else ''
    m, med = stats(src, crop)
    br = m[2] / m[0]
    exterior = br > 0.9
    target = 0.66; rg = gg = bg = 1.0
    if not exterior and br < target:
        k = min(math.sqrt(target / br), 1.32)
        rg = k ** -0.35; bg = k ** 0.65; gg = k ** 0.05
    tgt = 162.0 if is_dani else 160.0
    g = math.log(med / 255) / math.log(tgt / 255)
    g = 1 + (g - 1) * 0.85
    g = min(max(g, 0.85), 1.75 if is_dani else 1.3)
    sat = 1.22 if is_dani else 1.12
    if exterior: sat = 1.18
    if br < 0.45 and not is_dani: sat = 1.0
    curve = "0/0 0.15/0.14 0.5/0.53 0.85/0.88 1/0.99" if is_dani else "0/0 0.15/0.135 0.5/0.51 0.85/0.87 1/0.99"
    f = (f"colorchannelmixer=rr={rg:.3f}:gg={gg:.3f}:bb={bg:.3f},"
         f"eq=gamma={g:.3f}:saturation={sat}:contrast=1.07,curves=master='{curve}'")
    return crop, f, dict(br=round(br, 2), med=round(med), gamma=round(g, 3))

# Dusk look: warm/rose multiply on the sky, lower exposure, warmer mids, a touch more contrast.
DUSK = ("colorchannelmixer=rr=1.02:gg=0.96:bb=0.88,eq=gamma=0.86:saturation=0.98:contrast=1.06:brightness=-0.03,"
        "curves=r='0/0 0.5/0.55 1/1':b='0/0.03 0.5/0.45 1/0.92'")

def render(s):
    out = f"seg/{s['id']}.mp4"
    nfr = round(s['dur'] * FPS)
    sp = s.get('speed', 1.0)
    srcdur = s['dur'] * sp + 0.25
    crop, gf, info = grade(s['src'])
    is_dani = s['src'].startswith('Mi_')
    vf = crop
    if s.get('freeze'):
        vf += f"trim=end_frame=1,loop=loop=-1:size=1:start=0,setpts=N/{FPS}/TB,"
    elif sp != 1.0:
        vf += f"setpts=PTS/{sp},minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
    else:
        vf += f"fps={FPS},"
    clean = "hqdn3d=1.5:1.5:3:3,unsharp=5:5:0.8:5:5:0" if is_dani else "hqdn3d=1:1:2:2,unsharp=5:5:0.4:5:5:0"
    if s.get('push'):
        vf += (f"scale={2*W}:{2*H}:flags=lanczos,{clean},"
               f"zoompan=z='1+0.06*on/{nfr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},")
    else:
        vf += f"scale={W}:{H}:flags=lanczos,{clean},"
    vf += gf
    inputs = ['-ss', str(s['ss']), '-t', f'{srcdur:.3f}', '-i', src_path(s['src'])]
    if 'dusk' in s:
        a, b = s['dusk']
        inputs += ['-loop', '1', '-i', 'dusk_grad.png']
        if b > a:
            k = f"clip((T-{a})/{b - a},0,1)"
            k = f"({k}*{k}*(3-2*{k}))"
        else:
            k = "1"
        tail = ",gblur=sigma=24,eq=brightness=-0.04" if s.get('closing') else ""
        fc = (f"[0:v]{vf},format=gbrp,split[day0][d0];[day0]format=yuv444p[day];"
              f"[1:v]scale={W}:{H},format=gbrp[gr];"
              f"[d0][gr]blend=all_mode=multiply:shortest=1,format=yuv444p,{DUSK},format=yuv444p[dusk];"
              f"[day][dusk]blend=all_expr='A*(1-{k})+B*{k}'{tail},format=yuv420p[o]")
        args = ['-filter_complex', fc, '-map', '[o]']
    else:
        if s.get('closing'):
            vf += ",gblur=sigma=24"
        args = ['-vf', vf + ",format=yuv420p"]
    cmd = (['ffmpeg', '-v', 'error', '-y'] + inputs + args +
           ['-frames:v', str(nfr), '-an', '-c:v', 'libx264', '-crf', '12', '-preset', 'medium',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', out])
    subprocess.run(cmd, check=True)
    return s['id'], info

only = sys.argv[1:]
todo = [s for s in SEGS if not only or s['id'] in only]
todo.sort(key=lambda s: -(s['dur'] if s.get('speed', 1) != 1 or 'dusk' in s else 0))
with ThreadPoolExecutor(4) as ex:
    for sid, info in ex.map(render, todo):
        print(sid, info, flush=True)
