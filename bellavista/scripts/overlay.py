# Animated overlay track (titles, data, kinetic captions, closing) rendered frame-by-frame as RGBA.
# Style follows the client's reference reels: bright, light soft shadows, beige serif italics,
# bold spaced sans caps, wine pills, word-by-word captions.
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, json, re
from edl import SEGS, VOICE, SUBS, timeline, FPS
W, H = 1080, 1920
BEIGE = (231, 211, 175); VINO = (102, 30, 26); WHITE = (255, 255, 255)
FT = ['lnum', 'kern']
SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def font(name, size, wght):
    f = ImageFont.truetype('fonts/' + name, size); f.set_variation_by_axes([wght]); return f
corm = lambda s, w=600: font('Cormorant.ttf', s, w)
cormi = lambda s, w=600: font('CormorantItalic.ttf', s, w)
mont = lambda s, w=600: font('Montserrat.ttf', s, w)

def tw(t, f, tr=0):
    if not tr: return f.getlength(t, features=FT)
    return sum(f.getlength(c, features=FT) for c in t) + tr * (len(t) - 1)

def dtext(d, x, y, t, f, fill, tr=0, center=True):
    w = tw(t, f, tr); x = x - w / 2 if center else x
    if not tr: d.text((x, y), t, font=f, fill=fill, features=FT); return w
    for c in t:
        d.text((x, y), c, font=f, fill=fill, features=FT); x += f.getlength(c, features=FT) + tr
    return w

def shadowed(L, radius=7, alpha=120, dy=3):
    a = L.split()[3].point(lambda v: v * alpha // 255).filter(ImageFilter.GaussianBlur(radius))
    sh = Image.new('RGBA', L.size, (25, 12, 8, 255)); sh.putalpha(a)
    out = Image.new('RGBA', L.size); out.alpha_composite(sh, (0, dy)); out.alpha_composite(L)
    return out

class Layer:
    def __init__(self, img, t0, t1, fin=0.5, fout=0.4, rise=18, scale_in=False):
        bb = img.getbbox() or (0, 0, 1, 1)
        pad = 2
        bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(W, bb[2] + pad), min(H, bb[3] + pad))
        self.x, self.y = bb[0], bb[1]
        a = np.asarray(img.crop(bb)).astype(np.float32) / 255.0
        self.rgb = a[..., :3]; self.a = a[..., 3:4]
        self.t0, self.t1, self.fin, self.fout, self.rise = t0, t1, fin, fout, rise
    def alpha_at(self, t):
        if t < self.t0 or t >= self.t1: return 0.0, 0
        k = 1.0
        if self.fin > 0: k = min(k, (t - self.t0) / self.fin)
        if self.fout > 0: k = min(k, (self.t1 - t) / self.fout)
        k = max(0.0, min(1.0, k))
        e = 1 - (1 - min(1.0, (t - self.t0) / max(self.fin * 1.3, 1e-3))) ** 3
        return k * k * (3 - 2 * k), int(round(self.rise * (1 - e)))

layers = []
tl, TOTAL = timeline()
def canvas(): return Image.new('RGBA', (W, H))

# ---------------- Title ----------------
L = canvas(); d = ImageDraw.Draw(L)
dtext(d, W / 2, 330, 'BELLAVISTA', corm(122, 600), WHITE, tr=16)
dtext(d, W / 2, 480, 'Un estilo de vida extraordinario', cormi(60, 600), BEIGE)
layers.append(Layer(shadowed(L, 11, 200, 3), 0.45, tl['b'][0] + 2.7, fin=1.0, fout=0.6, rise=26))

# ---------------- Data blocks ----------------
def data_numbers(rows, y=250):
    L = canvas(); d = ImageDraw.Draw(L)
    for big, small in rows:
        dtext(d, W / 2, y, big, corm(118, 700), WHITE); y += 132
        dtext(d, W / 2, y, small, mont(30, 700), WHITE, tr=8); y += 78
    return shadowed(L, 12, 215, 3)

def data_italic(big, small, y=260):
    L = canvas(); d = ImageDraw.Draw(L)
    dtext(d, W / 2, y, big, cormi(104, 700), WHITE)
    dtext(d, W / 2, y + 128, small, mont(32, 700), WHITE, tr=8)
    return shadowed(L, 12, 215, 3)

def icon_house(d, cx, cy, r, col):
    d.polygon([(cx - r * .55, cy - r * .02), (cx, cy - r * .5), (cx + r * .55, cy - r * .02)], fill=col)
    d.rectangle((cx - r * .38, cy - r * .05, cx + r * .38, cy + r * .42), fill=col)
    d.rectangle((cx - r * .1, cy + r * .12, cx + r * .1, cy + r * .42), fill=VINO)

def pill(bold, ital, y, x_center=W / 2, icon=icon_house):
    L = canvas(); d = ImageDraw.Draw(L)
    fb = mont(34, 700); fi = cormi(38, 600)
    wb = tw(bold, fb, 3); wi = tw(ital, fi)
    inner = max(wb, wi); ic = 78
    w = inner + ic + 70; h = 128
    x0 = x_center - w / 2
    d.rounded_rectangle((x0, y, x0 + w, y + h), radius=h / 2, fill=VINO + (235,), outline=BEIGE + (200,), width=2)
    cx, cy = x0 + 22 + ic / 2, y + h / 2
    d.ellipse((cx - ic / 2, cy - ic / 2, cx + ic / 2, cy + ic / 2), fill=BEIGE)
    icon(d, cx, cy, ic * 0.62, VINO)
    tx = x0 + 22 + ic + 22
    dtext(d, tx, y + 20, bold, fb, WHITE, tr=3, center=False)
    dtext(d, tx, y + 64, ital, fi, BEIGE, center=False)
    return shadowed(L, 12, 120, 5)

layers.append(Layer(data_numbers([('315 m²', 'DE CONSTRUCCIÓN'), ('180 m²', 'DE TERRENO')]),
                    tl['d'][0] + 0.3, tl['e'][1] - 0.3, rise=22))
# shown on the upstairs B-roll (not over Dani)
layers.append(Layer(data_italic('3 habitaciones', '3.5 BAÑOS'), tl['l'][0] + 0.05, tl['l'][1] + 0.9, rise=22))
layers.append(Layer(pill('SALA FAMILIAR  ·  2 PATIOS', 'terraza con pérgola', 300),
                    tl['r'][0] + 0.5, tl['s'][1] - 0.3, fin=0.45, rise=20))
layers.append(Layer(pill('DORMITORIO DE SERVICIO', 'parqueo para 2 vehículos', 300),
                    tl['u'][0] + 0.4, tl['v'][0] + 0.75, fin=0.45, rise=20))

# ---------------- Kinetic captions ----------------
STOP = set('a al de del el en la las los y o con por para sus su mis mi que se nos una uno un te es esta este esa sino no solo ya'.split())
words_db = json.load(open('transcripts.json'))
vmap = {v[0]: v for v in VOICE}
fw_bold = mont(50, 800); fw_ital = cormi(66, 700)
SPACE = 18; MAXW = 900; CAP_Y = 1300
def word_style(w):
    core = re.sub(r'[^\wáéíóúñü-]', '', w.lower())
    if core in STOP: return w, fw_ital, False
    return w.upper(), fw_bold, True

for clip, chunks in SUBS.items():
    _, a, b, anc, off = vmap[clip]
    base = tl[anc][0] + off - a
    wd = words_db[clip + '.mp4']['words']
    for ci, (txt, s0, s1) in enumerate(chunks):
        toks = txt.split()
        ws = [w for w in wd if s0 - 0.15 <= w[1] < s1 - 0.05]
        if len(ws) == len(toks):
            starts = [max(s0, w[1]) for w in ws]
        else:
            lens = np.array([len(t) + 2 for t in toks], float)
            starts = list(s0 + (s1 - 0.3 - s0) * np.concatenate([[0], np.cumsum(lens)[:-1]]) / lens.sum())
        # layout (wrap)
        styled = [word_style(t) for t in toks]
        widths = [tw(t, f) for t, f, _ in styled]
        lines = [[]]; cur = 0
        for i, wv in enumerate(widths):
            if lines[-1] and cur + SPACE + wv > MAXW:
                lines.append([]); cur = 0
            cur += (SPACE if lines[-1] else 0) + wv; lines[-1].append(i)
        y = CAP_Y - (len(lines) - 1) * 40
        end = s1 + 0.12
        if ci + 1 < len(chunks): end = min(end, chunks[ci + 1][1])
        for line in lines:
            lw = sum(widths[i] for i in line) + SPACE * (len(line) - 1)
            x = W / 2 - lw / 2
            for i in line:
                t, f, bold = styled[i]
                L = canvas(); d = ImageDraw.Draw(L)
                yy = y + (0 if bold else -9)
                d.text((x, yy), t, font=f, fill=WHITE, features=FT)
                layers.append(Layer(shadowed(L, 5, 215, 2), base + starts[i] - 0.03, base + end,
                                    fin=0.14, fout=0.12, rise=10))
                x += widths[i] + SPACE
            y += 80

# ---------------- Closing (over blurred façade, segment v) ----------------
v0, v1 = tl['v']
A0 = v0 + 0.5; A1 = v0 + 3.85          # price phase
B0 = A1 + 0.1; B1 = TOTAL             # brand phase
def blk(fn):
    L = canvas(); d = ImageDraw.Draw(L); fn(d); return shadowed(L, 10, 200, 3)
layers.append(Layer(blk(lambda d: (dtext(d, W/2, 520, 'CASA EN VENTA', mont(34, 700), WHITE, tr=10),
                                   dtext(d, W/2, 575, 'RESIDENCIAL BELLAVISTA', corm(76, 700), WHITE, tr=3))),
                    A0, A1, fin=0.6, fout=0.4))
def _price(d):
    dtext(d, W/2, 700, 'US$550,000', corm(160, 650), WHITE, tr=2)
    dtext(d, W/2, 895, 'MÁS IMPUESTOS', mont(32, 700), BEIGE, tr=10)
layers.append(Layer(blk(_price), A0 + 0.35, A1, fin=0.6, fout=0.35, rise=14))
def _specs(d):
    y = 1010
    d.line((W/2 - 60, y, W/2 + 60, y), fill=BEIGE, width=3); y += 40
    for t in ['315 m² DE CONSTRUCCIÓN', '180 m² DE TERRENO', '3 HABITACIONES  |  3.5 BAÑOS', 'PARQUEO PARA 2 VEHÍCULOS']:
        dtext(d, W/2, y, t, mont(36, 600), WHITE, tr=4); y += 64
layers.append(Layer(blk(_specs), A0 + 0.8, A1, fin=0.6, fout=0.35, rise=14))

layers.append(Layer(blk(lambda d: dtext(d, W/2, 330, '¿TE IMAGINAS VIVIENDO AQUÍ?', corm(58, 650), WHITE, tr=2)),
                    B0, B1, fin=0.6, fout=0.01, rise=14))
logo = Image.open('logo/t3.png').convert('RGBA').crop((51, 48, 450, 418))
lw = 470; lh = round(logo.height * lw / logo.width); logo = logo.resize((lw, lh), Image.LANCZOS)
LG = canvas(); LG.alpha_composite(logo, ((W - lw) // 2, 440))
layers.append(Layer(shadowed(LG, 10, 140, 4), B0 + 0.25, B1, fin=0.8, fout=0.01, rise=0))
def phone_pill(d, y, num):
    f = mont(40, 700); w = tw(num, f, 1) + 130; h = 82; x0 = W/2 - w/2
    d.rounded_rectangle((x0, y, x0 + w, y + h), radius=h/2, fill=VINO + (240,))
    cx, cy = x0 + 46, y + h/2
    d.ellipse((cx - 25, cy - 25, cx + 25, cy + 25), fill=WHITE)
    sf = ImageFont.truetype(SYM, 30); g = '✆'
    bb = d.textbbox((0, 0), g, font=sf); d.text((cx - (bb[0]+bb[2])/2, cy - (bb[1]+bb[3])/2), g, font=sf, fill=VINO)
    dtext(d, x0 + 92, y + 16, num, f, WHITE, tr=1, center=False)
def _contact(d):
    y = 440 + lh + 50
    phone_pill(d, y, '+502 5565-4621'); phone_pill(d, y + 102, '+502 5952-8514')
    y += 230
    dtext(d, W/2, y, 'AGENDA TU VISITA', mont(38, 800), WHITE, tr=8)
    y += 76
    # social row
    y += 20; handle = '@espacio.inmobiliariogt'; fh = mont(32, 600)
    total = 3 * 40 + 2 * 12 + 20 + tw(handle, fh); x = W/2 - total/2
    for kind in 'fit':
        cx, cy = x + 20, y + 22
        if kind == 'f':
            d.ellipse((cx - 19, cy - 19, cx + 19, cy + 19), fill=WHITE)
            ff = mont(30, 800); d.text((cx - 7, cy - 21), 'f', font=ff, fill=VINO)
        elif kind == 'i':
            d.rounded_rectangle((cx - 18, cy - 18, cx + 18, cy + 18), radius=10, outline=WHITE, width=4)
            d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), outline=WHITE, width=4)
            d.ellipse((cx + 8, cy - 13, cx + 13, cy - 8), fill=WHITE)
        else:
            sf = ImageFont.truetype(SYM, 40); bb = d.textbbox((0, 0), '♪', font=sf)
            d.text((cx - (bb[0]+bb[2])/2, cy - (bb[1]+bb[3])/2), '♪', font=sf, fill=WHITE)
        x += 52
    d.text((x + 8, y + 2), handle, font=fh, fill=WHITE)
layers.append(Layer(blk(_contact), B0 + 0.6, B1, fin=0.7, fout=0.01, rise=12))

def frame(t):
    out = np.zeros((H, W, 4), np.float32)
    for ly in layers:
        k, dy = ly.alpha_at(t)
        if k <= 0: continue
        y0 = ly.y + dy; h, w = ly.a.shape[:2]
        y1 = min(H, y0 + h); hh = y1 - y0
        if hh <= 0: continue
        reg = out[y0:y1, ly.x:ly.x + w]
        a = ly.a[:hh] * k
        ra = reg[..., 3:4]
        na = a + ra * (1 - a)
        rgb = (ly.rgb[:hh] * a + reg[..., :3] * ra * (1 - a)) / np.maximum(na, 1e-6)
        reg[..., :3] = rgb; reg[..., 3:4] = na
    return (out * 255 + 0.5).astype(np.uint8)

if __name__ == '__main__':
    import sys
    for t in map(float, sys.argv[1:]):
        Image.fromarray(frame(t), 'RGBA').save(f'st/ov_{t}.png')
    print(len(layers), 'layers')
