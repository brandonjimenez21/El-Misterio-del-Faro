# Exporta colecciones tal cual (sin hornear; los materiales viajan por nombre y Unity les pone su shader). NO guarda el .blend.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/exportar_sin_hornear.py -- Narrativa_Detalles [Otra ...]
import bpy, os, sys
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
for nombre in sys.argv[sys.argv.index("--") + 1:]:
    col = bpy.data.collections[nombre]
    objs = [o for o in col.objects if o.type in ('MESH', 'EMPTY')]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, nombre + ".fbx"), use_selection=True,
                             apply_scale_options='FBX_SCALE_ALL', bake_anim=False, add_leaf_bones=False,
                             object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=False)
    print("EXPORTADO", nombre, len(objs))
