# Aplana el terreno de la isla dentro de la torre (el cesped asomaba 1-2 m sobre el suelo interior, PISO=7.37)
# y lo suaviza hacia afuera. Solo BAJA vertices. Se aplica una sola vez.
import bpy, math
from mathutils import Vector

S = bpy.context.scene
if S.get("terreno_torre") == 2:
    raise SystemExit("ya aplicado")
TC = Vector((-6.64, 89.52))
Z_PISO = 7.25
R0, R1 = 10.5, 14.5
cambiados = 0
for nombre in ("IslandModel", "IslandModel.001"):
    o = bpy.data.objects.get(nombre)
    if not o:
        continue
    mw = o.matrix_world
    inv = mw.inverted()
    for v in o.data.vertices:
        w = mw @ v.co
        d = (Vector((w.x, w.y)) - TC).length
        if d >= R1 or w.z <= Z_PISO:
            continue
        if d <= R0:
            nz = Z_PISO
        else:
            t = (d - R0) / (R1 - R0)
            t = t * t * (3 - 2 * t)
            nz = min(w.z, Z_PISO + (w.z - Z_PISO) * t)
        if nz < w.z - 1e-4:
            w.z = nz
            v.co = inv @ w
            cambiados += 1
    o.data.update()
S["terreno_torre"] = 2
bpy.ops.wm.save_mainfile()
print("TERRENO OK vertices bajados", cambiados)
