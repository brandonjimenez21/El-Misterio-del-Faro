# Pasto y rocas sueltas de la isla (ligeros). Coleccion "Vegetacion_Isla":
#   Pasto_i_j   : matas de hierba = 3 tarjetas cruzadas con la textura T_Pasto_Matas.png (atlas 2x2, recorte por alfa; la genera
#                 textura_pasto.py), agrupadas en bloques de 24 m para que Unity los descarte por distancia/vista.
#                 Solo donde la textura horneada de la isla es verde (igual que decide el shader), tambien en laderas suaves;
#                 la densidad y la altura cambian por zonas (claros, hierba alta, mas baja junto al camino).
#                 UV0 = textura de la mata; UV1 "Datos" = (tinte aleatorio, altura 0..1) para el viento y el color.
#   Roca_i_j    : cantos y bloques de baja resolucion (alrededor de los "dedos" de roca, la costa y los postes),
#                 tambien en bloques.
# Uso: blender -b archivo.blend --python pasto_y_rocas.py -- [--save] [--solo-pasto]
#      --solo-pasto : rehace solo la hierba; las rocas y ramas que ya hay se quedan donde estan y solo se vuelven a apoyar
#                     en el terreno (para despues de relieve_terreno.py)
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix, noise
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramas_lib, camino_lib, apoyo_lib

S = bpy.context.scene
I = bpy.data.objects["IslandModel"]
bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
R = random.Random(21)
PI = math.pi
NIVEL_MAR = -0.55
CELDA = 24.0
PASO_PASTO = 0.36         # separacion media entre matas (m)
SOLO_PASTO = "--solo-pasto" in sys.argv
N_ROCAS_BASE = 190
N_ROCAS_COSTA = 90
N_GUIJARROS = 520       # grupos de piedrecitas sueltas
N_RAMAS = 150           # ramas caidas


def suelo(x, y):
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    if not h:
        return None, None
    nw = (I.matrix_world.to_3x3() @ n).normalized()
    return (I.matrix_world @ l).z, nw


col = bpy.data.collections.get("Vegetacion_Isla")
if col:
    for o in list(col.objects):
        if SOLO_PASTO and not o.name.startswith("Pasto_"):
            continue
        me_v = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me_v and me_v.users == 0:
            bpy.data.meshes.remove(me_v)
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
# huellas de las piezas vikingas (vikingos.py las deja en vikingo_huellas.json): sin hierba atravesando las piedras
_huellas = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vikingo_huellas.json")
if os.path.exists(_huellas):
    import json
    fijos += [((h[0], h[1]), h[2]) for h in json.load(open(_huellas))]
def libre(x, y, margen=0.0):
    return not any((Vector((x, y)) - Vector(c)).length < r + margen for c, r in fijos)


# ---------------------------------------------------------------- PASTO
import numpy as np
from mathutils.interpolate import poly_3d_calc
RP = random.Random(77)                     # azar propio de la hierba (no cambia donde caen rocas y ramas)
ME = I.data
UV0 = ME.uv_layers["UVMap"].data
UVD = ME.uv_layers["Datos"].data if "Datos" in ME.uv_layers else None     # pendiente original (relieve_terreno.py)
# textura horneada de la isla (reducida): la hierba solo va donde es verde, igual que decide el shader Faro/IslaDetalle
_im = bpy.data.images.load(os.path.join(os.path.dirname(bpy.data.filepath), "texturas", "Isla_c.jpg"))
_im.scale(1024, 1024)
HORNEADA = np.array(_im.pixels[:], dtype=np.float32).reshape(1024, 1024, 4)[..., :3] ** 2.2     # a lineal
bpy.data.images.remove(_im)


def suave(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def cuanta_hierba(x, y):
    """(altura del suelo, normal, 0..1 cuanta hierba hay) en el punto; None si no hay isla"""
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    if not h:
        return None
    pol = ME.polygons[i]
    w = poly_3d_calc([ME.vertices[k].co for k in pol.vertices], l)
    u = sum(UV0[li].uv[0] * wk for li, wk in zip(pol.loop_indices, w))
    v = sum(UV0[li].uv[1] * wk for li, wk in zip(pol.loop_indices, w))
    c = HORNEADA[int(v * 1024) % 1024, int(u * 1024) % 1024]
    nw = (I.matrix_world.to_3x3() @ n).normalized()
    ny = sum(UVD[li].uv[0] * wk for li, wk in zip(pol.loop_indices, w)) if UVD else nw.z
    verde = suave(-0.03, 0.0, c[1] - c[0] * 1.1)
    return (I.matrix_world @ l).z, nw, verde * suave(0.5, 0.74, ny)


# celdas del atlas T_Pasto_Matas.png: 0 media, 1 alta, 2 corta, 3 tallos secos
def celda_uv(k):
    cx, cy = k % 2, k // 2
    m = 0.004
    return cx * 0.5 + m, cy * 0.5 + m, cx * 0.5 + 0.5 - m, cy * 0.5 + 0.5 - m


def mata(bm, uv0, uv1, c, n, alto, ancho, variante, tinte):
    """3 tarjetas cruzadas, algo desplazadas del centro e inclinadas (asi no se ve una 'X' desde arriba)"""
    u0, v0, u1, v1 = celda_uv(variante)
    a0 = RP.uniform(0, PI)
    arriba = (Vector((0, 0, 0.35)) + n * 0.65).normalized()       # la mata crece casi perpendicular al suelo
    for k in range(3):
        a = a0 + k * PI / 3 + RP.uniform(-0.25, 0.25)
        t = Vector((math.cos(a), math.sin(a), 0))
        q = Vector((-t.y, t.x, 0))
        centro = c + q * RP.uniform(-0.12, 0.12) * ancho
        cae = q * RP.choice((-1, 1)) * RP.uniform(0.25, 0.7) * alto     # la parte de arriba se abre hacia un lado (ninguna tarjeta queda vertical)
        esq = []
        for lado in (-0.5, 0.5):
            p = centro + t * lado * ancho
            p.z = c.z - (n.x * (p.x - c.x) + n.y * (p.y - c.y)) / max(n.z, 0.3) - 0.04     # la base sigue la pendiente
            esq.append(p)
        vs = [bm.verts.new(esq[0]), bm.verts.new(esq[1]),
              bm.verts.new(esq[1] + cae + arriba * alto), bm.verts.new(esq[0] + cae + arriba * alto)]
        f = bm.faces.new(vs)
        ua, ub = (u0, u1) if RP.random() < 0.5 else (u1, u0)
        for lp, (uu, vv, hh) in zip(f.loops, ((ua, v0, 0.0), (ub, v0, 0.0), (ub, v1, 1.0), (ua, v1, 1.0))):
            lp[uv0].uv = (uu, vv)
            lp[uv1].uv = (tinte, hh)


celdas = {}
puestos = 0
for iy in range(int(-34 / PASO_PASTO), int(118 / PASO_PASTO)):
    for ix in range(int(-62 / PASO_PASTO), int(58 / PASO_PASTO)):
        x, y = (ix + RP.random()) * PASO_PASTO, (iy + RP.random()) * PASO_PASTO
        if not libre(x, y):
            continue
        r = cuanta_hierba(x, y)
        if r is None:
            continue
        g, n, hierba = r
        if g < 1.6 or n.z < 0.6 or hierba < 0.5:
            continue
        dc = dist_camino(x, y)
        # camino principal: la hierba empieza donde acaba la tierra (mismo borde ondulado que usan el relieve y el shader)
        dp = camino_lib.dist_borde(x, y)
        if dp < camino_lib.BORDE_TIERRA or (dc < 1.3 and dp > 3.0):       # (los caminos ocultos, como antes: 1.3 m sin matas)
            continue
        dc = min(dc, dp)
        # zonas: claros donde casi no hay matas, manchas de hierba alta y manchas de tallos secos
        zona = noise.noise(Vector((x / 11.0, y / 11.0, 0.7)))
        zona2 = noise.noise(Vector((x / 4.3 + 30.0, y / 4.3, 5.1)))
        densidad = suave(-0.55, 0.05, zona + 0.5 * zona2) * 0.6 + 0.4
        ralo = 0.3 + 0.7 * suave(camino_lib.BORDE_TIERRA, 2.6, dp)       # junto al camino las matas ralean (hierba pisada con tierra entre medias)
        if RP.random() > densidad * suave(0.45, 0.95, hierba) * ralo:
            continue
        alta = suave(-0.1, 0.5, noise.noise(Vector((x / 15.0 + 9.0, y / 15.0 + 4.0, 2.2))) + 0.35 * zona2)
        borde = suave(1.3, 4.5, dc)                               # junto al camino, mas baja (pisada)
        ladera = suave(0.62, 0.85, n.z)                           # en pendiente, mas corta
        alto = (0.24 + 0.32 * alta + RP.uniform(0.0, 0.16)) * (0.55 + 0.45 * borde) * (0.6 + 0.4 * ladera)
        seco = noise.noise(Vector((x / 8.0 + 50.0, y / 8.0 + 17.0, 9.3)))
        if RP.random() < 0.03 + 0.14 * suave(0.1, 0.5, seco):
            variante, alto = 3, alto * 1.7 + 0.15                 # tallos secos con espiga: mas altos
        elif alto < 0.3:
            variante = 2 if RP.random() < 0.75 else 0
        else:
            variante = 1 if RP.random() < 0.3 + 0.4 * alta else 0
        ancho = 0.42 + 0.55 * alto + RP.uniform(0.0, 0.15)
        key = (int(math.floor(x / CELDA)), int(math.floor(y / CELDA)))
        if key not in celdas:
            bmc = bmesh.new()
            celdas[key] = (bmc, bmc.loops.layers.uv.new("UVMap"), bmc.loops.layers.uv.new("Datos"))
        bmc, l0, l1 = celdas[key]
        mata(bmc, l0, l1, Vector((x, y, g)), n, alto, ancho, variante, RP.random())
        puestos += 1
tris = 0
for (i, j), (bm, l0, l1) in celdas.items():
    me = bpy.data.meshes.new("Pasto_%d_%d" % (i, j))
    bm.to_mesh(me)
    tris += len(me.polygons) * 2
    bm.free()
    me.materials.append(M_PASTO)
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new("Pasto_%d_%d" % (i, j), me)
    col.objects.link(ob)
print("VEG pasto matas", puestos, "bloques", len(celdas), "tris", tris)

if SOLO_PASTO:
    # rocas y ramas que ya existen: cada pieza suelta sube o baja lo mismo que cambio el suelo debajo de ella
    base = bpy.data.meshes.get("IslandModel_SinRelieve")
    hecho = 0
    if base is not None:
        # las que ya se apoyaron una vez (apoyado_relieve) las mantiene al dia relieve_terreno.py cada vez que cambia el suelo
        sueltos = [o for o in col.objects if o.type == 'MESH' and not o.name.startswith("Pasto_") and not o.get("apoyado_relieve")]
        if sueltos:
            hecho = apoyo_lib.reapoyar(sueltos, apoyo_lib.arbol(base, I.matrix_world), apoyo_lib.arbol(I.data, I.matrix_world))
        for o in sueltos:
            o["apoyado_relieve"] = 1
    print("VEG rocas y ramas reapoyadas en el terreno: %d piezas movidas" % hecho)
    if "--save" in sys.argv:
        bpy.ops.wm.save_mainfile()
    sys.exit(0)


# ---------------------------------------------------------------- ROCAS SUELTAS
def canto(bm, c, tam, achatado, sub=2):
    """roca esculpida: icosfera + ruido de dos frecuencias (forma irregular) + planos de corte (caras planas y aristas),
    sombreado suave; la textura la pone el shader en el mundo (triplanar), asi que no necesita UV."""
    r = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    vs = r["verts"]
    ejes = Vector((R.uniform(0.8, 1.5), R.uniform(0.8, 1.5), achatado))
    rot = Matrix.Rotation(R.uniform(0, 2 * PI), 3, 'Z')
    sem = Vector((R.uniform(0, 200), R.uniform(0, 200), R.uniform(0, 200)))
    cortes = []
    for _ in range(R.randint(3, 6) if sub >= 2 else 2):
        nrm = Vector((R.uniform(-1, 1), R.uniform(-1, 1), R.uniform(-0.25, 1))).normalized()
        cortes.append((nrm, R.uniform(0.6, 0.86)))
    for v in vs:
        p = v.co.copy()
        p = p * (1.0 + 0.24 * noise.noise(p * 1.5 + sem) + 0.08 * noise.noise(p * 4.2 + sem * 1.7)
                 + (0.025 * noise.noise(p * 11.0 + sem * 2.3) if sub >= 2 else 0.0))
        for nrm, h in cortes:
            dd = p.dot(nrm)
            if dd > h:
                p -= nrm * (dd - h) * 0.92                       # aplana la punta: cara plana con arista
        p = Vector((p.x * ejes.x, p.y * ejes.y, p.z * ejes.z))
        v.co = rot @ p * tam + c
    for v in vs:
        v.co.z = max(v.co.z, c.z - tam * 0.25)                  # base hundida en el suelo


rocas = {}
n_r = 0
def poner_roca(x, y, g, tam, achat, sub=2):
    global n_r
    key = (int(math.floor(x / CELDA)), int(math.floor(y / CELDA)))
    if key not in rocas:
        rocas[key] = bmesh.new()
    canto(rocas[key], Vector((x, y, g)), tam, achat, sub)
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

# 3) guijarros: grupos de piedrecitas sueltas por el suelo (rompen la "alfombra" lisa de tierra y pasto)
tot, intentos = 0, 0
while tot < N_GUIJARROS and intentos < 60000:
    intentos += 1
    x, y = R.uniform(-64, 60), R.uniform(-34, 120)
    g, n = suelo(x, y)
    if g is None or g < 0.6 or n.z < 0.75:
        continue
    if (y < -10 and abs(x) < 8) or not libre(x, y, 0.5):
        continue
    for _ in range(R.randint(3, 7)):
        px, py = x + R.gauss(0, 0.45), y + R.gauss(0, 0.45)
        g2, n2 = suelo(px, py)
        if g2 is None or n2.z < 0.7:
            continue
        poner_roca(px, py, g2, R.uniform(0.05, 0.2), R.uniform(0.45, 0.8), sub=1)
    tot += 1
rt = 0
for (i, j), bm in rocas.items():
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new("Roca_%d_%d" % (i, j))
    bm.to_mesh(me)
    rt += len(me.polygons)
    bm.free()
    me.materials.append(M_ROCA)
    ob = bpy.data.objects.new("Roca_%d_%d" % (i, j), me)
    col.objects.link(ob)
print("VEG rocas", n_r, "bloques", len(rocas), "tris", rt)


# ---------------------------------------------------------------- RAMAS CAIDAS (material de corteza del atrezzo; UV en tiles para el detalle de corteza)
M_COR = bpy.data.materials.get("M_Atrezzo_Corteza") or mat("M_Atrezzo_Corteza", (0.1, 0.085, 0.07), 1.0)
ramas = {}
n_ram = 0
intentos = 0
while n_ram < N_RAMAS and intentos < 40000:
    intentos += 1
    x, y = R.uniform(-60, 56), R.uniform(-30, 116)
    g, n = suelo(x, y)
    if g is None or g < 2.2 or n.z < 0.82:
        continue
    if dist_camino(x, y) < 2.4 or not libre(x, y, 0.5):
        continue
    key = (int(math.floor(x / CELDA)), int(math.floor(y / CELDA)))
    if key not in ramas:
        ramas[key] = bmesh.new()
    bm = ramas[key]
    largo = R.uniform(0.5, 1.9)
    r0 = R.uniform(0.012, 0.032)
    ang = R.uniform(0, 2 * PI)
    d = Vector((math.cos(ang), math.sin(ang), 0))
    pts, rad = [], []
    pasos = 5
    tuerce = R.uniform(-0.35, 0.35)
    for k in range(pasos + 1):
        t = k / pasos
        dd = (d + Vector((-d.y, d.x, 0)) * tuerce * t).normalized()
        px, py = x + dd.x * largo * t, y + dd.y * largo * t
        gz = suelo(px, py)[0]
        gz = g if gz is None else gz
        pts.append(Vector((px, py, gz + r0 * 0.7 + R.uniform(0.0, 0.03) + (0.05 * math.sin(t * PI) if R.random() < 0.5 else 0))))
        rad.append(r0 * (1.0 - 0.7 * t))
    ramas_lib.tubo_curvo(bm, pts, rad, seg=5, tapa_base=True, v0=R.uniform(0, 4))
    for _ in range(R.randint(1, 3)):                              # ramitas laterales
        k = R.randint(1, pasos - 2)
        d2 = (pts[k + 1] - pts[k]).normalized()
        d2 = (d2 + Vector((R.uniform(-0.8, 0.8), R.uniform(-0.8, 0.8), R.uniform(0.0, 0.5)))).normalized()
        l2 = largo * R.uniform(0.2, 0.4)
        q = [pts[k] + d2 * l2 * s for s in (0.0, 0.5, 1.0)]
        for qq in q:
            qq.z = max(qq.z, pts[k].z - 0.01)
        ramas_lib.tubo_curvo(bm, q, [rad[k] * 0.6, rad[k] * 0.42, rad[k] * 0.2], seg=4, tapa_base=False, v0=R.uniform(0, 4))
    n_ram += 1
tr = 0
for (i, j), bm in ramas.items():
    me = bpy.data.meshes.new("Rama_%d_%d" % (i, j))
    bm.to_mesh(me)
    tr += len(me.polygons)
    bm.free()
    me.materials.append(M_COR)
    ob = bpy.data.objects.new("Rama_%d_%d" % (i, j), me)
    col.objects.link(ob)
print("VEG ramas", n_ram, "bloques", len(ramas), "tris", tr)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
