# Rehace los arboles secos de la coleccion "Atrezzo_Exterior" SIN tocar el resto del atrezzo (usa su propio generador aleatorio).
# Cada Arbol_Seco_NN se sustituye por uno nuevo en la misma posicion y con la misma altura:
#   - tronco curvo con base ensanchada y raices, ramas que se afinan y se doblan, ramitas finas y munones rotos
#   - UV en "tiles" (ver ramas_lib.py) para que Unity le ponga el detalle de corteza (T_Det_Corteza)
# Uso: blender -b el_misterio_del_faro.blend --python arboles_secos.py -- [--save]
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ramas_lib

PI = math.pi
col = bpy.data.collections["Atrezzo_Exterior"]
M_COR = bpy.data.materials["M_Atrezzo_Corteza"]
viejos = sorted([o for o in col.objects if o.name.startswith("Arbol_Seco_")], key=lambda o: o.name)
print("ARBOLES a rehacer:", len(viejos))


def curva(p0, d0, largo, n, dobla, gravedad, rt):
    pts = [Vector(p0)]
    d = Vector(d0).normalized()
    for _ in range(n):
        d = (d + Vector((rt.gauss(0, dobla), rt.gauss(0, dobla), rt.gauss(0, dobla * 0.5) - gravedad))).normalized()
        pts.append(pts[-1] + d * (largo / n))
    return pts


def rama(bm, p, d, largo, r, prof, rt):
    n = 4 if prof > 0 else 3
    pts = curva(p, d, largo, n, 0.24, 0.05 if prof == 0 else 0.015, rt)
    rad = [r * (1.0 - 0.68 * k / n) for k in range(n + 1)]
    seg = 7 if r > 0.06 else (5 if r > 0.02 else 4)
    ramas_lib.tubo_curvo(bm, pts, rad, seg=seg, v0=rt.uniform(0, 6))
    if prof > 0:
        for _ in range(rt.choice((2, 2, 3))):
            k = rt.randint(1, n)
            t = (pts[min(k + 1, n)] - pts[k - 1]).normalized()
            nd = (t + Vector((rt.uniform(-0.9, 0.9), rt.uniform(-0.9, 0.9), rt.uniform(-0.1, 0.5)))).normalized()
            rama(bm, pts[k], nd, largo * rt.uniform(0.45, 0.7), rad[k] * 0.62, prof - 1, rt)


def arbol(nombre, alto, rt):
    bm = bmesh.new()
    r0 = 0.034 * alto
    inc = Vector((rt.uniform(-0.22, 0.22), rt.uniform(-0.22, 0.22), 1)).normalized()
    tronco = curva((0, 0, -0.1), inc, alto, 6, 0.12, 0.0, rt)
    rad = [r0 * f for f in (1.6, 1.2, 1.0, 0.86, 0.72, 0.56, 0.38)]
    ramas_lib.tubo_curvo(bm, tronco, rad, seg=9, tapa_base=True)
    # ramas principales repartidas por el tronco (de la mitad hacia arriba), con prof 2 (hijas y nietas)
    for k in range(2, 7):
        for _ in range(rt.choice((1, 2, 2))):
            ang = rt.uniform(0, 2 * PI)
            d = Vector((math.cos(ang) * 0.9, math.sin(ang) * 0.9, rt.uniform(0.2, 0.7))).normalized()
            largo = alto * rt.uniform(0.28, 0.42) * (1.25 - k * 0.12)
            rama(bm, tronco[k], d, max(largo, 0.5), rad[k] * 0.55, 2, rt)
    # munones rotos (ramas que se partieron)
    for _ in range(3):
        k = rt.randint(1, 4)
        ang = rt.uniform(0, 2 * PI)
        d = Vector((math.cos(ang), math.sin(ang), rt.uniform(0.0, 0.5))).normalized()
        q = [tronco[k], tronco[k] + d * 0.12, tronco[k] + d * rt.uniform(0.22, 0.4)]
        ramas_lib.tubo_curvo(bm, q, [rad[k] * 0.32, rad[k] * 0.27, rad[k] * 0.24], seg=5, v0=rt.uniform(0, 6))
    # raices
    for _ in range(rt.randint(5, 7)):
        ang = rt.uniform(0, 2 * PI)
        d = Vector((math.cos(ang), math.sin(ang), 0))
        largo = rt.uniform(0.9, 1.9)
        pts = [Vector((0, 0, 0.45)) + d * 0.05, Vector((0, 0, 0.3)) + d * largo * 0.35, Vector((0, 0, 0.05)) + d * largo * 0.7, Vector((0, 0, -0.12)) + d * largo]
        ramas_lib.tubo_curvo(bm, pts, [r0 * 0.85, r0 * 0.6, r0 * 0.38, r0 * 0.18], seg=6, v0=rt.uniform(0, 6))
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    n_tris = len(me.polygons)
    bm.free()
    me.materials.append(M_COR)
    return me, n_tris


total = 0
for i, o in enumerate(viejos):
    nombre, loc, alto = o.name, o.location.copy(), max(o.dimensions.z, 3.0)
    rot = o.rotation_euler.copy()
    me_old = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    if me_old.users == 0:
        bpy.data.meshes.remove(me_old)
    rt = random.Random(700 + i)
    me, nt = arbol(nombre, alto, rt)
    ob = bpy.data.objects.new(nombre, me)
    ob.location = loc
    ob.rotation_euler = rot
    col.objects.link(ob)
    total += nt
    print("ARBOL", nombre, "alto", round(alto, 1), "tris", nt)
print("ARBOLES nuevos", len(viejos), "tris", total)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
