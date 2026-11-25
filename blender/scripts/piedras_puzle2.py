# Rocas con figuras del puzle 2 (postes, placa, rocas del sendero) y la estela de las mareas: textura nueva.
#   Antes: piedra gris plana, "tinta" negra, musgo verde chillon y grietas de baldosa; al hornear quedaban borrosas.
#   Ahora: piedra antigua (manchas, grano, grietas finas, chorreras, liquen, musgo y humedad al pie), las figuras son surcos
#          con restos de pigmento rojo, y talla vikinga anadida: bandas de runas alrededor de los postes, trenzas en las
#          cabezas y la serpiente del mundo con "no sigas adelante" en la roca que corta el sendero.
#   Las figuras del puzle (geometria 'M_Tinta') NO cambian de forma ni de sitio.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/piedras_puzle2.py -- [--save] [--hornear]
#   --save     guarda los materiales nuevos en el .blend (antes de hornear)
#   --hornear  hornea a mas resolucion (postes y rocas 4096, cabezas y placa 2048) con UV nuevas, y re-exporta
#              Puzle2_IslaAlterada.fbx; la estela usa las UV de siempre (no se toca Puzle1_Muelle.fbx)
# Sustituye a brillo_puzle2.py (el brillo ya va en el material; no volver a ejecutar aquel sobre estos objetos).
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import vikingo_mats as vm

D = bpy.data
POSTES = ["Poste_1_Reflejo", "Poste_2_Origen", "Poste_3_Fin"]
OBJETOS = [o for o in D.collections["Puzle2_IslaAlterada"].objects if o.type == 'MESH'] + [D.objects["Estela_Mareas"]]
TAM = {"Poste_1_Reflejo_Base": 4096, "Poste_2_Origen_Base": 4096, "Poste_3_Fin_Base": 4096, "Roca_Bloqueo_Sendero": 4096,
       "Roca_Normal": 2048, "Placa_Inscripcion": 2048, "Estela_Mareas": 4096}

bpy.context.view_layer.update()
ISLA = D.objects["IslandModel"]
_inv = ISLA.matrix_world.inverted()
_dl = (_inv.to_3x3() @ Vector((0, 0, -1))).normalized()


def suelo(x, y):
    h, l, n, i = ISLA.ray_cast(_inv @ Vector((x, y, 500.0)), _dl)
    return (ISLA.matrix_world @ l).z if h else None


if not os.path.exists(os.path.join(vm.TALLAS, "T_V_Banda_Faro.png")):
    vm.generar_tallas()


def base(m):
    return m.name.split("__")[0].split(".")[0] if m else ""


def ventana_sin_figuras(o, z_min, z_max, alto, r_max):
    """busca en el fuste (coordenadas locales) la franja de altura 'alto' con menos caras de figura; devuelve (z0, cx, cy, radio)"""
    me = o.data
    co = np.array([v.co[:] for v in me.vertices])
    tinta = [i for i, m in enumerate(me.materials) if base(m) in ("M_Tinta", "M_V_Talla")]
    zt = np.array([me.vertices[v].co.z for p in me.polygons if p.material_index in tinta for v in p.vertices] or [1e9])
    mejor = None
    z = z_max - alto
    while z >= z_min:
        n = int(((zt >= z - 0.01) & (zt <= z + alto + 0.01)).sum())
        if mejor is None or n < mejor[0]:
            mejor = (n, z)
        z -= 0.02
    n, z0 = mejor
    sel = co[(co[:, 2] >= z0 - 0.1) & (co[:, 2] <= z0 + alto + 0.1) & (np.hypot(co[:, 0], co[:, 1]) < r_max)]
    if len(sel) < 4:
        return z0, 0.0, 0.0, 0.5, n
    c = sel[:, :2].mean(axis=0)
    r = float(np.median(np.hypot(sel[:, 0] - c[0], sel[:, 1] - c[1])))
    return z0, float(c[0]), float(c[1]), r, n


def cara_mayor(o, direccion=(0, -1, 0)):
    """penasco (isla de malla) con mas superficie mirando en 'direccion' (local): centro y tamano de esa cara"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.faces.ensure_lookup_table()
    d = Vector(direccion)
    visto = set()
    mejor = None
    for f0 in bm.faces:
        if f0.index in visto:
            continue
        pila, isla = [f0], []
        visto.add(f0.index)
        while pila:
            f = pila.pop()
            isla.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in visto:
                        visto.add(g.index)
                        pila.append(g)
        caras = [f for f in isla if f.normal.dot(d) > 0.6]
        area = sum(f.calc_area() for f in caras)
        if caras and (mejor is None or area > mejor[0]):
            cs = [f.calc_center_median() for f in caras]
            ar = [f.calc_area() for f in caras]
            cx = sum(c.x * a for c, a in zip(cs, ar)) / area
            cz = sum(c.z * a for c, a in zip(cs, ar)) / area
            vs = {v for f in caras for v in f.verts}
            ancho = max(v.co.x for v in vs) - min(v.co.x for v in vs)
            alto = max(v.co.z for v in vs) - min(v.co.z for v in vs)
            mejor = (area, cx, cz, ancho, alto)
    bm.free()
    return mejor


# materiales compartidos
M_TALLA = vm.talla_pintada("M_V_Talla")
M_MUSGO = vm.musgo("M_V_Musgo")
CLARO, OSCURO = (0.135, 0.135, 0.14), (0.046, 0.048, 0.054)
M_OSCURA = vm.piedra("M_V_PiedraOscura", claro=vm.gris(CLARO, 0.6), oscuro=vm.gris(OSCURO, 0.6), calido=0.2, liquen=0.8, musgo=1.0)

for o in OBJETOS:
    me = o.data
    esc = o.matrix_world.to_scale().x
    tallas = []
    nota = ""
    if o.name.endswith("_Base"):
        co_z = max(v.co.z for v in me.vertices)
        alto = 0.2
        z0, cx, cy, r, n = ventana_sin_figuras(o, 0.78, co_z - 0.03, alto, 0.8)
        rep = max(1, round(2 * math.pi * r * esc / (alto * esc * 8.0)))
        tallas.append({'imagen': "T_V_Banda_Faro" if "Origen" not in o.name else "T_V_Banda_Futhark", 'modo': 'cilindro',
                       'z0': z0, 'z1': z0 + alto, 'cx': cx, 'cy': cy, 'rep': rep})
        nota = "banda de runas z %.2f (figuras en la franja: %d, radio %.2f, x%d)" % (z0, n, r, rep)
    elif o.name.endswith("_Cabeza"):
        for za, zb in ((0.275, 0.36), (-0.455, -0.375)):
            z0, cx, cy, r, n = ventana_sin_figuras(o, za, zb, zb - za, 0.9)
            if n <= 16:
                rep = max(1, round(2 * math.pi * r * esc / ((zb - za) * esc * 8.0)))
                tallas.append({'imagen': "T_V_Banda_Nudos", 'modo': 'cilindro', 'z0': za, 'z1': zb, 'cx': 0.0, 'cy': 0.0, 'rep': rep})
                nota += "trenza z %.2f x%d  " % (za, rep)
    elif o.name == "Roca_Bloqueo_Sendero":
        area, cx, cz, ancho, alto = cara_mayor(o)
        dia = 0.86 * min(ancho, alto)
        tallas.append({'imagen': "T_V_Anillo_Serpiente", 'modo': 'frente', 'ancho': dia, 'alto': dia, 'cx': cx, 'z0': cz - dia / 2})
        nota = "anillo de la serpiente, diametro %.2f m" % (dia * esc)
    roca = o.name.startswith("Roca_")
    # la placa esta tumbada a ras de suelo: sin esto el musgo la cubre entera y no se lee la inscripcion
    extra = {'musgo_arriba': 0.03, 'musgo_pie': 0.04, 'humedad': 0.3} if o.name == "Placa_Inscripcion" else {}
    m_clara = vm.piedra("M_V_Piedra__" + o.name, claro=vm.gris(CLARO, 0.9 if roca else 1.0), oscuro=vm.gris(OSCURO, 0.9 if roca else 1.0),
                        calido=0.35 if roca else 0.25, liquen=1.0, musgo=1.0, tallas=tallas or None, escala=0.7 if roca else 1.0, **extra)
    for i, m in enumerate(list(me.materials)):
        b = base(m)
        if b in ("M_PiedraVieja", "M_Roca", "M_V_Piedra"):
            me.materials[i] = m_clara
        elif b in ("M_PiedraOscura", "M_RocaOscura", "M_V_PiedraOscura"):
            me.materials[i] = M_OSCURA
        elif b in ("M_Tinta", "M_V_Talla"):
            me.materials[i] = M_TALLA
        elif b in ("M_Musgo", "M_V_Musgo"):
            me.materials[i] = M_MUSGO
    # altura de cada vertice sobre el terreno (humedad y musgo al pie)
    mw = o.matrix_world
    alt = []
    for v in me.vertices:
        q = mw @ v.co
        h = suelo(q.x, q.y)
        alt.append(max(0.0, q.z - h) if h is not None else 3.0)
    vm.atributo_suelo(me, alt)
    print("PUZLE2", o.name, [base(m) for m in me.materials], nota)

for m in list(D.materials):          # materiales viejos que se quedan sin uso
    if m.users == 0 and base(m) in ("M_PiedraVieja", "M_PiedraOscura", "M_Tinta", "M_Musgo", "M_Roca", "M_RocaOscura") and "__" in m.name:
        D.materials.remove(m)

if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()

if "--hornear" in sys.argv:
    import hornear_lib as hl
    col = D.collections["Puzle2_IslaAlterada"]
    for o in OBJETOS:
        if o.name == "Estela_Mareas":
            hl.hornear(o, TAM[o.name], 'unity')
        else:
            hl.hornear(o, TAM.get(o.name, 2048), 'hd')
    hl.exportar_fbx("Puzle2_IslaAlterada", list(col.objects), anim=True)     # igual que exportar_puzle2.py
