# Exporta solo Isla.fbx (mismo procedimiento que exportar_unity.py, sin hornear nada). NO guarda el .blend.
import bpy, os
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
isla = bpy.data.objects["IslandModel"]
m = bpy.data.materials.new("B_IslandModel")
m.use_nodes = True
m.diffuse_color = (0.5, 0.5, 0.5, 1)
isla.data.materials.clear()
isla.data.materials.append(m)
bpy.ops.object.select_all(action='DESELECT')
isla.select_set(True)
bpy.context.view_layer.objects.active = isla
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "Isla.fbx"), use_selection=True,
                         apply_scale_options='FBX_SCALE_ALL', bake_anim=True, add_leaf_bones=False,
                         object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=True)
print("ISLA EXPORTADA")
