# Piezas comunes para pintar texturas sobre las UV de una malla (la usa pintar_calamar.py): cada texel sabe en que punto 3D del animal cae,
# asi el dibujo se define en el espacio del animal y no hace falta desplegar nada a mano.
import bpy
import numpy as np


def suave(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ruido(p, semilla, frecuencia=1.0):
    """ruido barato y continuo (suma de senos girados), 0..1"""
    rng = np.random.default_rng(semilla)
    s = np.zeros(len(p), dtype=np.float32)
    amp, tot = 1.0, 0.0
    for o in range(4):
        d = rng.normal(size=(3, 3)).astype(np.float32) * (2.0 ** o) * frecuencia
        f = rng.uniform(0, 6.28, 3).astype(np.float32)
        q = p @ d.T + f
        s += amp * (np.sin(q[:, 0]) * np.sin(q[:, 1] + 1.3 * np.sin(q[:, 2])))
        tot += amp
        amp *= 0.5
    return 0.5 + 0.5 * s / tot


def rasterizar(me, tam):
    """devuelve (pos, lleno, co): pos[y, x] = punto 3D del texel, lleno = texels cubiertos por alguna cara, co = vertices"""
    me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices], dtype=np.float32)
    uvs = np.array([d.uv[:] for d in me.uv_layers.active.data], dtype=np.float32)
    pos = np.zeros((tam, tam, 3), dtype=np.float32)
    lleno = np.zeros((tam, tam), dtype=bool)
    for t in me.loop_triangles:
        a, b, c = (uvs[i] * tam for i in t.loops)
        pa, pb, pc = (co[i] for i in t.vertices)
        x0, x1 = int(max(0, np.floor(min(a[0], b[0], c[0])) - 1)), int(min(tam - 1, np.ceil(max(a[0], b[0], c[0])) + 1))
        y0, y1 = int(max(0, np.floor(min(a[1], b[1], c[1])) - 1)), int(min(tam - 1, np.ceil(max(a[1], b[1], c[1])) + 1))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
        w2 = 1.0 - w0 - w1
        e = -0.6 / max(1.0, np.sqrt(abs(den)))          # un pelin de margen para no dejar costuras
        m = (w0 >= e) & (w1 >= e) & (w2 >= e)
        if not m.any():
            continue
        p = w0[..., None] * pa + w1[..., None] * pb + w2[..., None] * pc
        sub = pos[y0:y1 + 1, x0:x1 + 1]
        sub[m] = p[m]
        lleno[y0:y1 + 1, x0:x1 + 1] |= m
    return pos, lleno, co


def guardar(col, lleno, tam, ruta, nombre, fondo):
    """col = color de cada texel cubierto (n, 3); extiende los bordes de cada isla de UV (sin costuras con los mipmaps) y guarda el PNG"""
    img = np.zeros((tam, tam, 3), dtype=np.float32)
    img[lleno] = np.clip(col, 0.0, 1.0)
    hecho = lleno.copy()
    for _ in range(20):
        if hecho.all():
            break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(hecho, (dy, dx), axis=(0, 1))
            nuevo = src & ~hecho
            if nuevo.any():
                img[nuevo] = np.roll(img, (dy, dx), axis=(0, 1))[nuevo]
                hecho |= nuevo
    img[~hecho] = fondo
    salida = bpy.data.images.new(nombre, tam, tam, alpha=False)
    salida.pixels.foreach_set(np.concatenate([img, np.ones((tam, tam, 1), dtype=np.float32)], axis=2).ravel())
    salida.filepath_raw = ruta
    salida.file_format = 'PNG'
    salida.save()
    return salida
