# Librería común para historias de 1 min (Espacio Inmobiliario).
# Video base con ffmpeg (segmentos + transiciones), capa gráfica animada con PIL/numpy,
# música original sintetizada, efectos de sonido diseñados y master a -14 LUFS.
import subprocess, os, json, wave, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('SRC', '/root/.claude/uploads/3d0d90bc-b966-5be0-b31a-8b91dd6a401d/'
                     '6ca82455-2c2a92ea-abee-476f-824e-de8020fe3f65.mp4')
W, H, FPS = 1080, 1920, 30
BEIGE = (231, 211, 175); VINO = (102, 30, 26); WHITE = (255, 255, 255)
# Margen de seguridad para historias/reels: libre arriba (perfil), abajo (respuesta) y a la derecha.
SAFE_TOP, SAFE_BOT, SAFE_L, SAFE_R = 270, 1580, 80, 960
SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def _f(name, size): return ImageFont.truetype(os.path.join(HERE, 'fonts', name), size)
cinzel = lambda s: _f('Cinzel-Regular.woff', s)
cinzelb = lambda s: _f('Cinzel-Bold.woff', s)
script = lambda s: _f('GreatVibes.woff', s)

def tw(t, f, tr=0):
    if not tr: return f.getlength(t)
    return sum(f.getlength(c) for c in t) + tr * (len(t) - 1)

def dtext(d, x, y, t, f, fill, tr=0, center=True):
    w = tw(t, f, tr); x = x - w / 2 if center else x
    if not tr: d.text((x, y), t, font=f, fill=fill); return w
    for c in t:
        d.text((x, y), c, font=f, fill=fill); x += f.getlength(c) + tr
    return w

def canvas(): return Image.new('RGBA', (W, H))

def shadowed(L, radius=8, alpha=170, dy=3):
    a = L.split()[3].point(lambda v: v * alpha // 255).filter(ImageFilter.GaussianBlur(radius))
    sh = Image.new('RGBA', L.size, (20, 8, 6, 255)); sh.putalpha(a)
    out = Image.new('RGBA', L.size); out.alpha_composite(sh, (0, dy)); out.alpha_composite(L)
    return out

def ease_out(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def ease_io(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def back_out(x):
    x = min(1, max(0, x)); c = 1.70158; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

# ------------------------------------------------------------------ capas
class Layer:
    """Imagen RGBA estática animada en el tiempo: fundido, subida, desplazamiento, escala, barrido y máscara."""
    def __init__(self, img, t0, t1, fin=0.45, fout=0.35, rise=18, dx=0, scale0=1.0, sdur=None,
                 wipe=None, mask=None, ease=ease_out, pivot=None):
        bb = img.getbbox() or (0, 0, 1, 1); p = 2
        bb = (max(0, bb[0] - p), max(0, bb[1] - p), min(img.width, bb[2] + p), min(img.height, bb[3] + p))
        self.x, self.y = bb[0], bb[1]
        self.img = img.crop(bb)
        a = np.asarray(self.img).astype(np.float32) / 255.0
        self.rgb = a[..., :3]; self.a = a[..., 3:4]
        self.t0, self.t1, self.fin, self.fout = t0, t1, fin, fout
        self.rise, self.dx, self.scale0, self.ease = rise, dx, scale0, ease
        self.sdur = sdur if sdur is not None else max(fin * 1.4, 0.3)
        self.wipe = wipe          # (dur) barrido de izquierda a derecha
        self.mask = mask          # función(t, h, w) -> máscara 2D 0..1
        self.pivot = pivot

    def state(self, t):
        if t < self.t0 or t >= self.t1: return None
        k = 1.0
        if self.fin > 0: k = min(k, (t - self.t0) / self.fin)
        if self.fout > 0: k = min(k, (self.t1 - t) / self.fout)
        k = ease_io(k)
        e = self.ease((t - self.t0) / self.sdur)
        return k, e

    def draw(self, out, t):
        st = self.state(t)
        if st is None: return
        k, e = st
        if k <= 0.002: return
        rgb, a = self.rgb, self.a
        x, y = self.x + self.dx * (1 - e), self.y + self.rise * (1 - e)
        if self.scale0 != 1.0 and e < 0.999:
            s = self.scale0 + (1 - self.scale0) * e
            h0, w0 = a.shape[:2]
            nw, nh = max(1, int(w0 * s)), max(1, int(h0 * s))
            im = self.img.resize((nw, nh), Image.BILINEAR)
            arr = np.asarray(im).astype(np.float32) / 255.0
            rgb, a = arr[..., :3], arr[..., 3:4]
            cx, cy = self.pivot if self.pivot else (self.x + w0 / 2, self.y + h0 / 2)
            x = cx - (cx - x) * s; y = cy - (cy - y) * s
        if self.wipe:
            fr = ease_io((t - self.t0) / self.wipe)
            if fr < 1:
                ww = a.shape[1]; cut = int(ww * fr)
                ramp = np.clip((cut - np.arange(ww)) / 25.0, 0, 1)[None, :, None]
                a = a * ramp
        if self.mask is not None:
            m = self.mask(t, a.shape[0], a.shape[1])
            if m is not None: a = a * m[..., None]
        blend(out, rgb, a * k, int(round(x)), int(round(y)))

class FrameLayer:
    """Capa dinámica: función(t) -> (Image RGBA de W×H) o None. Para elementos que cambian cada cuadro."""
    def __init__(self, fn, t0, t1): self.fn, self.t0, self.t1 = fn, t0, t1
    def draw(self, out, t):
        if t < self.t0 or t >= self.t1: return
        im = self.fn(t)
        if im is None: return
        bb = im.getbbox()
        if not bb: return
        arr = np.asarray(im.crop(bb)).astype(np.float32) / 255.0
        blend(out, arr[..., :3], arr[..., 3:4], bb[0], bb[1])

def blend(out, rgb, a, x, y):
    h, w = a.shape[:2]
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    sl = (slice(y0 - y, y1 - y), slice(x0 - x, x1 - x))
    reg = out[y0:y1, x0:x1]; aa = a[sl]; ra = reg[..., 3:4]
    na = aa + ra * (1 - aa)
    reg[..., :3] = (rgb[sl] * aa + reg[..., :3] * ra * (1 - aa)) / np.maximum(na, 1e-6)
    reg[..., 3:4] = na

def render_frame(layers, t):
    out = np.zeros((H, W, 4), np.float32)
    for ly in layers: ly.draw(out, t)
    return (out * 255 + 0.5).astype(np.uint8)

# ------------------------------------------------------------------ textos
def typewriter(lines, t0, t1, cps=22, shadow=(6, 200, 2), fout=0.4, rise=8):
    """Letras que aparecen una a una. lines = [(texto, fuente, color, y, tracking)]."""
    out = []; t = t0
    for txt, f, col, y, tr in lines:
        x = W / 2 - tw(txt, f, tr) / 2
        for c in txt:
            if c != ' ':
                L = canvas(); ImageDraw.Draw(L).text((x, y), c, font=f, fill=col)
                out.append(Layer(shadowed(L, *shadow), t, t1, fin=0.12, fout=fout, rise=rise, sdur=0.25))
            x += f.getlength(c) + tr; t += 1 / cps
        t += 0.12
    return out, t

def block(fn, shadow=(9, 190, 3)):
    L = canvas(); d = ImageDraw.Draw(L); fn(d); return shadowed(L, *shadow)

def pill_label(d, cx, y, text, f, fill, color, padx=34, h=64, tr=6):
    w = tw(text, f, tr) + 2 * padx; x0 = cx - w / 2
    d.rounded_rectangle((x0, y, x0 + w, y + h), radius=h / 2, fill=fill)
    bb = f.getbbox(text)
    dtext(d, cx, y + (h - (bb[3] + bb[1])) / 2, text, f, color, tr=tr)
    return w

def wrap(text, f, maxw, tr=0):
    words = text.split(); lines = [[]]
    for w in words:
        trial = ' '.join(lines[-1] + [w])
        if lines[-1] and tw(trial, f, tr) > maxw: lines.append([w])
        else: lines[-1].append(w)
    return [' '.join(l) for l in lines]

def arrow_down(d, cx, y, h, col, w=6):
    d.line((cx, y, cx, y + h), fill=col, width=w)
    d.line((cx - h * 0.35, y + h * 0.62, cx, y + h), fill=col, width=w)
    d.line((cx + h * 0.35, y + h * 0.62, cx, y + h), fill=col, width=w)

def pin_icon(d, cx, cy, r, col, hole):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    d.polygon([(cx - r * .82, cy + r * .45), (cx + r * .82, cy + r * .45), (cx, cy + r * 2.1)], fill=col)
    d.ellipse((cx - r * .42, cy - r * .42, cx + r * .42, cy + r * .42), fill=hole)

# ------------------------------------------------------------------ tarjeta final
LOGO = Image.open(os.path.join(HERE, 'logo', 't3.png')).convert('RGBA').crop((51, 48, 450, 418))
LOGO_W = 420

def endcard(t0, t1, mode='aparece', cta='AGENDA TU VISITA'):
    """Tarjeta final de marca sobre la última toma desenfocada. Devuelve (capas, tiempos de cada elemento)."""
    lw = LOGO_W; s = lw / LOGO.width; lh = round(LOGO.height * s)
    logo = LOGO.resize((lw, lh), Image.LANCZOS)
    LY = 290; LX = (W - lw) // 2
    layers = []; ev = []
    def piece(y0, y1):
        L = canvas(); L.alpha_composite(logo.crop((0, int(y0 * s), lw, int(y1 * s))), (LX, LY + int(y0 * s)))
        return shadowed(L, 12, 150, 4)
    if mode == 'aparece':
        L = canvas(); L.alpha_composite(logo, (LX, LY))
        layers.append(Layer(shadowed(L, 12, 150, 4), t0, t1, fin=1.0, fout=0.01, rise=0, scale0=0.88, sdur=1.6))
        ev.append(('logo', t0)); tl = t0 + 1.2
    elif mode == 'arma':
        # piezas (logo recortado: farol 0-246, ESPACIO 250-328, INMOBILIARIO 345-370 en px originales)
        layers.append(Layer(piece(0, 248), t0, t1, fin=0.35, fout=0.01, rise=-260, sdur=0.75, ease=back_out))
        layers.append(Layer(piece(248, 334), t0 + 0.45, t1, fin=0.3, fout=0.01, rise=0, dx=-420, sdur=0.6, ease=back_out))
        layers.append(Layer(piece(334, 370), t0 + 0.8, t1, fin=0.3, fout=0.01, rise=0, dx=420, sdur=0.6, ease=back_out))
        ev += [('logo', t0), ('pop', t0 + 0.45), ('pop', t0 + 0.8)]; tl = t0 + 1.4
    else:  # 'dibuja': el farol y la espiral se trazan (barrido angular desde el centro de la espiral), luego el texto
        lamp = piece(0, 248)
        bx, by = LX + 0.30 * lw, LY + 0.36 * lh       # centro aproximado del brazo en espiral
        dur = 1.5
        def mk(lay):
            ox, oy = lay.x, lay.y; hh, ww = lay.a.shape[:2]
            yy, xx = np.mgrid[0:hh, 0:ww]
            ang = (np.arctan2(yy + oy - by, xx + ox - bx) + np.pi * 1.15) % (2 * np.pi) / (2 * np.pi)
            rad = np.hypot(yy + oy - by, xx + ox - bx) / (lw * 0.9)
            key = (0.7 * ang + 0.3 * rad).astype(np.float32)
            def m(t, h, w):
                p = (t - lay.t0) / dur
                if p >= 1.05: return None
                return np.clip((p * 1.08 - key) / 0.05, 0, 1)
            return m
        ly = Layer(lamp, t0, t1, fin=0.05, fout=0.01, rise=0); ly.mask = mk(ly); layers.append(ly)
        # brillo que acompaña el trazo
        layers.append(Layer(piece(248, 370), t0 + dur, t1, fin=0.5, fout=0.01, rise=0, wipe=0.8))
        ev += [('draw', t0), ('logo', t0 + dur)]; tl = t0 + dur + 0.7
    # botones de WhatsApp
    yb = LY + lh + 50
    for i, num in enumerate(['+502 5565-4621', '+502 5952-8514']):
        def _p(d, y=yb + i * 112, num=num):
            f = cinzelb(44); w = tw(num, f, 2) + 150; h = 92; x0 = W / 2 - w / 2
            d.rounded_rectangle((x0, y, x0 + w, y + h), radius=h / 2, fill=VINO + (245,))
            cx, cy = x0 + 52, y + h / 2
            wa_icon(d, cx, cy, 32)
            bb = f.getbbox(num)
            dtext(d, x0 + 104, y + (h - (bb[1] + bb[3])) / 2, num, f, WHITE, tr=2, center=False)
        tt = tl + i * 0.35
        layers.append(Layer(block(_p, (12, 120, 5)), tt, t1, fin=0.35, fout=0.01, rise=0, scale0=0.6, sdur=0.5, ease=back_out))
        ev.append(('pop', tt))
    yc = yb + 2 * 112 + 30; tc = tl + 0.8
    layers.append(Layer(block(lambda d: dtext(d, W / 2, yc, cta, cinzelb(52), WHITE, tr=9)), tc, t1, fin=0.4, fout=0.01, rise=20))
    ev.append(('whoosh', tc))
    ys = yc + 100; tsoc = tc + 0.4
    def _soc(d):
        handle = '@espacioinmobiliarioantigua'; fh = cinzelb(31)
        icons = 3 * 46 + 2 * 22
        x = W / 2 - icons / 2; cy = ys + 24
        for kind in 'fit':
            cx = x + 23
            if kind == 'f':
                d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=WHITE)
                ff = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
                bb = d.textbbox((0, 0), 'f', font=ff); d.text((cx - (bb[0] + bb[2]) / 2 + 2, cy - (bb[1] + bb[3]) / 2 + 3), 'f', font=ff, fill=VINO)
            elif kind == 'i':
                d.rounded_rectangle((cx - 21, cy - 21, cx + 21, cy + 21), radius=12, outline=WHITE, width=4)
                d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), outline=WHITE, width=4)
                d.ellipse((cx + 9, cy - 15, cx + 15, cy - 9), fill=WHITE)
            else:
                tiktok(d, cx, cy, 22)
            x += 46 + 22
        dtext(d, W / 2, ys + 64, handle, fh, WHITE, tr=1)
    layers.append(Layer(block(_soc), tsoc, t1, fin=0.4, fout=0.01, rise=16))
    ev.append(('pop', tsoc))
    return layers, ev

def wa_icon(d, cx, cy, r):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE)
    ri = r * 0.66
    d.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), outline=VINO, width=max(3, int(r * 0.12)))
    d.polygon([(cx - ri * 0.95, cy + ri * 0.45), (cx - ri * 1.15, cy + ri * 1.15), (cx - ri * 0.4, cy + ri * 0.9)], fill=VINO)
    # auricular
    sf = ImageFont.truetype(SYM, int(r * 0.85)); g = '✆'
    bb = d.textbbox((0, 0), g, font=sf); d.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), g, font=sf, fill=VINO)

def tiktok(d, cx, cy, r):
    w = max(4, int(r * 0.28))
    d.line((cx + r * 0.05, cy - r * 0.95, cx + r * 0.05, cy + r * 0.45), fill=WHITE, width=w)
    d.ellipse((cx - r * 0.75, cy + r * 0.05, cx + r * 0.2, cy + r * 0.95), outline=WHITE, width=w)
    d.arc((cx + r * 0.05 - 2, cy - r * 1.55, cx + r * 0.95, cy - r * 0.35), 90, 180, fill=WHITE, width=w)

# ------------------------------------------------------------------ video base
GRADE = 'eq=contrast=1.07:saturation=1.15:gamma=1.03,unsharp=5:5:0.55:5:5:0.0'

def seg(a, b, speed=1.0, **kw):
    d = dict(src=(a, b), speed=speed, dur=round((b - a) / speed * FPS) / FPS); d.update(kw); return d

def freeze(t, dur, **kw):
    d = dict(freeze=t, dur=dur); d.update(kw); return d

def render_segments(segs, wd):
    os.makedirs(wd, exist_ok=True)
    for k, s in enumerate(segs):
        out = f'{wd}/s{k:02d}.mp4'; nf = round(s['dur'] * FPS)
        extra = ',gblur=sigma=26,eq=brightness=-0.02' if s.get('blur') else ''
        if 'freeze' in s:
            vf = (f"scale={W}:{H}:flags=lanczos,{GRADE}{extra},trim=end_frame=1,loop=loop=-1:size=1,"
                  f"setpts=N/{FPS}/TB,format=yuv420p")
            cmd = ['-ss', f"{s['freeze']:.3f}", '-i', SRC]
        else:
            a, b = s['src']; sp = s.get('speed', 1.0)
            zoom = ''
            if s.get('push'):   # empuje de cámara lento (zoom suave)
                z = s['push']
                zoom = (f",scale=iw*{1 + z}:ih*{1 + z}:eval=frame,"
                        f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2")
            vf = (f"setpts=(PTS-STARTPTS)/{sp},fps={FPS},scale={W}:{H}:flags=lanczos{zoom},{GRADE}{extra},format=yuv420p")
            cmd = ['-ss', f'{a:.3f}', '-t', f'{(b - a) + 1:.3f}', '-i', SRC]
        subprocess.run(['ffmpeg', '-v', 'error', '-y'] + cmd + ['-vf', vf, '-an', '-frames:v', str(nf),
                        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-r', str(FPS), out], check=True)
        frames = int(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v', '-show_entries',
                                     'stream=nb_read_frames', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout)
        assert frames == nf, (k, frames, nf)

def timeline(segs):
    starts = []; cur = 0.0
    for k, s in enumerate(segs):
        xf = s.get('xf', (None, 0))[1] if k else 0
        st = cur - xf; starts.append(st); cur = st + s['dur']
    return starts, cur

def assemble(segs, wd, layers, audio, out):
    starts, total = timeline(segs)
    NF = round(total * FPS)
    inputs = []; fc = []
    for k in range(len(segs)): inputs += ['-i', f'{wd}/s{k:02d}.mp4']
    fc.append(f'[0:v]settb=1/{FPS},setpts=PTS-STARTPTS[s0]'); cur = '[s0]'; curlen = segs[0]['dur']
    for k, s in enumerate(segs[1:], start=1):
        fc.append(f'[{k}:v]settb=1/{FPS},setpts=PTS-STARTPTS[s{k}]')
        kind, xf = s.get('xf', (None, 0))
        if xf:
            off = curlen - xf
            fc.append(f'{cur}[s{k}]xfade=transition={kind}:duration={xf}:offset={off:.4f},settb=1/{FPS}[j{k}]')
            curlen = off + s['dur']
        else:
            fc.append(f'{cur}[s{k}]concat=n=2:v=1:a=0,settb=1/{FPS}[j{k}]'); curlen += s['dur']
        cur = f'[j{k}]'
    ov = len(segs); au = ov + 1
    inputs += ['-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', 'pipe:0', '-i', audio]
    fc.append(f'[{ov}:v]settb=1/{FPS},setpts=PTS-STARTPTS[ovl]')
    fc.append(f'{cur}[ovl]overlay=0:0:format=auto,fade=t=in:st=0:d=0.25,format=yuv420p[vout]')
    cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + [
        '-filter_complex', ';'.join(fc), '-map', '[vout]', '-map', f'{au}:a',
        '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.2', '-preset', 'medium', '-crf', '18', '-maxrate', '10M', '-bufsize', '20M',
        '-pix_fmt', 'yuv420p', '-r', str(FPS), '-g', '60', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
        '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-movflags', '+faststart', '-frames:v', str(NF), out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(NF):
        p.stdin.write(render_frame(layers, n / FPS).tobytes())
    p.stdin.close(); p.wait(); assert p.returncode == 0
    return total

def still(t_src, path, blur=False):
    extra = ',gblur=sigma=26' if blur else ''
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t_src:.3f}', '-i', SRC, '-frames:v', '1',
                    '-vf', f'scale={W}:{H}:flags=lanczos,{GRADE}{extra}', path], check=True)
    return Image.open(path).convert('RGBA')

def photo_card(img, w, radius=46, border=10):
    """Tarjeta de foto redondeada con borde blanco."""
    h = round(img.height * w / img.width)
    im = img.resize((w, h), Image.LANCZOS)
    m = Image.new('L', (w, h)); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    card = Image.new('RGBA', (w + 2 * border, h + 2 * border))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, w + 2 * border - 1, h + 2 * border - 1), radius=radius + border, fill=WHITE)
    im.putalpha(m); card.alpha_composite(im, (border, border))
    return card

# ------------------------------------------------------------------ audio
SR = 48000
_rng = np.random.default_rng(5)

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)

def lp_fast(x, fc):
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / (1 + (fr / fc) ** 4)
    return np.fft.irfft(X, len(x))

def hp_fast(x, fc):
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(len(x), 1 / SR); X *= 1 / (1 + (fc / np.maximum(fr, 1)) ** 4)
    return np.fft.irfft(X, len(x))

def piano(m, dur, vel=0.6):
    f = mtof(m); n = int((dur + 2.5) * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        if fk > 16000: break
        dec = 1.2 + 0.9 * k + f / 400
        s += (0.9 ** k) / k ** 0.6 * np.sin(2 * np.pi * fk * t + _rng.uniform(0, 6.28)) * np.exp(-t * dec / (1 + 1.5 * (1 - vel)))
    rel = np.ones(n); r0 = int(dur * SR)
    if r0 < n: rel[r0:] = np.exp(-(np.arange(n - r0) / SR) * 3.5)
    return (s * rel * np.minimum(1, t / 0.004) + _rng.normal(0, 1, n) * np.exp(-t * 90) * 0.05) * vel * 0.22

def pad(m, dur, vel=0.5, att=1.2, rel=1.8, bright=2200):
    f = mtof(m); n = int((dur + rel) * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for dc in (-7, -2, 3, 7):
        fd = f * 2 ** (dc / 1200)
        ph = 2 * np.pi * np.cumsum(fd * (1 + 0.003 * np.sin(2 * np.pi * 5 * t + _rng.uniform(0, 6)))) / SR
        s += sum(np.sin(k * ph) / k for k in range(1, 12) if f * k < 12000)
    s = lp_fast(s, bright); env = np.minimum(1, t / att)
    r0 = int(dur * SR); env[r0:] *= np.exp(-(np.arange(n - r0) / SR) * 4 / rel)
    return s * env * vel * 0.05

def reverb(x, secs=2.8, wet=0.3):
    n = int(secs * SR); t = np.arange(n) / SR
    ir = lp_fast(_rng.normal(0, 1, n) * np.exp(-t * 6.9 / secs), 6000); ir /= np.sqrt(np.sum(ir ** 2))
    m = len(x) + n
    return x * (1 - wet) + np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[:len(x)] * wet * 1.4

class Mix:
    def __init__(self, total):
        self.N = int(total * SR) + SR; self.total = total
        self.mus = np.zeros((2, self.N)); self.fx = np.zeros((2, self.N))
    def put(self, bus, sig, t, pan=0.0, gain=1.0):
        i = int(t * SR)
        if sig.ndim == 1:
            sig = np.stack([sig * np.sqrt((1 - pan) / 2), sig * np.sqrt((1 + pan) / 2)]) * np.sqrt(2)
        if i < 0: sig = sig[:, -i:]; i = 0
        j = min(self.N, i + sig.shape[1])
        if j > i: bus[:, i:j] += sig[:, :j - i] * gain

# ---- música
CALM = [(38, [62, 66, 69, 74]), (33, [61, 64, 69, 73]), (35, [59, 62, 66, 71]), (31, [59, 62, 67, 71])]  # D A Bm G

def music_calm(mx, bpm=72, end_hold=True):
    beat = 60 / bpm; bar = 4 * beat; T = mx.total
    for b in range(int(T / bar) + 1):
        t0 = b * bar
        if t0 > T - 1: break
        bass, v = CALM[b % 4]; it = min(1, 0.35 + t0 / T * 0.8)
        arp = [bass + 24, v[0], v[1], v[2], v[3], v[2], v[1], v[0]]
        for k, m in enumerate(arp):
            mx.put(mx.mus, piano(m, beat * 1.5, 0.3 + 0.25 * it), t0 + k * beat / 2 + _rng.uniform(0, .012), pan=-0.3 + 0.08 * k)
        mx.put(mx.mus, piano(bass + 12, bar, 0.45 + 0.2 * it), t0)
        if b >= 2:
            mel = [(0, 78), (1.5, 76), (2, 74), (3, 76)] if (b // 2) % 2 == 0 else [(0, 81), (1, 78), (2, 76), (3, 74)]
            for bt, m in mel:
                if b % 2 and bt > 1: continue
                mx.put(mx.mus, piano(m, beat * 1.8, 0.4 + 0.3 * it), t0 + bt * beat, pan=0.25)
        for m in v[:3]: mx.put(mx.mus, pad(m, bar, 0.2 + 0.6 * it, att=1.4), t0, pan=_rng.uniform(-.5, .5))
        mx.put(mx.mus, pad(bass + 12, bar, 0.5 * it, bright=900), t0)

POP = [(33, [57, 61, 64, 69]), (40, [56, 59, 64, 68]), (42, [57, 61, 66, 69]), (38, [57, 62, 66, 69])]  # A E F#m D

def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t * 32)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 0.9 + _rng.normal(0, 1, n) * np.exp(-t * 300) * 0.08

def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR); t = np.arange(n) / SR
    return hp_fast(_rng.normal(0, 1, n), 7000) * np.exp(-t * (14 if open_ else 70)) * 0.25

def clap():
    n = int(0.3 * SR); t = np.arange(n) / SR; x = _rng.normal(0, 1, n)
    env = sum(np.exp(-np.maximum(t - d, 0) * 60) * (t >= d) for d in (0, 0.011, 0.022)) + np.exp(-t * 12) * 0.4
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1 / SR); X *= np.exp(-((np.log(fr + 1) - np.log(1400)) ** 2) / 0.5)
    return np.fft.irfft(X, n) * env * 0.5

def pluck(m, dur, vel=0.5):
    f = mtof(m); n = int((dur + 0.6) * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * k * t) * (0.55 ** k) * np.exp(-t * (6 + 3 * k)) for k in range(1, 7))
    return s * vel * 0.3 * np.minimum(1, t / 0.003)

def music_pop(mx, bpm=100, drop_at=None, quiet=()):
    """Base alegre: acordes de piano, pluck, bajo, bombo/aplauso/hats. quiet = [(t0,t1)] tramos sin batería."""
    beat = 60 / bpm; bar = 4 * beat; T = mx.total
    def q(t): return any(a <= t < b for a, b in quiet)
    for b in range(int(T / bar) + 1):
        t0 = b * bar
        if t0 > T - 0.5: break
        bass, v = POP[b % 4]
        for bt in (0, 1.5, 2.5):
            for m in v: mx.put(mx.mus, piano(m, beat * 0.9, 0.38), t0 + bt * beat + _rng.uniform(0, .01), pan=_rng.uniform(-.3, .3), gain=0.55)
        for k in range(8):
            m = [v[0] + 12, v[2] + 12, v[1] + 12, v[3] + 12][k % 4]
            mx.put(mx.mus, pluck(m, beat / 2, 0.35), t0 + k * beat / 2, pan=0.4 if k % 2 else -0.4, gain=0.5)
        for bt, ln in ((0, 1.4), (1.5, 0.5), (2, 1.4), (3.5, 0.5)):
            mx.put(mx.mus, lp_fast(pluck(bass + 12, beat * ln, 0.9), 600) * 1.6, t0 + bt * beat)
        mx.put(mx.mus, pad(v[1], bar, 0.25, att=0.6), t0, pan=-0.4)
        for k in range(4):
            tt = t0 + k * beat
            if q(tt): continue
            mx.put(mx.mus, kick(), tt, gain=0.8)
            if k % 2: mx.put(mx.mus, clap(), tt, gain=0.6)
            mx.put(mx.mus, hat(), tt + beat / 2, pan=0.3, gain=0.8)
            mx.put(mx.mus, hat(), tt, pan=-0.2, gain=0.45)

# ---- efectos de sonido
def sfx_whoosh(dur=0.7, f_lo=350, f_hi=5000, gain=0.25):
    n = int(dur * SR); x = np.arange(n) / n; noise = _rng.normal(0, 1, n); out = np.zeros(n)
    hop = 1024; win = np.hanning(2 * hop); fr = np.fft.rfftfreq(2 * hop, 1 / SR)
    for s in range(0, n - 2 * hop, hop):
        p = (s + hop) / n
        fc = f_lo * (f_hi / f_lo) ** (np.sin(np.pi * min(p / 0.7, 1) * 0.5) if p < 0.7 else 1 - (p - 0.7) / 0.3 * 0.6)
        X = np.fft.rfft(noise[s:s + 2 * hop] * win) * np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / (2 * 0.45 ** 2))
        out[s:s + 2 * hop] += np.fft.irfft(X, 2 * hop)
    env = np.where(x < 0.7, (x / 0.7) ** 2.2, np.exp(-(x - 0.7) * 14))
    return out / (np.max(np.abs(out)) + 1e-9) * env * gain

def sfx_pop(gain=0.3, f=900):
    n = int(0.18 * SR); t = np.arange(n) / SR
    ff = f * (1 + 0.8 * np.exp(-t * 60))
    return np.sin(2 * np.pi * np.cumsum(ff) / SR) * np.exp(-t * 28) * gain

def sfx_hit(gain=0.35):
    n = int(2.0 * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(60 + 45 * np.exp(-t * 8)) / SR) * np.exp(-t * 2.4)
    sh = sum(np.sin(2 * np.pi * fr * t) * np.exp(-t * (1.8 + k * .4)) * 0.1 for k, fr in enumerate([880, 1320, 1760, 2640]))
    return (body * 0.9 + sh) * np.minimum(1, t / 0.01) * gain

def sfx_ding(gain=0.22, m=88):
    return sum(np.sin(2 * np.pi * mtof(m) * r * np.arange(int(1.5 * SR)) / SR) * a * np.exp(-np.arange(int(1.5 * SR)) / SR * d)
               for r, a, d in ((1, 1, 3), (2.76, 0.4, 6), (5.4, 0.2, 9))) * gain

def sfx_scribble(dur=0.45, gain=0.25):
    n = int(dur * SR); t = np.arange(n) / SR
    x = hp_fast(_rng.normal(0, 1, n), 1800) * (0.6 + 0.4 * np.sin(2 * np.pi * 18 * t) ** 2)
    return x * np.minimum(1, t / 0.02) * np.exp(-np.maximum(t - dur * 0.7, 0) * 25) * gain * 0.5

def sfx_tick(gain=0.25):
    n = int(0.05 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2400 * t) * 0.6 + hp_fast(_rng.normal(0, 1, n), 3000) * 0.4) * np.exp(-t * 120) * gain

def sfx_shutter(gain=0.3):
    n = int(0.25 * SR); t = np.arange(n) / SR; x = hp_fast(_rng.normal(0, 1, n), 1200)
    env = np.exp(-t * 80) + np.exp(-np.maximum(t - 0.07, 0) * 70) * (t > 0.07) * 0.8
    return x * env * gain * 0.6 + sfx_hit(0.12)[:n] * 0.5

def sfx_riser(dur=1.5, gain=0.18):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 200 * (8 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    return (tone + sfx_whoosh(dur, 300, 7000, 1.0)[:n] * 0.6) * (t / dur) ** 2 * gain

FX = {'whoosh': lambda: sfx_whoosh(), 'pop': lambda: sfx_pop(), 'logo': lambda: sfx_hit(0.3), 'hit': lambda: sfx_hit(),
      'ding': lambda: sfx_ding(), 'scribble': lambda: sfx_scribble(), 'tick': lambda: sfx_tick(),
      'shutter': lambda: sfx_shutter(), 'draw': lambda: sfx_whoosh(1.5, 250, 2500, 0.15), 'riser': lambda: sfx_riser()}
LEAD = {'whoosh': 0.49, 'draw': 0.2, 'riser': 1.5}

def save(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1).T * 32767).astype('<i2').tobytes())

def master(mx, events, out, music_gain=0.5, fade_out=1.5, reverb_music=True):
    for name, t in events:
        mx.put(mx.fx, FX[name](), t - LEAD.get(name, 0), pan=_rng.uniform(-0.25, 0.25))
    m = mx.mus
    if reverb_music: m = np.stack([reverb(m[0], 2.6, 0.3), reverb(m[1], 2.8, 0.3)])
    m = m / (np.max(np.abs(m)) + 1e-9) * music_gain
    mix = (m + mx.fx)[:, :int(mx.total * SR)]
    f = int(fade_out * SR); mix[:, -f:] *= np.linspace(1, 0, f) ** 2
    tmp = out + '.pre.wav'; save(tmp, mix / max(1, np.max(np.abs(mix)) / 0.95))
    r = subprocess.run(['ffmpeg', '-i', tmp, '-af', 'loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    j = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    ln = (f"loudnorm=I=-14:TP=-1.0:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', ln + ',aresample=48000', '-ar', '48000', out], check=True)
    os.remove(tmp)
