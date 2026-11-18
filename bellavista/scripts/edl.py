# Edit decision list — Bellavista (Espacio Inmobiliario)
# Each segment: id, src, ss (source in), dur (timeline dur), speed (<1 = slow), xf (dissolve INTO this seg)
FPS = 30
SEGS = [
 # ESCENA 1 — BELLAVISTA
 dict(id='a', src='Mi_peli_cula', ss=0.45, dur=2.2, speed=0.68, scene=1),
 dict(id='b', src='Mi_peli_cula', ss=1.95, dur=10.45, scene=1),
 # ESCENA 2 — SALA PRINCIPAL
 dict(id='c', src='Mi_peli_cula_1', ss=0.30, dur=5.25, xf=0.45, scene=2),
 dict(id='d', src='IMG_1474', ss=0.30, dur=3.6, speed=0.75, scene=2),
 dict(id='e', src='IMG_1458', ss=0.20, dur=2.8, scene=2),
 # ESCENA 3 — COMEDOR, COCINA, PATIO
 dict(id='f', src='Mi_peli_cula_2', ss=0.45, dur=3.0, scene=3),
 dict(id='g', src='IMG_1476', ss=4.0, dur=2.7, scene=3),
 dict(id='h', src='IMG_1477', ss=0.0, dur=3.0, scene=3),
 dict(id='i', src='IMG_1478', ss=1.2, dur=2.4, xf=0.35, scene=3),
 # ESCENA 4 — SEGUNDO NIVEL
 dict(id='j', src='IMG_1480', ss=5.0, dur=2.2, scene=4),
 dict(id='k', src='Mi_peli_cula_3', ss=None, dur=2.8, sync='j', scene=4),
 dict(id='l', src='IMG_1460', ss=1.7, dur=2.8, scene=4),
 # ESCENA 5 — HABITACIÓN PRINCIPAL
 dict(id='m', src='Mi_peli_cula_4', ss=2.4, dur=2.9, scene=5),
 dict(id='n', src='IMG_1465', ss=0.3, dur=1.35, scene=5),
 dict(id='o', src='IMG_1466', ss=0.4, dur=1.2, scene=5),
 dict(id='p', src='IMG_1468', ss=2.4, dur=3.2, scene=5),
 dict(id='q', src='IMG_1463', ss=0.5, dur=2.2, speed=0.8, scene=5),
 # ESCENA 6 — PATIO ALTO, TERRAZA Y CIERRE
 dict(id='r', src='IMG_1470', ss=0.8, dur=3.4, xf=0.35, scene=6),
 dict(id='s', src='IMG_1471', ss=0.0, dur=2.8, scene=6),
 dict(id='t', src='Mi_peli_cula_5', ss=0.55, dur=7.2, scene=6),
 dict(id='u', src='Mi_peli_cula', ss=12.30, dur=2.8, speed=0.5, xf=0.5, scene=7),
 dict(id='v', src='IMG_1459', ss=0.4, dur=6.6, speed=0.5, xf=0.6, scene=7, closing=True),
 dict(id='w', src='CARD', ss=0, dur=4.2, xf=0.6, scene=7),
]

# Voice placements: clip, src_from, src_to, anchor segment id, timeline offset relative to anchor start
VOICE = [
 ('Mi_peli_cula',   1.85, 12.00, 'b', -0.10),
 ('Mi_peli_cula_1', 1.10,  5.45, 'c',  0.80),
 ('Mi_peli_cula_2', 0.62,  6.25, 'f',  0.17),
 ('Mi_peli_cula_3', 0.70,  5.30, 'j',  0.30),
 ('Mi_peli_cula_4', 2.65,  8.75, 'm',  0.25),
 ('Mi_peli_cula_5', 0.75,  7.55, 't',  0.20),
]

# Subtitles (source-time ranges within each dialogue clip)
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

def timeline():
    """Return dict id -> (start, end) on the output timeline (dissolves overlap)."""
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
            anc = s['sync']; clip, a, b, _, off = vmap[anc]
            # source time of this clip at this segment's start
            s['ss'] = a + (tl[s['id']][0] - (tl[anc][0] + off))
resolve_sync()

if __name__ == '__main__':
    tl, total = timeline()
    for s in SEGS:
        print(s['id'], s['src'], round(s['ss'], 2), tl[s['id']])
    print('TOTAL', round(total, 2))
