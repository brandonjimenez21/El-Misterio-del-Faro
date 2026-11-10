# Anillo de oceano lejano: plano grande con un hueco del tamano del oceano animado, para que desde lo alto
# no se vea el borde cuadrado. Se crea en la coleccion "Oceano" con el mismo material (M_Oceano).
# Uso: blender -b archivo.blend --python oceano_lejano.py -- [--save]
import bpy, sys
from mathutils import Vector

S = bpy.context.scene
oc = bpy.data.objects["Oceano"]
esq = [oc.matrix_world @ Vector(c) for c in oc.bound_box]
x0 = min(c.x for c in esq); x1 = max(c.x for c in esq)
y0 = min(c.y for c in esq); y1 = max(c.y for c in esq)
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
mitad = (x1 - x0) / 2 - 2.0          # el hueco queda 2 m por debajo del oceano animado
L = 4000.0                            # radio del anillo (m)
N = 80
cel = 2 * L / N

if "Oceano_Lejano" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["Oceano_Lejano"], do_unlink=True)

verts, caras, idx = [], [], {}
def I(i, j):
    if (i, j) not in idx:
        idx[(i, j)] = len(verts)
        verts.append((cx - L + i * cel, cy - L + j * cel, 0.0))
    return idx[(i, j)]
for i in range(N):
    for j in range(N):
        ax, bx = -L + i * cel, -L + (i + 1) * cel
        ay, by = -L + j * cel, -L + (j + 1) * cel
        if ax >= -mitad and bx <= mitad and ay >= -mitad and by <= mitad:
            continue
        caras.append((I(i, j), I(i + 1, j), I(i + 1, j + 1), I(i, j + 1)))
me = bpy.data.meshes.new("Oceano_Lejano")
me.from_pydata(verts, [], caras)
me.update()
ob = bpy.data.objects.new("Oceano_Lejano", me)
ob.location = (0, 0, oc.location.z - 0.02)
for c in oc.users_collection:
    c.objects.link(ob)
if oc.data.materials:
    me.materials.append(oc.data.materials[0])
ob.hide_render = False
print("OCEANO_LEJANO centro", round(cx, 2), round(cy, 2), "hueco", round(2 * mitad, 1), "caras", len(caras))
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
