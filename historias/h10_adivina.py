# Historia 10 — "Adivina la calle" (interactiva: la imagen se congela y el público adivina).
import sys
from lib import *

FRZ = [79.5, 93.0, 111.5]
SEGS = [
    seg(0.0, 7.0, 1.0),
    seg(37.0, 45.0, 1.0, xf=('hblur', 0.4)),
    seg(72.0, FRZ[0], 1.3, xf=('zoomin', 0.4)),
    freeze(FRZ[0], 7.0, blur=True, xf=('fadewhite', 0.3)),
    seg(86.0, FRZ[1], 1.3, xf=('hblur', 0.4)),
    freeze(FRZ[1], 7.0, blur=True, xf=('fadewhite', 0.3)),
    seg(104.0, FRZ[2], 1.2, xf=('hblur', 0.4)),
    freeze(FRZ[2], 7.0, blur=True, xf=('fadewhite', 0.3)),
    seg(110.6, 114.9, 0.45, blur=True, xf=('fade', 0.8)),
]
ST, TOTAL = timeline(SEGS)
L = []; EV = []
for k in (1, 2, 4, 6, 8): EV.append(('whoosh', ST[k] + 0.2))

# ---- gancho
L.append(Layer(block(lambda d: dtext(d, W / 2, 700, '¿Qué tan bien', cinzel(72), WHITE, tr=3)), 0.3, ST[1] + 0.3, fin=0.4, rise=22))
EV.append(('pop', 0.3))
L.append(Layer(block(lambda d: dtext(d, W / 2, 790, 'conoces', script(130), BEIGE), (8, 210, 3)), 0.9, ST[1] + 0.3, wipe=0.7, fin=0.2, rise=0))
EV.append(('whoosh', 0.9))
L.append(Layer(block(lambda d: dtext(d, W / 2, 990, 'ANTIGUA?', cinzelb(150), WHITE, tr=6), (14, 210, 4)), 1.7, ST[1] + 0.3,
               fin=0.25, rise=0, scale0=1.5, sdur=0.45)); EV.append(('hit', 1.7))

# ---- reglas del juego
t = ST[1] + 0.4
L.append(Layer(block(lambda d: pill_label(d, W / 2, 640, 'JUEGO', cinzelb(40), VINO + (250,), WHITE, h=70, tr=10)), t, ST[2] + 0.2,
               fin=0.25, rise=0, scale0=0.4, sdur=0.4, ease=back_out)); EV.append(('pop', t))
L.append(Layer(block(lambda d: dtext(d, W / 2, 740, 'Adivina la calle', script(140), BEIGE), (8, 210, 3)), t + 0.5, ST[2] + 0.2, wipe=0.9, fin=0.2, rise=0))
EV.append(('whoosh', t + 0.5))
ls, te = typewriter([('Congelo la imagen…', cinzel(56), WHITE, 940, 2), ('y tú me dices dónde es.', cinzel(56), WHITE, 1020, 2)],
                    t + 1.8, ST[2] + 0.2, cps=24); L += ls
L.append(Layer(block(lambda d: dtext(d, W / 2, 1130, '¡RESPÓNDEME POR MENSAJE!', cinzelb(40), BEIGE, tr=4)), te + 0.3, ST[2] + 0.2, fin=0.3, rise=14))
EV.append(('pop', te + 0.3))

# ---- rondas
CARD_W = 740
def ronda(n, k, src):
    t0, t1 = ST[k], ST[k + 1] + 0.3
    im = still(src, f'work/h10_still{n}.png').crop((0, 110, W, 1060))
    card = photo_card(im, CARD_W, radius=44, border=10)
    cy0 = 390; cx0 = (W - card.width) // 2
    C = canvas(); C.alpha_composite(card, (cx0, cy0))
    L.append(Layer(shadowed(C, 24, 160, 10), t0 + 0.1, t1, fin=0.25, fout=0.3, rise=0, scale0=1.25, sdur=0.6))
    EV.append(('shutter', t0 + 0.05))
    L.append(Layer(block(lambda d: pill_label(d, W / 2, 300, f'CALLE #{n}', cinzelb(40), VINO + (250,), WHITE, h=70, tr=10)),
                   t0 + 0.6, t1, fin=0.25, fout=0.3, rise=0, scale0=0.4, sdur=0.4, ease=back_out)); EV.append(('pop', t0 + 0.6))
    ybot = cy0 + card.height
    L.append(Layer(block(lambda d: dtext(d, W / 2, ybot + 80, '¿SABES DÓNDE ES?', cinzelb(58), WHITE, tr=4)),
                   t0 + 1.0, t1, fin=0.3, fout=0.3, rise=18)); EV.append(('whoosh', t0 + 1.0))
    # cuenta regresiva 5..1 con anillo
    tc = t0 + 1.4; R = 52; cy = ybot - 4
    def cd(t, tc=tc, cy=cy):
        p = t - tc
        if p < 0 or p >= 5.4: return None
        k = min(1, p / 0.25) * (1 - max(0, (p - 5.1) / 0.3))
        L_ = canvas(); d = ImageDraw.Draw(L_)
        d.ellipse((W / 2 - R, cy - R, W / 2 + R, cy + R), fill=VINO + (int(245 * k),))
        frac = min(1, p / 5)
        d.arc((W / 2 - R + 6, cy - R + 6, W / 2 + R - 6, cy + R - 6), -90, -90 + 360 * (1 - frac), fill=BEIGE + (int(255 * k),), width=7)
        num = str(max(1, 5 - int(p))); f = cinzelb(56)
        bb = f.getbbox(num)
        pop = 1 + 0.25 * max(0, 1 - (p % 1) / 0.2)
        if pop > 1.01:
            f = cinzelb(int(56 * pop)); bb = f.getbbox(num)
        d.text((W / 2 - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), num, font=f, fill=WHITE + (int(255 * k),))
        return L_
    L.append(FrameLayer(cd, tc, tc + 5.4))
    for s in range(5): EV.append(('tick', tc + s))
    EV.append(('ding', tc + 5.0))

for n, k in enumerate((3, 5, 7), start=1):
    ronda(n, k, FRZ[n - 1])

# ---- cierre: respuestas en la siguiente historia
t = ST[8] + 0.3; te_ = t + 2.9
L.append(Layer(block(lambda d: (dtext(d, W / 2, 720, 'LAS RESPUESTAS', cinzelb(78), WHITE, tr=5),
                                dtext(d, W / 2, 830, 'en la siguiente historia', script(110), BEIGE))), t, te_, fin=0.35, fout=0.35, rise=22))
EV.append(('whoosh', t))
ec, ev = endcard(te_ + 0.2, TOTAL + 1, mode='dibuja')
L += ec; EV += ev

if __name__ == '__main__':
    if sys.argv[1:2] == ['frames']:
        for tt in map(float, sys.argv[2:]):
            Image.fromarray(render_frame(L, tt), 'RGBA').save(f'work/h10_ov_{tt}.png')
    else:
        print('total', TOTAL, 'starts', ST)
        render_segments(SEGS, 'work/h10')
        mx = Mix(TOTAL); music_pop(mx, bpm=100, quiet=[(ST[k] + 1.3, ST[k] + 6.5) for k in (3, 5, 7)])
        master(mx, EV, 'work/h10_audio.wav', music_gain=0.42, reverb_music=False)
        assemble(SEGS, 'work/h10', L, 'work/h10_audio.wav', 'out/historia10_adivina_la_calle.mp4')
        print('ok')
