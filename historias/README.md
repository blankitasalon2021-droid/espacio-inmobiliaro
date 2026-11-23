# Historias de 1 minuto — estilo de vida (Espacio Inmobiliario)

Tres historias verticales (1080×1920, 30 fps, ~60 s, −14 LUFS), hechas con el video de la ruta al atardecer:

- `h3_ruta_favorita.py`: "Mi ruta favorita al atardecer". Frases letra por letra, pin de Antigua y pregunta con espacio para la caja de preguntas. El logo aparece.
- `h6_mitos.py`: "Mitos de comprar casa en Guatemala". 4 mitos que se tachan, realidad y encuesta. El logo se arma.
- `h10_adivina.py`: "Adivina la calle". 3 rondas con imagen congelada y cuenta regresiva. El logo se dibuja.

`lib.py` reúne el video base, los gráficos, la tarjeta final de marca, la música original sintetizada, los efectos de sonido y el master.
Zona libre para stickers (encuesta/preguntas): entre y=1250 y y=1560.
Uso: `SRC=/ruta/video.mp4 python3 h3_ruta_favorita.py render` (genera `out/*.mp4`, no se versiona).
