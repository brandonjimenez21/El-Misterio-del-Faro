# Terror psicologico: (1) haz de luz del faro (dos conos abiertos opuestos, UV.v = distancia 0..1 desde la lampara)
#                     (2) figura del antiguo cuidador (silueta con capucha, abrigo largo y brazos largos, ~1700 triangulos)
# Cada uno en su coleccion y FBX: Assets/Models/Faro/Faro_Haz.fbx y Figura_Cuidador.fbx
# Uso: blender -b el_misterio_del_faro.blend --python scripts/terror_faro_figura.py -- --save
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, Euler

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
LAMPARA = (-6.8, 89.2, 50.6)      # Blender; en Unity (6.8, 50.6, -89.2)


def coleccion(nombre):
    c = bpy.data.collections.get(nombre) or bpy.data.collections.new(nombre)
    if nombre not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return c


def material(nombre, color, rough=0.9):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*color, 1)
    return m


def objeto(nombre, bm, mat, col, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(nombre, me)
    ob.location = loc
    col.objects.link(ob)
    return ob


def exportar(col, ruta):
    bpy.ops.object.select_all(action='DESELECT')
    for o in col.objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = list(col.objects)[0]
    bpy.ops.export_scene.fbx(filepath=ruta, use_selection=True, apply_scale_options='FBX_SCALE_ALL', bake_anim=False,
                             add_leaf_bones=False, object_types={'MESH'}, path_mode='STRIP', use_tspace=True)


# ------------------------------------------------------------------ 1) haz del faro
col = coleccion("Faro_Haz")
LARGO, R0, R1, SEG, ANILLOS = 170.0, 0.6, 20.0, 28, 8
bm = bmesh.new()
uvl = bm.loops.layers.uv.new("UVMap")
for signo in (1, -1):           # dos haces opuestos (la lampara tiene dos lentes)
    filas = []
    for k in range(ANILLOS + 1):
        t = k / ANILLOS
        d = (t ** 1.2) * LARGO
        r = R0 + (R1 - R0) * t
        fila = []
        for i in range(SEG):
            a = 2 * math.pi * i / SEG
            fila.append(bm.verts.new((r * math.cos(a), signo * d, r * math.sin(a) * 0.8)))
        filas.append(fila)
    for k in range(ANILLOS):
        for i in range(SEG):
            j = (i + 1) % SEG
            try:
                f = bm.faces.new((filas[k][i], filas[k][j], filas[k + 1][j], filas[k + 1][i]) if signo > 0 else (filas[k][j], filas[k][i], filas[k + 1][i], filas[k + 1][j]))
            except ValueError:
                continue
            for l, (vi, kk) in zip(f.loops, ((i, k), (j, k), (j, k + 1), (i, k + 1)) if signo > 0 else ((j, k), (i, k), (i, k + 1), (j, k + 1))):
                l[uvl].uv = (vi / SEG if vi != 0 or l.vert is not filas[kk][0] else 0, kk / ANILLOS)
ob = objeto("Haz_Faro", bm, material("M_Haz_Faro", (1.0, 0.85, 0.55)), col, LAMPARA)
# la normal debe apuntar hacia fuera del cono
print("HAZ", len(ob.data.polygons), "caras")
exportar(col, os.path.join(OUT, "Faro_Haz.fbx"))

# ------------------------------------------------------------------ 2) figura del cuidador
colf = coleccion("Figura_Cuidador")
rnd = random.Random(1313)
bm = bmesh.new()


def anillo(z, rx, ry, seg=10, ox=0.0, oy=0.0, ruido=0.0):
    vs = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        k = 1.0 + rnd.uniform(-ruido, ruido)
        vs.append(bm.verts.new((ox + rx * k * math.cos(a), oy + ry * k * math.sin(a), z)))
    return vs


def unir(a, b):
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))


def tapar(a, arriba=True):
    bm.faces.new(a if arriba else a[::-1])


# cuerpo: abrigo largo en campana, algo encorvado hacia delante (-Y es "delante" en Blender)
perfil = [  # (z, rx, ry, ox, oy)
    (0.05, 0.50, 0.36, 0.00, 0.02), (0.30, 0.44, 0.31, 0.00, 0.01), (0.65, 0.34, 0.25, 0.00, -0.01),
    (1.00, 0.28, 0.21, 0.00, -0.03), (1.25, 0.31, 0.22, 0.00, -0.06), (1.42, 0.28, 0.20, 0.00, -0.10),
    (1.52, 0.17, 0.15, 0.00, -0.13)]
filas = [anillo(z, rx, ry, 12, ox, oy, 0.07) for z, rx, ry, ox, oy in perfil]
for a, b in zip(filas, filas[1:]):
    unir(a, b)
tapar(filas[0], False)
# cabeza con capucha (ovoide caido hacia delante) y cara hueca
cab = [anillo(1.50, 0.15, 0.15, 10, 0, -0.13), anillo(1.60, 0.19, 0.20, 10, 0, -0.19), anillo(1.74, 0.18, 0.21, 10, 0, -0.22),
       anillo(1.84, 0.12, 0.17, 10, 0, -0.21), anillo(1.89, 0.05, 0.08, 10, 0, -0.19)]
for a, b in zip(cab, cab[1:]):
    unir(a, b)
tapar(cab[-1], True)
# brazos largos que cuelgan (mas largos de lo normal), uno ligeramente separado del cuerpo
def brazo(lado, sep):
    pts = [(1.38, 0.0), (1.12, 0.05), (0.82, 0.08), (0.52, 0.09), (0.30, 0.08), (0.14, 0.05)]
    radios = [0.075, 0.062, 0.052, 0.046, 0.04, 0.034]
    fs = []
    for (z, dy), r in zip(pts, radios):
        fs.append(anillo(z, r, r, 6, lado * (0.30 + sep * (1.38 - z)), -0.07 + dy * -1.0))
    for a, b in zip(fs, fs[1:]):
        unir(a, b)
    tapar(fs[0], True)
    tapar(fs[-1], False)
brazo(1, 0.04)
brazo(-1, 0.12)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
fig = objeto("Cuidador", bm, material("M_Figura_Cuidador", (0.012, 0.014, 0.018), 0.95), colf)
for p in fig.data.polygons:
    p.use_smooth = True
print("FIGURA", len(fig.data.polygons), "caras")
exportar(colf, os.path.join(OUT, "Figura_Cuidador.fbx"))
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
