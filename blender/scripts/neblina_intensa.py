# Niebla mas intensa: casi tapa el faro y las torres de piedra desde el muelle.
# Blender: sube la densidad a nivel del mar del volumen del mundo (la niebla "baja" con caida por altura).
# Unity: la niebla exponencial^2 se iguala con DENSIDAD_UNITY (ver Assets/Scripts/ y la escena).
# Uso: blender -b archivo.blend --python neblina_intensa.py -- [--save]
import bpy, sys
FACTOR = 4.0 / 3.0            # 0.009 -> 0.012 en Unity (x1.33), la densidad de Blender sube igual
S = bpy.context.scene
nt = S.world.node_tree
if S.get("niebla_factor"):
    raise SystemExit("ya aplicado (niebla_factor = %s)" % S["niebla_factor"])
m = nt.nodes["Math.008"]                                  # densidad a nivel del mar (multiplica la caida con la altura)
antes = m.inputs[1].default_value
m.inputs[1].default_value = antes * FACTOR
S["niebla_factor"] = FACTOR
print("NIEBLA densidad mar", antes, "->", m.inputs[1].default_value)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
