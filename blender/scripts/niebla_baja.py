# Capas de niebla baja: 3 discos horizontales (subdivididos) a distintas alturas sobre el mar y la isla.
# Unity les pone un shader transparente con ruido que se desplaza (Faro/NieblaBaja), con borde suave contra la geometria.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/niebla_baja.py -- --save
# Coordenadas: Unity y = Blender z; nivel del mar ~ -0.75 en Unity.
import bpy, bmesh, math, os, sys

RADIO = 330.0
ALTURAS = (-0.35, 0.7, 1.9)          # Blender z (m)
NOMBRE_COL = "Niebla_Baja"

col = bpy.data.collections.get(NOMBRE_COL) or bpy.data.collections.new(NOMBRE_COL)
if NOMBRE_COL not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(col)
for o in list(col.objects):
    bpy.data.objects.remove(o, do_unlink=True)

mat = bpy.data.materials.get("M_Niebla_Baja") or bpy.data.materials.new("M_Niebla_Baja")
mat.use_nodes = True
mat.diffuse_color = (0.6, 0.68, 0.78, 0.3)

for i, z in enumerate(ALTURAS):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, cap_tris=False, segments=48, radius=RADIO)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=0)
    me = bpy.data.meshes.new("Niebla_Baja_%d" % (i + 1))
    bm.to_mesh(me)
    bm.free()
    # uv en metros (para que el ruido tenga escala fija en Unity)
    uv = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        for li in p.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (v.x / 40.0, v.y / 40.0)
    me.materials.append(mat)
    ob = bpy.data.objects.new("Niebla_Baja_%d" % (i + 1), me)
    ob.location = (0.0, 0.0, z)
    ob.rotation_euler = (0.0, 0.0, math.radians(37 * i))
    col.objects.link(ob)

if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()

# exportar FBX (solo esta coleccion)
raiz = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = list(col.objects)[0]
bpy.ops.export_scene.fbx(filepath=os.path.join(raiz, "Assets", "Models", "Faro", "Niebla_Baja.fbx"), use_selection=True,
                         apply_scale_options='FBX_SCALE_ALL', bake_anim=False, add_leaf_bones=False,
                         object_types={'MESH'}, path_mode='STRIP')
print("NIEBLA_BAJA OK", [o.name for o in col.objects])
