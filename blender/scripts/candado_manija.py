# Candado: (1) las 4 ruedas de numeros se recolocan DENTRO de la ranura inferior del candado (estaban giradas
# alrededor de un origen equivocado y quedaban esparcidas fuera), (2) el candado cuelga de la manija
# (Cylinder.053, el aldabon redondo de la puerta del portal de la cabana), mirando hacia afuera.
import bpy, math
from mathutils import Vector, Matrix

O = bpy.data.objects
bpy.context.view_layer.update()
U = Vector((0.8, 0.6, 0.0))
cuerpo = O["Candado_Cuerpo"]
ruedas = [O["Candado_Rueda_%d" % i] for i in (1, 2, 3, 4)]

# ------------------------------------------------ ruedas
X = (-0.068, -0.023, 0.023, 0.068)         # posiciones a lo ancho del cuerpo (coordenadas locales)
for o, x in zip(ruedas, X):
    # centrar la malla en su propio origen (para que gire sobre su eje)
    pts = [v.co for v in o.data.vertices]
    ctr = sum(pts, Vector()) / len(pts)
    ctr = Vector(((min(p.x for p in pts) + max(p.x for p in pts)) / 2,
                  (min(p.y for p in pts) + max(p.y for p in pts)) / 2,
                  (min(p.z for p in pts) + max(p.z for p in pts)) / 2))
    o.data.transform(Matrix.Translation(-ctr))
    o.data.update()
    o.matrix_parent_inverse.identity()
    o.location = (x, -0.045, 0.145)           # en la ranura de la tapa inferior, medio rodete asomando por delante

# ------------------------------------------------ colgar de la manija
manija = O["Cylinder.053"]
bb = [manija.matrix_world @ Vector(c) for c in manija.bound_box]
H = sum(bb, Vector()) / 8                      # centro de la manija
cara = max((p - H).dot(U) for p in bb)         # cuanto sobresale hacia afuera (a lo largo de U)
esc = cuerpo.scale.x
# la arco (asa) del candado atraviesa la manija: el arco esta en z local 0.25..0.36
origen_z = H.z - 0.30 * esc
pos = H + U * (cara + 0.07 * esc)
cuerpo.location = (pos.x, pos.y, origen_z)
cuerpo.rotation_euler = (0, 0, math.atan2(U.y, U.x) + math.pi / 2)
print("CANDADO manija", tuple(round(v, 2) for v in H), "cuerpo", tuple(round(v, 2) for v in cuerpo.location))
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("CANDADO OK")
