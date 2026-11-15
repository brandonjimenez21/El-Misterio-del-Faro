# Suaviza la madera procedural del muelle (M_MaderaGris / M_MaderaMojada): las manchas casi negras duras
# pasan a vetas/manchas marron oscuro suaves, mas contraste de veta y mas rugosidad en el relieve.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/madera_muelle.py -- --save
import bpy, sys
for nm in ("M_MaderaGris", "M_MaderaMojada"):
    nt = bpy.data.materials[nm].node_tree
    n = nt.nodes
    r = n["Color Ramp.001"].color_ramp.elements       # umbral duro de las manchas
    r[0].position, r[1].position = 0.46, 0.80
    mez = n["Mix.002"]
    mez.inputs[7].default_value = (0.075, 0.062, 0.05, 1.0) if nm == "M_MaderaGris" else (0.05, 0.045, 0.04, 1.0)
    n["Noise Texture.001"].inputs["Scale"].default_value = 60.0     # manchas mas finas, como poros / nudos pequenos
    n["Mapping.003"].inputs["Scale"].default_value = (0.25, 1.0, 1.0)
    n["Bump"].inputs["Strength"].default_value = 0.8
    n["Bump"].inputs["Distance"].default_value = 0.02
    n["Principled BSDF"].inputs["Roughness"].default_value = 0.6 if nm == "M_MaderaGris" else 0.46   # madera calada por la lluvia
    print("OK", nm)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
