# La niebla del mundo llenaba tambien el cielo (render gris plano, sin estrellas ni luna). Se hace "baja": la densidad
# cae con la altura (z del mundo), asi el mar y la isla quedan brumosos y el cielo despejado.
import bpy

S = bpy.context.scene
if S.get("niebla_altura"):
    raise SystemExit("ya aplicado")
nt = S.world.node_tree
N, L = nt.nodes, nt.links
neb = N["Neblina"]

geo = N.new("ShaderNodeNewGeometry")
sep = N.new("ShaderNodeSeparateXYZ")
L.new(geo.outputs["Position"], sep.inputs["Vector"])
zpos = N.new("ShaderNodeMath")
zpos.operation = 'MAXIMUM'
zpos.inputs[1].default_value = 0.0
L.new(sep.outputs["Z"], zpos.inputs[0])
esc = N.new("ShaderNodeMath")                  # -z / altura de escala
esc.operation = 'DIVIDE'
esc.inputs[1].default_value = -22.0
L.new(zpos.outputs[0], esc.inputs[0])
ex = N.new("ShaderNodeMath")                   # e ^ (-z / 22)
ex.operation = 'POWER'
ex.inputs[0].default_value = 2.71828
L.new(esc.outputs[0], ex.inputs[1])
dens = N.new("ShaderNodeMath")
dens.operation = 'MULTIPLY'
dens.inputs[1].default_value = 0.020           # densidad a nivel del mar
L.new(ex.outputs[0], dens.inputs[0])
for l in list(neb.inputs["Density"].links):
    L.remove(l)
L.new(dens.outputs[0], neb.inputs["Density"])
neb.inputs["Emission Strength"].default_value = 0.0

S["niebla_altura"] = 1
bpy.ops.wm.save_mainfile()
print("NIEBLA ALTURA OK")
