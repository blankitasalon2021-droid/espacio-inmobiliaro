# Edit decision list — Bellavista v4 (combinación de las 3 ideas)
# tr: transición HACIA este segmento: 'whipL'/'whipR' (barrido con desenfoque), 'flash' (flash blanco),
#     'fade' (disolvencia). xf = duración del traslape.
FPS = 30
VDUR = 9.2
SEGS = [
 # GANCHO — portada de revista (fotograma congelado) y arranque
 dict(id='a', src='Mi_peli_cula', ss=1.95, dur=2.4, freeze=True, push=True),
 dict(id='b', src='Mi_peli_cula', ss=1.95, dur=10.3, tr='flash', xf=0.3),
 # SALA EN DOBLE ALTURA
 dict(id='c', src='Mi_peli_cula_1', ss=0.80, dur=3.4, tr='whipL', xf=0.3),
 dict(id='d', src='IMG_1459', ss=0.6, dur=1.8),
 dict(id='e', src='IMG_1474', ss=0.3, dur=2.0, speed=0.75),
 # COMEDOR, COCINA Y PATIO
 dict(id='f', src='Mi_peli_cula_2', ss=0.45, dur=3.0, tr='whipR', xf=0.3),
 dict(id='g', src='IMG_1476', ss=4.0, dur=2.4),
 dict(id='h', src='IMG_1477', ss=0.0, dur=1.6),
 dict(id='i', src='IMG_1478', ss=0.2, dur=3.8, checklist=True),
 # SEGUNDO NIVEL
 dict(id='j', src='IMG_1480', ss=5.0, dur=2.0, tr='whipL', xf=0.3),
 dict(id='k', src='Mi_peli_cula_3', ss=None, dur=2.9, sync='j'),
 dict(id='l', src='IMG_1460', ss=1.7, dur=2.0),
 # HABITACIÓN PRINCIPAL
 dict(id='m', src='Mi_peli_cula_4', ss=2.4, dur=2.9, tr='whipR', xf=0.3),
 dict(id='n', src='IMG_1465', ss=0.3, dur=1.3),
 dict(id='o', src='IMG_1466', ss=0.4, dur=1.2),
 dict(id='p', src='IMG_1468', ss=2.4, dur=2.0),
 # TERRAZA: día → atardecer
 dict(id='r', src='IMG_1470', ss=0.8, dur=2.0, tr='whipL', xf=0.3),
 dict(id='t', src='Mi_peli_cula_5', ss=0.55, dur=7.25, dusk=(1.2, 6.2)),
 # PRECIO + TARJETA FINAL (última toma desenfocada, ya en atardecer)
 dict(id='v', src='Mi_peli_cula_5', ss=7.78, dur=VDUR, tr='fade', xf=0.7, freeze=True, closing=True, dusk=(0, 0)),
]

VOICE = [
 ('Mi_peli_cula',   1.85, 12.00, 'b', -0.10),
 ('Mi_peli_cula_1', 1.10,  5.45, 'c',  0.30),
 ('Mi_peli_cula_2', 0.62,  6.25, 'f',  0.17),
 ('Mi_peli_cula_3', 0.70,  5.30, 'j',  0.30),
 ('Mi_peli_cula_4', 2.65,  8.75, 'm',  0.25),
 ('Mi_peli_cula_5', 0.75,  7.55, 't',  0.20),
]

SUBS = {
 'Mi_peli_cula': [("Bellavista, uno de mis", 1.95, 3.34), ("residenciales favoritos,", 3.34, 4.42),
                  ("no solo por sus calles empedradas", 4.42, 5.98), ("y abundante vegetación,", 5.98, 7.25),
                  ("sino por esa tranquilidad", 7.30, 8.44), ("que solo se vive a minutos de Antigua.", 8.44, 10.38),
                  ("Ven, que te muestro esta propiedad.", 10.38, 11.95)],
 'Mi_peli_cula_1': [("Al entrar a esta hermosa casa", 1.25, 2.36), ("nos recibe una imponente sala", 2.36, 4.0),
                    ("con techo en doble altura.", 4.0, 5.4)],
 'Mi_peli_cula_2': [("Y a través de este pasillo", 0.79, 2.0), ("que nos conduce hacia el comedor", 2.0, 3.3),
                    ("y la cocina,", 3.3, 3.9), ("con acceso directo hacia el patio trasero.", 3.9, 6.2)],
 'Mi_peli_cula_3': [("Y en el segundo nivel", 0.88, 1.78), ("nos encontramos en medio", 1.78, 2.86),
                    ("de las tres habitaciones", 2.86, 3.88), ("una sala familiar.", 3.88, 5.2)],
 'Mi_peli_cula_4': [("Y además la habitación principal", 2.92, 4.48), ("cuenta con su propia chimenea,", 4.48, 5.95),
                    ("techo en doble altura,", 5.95, 6.95), ("walk-in closet y baño privado.", 6.95, 8.6)],
 'Mi_peli_cula_5': [("Y como no puede faltar", 0.92, 2.18), ("una amplia terraza.", 2.18, 3.48),
                    ("Si deseas conocer esta casa,", 3.48, 4.78), ("contáctame.", 4.78, 5.46),
                    ("Soy Dani Álvarez", 5.46, 6.42), ("de Espacio Inmobiliario.", 6.42, 7.5)],
}
# Palabras clave que cambian de color (fondo vino)
KEYWORDS = {'BELLAVISTA', 'EMPEDRADAS', 'ANTIGUA', 'IMPONENTE', 'DOBLE', 'ALTURA', 'COMEDOR', 'COCINA', 'PATIO',
            'TRASERO', 'NIVEL', 'TRES', 'HABITACIONES', 'FAMILIAR', 'PRINCIPAL', 'CHIMENEA', 'WALK-IN', 'CLOSET',
            'BAÑO', 'PRIVADO', 'TERRAZA'}

def src_path(src):
    return f"norm/{src}.mov" if src.startswith('Mi_') else f"norm/{src}.mp4"

def timeline():
    t = 0.0; out = {}
    for s in SEGS:
        xf = s.get('xf', 0.0)
        st = t - xf
        out[s['id']] = (st, st + s['dur'])
        t = st + s['dur']
    return out, t

def resolve_sync():
    tl, _ = timeline()
    vmap = {v[3]: v for v in VOICE}
    for s in SEGS:
        if s.get('sync'):
            clip, a, b, _, off = vmap[s['sync']]
            s['ss'] = a + (tl[s['id']][0] - (tl[s['sync']][0] + off))
resolve_sync()

if __name__ == '__main__':
    tl, total = timeline()
    for s in SEGS:
        print(s['id'], s['src'], round(s['ss'], 2), [round(x, 2) for x in tl[s['id']]])
    print('TOTAL', round(total, 2))
