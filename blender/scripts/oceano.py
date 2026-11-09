# Oceano animado + neblina para "El Misterio del Faro".
# Uso (Blender): abrir el .blend y ejecutar este script en el editor de texto, o:
#   blender -b archivo.blend --python oceano.py
# Las olas cambian de tamano y fuerza con DRIVERS (no necesita el script abierto):
#   tiempo, wave_scale, choppiness y espuma oscilan con el frame. Ajusta los numeros en DRIVERS.
import bpy, sys, math

S = bpy.context.scene
NIVEL_MAR = -0.55            # altura del agua (m)
TAM = 160.0                  # tamano de un mosaico de oceano (m)
REPETIR = 2                  # mosaicos por lado -> ~320 m de oceano
CENTRO = (0.0, 45.0)         # centro del oceano (m): entre el muelle y la isla
NEBLINA = 0.009              # densidad de la neblina (mas alto = horizonte mas cerrado)
BRILLO_NEBLINA = 0.0008      # resplandor de la neblina (mas alto = noche mas clara)
COLOR_NEBLINA = (0.045, 0.06, 0.085)
SCRATCH = sys.argv[-1] if sys.argv[-1].endswith("scratchpad") else None

# ------------------------------------------------------------ limpiar
if "Oceano" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["Oceano"], do_unlink=True)
for c in list(bpy.data.collections):
    if c.name == "Oceano":
        bpy.data.collections.remove(c)
for m in list(bpy.data.materials):
    if m.name == "M_Oceano":
        bpy.data.materials.remove(m)

col = bpy.data.collections.new("Oceano")
S.collection.children.link(col)

# ------------------------------------------------------------ malla + modificador Ocean
me = bpy.data.meshes.new("Oceano")
me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
ob = bpy.data.objects.new("Oceano", me)
col.objects.link(ob)
mod = ob.modifiers.new("Ocean", 'OCEAN')
mod.geometry_mode = 'GENERATE'
mod.spatial_size = int(TAM)
mod.resolution = 20            # calidad de render (celdas ~0.5 m)
mod.viewport_resolution = 8    # visor ligero (para 60 fps); sube a 8-10 si tu PC va sobrado
mod.repeat_x = REPETIR
mod.repeat_y = REPETIR
mod.random_seed = 7
mod.wave_scale = 0.7
mod.wave_scale_min = 0.0
mod.choppiness = 1.2
mod.wind_velocity = 18.0
mod.wave_alignment = 0.35
mod.wave_direction = math.radians(20)
mod.damping = 0.6
mod.use_foam = True
mod.foam_layer_name = "foam"
mod.foam_coverage = 0.03
mod.use_normals = True
# el oceano generado se extiende hacia +x,+y desde el origen del objeto: se centra
ob.location = (CENTRO[0] - TAM * REPETIR / 2 + TAM / 2, CENTRO[1] - TAM * REPETIR / 2 + TAM / 2, NIVEL_MAR)

# ------------------------------------------------------------ DRIVERS: olas que cambian de tamano y fuerza
DRIVERS = {
    "time":          "frame / 60.0 * 0.55",
    "wave_scale":    "0.65 + 0.28 * sin(frame / 137.0) + 0.12 * sin(frame / 42.0 + 1.3)",
    "choppiness":    "0.9 + 0.35 * sin(frame / 102.0 + 0.7)",
    "foam_coverage": "0.03 + 0.02 * sin(frame / 137.0)",
}
for prop, expr in DRIVERS.items():
    fc = mod.driver_add(prop)
    d = fc.driver
    d.type = 'SCRIPTED'
    d.expression = expr
S.frame_start, S.frame_end = 1, 1200
S.render.fps = 60              # la reproduccion del visor va a los fps de la escena

# ------------------------------------------------------------ material del agua
m = bpy.data.materials.new("M_Oceano")
m.use_nodes = True
nt = m.node_tree
nt.nodes.clear()
N = nt.nodes.new
L = nt.links.new
out = N('ShaderNodeOutputMaterial')
bsdf = N('ShaderNodeBsdfPrincipled')
bsdf.inputs['Base Color'].default_value = (0.008, 0.03, 0.045, 1)
bsdf.inputs['Roughness'].default_value = 0.07
bsdf.inputs['IOR'].default_value = 1.333
bsdf.inputs['Metallic'].default_value = 0.0
tc = N('ShaderNodeTexCoord')
mp = N('ShaderNodeMapping')
nz = N('ShaderNodeTexNoise')
nz.noise_dimensions = '4D'
nz.inputs['Scale'].default_value = 0.9
nz.inputs['Detail'].default_value = 5
nz.inputs['Roughness'].default_value = 0.6
bump = N('ShaderNodeBump')
bump.inputs['Strength'].default_value = 0.12
bump.inputs['Distance'].default_value = 0.4
L(tc.outputs['Object'], mp.inputs['Vector'])
L(mp.outputs['Vector'], nz.inputs['Vector'])
L(nz.outputs['Fac'], bump.inputs['Height'])
L(bump.outputs['Normal'], bsdf.inputs['Normal'])
fw = nz.inputs['W'].driver_add('default_value')
fw.driver.type = 'SCRIPTED'
fw.driver.expression = "frame / 60.0 * 0.35"
# color: mas claro en las crestas y espuma desde el atributo "foam"
geo = N('ShaderNodeNewGeometry')
sep = N('ShaderNodeSeparateXYZ')
L(geo.outputs['Position'], sep.inputs['Vector'])
ramp = N('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = NIVEL_MAR - 0.9
ramp.color_ramp.elements[0].color = (0.004, 0.02, 0.032, 1)
ramp.color_ramp.elements[1].position = NIVEL_MAR + 0.9
ramp.color_ramp.elements[1].color = (0.03, 0.09, 0.105, 1)
L(sep.outputs['Z'], ramp.inputs['Fac'])
foam = N('ShaderNodeAttribute')
foam.attribute_name = "foam"
foam.attribute_type = 'GEOMETRY'
fr = N('ShaderNodeMapRange')
fr.inputs['From Min'].default_value = 0.9
fr.inputs['From Max'].default_value = 1.4
L(foam.outputs['Fac'], fr.inputs['Value'])
fn = N('ShaderNodeTexNoise')
fn.inputs['Scale'].default_value = 3.0
fn.inputs['Detail'].default_value = 10
mulf = N('ShaderNodeMath')
mulf.operation = 'MULTIPLY'
L(fr.outputs['Result'], mulf.inputs[0])
L(fn.outputs['Fac'], mulf.inputs[1])
mix = N('ShaderNodeMix')
mix.data_type = 'RGBA'
mix.inputs[7].default_value = (0.2, 0.26, 0.3, 1)
L(mulf.outputs[0], mix.inputs[0])
L(ramp.outputs['Color'], mix.inputs[6])
L(mix.outputs[2], bsdf.inputs['Base Color'])
L(bsdf.outputs['BSDF'], out.inputs['Surface'])
ob.data.materials.append(m)

# ------------------------------------------------------------ neblina (volumen en el mundo)
w = S.world or bpy.data.worlds.new("Mundo")
S.world = w
w.use_nodes = True
wt = w.node_tree
bg = wt.nodes.get("Background")
bg.inputs['Color'].default_value = (*COLOR_NEBLINA, 1)
wo = wt.nodes.get("World Output")
for n in [n for n in wt.nodes if n.name == "Neblina"]:
    wt.nodes.remove(n)
vs = wt.nodes.new('ShaderNodeVolumePrincipled')
vs.name = "Neblina"
vs.inputs['Color'].default_value = (0.5, 0.6, 0.7, 1)
vs.inputs['Density'].default_value = NEBLINA
vs.inputs['Emission Color'].default_value = (0.10, 0.14, 0.20, 1)
vs.inputs['Emission Strength'].default_value = BRILLO_NEBLINA
wt.links.new(vs.outputs['Volume'], wo.inputs['Volume'])
bg.inputs['Strength'].default_value = 2.0
S.view_settings.exposure = 0.6
S.cycles.volume_bounces = 2

# ------------------------------------------------------------ referencias fuera del render
if "Referencia_Layout" in bpy.data.collections:
    for o in bpy.data.collections["Referencia_Layout"].objects:
        o.hide_render = True
    if "Ref_Mapa_Isla" in bpy.data.objects:
        bpy.data.objects["Ref_Mapa_Isla"].hide_viewport = True

bpy.ops.object.select_all(action='DESELECT')
if SCRATCH:
    bpy.ops.wm.save_as_mainfile(filepath=SCRATCH + r"\faro_oceano.blend", copy=True)
else:
    bpy.ops.wm.save_mainfile()
print("OCEANO OK", tuple(ob.location))
