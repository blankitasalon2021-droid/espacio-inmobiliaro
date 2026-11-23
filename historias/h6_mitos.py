# Historia 6 — "Mitos de comprar casa en Guatemala" (educativa, ritmo alegre).
import sys
from lib import *

SEGS = [
    seg(37.0, 45.0, 1.0),
    seg(15.0, 25.0, 1.0, xf=('hblur', 0.4)),
    seg(46.0, 58.0, 1.15, xf=('zoomin', 0.4)),
    seg(76.0, 94.0, 1.7, xf=('fadewhite', 0.4)),
    seg(95.0, 105.0, 1.0, xf=('hblur', 0.4)),
    seg(105.0, 110.6, 1.0, xf=('smoothleft', 0.4)),
    seg(110.6, 114.7, 0.5, blur=True, xf=('fade', 0.8)),
]
ST, TOTAL = timeline(SEGS)
L = []; EV = []
for k in range(1, 6): EV.append(('whoosh', ST[k] + 0.2))

# ---- gancho
L.append(Layer(block(lambda d: dtext(d, W / 2, 700, 'MITOS', cinzelb(210), WHITE, tr=10), (14, 210, 4)), 0.3, ST[1] + 0.3,
               fin=0.25, rise=0, scale0=1.6, sdur=0.5)); EV.append(('hit', 0.3))
L.append(Layer(block(lambda d: dtext(d, W / 2, 900, 'de comprar casa', script(120), BEIGE), (8, 210, 3)), 1.0, ST[1] + 0.3, wipe=0.8, fin=0.2, rise=0))
EV.append(('whoosh', 1.0))
L.append(Layer(block(lambda d: dtext(d, W / 2, 1060, 'EN GUATEMALA', cinzelb(50), WHITE, tr=14)), 1.8, ST[1] + 0.3, fin=0.4, rise=20))
EV.append(('pop', 1.8))
L.append(Layer(block(lambda d: pill_label(d, W / 2, 1160, '¿CUÁNTOS CREÍAS?', cinzelb(36), VINO + (240,), WHITE)), 3.2, ST[1] + 0.3,
               fin=0.3, rise=0, scale0=0.5, sdur=0.45, ease=back_out)); EV.append(('pop', 3.2))

MITOS = [
    ('Necesitas tener todo el dinero para comprar.',
     'Con un enganche y un crédito puedes pagar tu casa en cuotas mensuales.'),
    ('Rentar siempre sale más barato.',
     'Muchas veces la cuota se parece a tu renta… y lo que pagas se vuelve tuyo.'),
    ('Antigua es solo para turistas.',
     'Cada vez más familias la escogen para vivir por su clima, su historia y su tranquilidad.'),
    ('Puedes hacer todo el trámite solo.',
     'Un asesor revisa papelería, negocia por ti y te ayuda a evitar errores costosos.'),
]

def mito(n, txt, real, t0, t1):
    fm = cinzelb(60); fr = cinzel(50)
    # panel de vidrio oscuro para que el texto se lea sobre cualquier toma
    lm = wrap(txt.upper(), fm, 820, 1); lr = wrap(real, fr, 840)
    y_m = 520; y_r = y_m + len(lm) * 78 + 150
    y_end = y_r + 90 + len(lr) * 66 + 40
    def _panel(d): d.rounded_rectangle((70, 430, W - 70, y_end), radius=48, fill=(18, 8, 6, 140))
    L.append(Layer(block(_panel, (30, 80, 8)), t0, t1, fin=0.35, fout=0.3, rise=0, scale0=0.94, sdur=0.4))
    L.append(Layer(block(lambda d: pill_label(d, W / 2, 400, f'MITO #{n}', cinzelb(38), VINO + (250,), WHITE, h=66, tr=8)),
                   t0 + 0.1, t1, fin=0.25, fout=0.3, rise=0, scale0=0.4, sdur=0.4, ease=back_out)); EV.append(('pop', t0 + 0.1))
    def _m(d, col=WHITE):
        for i, ln in enumerate(lm): dtext(d, W / 2, y_m + i * 78, ln, fm, col, tr=1)
    ts = t0 + 3.4
    L.append(Layer(block(_m), t0 + 0.5, ts + 0.35, fin=0.35, fout=0.35, rise=20)); EV.append(('whoosh', t0 + 0.5))
    L.append(Layer(block(lambda d: _m(d, (205, 195, 185))), ts, t1, fin=0.35, fout=0.3, rise=0))
    # tachado que se dibuja
    for i, ln in enumerate(lm):
        w = tw(ln, fm, 1); yy = y_m + i * 78 + 38
        L.append(Layer(block(lambda d, w=w, yy=yy: d.line((W / 2 - w / 2 - 14, yy, W / 2 + w / 2 + 14, yy - 6), fill=BEIGE, width=9), (4, 120, 2)),
                       ts + i * 0.2, t1, fin=0.05, fout=0.3, rise=0, wipe=0.35))
    EV.append(('scribble', ts))
    tr_ = ts + 1.0
    L.append(Layer(block(lambda d: pill_label(d, W / 2, y_r, 'REALIDAD', cinzelb(38), BEIGE + (255,), VINO, h=66, tr=8)),
                   tr_, t1, fin=0.25, fout=0.3, rise=0, scale0=0.4, sdur=0.4, ease=back_out)); EV.append(('ding', tr_))
    for i, ln in enumerate(lr):
        L.append(Layer(block(lambda d, ln=ln, i=i: dtext(d, W / 2, y_r + 95 + i * 66, ln, fr, WHITE)),
                       tr_ + 0.4 + i * 0.3, t1, fin=0.35, fout=0.3, rise=16))
    EV.append(('pop', tr_ + 0.4))

for n, (m, r) in enumerate(MITOS, start=1):
    mito(n, m, r, ST[n] + 0.25, ST[n + 1] + 0.2)

# ---- encuesta (espacio libre abajo para el sticker)
t = ST[5] + 0.3
L.append(Layer(block(lambda d: (dtext(d, W / 2, 700, '¿Cuál de estos', cinzel(70), WHITE, tr=3),
                                dtext(d, W / 2, 790, 'MITOS', cinzelb(140), BEIGE, tr=6),
                                dtext(d, W / 2, 950, 'creías tú?', script(120), WHITE))), t, ST[6] + 0.5, fin=0.4, rise=24))
EV.append(('whoosh', t))
def _v(d):
    w = dtext(d, W / 2 - 30, 1150, 'VOTA AQUÍ', cinzelb(40), WHITE, tr=6)
    arrow_down(d, W / 2 - 30 + w / 2 + 40, 1150, 42, WHITE)
L.append(Layer(block(_v), t + 1.0, ST[6] + 0.5, fin=0.3, rise=-14)); EV.append(('pop', t + 1.0))

ec, ev = endcard(ST[6] + 0.5, TOTAL + 1, mode='arma')
L += ec; EV += ev

if __name__ == '__main__':
    if sys.argv[1:2] == ['frames']:
        for tt in map(float, sys.argv[2:]):
            Image.fromarray(render_frame(L, tt), 'RGBA').save(f'work/h6_ov_{tt}.png')
    else:
        print('total', TOTAL, 'starts', ST)
        render_segments(SEGS, 'work/h6')
        mx = Mix(TOTAL); music_pop(mx, bpm=100)
        master(mx, EV, 'work/h6_audio.wav', music_gain=0.42, reverb_music=False)
        assemble(SEGS, 'work/h6', L, 'work/h6_audio.wav', 'out/historia6_mitos.mp4')
        print('ok')
