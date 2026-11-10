# 1) Puerta de Lighthouse.blend -> entrada a la torre (pared de la torre que da a la cabana), con hueco cortado.
# 2) Escalera de caracol dentro de la torre (columna + peldanos + barandilla) hasta la sala de la linterna.
# 3) Candado en la puerta ORIGINAL del portal de la cabana.
# 4) Interior de la cabana reorganizado (las dos mesas juntas en la pared norte, reloj y cuadro encima).
# Marco de la cabana: CC centro, U hacia la entrada, W perpendicular. Se aplica una sola vez.
import bpy, bmesh, math
from mathutils import Vector, Matrix

S = bpy.context.scene
if S.get("escalera_torre"):
    raise SystemExit("ya aplicado")
O = bpy.data.objects
bpy.context.view_layer.update()
CC = Vector((1.82, 95.01))
U = Vector((0.8, 0.6))
W = Vector((0.6, -0.8))
GIRO = math.degrees(math.atan2(U.y, U.x))
TC = Vector((-6.64, 89.52))            # centro de la torre
PISO = 7.37                            # piso de la cabana y de la torre


def P(a, b):
    return CC + U * a + W * b


RAIZ = O["Faro_Cabana_Raiz"]
COL = bpy.data.collections["Faro_Cabana"]
TORRE = O["Cylinder"]


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
    o.matrix_parent_inverse.identity()
    me.materials.append(material)
    return o


# ------------------------------------------------ 1) hueco en la torre y en el muro interior
HB = -0.68
ANCHO = 1.7
Z0 = PISO + 0.08
Z1 = PISO + 2.7
bm = bmesh.new()
bm.from_mesh(TORRE.data)
mw = TORRE.matrix_world
borrar = []
for f in bm.faces:
    c = mw @ f.calc_center_median()
    rel = Vector((c.x, c.y)) - TC
    s = rel.dot(U)
    b = (Vector((c.x, c.y)) - CC).dot(W)
    if s > 5.0 and abs(b - HB) < ANCHO / 2 and Z0 < c.z < Z1:
        borrar.append(f)
bmesh.ops.delete(bm, geom=borrar, context='FACES')
bm.to_mesh(TORRE.data)
bm.free()
print("HUECO TORRE caras borradas", len(borrar))

pl = O["Faro_Plane.004"]
mwp = pl.matrix_world
bm = bmesh.new()
bm.from_mesh(pl.data)
objetivo = None
for f in bm.faces:
    pts = [mwp @ v.co for v in f.verts]
    az = [(Vector((p.x, p.y)) - CC).dot(U) for p in pts]
    if len(pts) == 4 and max(abs(a + 4.0) for a in az) < 0.8 and min(p.z for p in pts) < PISO + 0.2 and max(p.z for p in pts) > PISO + 3:
        objetivo = f
        break
if objetivo:
    q = [mwp @ v.co for v in objetivo.verts]
    q.sort(key=lambda p: ((Vector((p.x, p.y)) - CC).dot(W), p.z))
    lo = sorted(q[:2], key=lambda p: p.z)
    hi = sorted(q[2:], key=lambda p: p.z)

    def punto(u, v):
        a = lo[0].lerp(hi[0], u)
        c2 = lo[1].lerp(hi[1], u)
        return a.lerp(c2, v)

    b0 = (Vector((lo[0].x, lo[0].y)) - CC).dot(W)
    b1 = (Vector((hi[0].x, hi[0].y)) - CC).dot(W)
    ua = (HB - ANCHO / 2 - b0) / (b1 - b0)
    ub = (HB + ANCHO / 2 - b0) / (b1 - b0)
    zlo = lo[0].z
    zhi = lo[1].z
    va = (Z0 - zlo) / (zhi - zlo)
    vb = (Z1 - zlo) / (zhi - zlo)
    inv = mwp.inverted()
    bmesh.ops.delete(bm, geom=[objetivo], context='FACES_ONLY')
    ps = {}
    for i, u in enumerate((0.0, ua, ub, 1.0)):
        for j, v in enumerate((0.0, max(va, 0.0), vb, 1.0)):
            ps[(i, j)] = bm.verts.new(inv @ punto(u, v))
    for (i0, j0, i1, j1) in ((0, 0, 1, 3), (2, 0, 3, 3), (1, 2, 2, 3)):
        bm.faces.new((ps[(i0, j0)], ps[(i1, j0)], ps[(i1, j1)], ps[(i0, j1)]))
    bm.to_mesh(pl.data)
    bm.free()
    print("HUECO MURO OK")
else:
    bm.free()
    print("MURO: no se encontro el cuadrilatero")

# ------------------------------------------------ 2) puerta de la torre
puerta = [O[n] for n in ("PuertaVar2_Cuerpo", "PuertaVar2_Marco", "PuertaVar2_Tablas", "PuertaVar2_Clavos", "PuertaVar2_Herraje")]
pts = [o.matrix_world @ v.co for o in puerta for v in o.data.vertices]
cx = (min(p.x for p in pts) + max(p.x for p in pts)) / 2
cy = (min(p.y for p in pts) + max(p.y for p in pts)) / 2
zmin = min(p.z for p in pts)
b_puerta_vieja = (Vector((cx, cy)) - CC).dot(W)
destino = P(-2.29, HB)
for o in puerta:
    m = o.matrix_world.copy()
    m.translation += Vector((destino.x - cx, destino.y - cy, PISO + 0.03 - zmin))
    o.matrix_world = m

# ------------------------------------------------ 3) candado en la puerta original del portal
cand = O["Candado_Cuerpo"]
bb = [cand.matrix_world @ Vector(c) for c in cand.bound_box]
cb = sum(bb, Vector()) / 8
a_c = (Vector((cb.x, cb.y)) - CC).dot(U)
nxy = P(a_c, b_puerta_vieja + 0.79)
cand.location += Vector((nxy.x - cb.x, nxy.y - cb.y, 8.95 - cb.z))

# ------------------------------------------------ 4) escalera de caracol
RAD_IN, RAD_OUT = 0.55, 5.2
Z_TOP = 45.4
SUBIDA = 0.30
N_VUELTA = 24
n = int((Z_TOP - PISO) / SUBIDA)
dth = 2 * math.pi / N_VUELTA
th0 = math.radians(GIRO - 80)
bm = bmesh.new()
for i in range(n):
    z = PISO + SUBIDA * (i + 1)
    th = th0 + dth * i
    th2 = th + dth * 1.25
    vs = []
    for zz in (z, z - 0.20):
        for (r, tt) in ((RAD_IN, th), (RAD_OUT, th), (RAD_OUT, th2), (RAD_IN, th2)):
            vs.append(bm.verts.new((TC.x + r * math.cos(tt), TC.y + r * math.sin(tt), zz)))
    top = vs[:4]
    bot = vs[4:]
    bm.faces.new(top)
    bm.faces.new(bot[::-1])
    for k in range(4):
        bm.faces.new((top[k], top[(k + 1) % 4], bot[(k + 1) % 4], bot[k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
nuevo("Escalera_Torre_Peldanos", bm, mat("Escalera_Madera", (0.16, 0.10, 0.06), 0.85))

bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.5, radius2=0.5, depth=Z_TOP - PISO + 0.4,
                      matrix=Matrix.Translation((TC.x, TC.y, (Z_TOP + PISO) / 2)))
nuevo("Escalera_Torre_Columna", bm, mat("Escalera_Hierro", (0.07, 0.07, 0.08), 0.6, 0.7))

# barandilla: postes + pasamanos como tubos finos (cajas delgadas)
bm = bmesh.new()
RB = RAD_OUT - 0.12


def caja(bm, p0, p1, g=0.03):
    d = p1 - p0
    l = d.length
    if l < 1e-6:
        return
    z = d.normalized()
    ref = Vector((0, 0, 1)) if abs(z.z) < 0.9 else Vector((1, 0, 0))
    x = z.cross(ref).normalized() * g
    y = z.cross(x).normalized() * g
    vs = []
    for p in (p0, p1):
        for (sx, sy) in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            vs.append(bm.verts.new(p + x * sx + y * sy))
    a = vs[:4]
    b = vs[4:]
    for k in range(4):
        bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(a[::-1])
    bm.faces.new(b)


prev = None
for i in range(0, n + 1, 2):
    tt = th0 + dth * i + dth * 0.6
    zb = PISO + SUBIDA * (i + 1)
    base = Vector((TC.x + RB * math.cos(tt), TC.y + RB * math.sin(tt), zb))
    arriba = base + Vector((0, 0, 0.95))
    caja(bm, base, arriba, 0.03)
    if prev is not None:
        caja(bm, prev, arriba, 0.025)
    prev = arriba
nuevo("Escalera_Torre_Baranda", bm, mat("Escalera_Hierro", (0.07, 0.07, 0.08), 0.6, 0.7))

# el segundo piso prototipo (disco en la torre) estorba a la escalera
if "Faro_Plane.003" in O:
    bpy.data.objects.remove(O["Faro_Plane.003"], do_unlink=True)


# ------------------------------------------------ 5) interior de la cabana
def mover(nombre, a, b, yaw=None, seguidores=()):
    o = O[nombre]
    x0, y0 = o.location.x, o.location.y
    dd = (math.radians(yaw) - o.rotation_euler.z) if yaw is not None else 0.0
    foll = [(O[f], Vector((O[f].location.x - x0, O[f].location.y - y0))) for f in seguidores]
    p = P(a, b)
    if yaw is not None:
        o.rotation_euler.z = math.radians(yaw)
    o.location.x, o.location.y = p.x, p.y
    R = Matrix.Rotation(dd, 2)
    for f, rel in foll:
        r = R @ rel
        f.location.x, f.location.y = p.x + r.x, p.y + r.y
        f.rotation_euler.z += dd


yaw_mesa = math.degrees(O["Mesa_Trabajo"].rotation_euler.z)
mover("Mesa_Trabajo", -1.6, -3.6, None, ("Caja_Cerillas", "Taza_Derramada"))
mover("Mesa_Navegacion", 0.9, -3.6, yaw_mesa, ("Mapa_Costa", "Bitacora_Farero"))
mover("Reloj_Pared", -1.6, -4.68, None, ("Reloj_Manecilla_Hora", "Reloj_Manecilla_Minutero"))
mover("Cuadro_Torcido", 0.9, -4.68)

S["escalera_torre"] = 1
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("ESCALERA OK peldanos", n)
