"""Her zirve için gerçek DEM (AWS Terrain Tiles / Terrarium) + Sentinel-2 cloudless 2016 (EOX, CC BY 4.0) indirir.
Çıktı: build/terrain/<rank>.f32 (NxN yükseklik, metre) + <rank>.jpg (uydu dokusu) + meta.json"""
import math, io, json, os, sys, urllib.request, concurrent.futures as cf
import numpy as np
from PIL import Image
OUT = 'build/terrain'; os.makedirs(OUT, exist_ok=True); CACHE = 'build/tilecache'; os.makedirs(CACHE, exist_ok=True)
# yaklaşık zirve koordinatları (DEM maksimumuna göre yeniden ortalanır), arama yarıçapı (derece)
PEAKS = {10: (37.414, 34.624, .05), 9: (39.78, 39.72, .08), 8: (39.364, 43.875, .06), 7: (37.828, 35.149, .03),
         6: (39.646, 44.409, .03), 5: (38.531, 35.448, .04), 4: (40.835, 41.161, .04), 3: (38.931, 42.831, .04),
         2: (37.47, 44.02, .06), 1: (39.702, 44.298, .04)}
SPAN_KM, N, TEX = 32.0, 800, 4096
DEM_Z, IMG_Z = 13, 14

def tile_xy(lat, lon, z):
    n = 2 ** z; x = (lon + 180) / 360 * n; y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n; return x, y

def get(url, path):
    if os.path.exists(path): return open(path, 'rb').read()
    for i in range(4):
        try:
            d = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'terrain-video/1.0'}), timeout=30).read()
            open(path, 'wb').write(d); return d
        except Exception as e: err = e
    raise err

def mosaic(lat, lon, half_km, z, kind):
    # half_km çevresindeki karoları birleştir, merkez etrafında kare kırp (piksel uzayı)
    cx, cy = tile_xy(lat, lon, z)
    m_per_px = 40075016.7 * math.cos(math.radians(lat)) / (2 ** z * 256)
    hp = half_km * 1000 / m_per_px  # piksel cinsinden yarım genişlik
    x0, x1 = int(math.floor((cx * 256 - hp) / 256)), int(math.floor((cx * 256 + hp) / 256))
    y0, y1 = int(math.floor((cy * 256 - hp) / 256)), int(math.floor((cy * 256 + hp) / 256))
    jobs = {}
    with cf.ThreadPoolExecutor(12) as ex:
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if kind == 'dem': url = f'https://elevation-tiles-prod.s3.amazonaws.com/terrarium/{z}/{tx}/{ty}.png'
                else: url = f'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{ty}/{tx}.jpg'
                jobs[(tx, ty)] = ex.submit(get, url, f'{CACHE}/{kind}_{z}_{tx}_{ty}')
    W, H = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256
    if kind == 'dem':
        arr = np.zeros((H, W), np.float32)
        for (tx, ty), j in jobs.items():
            a = np.asarray(Image.open(io.BytesIO(j.result())).convert('RGB')).astype(np.float32)
            arr[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
        img = Image.fromarray(arr, 'F')
    else:
        img = Image.new('RGB', (W, H))
        for (tx, ty), j in jobs.items(): img.paste(Image.open(io.BytesIO(j.result())).convert('RGB'), ((tx - x0) * 256, (ty - y0) * 256))
    ox, oy = cx * 256 - x0 * 256, cy * 256 - y0 * 256
    return img.crop((round(ox - hp), round(oy - hp), round(ox + hp), round(oy + hp)))

meta = {}
for rank, (lat, lon, rad) in PEAKS.items():
    # 1) zirveyi bul: arama alanını DEM'de tara
    srch = mosaic(lat, lon, rad * 111, DEM_Z, 'dem'); a = np.asarray(srch)
    iy, ix = np.unravel_index(np.argmax(a), a.shape); s = a.shape[0]
    plat = lat - (iy / s - .5) * 2 * rad * 111 / 111.0 * 1.0 / 1.0 * (1 / 1)  # yaklaşık
    plon = lon + (ix / s - .5) * 2 * rad * 111 / (111.32 * math.cos(math.radians(lat)))
    plat = lat - (iy / s - .5) * 2 * rad * 111 / 110.57
    dem = mosaic(plat, plon, SPAN_KM / 2, DEM_Z, 'dem').resize((N, N), Image.BILINEAR)
    d = np.asarray(dem, np.float32); d.astype('<f4').tofile(f'{OUT}/{rank}.f32')
    tex = mosaic(plat, plon, SPAN_KM / 2, IMG_Z, 'img').resize((TEX, TEX), Image.LANCZOS); tex.save(f'{OUT}/{rank}.jpg', quality=90)
    meta[rank] = {'lat': round(plat, 4), 'lon': round(plon, 4), 'max': float(d.max()), 'min': float(d.min()), 'span_km': SPAN_KM, 'n': N}
    print(rank, meta[rank], flush=True)
json.dump(meta, open(f'{OUT}/meta.json', 'w'), indent=1)
