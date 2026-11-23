"""Historia 'Adivina el precio' — Espacio Inmobiliario.
Genera los cuadros 1080x1920 a 30 fps y los manda a ffmpeg (video sin audio).
Uso: python3 render.py <carpeta_trabajo>   (img/, fontpkg/ y logos dentro)
"""
import sys, math, subprocess, collections
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H, FPS = 1080, 1920, 30
WORK = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else WORK + "/video_mudo.mp4"
LOGO_DIR = sys.argv[3] if len(sys.argv) > 3 else "/home/user/espacio-inmobiliaro/bellavista/logo"

BEIGE = (231, 211, 175)
VINO = (102, 30, 26)
WHITE = (255, 255, 255)

FD = WORK + "/fontpkg/"
CINZEL_B = FD + "fontsource-cinzel-5.0.8/files/cinzel-latin-700-normal.woff"
CINZEL_R = FD + "fontsource-cinzel-5.0.8/files/cinzel-latin-400-normal.woff"
SCRIPT = FD + "fontsource-great-vibes-5.0.8/files/great-vibes-latin-400-normal.woff"

# ---------- tiempos (sincronizados al pulso de la canción) ----------
B = 60 / 117.45          # un pulso
O = 0.43                 # fase del primer pulso
def beat(k): return O + k * B
T_HOOK_END = beat(4)
PROP_LEN = 8 * B
T_TEASE = beat(36)
T_JOYA = beat(39)
T_END = beat(47)
TOTAL = 28.4
NFR = int(round(TOTAL * FPS))

# orden de menor a mayor precio
PROPS = [
    ("condado",    (108, 1025, 505, 1110)),
    ("bellavista", (68, 555, 490, 632)),
    ("gardens400", (108, 1025, 615, 1110)),
    ("gardens460", (108, 1025, 625, 1110)),
    ("hacienda",   (70, 555, 490, 632)),
]
STARTS = [beat(4 + 8 * i) for i in range(4)] + [T_JOYA]

# ---------- utilidades ----------
_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]

def text_layer(txt, path, size, color, tracking=0, shadow=True, shadow_alpha=150):
    """Texto en un RGBA recortado, con espaciado y sombra suave."""
    f = font(path, size)
    widths = [f.getlength(c) for c in txt]
    tw = int(sum(widths) + tracking * (len(txt) - 1)) + 4
    asc, desc = f.getmetrics()
    pad = int(size * 0.35)
    im = Image.new("RGBA", (tw + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for c, w in zip(txt, widths):
        d.text((x, pad), c, font=f, fill=color + (255,))
        x += w + tracking
    if shadow:
        a = im.split()[3]
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: v * shadow_alpha // 255).filter(ImageFilter.GaussianBlur(size * 0.12)))
        sh = ImageChops.offset(sh, 0, max(2, size // 22))
        sh.alpha_composite(im)
        im = sh
    return im

def letters_layers(txt, path, size, color, tracking=0):
    """Una capa por letra para que aparezcan una a una (devuelve lista de (img, x))."""
    f = font(path, size)
    out, x = [], 0
    for c in txt:
        w = f.getlength(c)
        if c != " ":
            out.append((text_layer(c, path, size, color), x))
        x += w + tracking
    return out, x

def paste_center(base, layer, cx, cy, alpha=1.0, scale=1.0):
    if alpha <= 0.003:
        return
    if scale != 1.0:
        layer = layer.resize((max(1, int(layer.width * scale)), max(1, int(layer.height * scale))), Image.LANCZOS)
    if alpha < 1:
        a = layer.split()[3].point(lambda v: int(v * alpha))
        layer = layer.copy(); layer.putalpha(a)
    base.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))

def ease_out(t): t = min(max(t, 0), 1); return 1 - (1 - t) ** 3
def ease_back(t):
    t = min(max(t, 0), 1); c1 = 1.9; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
def clamp(t): return min(max(t, 0.0), 1.0)

def cover_fill(im, w, h):
    s = max(w / im.width, h / im.height)
    r = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x = (r.width - w) // 2; y = (r.height - h) // 2
    return r.crop((x, y, x + w, y + h))

def tinted_bg(im, blur=38, tint=VINO, amount=0.55, dark=0.0):
    bg = cover_fill(im, W, H).filter(ImageFilter.GaussianBlur(blur)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), tint + (int(255 * amount),))
    bg.alpha_composite(ov)
    if dark:
        bg.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dark))))
    return bg

def rounded(im, r):
    m = Image.new("L", (im.width * 3, im.height * 3), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, m.width - 1, m.height - 1), r * 3, fill=255)
    m = m.resize(im.size, Image.LANCZOS)
    out = im.convert("RGBA"); out.putalpha(m)
    return out

def shadow_of(card, blur=30, alpha=170, grow=10):
    sh = Image.new("RGBA", (card.width + 4 * blur, card.height + 4 * blur), (0, 0, 0, 0))
    a = Image.new("L", sh.size, 0)
    a.paste(card.split()[3].point(lambda v: v * alpha // 255), (2 * blur, 2 * blur + grow))
    sh.putalpha(a.filter(ImageFilter.GaussianBlur(blur)))
    return sh

def zoom_blur(frame, amount, n=7):
    """Desenfoque radial (zoom blur) desde el centro."""
    if amount < 0.004:
        return frame
    acc = np.asarray(frame, dtype=np.float32)
    tot = acc.copy()
    for i in range(1, n):
        s = 1 + amount * i / (n - 1)
        r = frame.resize((int(W * s), int(H * s)), Image.BILINEAR)
        x = (r.width - W) // 2; y = (r.height - H) // 2
        tot += np.asarray(r.crop((x, y, x + W, y + H)), dtype=np.float32)
    return Image.fromarray((tot / n).astype(np.uint8), "RGBA")

def ss(size, fn):
    """Dibuja a 4x y reduce (antialias) — fn(draw, k)."""
    k = 4
    im = Image.new("RGBA", (size[0] * k, size[1] * k), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), k)
    return im.resize(size, Image.LANCZOS)

# ---------- recursos ----------
IMG = {n: Image.open(f"{WORK}/img/{n}.jpg").convert("RGB") for n, _ in PROPS}

class Prop:
    def __init__(self, name, box, idx):
        im = IMG[name]
        self.idx = idx
        portrait = im.height > im.width
        cw = 880 if portrait else 960
        self.s = cw / im.width
        ch = int(im.height * self.s)
        self.card = rounded(im.resize((cw, ch), Image.LANCZOS), 34)
        self.shadow = shadow_of(self.card)
        self.cx, self.cy = W // 2, (1010 if portrait else 1000)
        self.x0 = self.cx - cw // 2; self.y0 = self.cy - ch // 2
        self.bg = tinted_bg(im, amount=0.6, dark=0.15)
        bx0, by0, bx1, by1 = [v * self.s for v in box]
        self.box = (bx0, by0, bx1, by1)  # en coordenadas de la tarjeta
        bw, bh = int(bx1 - bx0) + 12, int(by1 - by0) + 12
        # tapa del precio
        def draw_cover(d, k):
            d.rounded_rectangle((0, 0, bw * k - 1, bh * k - 1), 16 * k, fill=VINO + (255,), outline=BEIGE + (255,), width=3 * k)
        self.cover = ss((bw, bh), draw_cover)
        q = text_layer("? ? ?", CINZEL_B, int(bh * 0.62), BEIGE, tracking=6, shadow=False)
        paste_center(self.cover, q, bw / 2, bh / 2 + 2)
        def draw_glow(d, k):
            d.rounded_rectangle((6 * k, 6 * k, (bw + 18) * k, (bh + 18) * k), 20 * k, outline=BEIGE + (255,), width=5 * k)
        self.glow = ss((bw + 24, bh + 24), draw_glow).filter(ImageFilter.GaussianBlur(1.2))
        self.glow_soft = self.glow.filter(ImageFilter.GaussianBlur(10))

PROPOBJ = [Prop(n, b, i) for i, (n, b) in enumerate(PROPS)]

# textos fijos
LBL = [text_layer(f"PROPIEDAD {i+1} DE 5", CINZEL_R, 34, WHITE, tracking=5) for i in range(5)]
Q_TXT = text_layer("¿CUÁNTO CUESTA?", CINZEL_B, 70, BEIGE, tracking=2)
A_TXT = text_layer("¿LE ATINASTE?", CINZEL_B, 70, WHITE, tracking=2)
JOYA_TXT = text_layer("LA JOYA", CINZEL_B, 76, BEIGE, tracking=6)
HINT = text_layer("adivina antes de que se revele", SCRIPT, 62, WHITE)
def _badge(n):
    def f(d, k):
        r = 250 * k
        d.ellipse((0, 0, r - 1, r - 1), fill=VINO + (235,), outline=BEIGE + (255,), width=6 * k)
    b = ss((250, 250), f)
    paste_center(b, text_layer(str(n), CINZEL_B, 190, BEIGE, shadow=False), 125, 125 - 6)
    sh = shadow_of(b, blur=18, alpha=150, grow=6)
    sh.alpha_composite(b, (36, 36))
    return sh
NUMS = {n: _badge(n) for n in (1, 2, 3)}

# gancho
HOOK_BG = tinted_bg(IMG["gardens460"], amount=0.80, blur=30)
H1, H1W = letters_layers("¿CUÁNTO CREES", CINZEL_R, 62, WHITE, tracking=4)
H2, H2W = letters_layers("QUE CUESTA", CINZEL_R, 62, WHITE, tracking=4)
H_SCRIPT = text_layer("vivir en", SCRIPT, 150, BEIGE)
H_BIG = text_layer("ANTIGUA?", CINZEL_B, 150, WHITE, tracking=4)
H_SUB = text_layer("5 PROPIEDADES · DE MENOR A MAYOR", CINZEL_R, 32, BEIGE, tracking=4)

# antesala de la última
TEASE_BG = tinted_bg(IMG["hacienda"], amount=0.82, blur=34)
T1 = text_layer("GUARDAMOS", CINZEL_B, 96, WHITE, tracking=6)
T2 = text_layer("la mejor", SCRIPT, 170, BEIGE)
T3 = text_layer("PARA EL FINAL", CINZEL_R, 64, WHITE, tracking=8)

# ---------- tarjeta final ----------
END_BG = cover_fill(IMG["hacienda"].crop((600, 255, 900, 788)), W, H).filter(ImageFilter.GaussianBlur(20)).convert("RGBA")

logo = Image.open(f"{LOGO_DIR}/t3.png").convert("RGBA")
la = np.asarray(logo.split()[3], dtype=np.float32) / 255
rows = np.where(la.max(axis=1) > 0.2)[0]
# separación entre farol y texto: primer hueco grande de filas vacías después de la mitad del farol
filled = la.max(axis=1) > 0.05
split = None
for y in range(int(rows[0] + (rows[-1] - rows[0]) * 0.45), rows[-1]):
    if not filled[y] and not filled[y + 1] and not filled[y + 2]:
        split = y; break
split = split or int(rows[0] + (rows[-1] - rows[0]) * 0.62)
# distancia geodésica a lo largo del trazo, desde la punta del espiral
mask = la > 0.08
mask[split:] = False
ys, xs = np.where(mask)
start = min(zip(xs, ys), key=lambda p: (p[0] - 0) ** 2 * 1.0 + (p[1] - split * 0.55) ** 2)  # extremo izquierdo
# usar el centro del espiral: el píxel del trazo más cercano al punto medio izquierdo del espiral
cxs = xs.min() + (xs.max() - xs.min()) * 0.12
cys = ys.min() + (split - ys.min()) * 0.55
start = min(zip(xs, ys), key=lambda p: (p[0] - cxs) ** 2 + (p[1] - cys) ** 2)
dist = np.full(la.shape, -1.0, dtype=np.float32)
dq = collections.deque([start]); dist[start[1], start[0]] = 0
hh, ww = la.shape
while dq:
    x, y = dq.popleft(); dv = dist[y, x]
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if 0 <= nx < ww and 0 <= ny < hh and mask[ny, nx] and dist[ny, nx] < 0:
                dist[ny, nx] = dv + 1; dq.append((nx, ny))
maxd = dist.max()
dist[(dist < 0) & (la > 0)] = maxd * 1.05  # piezas sueltas al final
# extender distancia a los bordes suaves (antialias) por dilatación simple
for _ in range(3):
    d2 = dist.copy()
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sh = np.roll(np.roll(dist, dy, 0), dx, 1)
        upd = (d2 < 0) & (sh >= 0)
        d2[upd] = sh[upd]
    dist = d2
DMAX = maxd * 1.05
LOGO_RGB = np.asarray(logo, dtype=np.float32)
LOGO_SH_BLUR = 10

def logo_frame(p_lamp, p_text):
    """p_lamp: avance del trazo 0..1; p_text: aparición del texto 0..1."""
    a = la.copy()
    ln = np.arange(hh)[:, None] < split
    reveal = np.clip((p_lamp * DMAX * 1.08 - dist) / 6.0, 0, 1)
    reveal[dist < 0] = 0
    a = np.where(ln, a * reveal, a * clamp(p_text))
    out = np.dstack([np.full(la.shape, 255, np.float32)] * 3 + [a * 255]).astype(np.uint8)
    im = Image.fromarray(out, "RGBA")
    if p_text < 1:
        # el texto sube ligeramente al aparecer
        top = im.crop((0, 0, ww, split)); bot = im.crop((0, split, ww, hh))
        im = Image.new("RGBA", (ww, hh), (0, 0, 0, 0)); im.alpha_composite(top, (0, 0))
        im.alpha_composite(bot, (0, split + int(18 * (1 - ease_out(p_text)))))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.split()[3].point(lambda v: v * 120 // 255).filter(ImageFilter.GaussianBlur(LOGO_SH_BLUR)))
    sh = ImageChops.offset(sh, 0, 5)
    sh.alpha_composite(im)
    return sh

def wa_icon(d_size=86):
    def f(d, k):
        r = d_size * k
        d.ellipse((0, 0, r - 1, r - 1), fill=WHITE + (255,))
        c = r / 2; R = r * 0.30; lw = int(r * 0.055)
        d.ellipse((c - R, c - R, c + R, c + R), outline=VINO + (255,), width=lw)
        # colita de la burbuja (abajo a la izquierda)
        d.polygon([(c - R * 0.80, c + R * 0.45), (c - R * 1.05, c + R * 1.05), (c - R * 0.40, c + R * 0.85)], fill=VINO + (255,))
        # auricular: curva por abajo-izquierda con extremos gruesos
        rr = R * 0.50
        d.arc((c - rr, c - rr, c + rr, c + rr), 75, 195, fill=VINO + (255,), width=int(r * 0.08))
        for ang in (75, 195):
            ax = c + rr * math.cos(math.radians(ang)); ay = c + rr * math.sin(math.radians(ang))
            e = r * 0.075
            d.ellipse((ax - e, ay - e, ax + e, ay + e), fill=VINO + (255,))
    im = ss((d_size, d_size), f)
    return im

def pill(number):
    pw, ph = 720, 118
    def f(d, k):
        d.rounded_rectangle((0, 0, pw * k - 1, ph * k - 1), ph * k // 2, fill=VINO + (255,))
    p = ss((pw, ph), f)
    p.alpha_composite(wa_icon(), (16, 16))
    t = text_layer(number, CINZEL_B, 54, WHITE, tracking=2, shadow=False)
    paste_center(p, t, 118 + (pw - 118 - 30) / 2, ph / 2 + 2)
    sh = shadow_of(p, blur=16, alpha=120, grow=6)
    sh.alpha_composite(p, (32, 32))
    return sh

def social_icons():
    s = 60
    def fb(d, k):
        r = s * k
        d.ellipse((0, 0, r - 1, r - 1), outline=WHITE + (255,), width=4 * k)
        d.text((r * 0.5, r * 0.56), "f", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(r * 0.62)), fill=WHITE + (255,), anchor="mm")
    def ig(d, k):
        r = s * k
        d.rounded_rectangle((2 * k, 2 * k, r - 2 * k, r - 2 * k), r * 0.28, outline=WHITE + (255,), width=4 * k)
        d.ellipse((r * 0.3, r * 0.3, r * 0.7, r * 0.7), outline=WHITE + (255,), width=4 * k)
        d.ellipse((r * 0.70, r * 0.18, r * 0.80, r * 0.28), fill=WHITE + (255,))
    def tt(d, k):
        r = s * k; lw = int(r * 0.1)
        x = r * 0.52
        d.line((x, r * 0.12, x, r * 0.68), fill=WHITE + (255,), width=lw)
        d.ellipse((x - r * 0.34, r * 0.52, x + lw * 0.5, r * 0.88), outline=WHITE + (255,), width=lw)
        d.arc((x - r * 0.02, r * -0.05, x + r * 0.38, r * 0.35), 90, 180, fill=WHITE + (255,), width=lw)
    icons = [ss((s, s), f) for f in (fb, ig, tt)]
    gap = 46
    row = Image.new("RGBA", (s * 3 + gap * 2, s), (0, 0, 0, 0))
    for i, ic in enumerate(icons):
        row.alpha_composite(ic, (i * (s + gap), 0))
    sh = Image.new("RGBA", row.size, (0, 0, 0, 0))
    sh.putalpha(row.split()[3].point(lambda v: v * 110 // 255).filter(ImageFilter.GaussianBlur(5)))
    sh.alpha_composite(row)
    return sh

PILL1 = pill("+502 5565-4621")
PILL2 = pill("+502 5952-8514")
CTA = text_layer("AGENDA TU VISITA", CINZEL_B, 60, WHITE, tracking=8, shadow_alpha=170)
SOC = social_icons()
HANDLE = text_layer("@espacioinmobiliarioantigua", CINZEL_B, 36, WHITE, tracking=1, shadow_alpha=170)
DOTS_R = 9

def dots(fr, active):
    y = 262
    xs0 = W / 2 - 2 * 40
    d = ImageDraw.Draw(fr)
    for i in range(5):
        x = xs0 + i * 40
        if i < active:
            d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=WHITE + (230,))
        elif i == active:
            d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=BEIGE + (255,))
        else:
            d.ellipse((x - 7, y - 7, x + 7, y + 7), outline=WHITE + (200,), width=3)

# ---------- escenas ----------
def scene_hook(t):
    fr = HOOK_BG.copy()
    # leve acercamiento del fondo
    # letras una a una
    def row(layers, tw, cy, t0, step):
        x0 = W / 2 - tw / 2
        for i, (ly, x) in enumerate(layers):
            p = clamp((t - t0 - i * step) / 0.12)
            if p > 0:
                fr.alpha_composite(ly if p >= 1 else _fade(ly, p), (int(x0 + x - ly.width * 0 - 21), int(cy - ly.height / 2 + 14 * (1 - p))))
    row(H1, H1W, 640, 0.05, 0.04)
    row(H2, H2W, 730, 0.55, 0.04)
    p = ease_back(clamp((t - 1.05) / 0.35))
    paste_center(fr, H_BIG, W / 2, 930, alpha=clamp((t - 1.05) / 0.2), scale=0.6 + 0.4 * p)
    paste_center(fr, H_SCRIPT, W / 2 - 150, 820, alpha=clamp((t - 1.35) / 0.25))
    paste_center(fr, H_SUB, W / 2, 1090, alpha=clamp((t - 1.7) / 0.3))
    # línea decorativa que se dibuja
    lp = ease_out(clamp((t - 1.6) / 0.5))
    if lp > 0:
        d = ImageDraw.Draw(fr)
        d.line((W / 2 - 230 * lp, 1040, W / 2 + 230 * lp, 1040), fill=BEIGE + (255,), width=3)
        d.polygon([(W / 2, 1031), (W / 2 + 9, 1040), (W / 2, 1049), (W / 2 - 9, 1040)], fill=BEIGE + (int(255 * lp),))
    return fr

def _fade(ly, p):
    l2 = ly.copy(); l2.putalpha(ly.split()[3].point(lambda v: int(v * p))); return l2

REVEAL_B = 4  # pulso en que se revela el precio

def scene_prop(P, u, last=False):
    fr = P.bg.copy()
    # entrada con zoom
    pin = ease_out(clamp(u / 0.40))
    sc = 1.0 + 0.012 * u  # acercamiento lento
    sc *= 1.0 + 0.25 * (1 - pin)
    card = P.card; shadow = P.shadow
    if abs(sc - 1) > 0.002:
        card = card.resize((int(card.width * sc), int(card.height * sc)), Image.BILINEAR)
        shadow = shadow.resize((int(shadow.width * sc), int(shadow.height * sc)), Image.BILINEAR)
    cxo = P.cx - card.width / 2; cyo = P.cy - card.height / 2
    paste_center(fr, shadow, P.cx, P.cy + 12 * sc, alpha=pin)
    fr.alpha_composite(card, (int(cxo), int(cyo)))
    bx0, by0, bx1, by1 = P.box
    bcx = cxo + (bx0 + bx1) / 2 * sc; bcy = cyo + (by0 + by1) / 2 * sc
    tr = REVEAL_B * B
    if u < tr:
        paste_center(fr, P.cover, bcx, bcy, scale=sc)
    else:
        v = u - tr
        if v < 0.25:
            paste_center(fr, P.cover, bcx, bcy, alpha=1 - v / 0.25, scale=sc * (1 + v * 1.6))
        gp = clamp(v / 0.2)
        pulse = 0.55 + 0.45 * math.cos(v * 2 * math.pi / (2 * B))
        paste_center(fr, P.glow_soft, bcx, bcy, alpha=gp * pulse, scale=sc)
        paste_center(fr, P.glow, bcx, bcy, alpha=gp, scale=sc)
    # cuenta regresiva 3-2-1 en los pulsos 1,2,3
    for k, n in ((1, 3), (2, 2), (3, 1)):
        v = u - k * B
        if 0 <= v < B:
            pp = ease_back(clamp(v / 0.18))
            a = 1.0 if v < B * 0.7 else 1 - (v - B * 0.7) / (B * 0.3)
            paste_center(fr, NUMS[n], P.cx, P.cy - 60, alpha=a, scale=0.55 + 0.45 * pp)
    # textos superiores
    dots(fr, P.idx)
    paste_center(fr, LBL[P.idx], W / 2, 318, alpha=pin)
    if u < tr:
        paste_center(fr, Q_TXT, W / 2, 392, alpha=pin)
        paste_center(fr, HINT, W / 2, 1690, alpha=clamp((u - 0.3) / 0.3) * (1 - clamp((u - tr + 0.25) / 0.25)))
    else:
        v = u - tr
        txt = JOYA_TXT if last else A_TXT
        paste_center(fr, txt, W / 2, 392, alpha=clamp(v / 0.15), scale=0.8 + 0.2 * ease_back(clamp(v / 0.3)))
    # destello blanco en la revelación
    if tr <= u < tr + 0.3:
        fa = (1 - (u - tr) / 0.3) ** 2 * 0.85
        fr.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * fa))))
    # desenfoque de entrada
    zb = (1 - pin) * 0.22
    if zb > 0.004:
        fr = zoom_blur(fr, zb)
    return fr

def scene_tease(t):
    fr = TEASE_BG.copy()
    paste_center(fr, T1, W / 2, 800, alpha=ease_out(clamp(t / 0.35)), scale=1.0 + 0.02 * t)
    paste_center(fr, T2, W / 2, 950, alpha=ease_out(clamp((t - 0.3) / 0.4)))
    paste_center(fr, T3, W / 2, 1090, alpha=ease_out(clamp((t - 0.6) / 0.4)))
    return fr

def scene_end(t, prev_last):
    fr = END_BG.copy()
    if t < 0.3:
        fr = Image.blend(prev_last, fr, ease_out(t / 0.3))
    # logo que se dibuja solo
    pl = clamp((t - 0.15) / 1.05)
    pt = clamp((t - 1.0) / 0.4)
    lg = logo_frame(ease_out(pl) if pl < 1 else 1.0, ease_out(pt))
    lg = lg.resize((500, 500), Image.LANCZOS)
    fr.alpha_composite(lg, (W // 2 - 250, 230))
    def pop(layer, cy, t0):
        p = clamp((t - t0) / 0.3)
        if p > 0:
            paste_center(fr, layer, W / 2, cy, alpha=clamp(p * 2.5), scale=0.75 + 0.25 * ease_back(p))
    pop(PILL1, 870, 1.45)
    pop(PILL2, 1020, 1.70)
    pop(CTA, 1170, 1.95)
    pop(SOC, 1310, 2.20)
    pop(HANDLE, 1395, 2.30)
    return fr

# ---------- render ----------
cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
       "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", OUT]
ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
last_prop_frame = None
only = None
if len(sys.argv) > 4:
    only = [int(float(x) * FPS) for x in sys.argv[4].split(",")]
for f in range(NFR):
    if only and f not in only:
        continue
    t = f / FPS
    if t < T_HOOK_END:
        fr = scene_hook(t)
        # salida con zoom blur hacia la primera propiedad
        if t > T_HOOK_END - 0.15:
            fr = zoom_blur(fr, (t - (T_HOOK_END - 0.15)) / 0.15 * 0.2)
    elif t < T_TEASE:
        i = int((t - beat(4)) // PROP_LEN)
        fr = scene_prop(PROPOBJ[i], t - STARTS[i])
    elif t < T_JOYA:
        fr = scene_tease(t - T_TEASE)
    elif t < T_END:
        fr = scene_prop(PROPOBJ[4], t - T_JOYA, last=True)
        last_prop_frame = fr
    else:
        if last_prop_frame is None:
            last_prop_frame = scene_prop(PROPOBJ[4], T_END - T_JOYA - 0.01, last=True)
        fr = scene_end(t - T_END, last_prop_frame)
    if only:
        fr.convert("RGB").save(f"{WORK}/check_{t:05.2f}.jpg", quality=85)
    else:
        ff.stdin.write(fr.convert("RGB").tobytes())
    if f % 60 == 0:
        print(f"{f}/{NFR}", flush=True)
ff.stdin.close(); ff.wait()
