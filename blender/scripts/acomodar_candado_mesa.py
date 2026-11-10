# Candado en la puerta de la cabana y mesa de navegacion (con mapa y bitacora) DENTRO de la cabana.
import bpy, math
from mathutils import Vector, Matrix
I = bpy.data.objects["IslandModel"]
CC = Vector((1.4, 83.7)); U = Vector((0.8, 0.6)); W = Vector((0.6, -0.8))
GIRO = math.degrees(math.atan2(U.y, U.x))
bpy.context.view_layer.update()
inv = I.matrix_world.inverted(); dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
def suelo(x, y):
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    return (I.matrix_world @ l).z if h else None
def P(a, b):
    v = CC + U * a + W * b; return v.x, v.y
PISO = 5.52
mesa = bpy.data.objects["Mesa_Navegacion"]
segs = [bpy.data.objects[n] for n in ("Mapa_Costa", "Bitacora_Farero")]
g0 = suelo(mesa.location.x, mesa.location.y) or 0
alt = {o.name: o.location.z - g0 for o in [mesa] + segs}
yaw = GIRO + 180 + 90
nx, ny = P(-0.6, -0.2)
dd = math.radians(yaw) - mesa.rotation_euler.z
rels = [(f, Vector((f.location.x - mesa.location.x, f.location.y - mesa.location.y))) for f in segs]
mesa.rotation_euler.z = math.radians(yaw); mesa.location = (nx, ny, PISO + alt[mesa.name])
R = Matrix.Rotation(dd, 2)
for f, rel in rels:
    r = R @ rel
    f.location = (nx + r.x, ny + r.y, PISO + alt[f.name]); f.rotation_euler.z += dd
# candado en la puerta (pared NE, a=+3.8, b=-1.0), mirando hacia afuera
c = bpy.data.objects["Candado_Cuerpo"]
cx, cy = P(4.0, -0.6)
c.location = (cx, cy, PISO + 1.2)
c.rotation_euler.z = math.radians(GIRO + 90)
print("MESA", round(nx,1), round(ny,1), "CANDADO", round(cx,1), round(cy,1))
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("CANDADO OK")
