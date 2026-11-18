# Generates all overlay graphics (RGBA 1080x1920 PNGs) + cue list (cues.json)
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json, os
from edl import SEGS, VOICE, SUBS, timeline
os.makedirs('gfx', exist_ok=True)
W, H = 1080, 1920
BEIGE = (231, 211, 175); VINO = (102, 30, 26); WHITE = (255, 255, 255)
F = 'fonts/'
FT = ['lnum', 'kern']

def font(name, size, wght):
    f = ImageFont.truetype(F + name, size)
    f.set_variation_by_axes([wght]); return f

def corm(size, w=500): return font('Cormorant.ttf', size, w)
def cormi(size, w=500): return font('CormorantItalic.ttf', size, w)
def mont(size, w=500): return font('Montserrat.ttf', size, w)

def text_w(txt, f, track=0):
    if not track: return f.getlength(txt, features=FT)
    return sum(f.getlength(c, features=FT) for c in txt) + track * (len(txt) - 1)

def draw_text(d, cx, y, txt, f, fill, track=0, anchor='center'):
    w = text_w(txt, f, track)
    x = cx - w / 2 if anchor == 'center' else cx
    if not track:
        d.text((x, y), txt, font=f, fill=fill, features=FT); return w
    for c in txt:
        d.text((x, y), c, font=f, fill=fill, features=FT); x += f.getlength(c, features=FT) + track
    return w

def with_shadow(layer, radius=10, alpha=170, scrim=None):
    """Composite a soft shadow under layer; optional radial scrim box (x0,y0,x1,y1,alpha)."""
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if scrim:
        x0, y0, x1, y1, a = scrim
        s = Image.new('L', (W, H), 0); sd = ImageDraw.Draw(s)
        sd.rounded_rectangle((x0, y0, x1, y1), radius=80, fill=a)
        s = s.filter(ImageFilter.GaussianBlur(70))
        out.paste(Image.new('RGBA', (W, H), (20, 8, 6, 255)), (0, 0), s)
    a = layer.split()[3].point(lambda v: v * alpha // 255).filter(ImageFilter.GaussianBlur(radius))
    sh = Image.new('RGBA', (W, H), (10, 4, 3, 255)); sh.putalpha(a)
    out = Image.alpha_composite(out, sh)
    return Image.alpha_composite(out, layer)

def save(img, name):
    p = f'gfx/{name}.png'; img.save(p); return p

cues = []
def cue(png, start, dur, kind='text', fin=0.55, fout=0.45, rise=22):
    cues.append(dict(png=png, start=round(start, 3), dur=round(dur, 3), fin=fin, fout=fout, rise=rise, kind=kind))

tl, TOTAL = timeline()

# ---------- Title: BELLAVISTA ----------
L = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(L)
y = 300
draw_text(d, W / 2, y, 'BELLAVISTA', corm(118, 600), WHITE, track=14)
d.line((W / 2 - 70, y + 165, W / 2 + 70, y + 165), fill=BEIGE, width=3)
draw_text(d, W / 2, y + 188, 'Un estilo de vida extraordinario', cormi(52, 500), BEIGE)
img = with_shadow(L, 14, 210, scrim=(120, y - 50, 960, y + 290, 175))
cue(save(img, 'title'), 0.45, tl['b'][0] + 2.6 - 0.45, fin=0.9, fout=0.6, rise=30)

# ---------- Feature blocks ----------
def feature_numbers(rows, name):
    L = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(L)
    y = 290
    d.line((W / 2 - 50, y, W / 2 + 50, y), fill=BEIGE, width=3); y += 26
    for big, small in rows:
        draw_text(d, W / 2, y, big, corm(96, 600), WHITE); y += 108
        draw_text(d, W / 2, y, small, mont(28, 600), BEIGE, track=6); y += 62
    img = with_shadow(L, 12, 200, scrim=(200, 250, 880, y + 30, 165))
    return save(img, name)

def feature_lines(lines, name):
    L = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(L)
    y = 300
    d.line((W / 2 - 50, y, W / 2 + 50, y), fill=BEIGE, width=3); y += 34
    for i, t in enumerate(lines):
        draw_text(d, W / 2, y, t, cormi(66, 600), WHITE); y += 84
    img = with_shadow(L, 12, 200, scrim=(150, 260, 930, y + 30, 165))
    return save(img, name)

f1 = feature_numbers([('315 m²', 'DE CONSTRUCCIÓN'), ('180 m²', 'DE TERRENO')], 'feat1')
cue(f1, tl['d'][0] + 0.3, tl['e'][1] - tl['d'][0] - 0.6)
f2 = feature_numbers([('3', 'HABITACIONES'), ('3.5', 'BAÑOS')], 'feat2')
cue(f2, tl['k'][0] + 0.5, tl['l'][1] - tl['k'][0] - 0.8)
f3 = feature_lines(['Sala familiar', '2 patios', 'Terraza con pérgola'], 'feat3')
cue(f3, tl['r'][0] + 0.6, tl['s'][1] - tl['r'][0] - 0.8)
f4 = feature_lines(['Dormitorio de servicio', 'Parqueo para 2 vehículos'], 'feat4')
cue(f4, tl['u'][0] + 0.35, tl['v'][0] + 0.2 - tl['u'][0] - 0.35)

# ---------- Price card (over segment v) ----------
v0, v1 = tl['v']
def layer(fn):
    L = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(L); fn(d); return with_shadow(L, 10, 160)
p1 = save(layer(lambda d: (draw_text(d, W/2, 470, 'CASA EN VENTA', mont(34, 600), BEIGE, track=10),
                           draw_text(d, W/2, 525, 'RESIDENCIAL BELLAVISTA', corm(70, 600), WHITE, track=4))), 'price1')
def _p2(d):
    d.line((W/2 - 60, 660, W/2 + 60, 660), fill=BEIGE, width=3)
    draw_text(d, W/2, 690, 'US$550,000', corm(150, 600), WHITE, track=2)
    draw_text(d, W/2, 870, 'MÁS IMPUESTOS', mont(32, 600), BEIGE, track=10)
    d.line((W/2 - 60, 955, W/2 + 60, 955), fill=BEIGE, width=3)
p2 = save(layer(_p2), 'price2')
def _p3(d):
    y = 1000
    for t in ['315 m² DE CONSTRUCCIÓN', '180 m² DE TERRENO', '3 HABITACIONES  |  3.5 BAÑOS', 'PARQUEO PARA 2 VEHÍCULOS']:
        draw_text(d, W/2, y, t, mont(34, 500), WHITE, track=4); y += 62
p3 = save(layer(_p3), 'price3')
end_v = v1 - 0.6
import numpy as np
yy, xx = np.mgrid[0:H, 0:W]
a = 0.62 + 0.25 * np.exp(-(((yy - 860) / 520.0) ** 2))
sc = np.zeros((H, W, 4), np.uint8); sc[..., 0], sc[..., 1], sc[..., 2] = 70, 18, 15
sc[..., 3] = (np.clip(a, 0, 0.9) * 255).astype(np.uint8)
cue(save(Image.fromarray(sc, 'RGBA'), 'price_scrim'), v0 + 0.1, v1 - v0 - 0.1, fin=0.9, fout=0.01, rise=0)
cue(p1, v0 + 0.5, end_v - (v0 + 0.5), fin=0.7, fout=0.5)
cue(p2, v0 + 1.3, end_v - (v0 + 1.3), fin=0.8, fout=0.5, rise=16)
cue(p3, v0 + 2.3, end_v - (v0 + 2.3), fin=0.8, fout=0.5, rise=16)

# ---------- Final brand card (over segment w) ----------
w0, w1 = tl['w']
q = save(layer(lambda d: draw_text(d, W/2, 380, '¿Te imaginas viviendo aquí?', cormi(76, 600), WHITE)), 'final_q')
logo = Image.open('logo/t3.png').convert('RGBA').crop((51, 48, 450, 418))
lw = 560; lh = round(logo.height * lw / logo.width)
logo = logo.resize((lw, lh), Image.LANCZOS)
r, g, b, a = logo.split()
logo_beige = Image.merge('RGBA', (r.point(lambda v: BEIGE[0]), g.point(lambda v: BEIGE[1]), b.point(lambda v: BEIGE[2]), a))
LL = Image.new('RGBA', (W, H)); LL.paste(logo_beige, ((W - lw) // 2, 560), logo_beige)
lg = save(LL, 'final_logo')
def _cta(d):
    y = 560 + lh + 90
    # AGENDA TU VISITA pill
    t = 'AGENDA TU VISITA'; f = mont(36, 700); tw = text_w(t, f, 8)
    d.rounded_rectangle((W/2 - tw/2 - 46, y - 22, W/2 + tw/2 + 46, y + 66), radius=44, outline=BEIGE, width=3)
    draw_text(d, W/2, y, t, f, WHITE, track=8)
    y += 150
    draw_text(d, W/2, y, 'DANI ÁLVAREZ', corm(64, 600), WHITE, track=8)
    draw_text(d, W/2, y + 82, 'ESPACIO INMOBILIARIO', mont(28, 600), BEIGE, track=10)
cta = save(layer(_cta), 'final_cta')
cue(q, w0 + 0.5, w1 - (w0 + 0.5), fin=0.8, fout=0.01, rise=18)
cue(lg, w0 + 0.9, w1 - (w0 + 0.9), fin=1.0, fout=0.01, rise=0)
cue(cta, w0 + 1.6, w1 - (w0 + 1.6), fin=0.8, fout=0.01, rise=14)

# ---------- Subtitles ----------
vmap = {v[0]: v for v in VOICE}
sf = mont(44, 600)
n = 0
for clip, chunks in SUBS.items():
    _, a, b, anc, off = vmap[clip]
    base = tl[anc][0] + off - a  # timeline = base + src
    for txt, s0, s1 in chunks:
        L = Image.new('RGBA', (W, H)); d = ImageDraw.Draw(L)
        tw = sf.getlength(txt); y = 1395
        bg = Image.new('RGBA', (W, H)); bd = ImageDraw.Draw(bg)
        bd.rounded_rectangle((W/2 - tw/2 - 30, y - 16, W/2 + tw/2 + 30, y + 66), radius=20, fill=(18, 8, 6, 165))
        d.text((W/2 - tw/2, y), txt, font=sf, fill=WHITE)
        img = Image.alpha_composite(bg, with_shadow(L, 6, 150))
        p = save(img, f'sub{n:02d}'); n += 1
        cue(p, base + s0, s1 - s0, kind='sub', fin=0.12, fout=0.1, rise=0)

json.dump(dict(cues=cues, total=TOTAL), open('cues.json', 'w'), indent=1, ensure_ascii=False)
print(len(cues), 'cues; total', TOTAL)
