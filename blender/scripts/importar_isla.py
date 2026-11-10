# Mete Island.blend y Lighthouse.blend dentro del .blend del proyecto (colecciones "Isla" y "Faro_Cabana").
# Se puede volver a ejecutar: borra lo importado antes y lo vuelve a traer.
import bpy, math, os
from mathutils import Vector

RUT = os.path.dirname(bpy.data.filepath)
S = bpy.context.scene
ISLA_ESCALA = 0.5            # el mapa pide una isla de ~5 veces el largo del muelle (~110 m): la isla original (300 m) se reduce a la mitad
ISLA_ROT_Z = 90.0            # giro de la isla (grados)
ISLA_POS = (-2.0, 46.0)      # centro de la isla (x, y) en metros: la meseta queda bajo los puzles y la punta sur junto al muelle
ISLA_Z = -10.8               # la meseta (11 m sobre la base) queda a ~0,2 m sobre el mar, a la altura de los objetos
FARO_XY = (-9.5, 72.0)       # posicion del faro segun el mapa (junto a la cabana)
FARO_ROT_Z = 180.0           # la cabana del modelo queda al este de la torre, como en el mapa


def limpiar():
    for n in ("Isla", "Faro_Cabana"):
        c = bpy.data.collections.get(n)
        if c:
            for o in list(c.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(c)
    for n in ("Faro_Cabana_Raiz",):
        if n in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)


def traer(archivo, nombres=None):
    with bpy.data.libraries.load(os.path.join(RUT, archivo), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if nombres is None or n in nombres]
    return [o for o in dst.objects if o]


limpiar()
c_isla = bpy.data.collections.new("Isla")
c_faro = bpy.data.collections.new("Faro_Cabana")
S.collection.children.link(c_isla)
S.collection.children.link(c_faro)

isla = traer("Island.blend", ["IslandModel"])      # se deja fuera UCX_Island (malla de colision)
for o in isla:
    c_isla.objects.link(o)
I = isla[0]
I.scale = tuple(v * ISLA_ESCALA for v in I.scale)
I.rotation_euler.z = math.radians(ISLA_ROT_Z)
I.location = (ISLA_POS[0], ISLA_POS[1], ISLA_Z)

faro = traer("Lighthouse.blend")
for o in faro:
    c_faro.objects.link(o)
raiz = bpy.data.objects.new("Faro_Cabana_Raiz", None)
raiz.empty_display_type = 'ARROWS'
raiz.empty_display_size = 3
c_faro.objects.link(raiz)
bpy.context.view_layer.update()

def suelo(x, y):
    """altura de la isla en (x, y), con un rayo contra la isla solamente"""
    m = I.matrix_world.inverted()
    o = m @ Vector((x, y, 500.0))
    d = (m.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit, loc, nor, idx = I.ray_cast(o, d)
    return (I.matrix_world @ loc).z if hit else None


bpy.context.view_layer.update()

# ---- asentar los objetos de los puzles sobre la isla (solo sube/baja en z; x e y no cambian)
SEGUIDORES = {"Bitacora_Farero": "Mesa_Navegacion", "Mapa_Costa": "Mesa_Navegacion",
              "Caja_Cerillas": "Mesa_Trabajo", "Taza_Derramada": "Mesa_Trabajo",
              "Reloj_Manecilla_Hora": "Reloj_Pared", "Reloj_Manecilla_Minutero": "Reloj_Pared"}
raices = [o for c in bpy.data.collections if c.name.startswith("Puzle") for o in c.objects if o.parent is None]
for o in raices:
    if "z_base" not in o:
        o["z_base"] = o.location.z          # altura original sobre el suelo plano (se guarda la primera vez)
# objetos de exterior que, si caen en una pendiente o fuera de la isla, se corren al sitio llano mas cercano
MOVIBLES = ("Poste_1_Reflejo", "Poste_2_Origen", "Poste_3_Fin", "Placa_Inscripcion", "Roca_Normal", "Roca_Bloqueo_Sendero")
for o in raices:
    if "xy_base" not in o:
        o["xy_base"] = (o.location.x, o.location.y)


def llano(g):
    return g is not None and -0.4 <= g <= 0.5


for n in MOVIBLES:
    o = bpy.data.objects[n]
    x0, y0 = o["xy_base"]
    o.location.x, o.location.y = x0, y0
    if not llano(suelo(x0, y0)):
        mejor = None
        for r in range(2, 16):
            for a in range(0, 360, 20):
                x, y = x0 + r * math.cos(math.radians(a)), y0 + r * math.sin(math.radians(a))
                if llano(suelo(x, y)) and llano(suelo(x + 1.5, y)) and llano(suelo(x - 1.5, y)) and llano(suelo(x, y + 1.5)) and llano(suelo(x, y - 1.5)):
                    mejor = (x, y)
                    break
            if mejor:
                break
        if mejor:
            o.location.x, o.location.y = mejor
            print("MOVIDO", n, "a", tuple(round(v, 1) for v in mejor))
for o in raices:
    anfitrion = bpy.data.objects[SEGUIDORES[o.name]] if o.name in SEGUIDORES else o
    g = suelo(anfitrion.location.x, anfitrion.location.y)
    if "Puzle3_InteriorFaro" in [c.name for c in o.users_collection]:
        g = suelo(5.2, 70.3)          # todo el interior de la cabana comparte un mismo suelo
    o.location.z = o["z_base"] + (g if g is not None else 0.0)
    print("ASENTADO", o.name, "suelo", None if g is None else round(g, 1))

# ---- el faro: cuelga de un empty en el origen; luego se gira, se lleva a su sitio y se apoya sobre la isla
for o in faro:
    o.parent = raiz
raiz.rotation_euler.z = math.radians(FARO_ROT_Z)
raiz.location = (FARO_XY[0], FARO_XY[1], 0.0)
bpy.context.view_layer.update()
zsuelo = suelo(FARO_XY[0], FARO_XY[1])
if zsuelo is None:
    zsuelo = ISLA_Z + 11
mn = min((o.matrix_world @ Vector(c)).z for o in faro if o.type == 'MESH' for c in o.bound_box)
raiz.location.z = zsuelo - mn
for n in ("Ref_Mapa_Isla", "Ref_Plano_Cabana"):
    if n in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("ISLA OK suelo del faro:", round(zsuelo, 1))
