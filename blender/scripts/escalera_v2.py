# Escalera de caracol v2: el arranque ya no tapa la puerta de la torre (primera vuelta libre delante de la puerta),
# sube hasta un descansillo metalico y termina en una trampilla metalica con huecos en el piso de la sala de la linterna.
import bpy, bmesh, math
from mathutils import Vector, Matrix

S = bpy.context.scene
if S.get("escalera_v2"):
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

for n in ("Escalera_Torre_Peldanos", "Escalera_Torre_Columna", "Escalera_Torre_Baranda"):
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
Z_LAND = DECK_Z0 - 2.3                       # descansillo: 2,3 m de altura libre bajo el piso de la linterna
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

# ------------------------------------------------ columna central (hasta el piso de la linterna)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.5, radius2=0.5, depth=DECK_Z0 - PISO,
                      matrix=Matrix.Translation((TC.x, TC.y, (DECK_Z0 + PISO) / 2)))
nuevo("Escalera_Torre_Columna", bm, mat("Escalera_Hierro", (0.07, 0.07, 0.08), 0.6, 0.7))

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

# ------------------------------------------------ hueco en el piso de la linterna + trampilla metalica con huecos
tt_h = (th_a + th_b) / 2
R_H = 3.3
HC = Vector((TC.x + R_H * math.cos(tt_h), TC.y + R_H * math.sin(tt_h)))       # centro del hueco
LADO = 1.25
rad = Vector((math.cos(tt_h), math.sin(tt_h)))
tan = Vector((-rad.y, rad.x))

bm = bmesh.new()
bm.from_mesh(DECK.data)
bm.transform(DECK.matrix_world)


def corta(pto, nor):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=pto, plane_no=nor, clear_inner=False, clear_outer=False)


for s_ in (-1, 1):
    corta(Vector((HC.x, HC.y, 0)) + Vector((rad.x, rad.y, 0)) * (s_ * LADO / 2), Vector((rad.x, rad.y, 0)))
    corta(Vector((HC.x, HC.y, 0)) + Vector((tan.x, tan.y, 0)) * (s_ * LADO / 2), Vector((tan.x, tan.y, 0)))
borrar = []
for f in bm.faces:
    c = f.calc_center_median()
    d = Vector((c.x, c.y)) - HC
    if abs(d.dot(rad)) < LADO / 2 and abs(d.dot(tan)) < LADO / 2 and DECK_Z0 - 0.05 < c.z < DECK_Z1 + 0.05:
        borrar.append(f)
bmesh.ops.delete(bm, geom=borrar, context='FACES')
bm.transform(DECK.matrix_world.inverted())
bm.to_mesh(DECK.data)
bm.free()
DECK.data.update()
print("HUECO LINTERNA caras", len(borrar))

hierro = mat("Escalera_Hierro", (0.07, 0.07, 0.08), 0.6, 0.7)
# marco (manguito de chapa que reviste el hueco) + placa perforada + argolla + bisagras
bm = bmesh.new()
h0, h1 = DECK_Z0, DECK_Z1
for s_ in (-1, 1):
    for (axis, other) in ((rad, tan), (tan, rad)):
        c = Vector((HC.x, HC.y, 0)) + Vector((axis.x, axis.y, 0)) * (s_ * (LADO / 2 + 0.02))
        a = c - Vector((other.x, other.y, 0)) * (LADO / 2 + 0.04) + Vector((0, 0, h0))
        b = c + Vector((other.x, other.y, 0)) * (LADO / 2 + 0.04) + Vector((0, 0, h0))
        for z in (h0 + 0.02, (h0 + h1) / 2, h1 - 0.02):
            caja(bm, Vector((a.x, a.y, z)), Vector((b.x, b.y, z)), 0.02)
nuevo("Trampilla_Marco", bm, hierro)

NH = 5
paso = LADO / NH
rad_h = paso * 0.30
zp = h1 + 0.015
GROS = 0.05

# placa solida + Boolean (diferencia) con cilindros -> huecos reales
bm = bmesh.new()
cen = Vector((HC.x, HC.y, zp - GROS / 2))
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co = Vector((v.co.x * LADO, v.co.y * LADO, v.co.z * GROS))
# orientar al angulo del hueco
rot = Matrix.Rotation(tt_h, 4, 'Z')
bmesh.ops.transform(bm, matrix=Matrix.Translation(cen) @ rot, verts=bm.verts)
placa = nuevo("Trampilla_Placa", bm, hierro)
cil = []
for i in range(NH):
    for j in range(NH):
        cu = (i + 0.5 - NH / 2) * paso
        cv = (j + 0.5 - NH / 2) * paso
        c = Vector((HC.x, HC.y)) + rad * cu + tan * cv
        bmc = bmesh.new()
        bmesh.ops.create_cone(bmc, cap_ends=True, segments=14, radius1=rad_h, radius2=rad_h, depth=GROS * 3,
                              matrix=Matrix.Translation((c.x, c.y, zp - GROS / 2)))
        me = bpy.data.meshes.new("tmp_hueco")
        bmc.to_mesh(me)
        bmc.free()
        ob = bpy.data.objects.new("tmp_hueco", me)
        bpy.context.scene.collection.objects.link(ob)
        cil.append(ob)
# unir cilindros en uno solo y aplicar un solo Boolean
bpy.ops.object.select_all(action='DESELECT')
for ob in cil:
    ob.select_set(True)
bpy.context.view_layer.objects.active = cil[0]
bpy.ops.object.join()
cutter = bpy.context.active_object
placa.parent = None
placa.matrix_world = Matrix.Identity(4)
mod = placa.modifiers.new("Huecos", 'BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.solver = 'EXACT'
mod.object = cutter
bpy.context.view_layer.objects.active = placa
bpy.ops.object.modifier_apply(modifier="Huecos")
me_c = cutter.data
bpy.data.objects.remove(cutter, do_unlink=True)
bpy.data.meshes.remove(me_c)
placa.parent = RAIZ
placa.matrix_parent_inverse = RAIZ.matrix_world.inverted()

# argolla (asa) y bisagras
rad3 = Vector((rad.x, rad.y, 0))
tan3 = Vector((tan.x, tan.y, 0))
bm = bmesh.new()
asa_c = Vector((HC.x, HC.y, zp + 0.03)) + rad3 * (LADO * 0.28)
caja(bm, asa_c - tan3 * 0.09, asa_c + tan3 * 0.09, 0.012)
caja(bm, asa_c - tan3 * 0.09, asa_c - tan3 * 0.09 - Vector((0, 0, 0.03)), 0.012)
caja(bm, asa_c + tan3 * 0.09, asa_c + tan3 * 0.09 - Vector((0, 0, 0.03)), 0.012)
for s_ in (-0.3, 0.3):
    b0 = Vector((HC.x, HC.y, zp + 0.01)) - rad3 * (LADO / 2 - 0.02) + tan3 * (s_ * LADO)
    caja(bm, b0 - rad3 * 0.06, b0 + rad3 * 0.12, 0.025)
nuevo("Trampilla_Herrajes", bm, hierro)

# el segundo piso prototipo en la torre ya se quito; la escalera ya no toca la puerta
S["escalera_v2"] = 1
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("ESCALERA V2 OK peldanos", n, "z descansillo", round(Z_LAND, 2), "hueco en", round(HC.x, 2), round(HC.y, 2))
