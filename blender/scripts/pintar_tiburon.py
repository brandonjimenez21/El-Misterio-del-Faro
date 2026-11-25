# Pinta la textura del tiburon con la estetica de aspecto_estetica_terror.jpg: cabeza de hueso palido que sale de un cuerpo
# negro, ojo negro hueco, fila de dientes en sierra y aranazos de trazo suelto. Se pinta sobre las UV que ya tiene la malla:
# cada texel sabe en que punto 3D del tiburon cae, asi que el dibujo se define en el espacio del animal (cabeza en -Y, lomo en +Z).
# Lo usa exportar_peces.py -> Assets/Models/Faro/Peces/Tex/Tiburon_c.png
import bpy
import numpy as np

HUESO = np.array([0.80, 0.79, 0.74], dtype=np.float32)
NEGRO = np.array([0.030, 0.034, 0.045], dtype=np.float32)
TRAZO_CLARO = np.array([0.36, 0.37, 0.40], dtype=np.float32)


def _suave(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _ruido(p, semilla):
    """ruido barato y continuo (suma de senos girados), 0..1"""
    rng = np.random.default_rng(semilla)
    s = np.zeros(len(p), dtype=np.float32)
    amp, tot = 1.0, 0.0
    for o in range(4):
        d = rng.normal(size=(3, 3)).astype(np.float32) * (2.0 ** o)
        f = rng.uniform(0, 6.28, 3).astype(np.float32)
        q = p @ d.T + f
        s += amp * (np.sin(q[:, 0]) * np.sin(q[:, 1] + 1.3 * np.sin(q[:, 2])))
        tot += amp
        amp *= 0.5
    return 0.5 + 0.5 * s / tot


def pintar(me, ruta, tam=2048, semilla=7):
    rng = np.random.default_rng(semilla)
    me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices], dtype=np.float32)
    uvs = np.array([d.uv[:] for d in me.uv_layers.active.data], dtype=np.float32)

    # ---- 1. posicion 3D de cada texel (rasterizado de los triangulos en UV)
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

    P = pos[lleno]                                       # (n, 3)
    # ---- 2. medidas del animal: t = 0 en el morro .. 1 en la cola; perfil (panza/lomo) a lo largo del cuerpo
    yh, yt = co[:, 1].min(), co[:, 1].max()
    L = yt - yh
    t = (P[:, 1] - yh) / L
    tv = (co[:, 1] - yh) / L
    # perfil del CUERPO (sin aletas): de cada tramo, percentiles en vez de extremos
    N = 40
    zb, zt_ = np.zeros(N), np.zeros(N)
    for i in range(N):
        m = (tv >= i / N - 0.02) & (tv <= (i + 1) / N + 0.02)
        z = co[m, 2] if m.any() else np.array([0.0])
        zb[i], zt_[i] = np.percentile(z, 8), np.percentile(z, 85)
    centros = (np.arange(N) + 0.5) / N
    panza = np.interp(t, centros, zb)
    lomo = np.interp(t, centros, zt_)
    alto = np.maximum(lomo - panza, 1e-4)
    zn = (P[:, 2] - panza) / alto                        # 0 = panza, 1 = lomo (las aletas se salen de 0..1)
    Pn = P / L

    # ---- 3. cabeza de hueso que se funde en un cuerpo negro, con borde roto
    borde = 0.34 + 0.16 * (_ruido(Pn * 9.0, 1) - 0.5) + 0.05 * np.sin(zn * 5.0 + P[:, 0] / L * 30.0)
    hueso = 1.0 - _suave(borde - 0.07, borde + 0.07, t)
    # el hueso sigue un poco por el lomo y la aleta dorsal, como en el dibujo (la forma palida sube hacia arriba)
    hueso = np.maximum(hueso, 0.75 * _suave(0.9, 1.25, zn) * (1.0 - _suave(0.50, 0.70, t)))
    mugre = 0.72 + 0.28 * _ruido(Pn * 14.0, 2)
    col = NEGRO[None, :] + (HUESO[None, :] * mugre[:, None] - NEGRO[None, :]) * hueso[:, None]
    # manchas palidas sueltas por el cuerpo negro (trazo seco)
    mancha = _suave(0.80, 0.92, _ruido(Pn * np.array([40.0, 6.0, 40.0], dtype=np.float32), 3)) * (1.0 - hueso) * 0.35
    col += (TRAZO_CLARO[None, :] - col) * mancha[:, None]

    # ---- 4. aranazos: segmentos al azar sobre la piel, sobre todo a lo largo del cuerpo
    # se trazan en coordenadas "desenrolladas" (largo del cuerpo, vuelta alrededor del cuerpo) para que sigan la piel curva
    # y salgan como trazos largos y no como puntos
    zc = 0.5 * (panza + lomo)
    vuelta = np.arctan2(P[:, 0], P[:, 2] - zc) * (0.055 * L)
    P2 = np.stack([P[:, 1], vuelta, np.zeros(len(P), dtype=np.float32)], axis=1).astype(np.float32)
    n_seg = 110
    idx = rng.integers(0, len(P2), n_seg)
    A = P2[idx]
    d = rng.normal(size=(n_seg, 3)).astype(np.float32) * np.array([1.0, 0.42, 0.0], dtype=np.float32)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    largo_s = (rng.uniform(0.04, 0.20, n_seg) * L).astype(np.float32)
    B = A + d * largo_s[:, None]
    grosor = (rng.uniform(0.0005, 0.0013, n_seg) * L).astype(np.float32)
    raya = np.zeros(len(P), dtype=np.float32)
    TROZO = 200000
    for i0 in range(0, len(P), TROZO):
        Q = P2[i0:i0 + TROZO]
        r = np.zeros(len(Q), dtype=np.float32)
        for k in range(n_seg):
            ab = B[k] - A[k]
            u = np.clip(((Q - A[k]) @ ab) / (ab @ ab), 0.0, 1.0)
            dist = np.linalg.norm(Q - (A[k] + u[:, None] * ab), axis=1)
            # mas fino en las puntas, como un trazo de lapiz
            g = grosor[k] * (0.35 + 0.65 * np.sin(u * np.pi))
            r = np.maximum(r, 1.0 - _suave(g * 0.6, g, dist))
        raya[i0:i0 + TROZO] = r
    # sobre el hueso el aranazo es negro; sobre el negro, gris claro
    col_raya = NEGRO[None, :] * 1.5 + (TRAZO_CLARO[None, :] - NEGRO[None, :] * 1.5) * (1.0 - hueso)[:, None]
    col += (col_raya - col) * (raya * (0.45 + 0.45 * hueso))[:, None]

    # ---- 5. boca: linea negra con dientes en sierra, a los lados del morro
    t_boca0, t_boca1 = 0.012, 0.150
    z_boca = 0.30 - 0.10 * _suave(t_boca0, t_boca1, t)                    # la comisura cae un poco hacia atras
    en_boca = _suave(t_boca0 - 0.006, t_boca0 + 0.004, t) * (1.0 - _suave(t_boca1 - 0.004, t_boca1 + 0.006, t))
    paso = 0.0105                                                          # un diente cada ~1 % del largo
    sierra = np.abs(((t / paso) % 1.0) - 0.5) * 2.0                         # 0 en la punta del diente, 1 entre dientes
    alto_d = 0.20 * (0.65 + 0.35 * np.sin(t * 190.0))                      # dientes desiguales
    bajo_linea = z_boca - zn
    encia = (1.0 - _suave(0.030, 0.050, np.abs(zn - z_boca - 0.03))) * en_boca              # linea negra de la boca
    hueco = _suave(-0.01, 0.01, bajo_linea) * (1.0 - _suave(alto_d * 1.15, alto_d * 1.3, bajo_linea)) * en_boca
    diente = hueco * _suave(0.0, 0.10, (1.0 - sierra) - bajo_linea / np.maximum(alto_d, 1e-4))
    col += (NEGRO[None, :] * 0.5 - col) * np.clip(encia + hueco * 0.92, 0.0, 1.0)[:, None]  # fondo negro de la boca
    col += (np.array([0.93, 0.92, 0.86], dtype=np.float32)[None, :] - col) * diente[:, None]

    # ---- 6. ojo negro hueco con un punto de brillo, a cada lado
    t_ojo, z_ojo, r_ojo = 0.105, 0.70, 0.024 * L
    cy = yh + t_ojo * L
    cz = np.interp(t_ojo, centros, zb) + z_ojo * (np.interp(t_ojo, centros, zt_) - np.interp(t_ojo, centros, zb))
    d_ojo = np.sqrt((P[:, 1] - cy) ** 2 + (P[:, 2] - cz) ** 2)
    ojo = 1.0 - _suave(r_ojo * 0.86, r_ojo, d_ojo)
    cerco = (1.0 - _suave(r_ojo, r_ojo * 1.9, d_ojo)) * 0.55               # sombra alrededor de la cuenca
    col *= (1.0 - cerco)[:, None]
    col += (NEGRO[None, :] * 0.3 - col) * ojo[:, None]
    d_brillo = np.sqrt((P[:, 1] - (cy - r_ojo * 0.18)) ** 2 + (P[:, 2] - (cz + r_ojo * 0.10)) ** 2)
    brillo = 1.0 - _suave(r_ojo * 0.10, r_ojo * 0.17, d_brillo)
    col += (np.array([0.55, 0.56, 0.60], dtype=np.float32)[None, :] - col) * brillo[:, None]

    # ---- 7. volcar a imagen, extender los bordes de cada isla de UV (sin costuras con los mipmaps) y guardar
    img = np.zeros((tam, tam, 3), dtype=np.float32)
    img[lleno] = np.clip(col, 0.0, 1.0)
    hecho = lleno.copy()
    for _ in range(24):
        if hecho.all():
            break
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(hecho, (dy, dx), axis=(0, 1))
            nuevo = src & ~hecho
            if nuevo.any():
                img[nuevo] = np.roll(img, (dy, dx), axis=(0, 1))[nuevo]
                hecho |= nuevo
    img[~hecho] = NEGRO
    salida = bpy.data.images.new("Tiburon_pintado", tam, tam, alpha=False)
    rgba = np.concatenate([img, np.ones((tam, tam, 1), dtype=np.float32)], axis=2)
    salida.pixels.foreach_set(rgba.ravel())
    salida.filepath_raw = ruta
    salida.file_format = 'PNG'
    salida.save()
    print("TIBURON pintado %d px, %.0f %% de la textura usada, hueso en %.0f %% de la piel" % (tam, 100.0 * lleno.mean(), 100.0 * float((hueso > 0.5).mean())), flush=True)
    return salida
