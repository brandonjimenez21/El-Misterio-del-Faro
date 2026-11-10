# Escalera de caracol v2: el arranque ya no tapa la puerta de la torre (primera vuelta libre delante de la puerta),
# sube hasta un descansillo metalico y termina en una trampilla metalica con huecos en el piso de la sala de la linterna.
import bpy, bmesh, math
from mathutils import Vector, Matrix

S = bpy.context.scene
if S.get("altura_trampilla"):
    raise SystemExit("ya aplicado")
O = bpy.data.objects
bpy.context.view_layer.update()
U = Vector((0.8, 0.6))
GIRO = math.degrees(math.atan2(U.y, U.x))
TC = Vector((-6.64, 89.52))
PISO = 7.37
RAIZ = O["Faro_Cabana_Raiz"]
COL = bpy.data.collections["Faro_Cabana"]
DECK = O["Cube.010"]
DECK_Z0, DECK_Z1 = 46.06, 46.56          # grosor del piso de la linterna (medido)

for n in ("Escalera_Torre_Peldanos", "Escalera_Torre_Baranda", "Escalera_Torre_Descansillo", "Escalera_Torre_Escala"):
    if n in O:
        me = O[n].data
        bpy.data.objects.remove(O[n], do_unlink=True)
        bpy.data.meshes.remove(me)


def mat(nombre, color, rough=0.8, metal=0.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def nuevo(nombre, bm, material):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(nombre, me)
    COL.objects.link(o)
    o.parent = RAIZ
    o.matrix_parent_inverse = RAIZ.matrix_world.inverted()      # la malla esta en coordenadas del mundo
    me.materials.append(material)
    return o


def caja(bm, p0, p1, g=0.03):
    d = p1 - p0
    if d.length < 1e-6:
        return
    z = d.normalized()
    ref = Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((1, 0, 0))
    x = z.cross(ref).normalized() * g
    y = z.cross(x).normalized() * g
    vs = []
    for p in (p0, p1):
        for (sx, sy) in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            vs.append(bm.verts.new(p + x * sx + y * sy))
    a, b = vs[:4], vs[4:]
    for k in range(4):
        bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)


# ------------------------------------------------ parametros
RAD_IN, RAD_OUT = 0.55, 5.2
SUBIDA = 0.30
N_VUELTA = 24
ALTURA_LIBRE = 2.6                             # altura libre de una persona bajo el piso de la linterna
Z_LAND = DECK_Z0 - ALTURA_LIBRE - SUBIDA
n = int((Z_LAND - PISO) / SUBIDA)
dth = 2 * math.pi / N_VUELTA
# el primer peldano empieza justo DESPUES del arco de la puerta (puerta = direccion GIRO), asi delante de ella
# la escalera esta a mas de 4 m de altura cuando vuelve a pasar
th0 = math.radians(GIRO + 40)
th_fin = th0 + dth * (n - 1)

# ------------------------------------------------ peldanos
bm = bmesh.new()
for i in range(n):
    z = PISO + SUBIDA * (i + 1)
    th = th0 + dth * i
    th2 = th + dth * 1.25
    vs = []
    for zz in (z, z - 0.20):
        for (r, tt) in ((RAD_IN, th), (RAD_OUT, th), (RAD_OUT, th2), (RAD_IN, th2)):
            vs.append(bm.verts.new((TC.x + r * math.cos(tt), TC.y + r * math.sin(tt), zz)))
    top, bot = vs[:4], vs[4:]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for k in range(4):
        bm.faces.new((top[k], top[(k + 1) % 4], bot[(k + 1) % 4], bot[k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
nuevo("Escalera_Torre_Peldanos", bm, mat("Escalera_Madera", (0.16, 0.10, 0.06), 0.85))

# ------------------------------------------------ barandilla
bm = bmesh.new()
RB = RAD_OUT - 0.12
prev = None
for i in range(0, n, 2):
    tt = th0 + dth * i + dth * 0.6
    zb = PISO + SUBIDA * (i + 1)
    base = Vector((TC.x + RB * math.cos(tt), TC.y + RB * math.sin(tt), zb))
    arriba = base + Vector((0, 0, 0.95))
    caja(bm, base, arriba, 0.03)
    if prev is not None:
        caja(bm, prev, arriba, 0.025)
    prev = arriba
nuevo("Escalera_Torre_Baranda", bm, mat("Escalera_Hierro", (0.07, 0.07, 0.08), 0.6, 0.7))

# ------------------------------------------------ descansillo metalico (sector de reja)
bm = bmesh.new()
th_a = th_fin + dth * 0.5
th_b = th_a + math.radians(52)
seg = 8
anillo = []
for k in range(seg + 1):
    tt = th_a + (th_b - th_a) * k / seg
    anillo.append(((RAD_IN, tt), (RAD_OUT, tt)))
for zz in (Z_LAND, Z_LAND - 0.12):
    pass
top = []
bot = []
for (pi, po) in anillo:
    top.append((bm.verts.new((TC.x + pi[0] * math.cos(pi[1]), TC.y + pi[0] * math.sin(pi[1]), Z_LAND + SUBIDA)),
                bm.verts.new((TC.x + po[0] * math.cos(po[1]), TC.y + po[0] * math.sin(po[1]), Z_LAND + SUBIDA))))
    bot.append((bm.verts.new((TC.x + pi[0] * math.cos(pi[1]), TC.y + pi[0] * math.sin(pi[1]), Z_LAND + SUBIDA - 0.12)),
                bm.verts.new((TC.x + po[0] * math.cos(po[1]), TC.y + po[0] * math.sin(po[1]), Z_LAND + SUBIDA - 0.12))))
for k in range(seg):
    bm.faces.new((top[k][0], top[k][1], top[k + 1][1], top[k + 1][0]))
    bm.faces.new((bot[k][0], bot[k + 1][0], bot[k + 1][1], bot[k][1]))
    bm.faces.new((top[k][1], bot[k][1], bot[k + 1][1], top[k + 1][1]))
    bm.faces.new((top[k][0], top[k + 1][0], bot[k + 1][0], bot[k][0]))
bm.faces.new((top[0][0], bot[0][0], bot[0][1], top[0][1]))
bm.faces.new((top[-1][0], top[-1][1], bot[-1][1], bot[-1][0]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
nuevo("Escalera_Torre_Descansillo", bm, mat("Escalera_Hierro", (0.07, 0.07, 0.08), 0.6, 0.7))


HC = Vector((-7.79, 92.61))
tt_h = math.atan2(HC.y - TC.y, HC.x - TC.x)
rad = Vector((math.cos(tt_h), math.sin(tt_h)))
tan = Vector((-rad.y, rad.x))
rad3 = Vector((rad.x, rad.y, 0))
tan3 = Vector((tan.x, tan.y, 0))
LADO = 1.5
Z_LAND_TOP = Z_LAND + SUBIDA
hierro = mat("Escalera_Hierro", (0.07, 0.07, 0.08), 0.6, 0.7)
# ------------------------------------------------ escala de gato (hierro) del descansillo a la trampilla
bm = bmesh.new()
cara_int = HC - rad * (LADO / 2)                  # borde de la trampilla hacia la columna
z_base = Z_LAND_TOP
z_alto = DECK_Z0                                  # el barrote superior queda al nivel de la trampilla
inclina = 0.35                                    # desplazamiento horizontal de la base (escala casi vertical)
top_c = Vector((cara_int.x, cara_int.y, z_alto)) - rad3 * 0.10
base_c = top_c - rad3 * inclina
base_c.z = z_base
for s_ in (-1, 1):
    p0 = base_c + tan3 * (s_ * 0.28)
    p1 = top_c + tan3 * (s_ * 0.28)
    caja(bm, p0, p1 + Vector((0, 0, DECK_Z1 - DECK_Z0 + 0.9)), 0.03)     # largueros, sobresalen 0,9 m sobre el piso
n_pel = int((z_alto - z_base) / 0.30)
for i in range(1, n_pel + 1):
    t = i / (n_pel + 0.5)
    pa = base_c.lerp(top_c, t)
    caja(bm, pa - tan3 * 0.28, pa + tan3 * 0.28, 0.02)
nuevo("Escalera_Torre_Escala", bm, hierro)


S["altura_trampilla"] = 1
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("ALTURA OK libre", ALTURA_LIBRE, "peldanos", n, "descansillo top", round(Z_LAND_TOP, 2))
