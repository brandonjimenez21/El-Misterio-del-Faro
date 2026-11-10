# Ambientacion nocturna en Blender (equivale a lo hecho en Unity): niebla mas densa, cielo con estrellas y horizonte
# brumoso, luz de luna alineada con la malla "Luna", olas mas altas/fuertes y marea lenta (driver en el nivel del mar).
# Se aplica una sola vez (bandera de escena "ambientacion").
import bpy, math
from mathutils import Vector

S = bpy.context.scene
if S.get("ambientacion"):
    raise SystemExit("ya aplicado")
O = bpy.data.objects
W = S.world
nt = W.node_tree
N = nt.nodes
L = nt.links

# ------------------------------------------------ niebla (volumen del mundo)
neb = N["Neblina"]
neb.inputs["Density"].default_value = 0.013
neb.inputs["Emission Strength"].default_value = 0.0012
neb.inputs["Emission Color"].default_value = (0.17, 0.22, 0.30, 1.0)

# ------------------------------------------------ cielo: degradado + estrellas (coordenadas "Generated" = direccion)
bg = N["Background"]
for l in list(bg.inputs["Color"].links):
    L.remove(l)
tc = N.new("ShaderNodeTexCoord")
sep = N.new("ShaderNodeSeparateXYZ")
L.new(tc.outputs["Generated"], sep.inputs["Vector"])
# 1 en el horizonte -> 0 en lo alto
glow = N.new("ShaderNodeMapRange")
glow.inputs["From Min"].default_value = 0.0
glow.inputs["From Max"].default_value = 0.35
glow.inputs["To Min"].default_value = 1.0
glow.inputs["To Max"].default_value = 0.0
glow.clamp = True
absz = N.new("ShaderNodeMath")
absz.operation = 'ABSOLUTE'
L.new(sep.outputs["Z"], absz.inputs[0])
L.new(absz.outputs[0], glow.inputs["Value"])
mix = N.new("ShaderNodeMix")
mix.data_type = 'RGBA'
mix.inputs[6].default_value = (0.012, 0.022, 0.06, 1.0)      # cenit
mix.inputs[7].default_value = (0.17, 0.22, 0.30, 1.0)        # horizonte (color de la niebla)
L.new(glow.outputs["Result"], mix.inputs[0])

# estrellas: celdas voronoi, solo ~3 % tienen estrella, punto pequeno
vor = N.new("ShaderNodeTexVoronoi")
vor.voronoi_dimensions = '3D'
vor.feature = 'F1'
vor.inputs["Scale"].default_value = 260.0
L.new(tc.outputs["Generated"], vor.inputs["Vector"])
punto = N.new("ShaderNodeMapRange")
punto.inputs["From Min"].default_value = 0.0
punto.inputs["From Max"].default_value = 0.07
punto.inputs["To Min"].default_value = 1.0
punto.inputs["To Max"].default_value = 0.0
punto.clamp = True
L.new(vor.outputs["Distance"], punto.inputs["Value"])
sepc = N.new("ShaderNodeSeparateColor")
L.new(vor.outputs["Color"], sepc.inputs["Color"])
elige = N.new("ShaderNodeMath")
elige.operation = 'GREATER_THAN'
elige.inputs[1].default_value = 0.97
L.new(sepc.outputs["Red"], elige.inputs[0])
estr = N.new("ShaderNodeMath")
estr.operation = 'MULTIPLY'
L.new(punto.outputs["Result"], estr.inputs[0])
L.new(elige.outputs[0], estr.inputs[1])
arriba = N.new("ShaderNodeMapRange")           # las estrellas desaparecen cerca del horizonte
arriba.inputs["From Min"].default_value = 0.03
arriba.inputs["From Max"].default_value = 0.35
arriba.clamp = True
L.new(sep.outputs["Z"], arriba.inputs["Value"])
estr2 = N.new("ShaderNodeMath")
estr2.operation = 'MULTIPLY'
estr2.inputs[1].default_value = 6.0              # brillo
L.new(estr.outputs[0], estr2.inputs[0])
estr3 = N.new("ShaderNodeMath")
estr3.operation = 'MULTIPLY'
L.new(estr2.outputs[0], estr3.inputs[0])
L.new(arriba.outputs["Result"], estr3.inputs[1])
suma = N.new("ShaderNodeMix")
suma.data_type = 'RGBA'
suma.blend_type = 'ADD'
suma.inputs[0].default_value = 1.0
L.new(mix.outputs[2], suma.inputs[6])
L.new(estr3.outputs[0], suma.inputs[7])          # float -> color (gris)
L.new(suma.outputs[2], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0

# ------------------------------------------------ luz de luna alineada con la malla Luna
luna = O["Luna"]
bpy.context.view_layer.update()
pl = luna.matrix_world.translation.copy()
isla = O["IslandModel"]
pis = sum((isla.matrix_world @ Vector(c) for c in isla.bound_box), Vector()) / 8
d = (pis - pl).normalized()                      # direccion de la luz: de la luna hacia la isla
sol = O["Luz_Luna"]
sol.rotation_mode = 'QUATERNION'
sol.rotation_quaternion = d.to_track_quat('-Z', 'Y')
sol.rotation_mode = 'XYZ'
sol.data.energy = 7.0
sol.data.color = (0.60, 0.74, 1.0)

# ------------------------------------------------ olas mas altas y fuertes
oc = O["Oceano"]
mod = oc.modifiers["Ocean"]
exprs = {
    "wave_scale": "1.15 + 0.25 * sin(frame / 137.0) + 0.10 * sin(frame / 42.0 + 1.3)",
    "choppiness": "1.15 + 0.35 * sin(frame / 102.0 + 0.7)",
    "foam_coverage": "0.05 + 0.03 * sin(frame / 137.0)",
}
for dr in oc.animation_data.drivers:
    for k, e in exprs.items():
        if dr.data_path == 'modifiers["Ocean"].%s' % k:
            dr.driver.expression = e
mod.foam_coverage = 0.05

# ------------------------------------------------ marea: el nivel del mar sube y baja +-0.3 m (ciclo ~3 min a 24 fps)
base = oc.location.z
fc = oc.driver_add("location", 2)
fc.driver.type = 'SCRIPTED'
fc.driver.expression = "%.4f + 0.3 * sin(frame / 690.0)" % base
S["nivel_mar_base"] = base

S["ambientacion"] = 1
bpy.ops.wm.save_mainfile()
print("AMBIENTACION OK luna", tuple(round(v, 1) for v in pl), "isla", tuple(round(v, 1) for v in pis), "dir", tuple(round(v, 2) for v in d), "nivel base", round(base, 3))
