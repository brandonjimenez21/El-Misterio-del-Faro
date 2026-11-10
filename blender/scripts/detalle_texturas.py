# Texturas de detalle "tileables" (se repiten sin costuras) para la roca y el pasto de la isla.
# Se generan con numpy (ruido por FFT = periodico por construccion). Salen a blender/texturas/ y Assets/Textures/.
#   T_Detalle_Roca.png / T_Detalle_Roca_N.png   : estratos, grietas y poros de roca
#   T_Detalle_Pasto.png / T_Detalle_Pasto_N.png : hebras de hierba y tierra
# Uso: blender -b archivo.blend --python detalle_texturas.py
import bpy, os, numpy as np

RUT = os.path.dirname(bpy.data.filepath)
SALIDAS = [os.path.join(RUT, "texturas"), os.path.join(os.path.dirname(RUT), "Assets", "Textures")]
for s in SALIDAS:
    os.makedirs(s, exist_ok=True)
N = 1024
rng = np.random.default_rng(5)


def fbm(beta, seed, aniso=(1.0, 1.0)):
    """ruido periodico con espectro 1/f^beta; aniso estira las estructuras en x o y"""
    r = np.random.default_rng(seed)
    ruido = r.standard_normal((N, N))
    fx = np.fft.fftfreq(N)[None, :] * aniso[0]
    fy = np.fft.fftfreq(N)[:, None] * aniso[1]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    esp = np.fft.fft2(ruido) / (f ** (beta / 2.0))
    esp[0, 0] = 0
    a = np.real(np.fft.ifft2(esp))
    a = (a - a.min()) / (a.max() - a.min())
    return a


def voronoi_aristas(n_pts, seed):
    """F2-F1 periodico: vale ~0 en las aristas de las celdas (grietas)"""
    r = np.random.default_rng(seed)
    pts = r.random((n_pts, 2))
    yy, xx = np.mgrid[0:N, 0:N] / N
    d1 = np.full((N, N), 9.0)
    d2 = np.full((N, N), 9.0)
    for p in pts:
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                d = np.sqrt((xx - p[0] - ox) ** 2 + (yy - p[1] - oy) ** 2)
                m = d < d1
                d2 = np.where(m, d1, np.minimum(d2, d))
                d1 = np.where(m, d, d1)
    return d2 - d1


def smooth(a, e0, e1):
    t = np.clip((a - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def normal_de(h, fuerza):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * fuerza * N / 256
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * fuerza * N / 256
    nx, ny, nz = -dx, -dy, np.ones_like(h)
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    return np.stack([nx / l * 0.5 + 0.5, ny / l * 0.5 + 0.5, nz / l * 0.5 + 0.5], -1)


def guardar(nombre, rgb, srgb=True):
    for s in SALIDAS:
        im = bpy.data.images.new(nombre, N, N, alpha=False)
        im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        px = np.ones((N, N, 4), dtype=np.float32)
        px[..., :3] = rgb
        im.pixels.foreach_set(px.ravel())
        im.filepath_raw = os.path.join(s, nombre)
        im.file_format = 'PNG'
        im.save()
        bpy.data.images.remove(im)
    print("DETALLE guardada", nombre)


# ------------------------------------------------------------ ROCA
base = fbm(2.6, 1)
cresta = 1.0 - np.abs(fbm(2.2, 2) * 2 - 1)               # crestas afiladas
lin = np.abs(fbm(2.3, 3) * 2 - 1)                         # ~0 sobre lineas sinuosas
lin2 = np.abs(fbm(2.0, 7) * 2 - 1)
mascara = smooth(fbm(2.6, 9), 0.45, 0.65)                 # las grietas solo aparecen en parte de la roca
grieta = np.maximum(1.0 - smooth(lin, 0.0, 0.05), 0.7 * (1.0 - smooth(lin2, 0.0, 0.03))) * mascara
yy = np.arange(N)[:, None] / N
estrato = 0.5 + 0.5 * np.sin(2 * np.pi * (7 * yy + 1.4 * fbm(2.0, 4)))
poros = fbm(1.2, 6)
h = 0.40 * base + 0.30 * cresta ** 2 + 0.14 * estrato + 0.16 * poros - 0.40 * grieta
h = (h - h.min()) / (h.max() - h.min())
alb = 0.38 + 0.62 * h
alb *= (1.0 - 0.55 * grieta)
alb *= 0.85 + 0.3 * fbm(3.0, 8)                           # manchas grandes
col = np.stack([alb * 1.0, alb * 0.97, alb * 0.92], -1)    # gris calido
guardar("T_Detalle_Roca.png", col, True)
guardar("T_Detalle_Roca_N.png", normal_de(h, 5.0), False)

# ------------------------------------------------------------ PASTO
hebras = fbm(1.6, 11, aniso=(0.12, 1.0))                  # estructuras alargadas
hebras2 = fbm(1.2, 12, aniso=(0.25, 1.0))
manchas = fbm(2.8, 13)
hp = 0.5 * hebras + 0.35 * hebras2 + 0.15 * manchas
hp = (hp - hp.min()) / (hp.max() - hp.min())
v = 0.45 + 0.55 * hp
v *= 0.8 + 0.4 * manchas
tierra = smooth(manchas, 0.62, 0.75)[..., None]
verde = np.stack([v * 0.9, v * 1.0, v * 0.65], -1)
marron = np.stack([v * 1.0, v * 0.82, v * 0.62], -1)
guardar("T_Detalle_Pasto.png", verde * (1 - tierra) + marron * tierra, True)
guardar("T_Detalle_Pasto_N.png", normal_de(hp, 3.0), False)
