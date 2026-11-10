# Re-exporta una coleccion SIN re-hornear texturas (UV deterministas con smart_project, como exportar_unity.py) y con
# materiales planos B_<objeto>. Uso: blender -b archivo.blend --python exportar_coleccion.py -- Puzle1_Muelle [Otra ...]
# NO guarda el .blend.
import bpy, os, sys
RUTA_EXP = os.path.join(os.path.dirname(os.path.abspath(bpy.data.filepath)), "scripts", "exportar_unity.py")
exec(compile(open(RUTA_EXP, encoding="utf-8").read().split("# ---------------------------------------------------------------- LUNA")[0], RUTA_EXP, "exec"))
for nombre in sys.argv[sys.argv.index("--") + 1:]:
    c = bpy.data.collections[nombre]
    objs = list(c.objects)
    for o in objs:
        if o.type == 'MESH' and len(o.data.polygons) > 0:
            unwrap(o)
            o.data.materials.clear()
            o.data.materials.append(plain_mat(o.name))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    VL.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, nombre + ".fbx"), use_selection=True,
                             apply_scale_options='FBX_SCALE_ALL', bake_anim=True, add_leaf_bones=False,
                             object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=True)
    print("COLECCION EXPORTADA", nombre, len(objs))
