# Huellas mojadas en el muelle: llegan desde el agua (extremo del muelle) hasta la isla y se van desvaneciendo (mas pequenas / separadas).
# Coleccion "Huellas_Muelle" y FBX Assets/Models/Faro/Huellas_Muelle.fbx. Cada huella es un objeto para poder ir activandolas por tramos.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/huellas_muelle.py -- --save
import bpy, bmesh, math, os, sys, random
from mathutils import Vector

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
rnd = random.Random(404)
NOMBRE = "Huellas_Muelle"
col = bpy.data.collections.get(NOMBRE) or bpy.data.collections.new(NOMBRE)
if NOMBRE not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(col)
for o in list(col.objects):
    bpy.data.objects.remove(o, do_unlink=True)
m = bpy.data.materials.get("M_Huella_Mojada") or bpy.data.materials.new("M_Huella_Mojada")
m.use_nodes = True
b = m.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.012, 0.016, 0.02, 1)
b.inputs["Roughness"].default_value = 0.08
m.diffuse_color = (0.012, 0.016, 0.02, 1)


def pie(lado, esc):
    """sola + talon, en metros, apuntando a +Y local. lado = +1 derecho, -1 izquierdo"""
    bm = bmesh.new()
    def elipse(cx, cy, rx, ry, n=10):
        vs = [bm.verts.new((cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
        bm.faces.new(vs)
    elipse(0.0, 0.07 * esc, 0.055 * esc, 0.105 * esc)               # planta
    elipse(0.0, -0.13 * esc, 0.045 * esc, 0.055 * esc)              # talon
    for dx, dy, r in ((-0.036, 0.205, 0.016), (-0.012, 0.22, 0.016), (0.012, 0.22, 0.015), (0.034, 0.208, 0.014)):   # dedos
        elipse(dx * lado * esc, dy * esc, r * esc, r * 1.2 * esc, 6)
    for v in bm.verts:
        v.co.x *= lado
    return bm


N = 15
x0, y0 = -2.0, -57.5           # extremo del muelle (Blender: y negativa = hacia el mar). Unity z = -y
x1, y1 = -2.2, -41.6           # llegada a la isla
Z = 1.992                      # justo sobre la cubierta (nivel 1.98)
for i in range(N):
    t = i / (N - 1)
    lado = 1 if i % 2 == 0 else -1
    x = x0 + (x1 - x0) * t + 0.14 * lado + rnd.uniform(-0.03, 0.03)
    y = y0 + (y1 - y0) * t + rnd.uniform(-0.05, 0.05)
    bm = pie(lado, 1.0 - 0.28 * t)
    me = bpy.data.meshes.new("Huella_%02d" % i)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    ob = bpy.data.objects.new("Huella_%02d" % i, me)
    ob.location = (x, y, Z)
    ob.rotation_euler = (0, 0, math.radians(rnd.uniform(-12, 12)) + math.pi + math.atan2(y1 - y0, x1 - x0) - math.pi / 2 + math.pi)
    col.objects.link(ob)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = list(col.objects)[0]
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "Huellas_Muelle.fbx"), use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                         bake_anim=False, add_leaf_bones=False, object_types={'MESH'}, path_mode='STRIP')
print("HUELLAS OK", len(col.objects))
