# Ajusta lo traido de Lighthouse.blend a NUESTRA cabana:
#  - pisos/paredes interiores (Faro_Plane*) bajados para que el piso quede a la altura del piso de la cabana (PISO)
#  - puerta (PuertaVar2_*) colocada en la entrada de la cabana (pared NE) mirando hacia afuera
#  - candado sobre la puerta
import bpy, math
from mathutils import Vector, Matrix
bpy.context.view_layer.update()
CC = Vector((1.4, 83.7)); U = Vector((0.8, 0.6)); W = Vector((0.6, -0.8))
PISO = 5.52
def P(a, b):
    v = CC + U * a + W * b; return v
# --- pisos y paredes
planes = [bpy.data.objects[n] for n in ("Faro_Plane", "Faro_Plane.001", "Faro_Plane.002", "Faro_Plane.003", "Faro_Plane.004", "Faro_Plane.005")]
if not planes[0].get("ajustado"):
    zf = min((planes[0].matrix_world @ v.co).z for v in planes[0].data.vertices)
    dz = (PISO + 0.02) - zf
    for o in planes:
        mw = o.matrix_world.copy(); mw.translation.z += dz; o.matrix_world = mw; o["ajustado"] = True
    print("PLANOS dz", round(dz, 3))
# --- puerta
puerta = [bpy.data.objects[n] for n in ("PuertaVar2_Cuerpo", "PuertaVar2_Marco", "PuertaVar2_Tablas", "PuertaVar2_Clavos", "PuertaVar2_Herraje")]
if not puerta[0].get("ajustado"):
    pts = [o.matrix_world @ v.co for o in puerta for v in o.data.vertices]
    cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2; cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2
    zmin = min(p.z for p in pts)
    tx, ty = P(3.95, -1.0)
    ang = math.radians(-53.13)
    M = Matrix.Translation((tx, ty, PISO + 0.03 - zmin)) @ Matrix.Rotation(ang, 4, 'Z') @ Matrix.Translation((-cx, -cy, 0))
    for o in puerta:
        o.matrix_world = M @ o.matrix_world; o["ajustado"] = True
bpy.context.view_layer.update()
pts = [o.matrix_world @ v.co for o in puerta for v in o.data.vertices]
ab = [((Vector((p.x, p.y)) - CC).dot(U), (Vector((p.x, p.y)) - CC).dot(W), p.z) for p in pts]
print("PUERTA a", round(min(t[0] for t in ab), 2), round(max(t[0] for t in ab), 2), "b", round(min(t[1] for t in ab), 2), round(max(t[1] for t in ab), 2), "z", round(min(t[2] for t in ab), 2), round(max(t[2] for t in ab), 2))
# herraje (donde ira el candado)
h = puerta[4]; hp = [h.matrix_world @ v.co for v in h.data.vertices]
hc = sum(hp, Vector()) / len(hp)
ha = (Vector((hc.x, hc.y)) - CC).dot(U); hb = (Vector((hc.x, hc.y)) - CC).dot(W)
print("HERRAJE a", round(ha, 2), "b", round(hb, 2), "z", round(hc.z, 2))
amax = max(t[0] for t in ab)
c = bpy.data.objects["Candado_Cuerpo"]
cx2, cy2 = P(amax + 0.05, hb)
c.location = (cx2, cy2, hc.z - 0.15)
c.rotation_euler.z = math.radians(math.degrees(math.atan2(U.y, U.x)) + 90)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("AJUSTE OK")
