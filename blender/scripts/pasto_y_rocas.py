# Pasto y rocas sueltas de la isla (ligeros). Coleccion "Vegetacion_Isla":
#   Pasto_i_j   : mechones de hierba (1 triangulo por hoja, 7 hojas por mechon) agrupados en bloques de 24 m
#                 para que Unity los descarte por distancia/vista. UV0 = (tinte aleatorio, altura 0..1) para el viento y el color.
#   Roca_i_j    : cantos y bloques de baja resolucion (alrededor de los "dedos" de roca, la costa y los postes),
#                 tambien en bloques.
# Uso: blender -b archivo.blend --python pasto_y_rocas.py -- [--save]
import bpy, bmesh, math, random, sys
from mathutils import Vector, Matrix

S = bpy.context.scene
I = bpy.data.objects["IslandModel"]
bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
R = random.Random(21)
PI = math.pi
NIVEL_MAR = -0.55
CELDA = 24.0
N_PASTO = 11000
N_ROCAS_BASE = 190
N_ROCAS_COSTA = 90


def suelo(x, y):
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    if not h:
        return None, None
    nw = (I.matrix_world.to_3x3() @ n).normalized()
    return (I.matrix_world @ l).z, nw


col = bpy.data.collections.get("Vegetacion_Isla")
if col:
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("Vegetacion_Isla")
    S.collection.children.link(col)


def mat(nombre, color, rough):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*color, 1)
    return m

M_PASTO = mat("M_Pasto", (0.08, 0.12, 0.03), 0.9)
M_ROCA = mat("M_RocaIsla", (0.44, 0.47, 0.52), 0.95)   # claro: las rocas sueltas salian casi negras de noche
# aspecto de roca en Blender (grietas + manchas + relieve). En Unity lo da el shader Faro/IslaDetalle; esto solo es para verlas bien aqui.
def roca_procedural(m):
    nt = m.node_tree
    if False:
        return
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ruido = nt.nodes.new('ShaderNodeTexNoise'); ruido.inputs["Scale"].default_value = 6.0; ruido.inputs["Detail"].default_value = 8.0
    ruido.name = "RocaProc"
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs["Scale"].default_value = 3.0
    rampa = nt.nodes.new('ShaderNodeValToRGB')
    rampa.color_ramp.elements[0].position = 0.35; rampa.color_ramp.elements[0].color = (0.2, 0.21, 0.24, 1)
    rampa.color_ramp.elements[1].position = 0.7; rampa.color_ramp.elements[1].color = (0.56, 0.59, 0.64, 1)
    grieta = nt.nodes.new('ShaderNodeMath'); grieta.operation = 'MULTIPLY'; grieta.inputs[1].default_value = 3.0
    mezcla = nt.nodes.new('ShaderNodeMix'); mezcla.data_type = 'RGBA'; mezcla.blend_type = 'MULTIPLY'; mezcla.inputs[0].default_value = 1.0
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs["Strength"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], ruido.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    nt.links.new(ruido.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(vor.outputs["Distance"], grieta.inputs[0])
    nt.links.new(rampa.outputs["Color"], mezcla.inputs[6])
    g2 = nt.nodes.new('ShaderNodeMath'); g2.operation = 'MINIMUM'; g2.inputs[1].default_value = 1.0
    nt.links.new(grieta.outputs[0], g2.inputs[0])
    gc = nt.nodes.new('ShaderNodeCombineColor')
    for k in ("Red", "Green", "Blue"):
        nt.links.new(g2.outputs[0], gc.inputs[k])
    nt.links.new(gc.outputs["Color"], mezcla.inputs[7])
    nt.links.new(mezcla.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(ruido.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = (0.4, 0.42, 0.46, 1)
roca_procedural(M_ROCA)

# ---------------------------------------------------------------- zonas a evitar
camino = [(0.0, -34.6), (0.5, -21.6), (1.0, -6.0), (2.1, 9.6), (1.0, 25.2), (-1.0, 40.8), (-1.9, 51.8), (3.9, 62.2), (7.1, 73.3), (11.7, 83.7), (14.3, 92.8), (11.0, 98.6), (6.0, 99.7)]
extra = [[(-1.0, 25.2), (-16.0, 23.5), (-31.1, 16.1), (-43.9, 14.5)], [(2.1, 9.6), (14.7, 9.6), (27.4, 13.9), (38.2, 13.9)], [(9.8, 100.6), (11.9, 103.0), (14.0, 101.7), (15.9, 103.7)]]
def polilinea(pts, paso=1.0):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        a, b = Vector(a), Vector(b)
        n = max(1, int((b - a).length / paso))
        for k in range(n):
            out.append(a.lerp(b, k / n))
    out.append(Vector(pts[-1]))
    return out
linea = polilinea(camino)
for e in extra:
    linea += polilinea(e)
def dist_camino(x, y):
    p = Vector((x, y))
    return min((p - q).length for q in linea)

fijos = [((-6.8, 91.5), 14.5), ((13.4, 30.8), 2.6), ((-24.7, 1.7), 2.6), ((-41.6, 42.7), 2.6), ((-23.7, 9.4), 3.0),
         ((36.4, 15.8), 5.5), ((-2.0, 54.6), 7.2), ((-18.2, 49.9), 6.0), ((0, -36), 4.5)]
def libre(x, y, margen=0.0):
    return not any((Vector((x, y)) - Vector(c)).length < r + margen for c, r in fijos)


# ---------------------------------------------------------------- PASTO
def mechon(bm, c, n, tinte, esc):
    hojas = R.randint(6, 8)
    for k in range(hojas):
        ang = 2 * PI * k / hojas + R.uniform(-0.4, 0.4)
        d = Vector((math.cos(ang), math.sin(ang), 0))
        t = Vector((-d.y, d.x, 0))
        alto = R.uniform(0.32, 0.62) * esc
        ancho = R.uniform(0.06, 0.095) * esc
        inc = R.uniform(0.25, 0.7)
        r0 = R.uniform(0.0, 0.07) * esc
        b0 = c + d * r0
        tip = b0 + d * (alto * inc) + Vector((0, 0, alto * (1 - 0.35 * inc)))
        v0 = bm.verts.new(b0 - t * ancho)
        v1 = bm.verts.new(b0 + t * ancho)
        v2 = bm.verts.new(tip)
        f = bm.faces.new((v0, v1, v2))
        uvl = bm.loops.layers.uv.verify()
        for lp, hh in zip(f.loops, (0.0, 0.0, 1.0)):
            lp[uvl].uv = (tinte, hh)

celdas = {}
puestos = 0
intentos = 0
while puestos < N_PASTO and intentos < N_PASTO * 6:
    intentos += 1
    x, y = R.uniform(-62, 58), R.uniform(-34, 118)
    g, n = suelo(x, y)
    if g is None or g < 2.6 or n.z < 0.9:
        continue
    if dist_camino(x, y) < 1.9 or not libre(x, y):
        continue
    key = (int(math.floor(x / CELDA)), int(math.floor(y / CELDA)))
    if key not in celdas:
        celdas[key] = bmesh.new()
    mechon(celdas[key], Vector((x, y, g - 0.03)), n, R.random(), R.uniform(0.8, 1.25))
    puestos += 1
tris = 0
for (i, j), bm in celdas.items():
    me = bpy.data.meshes.new("Pasto_%d_%d" % (i, j))
    bm.to_mesh(me)
    tris += len(me.polygons)
    bm.free()
    me.materials.append(M_PASTO)
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new("Pasto_%d_%d" % (i, j), me)
    col.objects.link(ob)
print("VEG pasto mechones", puestos, "bloques", len(celdas), "tris", tris)


# ---------------------------------------------------------------- ROCAS SUELTAS
def canto(bm, c, tam, achatado):
    r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    vs = r["verts"]
    ejes = Vector((R.uniform(0.8, 1.4), R.uniform(0.8, 1.4), achatado))
    rot = Matrix.Rotation(R.uniform(0, 2 * PI), 3, 'Z')
    for v in vs:
        k = 1.0 + R.uniform(-0.28, 0.28)                       # facetas irregulares
        v.co = rot @ Vector((v.co.x * ejes.x * k, v.co.y * ejes.y * k, v.co.z * ejes.z * k)) * tam + c
    for v in vs:
        v.co.z = max(v.co.z, c.z - tam * 0.25)                  # base hundida en el suelo


rocas = {}
n_r = 0
def poner_roca(x, y, g, tam, achat):
    global n_r
    key = (int(math.floor(x / CELDA)), int(math.floor(y / CELDA)))
    if key not in rocas:
        rocas[key] = bmesh.new()
    canto(rocas[key], Vector((x, y, g)), tam, achat)
    n_r += 1

# 1) al pie de los "dedos" y las laderas: puntos donde el terreno se endereza tras una pendiente
tot, intentos = 0, 0
while tot < N_ROCAS_BASE and intentos < 40000:
    intentos += 1
    x, y = R.uniform(-66, 62), R.uniform(-34, 120)
    g, n = suelo(x, y)
    if g is None or g < 1.5 or not (0.6 < n.z < 0.93):
        continue
    if y < -10 or dist_camino(x, y) < 4.0 or not libre(x, y, 1.0):
        continue                                              # y < -10: no tapar la entrada del muelle
    poner_roca(x, y, g, R.choice((0.35, 0.5, 0.7, 0.9, 1.3, 1.8)) * R.uniform(0.8, 1.2), R.uniform(0.5, 0.9))
    tot += 1
# 2) en la costa (cerca del agua)
tot, intentos = 0, 0
while tot < N_ROCAS_COSTA and intentos < 40000:
    intentos += 1
    x, y = R.uniform(-80, 76), R.uniform(-45, 130)
    g, n = suelo(x, y)
    if g is None or g < NIVEL_MAR - 0.4 or g > 1.3:
        continue
    if abs(x) < 7 and y < -30:
        continue                                              # no tapar el muelle
    poner_roca(x, y, g, R.choice((0.4, 0.6, 0.9, 1.4, 2.0)) * R.uniform(0.8, 1.2), R.uniform(0.45, 0.8))
    tot += 1
rt = 0
for (i, j), bm in rocas.items():
    for f in bm.faces:
        f.smooth = False
    me = bpy.data.meshes.new("Roca_%d_%d" % (i, j))
    bm.to_mesh(me)
    rt += len(me.polygons)
    bm.free()
    me.materials.append(M_ROCA)
    ob = bpy.data.objects.new("Roca_%d_%d" % (i, j), me)
    col.objects.link(ob)
print("VEG rocas", n_r, "bloques", len(rocas), "tris", rt)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
