# Atrezzo exterior de la isla: bote amarrado, boyas, cuerdas, redes, restos de naufragio, arboles secos, vallas
# y luces de referencia para los postes de piedra. Todo en la coleccion "Atrezzo_Exterior" (se recrea al ejecutar).
# Uso: blender -b archivo.blend --python atrezzo_exterior.py -- [--save]
import bpy, bmesh, math, random, sys
from mathutils import Vector, Matrix, Euler

S = bpy.context.scene
I = bpy.data.objects["IslandModel"]
bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
R = random.Random(11)
NIVEL_MAR = -0.55
PI = math.pi


def suelo(x, y):
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    return (I.matrix_world @ l).z if h else None


# ------------------------------------------------------------ limpiar
col = bpy.data.collections.get("Atrezzo_Exterior")
if col:
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("Atrezzo_Exterior")
    S.collection.children.link(col)

# ------------------------------------------------------------ materiales (el nombre se conserva al exportar y se enlaza en Unity)
def mat(nombre, color, rough=0.8, metal=0.0):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*color, 1)
    return m

M_MADERA = mat("M_Atrezzo_Madera", (0.16, 0.115, 0.075), 0.9)
M_MADERA_VIEJA = mat("M_Atrezzo_MaderaVieja", (0.22, 0.2, 0.17), 0.95)
M_CASCO = mat("M_Atrezzo_Casco", (0.07, 0.13, 0.13), 0.75)
M_CUERDA = mat("M_Atrezzo_Cuerda", (0.36, 0.3, 0.2), 0.95)
M_RED = mat("M_Atrezzo_Red", (0.12, 0.13, 0.11), 0.95)
M_METAL = mat("M_Atrezzo_Metal", (0.2, 0.12, 0.08), 0.55, 0.7)
M_CORTEZA = mat("M_Atrezzo_Corteza", (0.1, 0.085, 0.07), 1.0)
M_BOYA_ROJA = mat("M_Atrezzo_BoyaRoja", (0.38, 0.05, 0.04), 0.6)
M_BOYA_BLANCA = mat("M_Atrezzo_BoyaBlanca", (0.55, 0.55, 0.5), 0.6)


# ------------------------------------------------------------ utilidades de malla
def nuevo():
    return bmesh.new()


def tubo(bm, a, b, r0, r1, seg=6, tapa=True):
    a, b = Vector(a), Vector(b)
    d = b - a
    if d.length < 1e-5:
        return
    z = d.normalized()
    up = Vector((0, 0, 1)) if abs(z.z) < 0.95 else Vector((1, 0, 0))
    x = z.cross(up).normalized()
    y = z.cross(x)
    angs = [2 * PI * k / seg for k in range(seg)]
    ra = [bm.verts.new(a + (x * math.cos(t) + y * math.sin(t)) * r0) for t in angs]
    rb = [bm.verts.new(b + (x * math.cos(t) + y * math.sin(t)) * r1) for t in angs]
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
    if tapa:
        bm.faces.new(ra[::-1])
        bm.faces.new(rb)


def cadena(bm, pts, r, seg=5):
    for p, q in zip(pts[:-1], pts[1:]):
        tubo(bm, p, q, r, r, seg, tapa=False)


def caja(bm, c, s, rot=(0, 0, 0)):
    r = bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Translation(Vector(c)) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((s[0], s[1], s[2], 1))
    bmesh.ops.transform(bm, matrix=M, verts=r["verts"])


def esfera(bm, c, rad, esc=(1, 1, 1), seg=10):
    r = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(4, seg // 2), radius=rad)
    M = Matrix.Translation(Vector(c)) @ Matrix.Diagonal((esc[0], esc[1], esc[2], 1))
    bmesh.ops.transform(bm, matrix=M, verts=r["verts"])


def objeto(nombre, bm, material, recentrar=True, padre=None, loc=None):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    if material:
        me.materials.append(material)
    ob = bpy.data.objects.new(nombre, me)
    col.objects.link(ob)
    if recentrar and me.vertices:
        cs = [v.co for v in me.vertices]
        c = Vector((sum(v.x for v in cs) / len(cs), sum(v.y for v in cs) / len(cs), min(v.z for v in cs)))
        me.transform(Matrix.Translation(-c))
        ob.location = c
    if padre:
        ob.parent = padre
    if loc is not None:
        ob.location = loc
    return ob


def vacio(nombre, loc, rot=(0, 0, 0)):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_type = 'PLAIN_AXES'
    e.location = loc
    e.rotation_euler = rot
    col.objects.link(e)
    return e


def casco(bm, L, B, prof, altura, estaciones=14, perfil=9):
    """casco abierto de bote (proa en +Y). Devuelve la lista de puntos de la quilla para poner costillas."""
    filas = []
    for k in range(estaciones + 1):
        s = k / estaciones
        f = (1 - s ** 2.6) ** 0.6 * (0.8 + 0.2 * math.sin(PI * s))
        b = max(B * f, 0.01)
        gun = altura * (1.0 + 0.55 * s ** 3)
        dep = prof * (1 - 0.5 * s ** 2)
        y = (s - 0.5) * L
        fila = []
        for p in range(perfil):
            u = -1 + 2 * p / (perfil - 1)
            fila.append(bm.verts.new((b * u * (1 + 0.1 * (1 - abs(u))), y, gun - dep * (1 - u * u))))
        filas.append(fila)
    for k in range(estaciones):
        for p in range(perfil - 1):
            bm.faces.new((filas[k][p], filas[k][p + 1], filas[k + 1][p + 1], filas[k + 1][p]))
    bm.faces.new(filas[0][::-1])      # espejo de popa
    return filas


# ============================================================ 1) BOTE AMARRADO AL MUELLE
BOTE_POS = Vector((4.3, -49.0, NIVEL_MAR))
bote = vacio("Bote_Jugador", BOTE_POS, (0, 0, math.radians(180 + 3)))   # proa hacia el mar (-Y)

bm = nuevo()
casco(bm, 4.4, 0.82, 0.62, 0.55)
h = objeto("Bote_Casco", bm, M_CASCO, recentrar=False, padre=bote)
h.location = (0, 0, -0.2)
sol = h.modifiers.new("Grosor", 'SOLIDIFY')
sol.thickness = 0.07
sol.offset = -1
bpy.context.view_layer.objects.active = h
bpy.ops.object.modifier_apply(modifier="Grosor")

bm = nuevo()
for yb in (-1.15, 0.0, 1.05):          # bancos
    ancho = 1.1 if yb < 1 else 0.8
    caja(bm, (0, yb, 0.18), (ancho * 1.25, 0.28, 0.05))
caja(bm, (0, -2.12, 0.28), (1.0, 0.07, 0.4))     # popa (tapa del espejo)
for sg in (-1, 1):                                # remos apoyados
    tubo(bm, (sg * 0.42, -1.5, 0.28), (sg * 0.6, 1.2, 0.34), 0.025, 0.025, 6)
    caja(bm, (sg * 0.62, 1.4, 0.35), (0.14, 0.45, 0.02), (0, 0, 0.1 * sg))
tubo(bm, (0, 2.1, 0.2), (0, 2.3, 0.62), 0.03, 0.03, 6)          # postecillo de proa
objeto("Bote_Madera", bm, M_MADERA, recentrar=False, padre=bote)

bm = nuevo()
for k in range(3):                                # rollo de cuerda en el fondo
    cadena(bm, [(0.25 * math.cos(2 * PI * t / 14 + k), -1.7 + 0.25 * math.sin(2 * PI * t / 14 + k), -0.02 + 0.035 * k) for t in range(15)], 0.03)
# cabo de amarre: de la proa a la bita del muelle (coordenadas locales -> el bote esta girado 180 grados)
cleat_w = Vector((2.45, -50.5, 1.98))
a_loc = Vector((0, 2.3, 0.62))
c_loc = (Matrix.Rotation(math.radians(180 + 3), 3, 'Z').inverted() @ (cleat_w - BOTE_POS))
pts = []
for t in range(11):
    u = t / 10
    p = a_loc.lerp(c_loc, u)
    p.z -= 0.45 * math.sin(PI * u)       # catenaria floja
    pts.append(p)
cadena(bm, pts, 0.028)
objeto("Bote_Cuerdas", bm, M_CUERDA, recentrar=False, padre=bote)

# bita (amarre) de hierro en el borde del muelle
bm = nuevo()
caja(bm, (cleat_w.x, cleat_w.y, cleat_w.z + 0.07), (0.10, 0.34, 0.12))
caja(bm, (cleat_w.x, cleat_w.y - 0.12, cleat_w.z + 0.16), (0.10, 0.10, 0.12))
caja(bm, (cleat_w.x, cleat_w.y + 0.12, cleat_w.z + 0.16), (0.10, 0.10, 0.12))
objeto("Muelle_Bita", bm, M_METAL)

# ============================================================ 2) BOYAS (3 flotando + 2 en el muelle)
def boya(nombre, c, color_mat, flota=True):
    bm = nuevo()
    esfera(bm, (0, 0, 0.22), 0.34, (1, 1, 1.1), 12)
    tubo(bm, (0, 0, 0.5), (0, 0, 0.78), 0.03, 0.03, 6)
    tubo(bm, (0, 0, 0.78), (0, 0, 0.84), 0.09, 0.09, 8)
    bm2 = nuevo()
    caja(bm2, (0, 0, 0.0), (0.0001, 0.0001, 0.0001))
    ob = objeto(nombre, bm, color_mat, recentrar=False)
    ob.location = c
    if flota:
        b2 = nuevo()
        cadena(b2, [(0, 0, 0.0), (0.05, 0.03, -0.7), (-0.04, 0.0, -1.5), (0.0, 0.05, -2.3)], 0.025)
        objeto(nombre + "_Cadena", b2, M_METAL, recentrar=False, padre=ob)
    bm2.free()
    return ob

boya("Boya_1", (-9.5, -52.0, NIVEL_MAR - 0.1), M_BOYA_ROJA)
boya("Boya_2", (12.0, -44.5, NIVEL_MAR - 0.1), M_BOYA_BLANCA)
boya("Boya_3", (7.0, -68.0, NIVEL_MAR - 0.1), M_BOYA_ROJA)
for i, (x, y) in enumerate(((-1.8, -41.2), (-2.0, -41.9))):   # apiladas en el muelle
    ob = boya("Boya_Muelle_%d" % (i + 1), (x, y, 1.98), M_BOYA_ROJA if i == 0 else M_BOYA_BLANCA, flota=False)
    ob.rotation_euler = (0, math.radians(90 if i else 0), 0)

# ============================================================ 3) CUERDAS en el muelle
for i, (x, y, r) in enumerate(((-1.4, -45.3, 0.42), (1.6, -55.2, 0.36))):
    bm = nuevo()
    for k in range(5):
        cadena(bm, [(r * math.cos(2 * PI * t / 16 + k * 0.7), r * math.sin(2 * PI * t / 16 + k * 0.7), 0.04 + 0.055 * k) for t in range(17)], 0.032)
    tubo(bm, (r, 0, 0.1), (r + 0.9, 0.3, 0.035), 0.03, 0.03, 5, tapa=False)
    ob = objeto("Cuerda_Muelle_%d" % (i + 1), bm, M_CUERDA, recentrar=False)
    ob.location = (x, y, 1.98)

# ============================================================ 4) REDES
def red(nombre, c, ancho, alto, rot_z, comba=0.18, hueco=0.14, malla=0.24):
    bm = nuevo()
    nx, nz = int(ancho / malla), int(alto / malla)
    def P(i, j):
        u, v = i / nx, j / nz
        return Vector((ancho * (u - 0.5), comba * math.sin(PI * u) * v + 0.04 * math.sin(i * 1.7 + j), -alto * v))
    for j in range(nz + 1):
        for i in range(nx):
            if R.random() > hueco or j == 0:
                tubo(bm, P(i, j), P(i + 1, j), 0.011, 0.011, 3, tapa=False)
    for i in range(nx + 1):
        for j in range(nz):
            if R.random() > hueco or i in (0, nx):
                tubo(bm, P(i, j), P(i, j + 1), 0.011, 0.011, 3, tapa=False)
    ob = objeto(nombre, bm, M_RED, recentrar=False)
    ob.location = c
    ob.rotation_euler = (0, 0, rot_z)
    return ob

# red colgada de las barandas del muelle (lado -X, donde esta la escalera esta en +X de Unity -> aqui -X)
red("Red_Muelle_1", (-2.55, -44.0, 1.95 + 1.1), 3.0, 1.0, math.radians(90))
red("Red_Muelle_2", (2.55, -39.5, 1.95 + 1.1), 2.2, 0.9, math.radians(90), hueco=0.22)

# ============================================================ 5) VALLAS junto al camino principal
camino = [(0.0, -34.6), (0.5, -21.6), (1.0, -6.0), (2.1, 9.6), (1.0, 25.2), (-1.0, 40.8), (-1.9, 51.8), (3.9, 62.2), (7.1, 73.3), (11.7, 83.7), (14.3, 92.8), (11.0, 98.6), (6.0, 99.7)]
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
def dist_camino(x, y):
    return min((Vector((x, y)) - p).length for p in linea)

def valla(nombre, p0, p1):
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    n = max(2, int(L / 2.0) + 1)
    d = (p1 - p0).normalized()
    bm = nuevo()
    postes = []
    for k in range(n):
        q = p0.lerp(p1, k / (n - 1))
        g = suelo(q.x, q.y)
        if g is None:
            return None
        inc = (R.uniform(-0.12, 0.12), R.uniform(-0.12, 0.12), 0)
        alto = R.uniform(0.95, 1.2)
        caja(bm, (q.x, q.y, g + alto / 2 - 0.1), (0.12, 0.12, alto), inc)
        postes.append((Vector((q.x, q.y, g)), alto))
    for (a, ha), (b, hb) in zip(postes[:-1], postes[1:]):
        for fr in (0.42, 0.8):
            if R.random() < 0.18:
                continue                    # tabla caida
            pa = a + Vector((0, 0, ha * fr - 0.1))
            pb = b + Vector((0, 0, hb * fr - 0.1 - (R.uniform(0, 0.25) if R.random() < 0.25 else 0)))
            tubo(bm, pa, pb, 0.04, 0.04, 4)
    return objeto(nombre, bm, M_MADERA_VIEJA)

tramos = [(-26, -14, 1), (-8, 4, -1), (12, 22, 1), (30, 40, -1), (50, 60, 1), (66, 76, -1), (80, 88, 1)]
for i, (y0, y1, lado) in enumerate(tramos):
    pts = [p for p in linea if y0 <= p.y <= y1]
    if len(pts) < 3:
        continue
    a, b = pts[0], pts[-1]
    d = (b - a).normalized()
    nrm = Vector((-d.y, d.x)) * lado * 2.6
    valla("Valla_%02d" % (i + 1), a + nrm, b + nrm)

# red tendida sobre una de las vallas del camino
va = bpy.data.objects.get("Valla_03")
if va:
    red("Red_Valla", va.location + Vector((0, 0, 1.15)), 3.6, 0.95, math.radians(R.uniform(-40, 40)), comba=0.1)

# ============================================================ 6) ARBOLES SECOS
def rama(bm, p, d, largo, r, prof):
    fin = p + d * largo
    tubo(bm, p, fin, r, max(r * 0.55, 0.012), 5, tapa=False)
    if prof > 0:
        for _ in range(R.choice((2, 2, 3))):
            nd = (d + Vector((R.uniform(-0.9, 0.9), R.uniform(-0.9, 0.9), R.uniform(-0.1, 0.45)))).normalized()
            rama(bm, p.lerp(fin, R.uniform(0.55, 1.0)), nd, largo * R.uniform(0.55, 0.75), r * 0.55, prof - 1)

def arbol(nombre, base, alto):
    bm = nuevo()
    p = Vector(base)
    inc = Vector((R.uniform(-0.25, 0.25), R.uniform(-0.25, 0.25), 1)).normalized()
    nodos = [p]
    for k in range(4):
        inc = (inc + Vector((R.uniform(-0.18, 0.18), R.uniform(-0.18, 0.18), 0))).normalized()
        nodos.append(nodos[-1] + inc * alto / 4)
    for k in range(4):
        r0 = 0.17 * alto / 5 * (1 - k * 0.2)
        tubo(bm, nodos[k], nodos[k + 1], r0, r0 * 0.8, 6, tapa=(k == 0))
    for k in range(1, 4):
        for _ in range(R.choice((1, 2, 2))):
            ang = R.uniform(0, 2 * PI)
            d = Vector((math.cos(ang) * 0.9, math.sin(ang) * 0.9, R.uniform(0.2, 0.7))).normalized()
            rama(bm, nodos[k], d, alto * R.uniform(0.28, 0.42) * (1.2 - k * 0.2), 0.08 * alto / 5, 2)
    for _ in range(4):                                   # raices
        ang = R.uniform(0, 2 * PI)
        tubo(bm, p + Vector((0, 0, 0.5)), p + Vector((math.cos(ang) * 0.9, math.sin(ang) * 0.9, -0.15)), 0.12, 0.04, 4, tapa=False)
    return objeto(nombre, bm, M_CORTEZA)

excl = [((-6.8, 91.5), 26), ((13.4, 30.8), 9), ((-24.7, 1.7), 9), ((-41.6, 42.7), 9), ((-23.7, 9.4), 8),
        ((36.4, 15.8), 13), ((-2.0, 54.6), 11), ((-18.2, 49.9), 10), ((0, -35), 10)]
arboles = []
intentos = 0
while len(arboles) < 16 and intentos < 4000:
    intentos += 1
    x, y = R.uniform(-52, 52), R.uniform(-20, 118)
    g = suelo(x, y)
    if g is None or g < 2.0 or g > 11.5:
        continue
    if dist_camino(x, y) < 5.5:
        continue
    if any((Vector((x, y)) - Vector(c)).length < r for c, r in excl):
        continue
    if any((Vector((x, y)) - Vector(a)).length < 12 for a in arboles):
        continue
    # sitio llano
    if max(abs((suelo(x + dx, y + dy) or g) - g) for dx, dy in ((1.5, 0), (-1.5, 0), (0, 1.5), (0, -1.5))) > 0.9:
        continue
    arboles.append((x, y))
    arbol("Arbol_Seco_%02d" % len(arboles), (x, y, g - 0.2), R.uniform(3.6, 6.2))
print("ATREZZO arboles", len(arboles), arboles)

# ============================================================ 7) NAUFRAGIO en la costa oeste
def costa_oeste(y):
    for k in range(0, 140):
        x = -85 + k
        g = suelo(x, y)
        if g is not None and g > NIVEL_MAR + 0.3:
            return x
    return None

yw = 52.0
xc = costa_oeste(yw)
print("ATREZZO costa_oeste", xc)
cx, cy = (xc + 3.0 if xc is not None else -50.0), yw   # sobre la playa, no en el agua
gs = suelo(cx, cy)
base_z = (gs if gs is not None else 0.0) - 0.05
bm = nuevo()
L, B, DEP = 9.5, 2.3, 1.7
estac = 12
tubo(bm, (0, -L / 2, 0.15), (0, L / 2, 0.15 + 0.9), 0.14, 0.12, 6)                  # quilla
tubo(bm, (0, L / 2, 0.15 + 0.9), (0, L / 2 + 0.7, 0.15 + 2.2), 0.12, 0.09, 6)         # roda de proa
tubo(bm, (0, -L / 2, 0.15), (0, -L / 2 - 0.4, 1.9), 0.12, 0.09, 6)                    # codaste
for k in range(1, estac):
    s = k / estac
    f = (1 - s ** 2.6) ** 0.6 * (0.8 + 0.2 * math.sin(PI * s))
    y = (s - 0.5) * L
    quilla_z = 0.15 + 0.9 * s
    for sg in (-1, 1):
        if R.random() < 0.2:
            continue
        frac = R.uniform(0.35, 1.0)                  # costilla rota a cierta altura
        pts = []
        for p in range(0, 9):
            u = p / 8 * frac
            pts.append((sg * B * f * u * 1.0 * 1.0, y, quilla_z + DEP * 1.0 * (u * u) * (1.0 + 0.2 * s) + 0.05))
        cadena(bm, pts, 0.07, 5)
for k in range(9):                                    # tablones que quedan en el fondo
    s0 = R.uniform(0.1, 0.75)
    sg = R.choice((-1, 1))
    yy = (s0 - 0.5) * L
    for t in range(2):
        caja(bm, (sg * (0.35 + 0.28 * k * 0.35), yy + t * 1.05, 0.22 + 0.07 * k), (0.07, 0.95, 0.025), (0, 0.08 * sg, 0.05 * sg))
tubo(bm, (0.2, 1.3, 0.3), (-2.3, 6.2, 0.55 - 0.4), 0.09, 0.07, 6)       # mastil caido
caja(bm, (-2.1, 6.3, 0.26), (0.4, 0.25, 0.04), (0, 0, 0.3))
nau = objeto("Restos_Naufragio", bm, M_MADERA_VIEJA, recentrar=False)
nau.location = (cx, cy, base_z)
nau.rotation_euler = (math.radians(7), math.radians(-17), math.radians(28))

# ============================================================ 8) LUCES de referencia (brillo suave de los postes de piedra)
def luz(nombre, loc, color=(0.55, 0.8, 0.95), energia=120.0, radio=6.0):
    ld = bpy.data.lights.new(nombre, 'POINT')
    ld.color = color
    ld.energy = energia
    ld.shadow_soft_size = 0.3
    ld.use_custom_distance = True
    ld.cutoff_distance = radio
    lo = bpy.data.objects.new(nombre, ld)
    lo.location = loc
    col.objects.link(lo)

for n, off in (("Poste_1_Reflejo_Cabeza", 1.6), ("Poste_2_Origen_Cabeza", 1.6), ("Poste_3_Fin_Cabeza", 1.6)):
    c = bpy.data.objects[n].matrix_world @ Vector((0, 0, 0))
    luz("Luz_" + n.replace("_Cabeza", ""), (c.x, c.y, c.z + off))
pl = bpy.data.objects["Placa_Inscripcion"].matrix_world @ Vector((0, 0, 0))
luz("Luz_Placa", (pl.x, pl.y, pl.z + 1.4), (0.9, 0.85, 0.6), 60.0, 5.0)
es = bpy.data.objects["Estela_Mareas"].matrix_world @ Vector((0, 0, 0))
luz("Luz_Estela", (es.x, es.y, es.z + 5.5), (0.55, 0.8, 0.95), 90.0, 8.0)

print("ATREZZO objetos", len(col.objects), "tris", sum(len(o.data.polygons) for o in col.objects if o.type == 'MESH'))
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
