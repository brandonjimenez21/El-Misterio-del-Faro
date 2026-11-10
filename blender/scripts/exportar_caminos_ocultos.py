# Exporta Caminos_Ocultos.fbx (cintas de los 3 caminos ocultos). Material M_CaminoOculto conservado. NO guarda el .blend.
import bpy, os
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
col = bpy.data.collections["Caminos_Ocultos"]
objs = [o for o in col.objects if o.type == 'MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "Caminos_Ocultos.fbx"), use_selection=True,
                         apply_scale_options='FBX_SCALE_ALL', bake_anim=False, add_leaf_bones=False,
                         object_types={'MESH'}, path_mode='STRIP', use_tspace=False)
print("OCULTOS EXPORTADOS", len(objs))
