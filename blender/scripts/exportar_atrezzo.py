# Exporta solo Atrezzo_Exterior.fbx (materiales M_Atrezzo_* conservados; las luces no viajan por FBX). NO guarda el .blend.
import bpy, os
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
col = bpy.data.collections["Atrezzo_Exterior"]
objs = [o for o in col.objects if o.type in ('MESH', 'EMPTY')]
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "Atrezzo_Exterior.fbx"), use_selection=True,
                         apply_scale_options='FBX_SCALE_ALL', bake_anim=False, add_leaf_bones=False,
                         object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=True)
print("ATREZZO EXPORTADO", len(objs))
