# Textura de las matas de hierba (T_Pasto_Matas.png, 1024 px, RGBA con recorte por alfa).
# Atlas de 2 x 2 matas distintas, pintadas hoja a hoja (hojas finas de ~1 cm, curvadas, con nervio y puntas secas):
#   0 = mata media y densa      1 = mata alta y abierta
#   2 = cesped corto y tupido   3 = tallos secos con espiga y algo de verde en la base
# Las usa pasto_y_rocas.py (cada mata son 3 tarjetas cruzadas) y el shader Faro/Pasto.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/textura_pasto.py
import bpy, os, math
import numpy as np

RUT = os.path.dirname(bpy.data.filepath)
SALIDAS = [os.path.join(RUT, "texturas"), os.path.join(os.path.dirname(RUT), "Assets", "Textures")]
C = 512            # lado de cada mata en la textura final
SS = 2             # se pinta al doble y se reduce (bordes suaves)
W = C * SS
MARGEN = 12


def mezcla(a, b, t):
    return a + (b - a) * t


def sello(col, alfa, x, y, radio, nx, ny, color, lado):
    """disco de la hoja en (x, y); 'lado' oscurece un borde y aclara el nervio central -> la hoja parece doblada, no plana"""
    r = int(math.ceil(radio)) + 1
    x0, x1, y0, y1 = int(x) - r, int(x) + r + 1, int(y) - r, int(y) + r + 1
    if x0 < 0 or y0 < 0 or x1 > W or y1 > W:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dx, dy = xx - x, yy - y
    m = dx * dx + dy * dy <= radio * radio
    s = (dx * nx + dy * ny) / max(radio, 1.0)                    # -1..1 a lo ancho de la hoja
    luz = 1.0 + 0.22 * s * lado + 0.28 * np.exp(-(s / 0.2) ** 2)
    sub = col[y0:y1, x0:x1]
    sub[m] = np.clip(color[None, :] * luz[m][:, None], 0, 1)
    alfa[y0:y1, x0:x1][m] = 1.0


def hoja(r, col, alfa, x0, largo, ang, curva, ancho, c_base, c_punta, brillo, punta_seca):
    """devuelve False si la hoja se sale de la celda (se prueba otra)"""
    pasos = int(largo)
    x, y = x0, 0.0
    pts = []
    for k in range(pasos):
        t = k / pasos
        a = ang + curva * t * t
        x += math.sin(a); y += math.cos(a)
        if x < MARGEN or x > W - MARGEN or y > W - MARGEN:
            return False
        pts.append((x, y, t, a))
    lado = 1.0 if r.random() < 0.5 else -1.0
    for x, y, t, a in pts:
        hw = ancho * (0.7 + 0.3 * min(1.0, t / 0.12)) * max(0.0, 1.0 - t ** 2.4) ** 0.8
        hw = max(hw, 0.9)
        c = mezcla(c_base, c_punta, min(1.0, t * 1.1) ** 0.8)
        if punta_seca > 0 and t > 1.0 - punta_seca:
            c = mezcla(c, np.array([0.42, 0.34, 0.17]), (t - (1.0 - punta_seca)) / punta_seca)
        sello(col, alfa, x, y, hw, math.cos(a), -math.sin(a), c * brillo, lado)
    return True


def mata(tipo, semilla):
    r = np.random.default_rng(semilla)
    col = np.zeros((W, W, 3), dtype=np.float32)
    alfa = np.zeros((W, W), dtype=np.float32)
    base_v = np.array([0.03, 0.055, 0.02])
    lista = []
    n, lmin, lmax, disp, amin, amax = {0: (95, 0.4, 0.9, 0.17, 4.5, 8.0),
                                       1: (60, 0.55, 0.97, 0.15, 5.0, 9.0),
                                       2: (130, 0.22, 0.62, 0.2, 4.0, 7.0),
                                       3: (45, 0.2, 0.5, 0.17, 4.0, 7.0)}[tipo]
    for _ in range(n):
        lista.append(("verde", r.random(), r.uniform(lmin, lmax), disp, r.uniform(amin, amax)))
    if tipo == 3:
        for _ in range(26):
            lista.append(("tallo", r.random(), r.uniform(0.68, 0.96), 0.13, r.uniform(1.8, 2.8)))
    lista.sort(key=lambda h: h[1])                                # de atras hacia delante
    for clase, fondo, lrel, disp, ancho in lista:
        sombra = 0.5 + 0.5 * fondo                                # las hojas de atras, mas oscuras (dentro de la mata llega menos luz)
        for _ in range(25):
            x0 = W * 0.5 + r.normal(0, disp) * W
            if not (W * 0.12 < x0 < W * 0.88):
                continue
            fuera = (x0 - W * 0.5) / (W * 0.4)
            ang = fuera * 0.45 + r.normal(0, 0.2 if clase == "verde" else 0.09)
            curva = (np.sign(ang) if abs(ang) > 0.05 else r.choice([-1, 1])) * r.uniform(0.1, 1.0 if clase == "verde" else 0.3)
            largo = lrel * (W - MARGEN)
            if clase == "verde":
                seca = r.random() < 0.1
                tinte = r.random()
                punta = np.array([0.4, 0.36, 0.17]) if seca else mezcla(np.array([0.2, 0.36, 0.1]), np.array([0.33, 0.47, 0.15]), tinte)
                ok = hoja(r, col, alfa, x0, largo, ang, curva, ancho, base_v, punta, sombra * r.uniform(0.85, 1.15),
                          r.uniform(0.08, 0.2) if r.random() < 0.3 else 0.0)
            else:
                paja = mezcla(np.array([0.36, 0.3, 0.16]), np.array([0.5, 0.44, 0.25]), r.random())
                ok = hoja(r, col, alfa, x0, largo, ang, curva, ancho, paja * 0.55, paja, sombra * r.uniform(0.9, 1.15), 0.0)
                if ok:
                    # espiga: granos alternos a los lados del ultimo tramo del tallo
                    x, y, a = x0, 0.0, ang
                    pasos = int(largo)
                    for k in range(pasos):
                        t = k / pasos
                        a = ang + curva * t * t
                        x += math.sin(a); y += math.cos(a)
                        if t > 0.84 and k % 9 == 0:
                            s = 1 if (k // 9) % 2 == 0 else -1
                            gx, gy = x + s * math.cos(a) * 4.0, y - s * math.sin(a) * 4.0
                            for q in range(5):
                                sello(col, alfa, gx + math.sin(a) * q * 1.6, gy + math.cos(a) * q * 1.6, 3.4 - abs(q - 2) * 0.7,
                                      math.cos(a), -math.sin(a), paja * sombra * r.uniform(0.9, 1.2), float(s))
            if ok:
                break
    # reducir a la mitad (promedio ponderado por alfa)
    a4 = alfa.reshape(C, SS, C, SS)
    c4 = (col * alfa[..., None]).reshape(C, SS, C, SS, 3)
    a = a4.mean(axis=(1, 3))
    c = c4.sum(axis=(1, 3)) / np.maximum(a4.sum(axis=(1, 3)), 1e-6)[..., None]
    return c, a


atlas_c = np.zeros((2 * C, 2 * C, 3), dtype=np.float32)
atlas_a = np.zeros((2 * C, 2 * C), dtype=np.float32)
for k in range(4):
    c, a = mata(k, 40 + k)
    cx, cy = k % 2, k // 2
    atlas_c[cy * C:(cy + 1) * C, cx * C:(cx + 1) * C] = c
    atlas_a[cy * C:(cy + 1) * C, cx * C:(cx + 1) * C] = a
    print("PASTO mata %d: cubre %.0f %%" % (k, 100 * (a > 0.4).mean()))

# el color se extiende hacia lo transparente (sin esto, de lejos las hojas saldrian con un borde negro)
lleno = atlas_a > 0.01
c = atlas_c.copy()
for _ in range(24):
    s = np.zeros_like(c); w = np.zeros(lleno.shape, dtype=np.float32)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        s += np.roll(c * lleno[..., None], (dy, dx), (0, 1)); w += np.roll(lleno, (dy, dx), (0, 1))
    nuevo = (~lleno) & (w > 0)
    c[nuevo] = s[nuevo] / w[nuevo][:, None]
    lleno = lleno | nuevo
c[~lleno] = c[lleno].mean(axis=0)

for carpeta in SALIDAS:
    os.makedirs(carpeta, exist_ok=True)
    im = bpy.data.images.new("T_Pasto_Matas.png", 2 * C, 2 * C, alpha=True)
    im.colorspace_settings.name = 'sRGB'
    im.alpha_mode = 'CHANNEL_PACKED'
    px = np.ones((2 * C, 2 * C, 4), dtype=np.float32)
    px[..., :3] = np.clip(c, 0, 1)
    px[..., 3] = np.clip(atlas_a, 0, 1)
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = os.path.join(carpeta, "T_Pasto_Matas.png")
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)
print("PASTO textura guardada: T_Pasto_Matas.png")
