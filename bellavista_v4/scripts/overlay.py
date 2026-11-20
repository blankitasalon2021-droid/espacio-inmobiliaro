# Capa animada (RGBA por fotograma): portada de revista, subtítulos palabra por palabra con palabras clave
# que cambian a vino, checklist sobre el patio, precio y tarjeta final con el imagotipo que se dibuja solo.
# Marca: beige #E7D3AF, vino #661E1A, blanco. Cinzel + Great Vibes (toque manuscrito) + Montserrat (apoyo).
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np, json, re, io
from collections import deque
from edl import SEGS, VOICE, SUBS, KEYWORDS, timeline, FPS
W, H = 1080, 1920
BEIGE = (231, 211, 175); VINO = (102, 30, 26); WHITE = (255, 255, 255)
tl, TOTAL = timeline()
EVENTS = []   # (time, kind) → efectos de sonido

def vfont(name, size, wght=None):
    f = ImageFont.truetype('fonts/' + name, size)
    if wght: f.set_variation_by_axes([wght])
    return f
cin = lambda s, w=700: vfont('Cinzel.ttf', s, w)
mont = lambda s, w=600: vfont('Montserrat.ttf', s, w)
script = lambda s: vfont('GreatVibes-Regular.ttf', s)

def tw(t, f, tr=0):
    if not tr: return f.getlength(t)
    return sum(f.getlength(c) for c in t) + tr * (len(t) - 1)

def dtext(d, x, y, t, f, fill, tr=0, anchor='c'):
    w = tw(t, f, tr)
    x = x - w / 2 if anchor == 'c' else (x - w if anchor == 'r' else x)
    if not tr: d.text((x, y), t, font=f, fill=fill); return x, w
    x0 = x
    for c in t:
        d.text((x, y), c, font=f, fill=fill); x += f.getlength(c) + tr
    return x0, w

def shadowed(L, radius=7, alpha=120, dy=3):
    a = L.split()[3].point(lambda v: v * alpha // 255).filter(ImageFilter.GaussianBlur(radius))
    sh = Image.new('RGBA', L.size, (25, 12, 8, 255)); sh.putalpha(a)
    out = Image.new('RGBA', L.size); out.alpha_composite(sh, (0, dy)); out.alpha_composite(L)
    return out

def canvas(): return Image.new('RGBA', (W, H))

def strong(L):
    return shadowed(shadowed(L, 4, 255, 2), 14, 170, 3)

def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)

class Layer:
    """Imagen fija con entrada/salida (fundido, subida, escala) y barrido horizontal opcional."""
    def __init__(self, img, t0, t1, fin=0.35, fout=0.25, rise=14, wipe=0.0, pop=0.0):
        bb = img.getbbox() or (0, 0, 1, 1)
        bb = (max(0, bb[0] - 2), max(0, bb[1] - 2), min(W, bb[2] + 2), min(H, bb[3] + 2))
        self.x, self.y = bb[0], bb[1]
        self.img = img.crop(bb)
        a = np.asarray(self.img).astype(np.float32) / 255.0
        self.rgb = a[..., :3]; self.a = a[..., 3:4]
        self.t0, self.t1, self.fin, self.fout, self.rise, self.wipe, self.pop = t0, t1, fin, fout, rise, wipe, pop
    def render(self, t):
        if t < self.t0 or t >= self.t1: return None
        k = 1.0
        if self.fin > 0: k = min(k, (t - self.t0) / self.fin)
        if self.fout > 0: k = min(k, (self.t1 - t) / self.fout)
        k = ease(k)
        e = 1 - (1 - min(1.0, (t - self.t0) / max(self.fin * 1.4, 1e-3))) ** 3
        dy = int(round(self.rise * (1 - e)))
        a = self.a * k
        if self.wipe > 0:
            p = min(1.0, (t - self.t0) / self.wipe)
            w = a.shape[1]; cols = np.clip((p * (w + 40) - np.arange(w)) / 40, 0, 1)
            a = a * cols[None, :, None]
        if self.pop > 0 and t - self.t0 < self.pop:
            s = 0.7 + 0.3 * (1 - (1 - (t - self.t0) / self.pop) ** 3) + 0.06 * np.sin(np.pi * (t - self.t0) / self.pop)
            im = self.img.resize((max(1, int(self.img.width * s)), max(1, int(self.img.height * s))), Image.BILINEAR)
            arr = np.asarray(im).astype(np.float32) / 255.0
            x = self.x + (self.img.width - im.width) // 2; y = self.y + (self.img.height - im.height) // 2
            return arr[..., :3], arr[..., 3:4] * k, x, y
        return self.rgb, a, self.x, self.y + dy

layers = []
def add(img, t0, t1, sfx=None, **kw):
    layers.append(Layer(img, t0, t1, **kw))
    if sfx: EVENTS.append((t0, sfx))

# ============ 1. GANCHO — PORTADA DE REVISTA (fotograma congelado) ============
a0, a1 = tl['a']; b0 = tl['b'][0]
COVER_END = b0 + 0.18
EVENTS.append((a0 + 0.05, 'shutter'))
# marco fino
L = canvas(); d = ImageDraw.Draw(L)
d.rectangle((44, 150, W - 44, H - 150), outline=WHITE + (230,), width=3)
add(shadowed(L, 6, 110, 2), a0 + 0.05, COVER_END, fin=0.3, fout=0.15, rise=0)
# cintillo superior
L = canvas(); d = ImageDraw.Draw(L)
dtext(d, W / 2, 200, 'EDICIÓN ANTIGUA GUATEMALA  ·  Nº 01', mont(25, 700), WHITE, tr=5)
add(shadowed(L, 6, 190, 2), a0 + 0.1, COVER_END, fin=0.3, fout=0.15, rise=8)
# cabecera BELLAVISTA letra por letra
mast = 'BELLAVISTA'; fm = cin(112, 900); TRK = 4
wm = tw(mast, fm, TRK); x = W / 2 - wm / 2
for i, ch in enumerate(mast):
    L = canvas(); d = ImageDraw.Draw(L); d.text((x, 240), ch, font=fm, fill=WHITE)
    add(shadowed(L, 9, 200, 3), a0 + 0.15 + i * 0.06, COVER_END, fin=0.18, fout=0.15, rise=22,
        sfx='tick' if i % 3 == 0 else None)
    x += fm.getlength(ch) + TRK
# palabra manuscrita encima
L = canvas(); d = ImageDraw.Draw(L)
d.text((W / 2 + 20, 335), 'Residencial', font=script(92), fill=BEIGE)
add(strong(L), a0 + 0.85, COVER_END, fin=0.35, fout=0.15, rise=0, wipe=0.45)
# titulares laterales (derecha, zona libre de la interfaz)
def coverline(y, big, small):
    L = canvas(); d = ImageDraw.Draw(L)
    dtext(d, W - 130, y, big, cin(46, 800), WHITE, anchor='r')
    dtext(d, W - 130, y + 54, small, script(50), BEIGE, anchor='r')
    return strong(L)
add(coverline(560, 'CASA EN VENTA', 'calles empedradas'), a0 + 1.0, COVER_END, fin=0.3, fout=0.15, rise=16, sfx='pop')
add(coverline(720, 'DOBLE ALTURA', 'y terraza'), a0 + 1.2, COVER_END, fin=0.3, fout=0.15, rise=16, sfx='pop')
# pie de portada: a minutos de ANTIGUA
L = canvas(); d = ImageDraw.Draw(L)
d.text((100, 1265), 'a minutos de', font=script(70), fill=BEIGE)
d.text((100, 1345), 'ANTIGUA', font=cin(96, 900), fill=WHITE)
d.line((104, 1468, 420, 1468), fill=BEIGE, width=4)
add(strong(L), a0 + 1.35, COVER_END, fin=0.3, fout=0.15, rise=18, sfx='pop')
EVENTS.append((b0 + 0.05, 'flash'))

# ============ 2. SUBTÍTULOS — palabra por palabra, palabra clave cambia a vino ============
STOP = set('a al de del el en la las los y o con por para sus su mis mi que se nos una uno un te es esta este esa sino no solo ya'.split())
words_db = json.load(open('transcripts.json'))
vmap = {v[0]: v for v in VOICE}
F_BOLD = cin(56, 900); F_SCR = script(74)
SPACE = 18; MAXW = 800; CX = 520; CAP_Y = 1290
def norm(w): return re.sub(r'[^\wáéíóúñü-]', '', w.lower())
for clip, chunks in SUBS.items():
    _, a, b, anc, off = vmap[clip]
    base = tl[anc][0] + off - a
    wd = words_db[clip + '.mp4']['words']
    emotional = clip == 'Mi_peli_cula_5'
    for ci, (txt, s0, s1) in enumerate(chunks):
        toks = txt.split()
        ws = [w for w in wd if s0 - 0.15 <= w[1] < s1 - 0.05]
        if len(ws) == len(toks):
            starts = [max(s0, w[1]) for w in ws]
        else:
            lens = np.array([len(t) + 2 for t in toks], float)
            starts = list(s0 + (s1 - 0.3 - s0) * np.concatenate([[0], np.cumsum(lens)[:-1]]) / lens.sum())
        styled = []
        for t in toks:
            if norm(t) in STOP: styled.append((t, F_SCR, False, False))
            else:
                up = t.upper(); styled.append((up, F_BOLD, True, re.sub(r'[^\wÁÉÍÓÚÑÜ-]', '', up) in KEYWORDS))
        widths = [tw(t, f) for t, f, _, _ in styled]
        lines = [[]]; cur = 0
        for i, wv in enumerate(widths):
            if lines[-1] and cur + SPACE + wv > MAXW: lines.append([]); cur = 0
            cur += (SPACE if lines[-1] else 0) + wv; lines[-1].append(i)
        y = CAP_Y - (len(lines) - 1) * 42
        end = s1 + 0.12
        if ci + 1 < len(chunks): end = min(end, chunks[ci + 1][1])
        for line in lines:
            lw = sum(widths[i] for i in line) + SPACE * (len(line) - 1)
            x = CX - lw / 2
            for i in line:
                t, f, bold, key = styled[i]
                ts = base + starts[i] - 0.03; te = base + end
                yy = y if bold else y - 14
                if key:
                    # 1) aparece en blanco, 2) el fondo vino barre y la letra cambia a beige
                    L = canvas(); d = ImageDraw.Draw(L); d.text((x, yy), t, font=f, fill=WHITE)
                    add(strong(L), ts, ts + 0.24, fin=0.12, fout=0.06, rise=10)
                    bb = d.textbbox((x, yy), t, font=f)
                    L = canvas(); d = ImageDraw.Draw(L)
                    d.rounded_rectangle((bb[0] - 12, bb[1] - 10, bb[2] + 12, bb[3] + 12), radius=12, fill=VINO + (235,))
                    add(shadowed(L, 8, 120, 3), ts + 0.18, te, fin=0.05, fout=0.12, rise=0, wipe=0.2,
                        sfx=None if emotional else 'swipe')
                    L = canvas(); d = ImageDraw.Draw(L); d.text((x, yy), t, font=f, fill=BEIGE)
                    add(L, ts + 0.18, te, fin=0.1, fout=0.12, rise=0)
                else:
                    L = canvas(); d = ImageDraw.Draw(L); d.text((x, yy), t, font=f, fill=WHITE)
                    add(strong(L), ts, te, fin=0.12, fout=0.12, rise=10)
                x += widths[i] + SPACE
            y += 84

# ============ 3. CHECKLIST CON PALOMITAS SOBRE EL PATIO ============
i0, i1 = tl['i']
L = canvas(); d = ImageDraw.Draw(L)
d.text((110, 395), 'Todo lo que', font=script(84), fill=BEIGE)
d.text((110, 480), 'INCLUYE', font=cin(92, 900), fill=WHITE)
add(shadowed(L, 9, 210, 3), i0 + 0.1, i1, fin=0.35, fout=0.25, rise=20, sfx='whoosh_s')
ITEMS = ['3 HABITACIONES', '3.5 BAÑOS', '315 m² CONSTRUCCIÓN', '180 m² TERRENO', 'PARQUEO PARA 2']
CHECKS = []
for k, it in enumerate(ITEMS):
    y = 640 + k * 118; t0 = i0 + 0.55 + k * 0.42
    L = canvas(); d = ImageDraw.Draw(L); f = cin(42, 800)
    w = tw(it, f) + 150; h = 92
    d.rounded_rectangle((110, y, 110 + w, y + h), radius=h / 2, fill=VINO + (232,))
    d.ellipse((122, y + 12, 190, y + 80), fill=BEIGE)
    d.text((212, y + 20), it, font=f, fill=WHITE)
    add(shadowed(L, 10, 130, 4), t0, i1, fin=0.25, fout=0.25, rise=0, wipe=0.3, sfx='pop')
    CHECKS.append((t0 + 0.2, 156, y + 46))

def draw_check(t, d):
    for tc, cx, cy in CHECKS:
        if not (tc <= t < i1): continue
        p = min(1.0, (t - tc) / 0.22)
        k = ease(min(1.0, (i1 - t) / 0.25))
        pts = [(cx - 17, cy + 1), (cx - 5, cy + 14), (cx + 19, cy - 13)]
        l1 = np.hypot(12, 13); l2 = np.hypot(24, 27); L = (l1 + l2) * p
        col = VINO + (int(255 * k),)
        if L <= l1:
            q = L / l1; d.line([pts[0], (pts[0][0] + 12 * q, pts[0][1] + 13 * q)], fill=col, width=8)
        else:
            q = (L - l1) / l2
            d.line([pts[0], pts[1], (pts[1][0] + 24 * q, pts[1][1] - 27 * q)], fill=col, width=8, joint='curve')
for tc, _, _ in CHECKS: EVENTS.append((tc, 'check'))

# ============ 4. PRECIO (sobre la terraza al atardecer, desenfocada) ============
v0, v1 = tl['v']
A0 = v0 + 0.55; A1 = v0 + 3.75
def blk(fn):
    L = canvas(); d = ImageDraw.Draw(L); fn(d); return shadowed(L, 11, 200, 3)
add(blk(lambda d: dtext(d, W / 2, 470, 'CASA EN VENTA', mont(32, 700), WHITE, tr=12)), A0, A1, fin=0.4, fout=0.3, rise=14, sfx='whoosh_s')
add(blk(lambda d: d.text((W / 2 - tw('Residencial', script(96)) / 2, 520), 'Residencial', font=script(96), fill=WHITE)),
    A0 + 0.2, A1, fin=0.4, fout=0.3, rise=0, wipe=0.5)
add(blk(lambda d: dtext(d, W / 2, 625, 'BELLAVISTA', cin(96, 900), WHITE, tr=4)), A0 + 0.35, A1, fin=0.4, fout=0.3, rise=14)
price = 'US$550,000'; fp = cin(132, 900); xp = W / 2 - tw(price, fp, 2) / 2
for k, ch in enumerate(price):
    L = canvas(); d = ImageDraw.Draw(L); d.text((xp, 800), ch, font=fp, fill=WHITE)
    add(shadowed(L, 12, 210, 4), A0 + 0.7 + k * 0.05, A1, fin=0.18, fout=0.3, rise=24)
    xp += fp.getlength(ch) + 2
EVENTS.append((A0 + 0.7, 'hit'))
add(blk(lambda d: (d.line((W / 2 - 70, 985, W / 2 + 70, 985), fill=BEIGE, width=3),
                   dtext(d, W / 2, 1010, 'MÁS IMPUESTOS', mont(34, 700), BEIGE, tr=10))),
    A0 + 1.3, A1, fin=0.4, fout=0.3, rise=12, sfx='pop')

# ============ 5. TARJETA FINAL — imagotipo que se dibuja solo ============
B0 = A1 + 0.1
logo = Image.open('logo/t3.png').convert('RGBA').crop((51, 48, 450, 418))
LW = 500; LH = round(logo.height * LW / logo.width); logo = logo.resize((LW, LH), Image.LANCZOS)
LX = (W - LW) // 2; LY = 320
SPLIT = round((297 - 48) * LW / 399)            # fila que separa farol (arriba) y texto (abajo)
la = np.asarray(logo).astype(np.float32) / 255.0
alpha = la[..., 3]
# distancia geodésica a lo largo del trazo (BFS) → el farol "se dibuja" desde la espiral
mask = alpha[:SPLIT] > 0.08
dist = np.full(mask.shape, np.inf)
def bfs(seed, d0):
    q = deque([seed]); dist[seed] = d0
    while q:
        y, x = q.popleft(); dv = dist[y, x]
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and dist[ny, nx] == np.inf:
                dist[ny, nx] = dv + (1.414 if dy and dx else 1.0); q.append((ny, nx))
ys, xs = np.nonzero(mask)
# semilla: punto del trazo más cercano al centro de la espiral izquierda
sc = (round(0.36 * LH), round(0.08 * LW))
k0 = np.argmin((ys - sc[0]) ** 2 + (xs - sc[1]) ** 2); bfs((ys[k0], xs[k0]), 0.0)
while np.isinf(dist[mask]).any():           # piezas sueltas: arrancan donde termina lo ya dibujado más cercano
    rem = np.argwhere(mask & np.isinf(dist)); done = np.argwhere(mask & ~np.isinf(dist))
    p = rem[0]; j = np.argmin(((done - p) ** 2).sum(1))
    bfs(tuple(p), dist[tuple(done[j])] + np.hypot(*(done[j] - p)) * 0.5)
D = np.where(mask, dist, 0); D = D / D[mask].max()
# máscara completa (dilatada) para incluir el antialias
DRAW0, DRAW1 = B0 + 0.15, B0 + 1.55
TXT0 = DRAW1 - 0.15
EVENTS.append((DRAW0, 'draw')); EVENTS.append((TXT0, 'shimmer'))
txt_cols = np.nonzero(alpha[SPLIT:].max(0) > 0.08)[0]; TX0, TX1 = txt_cols.min(), txt_cols.max()

def logo_rgba(t):
    if t < DRAW0: return None
    a = np.zeros_like(alpha)
    p = ease((t - DRAW0) / (DRAW1 - DRAW0)) * 1.04
    near = Image.fromarray((np.clip((p - D) / 0.025, 0, 1) * mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    a[:SPLIT] = alpha[:SPLIT] * (np.asarray(near) / 255.0)
    q = (t - TXT0) / 0.7
    if q > 0:
        cols = np.clip((ease(q) * (TX1 - TX0 + 80) - (np.arange(LW) - TX0)) / 80, 0, 1)
        a[SPLIT:] = alpha[SPLIT:] * cols[None, :] * ease(q * 1.5)
    img = Image.fromarray(np.dstack([la[..., :3] * 255, a * 255]).astype(np.uint8), 'RGBA')
    # punta luminosa mientras dibuja
    if p < 1.0:
        front = mask & (np.abs(D - p) < 0.012)
        if front.any():
            fy, fx = np.nonzero(front); cy, cx = fy.mean(), fx.mean()
            g = Image.new('RGBA', img.size); gd = ImageDraw.Draw(g)
            gd.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill=BEIGE + (230,))
            img.alpha_composite(g.filter(ImageFilter.GaussianBlur(4)))
    full = Image.new('RGBA', (LW + 80, LH + 80)); full.alpha_composite(img, (40, 40))
    return shadowed(full, 12, 170, 4), LX - 40, LY - 40

# botones de WhatsApp, CTA y redes
import cairosvg
def svg_icon(name, size, color):
    s = open(f'icons/{name}.svg').read().replace('<path ', f'<path fill="rgb{color}" ')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode(), output_width=size, output_height=size))).convert('RGBA')
Y0 = LY + LH + 90
def phone_pill(num, y):
    L = canvas(); d = ImageDraw.Draw(L)
    f = cin(46, 800); w = tw(num, f, 1) + 150; h = 96; x0 = W / 2 - w / 2
    d.rounded_rectangle((x0, y, x0 + w, y + h), radius=h / 2, fill=VINO + (245,))
    cx, cy = x0 + 52, y + h / 2
    d.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=WHITE)
    ic = svg_icon('whatsapp', 40, VINO); L.alpha_composite(ic, (int(cx - 20), int(cy - 20)))
    dtext(d, x0 + 104, y + 22, num, f, WHITE, tr=1, anchor='l')
    return shadowed(L, 12, 150, 5)
C0 = TXT0 + 0.75
add(phone_pill('+502 5565-4621', Y0), C0, TOTAL + 1, fin=0.3, fout=0, rise=0, pop=0.35, sfx='pop')
add(phone_pill('+502 5952-8514', Y0 + 120), C0 + 0.3, TOTAL + 1, fin=0.3, fout=0, rise=0, pop=0.35, sfx='pop')
add(blk(lambda d: dtext(d, W / 2, Y0 + 262, 'AGENDA TU VISITA', cin(50, 800), WHITE, tr=10)),
    C0 + 0.6, TOTAL + 1, fin=0.35, fout=0, rise=16, sfx='whoosh_s')
def socials():
    L = canvas(); d = ImageDraw.Draw(L)
    handle = '@espacioinmobiliarioantigua'; fh = mont(34, 600); sz = 46
    y = Y0 + 365
    total = 3 * sz + 2 * 22 + 26 + tw(handle, fh); x = W / 2 - total / 2
    for n in ('facebook', 'instagram', 'tiktok'):
        L.alpha_composite(svg_icon(n, sz, WHITE), (int(x), y)); x += sz + 22
    d.text((x + 4, y + 2), handle, font=fh, fill=WHITE)
    return shadowed(L, 9, 190, 3)
add(socials(), C0 + 0.9, TOTAL + 1, fin=0.4, fout=0, rise=14, sfx='pop')

# ============ composición por fotograma ============
def frame(t):
    out = Image.new('RGBA', (W, H))
    acc = np.zeros((H, W, 4), np.float32)
    def comp(rgb, a, x, y):
        h, w = a.shape[:2]
        x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0: return
        rgb = rgb[y0 - y:y1 - y, x0 - x:x1 - x]; a = a[y0 - y:y1 - y, x0 - x:x1 - x]
        reg = acc[y0:y1, x0:x1]; ra = reg[..., 3:4]
        na = a + ra * (1 - a)
        reg[..., :3] = (rgb * a + reg[..., :3] * ra * (1 - a)) / np.maximum(na, 1e-6); reg[..., 3:4] = na
    for ly in layers:
        r = ly.render(t)
        if r is not None: comp(*r)
    # palomitas (trazo animado)
    if any(tc <= t < i1 for tc, _, _ in CHECKS):
        L = canvas(); draw_check(t, ImageDraw.Draw(L))
        arr = np.asarray(L).astype(np.float32) / 255; comp(arr[..., :3], arr[..., 3:4], 0, 0)
    lg = logo_rgba(t)
    if lg is not None:
        img, x, y = lg; arr = np.asarray(img).astype(np.float32) / 255; comp(arr[..., :3], arr[..., 3:4], x, y)
    return (acc * 255 + 0.5).astype(np.uint8)

if __name__ == '__main__':
    import sys, os
    os.makedirs('st', exist_ok=True)
    for t in map(float, sys.argv[1:]):
        Image.fromarray(frame(t), 'RGBA').save(f'st/ov_{t}.png')
    print(len(layers), 'layers', 'TOTAL', TOTAL)
    for e in sorted(EVENTS)[:5]: print(e)
