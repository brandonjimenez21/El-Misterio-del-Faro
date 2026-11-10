# Mete los objetos del puzle 3 (caldera, nota, mesa de trabajo, cerillas, taza, lata de aceite, cuadro y reloj)
# DENTRO de la cabana del faro, segun el plano del texto:
#   - zona del generador junto a la torre (pared oeste), con la nota/pizarra encima de la caldera
#   - mesa de trabajo con cerillas y taza y la lata de aceite en la zona de cocina/almacen (pared sur y esquina)
#   - cuadro torcido y reloj de pared en la pared norte
# No toca la isla ni los objetos del exterior. Se puede repetir.
import bpy, math
from mathutils import Vector, Matrix

S = bpy.context.scene
I = bpy.data.objects["IslandModel"]
CC = Vector((1.4, 83.7))                       # centro de la cabana (xy)
U = Vector((0.8, 0.6))                         # eje largo (hacia la torre es -U)
W = Vector((0.6, -0.8))                        # eje perpendicular
GIRO = math.degrees(math.atan2(U.y, U.x))      # 36.87 grados: giro de la cabana
MITAD = 3.45                                   # medio lado interior (m)

bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()


def suelo(x, y):
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    return (I.matrix_world @ l).z if h else None


def P(a, b):
    v = CC + U * a + W * b
    return v.x, v.y


# suelo de la cabana: mediana de la isla bajo la planta
mu = sorted(g for g in (suelo(*P(a, b)) for a in (-3, 0, 3) for b in (-3, 0, 3)) if g is not None)
PISO = round(mu[len(mu) // 2], 2)
print("PISO", PISO)

# alturas actuales sobre el suelo, ANTES de aplanar la isla
alturas = {}
for n in ("Caldera_Conjunto", "Nota_Instrucciones_Vapor", "Mesa_Trabajo", "Lata_Aceite", "Cuadro_Torcido", "Reloj_Pared",
          "Caja_Cerillas", "Taza_Derramada", "Reloj_Manecilla_Hora", "Reloj_Manecilla_Minutero"):
    o = bpy.data.objects[n]
    g = suelo(o.location.x, o.location.y)
    alturas[n] = o.location.z - (g if g is not None else 0.0)

# ---- aplanar el terreno bajo la cabana (la isla tiene un monticulo ahi) con transicion suave
MARGEN = 2.5
mw = I.matrix_world
mi = mw.inverted()
cambios = 0
for v in I.data.vertices:
    p = mw @ v.co
    rel = Vector((p.x, p.y)) - CC
    a_, b_ = rel.dot(U), rel.dot(W)
    d = max(abs(a_), abs(b_)) - (MITAD + 0.35)
    if d < MARGEN:
        w_ = 1.0 if d <= 0 else (1 - d / MARGEN)
        w_ = w_ * w_ * (3 - 2 * w_)
        nz = p.z + (PISO - p.z) * w_
        if abs(nz - p.z) > 1e-4:
            v.co = mi @ Vector((p.x, p.y, nz))
            cambios += 1
I.data.update()
bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
print("APLANADOS", cambios, "vertices")

# (objeto, a, b, yaw, seguidores): a = a lo largo de la cabana (+ hacia la puerta, - hacia la torre), b = lado (+ pared sur)
yaw_mira = lambda ang: ang + 90.0              # yaw que hace que el objeto mire hacia el angulo dado
ANG_W = math.degrees(math.atan2(W.y, W.x))     # mira hacia la pared sur
PLAN = [
    ("Caldera_Conjunto",         0.20,  2.35, yaw_mira(ANG_W + 180), ()),                 # pared sur, mira al interior
    ("Nota_Instrucciones_Vapor", 3.62,  2.60, yaw_mira(GIRO + 180),  ()),                 # pared de la puerta, junto a la caldera
    ("Mesa_Trabajo",            -0.80, -2.85, yaw_mira(ANG_W),       ("Caja_Cerillas", "Taza_Derramada")),
    ("Lata_Aceite",              3.00, -3.00, yaw_mira(GIRO) + 30.0, ()),                 # esquina del almacen
    ("Cuadro_Torcido",           2.30, -3.62, yaw_mira(ANG_W),       ()),                 # pared norte
    ("Reloj_Pared",             -0.80, -3.62, yaw_mira(ANG_W),       ("Reloj_Manecilla_Hora", "Reloj_Manecilla_Minutero")),
]
for nombre, a, b, yaw, seg in PLAN:
    o = bpy.data.objects[nombre]
    x0, y0 = o.location.x, o.location.y
    dd = math.radians(yaw) - o.rotation_euler.z
    foll = [(bpy.data.objects[fn], Vector((bpy.data.objects[fn].location.x - x0, bpy.data.objects[fn].location.y - y0)), alturas[fn]) for fn in seg]
    nx, ny = P(a, b)
    o.rotation_euler.z = math.radians(yaw)
    o.location = (nx, ny, PISO + alturas[nombre])
    R = Matrix.Rotation(dd, 2)
    for f, rel, alt in foll:
        r = R @ rel
        f.location = (nx + r.x, ny + r.y, PISO + alt)
        f.rotation_euler.z += dd
    print("INTERIOR", nombre, (round(nx, 1), round(ny, 1)), "yaw", round(yaw))

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("INTERIOR OK")
