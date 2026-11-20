# Vista previa: compone el fotograma del segmento + capa gráfica en tiempos dados → hoja de contacto
import sys, subprocess, io
from PIL import Image, ImageDraw
sys.argv, ts = sys.argv[:1], [float(x) for x in sys.argv[1:]]
from edl import SEGS, timeline
import overlay
tl, T = timeline()
tiles = []
for t in ts:
    seg = [s for s in SEGS if tl[s['id']][0] <= t < tl[s['id']][1]][-1]
    lt = t - tl[seg['id']][0]
    png = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{lt:.3f}', '-i', f"seg/{seg['id']}.mp4", '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    bg = Image.open(io.BytesIO(png)).convert('RGBA')
    bg.alpha_composite(Image.fromarray(overlay.frame(t), 'RGBA'))
    d = ImageDraw.Draw(bg)
    # guías de margen de seguridad
    d.rectangle((60, 220, 960, 1500), outline=(0, 255, 0, 255), width=2)
    d.text((10, 10), f't={t}', fill=(255, 0, 0, 255))
    tiles.append(bg.convert('RGB').resize((360, 640)))
sheet = Image.new('RGB', (360 * len(tiles), 640))
for k, im in enumerate(tiles): sheet.paste(im, (360 * k, 0))
sheet.save('st/preview.jpg', quality=88)
