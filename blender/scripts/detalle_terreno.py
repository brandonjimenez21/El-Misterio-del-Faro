# Capas de terreno "tileables" (1024 px, periodicas) para el shader Faro/IslaDetalle v3.
# Cada capa sale como RGBA: RGB = color (albedo, valores absolutos) y A = altura (para mezclar capas por altura, sin transiciones borrosas).
#   T_Ter_Hierba.png / T_Ter_Hierba_N.png : cesped corto (hebras en varias direcciones, motas secas, huecos de tierra)
#   T_Ter_Tierra.png / T_Ter_Tierra_N.png : tierra de camino pisada y humeda, con gravilla, piedras medio enterradas y paja seca
#   T_Ter_Arena.png  / T_Ter_Arena_N.png  : arena de orilla con granos, ondulaciones y piedrecitas
# Uso: blender -b archivo.blend --python detalle_terreno.py
import bpy, os, numpy as np

RUT = os.path.dirname(bpy.data.filepath)
SALIDAS = [os.path.join(RUT, "texturas"), os.path.join(os.path.dirname(RUT), "Assets", "Textures")]
for s in SALIDAS:
    os.makedirs(s, exist_ok=True)
N = 1024


def fbm(beta, seed, aniso=(1.0, 1.0), theta=0.0):
    """ruido periodico 1/f^beta; theta gira la direccion de las estructuras, aniso las estira (valor bajo = alargado)"""
    r = np.random.default_rng(seed)
    ruido = r.standard_normal((N, N))
    fx0 = np.fft.fftfreq(N)[None, :] * np.ones((N, 1))
    fy0 = np.fft.fftfreq(N)[:, None] * np.ones((1, N))
    c, s = np.cos(theta), np.sin(theta)
    fx = (fx0 * c + fy0 * s) * aniso[0]
    fy = (-fx0 * s + fy0 * c) * aniso[1]
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1.0
    esp = np.fft.fft2(ruido) / (f ** (beta / 2.0))
    esp[0, 0] = 0
    a = np.real(np.fft.ifft2(esp))
    return (a - a.min()) / (a.max() - a.min())


def smooth(a, e0, e1):
    t = np.clip((a - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def voronoi(n_pts, seed):
    """periodico: devuelve d1 (distancia al centro mas cercano), d2 (al segundo) y el indice de celda"""
    r = np.random.default_rng(seed)
    pts = r.random((n_pts, 2))
    yy, xx = np.mgrid[0:N, 0:N] / N
    d1 = np.full((N, N), 9.0)
    d2 = np.full((N, N), 9.0)
    idx = np.zeros((N, N), dtype=np.int32)
    for k, p in enumerate(pts):
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                d = np.sqrt((xx - p[0] - ox) ** 2 + (yy - p[1] - oy) ** 2)
                m = d < d1
                d2 = np.where(m, d1, np.minimum(d2, d))
                idx = np.where(m, k, idx)
                d1 = np.where(m, d, d1)
    return d1, d2, idx, r.random(n_pts)


def normal_de(h, fuerza):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * fuerza * N / 256
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * fuerza * N / 256
    nx, ny, nz = -dx, -dy, np.ones_like(h)
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    return np.stack([nx / l * 0.5 + 0.5, ny / l * 0.5 + 0.5, nz / l * 0.5 + 0.5], -1)


def guardar(nombre, rgb, alfa=None, srgb=True):
    for s in SALIDAS:
        im = bpy.data.images.new(nombre, N, N, alpha=True)
        im.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
        im.alpha_mode = 'CHANNEL_PACKED'
        px = np.ones((N, N, 4), dtype=np.float32)
        px[..., :3] = np.clip(rgb, 0, 1)
        if alfa is not None:
            px[..., 3] = np.clip(alfa, 0, 1)
        im.pixels.foreach_set(px.ravel())
        im.filepath_raw = os.path.join(s, nombre)
        im.file_format = 'PNG'
        im.save()
        bpy.data.images.remove(im)
    print("TERRENO guardada", nombre)


def mezcla(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def col(r, g, b):
    return np.array([r, g, b], dtype=np.float32)


# ------------------------------------------------------------ utilidades de pintado (todo periodico: las coordenadas dan la vuelta)
def pintar(Y, X, H, C, hgt, color):
    """escribe los puntos ordenados por altura creciente: en cada pixel gana el mas alto"""
    iy, ix = Y % N, X % N
    orden = np.argsort(hgt, kind="stable")
    iy, ix, hgt, color = iy[orden], ix[orden], hgt[orden], color[orden]
    # solo si supera lo que ya hay
    mejor = hgt > H[iy, ix]
    H[iy[mejor], ix[mejor]] = hgt[mejor]
    C[iy[mejor], ix[mejor]] = color[mejor]


def hojas(n, seed, lmin, lmax, ancho):
    r = np.random.default_rng(seed)
    pasos = 48
    t = np.linspace(0, 1, pasos)[None, :]
    x0, y0 = r.random(n)[:, None] * N, r.random(n)[:, None] * N
    ang = r.uniform(0, 2 * np.pi, n)[:, None]
    L = r.uniform(lmin, lmax, n)[:, None]
    curv = r.uniform(-0.55, 0.55, n)[:, None]
    dx, dy = np.cos(ang), np.sin(ang)
    px, py = -dy, dx
    X = x0 + L * (t * dx + 0.5 * curv * t * t * px)
    Y = y0 + L * (t * dy + 0.5 * curv * t * t * py)
    base = r.uniform(0.0, 0.45, n)[:, None]
    Hh = base + t * 0.55
    w = ancho * r.uniform(0.7, 1.3, n)[:, None] * (1.0 - 0.85 * t)
    tinte = r.random(n)[:, None]
    # color: base oscura -> punta clara; algunas hojas amarillentas/secas
    seca = (r.random(n) < 0.12)[:, None]
    verde_b = np.array([0.045, 0.075, 0.025])
    verde_p = np.array([0.15, 0.27, 0.06])
    verde_p2 = np.array([0.26, 0.38, 0.1])
    seco_p = np.array([0.36, 0.3, 0.12])
    tt = t[..., None]
    punta = np.where(seca[..., None], seco_p, verde_p + (verde_p2 - verde_p) * tinte[..., None])
    col_ = verde_b + (punta - verde_b) * np.clip(tt * 1.15, 0, 1)
    col_ = col_ * (0.8 + 0.4 * r.random((n, 1, 1)))
    col_ = np.broadcast_to(col_, (n, pasos, 3))
    Xs, Ys, Hs, Cs = [], [], [], []
    for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1)):
        m = np.ones((n, pasos), dtype=bool) if (ox, oy) in ((0, 0), (1, 0), (0, 1), (1, 1)) else (w > 1.6)
        Xs.append(np.round(X + ox)[m]); Ys.append(np.round(Y + oy)[m]); Hs.append(Hh[m])
        Cs.append(col_[m])
    return (np.concatenate(Ys).astype(np.int64), np.concatenate(Xs).astype(np.int64),
            np.concatenate(Hs), np.concatenate(Cs))


def piedrecitas(n, seed, rmin, rmax, paleta, H, C, z0=0.0, escala_h=1.0):
    """guijarros redondeados (elipses con perfil de cupula) pintados sobre H (altura) y C (color)"""
    r = np.random.default_rng(seed)
    for _ in range(n):
        cx, cy = r.random() * N, r.random() * N
        R = r.uniform(rmin, rmax)
        e = r.uniform(0.6, 1.0)
        a = r.uniform(0, np.pi)
        ext = int(R * 1.25) + 2
        ys = np.arange(int(cy) - ext, int(cy) + ext + 1)
        xs = np.arange(int(cx) - ext, int(cx) + ext + 1)
        Y, X = np.meshgrid(ys, xs, indexing="ij")
        dx, dy = X - cx, Y - cy
        u = (dx * np.cos(a) + dy * np.sin(a)) / R
        v = (-dx * np.sin(a) + dy * np.cos(a)) / (R * e)
        d2 = u * u + v * v
        dentro = d2 < 1.0
        if not dentro.any():
            continue
        alto = z0 + escala_h * (0.25 + 0.75 * R / rmax) * np.sqrt(np.clip(1 - d2, 0, 1)) ** 0.8 + r.uniform(0, 0.05)
        base_c = np.array(paleta(r))
        luz = 0.85 + 0.3 * (-(u + v) * 0.5 * (d2 < 1))                    # luz desde una esquina: da volumen al color
        c = base_c[None, None, :] * np.clip(luz, 0.6, 1.25)[..., None]
        iy, ix = Y % N, X % N
        mejor = dentro & (alto > H[iy, ix])
        H[iy[mejor], ix[mejor]] = alto[mejor]
        C[iy[mejor], ix[mejor]] = c[mejor]


def suavizar(a, k=1):
    for _ in range(k):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5.0
    return a


# ------------------------------------------------------------ HIERBA (hojas pintadas una a una)
H = np.zeros((N, N))
suelo_c = np.array([0.07, 0.05, 0.035])
C = np.ones((N, N, 3)) * suelo_c
C *= (0.8 + 0.4 * fbm(2.0, 99))[..., None]
Y, X, Hh, Cc = hojas(11000, 5, 18, 52, 2.6)
pintar(Y, X, H, C, Hh, Cc)
H = np.clip(H / max(H.max(), 1e-6), 0, 1)
C *= (0.85 + 0.3 * fbm(3.0, 132))[..., None]
guardar("T_Ter_Hierba.png", C, H, True)
guardar("T_Ter_Hierba_N.png", normal_de(suavizar(H, 1), 3.2), None, False)

# ------------------------------------------------------------ TIERRA DE CAMINO (pisada y humeda)
# Antes era un lecho de guijarros grises claros: de noche brillaba y no pegaba con la hierba. Ahora es tierra apisonada oscura
# (mas oscura y humeda en lo bajo), gravilla, alguna piedra medio enterrada y paja seca pisada. La altura (alfa) deja lo bajo
# para el agua de los charcos y lo alto (piedras, terrones) asomando.
terron = fbm(2.0, 140)                                         # lomas suaves de la tierra apisonada
grumo = fbm(1.0, 141)                                          # grumos
grano = fbm(0.3, 142)                                          # granulado fino
H = 0.30 + 0.17 * terron + 0.10 * grumo + 0.05 * grano
seca = np.clip(0.75 * smooth(terron, 0.25, 0.7) + 0.25 * smooth(grumo, 0.3, 0.8), 0, 1)     # lo alto esta mas seco y claro
C = mezcla(col(0.058, 0.042, 0.029), col(0.150, 0.108, 0.072), seca)
C = C * (0.86 + 0.28 * fbm(2.6, 144))[..., None] * (0.9 + 0.2 * grano)[..., None]


def pal_piedra(r):
    g = r.uniform(0.10, 0.24)                                  # piedras oscuras y calidas (mojadas), nunca gris claro
    c = r.choice(3)
    t = ((1.0, 0.9, 0.78), (0.96, 0.92, 0.84), (0.9, 0.88, 0.84))[c]
    return (g * t[0], g * t[1], g * t[2])


# z0 cerca del nivel de la tierra: de cada piedra solo asoma la parte de arriba (medio enterradas)
piedrecitas(950, 21, 2, 5, pal_piedra, H, C, z0=0.27, escala_h=0.22)     # gravilla
piedrecitas(150, 22, 6, 14, pal_piedra, H, C, z0=0.30, escala_h=0.32)    # guijarros
piedrecitas(14, 23, 16, 30, pal_piedra, H, C, z0=0.32, escala_h=0.42)    # alguna piedra grande
# paja y hebras secas pisadas, tumbadas sobre la tierra (enlaza con la hierba de los lados)
Yp, Xp, Hp, Cp = hojas(280, 77, 16, 44, 1.5)
lum = np.clip((Cp @ np.array([0.3, 0.59, 0.11])) / 0.12, 0.55, 1.4)
pintar(Yp, Xp, H, C, 0.50 + 0.12 * Hp, np.array([0.19, 0.15, 0.08])[None, :] * lum[:, None])
H = np.clip((H - H.min()) / (H.max() - H.min()), 0, 1)
cavidad = np.clip((suavizar(H, 6) - H) * 4.0, 0, 1)                      # huecos: mas oscuros
C = C * (1.0 - 0.45 * cavidad)[..., None] * (0.9 + 0.2 * fbm(0.6, 145))[..., None]
guardar("T_Ter_Tierra.png", C, H, True)
guardar("T_Ter_Tierra_N.png", normal_de(suavizar(H, 2), 2.2), None, False)

# ------------------------------------------------------------ ARENA / GRAVA DE ORILLA
grano = fbm(0.4, 150)
ond = 0.5 + 0.5 * np.sin(2 * np.pi * (5 * (np.arange(N)[:, None] / N) + 2.5 * fbm(2.4, 151, aniso=(0.5, 1.0))))
H = 0.35 * grano + 0.2 * ond + 0.15 * fbm(1.8, 152)
C = mezcla(col(0.36, 0.31, 0.22), col(0.64, 0.58, 0.46), smooth(grano, 0.3, 0.8)) * (0.85 + 0.3 * fbm(2.5, 153))[..., None]


def pal_arena(r):
    g = r.uniform(0.3, 0.6)
    return (g, g * 0.95, g * 0.85)


piedrecitas(700, 31, 2, 6, pal_arena, H, C, z0=0.35, escala_h=0.4)
piedrecitas(90, 32, 7, 16, pal_arena, H, C, z0=0.38, escala_h=0.5)
H = np.clip((H - H.min()) / (H.max() - H.min()), 0, 1)
cav = np.clip((suavizar(H, 5) - H) * 4.0, 0, 1)
C = C * (1.0 - 0.4 * cav)[..., None]
guardar("T_Ter_Arena.png", C, H, True)
guardar("T_Ter_Arena_N.png", normal_de(suavizar(H, 1), 3.0), None, False)
