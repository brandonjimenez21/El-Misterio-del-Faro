# Acomoda el muelle, los objetos de los puzles y el faro sobre la isla, SIN tocar la isla
# (su posicion, escala y altura son las que dejaste en Blender).
# Se puede repetir: si mueves o subes la isla, vuelve a ejecutarlo.
import bpy, math
from mathutils import Vector

S = bpy.context.scene
I = bpy.data.objects["IslandModel"]
MUELLE_XY = (0.0, -17.0)          # el muelle se corre para que su extremo de tierra toque la orilla de la isla
CABANA_XY = (5.2, 70.3)           # centro de la cabana: todo su interior comparte el mismo suelo
SEGUIDORES = {"Bitacora_Farero": "Mesa_Navegacion", "Mapa_Costa": "Mesa_Navegacion",
              "Caja_Cerillas": "Mesa_Trabajo", "Taza_Derramada": "Mesa_Trabajo",
              "Reloj_Manecilla_Hora": "Reloj_Pared", "Reloj_Manecilla_Minutero": "Reloj_Pared"}

bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
dirl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()


def suelo(x, y):
    hit, loc, nor, idx = I.ray_cast(inv @ Vector((x, y, 500.0)), dirl)
    return (I.matrix_world @ loc).z if hit else None


# ---- muelle
bpy.data.objects["Muelle_Conjunto"].location = (MUELLE_XY[0], MUELLE_XY[1], 0.0)

# ---- objetos de los puzles (solo cambia la altura z)
raices = [o for c in bpy.data.collections if c.name.startswith("Puzle") for o in c.objects if o.parent is None]
for o in raices:
    if "z_base" not in o:
        o["z_base"] = o.location.z
g_cabana = suelo(*CABANA_XY)
for o in raices:
    if o.name == "Luna":
        continue
    host = bpy.data.objects[SEGUIDORES[o.name]] if o.name in SEGUIDORES else o
    if "Puzle3_InteriorFaro" in [c.name for c in o.users_collection]:
        g = g_cabana
    else:
        g = suelo(host.location.x, host.location.y)
    if g is None:
        print("SIN ISLA", o.name)
        continue
    o.location.z = o["z_base"] + g
    print("ASENTADO", o.name, round(g, 1))

# ---- faro y cabana
raiz = bpy.data.objects["Faro_Cabana_Raiz"]
bpy.context.view_layer.update()
gf = suelo(raiz.location.x, raiz.location.y)
meshes = [o for o in raiz.children_recursive if o.type == 'MESH']
mn = min((o.matrix_world @ Vector(c)).z for o in meshes for c in o.bound_box)
raiz.location.z += gf - mn
print("FARO suelo", round(gf, 1))
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("ACOMODADO OK")
