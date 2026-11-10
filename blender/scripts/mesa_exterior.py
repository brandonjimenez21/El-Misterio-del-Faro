# La mesa de navegacion (con el mapa y la bitacora) y el candado van FUERA de la puerta exterior de la cabana
# (segun puzzles_objetos.txt: "al lado de la puerta, una mesa de navegacion con una bitacora y un mapa de la costa").
# Puerta exterior: pared oeste de la cabana (Blender x ~ 8.7, y ~ 100.2), mirando hacia +X.
# Uso: blender -b archivo.blend --python mesa_exterior.py -- [--save]
import bpy, math, sys
from mathutils import Vector, Matrix

O = bpy.data.objects
I = O["IslandModel"]
bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
def suelo(x, y):
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    return (I.matrix_world @ l).z if h else None

PUERTA = Vector((8.75, 100.2))
PISO_INT = 7.37
mesa = O["Mesa_Navegacion"]
sobre = [O["Mapa_Costa"], O["Bitacora_Farero"]]
if not mesa.get("exterior"):
    alt = {o.name: o.location.z - PISO_INT for o in [mesa] + sobre}
    # mesa junto a la puerta, hacia el sur para no tapar el sendero del farero (que sale al NE)
    nx, ny = PUERTA.x + 3.4, PUERTA.y - 3.4
    g = suelo(nx, ny)
    if g is None:
        g = PISO_INT
    larga_en_x = mesa.dimensions.x >= mesa.dimensions.y
    destino = math.radians(90.0) if larga_en_x else 0.0       # eje largo paralelo a la pared (eje Y)
    dd = destino - mesa.rotation_euler.z
    rels = [(f, Vector((f.location.x - mesa.location.x, f.location.y - mesa.location.y))) for f in sobre]
    mesa.rotation_euler.z = destino
    mesa.location = (nx, ny, g + alt[mesa.name])
    R = Matrix.Rotation(dd, 2)
    for f, rel in rels:
        r = R @ rel
        f.location = (nx + r.x, ny + r.y, g + alt[f.name])
        f.rotation_euler.z += dd
    mesa["exterior"] = True
    print("MESA nueva posicion", round(nx, 2), round(ny, 2), "suelo", round(g, 2), "dims", tuple(round(d, 2) for d in mesa.dimensions))

# candado en la puerta exterior, a la altura de la manija, mirando hacia afuera (+X)
c = O["Candado_Cuerpo"]
if not c.get("exterior"):
    ruedas = [o for o in O if o.parent == c]
    gp = suelo(PUERTA.x + 0.8, PUERTA.y) or PISO_INT
    nueva = Vector((PUERTA.x + 0.22, PUERTA.y + 0.35, PISO_INT + 1.15))
    giro = math.radians(0.0) - c.rotation_euler.z + math.radians(float(sys.argv[sys.argv.index("--giro") + 1]) if "--giro" in sys.argv else 0.0)
    c.location = nueva
    c.rotation_euler.z += giro
    c["exterior"] = True
    print("CANDADO en", tuple(round(v, 2) for v in nueva), "giro", round(math.degrees(c.rotation_euler.z), 1))
# farol/luz calida junto a la puerta para que se vea la mesa y el candado de noche (en Unity: Luz_Puerta con parpadeo)
if "Luz_Puerta" not in O:
    ld = bpy.data.lights.new("Luz_Puerta", 'POINT')
    ld.color = (1.0, 0.62, 0.3); ld.energy = 250.0; ld.shadow_soft_size = 0.2
    lo = bpy.data.objects.new("Luz_Puerta", ld)
    lo.location = (PUERTA.x + 1.6, PUERTA.y - 1.4, PISO_INT + 3.0)
    for col in O["Mesa_Navegacion"].users_collection:
        col.objects.link(lo)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
