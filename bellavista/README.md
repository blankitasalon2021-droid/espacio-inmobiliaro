# Bellavista — Video inmobiliario (Espacio Inmobiliario)

Proyecto de edición por código (ffmpeg + Python).

1. `scripts/transcribe.py` — transcripción de diálogos (Whisper).
2. `scripts/edl.py` — lista de edición: tomas, entradas, duraciones, cámara lenta, disolvencias, voz y subtítulos.
3. `scripts/render_segments.py` — HDR→SDR, encuadre 9:16, corrección de color, nitidez y cámara lenta interpolada.
4. `scripts/graphics.py` — títulos, datos, subtítulos, precio y cierre de marca (Cormorant Garamond + Montserrat, colores #E7D3AF / #661E1A).
5. `scripts/music.py` — música original compuesta y sintetizada por código (piano + cuerdas), libre de derechos de terceros.
6. `scripts/audio.py` — limpieza de voz, EQ, compresión, ducking de música, mezcla a -14 LUFS / -1 dBTP.
7. `scripts/assemble.py` — montaje final 1080x1920, 30 fps, H.264 + AAC.

Los videos originales no se incluyen en el repositorio.
