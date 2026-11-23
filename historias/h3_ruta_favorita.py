# Historia 3 — "Mi ruta favorita al atardecer" (estilo de vida, emocional, sin voz).
# Uso: python3 h3_ruta_favorita.py [render|frames t1 t2 ...]
import sys
from lib import *

SEGS = [
    seg(0.0, 12.0, 1.0),
    seg(15.0, 25.0, 1.0, xf=('fade', 0.6)),
    seg(46.0, 58.0, 1.0, xf=('hblur', 0.5)),
    seg(77.0, 94.0, 1.3, xf=('fade', 0.6)),
    seg(104.0, 112.0, 1.0, xf=('smoothleft', 0.6)),
    seg(110.6, 114.7, 0.5, blur=True, xf=('fade', 1.0)),
]
ST, TOTAL = timeline(SEGS)
END = ST[5] + 0.5

def at(k, src):  # tiempo final de un instante de la fuente dentro del segmento k
    s = SEGS[k]; return ST[k] + (src - s['src'][0]) / s['speed']

L = []; EV = []
# ---- gancho: "Mi ruta / FAVORITA / al atardecer"
L.append(Layer(block(lambda d: dtext(d, W / 2, 760, 'MI RUTA', cinzel(64), WHITE, tr=14)), 0.4, 6.2, fin=0.6, rise=20))
L.append(Layer(block(lambda d: dtext(d, W / 2, 840, 'FAVORITA', cinzelb(150), WHITE, tr=6), (12, 200, 4)), 0.8, 6.2, fin=0.7, rise=0, scale0=1.15, sdur=1.4))
L.append(Layer(block(lambda d: dtext(d, W / 2 + 40, 975, 'al atardecer', script(130), BEIGE), (8, 200, 3)), 1.6, 6.2, wipe=1.1, fin=0.2, rise=0))

# ---- frases letra por letra (zona media; abajo queda libre para la caja de preguntas)
def phrase(lines, t0, t1, cps=20):
    ls, tend = typewriter(lines, t0, t1, cps=cps); L.extend(ls); return tend

phrase([('Hay caminos', cinzel(66), WHITE, 860, 3), ('que se vuelven costumbre…', cinzel(58), WHITE, 950, 2)], 7.0, 12.6)
phrase([('…y costumbres', cinzel(66), WHITE, 820, 3), ('que se vuelven', cinzel(58), WHITE, 905, 2)], 13.6, 20.0)
L.append(Layer(block(lambda d: dtext(d, W / 2, 985, 'hogar', script(190), BEIGE), (10, 210, 3)), 15.3, 20.0, wipe=0.9, fin=0.2, rise=0))

# pin de ubicación cuando aparecen los volcanes
tp = at(2, 49.5)
def _pin(d):
    pin_icon(d, W / 2, 610, 30, BEIGE, VINO)
    dtext(d, W / 2, 500, 'ANTIGUA GUATEMALA', cinzelb(46), WHITE, tr=6)
L.append(Layer(block(_pin), tp, tp + 6.0, fin=0.4, rise=-60, sdur=0.7, ease=back_out))
phrase([('Volcanes de fondo,', cinzel(62), WHITE, 900, 2)], tp + 1.2, ST[3] + 0.2)
phrase([('calles con historia,', cinzel(62), WHITE, 990, 2)], tp + 3.6, ST[3] + 0.2)

t = ST[3] + 1.0
phrase([('y un cielo que cada tarde', cinzel(58), WHITE, 880, 2), ('se pinta distinto.', cinzel(58), WHITE, 960, 2)], t, t + 7.5)

# "Así se siente / VIVIR EN ANTIGUA" con palabra clave que cambia de color
t = ST[3] + 9.2
L.append(Layer(block(lambda d: dtext(d, W / 2, 850, 'así se siente', script(110), BEIGE)), t, ST[4] + 1.5, wipe=0.9, fin=0.2, rise=0))
L.append(Layer(block(lambda d: dtext(d, W / 2, 975, 'VIVIR EN ANTIGUA', cinzelb(84), WHITE, tr=5), (10, 210, 3)), t + 0.8, ST[4] + 1.5, fin=0.6, rise=24))
L.append(Layer(block(lambda d: dtext(d, W / 2, 975, 'VIVIR EN ANTIGUA', cinzelb(84), BEIGE, tr=5), (10, 210, 3)), t + 2.4, ST[4] + 1.5, fin=0.8, rise=0))

# pregunta para la caja de preguntas
t = ST[4] + 2.0
L.append(Layer(block(lambda d: (dtext(d, W / 2, 820, '¿Y cuál es', cinzel(66), WHITE, tr=3),
                                dtext(d, W / 2, 900, 'TU', cinzelb(120), BEIGE, tr=4),
                                dtext(d, W / 2, 1030, 'ruta favorita?', script(118), WHITE))), t, ST[5] + 0.6, fin=0.7, rise=24))
def _cta(d):
    w = dtext(d, W / 2 - 30, 1190, 'CUÉNTAMELA AQUÍ', cinzelb(38), WHITE, tr=6)
    arrow_down(d, W / 2 - 30 + w / 2 + 40, 1192, 40, WHITE)
L.append(Layer(block(_cta), t + 1.2, ST[5] + 0.6, fin=0.5, rise=-14))

# ---- tarjeta final (logo: aparece)
ec, ev = endcard(END, TOTAL + 1, mode='aparece')
L += ec; EV += ev

if __name__ == '__main__':
    if sys.argv[1:2] == ['frames']:
        for tt in map(float, sys.argv[2:]):
            Image.fromarray(render_frame(L, tt), 'RGBA').save(f'work/h3_ov_{tt}.png')
    else:
        os.makedirs('work', exist_ok=True)
        print('total', TOTAL, 'starts', ST)
        render_segments(SEGS, 'work/h3')
        mx = Mix(TOTAL); music_calm(mx, bpm=72)
        # regla: en la parte emocional, sin efectos; solo en la tarjeta final
        master(mx, EV, 'work/h3_audio.wav', music_gain=0.6)
        assemble(SEGS, 'work/h3', L, 'work/h3_audio.wav', 'out/historia3_ruta_favorita.mp4')
        print('ok')
