# Exporta solo Puzle2_IslaAlterada.fbx sin re-hornear texturas (para cuando solo cambian posiciones).
# Materiales B_<objeto> como en exportar_unity.py. NO guarda el .blend.
import bpy, os
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
col = bpy.data.collections["Puzle2_IslaAlterada"]
objs = list(col.objects)
for o in objs:
    if o.type == 'MESH':
        m = bpy.data.materials.new("B_" + o.name)
        m.use_nodes = True
        m.diffuse_color = (0.5, 0.5, 0.5, 1)
        o.data.materials.clear()
        o.data.materials.append(m)
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "Puzle2_IslaAlterada.fbx"), use_selection=True,
                         apply_scale_options='FBX_SCALE_ALL', bake_anim=True, add_leaf_bones=False,
                         object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=True)
print("PUZLE2 EXPORTADO", len(objs))
