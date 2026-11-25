# Pinta la textura de la lubina rayada (la original de Alejandro apuntaba a su carpeta de Descargas y no esta en el repo):
# lomo gris pizarra, flancos plateados palidos con rayas oscuras a lo largo, panza blanca hueso, tono apagado para la noche.
# Se pinta sobre las UV de la malla: cada texel sabe en que punto 3D del pez cae (cabeza en -Y, lomo en +Z), igual que pintar_tiburon.py.
# Lo usa exportar_peces.py -> Assets/Models/Faro/Peces/Tex/Lubina_c.png
import bpy
import numpy as np

LOMO = np.array([0.075, 0.095, 0.100], dtype=np.float32)
FLANCO = np.array([0.50, 0.54, 0.55], dtype=np.float32)
PANZA = np.array([0.80, 0.80, 0.74], dtype=np.float32)
RAYA = np.array([0.035, 0.042, 0.050], dtype=np.float32)


def _suave(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ruido(p, semilla):
    rng = np.random.default_rng(semilla)
    s = np.zeros(len(p), dtype=np.float32)
    amp, tot = 1.0, 0.0
    for o in range(4):
        d = rng.normal(size=(3, 3)).astype(np.float32) * (2.0 ** o) * 18.0
        f = rng.uniform(0, 6.28, 3).astype(np.float32)
        q = p @ d.T + f
        s += amp * (np.sin(q[:, 0]) * np.sin(q[:, 1] + 1.3 * np.sin(q[:, 2])))
        tot += amp
        amp *= 0.5
    return 0.5 + 0.5 * s / tot


def pintar(me, ruta, tam=1024, semilla=11):
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
        e = -0.6 / max(1.0, np.sqrt(abs(den)))
        m = (w0 >= e) & (w1 >= e) & (w2 >= e)
        if not m.any():
            continue
        p = w0[..., None] * pa + w1[..., None] * pb + w2[..., None] * pc
        sub = pos[y0:y1 + 1, x0:x1 + 1]
        sub[m] = p[m]
        lleno[y0:y1 + 1, x0:x1 + 1] |= m

    P = pos[lleno]
    yh, yt = co[:, 1].min(), co[:, 1].max()
    t = (P[:, 1] - yh) / (yt - yh)                  # 0 morro .. 1 cola
    tv = (co[:, 1] - yh) / (yt - yh)
    # perfil vertical del cuerpo (percentiles: las aletas no cuentan), suavizado a lo largo del cuerpo e interpolado sin escalones
    N = 64
    zb, zt = np.zeros(N), np.zeros(N)
    for i in range(N):
        m = (tv >= i / N - 0.03) & (tv <= (i + 1) / N + 0.03)
        zs = co[m, 2] if m.sum() > 8 else co[:, 2]
        zb[i], zt[i] = np.percentile(zs, 8), np.percentile(zs, 92)
    ker = np.ones(5) / 5.0
    zb = np.convolve(np.pad(zb, 2, mode='edge'), ker, mode='valid')
    zt = np.convolve(np.pad(zt, 2, mode='edge'), ker, mode='valid')
    centros = (np.arange(N) + 0.5) / N
    zbp, ztp = np.interp(t, centros, zb), np.interp(t, centros, zt)
    h = np.maximum(ztp - zbp, 1e-4)
    v = np.clip((P[:, 2] - zbp) / h, -0.3, 1.3)       # 0 panza .. 1 lomo
    ru = _ruido(P, semilla)
    ru2 = _ruido(P * 2.3, semilla + 5)

    col = np.tile(FLANCO, (len(P), 1))
    # panza hueso, lomo pizarra
    col += (PANZA - col) * _suave(0.34, 0.12, v)[:, None]
    col += (LOMO - col) * _suave(0.62, 0.86, v + 0.05 * (ru - 0.5))[:, None]
    # rayas oscuras a lo largo del flanco (7 lineas que se parten con el ruido), desde detras de la agalla
    raya = np.zeros(len(P), dtype=np.float32)
    for i in range(7):
        vc = 0.28 + 0.065 * i
        d = np.abs(v - vc - 0.012 * np.sin(t * 22 + i))
        r = 1.0 - _suave(0.007, 0.020, d)
        corte = _suave(0.35, 0.55, ru2 + 0.1 * np.sin(t * 40 + i * 2.0))
        raya = np.maximum(raya, r * corte)
    raya *= _suave(0.17, 0.26, t) * (1.0 - _suave(0.93, 0.99, t))
    col += (RAYA - col) * (raya * 0.92)[:, None]
    # agalla (arco palido) y morro mas oscuro
    ag = np.exp(-((t - 0.20) / 0.012) ** 2)
    col += (PANZA * 0.8 - col) * (ag * _suave(0.1, 0.5, v) * 0.5)[:, None]
    col += (RAYA - col) * (_suave(0.07, 0.0, t) * 0.5)[:, None]
    # moteado y grano
    col *= (0.82 + 0.36 * ru)[:, None]

    img = np.zeros((tam, tam, 3), dtype=np.float32)
    img[lleno] = np.clip(col, 0.0, 1.0)
    hecho = lleno.copy()
    for _ in range(16):
        if hecho.all():
            break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(hecho, (dy, dx), axis=(0, 1))
            nuevo = src & ~hecho
            if nuevo.any():
                img[nuevo] = np.roll(img, (dy, dx), axis=(0, 1))[nuevo]
                hecho |= nuevo
    img[~hecho] = LOMO
    salida = bpy.data.images.new("Lubina_pintada", tam, tam, alpha=False)
    rgba = np.concatenate([img, np.ones((tam, tam, 1), dtype=np.float32)], axis=2)
    salida.pixels.foreach_set(rgba.ravel())
    salida.filepath_raw = ruta
    salida.file_format = 'PNG'
    salida.save()
    print("LUBINA pintada %d px, %.0f %% de la textura usada" % (tam, 100.0 * lleno.mean()), flush=True)
    return salida
