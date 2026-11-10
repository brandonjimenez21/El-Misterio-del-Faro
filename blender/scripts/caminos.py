# Crea los caminos de la isla como CURVAS editables (coleccion "Caminos") segun el texto:
#   Camino_Principal      : sendero de tierra del muelle hasta la puerta de la cabana (lo corta la roca del puzle 2)
#   Camino_Cueva          : sendero antiguo que baja a una cueva en la costa (se revela con la luz del faro)
#   Camino_Puente         : camino hacia la costa donde arranca el puente de piedra a la isleta lejana
#   Camino_Farero         : huellas del farero que terminan al borde de un embarcadero secundario
# Cada curva tiene propiedades personalizadas: "ancho" (m) e "intensidad" (0-1).
# Puedes mover los puntos de control de las curvas en Blender y luego ejecutar texturizar_isla.py para hornearlos en la isla.
import bpy, math
from mathutils import Vector

S = bpy.context.scene
I = bpy.data.objects["IslandModel"]
bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()


def suelo(x, y):
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    return (I.matrix_world @ l).z if h else None


def borde(x0, y0, dx, dy, minimo=3.5, paso=1.0, maximo=120):
    """camina desde (x0,y0) en la direccion dada hasta el borde de la meseta y devuelve el ultimo punto firme"""
    d = Vector((dx, dy)).normalized()
    ult = (x0, y0)
    for k in range(1, int(maximo / paso)):
        x, y = x0 + d.x * k * paso, y0 + d.y * k * paso
        g = suelo(x, y)
        if g is None or g < minimo:
            break
        ult = (x, y)
    return ult


# limpiar
col = bpy.data.collections.get("Caminos")
if col:
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("Caminos")
    S.collection.children.link(col)
for c in list(bpy.data.curves):
    if c.users == 0:
        bpy.data.curves.remove(c)


def curva(nombre, pts, ancho, intensidad):
    cu = bpy.data.curves.new(nombre, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 0.0
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for bp, (x, y) in zip(sp.bezier_points, pts):
        g = suelo(x, y)
        bp.co = (x, y, (g if g is not None else 5.5) + 0.25)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(nombre, cu)
    o["ancho"] = ancho
    o["intensidad"] = intensidad
    o.color = (0.9, 0.6, 0.1, 1)
    col.objects.link(o)
    return o


def marcador(nombre, xy):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_type = 'SPHERE'
    e.empty_display_size = 1.5
    g = suelo(*xy)
    e.location = (xy[0], xy[1], (g if g is not None else 5.5))
    col.objects.link(e)


# ---- camino principal: del muelle a la puerta de la cabana, pasando por las zonas de los puzles 1 y 2
PRINCIPAL = [(0.0, -16.0), (0.4, -6.0), (0.8, 6.0), (1.6, 18.0), (0.8, 30.0), (-0.8, 42.0), (-1.5, 50.5),
             (3.0, 58.5), (5.5, 67.0), (9.0, 75.0), (11.0, 82.0), (8.5, 86.5), (4.6, 87.3)]
curva("Camino_Principal", PRINCIPAL, 2.4, 1.0)

# ---- caminos secundarios: nacen del principal y acaban al borde de la costa
fin_c = borde(-0.8, 30.0, -1.0, -0.25)
curva("Camino_Cueva", [(-0.8, 30.0), (-0.8 + (fin_c[0] + 0.8) * 0.35, 30.0 + (fin_c[1] - 30) * 0.35 + 1.6),
                      (-0.8 + (fin_c[0] + 0.8) * 0.7, 30.0 + (fin_c[1] - 30) * 0.7 - 1.2), fin_c], 1.3, 0.75)
marcador("Punto_Cueva", fin_c)
fin_p = borde(1.6, 18.0, 1.0, 0.12)
curva("Camino_Puente", [(1.6, 18.0), (1.6 + (fin_p[0] - 1.6) * 0.35, 18.0 + (fin_p[1] - 18) * 0.35 - 1.2),
                       (1.6 + (fin_p[0] - 1.6) * 0.7, 18.0 + (fin_p[1] - 18) * 0.7 + 1.0), fin_p], 1.6, 0.75)
marcador("Punto_Puente_Isleta", fin_p)
fin_f = borde(9.0, 88.0, 1.0, 0.75)
curva("Camino_Farero", [(7.5, 88.0), (7.5 + (fin_f[0] - 7.5) * 0.35, 88.0 + (fin_f[1] - 88) * 0.35 + 1.0),
                       (7.5 + (fin_f[0] - 7.5) * 0.7, 88.0 + (fin_f[1] - 88) * 0.7 - 0.8), fin_f], 0.9, 0.6)
marcador("Punto_Embarcadero_Secundario", fin_f)

I["optimizada"] = True      # la malla ya esta reducida: texturizar_isla.py no la vuelve a reducir
for p in PRINCIPAL:
    print("SUELO", p, suelo(*p) and round(suelo(*p), 1))
print("FINES cueva", tuple(round(v, 1) for v in fin_c), "puente", tuple(round(v, 1) for v in fin_p), "farero", tuple(round(v, 1) for v in fin_f))
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("CAMINOS OK")
