# Texturas de detalle "tileables" NEUTRAS (media ~0.5) para madera, metal y piedra.
# Se usan en Unity como Detail Map de URP/Lit (albedo x2 + normal) encima de las texturas horneadas
# de los objetos B_*: aportan alta frecuencia (~700 px/m con un tile de 1.5 m) sin gastar VRAM extra.
#   T_Det_Madera.png / T_Det_Madera_N.png : veta, poros y grietas finas (veta en el eje X)
#   T_Det_Metal.png  / T_Det_Metal_N.png  : rayones, picaduras y manchas de oxido
#   T_Det_Piedra.png / T_Det_Piedra_N.png : sillares, poros y grietas
# Uso: blender -b archivo.blend --python detalle_materiales.py
import bpy, os, numpy as np

RUT = os.path.dirname(bpy.data.filepath)
SALIDAS = [os.path.join(RUT, "texturas"), os.path.join(os.path.dirname(RUT), "Assets", "Textures")]
for s in SALIDAS:
    os.makedirs(s, exist_ok=True)
N = 1024


def fbm(beta, seed, aniso=(1.0, 1.0)):
    """ruido periodico con espectro 1/f^beta; aniso estira las estructuras (valor bajo = alargado en ese eje)"""
    r = np.random.default_rng(seed)
    ruido = r.standard_normal((N, N))
    fx = np.fft.fftfreq(N)[None, :] * aniso[0]
    fy = np.fft.fftfreq(N)[:, None] * aniso[1]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    esp = np.fft.fft2(ruido) / (f ** (beta / 2.0))
    esp[0, 0] = 0
    a = np.real(np.fft.ifft2(esp))
    return (a - a.min()) / (a.max() - a.min())


def smooth(a, e0, e1):
    t = np.clip((a - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def neutro(h, contraste):
    """lleva el mapa a media 0.5 con la desviacion pedida (albedo de detalle: 0.5 = sin cambio)"""
    h = (h - h.mean()) / (h.std() + 1e-6)
    return np.clip(0.5 + contraste * h, 0.0, 1.0)


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


def gris(a):
    return np.stack([a, a, a], -1)


yy = np.arange(N)[:, None] / N

# ------------------------------------------------------------ MADERA (veta a lo largo de X)
veta = fbm(1.5, 21, aniso=(0.05, 1.0))                        # fibras largas
fibra = fbm(1.1, 22, aniso=(0.10, 1.0))                       # fibras finas
anillos = 0.5 + 0.5 * np.sin(2 * np.pi * (9 * yy + 3.0 * fbm(2.2, 23, aniso=(0.2, 1.0))))
poros = fbm(0.8, 24, aniso=(0.3, 1.0))
lin = np.abs(fbm(1.8, 25, aniso=(0.08, 1.0)) * 2 - 1)
grieta = (1.0 - smooth(lin, 0.0, 0.035)) * smooth(fbm(2.6, 26), 0.5, 0.7)   # fisuras finas, solo en parte
h = 0.40 * veta + 0.22 * fibra + 0.22 * anillos + 0.16 * poros - 0.55 * grieta
alb = neutro(h, 0.13) * (1.0 - 0.45 * grieta) * (0.92 + 0.16 * fbm(3.0, 27))
guardar("T_Det_Madera.png", gris(np.clip(alb, 0, 1)), True)
guardar("T_Det_Madera_N.png", normal_de(h, 3.2), False)

# ------------------------------------------------------------ METAL OXIDADO
rayas = fbm(0.9, 31, aniso=(0.06, 1.0)) * 0.6 + fbm(0.9, 32, aniso=(1.0, 0.06)) * 0.4
picado = smooth(fbm(0.7, 33), 0.62, 0.8)                      # picaduras diminutas
oxido = smooth(fbm(2.4, 34), 0.45, 0.72)                      # manchas grandes de oxido
granos = fbm(0.6, 35)
h = 0.30 * rayas + 0.25 * granos - 0.45 * picado + 0.35 * oxido * fbm(1.4, 36)
alb = neutro(h, 0.14) * (1.0 - 0.30 * oxido) * (1.0 - 0.35 * picado)
guardar("T_Det_Metal.png", gris(np.clip(alb, 0, 1)), True)
guardar("T_Det_Metal_N.png", normal_de(h, 2.6), False)

# ------------------------------------------------------------ PIEDRA / MAMPOSTERIA
base = fbm(2.4, 41)
poros = fbm(1.0, 42)
cresta = 1.0 - np.abs(fbm(2.1, 43) * 2 - 1)
lin = np.abs(fbm(2.2, 44) * 2 - 1)
grieta = (1.0 - smooth(lin, 0.0, 0.04)) * smooth(fbm(2.6, 45), 0.5, 0.68)
h = 0.38 * base + 0.26 * cresta ** 2 + 0.22 * poros - 0.45 * grieta
alb = neutro(h, 0.14) * (1.0 - 0.40 * grieta) * (0.9 + 0.2 * fbm(3.0, 46))
guardar("T_Det_Piedra.png", gris(np.clip(alb, 0, 1)), True)
guardar("T_Det_Piedra_N.png", normal_de(h, 3.6), False)

# ------------------------------------------------------------ CORTEZA (surcos a lo largo de V = eje Y de la textura)
surco = fbm(1.7, 51, aniso=(1.0, 0.045))                      # surcos largos verticales
surco2 = fbm(1.3, 52, aniso=(0.7, 0.08))
fis = np.abs(fbm(1.9, 53, aniso=(1.0, 0.06)) * 2 - 1)
grieta = (1.0 - smooth(fis, 0.0, 0.05)) * smooth(fbm(2.4, 54), 0.35, 0.65)
placas = smooth(fbm(2.2, 55, aniso=(0.8, 0.15)), 0.5, 0.65)    # placas de corteza levantadas
liquen = smooth(fbm(2.8, 56), 0.62, 0.78)                      # manchas claras (liquen / ceniza)
h = 0.45 * surco + 0.2 * surco2 + 0.2 * placas - 0.7 * grieta
alb = neutro(h, 0.16) * (1.0 - 0.55 * grieta) * (1.0 + 0.35 * liquen)
guardar("T_Det_Corteza.png", gris(np.clip(alb, 0, 1)), True)
guardar("T_Det_Corteza_N.png", normal_de(h, 4.2), False)
