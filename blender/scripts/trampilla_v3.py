# Escalera de caracol v2: el arranque ya no tapa la puerta de la torre (primera vuelta libre delante de la puerta),
# sube hasta un descansillo metalico y termina en una trampilla metalica con huecos en el piso de la sala de la linterna.
import bpy, bmesh, math
from mathutils import Vector, Matrix

S = bpy.context.scene
if S.get("trampilla_v3"):
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

for n in ("Trampilla_Marco", "Trampilla_Placa", "Trampilla_Herrajes", "Escalera_Torre_Escala"):
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



Z_LAND_TOP = DECK_Z0 - 2.0
dth = 2 * math.pi / 24
RAD_IN, RAD_OUT = 0.55, 5.2
HC = Vector((-7.79, 92.61))                      # centro de la trampilla (el mismo de antes)
tt_h = math.atan2(HC.y - TC.y, HC.x - TC.x)
rad = Vector((math.cos(tt_h), math.sin(tt_h)))
tan = Vector((-rad.y, rad.x))
rad3 = Vector((rad.x, rad.y, 0))
tan3 = Vector((tan.x, tan.y, 0))
LADO = 1.5                                       # abertura de 1,5 x 1,5 m: pasa una persona con holgura
hierro = mat("Escalera_Hierro", (0.07, 0.07, 0.08), 0.6, 0.7)

# ------------------------------------------------ agrandar el hueco del piso de la linterna
bm = bmesh.new()
bm.from_mesh(DECK.data)
bm.transform(DECK.matrix_world)


def corta(pto, nor):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=pto, plane_no=nor, clear_inner=False, clear_outer=False)


for s_ in (-1, 1):
    corta(Vector((HC.x, HC.y, 0)) + rad3 * (s_ * LADO / 2), rad3)
    corta(Vector((HC.x, HC.y, 0)) + tan3 * (s_ * LADO / 2), tan3)
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
print("HUECO 1,5 m caras", len(borrar))

# ------------------------------------------------ marco (manguito de chapa)
h0, h1 = DECK_Z0, DECK_Z1
bm = bmesh.new()
for s_ in (-1, 1):
    for (axis, other) in ((rad3, tan3), (tan3, rad3)):
        c = Vector((HC.x, HC.y, 0)) + axis * (s_ * (LADO / 2 + 0.02))
        a_ = c - other * (LADO / 2 + 0.04) + Vector((0, 0, h0))
        b_ = c + other * (LADO / 2 + 0.04) + Vector((0, 0, h0))
        for z in (h0 + 0.02, (h0 + h1) / 2, h1 - 0.02):
            caja(bm, Vector((a_.x, a_.y, z)), Vector((b_.x, b_.y, z)), 0.02)
nuevo("Trampilla_Marco", bm, hierro)

# ------------------------------------------------ placa con huecos (6x6 agujeros) = cubierta de la trampilla
NH = 6
paso = LADO / NH
rad_h = paso * 0.30
zp = h1 + 0.015
GROS = 0.05
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co = Vector((v.co.x * (LADO - 0.02), v.co.y * (LADO - 0.02), v.co.z * GROS))
bmesh.ops.transform(bm, matrix=Matrix.Translation((HC.x, HC.y, zp - GROS / 2)) @ Matrix.Rotation(tt_h, 4, 'Z'), verts=bm.verts)
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

# ------------------------------------------------ asa y bisagras
bm = bmesh.new()
asa_c = Vector((HC.x, HC.y, zp + 0.04)) + rad3 * (LADO * 0.25)
caja(bm, asa_c - tan3 * 0.12, asa_c + tan3 * 0.12, 0.015)
caja(bm, asa_c - tan3 * 0.12, asa_c - tan3 * 0.12 - Vector((0, 0, 0.04)), 0.015)
caja(bm, asa_c + tan3 * 0.12, asa_c + tan3 * 0.12 - Vector((0, 0, 0.04)), 0.015)
for s_ in (-0.3, 0.3):
    b0 = Vector((HC.x, HC.y, zp + 0.01)) - rad3 * (LADO / 2 - 0.02) + tan3 * (s_ * LADO)
    caja(bm, b0 - rad3 * 0.06, b0 + rad3 * 0.14, 0.03)
nuevo("Trampilla_Herrajes", bm, hierro)

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

S["trampilla_v3"] = 1
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("TRAMPILLA V3 OK  lado", LADO, "altura libre entre descansillo y trampilla", round(DECK_Z0 - Z_LAND_TOP, 2))
