# Narrativa ambiental del exterior (provisional: se ajustara con la historia). Crea dos colecciones:
#   Narrativa_Exterior (se hornea con exportar_hd.py): bote volcado en la playa, farol roto en el muelle, linterna encendida
#       en la playa, valla caida junto al camino, tendedero con la ropa del cuidador, costillar de un barco hundido.
#   Narrativa_Detalles (NO se hornea; materiales propios en Unity): red seca sobre el bote, cristal de la linterna y llama,
#       cristales rotos, aranazos en la puerta de la torre, marcas de conteo en un poste del muelle y charcos.
# Texturas generadas: Assets/Textures/Narrativa/T_Aranazos.png, T_Conteo.png, T_RedSeca.png
# Uso: blender -b el_misterio_del_faro.blend --python scripts/narrativa_exterior.py -- --save   (re-ejecutable: rehace todo)
import bpy, bmesh, math, random, sys, os
import numpy as np
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
TEXD = os.path.join(RAIZ, "Assets", "Textures", "Narrativa")
os.makedirs(TEXD, exist_ok=True)
RUTA = os.path.join(os.path.dirname(os.path.abspath(bpy.data.filepath)), "scripts", "texturizar_faro.py")
exec(compile(open(RUTA, encoding="utf-8").read().split("# ------------------------------------------------------------------ materiales")[0], RUTA, "exec"))
rnd = random.Random(1871)
D = bpy.data


# ------------------------------------------------------------------ colecciones (se rehacen)
def coleccion(nombre):
    c = D.collections.get(nombre)
    if c:
        for o in list(c.objects):
            me = o.data if o.type == 'MESH' else None
            D.objects.remove(o)
            if me and me.users == 0:
                D.meshes.remove(me)
    else:
        c = D.collections.new(nombre)
        bpy.context.scene.collection.children.link(c)
    return c


CN = coleccion("Narrativa_Exterior")
CD = coleccion("Narrativa_Detalles")

# ------------------------------------------------------------------ suelo (isla, rocas, muelle)
dg = bpy.context.evaluated_depsgraph_get()


def bvh_de(nombres):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for nm in nombres:
        o = D.objects.get(nm)
        if not o or o.type != 'MESH':
            continue
        bm = bmesh.new()
        bm.from_object(o, dg)
        bm.transform(o.matrix_world)
        out.append(BVHTree.FromBMesh(bm))
    return out


SUELO = bvh_de(["IslandModel"] + [o.name for o in D.collections["Atrezzo_Exterior"].objects if o.name.startswith("Roca_")]
               + ["Muelle_Cubierta"])


def suelo(x, y, lista=None):
    best = None
    for b in (lista or SUELO):
        r = b.ray_cast(Vector((x, y, 100)), Vector((0, 0, -1)))
        if r[0] is not None and (best is None or r[0].z > best):
            best = r[0].z
    return best


# ------------------------------------------------------------------ utilidades de malla
def objeto(nombre, bm, mats, col, loc=(0, 0, 0), rot=(0, 0, 0), suave=False):
    me = D.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if suave:
        for p in me.polygons:
            p.use_smooth = True
    o = D.objects.new(nombre, me)
    col.objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    return o


def caja(bm, c, dims, rot=None, mat=0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r['verts']
    M = Matrix.Translation(Vector(c)) @ (rot.to_matrix().to_4x4() if rot else Matrix()) @ Matrix.Diagonal((*dims, 1))
    bmesh.ops.transform(bm, matrix=M, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mat
    return vs


def tubo(bm, pts, radio, segs=8, mat=0, cerrar=True):
    """tubo a lo largo de una polilinea; radio puede ser numero o lista"""
    pts = [Vector(p) for p in pts]
    anillos = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        a = t.cross(ref).normalized()
        b = t.cross(a).normalized()
        r = radio[i] if isinstance(radio, (list, tuple)) else radio
        anillos.append([bm.verts.new(p + r * (math.cos(2 * math.pi * k / segs) * a + math.sin(2 * math.pi * k / segs) * b)) for k in range(segs)])
    caras = []
    for i in range(len(anillos) - 1):
        for k in range(segs):
            f = bm.faces.new((anillos[i][k], anillos[i][(k + 1) % segs], anillos[i + 1][(k + 1) % segs], anillos[i + 1][k]))
            f.material_index = mat
            caras.append(f)
    if cerrar:
        for an in (anillos[0], anillos[-1][::-1]):
            f = bm.faces.new(an[::-1])
            f.material_index = mat
    return caras


def torno(bm, perfil, segs=16, mat=0, tapas=True, desde=0.0, hasta=2 * math.pi):
    """superficie de revolucion alrededor de Z: perfil = [(r, z), ...]"""
    completo = abs(hasta - desde - 2 * math.pi) < 1e-4
    n = segs if completo else segs + 1
    anillos = []
    for r, z in perfil:
        anillos.append([bm.verts.new((r * math.cos(desde + (hasta - desde) * k / segs), r * math.sin(desde + (hasta - desde) * k / segs), z)) for k in range(n)])
    for i in range(len(anillos) - 1):
        for k in range(segs):
            k2 = (k + 1) % n if completo else k + 1
            f = bm.faces.new((anillos[i][k], anillos[i][k2], anillos[i + 1][k2], anillos[i + 1][k]))
            f.material_index = mat
    if tapas and completo:
        if perfil[0][0] > 1e-4:
            bm.faces.new(anillos[0][::-1]).material_index = mat
        if perfil[-1][0] > 1e-4:
            bm.faces.new(anillos[-1]).material_index = mat
    return anillos


def solidificar(o, grosor):
    m = o.modifiers.new("sol", 'SOLIDIFY')
    m.thickness = grosor
    m.offset = 0
    with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
        bpy.ops.object.modifier_apply(modifier=m.name)


def mat(nombre):
    m = D.materials.get(nombre)
    if m is None:
        raise RuntimeError("falta material " + nombre)
    return m


# ------------------------------------------------------------------ materiales procedurales nuevos (para hornear)
def nuevo_mat(nombre):
    m = D.materials.get(nombre) or D.materials.new(nombre)
    nt, b = limpiar(m)
    return m, nt, b, K(nt)


def obj_coords(k):
    return k.n('ShaderNodeTexCoord').outputs['Object']


def mat_bote():
    m, nt, b, k = nuevo_mat("M_N_BotePintura")
    x, y, z = k.xyz(obj_coords(k))
    # tracas (tablas solapadas) a lo largo del casco: bandas en z local
    tr = k.mat_('FRACT', k.mat_('MULTIPLY', z, 9.0))
    linea = umbral_(k, tr, 0.9, 0.97)
    veta = k.noise(k.comb(k.mat_('MULTIPLY', x, 2.0), k.mat_('MULTIPLY', y, 30.0), k.mat_('MULTIPLY', z, 30.0)), 1.0, 6.0, 0.6)
    madera = k.rampa(veta, (0.16, 0.15, 0.13), (0.30, 0.28, 0.25))
    # pintura verde desvaida que se cae a placas
    pin = k.noise(k.comb(k.mat_('MULTIPLY', x, 2.5), k.mat_('MULTIPLY', y, 2.5), k.mat_('MULTIPLY', z, 2.5)), 1.4, 9.0, 0.65)
    mp = umbral_(k, pin, 0.47, 0.5)
    pintura = k.mix((0.13, 0.21, 0.19), (0.24, 0.30, 0.27), k.noise(k.comb(x, y, z), 3.0, 4.0, 0.5))
    col = k.mix(madera, pintura, mp)
    # patente rojiza en la obra viva (zona baja del casco)
    viva = rampa_(k, z, -0.42, -0.36, 1.0, 0.0)
    col = k.mix(col, k.mix((0.20, 0.07, 0.045), madera, umbral_(k, pin, 0.62, 0.66)), viva)
    col = k.mix(col, (0.02, 0.018, 0.015), k.mat_('MULTIPLY', linea, 0.85))
    # salitre y mugre
    sal = k.noise(k.comb(x, y, z), 6.0, 7.0, 0.6)
    col = k.mix(col, (0.55, 0.55, 0.5), k.mat_('MULTIPLY', umbral_(k, sal, 0.6, 0.75), 0.5))
    n = k.bump(k.mat_('ADD', k.mat_('MULTIPLY', mp, 0.4), k.mat_('SUBTRACT', 0.0, linea)), 0.6, 0.01)
    listo(b, col, n, 0.85, 0.0, k)
    return m


def mat_tela(nombre, c1, c2, rough, sucio=(0.30, 0.27, 0.2)):
    m, nt, b, k = nuevo_mat(nombre)
    x, y, z = k.xyz(obj_coords(k))
    trama = k.noise(k.comb(k.mat_('MULTIPLY', x, 140.0), k.mat_('MULTIPLY', y, 140.0), k.mat_('MULTIPLY', z, 140.0)), 1.0, 2.0, 0.5)
    man = k.noise(k.comb(k.mat_('MULTIPLY', x, 3.0), k.mat_('MULTIPLY', y, 3.0), k.mat_('MULTIPLY', z, 3.0)), 1.0, 6.0, 0.6)
    col = k.mix(c1, c2, man)
    col = k.mix(col, k.rampa(trama, (0.85, 0.85, 0.85), (1.05, 1.05, 1.05)), 1.0, 'MULTIPLY')
    # manchas de humedad / barro abajo (z local negativo: la prenda cuelga hacia abajo)
    abajo = rampa_(k, z, -1.0, -0.55, 0.6, 0.0)
    col = k.mix(col, sucio, k.mat_('MULTIPLY', abajo, k.mat_('ADD', 0.4, man)))
    listo(b, col, k.bump(trama, 0.3, 0.003), rough, 0.0, k)
    return m


def umbral_(k, v, a, b):
    return k.mat_('MULTIPLY', k.mat_('SUBTRACT', v, a, True), 1.0 / (b - a), True)


def rampa_(k, v, a, b, va, vb):
    mr = k.n('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = a
    mr.inputs['From Max'].default_value = b
    mr.inputs['To Min'].default_value = va
    mr.inputs['To Max'].default_value = vb
    mr.clamp = True
    k.l(v, mr.inputs['Value'])
    return mr.outputs[0]


M_BOTE = mat_bote()
M_HULE = mat_tela("M_N_Hule", (0.30, 0.22, 0.06), (0.20, 0.15, 0.05), 0.45, (0.12, 0.10, 0.06))
M_CAMISA = mat_tela("M_N_Camisa", (0.27, 0.25, 0.21), (0.19, 0.17, 0.14), 0.9, (0.12, 0.10, 0.07))
M_LANA = mat_tela("M_N_Lana", (0.05, 0.05, 0.055), (0.085, 0.08, 0.075), 0.95, (0.04, 0.035, 0.03))
MG, MM, MUS = mat("M_MaderaGris"), mat("M_MaderaMojada"), mat("M_Musgo")
MH, MO, ML, MC = mat("M_Hierro"), mat("M_Oxido"), mat("M_Laton"), mat("M_Canamo")


# materiales de Narrativa_Detalles: solo nombre y color (Unity les pone su shader)
def mat_simple(nombre, color):
    m = D.materials.get(nombre) or D.materials.new(nombre)
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    return m


MD_RED = mat_simple("M_N_RedSeca", (0.25, 0.24, 0.18))
MD_VIDRIO = mat_simple("M_N_Vidrio", (0.5, 0.55, 0.5))
MD_LLAMA = mat_simple("M_N_Llama", (1.0, 0.6, 0.25))
MD_ARA = mat_simple("M_N_Aranazos", (0.4, 0.3, 0.2))
MD_CONTEO = mat_simple("M_N_Conteo", (0.1, 0.08, 0.06))
MD_CHARCO = mat_simple("M_N_Charco", (0.02, 0.025, 0.03))


# ------------------------------------------------------------------ 1. bote volcado en la playa
def bote():
    L, B, P = 4.2, 1.45, 0.62
    nu, nt = 40, 20
    bm = bmesh.new()
    filas = []
    ts = [-0.92 + 1.92 * i / nu for i in range(nu + 1)]
    for t in ts:
        if t >= 0:
            w = B / 2 * max(1 - t * t, 0.0) ** 0.72
        else:
            w = B / 2 * max(1 - abs(t) ** 5, 0.0) ** 0.5
        w = max(w, 0.012)
        d = P * (1 - 0.3 * t * t)
        zg = 0.10 * t * t + (0.10 * (t - 0.75) / 0.25 if t > 0.75 else 0.0)
        fila = []
        for j in range(nt + 1):
            th = math.pi * j / nt
            y = w * math.cos(th)
            z = zg - d * (math.sin(th) ** 0.85) * (w / (B / 2)) ** 0.25
            fila.append(bm.verts.new((t * L / 2, y, z)))
        filas.append(fila)
    for i in range(nu):
        for j in range(nt):
            bm.faces.new((filas[i][j], filas[i][j + 1], filas[i + 1][j + 1], filas[i + 1][j]))
    # espejo de popa
    bm.faces.new(filas[0])
    o = objeto("Bote_Volcado", bm, [M_BOTE], CN, suave=True)
    solidificar(o, 0.03)
    # quilla y regala
    bm = bmesh.new()
    bm.from_mesh(o.data)
    quilla = []
    for t in ts[::4]:
        d = P * (1 - 0.3 * t * t)
        zg = 0.10 * t * t + (0.10 * (t - 0.75) / 0.25 if t > 0.75 else 0.0)
        w = B / 2 * max(1 - t * t, 0.0) ** 0.72 if t >= 0 else B / 2 * max(1 - abs(t) ** 5, 0.0) ** 0.5
        quilla.append((t * L / 2, 0, zg - d * (max(w, 0.012) / (B / 2)) ** 0.25 - 0.03))
    tubo(bm, quilla, 0.045, 4, 0)
    for lado in (1, -1):
        reg = []
        for t in ts[::2]:
            w = B / 2 * max(1 - t * t, 0.0) ** 0.72 if t >= 0 else B / 2 * max(1 - abs(t) ** 5, 0.0) ** 0.5
            zg = 0.10 * t * t + (0.10 * (t - 0.75) / 0.25 if t > 0.75 else 0.0)
            reg.append((t * L / 2, lado * (max(w, 0.012) + 0.015), zg))
        tubo(bm, reg, 0.03, 6, 0)
    bm.to_mesh(o.data)
    bm.free()
    # boca abajo, apoyado en un lado sobre un tronco
    x, y = -13.0, -31.2
    z = suelo(x, y)
    o.rotation_euler = Euler((math.pi + math.radians(9), math.radians(-3), math.radians(28)), 'XYZ')
    o.location = (x, y, z + 0.22)
    # tronco de deriva bajo un costado
    bm = bmesh.new()
    pts = [(-1.1 + 2.2 * i / 6, 0.03 * math.sin(i * 1.3), 0) for i in range(7)]
    tubo(bm, pts, [0.11, 0.13, 0.12, 0.12, 0.11, 0.1, 0.07], 8, 0)
    xl, yl = x + 0.55 * math.cos(math.radians(28 + 90)), y + 0.55 * math.sin(math.radians(28 + 90))
    objeto("Tronco_Deriva", bm, [MM], CN, (xl, yl, suelo(xl, yl) + 0.06), (0, 0, math.radians(28 + 8)), suave=True)
    return o


BOTE = bote()


# ------------------------------------------------------------------ 2. red seca sobre el bote (malla que cae sobre el)
def red_seca():
    dg2 = bpy.context.evaluated_depsgraph_get()
    bv = bvh_de(["Bote_Volcado", "Tronco_Deriva", "IslandModel"])
    c = BOTE.location
    a = BOTE.rotation_euler.z
    ex, ey = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    nx, ny = 18, 24
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            u, v = 0.2 + 1.6 * i / nx, -1.15 + 2.3 * j / ny
            p = c + ex * u + ey * v
            p.x += rnd.uniform(-0.02, 0.02)
            p.y += rnd.uniform(-0.02, 0.02)
            best = None
            for b in bv:
                r = b.ray_cast(Vector((p.x, p.y, c.z + 5)), Vector((0, 0, -1)))
                if r[0] is not None and (best is None or r[0].z > best):
                    best = r[0].z
            z = (best if best is not None else c.z) + 0.025 + rnd.uniform(0, 0.03)
            vs[i, j] = bm.verts.new((p.x, p.y, z))
    for i in range(nx):
        for j in range(ny):
            f = bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
            for l, (a2, b2) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uvl].uv = (a2 / nx * 16, b2 / ny * 23)
    objeto("Red_Seca", bm, [MD_RED], CD, suave=True)


red_seca()


# ------------------------------------------------------------------ 3. linternas de tormenta (una encendida, otra rota)
PERFIL_BASE = [(0.0, 0.0), (0.085, 0.0), (0.09, 0.012), (0.09, 0.05), (0.075, 0.06)]
PERFIL_GLOBO = [(0.06, 0.06), (0.078, 0.09), (0.085, 0.14), (0.075, 0.19), (0.05, 0.215)]
PERFIL_TAPA = [(0.055, 0.215), (0.09, 0.225), (0.085, 0.24), (0.045, 0.28), (0.03, 0.30), (0.0, 0.305)]


def linterna(nombre, roto=False):
    bm = bmesh.new()
    torno(bm, PERFIL_BASE, 18, 0)
    torno(bm, PERFIL_TAPA, 18, 0 if not roto else 1)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        pts = [(0.098 * math.cos(a) * (1 + 0.15 * math.sin(math.pi * s / 6)), 0.098 * math.sin(a) * (1 + 0.15 * math.sin(math.pi * s / 6)), 0.055 + 0.17 * s / 6) for s in range(7)]
        if roto and k == 1:
            pts = pts[:3]
        tubo(bm, pts, 0.005, 5, 1)
    # asa
    asa = [(0.0, 0.09 * math.cos(math.pi * s / 10), 0.30 + 0.09 * math.sin(math.pi * s / 10)) for s in range(11)]
    tubo(bm, asa, 0.004, 5, 0)
    bmesh.ops.scale(bm, vec=(ESC, ESC, ESC), verts=bm.verts)
    return bm


ESC = 1.35          # tamano de las linternas (las de tormenta miden ~40 cm con el asa)


def lampara_encendida():
    x, y = -2.6, -30.6
    z = suelo(x, y)
    o = objeto("Linterna_Encendida", linterna("a"), [MH, MO], CN, (x, y, z - 0.005), (0.03, -0.04, 0.6))
    bm = bmesh.new()
    torno(bm, PERFIL_GLOBO, 18, 0)
    bmesh.ops.scale(bm, vec=(ESC, ESC, ESC), verts=bm.verts)
    g = objeto("Linterna_Cristal", bm, [MD_VIDRIO], CD, o.location.copy(), o.rotation_euler.copy(), suave=True)
    bm = bmesh.new()
    torno(bm, [(0.0, 0.085), (0.008, 0.095), (0.011, 0.11), (0.006, 0.13), (0.0, 0.145)], 10, 0)
    bmesh.ops.scale(bm, vec=(ESC, ESC, ESC), verts=bm.verts)
    objeto("Linterna_Llama", bm, [MD_LLAMA], CD, o.location.copy(), o.rotation_euler.copy(), suave=True)
    print("LINTERNA ENCENDIDA en", tuple(round(v, 2) for v in o.location))


def farol_roto():
    x, y = 1.15, -44.6
    z = suelo(x, y)
    o = objeto("Farol_Roto", linterna("b", True), [MH, MO], CN, (x, y, z + 0.09 * ESC),(math.radians(88), math.radians(6), math.radians(-35)))
    # cristales rotos por la cubierta
    bm = bmesh.new()
    for i in range(16):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0.12, 0.7) ** 1.3
        cx, cy = x + r * math.cos(a), y + r * math.sin(a)
        cz = (suelo(cx, cy) or z) + 0.004
        s = rnd.uniform(0.012, 0.045)
        ps = [(cx + s * math.cos(b) * rnd.uniform(0.5, 1.2), cy + s * math.sin(b) * rnd.uniform(0.5, 1.2), cz) for b in (0, 2.1 + rnd.uniform(-0.4, 0.4), 4.2 + rnd.uniform(-0.4, 0.4))]
        bm.faces.new([bm.verts.new(p) for p in ps])
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.003)
    objeto("Cristales_Rotos", bm, [MD_VIDRIO], CD)


lampara_encendida()
farol_roto()


# ------------------------------------------------------------------ 4. valla caida junto al camino
def valla_caida():
    x0, y0 = -4.2, -12.5
    bm = bmesh.new()
    # poste 1 en pie, poste 2 inclinado, poste 3 en el suelo; un travesano aun clavado y otro caido
    caja(bm, (0, 0, 0.6), (0.12, 0.12, 1.3))
    caja(bm, (0, 2.0, 0.45), (0.12, 0.12, 1.3), Euler((math.radians(38), math.radians(8), 0)))
    caja(bm, (0.35, 4.1, 0.07), (0.12, 1.3, 0.12), Euler((0, 0, math.radians(15))))
    caja(bm, (0, 1.0, 0.95), (0.05, 2.15, 0.09), Euler((math.radians(-14), 0, 0)))
    caja(bm, (0.4, 2.9, 0.05), (0.05, 2.1, 0.09), Euler((math.radians(90), 0, math.radians(-12))))
    caja(bm, (-0.25, 1.4, 0.04), (0.05, 1.2, 0.09), Euler((math.radians(85), 0, math.radians(20))))   # trozo partido
    # cuerda vieja colgando del primer poste
    tubo(bm, [(0.07, 0.0, 1.05), (0.09, 0.1, 0.85), (0.1, 0.18, 0.6), (0.15, 0.25, 0.4)], 0.012, 6, 1)
    o = objeto("Valla_Caida", bm, [MG, MC], CN, (x0, y0, suelo(x0, y0) - 0.1), (0, 0, math.radians(-4)))
    return o


valla_caida()


# ------------------------------------------------------------------ 5. tendedero con la ropa del cuidador
def catenaria(a, b, flecha, n=16):
    return [a.lerp(b, i / n) - Vector((0, 0, flecha * 4 * (i / n) * (1 - i / n))) for i in range(n + 1)]


def prenda(nombre, piezas, matp, punto, dirl):
    """piezas: rectangulos (u0, v0, u1, v1, giro) en el plano de la prenda (u a lo largo de la cuerda, v hacia abajo)"""
    bm = bmesh.new()
    fase = rnd.uniform(0, 6)
    for pi_, (u0, v0, u1, v1, giro) in enumerate(piezas):
        nu, nv = max(2, int((u1 - u0) / 0.04)), max(2, int((v1 - v0) / 0.04))
        g = {}
        for i in range(nu + 1):
            for j in range(nv + 1):
                u, v = u0 + (u1 - u0) * i / nu, v0 + (v1 - v0) * j / nv
                # giro de la manga alrededor de su hombro (u0, v0)
                cu, sv = math.cos(giro), math.sin(giro)
                du, dv = u - u0, v - v0
                u2, v2 = u0 + du * cu - dv * sv, v0 + du * sv + dv * cu
                w = 0.03 * math.sin(u2 * 22 + fase) * min(1, v2 * 3) + 0.04 * v2 * math.sin(fase + v2 * 3) + (0.018 if pi_ else 0.0)
                g[i, j] = bm.verts.new((u2, w, -v2))
        for i in range(nu):
            for j in range(nv):
                bm.faces.new((g[i, j], g[i + 1, j], g[i + 1, j + 1], g[i, j + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.005)
    a = math.atan2(dirl.y, dirl.x)
    o = objeto(nombre, bm, [matp], CN, punto, (0, 0, a), suave=True)
    solidificar(o, 0.01)
    return o


def tendedero():
    A, Bp = Vector((18.6, 86.8, 0)), Vector((19.4, 94.6, 0))
    A.z, Bp.z = suelo(A.x, A.y), suelo(Bp.x, Bp.y)
    dirl = (Bp - A).normalized()
    lado = Vector((-dirl.y, dirl.x, 0))
    bm = bmesh.new()
    for P, inc in ((A, 4), (Bp, -6)):
        rot = Euler((math.radians(inc), 0, math.atan2(dirl.y, dirl.x)))
        caja(bm, P + Vector((0, 0, 1.0)), (0.12, 0.12, 2.4), rot)
        caja(bm, P + Vector((0, 0, 2.05)), (0.08, 0.9, 0.08), Euler((0, 0, math.atan2(dirl.y, dirl.x))))
    objeto("Tendedero_Postes", bm, [MG], CN)
    a, b = A + Vector((0, 0, 2.08)) + lado * 0.3, Bp + Vector((0, 0, 2.08)) + lado * 0.3
    linea = catenaria(a, b, 0.32)
    bm = bmesh.new()
    tubo(bm, linea, 0.007, 6, 0)
    a2, b2 = A + Vector((0, 0, 2.08)) - lado * 0.3, Bp + Vector((0, 0, 2.08)) - lado * 0.3
    linea2 = catenaria(a2, b2, 0.12, 12)
    tubo(bm, linea2[:7] + [linea2[7] - Vector((0, 0, 0.5)), linea2[7] - Vector((0, 0, 1.2))], 0.007, 6, 0)   # una cuerda rota que cuelga
    objeto("Tendedero_Cuerdas", bm, [MC], CN)

    def en(s):
        i = s * (len(linea) - 1)
        return linea[int(i)].lerp(linea[min(int(i) + 1, len(linea) - 1)], i - int(i))
    # abrigo de hule (el impermeable del cuidador), camisa y pantalon
    prenda("Ropa_Abrigo", [(-0.30, 0.0, 0.30, 1.05, 0), (-0.30, 0.02, -0.16, 0.62, math.radians(12)), (0.16, 0.02, 0.30, 0.62, math.radians(-12))], M_HULE, en(0.27), dirl)
    prenda("Ropa_Camisa", [(-0.24, 0.0, 0.24, 0.72, 0), (-0.24, 0.02, -0.10, 0.45, math.radians(25)), (0.10, 0.02, 0.24, 0.45, math.radians(-25))], M_CAMISA, en(0.55), dirl)
    prenda("Ropa_Pantalon", [(-0.21, 0.0, 0.21, 0.22, 0), (-0.21, 0.2, -0.01, 0.95, math.radians(3)), (0.01, 0.2, 0.21, 0.95, math.radians(-3))], M_LANA, en(0.78), dirl)


tendedero()


# ------------------------------------------------------------------ 6. costillar de un barco hundido junto a la costa
def costillar():
    bm = bmesh.new()
    L = 11.0
    quilla = [(0, L * s / 10 - L / 2, -0.15 * math.sin(math.pi * s / 10)) for s in range(11)]
    tubo(bm, quilla, 0.16, 4, 0)
    tubo(bm, [(0, L / 2, 0), (0, L / 2 + 0.6, 0.8), (0, L / 2 + 0.9, 2.2), (0, L / 2 + 0.85, 3.0)], 0.13, 4, 0)    # roda
    for i in range(12):
        yy = -L / 2 + 0.6 + i * (L - 1.2) / 11
        t = yy / (L / 2)
        w = 2.1 * (1 - t * t) ** 0.6 + 0.3
        alto = 2.6 + rnd.uniform(-0.2, 0.2)
        for lado in (1, -1):
            if rnd.random() < 0.25:
                continue                       # costilla perdida
            corte = 1.0 if rnd.random() > 0.4 else rnd.uniform(0.4, 0.8)
            pts = []
            for s in range(9):
                f = s / 8 * corte
                ang = f * math.pi / 2
                pts.append((lado * w * math.sin(ang) * (1 + 0.15 * f), yy + rnd.uniform(-0.02, 0.02), alto * (1 - math.cos(ang)) * 0.95))
            tubo(bm, pts, 0.13 - 0.03 * corte * 0.5, 5, 0)
    # algunas tablas del forro que quedan abajo
    for lado in (1, -1):
        for k in range(2):
            ang = (0.25 + 0.18 * k) * math.pi / 2
            for seg in range(3):
                if rnd.random() < 0.35:
                    continue
                y0 = -L / 2 + 1.5 + seg * 2.8
                pts = []
                for s in range(6):
                    yy = y0 + 2.4 * s / 5
                    t = yy / (L / 2)
                    w = 2.1 * (1 - t * t) ** 0.6 + 0.3
                    pts.append((lado * (w * math.sin(ang) + 0.1), yy, 2.6 * (1 - math.cos(ang)) * 0.95))
                tubo(bm, pts, 0.05, 4, 1)
    o = objeto("Naufragio_Costillar", bm, [MM, MUS], CN, (-19.5, -45.5, -1.2),(math.radians(-5), math.radians(17), math.radians(62)))
    return o


costillar()


# ------------------------------------------------------------------ 7. texturas: aranazos, conteo, red
def guardar_rgba(nombre, arr):
    h, w, _ = arr.shape
    img = D.images.new(nombre, w, h, alpha=True)
    img.pixels.foreach_set(arr[::-1].astype(np.float32).ravel())
    img.filepath_raw = os.path.join(TEXD, nombre + ".png")
    img.file_format = 'PNG'
    img.save()
    D.images.remove(img)


def trazo(arr, p0, p1, ancho0, ancho1, color, alfa=1.0, irregular=0.35, seed=0):
    h, w, _ = arr.shape
    r = random.Random(seed)
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1])) * 1.5) + 2
    yy, xx = np.mgrid[0:h, 0:w]
    for i in range(n):
        f = i / (n - 1)
        x = p0[0] + (p1[0] - p0[0]) * f + r.uniform(-1, 1) * irregular
        y = p0[1] + (p1[1] - p0[1]) * f + r.uniform(-1, 1) * irregular
        rad = ancho0 + (ancho1 - ancho0) * f
        rad *= 0.8 + 0.4 * r.random()
        x0, x1, y0, y1 = int(max(0, x - rad - 2)), int(min(w, x + rad + 3)), int(max(0, y - rad - 2)), int(min(h, y + rad + 3))
        d = np.sqrt((xx[y0:y1, x0:x1] - x) ** 2 + (yy[y0:y1, x0:x1] - y) ** 2)
        a = np.clip(rad - d + 0.5, 0, 1) * alfa
        sub = arr[y0:y1, x0:x1]
        for c in range(3):
            sub[..., c] = sub[..., c] * (1 - a) + color[c] * a
        sub[..., 3] = np.maximum(sub[..., 3], a)


def tex_aranazos():
    S = 1024
    arr = np.zeros((S, S, 4), np.float32)
    r = random.Random(7)
    grupos = [((300, 180), 1.18, 520), ((640, 330), 1.32, 430), ((420, 560), 1.05, 360), ((760, 640), 1.25, 260)]
    for gi, ((cx, cy), ang, largo) in enumerate(grupos):
        dx, dy = math.cos(ang), math.sin(ang)
        px, py = -dy, dx
        for k in range(4):
            off = (k - 1.5) * 26 + r.uniform(-4, 4)
            l = largo * r.uniform(0.75, 1.0)
            x0, y0 = cx + px * off, cy + py * off
            x1, y1 = x0 + dx * l, y0 + dy * l
            # borde oscuro y fondo claro (madera viva bajo la superficie gris)
            trazo(arr, (x0, y0), (x1, y1), 12.0, 2.0, (0.03, 0.025, 0.02), 0.95, 1.6, gi * 10 + k)
            trazo(arr, (x0, y0), (x1, y1), 6.0, 0.8, (0.50, 0.37, 0.22), 1.0, 1.2, gi * 10 + k + 100)
    guardar_rgba("T_Aranazos", arr)


def tex_conteo():
    W, H = 1024, 512
    arr = np.zeros((H, W, 4), np.float32)
    x = 60
    marcas = 23
    k = 0
    r = random.Random(3)
    while k < marcas:
        grupo = min(5, marcas - k)
        x0 = x
        for i in range(min(grupo, 4)):
            xx = x + i * 34 + r.uniform(-4, 4)
            trazo(arr, (xx + r.uniform(-6, 6), 90 + r.uniform(-12, 12)), (xx + r.uniform(-6, 6), 400 + r.uniform(-15, 15)), 7, 5, (0.40, 0.31, 0.20), 1.0, 1.2, k * 3 + i)
        if grupo == 5:
            trazo(arr, (x0 - 20, 330 + r.uniform(-10, 10)), (x0 + 125, 150 + r.uniform(-10, 10)), 7, 5, (0.40, 0.31, 0.20), 1.0, 1.2, k * 7)
        k += grupo
        x += 200
    guardar_rgba("T_Conteo", arr)


def tex_red():
    S = 256
    yy, xx = np.mgrid[0:S, 0:S] / S
    # malla de rombos: dos familias de hilos diagonales + nudos
    a = np.abs(((xx + yy) % 1.0) - 0.5)
    b = np.abs(((xx - yy) % 1.0) - 0.5)
    hilo = np.clip((0.035 - np.minimum(0.5 - a, a)) * 60, 0, 1)
    hilo2 = np.clip((0.035 - np.minimum(0.5 - b, b)) * 60, 0, 1)
    alfa = np.maximum(hilo, hilo2)
    nudo = np.clip((0.07 - np.sqrt((np.minimum(xx, 1 - xx)) ** 2 + (np.minimum(yy, 1 - yy)) ** 2)) * 30, 0, 1)
    nudo = np.maximum(nudo, np.clip((0.07 - np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2)) * 30, 0, 1))
    alfa = np.maximum(alfa, nudo)
    rng = np.random.default_rng(5)
    ruido = rng.random((S, S)) * 0.15
    arr = np.zeros((S, S, 4), np.float32)
    arr[..., 0] = 0.22 + ruido
    arr[..., 1] = 0.21 + ruido
    arr[..., 2] = 0.15 + ruido * 0.8
    arr[..., 3] = alfa
    guardar_rgba("T_RedSeca", arr)


tex_aranazos()
tex_conteo()
tex_red()


# ------------------------------------------------------------------ 8. calcomanias: aranazos en la puerta y conteo en un poste
def calco(nombre, matc, centro, normal, arriba, ancho, alto):
    n = normal.normalized()
    r = arriba.cross(n).normalized()
    u = n.cross(r).normalized()
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(centro + r * sx * ancho / 2 + u * sy * alto / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        l[uvl].uv = uv
    return objeto(nombre, bm, [matc], CD)


def superficie(objs, origen, dirc):
    best = None
    for b in bvh_de(objs):
        r = b.ray_cast(origen, dirc)
        if r[0] is not None and (best is None or (r[0] - origen).length < (best[0] - origen).length):
            best = r
    return best


def calcos():
    # puerta exterior de la cabana (al final del camino, con escalones): se busca con un rayo desde fuera
    hit = superficie([o.name for o in D.collections["Faro_Cabana"].objects if o.type == 'MESH'], Vector((16.0, 97.4, 8.85)), Vector((-1, 0, 0)))
    if hit:
        nrm = Vector((hit[1].x, hit[1].y, 0)).normalized()
        if nrm.x < 0:
            nrm = -nrm                     # que mire hacia fuera (hacia donde vino el rayo)
        calco("Aranazos_Puerta", MD_ARA, hit[0] + nrm * 0.035, nrm, Vector((0, 0, 1)), 0.75, 0.75)
        print("ARANAZOS en", tuple(round(v, 2) for v in hit[0]))
    else:
        print("ARANAZOS: no se encontro la puerta")
    # poste del muelle mas cercano a donde empieza el jugador, cara hacia el centro de la cubierta
    ba = D.objects["Muelle_Barandas"]
    bm = bmesh.new()
    bm.from_mesh(ba.data)
    bm.transform(ba.matrix_world)
    bm.verts.ensure_lookup_table()
    visto, mejores = set(), []
    for v in bm.verts:
        if v.index in visto:
            continue
        pila, vs = [v], []
        visto.add(v.index)
        while pila:
            x = pila.pop()
            vs.append(x)
            for e in x.link_edges:
                w = e.other_vert(x)
                if w.index not in visto:
                    visto.add(w.index)
                    pila.append(w)
        xs, ys, zs = [q.co.x for q in vs], [q.co.y for q in vs], [q.co.z for q in vs]
        if len(vs) == 8 and max(zs) - min(zs) > 0.8 and max(xs) - min(xs) < 0.5 and max(ys) - min(ys) < 0.5:
            mejores.append(Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2)))
    bm.free()
    obj = Vector((-1.5, -49.0, 0))
    mejores.sort(key=lambda p: (p.x + 2.4) ** 2 + (p.y + 50.5) ** 2)
    p = mejores[0]
    hacia = Vector((-math.copysign(1, p.x), 0, 0))
    hit = superficie(["Muelle_Barandas"], Vector((p.x + hacia.x * 1.0, p.y, p.z + 0.05)), -hacia)
    if hit:
        nc = hit[1] if hit[1].dot(hacia) > 0 else -hit[1]
        calco("Marcas_Conteo", MD_CONTEO, hit[0] + nc * 0.004, nc, Vector((0, 0, 1)), 0.22, 0.30)
        print("CONTEO en", tuple(round(v, 2) for v in hit[0]))
    else:
        print("CONTEO: no se encontro el poste")


calcos()


# ------------------------------------------------------------------ 9. charcos (siguen el suelo; uv.x = 0 en el borde, 1 en el centro)
def charco(i, x, y, R):
    hs = [suelo(x + R * math.cos(a), y + R * math.sin(a), SUELO[:-1]) for a in [k * math.pi / 4 for k in range(8)]]
    hc = suelo(x, y, SUELO[:-1])
    if hc is None or any(h is None for h in hs) or max(hs) - min(hs) > 0.35:
        print("CHARCO omitido", x, y)
        return
    n, anillos = 36, 5
    fase = [rnd.uniform(0, 6.28) for _ in range(3)]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rad = [R * (1 + 0.22 * math.sin(2 * a + fase[0]) + 0.12 * math.sin(3 * a + fase[1]) + 0.07 * math.sin(5 * a + fase[2])) for a in [2 * math.pi * k / n for k in range(n)]]
    filas = []
    for an in range(anillos + 1):
        f = 1 - an / anillos
        fila = []
        for k in range(n if an < anillos else 1):
            a = 2 * math.pi * k / n
            px, py = x + rad[k] * f * math.cos(a), y + rad[k] * f * math.sin(a)
            pz = suelo(px, py, SUELO[:-1])
            fila.append((bm.verts.new((px, py, (pz if pz is not None else hc) + 0.02)), an / anillos))
        filas.append(fila)
    for an in range(anillos):
        for k in range(n):
            if an < anillos - 1:
                q = (filas[an][k], filas[an][(k + 1) % n], filas[an + 1][(k + 1) % n], filas[an + 1][k])
            else:
                q = (filas[an][k], filas[an][(k + 1) % n], filas[anillos][0])
            fc = bm.faces.new([v for v, _ in q])
            for l, (_, e) in zip(fc.loops, q):
                l[uvl].uv = (min(1.0, e * 1.6), (i * 0.137) % 1.0)
    objeto("Charco_%d" % i, bm, [MD_CHARCO], CD)


for i, (x, y, R) in enumerate([(0.7, -18.5, 1.3), (1.9, -14.2, 0.8), (1.5, 16.5, 1.1), (3.4, 63.5, 1.4),
                               (12.6, 88.6, 1.0), (8.3, 99.4, 1.5), (2.2, 96.2, 1.1), (6.5, -31.2, 0.9), (-1.0, 22.0, 0.9)]):
    charco(i, x, y, R)

print("NARRATIVA:", len(CN.objects), "objetos horneables,", len(CD.objects), "detalles")
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
