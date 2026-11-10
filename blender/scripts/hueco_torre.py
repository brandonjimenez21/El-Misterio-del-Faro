# Corta el hueco de la entrada en la pared de la torre (la que da a la cabana): se parten las caras con planos
# (lados, suelo y dintel) y se borran las del interior del hueco. La torre es una malla abierta, no sirve el Boolean.
import bpy, bmesh, math
from mathutils import Vector

O = bpy.data.objects
S = bpy.context.scene
if S.get("hueco_torre"):
    raise SystemExit("ya aplicado")
CC = Vector((1.82, 95.01))
U = Vector((0.8, 0.6))
W = Vector((0.6, -0.8))
TC = Vector((-6.64, 89.52))
PISO = 7.37
HB = -0.68
ANCHO = 1.7
Z0 = PISO + 0.08
Z1 = PISO + 2.7
TORRE = O["Cylinder"]
mw = TORRE.matrix_world
inv = mw.inverted()
n0 = len(TORRE.data.polygons)

bm = bmesh.new()
bm.from_mesh(TORRE.data)
bm.transform(mw)                         # trabajar en coordenadas del mundo


def corta(punto, normal):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=punto, plane_no=normal, clear_inner=False, clear_outer=False)


c0 = Vector((CC.x, CC.y, 0)) + Vector((W.x, W.y, 0)) * (HB - ANCHO / 2)
c1 = Vector((CC.x, CC.y, 0)) + Vector((W.x, W.y, 0)) * (HB + ANCHO / 2)
corta(c0, Vector((W.x, W.y, 0)))
corta(c1, Vector((W.x, W.y, 0)))
corta(Vector((0, 0, Z0)), Vector((0, 0, 1)))
corta(Vector((0, 0, Z1)), Vector((0, 0, 1)))

borrar = []
for f in bm.faces:
    c = f.calc_center_median()
    rel = Vector((c.x, c.y)) - TC
    b = (Vector((c.x, c.y)) - CC).dot(W)
    if rel.dot(U) > 5.0 and HB - ANCHO / 2 < b < HB + ANCHO / 2 and Z0 < c.z < Z1:
        borrar.append(f)
bmesh.ops.delete(bm, geom=borrar, context='FACES')
bm.transform(inv)
bm.to_mesh(TORRE.data)
bm.free()
TORRE.data.update()
print("HUECO polys", n0, "->", len(TORRE.data.polygons), "borradas", len(borrar))
S["hueco_torre"] = 1
bpy.ops.wm.save_mainfile()
print("HUECO OK")
