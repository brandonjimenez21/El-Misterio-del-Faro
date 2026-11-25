# Texturas para la lluvia en Unity (se generan aqui para mantener el flujo Blender -> Unity):
#   T_Salpicadura.png : hoja de 4 fotogramas (corona de una gota al chocar), 512x128, RGBA (blanco con alfa)
# Uso: blender -b el_misterio_del_faro.blend --python scripts/texturas_lluvia.py   (no guarda el .blend)
import bpy, os, math
import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Textures", "Lluvia")
os.makedirs(OUT, exist_ok=True)


def guardar(nombre, arr):
    h, w, _ = arr.shape
    img = bpy.data.images.new(nombre, w, h, alpha=True)
    img.pixels.foreach_set(arr[::-1].astype(np.float32).ravel())
    img.filepath_raw = os.path.join(OUT, nombre + ".png")
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    print("TEXTURA", nombre)


def corona():
    F, S = 4, 128
    arr = np.zeros((S, S * F, 4), np.float32)
    arr[..., :3] = 1.0
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    gotas = [(rng.uniform(-1.2, 1.2), rng.uniform(0.6, 1.0), rng.uniform(0.6, 1.0)) for _ in range(9)]
    for f in range(F):
        t = (f + 0.5) / F                         # 0..1 a lo largo de la vida de la salpicadura
        a = np.zeros((S, S), np.float32)
        base_y = S * 0.86
        # corona: arco bajo que se abre y se cae
        ancho = S * (0.12 + 0.30 * t)
        alto = S * (0.30 * math.sin(math.pi * min(1.0, t * 1.3)))
        dx = (xx - S / 2) / max(ancho, 1)
        perfil = base_y - alto * np.clip(1 - dx * dx, 0, 1) ** 0.5
        pared = np.exp(-((yy - perfil) / (2.0 + 2.0 * t)) ** 2) * (np.abs(dx) < 1.05)
        pared *= np.clip((base_y + 2 - yy) / 6.0, 0, 1)
        a = np.maximum(a, pared * (1.0 - t * 0.6))
        # gotitas que salen disparadas
        for (ang, vel, tam) in gotas:
            px = S / 2 + ang * S * 0.32 * t * vel
            py = base_y - S * 0.62 * vel * t + S * 0.55 * t * t
            r = (1.6 + 1.6 * tam) * (1.0 - 0.5 * t)
            a = np.maximum(a, np.clip(r - np.sqrt((xx - px) ** 2 + (yy - py) ** 2) + 0.5, 0, 1) * (1.0 - t * 0.7))
        arr[:, f * S:(f + 1) * S, 3] = np.clip(a, 0, 1)
    guardar("T_Salpicadura", arr)


corona()
# (los anillos de las gotas en charcos y en el mar se dibujan en los shaders, no necesitan textura)
