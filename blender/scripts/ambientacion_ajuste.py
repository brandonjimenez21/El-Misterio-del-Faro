# Ajuste de brillo de la ambientacion nocturna: luna menos intensa, niebla y cielo mas oscuros (parecia de dia).
# Uso: blender -b archivo.blend --python ambientacion_ajuste.py -- [--save]
import bpy, sys

S = bpy.context.scene
O = bpy.data.objects
nt = S.world.node_tree
N = nt.nodes

O["Luz_Luna"].data.energy = 2.2
N["Neblina"].inputs["Color"].default_value = (0.22, 0.29, 0.40, 1.0)
for n in N:
    if n.bl_idname == "ShaderNodeMix" and n.data_type == 'RGBA' and n.blend_type == 'MIX':
        n.inputs[6].default_value = (0.004, 0.008, 0.022, 1.0)     # cenit
        n.inputs[7].default_value = (0.045, 0.065, 0.10, 1.0)      # horizonte
N["Background"].inputs["Strength"].default_value = 1.0
# estrellas mas grandes y brillantes (el denoiser se las comia)
for n in N:
    if n.bl_idname == "ShaderNodeMapRange" and abs(n.inputs["From Max"].default_value - 0.07) < 1e-6:
        n.inputs["From Max"].default_value = 0.14
    if n.bl_idname == "ShaderNodeMath" and n.operation == 'MULTIPLY' and abs(n.inputs[1].default_value - 6.0) < 1e-6:
        n.inputs[1].default_value = 14.0
# la malla de la luna brilla un poco por si sola (en Unity el disco es emisivo)
for m in O["Luna"].data.materials:
    if m and m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.bl_idname == "ShaderNodeBsdfPrincipled":
                nd.inputs["Emission Color"].default_value = (0.75, 0.85, 1.0, 1.0)
                nd.inputs["Emission Strength"].default_value = 0.2
print("AJUSTE aplicado")
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
    print("AJUSTE guardado")
