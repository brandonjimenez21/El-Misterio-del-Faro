# Relieve real del terreno de la isla ("IslandModel"). La malla original es muy gruesa (aristas de 2-5 m) y lisa:
# de noche el suelo parecia una alfombra plana y las rocas grandes, formas de plastilina.
#  1) Guarda una copia de la malla sin relieve ("IslandModel_SinRelieve") y SIEMPRE parte de ella (se puede repetir sin acumular).
#  2) Subdivide solo lo que esta fuera del agua (suelo: aristas de ~1 m, roca: ~0.65 m). Las UV se conservan.
#  3) Desplaza los vertices:
#       - suelo (hierba, tierra, arena alta): lomas, monticulos y baches (hacia arriba/abajo)
#       - roca (pendientes): bloques fracturados, estratos y aristas (a lo largo de la normal)
#     NO toca: lo que esta bajo el agua y la orilla, ni el suelo alrededor de cualquier objeto apoyado en la isla
#     (cabana, torre, postes, vallas, arboles, rocas del atrezzo, charcos, caminos ocultos...). El camino queda casi liso y algo hundido.
#     Camino principal (camino_lib.py): malla mas fina (aristas de ~0.45 m), borde ondulado, hombros algo levantados y
#     baches de 1-2 m donde se junta el agua de lluvia.
#  4) Guarda en una segunda UV ("Datos") dos datos para el shader Faro/IslaDetalle:
#       U = pendiente ORIGINAL (para que hierba / tierra / arena / roca sigan estando donde estaban)
#       V = cuanto subio o bajo el suelo (0.5 = nada): los huecos se oscurecen y juntan agua antes
#     y en una tercera UV ("Camino"): U = 1 en el eje del camino principal ... 0 a 6 m (con el borde ya ondulado),
#       V = baches (0..1): el shader pone ahi los charcos y la tierra / hierba pisada a los lados
#  5) Si el terreno ya tenia relieve, las rocas y ramas sueltas (Vegetacion_Isla) suben o bajan con el suelo nuevo.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/relieve_terreno.py -- --save
#      --quitar  deja la malla original (sin relieve)      --fuerza 1.0  multiplica la altura del relieve
# Despues: pasto_y_rocas.py (la hierba y las rocas se apoyan en el terreno nuevo), exportar_isla.py y exportar_vegetacion.py
import bpy, bmesh, math, sys, time, os, json
import numpy as np
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camino_lib, apoyo_lib

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opcion(nombre, defecto):
    return float(args[args.index(nombre) + 1]) if nombre in args else defecto


FUERZA = opcion("--fuerza", 1.0)
L_SUELO = opcion("--arista-suelo", 1.0)     # arista maxima en el suelo (m)
L_ROCA = opcion("--arista-roca", 0.65)      # arista maxima en la roca (m)
L_CAMINO = opcion("--arista-camino", 0.45)  # arista maxima en el camino principal y sus bordes (m)
R_CAMINO = 3.4                              # hasta que distancia del eje se usa la malla fina (m)
Z_SUBDIV = -1.2                             # por debajo de esta altura no se subdivide (esta bajo el agua)
CEL = 0.5                                   # celda de la mascara de objetos (m)
BASE = "IslandModel_SinRelieve"
# "Vikingo_Antiguo" se coloco sobre el terreno CON relieve (vikingos.py): si contara como apoyado, el suelo volveria a quedar liso debajo
NO_APOYAN = {"Isla", "Vegetacion_Isla", "Oceano", "Niebla_Baja", "Faro_Haz", "Referencia_Layout", "Figura_Anciano", "Figura_Cuidador", "Caminos", "Vikingo_Antiguo"}

t0 = time.time()
S = bpy.context.scene
I = bpy.data.objects["IslandModel"]
bpy.context.view_layer.update()
MW = I.matrix_world.copy()

# ------------------------------------------------------------------ malla de partida (siempre la original)
nombre_malla = I.data.name
base = bpy.data.meshes.get(BASE)
if base is None:
    if I.get("relieve"):
        raise SystemExit("RELIEVE: la malla ya tiene relieve y falta la copia original '%s'" % BASE)
    base = I.data.copy()
    base.name = BASE
    base.use_fake_user = True
vieja = I.data
# el terreno tal como estaba (si ya tenia relieve): para mover despues las rocas sueltas lo mismo que cambie el suelo
ANTES = apoyo_lib.arbol(vieja, MW) if (I.get("relieve") and vieja != base and "--quitar" not in args) else None
nueva = base.copy()
I.data = nueva
if vieja != base and vieja.users == 0:
    bpy.data.meshes.remove(vieja)
nueva.name = nombre_malla
if "--quitar" in args:
    I["relieve"] = 0
    print("RELIEVE quitado: %d triangulos" % len(nueva.polygons))
    if "--save" in args:
        bpy.ops.wm.save_mainfile()
    raise SystemExit(0)

bm = bmesh.new()
bm.from_mesh(nueva)
bm.transform(MW)                 # se trabaja en metros, en el mundo
bm.normal_update()
tris0 = len(bm.faces)


def suave(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ mascara: suelo junto a objetos apoyados en la isla
bvh0 = BVHTree.FromBMesh(bm)
xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]
X0, Y0 = min(xs) - 2, min(ys) - 2
NX, NY = int((max(xs) + 2 - X0) / CEL) + 1, int((max(ys) + 2 - Y0) / CEL) + 1
ocupado = np.zeros((NY, NX), dtype=bool)
dg = bpy.context.evaluated_depsgraph_get()
n_obj = 0
for col in bpy.data.collections:
    if col.name in NO_APOYAN:
        continue
    for o in col.objects:
        if o.type != 'MESH':
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        if me is None or len(me.vertices) == 0:
            continue
        me.calc_loop_triangles()
        mw = np.array(o.matrix_world)
        co = np.empty(len(me.vertices) * 3, dtype=np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        pts = [co]
        if len(me.loop_triangles):
            tri = np.empty(len(me.loop_triangles) * 3, dtype=np.int32)
            me.loop_triangles.foreach_get("vertices", tri)
            T = co[tri.reshape(-1, 3)]                                    # (n, 3, 3)
            largo = np.maximum(np.linalg.norm(T[:, 0] - T[:, 1], axis=1),
                               np.maximum(np.linalg.norm(T[:, 1] - T[:, 2], axis=1), np.linalg.norm(T[:, 2] - T[:, 0], axis=1)))
            for k in np.nonzero(largo > 0.6)[0]:                          # caras grandes: puntos repartidos por dentro
                n = int(min(80, math.ceil(largo[k] / 0.4)))
                u, v = np.meshgrid(np.arange(n + 1) / n, np.arange(n + 1) / n)
                m = (u + v) <= 1.0
                u, v = u[m][:, None], v[m][:, None]
                pts.append(T[k, 0] * (1 - u - v) + T[k, 1] * u + T[k, 2] * v)
        ev.to_mesh_clear()
        P = np.concatenate(pts)
        # solo lo que esta dentro de la isla y, agrupado en celdas de 25 cm, a menos de 1.2 m de la superficie
        P = P[(P[:, 0] > X0) & (P[:, 1] > Y0) & (P[:, 0] < X0 + NX * CEL) & (P[:, 1] < Y0 + NY * CEL) & (P[:, 2] > Z_SUBDIV - 1)]
        if len(P) == 0:
            continue
        P = np.unique(np.round(P / 0.25).astype(np.int32), axis=0) * 0.25
        toca = False
        for p in P:
            r = bvh0.find_nearest(Vector(p), 1.2)
            if r[0] is not None:
                ocupado[int((p[1] - Y0) / CEL), int((p[0] - X0) / CEL)] = True
                toca = True
        n_obj += toca
dist = np.full(ocupado.shape, 99.0)
dist[ocupado] = 0
cur = ocupado.copy()
for k in range(1, 9):
    d = cur.copy()
    d[1:, :] |= cur[:-1, :]; d[:-1, :] |= cur[1:, :]; d[:, 1:] |= cur[:, :-1]; d[:, :-1] |= cur[:, 1:]
    if k % 2 == 0:
        d[1:, 1:] |= cur[:-1, :-1]; d[:-1, :-1] |= cur[1:, 1:]; d[1:, :-1] |= cur[:-1, 1:]; d[:-1, 1:] |= cur[1:, :-1]
    dist[d & ~cur] = k * CEL
    cur = d
t = np.clip((dist - 0.75) / 2.0, 0, 1)
masc = t * t * (3 - 2 * t)
for _ in range(2):                                                         # sin escalones
    masc = (masc + np.roll(masc, 1, 0) + np.roll(masc, -1, 0) + np.roll(masc, 1, 1) + np.roll(masc, -1, 1)) / 5.0
masc[ocupado] = 0
print("RELIEVE mascara: %d objetos apoyados, %.0f m2 protegidos (%.1f s)" % (n_obj, (masc < 0.5).sum() * CEL * CEL, time.time() - t0))


def mascara(x, y):
    fx, fy = (x - X0) / CEL - 0.5, (y - Y0) / CEL - 0.5
    ix, iy = int(math.floor(fx)), int(math.floor(fy))
    if ix < 0 or iy < 0 or ix >= NX - 1 or iy >= NY - 1:
        return 1.0
    tx, ty = fx - ix, fy - iy
    return (masc[iy, ix] * (1 - tx) + masc[iy, ix + 1] * tx) * (1 - ty) + (masc[iy + 1, ix] * (1 - tx) + masc[iy + 1, ix + 1] * tx) * ty


# construcciones (mismos circulos que usa pasto_y_rocas.py) y el interior aplanado de la torre
fijos = [((-6.8, 91.5), 14.5), ((13.4, 30.8), 2.6), ((-24.7, 1.7), 2.6), ((-41.6, 42.7), 2.6), ((-23.7, 9.4), 3.0),
         ((36.4, 15.8), 5.5), ((-2.0, 54.6), 7.2), ((-18.2, 49.9), 6.0), ((0, -36), 4.5)]


def lejos_de_fijos(x, y):
    m = 1.0
    for (cx, cy), r in fijos:
        m = min(m, suave(r, r + 2.5, math.hypot(x - cx, y - cy)))
    return m


# camino (los mismos puntos que pasto_y_rocas.py)
camino = [(0.0, -34.6), (0.5, -21.6), (1.0, -6.0), (2.1, 9.6), (1.0, 25.2), (-1.0, 40.8), (-1.9, 51.8), (3.9, 62.2), (7.1, 73.3), (11.7, 83.7), (14.3, 92.8), (11.0, 98.6), (6.0, 99.7)]
extra = [[(-1.0, 25.2), (-16.0, 23.5), (-31.1, 16.1), (-43.9, 14.5)], [(2.1, 9.6), (14.7, 9.6), (27.4, 13.9), (38.2, 13.9)], [(9.8, 100.6), (11.9, 103.0), (14.0, 101.7), (15.9, 103.7)]]
linea = []
for pl in [camino] + extra:
    for a, b in zip(pl[:-1], pl[1:]):
        n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.5))
        linea += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    linea.append(pl[-1])
LINEA = np.array(linea)
# distancia al eje del camino principal, en la misma rejilla que la mascara (para decidir donde va la malla fina)
_gx, _gy = np.meshgrid(X0 + (np.arange(NX) + 0.5) * CEL, Y0 + (np.arange(NY) + 0.5) * CEL)
DEJE = camino_lib.dist_eje_np(_gx, _gy)
# piezas vikingas: los baches y hombros nuevos no tocan el suelo donde estan apoyadas
_h = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vikingo_huellas.json")
HUELLAS = json.load(open(_h)) if os.path.exists(_h) else []


def lejos_de_huellas(x, y):
    m = 1.0
    for hx, hy, hr in HUELLAS:
        m = min(m, suave(hr + 0.3, hr + 1.5, math.hypot(x - hx, y - hy)))
    return m


# ------------------------------------------------------------------ subdividir lo que esta fuera del agua
for pasada in range(9):
    sel = []
    for e in bm.edges:
        a, b = e.verts[0].co, e.verts[1].co
        if (a.z + b.z) * 0.5 < Z_SUBDIV:
            continue
        nz = min((f.normal.z for f in e.link_faces), default=1.0)
        lim = L_ROCA if nz < 0.6 else L_SUELO
        if nz >= 0.6:
            gx, gy = int(((a.x + b.x) * 0.5 - X0) / CEL), int(((a.y + b.y) * 0.5 - Y0) / CEL)
            if 0 <= gx < NX and 0 <= gy < NY and DEJE[gy, gx] < R_CAMINO:
                lim = L_CAMINO
        if e.calc_length() > lim:
            sel.append(e)
    if not sel:
        break
    bmesh.ops.subdivide_edges(bm, edges=sel, cuts=1)
    ngon = [f for f in bm.faces if len(f.verts) > 3]
    if ngon:
        bmesh.ops.triangulate(bm, faces=ngon)
    bm.normal_update()
print("RELIEVE subdividido: %d -> %d triangulos en %d pasadas (%.1f s)" % (tris0, len(bm.faces), pasada, time.time() - t0))

# ------------------------------------------------------------------ camino principal: redondear los pliegues de la malla original
# La malla de partida tiene caras de 2-5 m: al subdividirlas quedan pliegues rectos que cruzan el camino (se ven como una
# raya cuando el barro mojado brilla). Se suaviza la franja del camino, sin tocar el suelo protegido ni las piezas vikingas.
bm.verts.ensure_lookup_table()
franja = [v for v in bm.verts
          if v.co.z > 0.3 and v.normal.z > 0.5 and camino_lib.dist_eje(v.co.x, v.co.y) < R_CAMINO - 0.4
          and mascara(v.co.x, v.co.y) * lejos_de_fijos(v.co.x, v.co.y) * lejos_de_huellas(v.co.x, v.co.y) > 0.6]
for _ in range(24):
    bmesh.ops.smooth_vert(bm, verts=franja, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bm.normal_update()
print("RELIEVE camino suavizado: %d vertices (%.1f s)" % (len(franja), time.time() - t0))

# ------------------------------------------------------------------ desplazar
bm.verts.ensure_lookup_table()
bm.verts.index_update()
bm.normal_update()
N = len(bm.verts)
CO = np.array([v.co[:] for v in bm.verts])
NZ0 = np.array([v.normal.z for v in bm.verts])                   # pendiente original (suavizada)
# distancia al camino
dcam = np.empty(N)
for i in range(0, N, 20000):
    q = CO[i:i + 20000, None, :2] - LINEA[None, :, :]
    dcam[i:i + 20000] = np.sqrt((q ** 2).sum(-1)).min(1)


def relieve_suelo(x, y):
    a = noise.noise(Vector((x / 9.0, y / 9.0, 3.1)))                 # lomas largas
    b = noise.noise(Vector((x / 3.6 + 40.0, y / 3.6 + 11.0, 7.7)))   # monticulos
    c = noise.noise(Vector((x / 1.7 + 5.0, y / 1.7 + 71.0, 1.3)))    # baches
    return 0.55 * a + 0.28 * b + 0.09 * c


def relieve_roca(p):
    r = noise.ridged_multi_fractal(p / 5.5, 1.0, 2.1, 3, 1.0, 2.0)   # aristas grandes
    d = (r - 0.9) * 0.36
    q = Vector((p.x / 1.9, p.y / 1.9, p.z / 1.2))                    # bloques (mas anchos que altos: lajas)
    dv, pv = noise.voronoi(q)
    borde = dv[1] - dv[0]
    alto = noise.cell(pv[0] * 13.7 + Vector((5.2, 1.3, 9.7)))
    d += (alto - 0.5) * 0.4 * suave(0.0, 0.3, borde) - 0.12 * (1.0 - suave(0.0, 0.14, borde))   # cada bloque sobresale distinto; grieta en la junta
    s = p.z * 0.9 + 1.2 * noise.noise(p / 7.0)                       # estratos: cornisa que crece hacia arriba y se corta
    f = s - math.floor(s)
    d += 0.22 * (suave(0.0, 0.85, f) * (1.0 - suave(0.85, 1.0, f)) - 0.45)
    return d * 0.75


DSUELO = np.zeros(N)
CAM_U = np.zeros(N)              # 1 en el eje del camino principal ... 0 a 6 m (borde ondulado)
CAM_V = np.zeros(N)              # baches del camino (0..1)
DEJE_V = camino_lib.dist_eje_np(CO[:, 0], CO[:, 1])
dmax_r = 0.0
for v in bm.verts:
    p = v.co
    if p.z < Z_SUBDIV:
        continue
    i = v.index
    m = mascara(p.x, p.y) * lejos_de_fijos(p.x, p.y)
    if m <= 0.001:
        continue
    nz = NZ0[i]
    w_suelo = suave(0.5, 0.72, nz)
    ds = 0.0
    if w_suelo > 0.001:
        fp = 0.25 + 0.75 * suave(1.2, 4.5, dcam[i])                   # el camino, casi liso
        ds = relieve_suelo(p.x, p.y) * fp - 0.07 * (1.0 - suave(0.5, 1.8, dcam[i]))   # y algo hundido (pisado)
        if DEJE_V[i] < camino_lib.ALCANCE + 1.0:
            # camino principal: hombros algo levantados a los lados y baches en lo llano (ahi se quedan los charcos)
            db = camino_lib.dist_borde(p.x, p.y, DEJE_V[i])
            cu = camino_lib.cuenca(p.x, p.y) * (1.0 - suave(0.7, 1.25, db)) * suave(0.90, 0.965, nz)
            hombro = 0.03 * suave(1.0, 1.7, db) * (1.0 - suave(1.7, 2.7, db))
            ds += (hombro - 0.075 * cu) * lejos_de_huellas(p.x, p.y)
        ds *= w_suelo * m * suave(0.1, 1.0, p.z) * FUERZA
    dr = 0.0
    if w_suelo < 0.999:
        dr = relieve_roca(p) * (1.0 - w_suelo) * m * suave(-1.0, 0.4, p.z) * FUERZA
        dmax_r = max(dmax_r, abs(dr))
    DSUELO[i] = ds
    v.co = p + Vector((0, 0, ds)) + v.normal * dr
# datos del camino para el shader. Tambien donde el suelo esta protegido (delante de la cabana...): ahi la malla no tiene
# bache, pero el shader si pone la tierra y los charcos
for v in bm.verts:
    i = v.index
    if DEJE_V[i] < camino_lib.ALCANCE + 1.0 and v.co.z > 0.3 and NZ0[i] > 0.5:
        x, y = CO[i, 0], CO[i, 1]
        db = camino_lib.dist_borde(x, y, DEJE_V[i])
        CAM_U[i] = max(0.0, 1.0 - db / camino_lib.ALCANCE)
        CAM_V[i] = camino_lib.cuenca(x, y) * (1.0 - suave(0.7, 1.25, db)) * suave(0.90, 0.965, NZ0[i])
bm.normal_update()

# ------------------------------------------------------------------ datos para el shader (segunda UV)
uv1 = bm.loops.layers.uv.get("Datos") or bm.loops.layers.uv.new("Datos")
for f in bm.faces:
    f.smooth = True
    for lp in f.loops:
        i = lp.vert.index
        lp[uv1].uv = (min(1.0, max(0.0, NZ0[i])), min(1.0, max(0.0, 0.5 + DSUELO[i])))
uv2 = bm.loops.layers.uv.get("Camino") or bm.loops.layers.uv.new("Camino")
for f in bm.faces:
    for lp in f.loops:
        i = lp.vert.index
        lp[uv2].uv = (CAM_U[i], CAM_V[i])

# rocas y ramas sueltas: suben o bajan lo mismo que cambio el suelo debajo (solo las que ya estaban apoyadas en el relieve anterior)
if ANTES is not None:
    AHORA = BVHTree.FromBMesh(bm)
    veg = bpy.data.collections.get("Vegetacion_Isla")
    if veg:
        sueltos = [o for o in veg.objects if o.type == 'MESH' and not o.name.startswith("Pasto_") and o.get("apoyado_relieve")]
        print("RELIEVE rocas y ramas reapoyadas: %d piezas movidas" % apoyo_lib.reapoyar(sueltos, ANTES, AHORA))
    # control: cuanto cambio el suelo respecto al relieve anterior, cerca y lejos del camino principal
    abajo = Vector((0, 0, -1))
    cerca, lejos_ = [], []
    for gy in range(0, NY, 2):
        for gx in range(0, NX, 2):
            x, y = X0 + (gx + 0.5) * CEL, Y0 + (gy + 0.5) * CEL
            r0, r1 = ANTES.ray_cast(Vector((x, y, 200.0)), abajo), AHORA.ray_cast(Vector((x, y, 200.0)), abajo)
            if r0[0] is None or r1[0] is None or r1[0].z < 0.3:
                continue
            (cerca if DEJE[gy, gx] < 4.0 else lejos_).append(abs(r1[0].z - r0[0].z))
    for nombre, l in (("a menos de 4 m del camino", cerca), ("en el resto de la isla", lejos_)):
        if l:
            a = np.array(l)
            print("RELIEVE cambio de altura %s: medio %.3f m, maximo %.3f m, puntos con mas de 5 cm: %d de %d" % (nombre, a.mean(), a.max(), (a > 0.05).sum(), len(a)))

bm.transform(MW.inverted())
bm.to_mesh(nueva)
bm.free()
# las normales personalizadas de la malla original ya no valen (la superficie cambio): se usan las normales suaves nuevas
if "custom_normal" in nueva.attributes:
    nueva.attributes.remove(nueva.attributes["custom_normal"])
if "sharp_face" in nueva.attributes:
    nueva.attributes.remove(nueva.attributes["sharp_face"])
nueva.uv_layers.active = nueva.uv_layers[0]
nueva.uv_layers[0].active_render = True
nueva.update()
I["relieve"] = 1
print("RELIEVE listo: %d vertices, %d triangulos | suelo sube/baja %.2f / %.2f m, roca hasta %.2f m | UV %s (%.1f s)" % (
    len(nueva.vertices), len(nueva.polygons), DSUELO.max(), DSUELO.min(), dmax_r, [u.name for u in nueva.uv_layers], time.time() - t0))
if "--save" in args:
    bpy.ops.wm.save_mainfile()
