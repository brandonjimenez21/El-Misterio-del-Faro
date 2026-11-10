# Exporta solo Oceano_Lejano.fbx (sin hornear nada). NO guarda el .blend.
import bpy, os
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
ob = bpy.data.objects["Oceano_Lejano"]
bpy.ops.object.select_all(action='DESELECT')
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "Oceano_Lejano.fbx"), use_selection=True,
                         apply_scale_options='FBX_SCALE_ALL', bake_anim=False, add_leaf_bones=False,
                         object_types={'MESH'}, path_mode='STRIP', use_tspace=True)
print("OCEANO_LEJANO EXPORTADO")
