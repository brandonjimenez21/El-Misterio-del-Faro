# Capa vikinga de la isla: la isla fue de los vikingos mucho antes del faro. Crea la coleccion "Vikingo_Antiguo"
# (se hornea y exporta con exportar_vikingo.py):
#   Vik_Piedra_Sendero  piedra runica en lo alto de la cuesta del muelle ("Ulf levanto esta piedra por su hermano. El mar se lo llevo")
#   Vik_Piedra_Barco    la piedra grande, junto al sendero, delante del barco de piedra ("Mientras el faro arda, el draugr duerme")
#   Vik_Piedra_Faro     piedra runica junto al camino del faro ("El mar da, el mar quita") con su altar (Vik_Altar)
#   Vik_Piedra_Caida    piedra runica caida y medio enterrada en la repisa del oeste
#   Vik_Barco_Piedras   barco de piedra (tumba): menhires en forma de casco, mas altos en proa y popa
#   Vik_Mojon + Vik_Espada + Vik_Escudo   mojon funerario en el centro del barco con una espada clavada y un escudo podrido
#   Vik_Roca_Grabados   penasco con petroglifos (barcas, rueda solar, figuras) y una linea de runas anadida despues
#   Vik_Proa_Dragon + Vik_Cuadernas       proa de drakkar con cabeza de dragon y cuadernas que asoman de la arena de la playa
# Tambien escribe vikingo_huellas.json (circulos donde pasto_y_rocas.py no pone hierba).
# Uso: blender -b el_misterio_del_faro.blend --python scripts/vikingos.py -- --save      (re-ejecutable: rehace todo)
import bpy, bmesh, math, random, sys, os, json
from mathutils import Vector, Matrix, Euler, noise

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import vikingo_mats as vm
import runas_lib

D = bpy.data
rnd = random.Random(793)
PI = math.pi

# ------------------------------------------------------------------ donde va cada cosa (x, y de Blender) y hacia donde mira
SITIOS = {
    'Sendero': ((5.6, -16.6), (-0.55, -0.83)),
    'Barco': ((10.4, 0.9), (-1.0, 0.06)),
    'Faro': ((-10.0, 72.0), (1.0, -0.2)),
    'Caida': ((-34.0, 70.0), (0.35, 1.0)),
}
BARCO_CENTRO, BARCO_LARGO, BARCO_ANCHO = (20.3, 0.6), 15.0, 4.7      # eje a lo largo de X, proa al este (hacia el mar)
ALTAR = (-12.6, 70.2)
ROCA_GRABADOS = ((6.6, 25.0), (-1.0, 0.1))
PROA = ((12.0, -29.6), (-0.8, 0.6))

# ------------------------------------------------------------------ coleccion (se rehace)
c = D.collections.get("Vikingo_Antiguo")
if c:
    for o in list(c.objects):
        me = o.data if o.type == 'MESH' else None
        D.objects.remove(o)
        if me and me.users == 0:
            D.meshes.remove(me)
else:
    c = D.collections.new("Vikingo_Antiguo")
    bpy.context.scene.collection.children.link(c)
COL = c

# ------------------------------------------------------------------ suelo
bpy.context.view_layer.update()
ISLA = D.objects["IslandModel"]
_inv = ISLA.matrix_world.inverted()
_dl = (_inv.to_3x3() @ Vector((0, 0, -1))).normalized()


def suelo(x, y):
    h, l, n, i = ISLA.ray_cast(_inv @ Vector((x, y, 500.0)), _dl)
    return (ISLA.matrix_world @ l).z if h else None


def giro_hacia(d):
    """angulo en Z para que la cara delantera (-Y local) mire en la direccion d"""
    return math.atan2(d[0], -d[1])


# ------------------------------------------------------------------ utilidades de malla
def interp(tabla, s):
    for (s0, v0), (s1, v1) in zip(tabla[:-1], tabla[1:]):
        if s <= s1:
            f = max(0.0, (s - s0) / (s1 - s0))
            return v0 + (v1 - v0) * f
    return tabla[-1][1]


def curva(ctrl, n):
    P = [Vector(q) for q in ctrl]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    segs = len(ctrl) - 1
    out = []
    for i in range(n + 1):
        u = i / n * segs
        k = min(int(u), segs - 1)
        t = u - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return out


def perfil_losa(z, ancho, alto, hombro, asim, p):
    """(centro x, semiancho, redondeo 0..1) de la losa a la altura z; igual que runas_lib.contorno_piedra"""
    zc = min(max(z, 0.0), alto)
    zh = alto * hombro
    estrecha = 1.0 - 0.10 * (zc / alto)
    ensancha = 1.0 - 0.07 * max(0.0, 1 - zc / (alto * 0.25)) ** 2
    if zc <= zh:
        return 0.0, ancho / 2 * estrecha * ensancha, 1.0
    f = (zc - zh) / (alto - zh)
    r = max(0.0, 1 - f ** p) ** (1 / p)
    return asim * f * f * (3 - 2 * f), ancho / 2 * estrecha * r, r


def losa_bm(bm, ancho, alto, grosor, hombro=0.62, asim=0.0, seed=0, p=2.2, enterrado=0.45, nz=46, na=44, frente=6.0,
            rugoso=1.0, M=None):
    """losa / menhir: seccion de superelipse (cara delantera -Y casi plana, trasera abombada), bordes mellados y bultos"""
    off = Vector((seed * 3.17, seed * 1.31, seed * 0.77))
    filas = []
    nuevos = []
    for kz in range(nz):
        t = kz / nz
        z = -enterrado + (alto + enterrado) * (1 - (1 - t) ** 1.7)
        xc, a, r = perfil_losa(z, ancho, alto, hombro, asim, p)
        a *= 1 + 0.035 * rugoso * noise.noise(Vector((z * 2.3, seed * 5.1, 0.3)))
        b = grosor / 2 * (1 - 0.2 * (max(z, 0) / alto)) * (0.3 + 0.7 * r)
        fila = []
        for j in range(na):
            th = 2 * PI * j / na
            cs, sn = math.cos(th), math.sin(th)
            e = frente if sn < 0 else 2.6
            X = a * math.copysign(abs(cs) ** (2 / e), cs)
            Y = b * math.copysign(abs(sn) ** (2 / e), sn)
            q = Vector((xc + X, Y, z))
            d = Vector((X / max(a, 1e-4), Y / max(b, 1e-4), 0))
            d = d.normalized() if d.length > 1e-6 else Vector((0, -1, 0))
            ff = 0.3 + 0.7 * min(1.0, max(0.0, (sn + 0.35) / 0.7))            # la cara tallada, mas lisa
            bulto = noise.noise(q * 1.15 + off) * 0.085 + noise.noise(q * 3.6 + off) * 0.028
            q += d * bulto * ff * rugoso
            fila.append(bm.verts.new(q))
        filas.append(fila)
        nuevos += fila
    xc, a, r = perfil_losa(alto, ancho, alto, hombro, asim, p)
    polo = bm.verts.new((xc, 0, alto))
    nuevos.append(polo)
    for kz in range(nz - 1):
        for j in range(na):
            bm.faces.new((filas[kz][j], filas[kz][(j + 1) % na], filas[kz + 1][(j + 1) % na], filas[kz + 1][j]))
    for j in range(na):
        bm.faces.new((filas[-1][j], filas[-1][(j + 1) % na], polo))
    bm.faces.new(filas[0][::-1])
    if M is not None:
        bmesh.ops.transform(bm, matrix=M, verts=nuevos)
    return nuevos


def roca_bm(bm, centro, radios, seed=0, sub=3, cuadrado=0.6, rug=0.2, M=None):
    """penasco: icoesfera hecha 'caja redondeada' + bultos"""
    r = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    off = Vector((seed * 2.3, seed * 0.9, seed * 1.7))
    for v in r['verts']:
        u = v.co.copy()
        w = Vector((math.copysign(abs(u.x) ** cuadrado, u.x), math.copysign(abs(u.y) ** cuadrado, u.y), math.copysign(abs(u.z) ** cuadrado, u.z)))
        w = w.lerp(w.normalized(), 0.35)
        d = 1 + rug * noise.noise(u * 1.6 + off) + rug * 0.4 * noise.noise(u * 4.2 + off)
        v.co = Vector(centro) + Vector((w.x * radios[0], w.y * radios[1], w.z * radios[2])) * d
    if M is not None:
        bmesh.ops.transform(bm, matrix=M, verts=r['verts'])
    return r['verts']


def tubo_e(bm, pts, ra, rb, lado=(0, 1, 0), segs=12, tapas=True):
    """tubo de seccion eliptica: ra = semieje en el plano de la curva, rb = semieje lateral (a lo largo de 'lado')"""
    pts = [Vector(q) for q in pts]
    lado = Vector(lado)
    anillos = []
    for i, q in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        l = (lado - t * lado.dot(t))
        l = l.normalized() if l.length > 1e-5 else t.orthogonal().normalized()
        u = l.cross(t).normalized()
        a = ra[i] if isinstance(ra, (list, tuple)) else ra
        b = rb[i] if isinstance(rb, (list, tuple)) else rb
        anillos.append([bm.verts.new(q + u * a * math.cos(2 * PI * k / segs) + l * b * math.sin(2 * PI * k / segs)) for k in range(segs)])
    for i in range(len(anillos) - 1):
        for k in range(segs):
            bm.faces.new((anillos[i][k], anillos[i][(k + 1) % segs], anillos[i + 1][(k + 1) % segs], anillos[i + 1][k]))
    if tapas:
        bm.faces.new(anillos[0][::-1])
        bm.faces.new(anillos[-1])
    return anillos


def cono(bm, base, punta, r, segs=6):
    base, punta = Vector(base), Vector(punta)
    t = (punta - base).normalized()
    a = t.orthogonal().normalized()
    b = t.cross(a)
    an = [bm.verts.new(base + (a * math.cos(2 * PI * k / segs) + b * math.sin(2 * PI * k / segs)) * r) for k in range(segs)]
    pv = bm.verts.new(punta)
    for k in range(segs):
        bm.faces.new((an[k], an[(k + 1) % segs], pv))
    bm.faces.new(an[::-1])


def caja(bm, centro, dims, rot=None, mat=0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Translation(Vector(centro)) @ (rot.to_matrix().to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*dims, 1))
    bmesh.ops.transform(bm, matrix=M, verts=r['verts'])
    for f in {f for v in r['verts'] for f in v.link_faces}:
        f.material_index = mat
    return r['verts']


def objeto(nombre, bm, mats, loc=(0, 0, 0), rot=(0, 0, 0), suave=True):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = D.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if suave:
        for pl in me.polygons:
            pl.use_smooth = True
    o = D.objects.new(nombre, me)
    COL.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    return o


def fijar_suelo(o):
    """atributo 'Suelo' = metros de cada vertice sobre el terreno (humedad y musgo al pie)"""
    bpy.context.view_layer.update()
    mw = o.matrix_world
    alt = []
    for v in o.data.vertices:
        q = mw @ v.co
        h = suelo(q.x, q.y)
        alt.append(max(0.0, q.z - h) if h is not None else 2.0)
    vm.atributo_suelo(o.data, alt)


HUELLAS = []          # (x, y, radio) sin hierba

# ------------------------------------------------------------------ tallas y materiales
vm.generar_tallas()
M_BARCO = vm.piedra("M_V_Piedra_Menhir", claro=(0.16, 0.16, 0.165), oscuro=(0.055, 0.057, 0.063), calido=0.2, liquen=1.0, musgo=0.75)
M_MOJON = vm.piedra("M_V_Piedra_Mojon", claro=(0.17, 0.165, 0.16), oscuro=(0.06, 0.06, 0.062), calido=0.5, liquen=0.8, musgo=0.8, grietas=0.5)
M_ALTAR = vm.piedra("M_V_Piedra_Altar", claro=(0.13, 0.13, 0.135), oscuro=(0.04, 0.04, 0.046), calido=0.25, liquen=0.9, musgo=1.0)
M_MADERA = vm.madera_vieja("M_V_MaderaVieja")
M_HIERRO = vm.hierro_oxidado("M_V_HierroOxidado")


# ------------------------------------------------------------------ 1. piedras runicas
def piedra_runica(nombre):
    ancho, alto, texto, motivo, hombro, asim, seed, seg = runas_lib.PIEDRAS[nombre]
    (x, y), d = SITIOS[nombre]
    grosor = 0.26 + 0.07 * ancho + 0.03 * (seed % 3)
    bm = bmesh.new()
    losa_bm(bm, ancho, alto, grosor, hombro, asim, seed, enterrado=0.5)
    tono = {'Sendero': 1.0, 'Barco': 0.92, 'Faro': 1.06, 'Caida': 0.85}[nombre]
    m = vm.piedra("M_V_Piedra_" + nombre, claro=vm.gris((0.165, 0.165, 0.17), tono), oscuro=vm.gris((0.055, 0.057, 0.063), tono),
                  calido=0.3 + 0.1 * (seed % 3), liquen=1.0, musgo=1.0 if nombre != 'Caida' else 0.75,
                  tallas=[{'imagen': "T_V_Piedra_" + nombre, 'modo': 'frente', 'ancho': ancho * 1.08, 'alto': alto * 1.03}],
                  **({'musgo_arriba': 0.09, 'musgo_pie': 0.06, 'humedad': 0.45} if nombre == 'Caida' else {}))
    z = suelo(x, y)
    if nombre == 'Caida':
        # tumbada boca arriba siguiendo el terreno, con la cabecera un poco levantada
        dn = Vector((d[0], d[1])).normalized()
        zc = suelo(x + dn.x * alto, y + dn.y * alto) or z
        inclin = math.atan2(zc - z, alto) + math.radians(5)
        o = objeto("Vik_Piedra_" + nombre, bm, [m], (x, y, z + grosor * 0.2), Euler((-(PI / 2 - inclin), math.radians(7), math.atan2(-dn.x, dn.y)), 'XYZ'))
        for k in range(4):
            HUELLAS.append((x + dn.x * alto * k / 3.5, y + dn.y * alto * k / 3.5, 0.75))
    else:
        cae = {'Sendero': (4, -3), 'Barco': (-3, 2), 'Faro': (7, 5)}[nombre]
        o = objeto("Vik_Piedra_" + nombre, bm, [m], (x, y, z - 0.04), Euler((math.radians(cae[0]), math.radians(cae[1]), giro_hacia(d)), 'XYZ'))
        HUELLAS.append((x, y, 0.55 + ancho * 0.35))
    print("PIEDRA", nombre, "en", (round(x, 1), round(y, 1), round(z, 2)), "cara %.2f x %.2f m" % (ancho, alto))
    return o


for _n in runas_lib.PIEDRAS:
    piedra_runica(_n)


# ------------------------------------------------------------------ 2. barco de piedra
def barco_piedra():
    cx, cy = BARCO_CENTRO
    L, W = BARCO_LARGO, BARCO_ANCHO
    bm = bmesh.new()
    puestos = []
    n_lado = 12
    for k in range(0, n_lado + 2):
        xs = L / 2 * math.cos(PI * k / (n_lado + 1))
        for lado in ((1,) if k in (0, n_lado + 1) else (1, -1)):
            ys = lado * W / 2 * max(0.0, 1 - (xs / (L / 2)) ** 2) ** 0.8
            puestos.append((xs, ys, lado, k))
    for i, (xs, ys, lado, k) in enumerate(puestos):
        extremo = k in (0, n_lado + 1)
        if not extremo and i in (9, 18):
            continue                                   # dos piedras que faltan (se las llevaron o estan bajo la hierba)
        f = abs(xs) / (L / 2)
        alto = (1.8 if xs > 0 else 1.5) if extremo else 0.55 + 0.9 * f ** 2.2 + rnd.uniform(-0.1, 0.14)
        ancho = 0.85 if extremo else rnd.uniform(0.5, 0.78)
        grosor = rnd.uniform(0.3, 0.44)
        # normal hacia fuera del casco
        if extremo:
            nrm = Vector((math.copysign(1, xs), 0, 0))
        else:
            dy_dx = -lado * W / 2 * 0.8 * max(1e-3, 1 - (xs / (L / 2)) ** 2) ** -0.2 * 2 * xs / (L / 2) ** 2
            nrm = Vector((-dy_dx * lado, lado, 0)).normalized()
        x, y = cx + xs + rnd.uniform(-0.12, 0.12), cy + ys + rnd.uniform(-0.12, 0.12)
        z = suelo(x, y)
        if z is None:
            continue
        rz = giro_hacia((nrm.x, nrm.y)) + rnd.uniform(-0.2, 0.2)
        if i == 13:                                    # una caida hacia fuera
            rot = Euler((math.radians(-78), math.radians(6), rz), 'XYZ')
            zoff = grosor * 0.25
        elif i in (5, 21):                             # dos muy vencidas
            rot = Euler((math.radians(rnd.choice((-22, 19))), math.radians(8), rz), 'XYZ')
            zoff = -0.05
        else:
            rot = Euler((math.radians(rnd.uniform(-6, 6)), math.radians(rnd.uniform(-5, 5)), rz), 'XYZ')
            zoff = -0.05
        M = Matrix.Translation((x, y, z + zoff)) @ rot.to_matrix().to_4x4()
        losa_bm(bm, ancho, alto, grosor, rnd.uniform(0.45, 0.62), rnd.uniform(-0.08, 0.08), 100 + i, p=rnd.uniform(2.0, 3.0), enterrado=0.4,
                nz=22, na=24, frente=4.0, rugoso=1.3, M=M)
        HUELLAS.append((x, y, 0.5))
    o = objeto("Vik_Barco_Piedras", bm, [M_BARCO])
    print("BARCO DE PIEDRA:", len(puestos) - 2, "menhires, centro", BARCO_CENTRO)
    return o


barco_piedra()


# ------------------------------------------------------------------ 3. mojon con espada y escudo (centro del barco)
def mojon():
    cx, cy = BARCO_CENTRO
    z0 = suelo(cx, cy)
    bm = bmesh.new()
    capas = [(0.78, 12, 0.13), (0.52, 8, 0.36), (0.27, 5, 0.58), (0.0, 1, 0.78)]
    for ci, (R, n, zc) in enumerate(capas):
        for i in range(n):
            a = 2 * PI * i / max(n, 1) + ci * 0.6 + rnd.uniform(-0.15, 0.15)
            r = R * rnd.uniform(0.85, 1.1)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            zz = (suelo(x, y) or z0) if ci == 0 else z0
            rad = (rnd.uniform(0.2, 0.3), rnd.uniform(0.17, 0.26), rnd.uniform(0.12, 0.18))
            M = Matrix.Translation((x, y, zz + zc)) @ Euler((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(0, PI)), 'XYZ').to_matrix().to_4x4()
            roca_bm(bm, (0, 0, 0), rad, 300 + ci * 20 + i, 2, 0.75, 0.22, M)
    objeto("Vik_Mojon", bm, [M_MOJON])
    HUELLAS.append((cx, cy, 1.2))

    # espada vikinga clavada en lo alto: hoja ancha, guarda corta, pomo lobulado; comida por el oxido
    bm = bmesh.new()
    hoja = [(-0.34, 0.9), (0.0, 1.0), (0.3, 0.92), (0.5, 0.86), (0.585, 0.8)]
    secs = []
    for zz, f in hoja:
        mella = 1 + rnd.uniform(-0.06, 0.06)
        secs.append([bm.verts.new((sx * 0.03 * f * mella, sy * 0.0065 * f, zz)) for sx, sy in ((1, 0), (0, 1), (-1, 0), (0, -1))])
    for a, b in zip(secs[:-1], secs[1:]):
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(secs[0][::-1])
    bm.faces.new(secs[-1])
    caja(bm, (0, 0, 0.6), (0.15, 0.03, 0.026))
    tubo_e(bm, [(0, 0, 0.61), (0, 0, 0.66), (0, 0, 0.71)], [0.014, 0.012, 0.013], [0.011, 0.01, 0.011], (0, 1, 0), 8)
    caja(bm, (0, 0, 0.72), (0.085, 0.028, 0.018))
    for dx, rr in ((-0.03, 0.017), (0, 0.022), (0.03, 0.017)):
        roca_bm(bm, (dx, 0, 0.74), (rr, 0.014, rr * 1.1), 5, 1, 1.0, 0.0)
    objeto("Vik_Espada", bm, [M_HIERRO], (cx + 0.05, cy - 0.04, z0 + 0.84), Euler((math.radians(8), math.radians(-11), math.radians(35)), 'XYZ'), suave=False)

    # escudo redondo apoyado en el mojon: tablas podridas (falta una), umbo de hierro y restos del aro
    bm = bmesh.new()
    R = 0.44
    nt = 6
    wt = 2 * R / nt
    for i in range(nt):
        if i == 4:
            continue
        xm = -R + (i + 0.5) * wt
        medio = math.sqrt(max(R * R - xm * xm, 0.01))
        arriba, abajo = medio * rnd.uniform(0.72, 1.0), medio * rnd.uniform(0.9, 1.0)
        caja(bm, (xm, 0, (arriba - abajo) / 2), (wt * 0.94, 0.02, arriba + abajo), Euler((0, rnd.uniform(-0.02, 0.02), 0)), 0)
    # umbo (semiesfera) y aro
    n = 12
    anillos = []
    for k in range(5):
        a = k / 4 * PI / 2
        anillos.append([bm.verts.new((0.085 * math.cos(a) * math.cos(2 * PI * j / n), -0.012 - 0.07 * math.sin(a), 0.085 * math.cos(a) * math.sin(2 * PI * j / n))) for j in range(n)])
    for a, b in zip(anillos[:-1], anillos[1:]):
        for j in range(n):
            f = bm.faces.new((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
            f.material_index = 1
    antes = set(bm.faces)
    tubo_e(bm, [(R * math.cos(a), 0, R * math.sin(a)) for a in [(-0.9 + 3.1 * k / 20) for k in range(21)]], 0.012, 0.014, (0, 1, 0), 6)
    for f in set(bm.faces) - antes:
        f.material_index = 1
    ang = math.radians(215)
    ex, ey = cx + 0.98 * math.cos(ang), cy + 0.98 * math.sin(ang)
    objeto("Vik_Escudo", bm, [M_MADERA, M_HIERRO], (ex, ey, (suelo(ex, ey) or z0) + R * 0.86),
           Euler((math.radians(-27), math.radians(9), ang + PI / 2), 'XYZ'), suave=False)


mojon()


# ------------------------------------------------------------------ 4. altar de piedra (horgr) junto a la piedra del faro
def altar():
    x, y = ALTAR
    z = suelo(x, y)
    bm = bmesh.new()
    rz = math.radians(24)
    R = Euler((0, 0, rz)).to_matrix().to_4x4()
    for i, (dx, dy) in enumerate(((-0.62, -0.12), (0.6, -0.2), (0.05, 0.36))):
        q = R @ Vector((dx, dy, 0))
        zz = suelo(x + q.x, y + q.y) or z
        roca_bm(bm, (x + q.x, y + q.y, zz + 0.2), (0.36, 0.3, 0.36), 400 + i, 2, 0.7, 0.2)
    M = Matrix.Translation((x, y, z + 0.66)) @ Euler((math.radians(3), math.radians(-4), rz)).to_matrix().to_4x4()
    roca_bm(bm, (0, 0, 0), (1.12, 0.66, 0.17), 410, 3, 0.42, 0.13, M)
    objeto("Vik_Altar", bm, [M_ALTAR])
    HUELLAS.append((x, y, 1.35))


altar()


# ------------------------------------------------------------------ 5. penasco de los grabados
def roca_grabados():
    (x, y), d = ROCA_GRABADOS
    z = suelo(x, y)
    bm = bmesh.new()
    losa_bm(bm, 3.3, 2.05, 1.75, 0.52, 0.18, 61, p=3.6, enterrado=0.6, nz=40, na=64, frente=7.0, rugoso=1.5)
    m = vm.piedra("M_V_Piedra_Grabados", claro=(0.15, 0.148, 0.145), oscuro=(0.05, 0.05, 0.054), calido=0.45, liquen=1.0, musgo=1.0,
                  tallas=[{'imagen': "T_V_Petroglifos", 'modo': 'frente', 'ancho': 2.72, 'alto': 1.7, 'z0': 0.2, 'cx': 0.03}], escala=0.8)
    objeto("Vik_Roca_Grabados", bm, [m], (x, y, z - 0.05), Euler((math.radians(-4), math.radians(2), giro_hacia(d)), 'XYZ'))
    HUELLAS.append((x, y, 1.9))


roca_grabados()


# ------------------------------------------------------------------ 6. proa de drakkar y cuadernas en la playa
def proa():
    (x, y), d = PROA
    z = suelo(x, y)
    bm = bmesh.new()
    # roda y cuello (plano XZ local, +X hacia delante)
    eje = curva([(0, 0, -0.9), (0.02, 0, 0.3), (0.12, 0, 1.2), (0.34, 0, 2.0), (0.62, 0, 2.6), (0.92, 0, 2.98), (1.22, 0, 3.12)], 30)
    ra_t = [(0, 0.27), (0.5, 0.2), (0.8, 0.165), (0.93, 0.2), (1.0, 0.225)]
    rb_t = [(0, 0.115), (0.5, 0.105), (0.8, 0.1), (0.93, 0.125), (1.0, 0.142)]
    ra, rb = [], []
    for i in range(len(eje)):
        s = i / (len(eje) - 1)
        anillo = 1.22 if i in (17, 20, 23) else 1.0                     # molduras talladas en el cuello
        ra.append(interp(ra_t, s) * anillo)
        rb.append(interp(rb_t, s) * anillo)
    tubo_e(bm, eje, ra, rb, (0, 1, 0), 14)
    # cabeza (todo escalado alrededor del final del cuello): mandibula de arriba con el hocico rizado y la de abajo, boca abierta
    E = 1.38
    piv = Vector((1.2, 0, 3.12))

    def H(q):
        return piv + (Vector(q) - piv) * E

    sup = [H(q) for q in curva([(1.2, 0, 3.12), (1.5, 0, 3.14), (1.78, 0, 3.09), (1.98, 0, 3.07), (2.09, 0, 3.15)], 12)]
    tubo_e(bm, sup, [E * interp([(0, 0.16), (0.4, 0.115), (0.8, 0.065), (1, 0.03)], i / 12) for i in range(13)],
           [E * interp([(0, 0.103), (0.4, 0.088), (0.8, 0.058), (1, 0.03)], i / 12) for i in range(13)], (0, 1, 0), 12)
    inf = [H(q) for q in curva([(1.12, 0, 2.96), (1.42, 0, 2.84), (1.68, 0, 2.74), (1.86, 0, 2.7), (1.96, 0, 2.75)], 10)]
    tubo_e(bm, inf, [E * interp([(0, 0.075), (0.5, 0.05), (1, 0.022)], i / 10) for i in range(11)],
           [E * interp([(0, 0.085), (0.5, 0.06), (1, 0.028)], i / 10) for i in range(11)], (0, 1, 0), 10)
    # dientes
    for xd, zs, zi in ((1.62, 3.0, 2.82), (1.76, 3.02, 2.76), (1.9, 3.03, 2.73)):
        for ly in (-0.035, 0.035):
            cono(bm, H((xd, ly, zs)), H((xd + 0.01, ly, zs - 0.085)), 0.018 * E)
            cono(bm, H((xd - 0.05, ly, zi)), H((xd - 0.05, ly, zi + 0.075)), 0.016 * E)
    # ojos saltones
    for ly in (-0.098, 0.098):
        roca_bm(bm, H((1.36, ly, 3.2)), (0.042 * E, 0.03 * E, 0.042 * E), 3, 1, 1.0, 0.0)
    # cresta en espiral detras de la cabeza y lengua
    cresta = []
    for k in range(27):
        a = math.radians(-60) + k / 26 * 2 * PI * 1.25
        r = 0.2 - 0.15 * k / 26
        cresta.append(H((0.98 - r * math.cos(a) * 1.0 + 0.1, 0, 3.47 + r * math.sin(a))))
    tubo_e(bm, cresta, [E * (0.055 - 0.035 * k / 26) for k in range(27)], [E * (0.05 - 0.03 * k / 26) for k in range(27)], (0, 1, 0), 8)
    lengua = [H(q) for q in curva([(1.5, 0, 2.9), (1.8, 0, 2.86), (2.02, 0, 2.9), (2.1, 0, 2.99)], 8)]
    tubo_e(bm, lengua, [E * (0.02 - 0.012 * i / 8) for i in range(9)], [E * (0.03 - 0.02 * i / 8) for i in range(9)], (0, 1, 0), 6)
    rz = math.atan2(d[1], d[0])
    o = objeto("Vik_Proa_Dragon", bm, [M_MADERA], (x, y, z - 0.05), Euler((math.radians(7), math.radians(-11), rz), 'XYZ'))
    HUELLAS.append((x, y, 0.7))

    # cuadernas del casco enterrado, detras de la proa
    bm = bmesh.new()
    dn = Vector((d[0], d[1])).normalized()
    lat = Vector((-dn.y, dn.x))
    for i, (atras, sep, alto) in enumerate(((1.5, 0.75, 0.75), (2.7, 1.1, 1.15), (3.9, 1.3, 0.55), (5.1, 1.35, 0.95), (6.3, 1.2, 0.4))):
        for lado in (1, -1):
            if (i, lado) in ((2, -1), (4, 1)):
                continue
            bx, by = x - dn.x * atras + lat.x * sep * lado, y - dn.y * atras + lat.y * sep * lado
            bz = suelo(bx, by)
            if bz is None or bz < -0.2:
                continue
            alto_r = alto * rnd.uniform(0.8, 1.15)
            pts = []
            for s in range(8):
                f = s / 7
                h = -0.7 + (alto_r + 0.7) * f
                fuera = 0.38 * max(0.0, h) ** 1.4
                pts.append((bx + lat.x * fuera * lado + rnd.uniform(-0.01, 0.01), by + lat.y * fuera * lado, bz + h))
            tubo_e(bm, pts, [0.1 - 0.03 * s / 7 for s in range(8)], [0.075 - 0.02 * s / 7 for s in range(8)], (dn.x, dn.y, 0), 8)
            HUELLAS.append((bx, by, 0.35))
    objeto("Vik_Cuadernas", bm, [M_MADERA])
    return o


proa()

# ------------------------------------------------------------------ final
for o in COL.objects:
    if o.type == 'MESH':
        fijar_suelo(o)
with open(os.path.join(AQUI, "vikingo_huellas.json"), "w") as f:
    json.dump([[round(a, 2), round(b, 2), round(r, 2)] for a, b, r in HUELLAS], f)
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in COL.objects if o.type == 'MESH')
print("VIKINGO:", len(COL.objects), "objetos,", tris, "triangulos,", len(HUELLAS), "huellas sin hierba")
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
