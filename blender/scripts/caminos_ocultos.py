# Los 3 caminos ocultos del final (Camino_Cueva, Camino_Puente, Camino_Farero) como CINTAS de malla pegadas al terreno,
# para que en Unity se puedan revelar poco a poco (luz del faro). Coleccion "Caminos_Ocultos":
#   Oculto_Cueva / Oculto_Puente / Oculto_Farero   (UV0 = (0..1 a lo ancho, 0..1 a lo largo: 0 en el cruce con el camino principal))
# Tambien pone "intensidad" = 0 en esas 3 curvas (la original queda en "intensidad_original") para que texturizar_isla.py
# ya no las pinte en la textura de la isla.
# Uso: blender -b archivo.blend --python caminos_ocultos.py -- [--save]
import bpy, bmesh, math, sys
from mathutils import Vector
from mathutils import geometry as mgeo

S = bpy.context.scene
I = bpy.data.objects["IslandModel"]
bpy.context.view_layer.update()
inv = I.matrix_world.inverted()
dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
SOBRE = 0.06                       # la cinta flota un poco sobre el suelo
PASO = 0.6


def suelo(x, y):
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    return (I.matrix_world @ l).z if h else None


def polilinea(o):
    pts = []
    for sp in o.data.splines:
        bp = sp.bezier_points
        for i in range(len(bp) - 1):
            seg = mgeo.interpolate_bezier(o.matrix_world @ bp[i].co, o.matrix_world @ bp[i].handle_right,
                                          o.matrix_world @ bp[i + 1].handle_left, o.matrix_world @ bp[i + 1].co, 32)
            pts += [Vector((p.x, p.y)) for p in seg]
    out = [pts[0]]
    for p in pts[1:]:
        if (p - out[-1]).length >= PASO:
            out.append(p)
    return out


def mat(nombre, color):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.95
    m.diffuse_color = (*color, 1)
    return m

M_CAMINO = mat("M_CaminoOculto", (0.12, 0.085, 0.055))

col = bpy.data.collections.get("Caminos_Ocultos")
if col:
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
else:
    col = bpy.data.collections.new("Caminos_Ocultos")
    S.collection.children.link(col)

NOMBRES = {"Camino_Cueva": "Oculto_Cueva", "Camino_Puente": "Oculto_Puente", "Camino_Farero": "Oculto_Farero"}
for cn, on in NOMBRES.items():
    cu = bpy.data.objects[cn]
    if "intensidad_original" not in cu:
        cu["intensidad_original"] = float(cu.get("intensidad", 1.0))
    hw = float(cu.get("ancho", 1.5)) / 2.0
    pts = polilinea(cu)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    # distancia acumulada para UV y para ensanchar un poco el extremo (se difumina con el terreno)
    L = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        L.append(L[-1] + (b - a).length)
    total = L[-1]
    filas = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
        if t.length < 1e-6:
            continue
        t.normalize()
        nrm = Vector((-t.y, t.x))
        u = L[i] / total
        ancho_local = hw * (0.75 + 0.25 * math.sin(L[i] * 0.9) ) * (1.0 - 0.35 * max(0.0, (u - 0.85) / 0.15))   # estrecho al final
        fila = []
        for s in (-1.0, 0.0, 1.0):                                  # 3 vertices a lo ancho para que copie el terreno
            q = p + nrm * s * ancho_local
            g = suelo(q.x, q.y)
            if g is None:
                g = suelo(p.x, p.y)
            fila.append(bm.verts.new((q.x, q.y, (g if g is not None else 0.0) + SOBRE)))
        filas.append((fila, u))
    for (f0, u0), (f1, u1) in zip(filas[:-1], filas[1:]):
        for k in range(2):
            face = bm.faces.new((f0[k], f0[k + 1], f1[k + 1], f1[k]))
            for lp, (uu, vv) in zip(face.loops, ((k / 2, u0), ((k + 1) / 2, u0), ((k + 1) / 2, u1), (k / 2, u1))):
                lp[uvl].uv = (uu, vv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(on)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M_CAMINO)
    ob = bpy.data.objects.new(on, me)
    ob["longitud"] = total
    ob["ancho"] = hw * 2
    col.objects.link(ob)
    cu["intensidad"] = 0.0
    print("OCULTO", on, "longitud", round(total, 1), "m, puntos", len(pts), "tris", len(me.polygons))

if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
