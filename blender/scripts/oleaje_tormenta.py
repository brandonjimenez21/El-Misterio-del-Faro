# Oleaje de tormenta: sube el tamano/fuerza de las olas del modificador Ocean, mas espuma en crestas y rizado fino en el agua.
# No reconstruye el oceano (no toca Oceano_Lejano). Uso: blender -b archivo.blend --python oleaje_tormenta.py -- [--save]
import bpy, sys
ob = bpy.data.objects["Oceano"]
mod = ob.modifiers["Ocean"]
mod.wind_velocity = 26.0
mod.wave_alignment = 0.25
mod.damping = 0.45
mod.foam_coverage = 0.05
DRIVERS = {
    "wave_scale":    "0.95 + 0.32 * sin(frame / 137.0) + 0.14 * sin(frame / 42.0 + 1.3)",
    "choppiness":    "1.35 + 0.4 * sin(frame / 102.0 + 0.7)",
    "foam_coverage": "0.05 + 0.03 * sin(frame / 137.0)",
}
for prop, expr in DRIVERS.items():
    ob.driver_remove(prop, -1) if False else None
    fc = [f for f in ob.animation_data.drivers if f.data_path == 'modifiers["Ocean"].' + prop]
    for f in fc:
        f.driver.expression = expr
        print("OLEAJE driver", prop, "->", expr)
for n in ob.data.materials[0].node_tree.nodes:
    if n.type == 'BUMP':
        n.inputs['Strength'].default_value = 0.22
    if n.type == 'TEX_NOISE' and n.inputs['Scale'].default_value == 0.9:
        n.inputs['Scale'].default_value = 1.4
print("OLEAJE listo: viento", mod.wind_velocity, "espuma", mod.foam_coverage)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
