# Prepara y exporta el calamar gigante de Alejandro (blender/giant_squid.blend) a Unity: Assets/Models/Faro/Peces/Calamar.fbx (+ Tex/Calamar_c.png)
# El .blend trae la malla SIN atar al esqueleto (sin pesos ni modificador) y la unica accion ("jump") es de un rig humano, asi que aqui:
#   1. aplica escalas y orienta el animal (tentaculos hacia -Y, que en Unity es "adelante"; manto hacia +Y)
#   2. crea 8 cadenas de huesos para los brazos (cada brazo es una isla de la malla al cortar por debajo de la cabeza) y cuelga
#      de la raiz los dos tentaculos largos que ya traia (Tent.*)
#   3. ata la malla con pesos por distancia al hueso mas cercano
#   4. anima un ciclo de nado de 48 fotogramas a 24 fps (ondas que recorren mazas y brazos, cabeceo suave del cuerpo)
#   5. pinta la piel (pintar_calamar.py) y exporta
# NO guarda el .blend.   Uso: blender -b blender/giant_squid.blend --python blender/scripts/exportar_calamar.py [-- --previa ruta.png]
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Matrix, Vector

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro", "Peces")
TEX = os.path.join(OUT, "Tex")
os.makedirs(TEX, exist_ok=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ESCALA_UNITY = 11.0         # el modelo mide ~7.9 m: x11 -> ~87 m de largo, manto de ~17 m de ancho, brazos de ~38 m y mazas de ~43 m: asoma por encima de las rocas de 30 m del puzle 2
FRAMES = 48                 # un ciclo de nado: 2 s a 24 fps

body = bpy.data.objects["body"]
arm = bpy.data.objects["Armature"]
ojos = [o for o in bpy.data.objects if o.type == 'MESH' and o is not body]
escena = bpy.context.scene

# ------------------------------------------------------------------ 1. aplicar transformaciones y orientar
mundo = {o: o.matrix_world.copy() for o in [body] + ojos}
for o in ojos:
    if o.data.users > 1:          # los dos ojos comparten la misma malla (el segundo es el reflejo por la matriz del objeto): sin copiarla
        o.data = o.data.copy()    # se transformaba dos veces y los dos ojos acababan en el mismo sitio, lejos de la cabeza
for o in [body] + ojos:
    o.parent = None
    o.data.transform(mundo[o])
    if mundo[o].determinant() < 0:      # matriz reflejada: se invierten las caras para que no queden del reves
        o.data.flip_normals()
    o.matrix_world = Matrix.Identity(4)
# el modelo viene con el manto hacia +Z y los tentaculos hacia -Z, y las mazas se curvan hacia -Y: giro (x,y,z) -> (-x, z, y) (propio, det +1):
# tentaculos a -Y (adelante en Unity) y las mazas cuelgan hacia abajo
R = Matrix(((-1, 0, 0, 0), (0, 0, 1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
for o in [body] + ojos:
    o.data.transform(R)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for eb in arm.data.edit_bones:
    eb.transform(R)
bpy.ops.object.mode_set(mode='OBJECT')
for m in list(body.modifiers):          # el subsurf duplicaba las caras al exportar; la malla ya es densa (22 mil vertices)
    body.modifiers.remove(m)
for o in [body] + ojos:
    for p in o.data.polygons:
        p.use_smooth = True
for o in ojos:      # ojos x1.7 sobre su propio centro (x2.5 los hacia pelotas que sobresalian de la cabeza)
    cen = np.mean([v.co[:] for v in o.data.vertices], axis=0)
    for v in o.data.vertices:
        v.co = Vector(cen) + (v.co - Vector(cen)) * 1.35
co = np.array([v.co[:] for v in body.data.vertices], dtype=np.float64)
# Los calamares tienen los ojos en los LADOS de la cabeza, no delante: se colocan sobre el costado, a media altura, hundidos a medias en la
# piel (el original los tenia delante y abajo, junto al pico). Se busca el costado real de la malla en esa zona.
OJO_Y, OJO_Z, HUNDIDO = -0.42, 0.02, 0.60            # posicion en la cabeza; fraccion del radio que queda dentro del cuerpo
for o in ojos:
    pts = np.array([v.co[:] for v in o.data.vertices])
    cen = pts.mean(axis=0)
    radio = float(np.linalg.norm(pts - cen, axis=1).mean())
    lado = 1.0 if cen[0] > 0 else -1.0
    zona = (np.abs(co[:, 1] - OJO_Y) < 0.25) & (np.abs(co[:, 2] - OJO_Z) < 0.2) & (co[:, 0] * lado > 0.1)
    xs = float(np.abs(co[zona, 0]).max()) if zona.any() else 0.42
    nuevo = np.array([lado * (xs - HUNDIDO * radio), OJO_Y, OJO_Z])
    for v in o.data.vertices:
        p = Vector(v.co) - Vector(cen)
        p.x *= 0.7                                  # achatado hacia el costado: lente, no pelota
        v.co = Vector(nuevo) + p
    print("CALAMAR ojo", o.name, "lado", lado, "costado x=%.2f" % xs, "radio %.3f" % radio, "centro", np.round(nuevo, 3), flush=True)
print("CALAMAR orientado: x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (co[:, 0].min(), co[:, 0].max(), co[:, 1].min(), co[:, 1].max(), co[:, 2].min(), co[:, 2].max()), flush=True)


def dist_seg(P, a, b):
    d = b - a
    t = np.clip(((P - a) @ d) / max(float(d @ d), 1e-9), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * d), axis=1)


# ------------------------------------------------------------------ 2. huesos de los brazos
viejos = [(np.array(b.head_local), np.array(b.tail_local)) for b in arm.data.bones if b.name != "Bone"]
dmin = np.full(len(co), 9.0)
for a, b in viejos:
    dmin = np.minimum(dmin, dist_seg(co, a, b))
zona = (co[:, 1] < -1.0) & (dmin > 0.15)          # brazos por debajo de la cabeza, sin las mazas
bm = bmesh.new()
bm.from_mesh(body.data)
bm.verts.ensure_lookup_table()
vistos, comps = set(), []
for i in np.nonzero(zona)[0]:
    if i in vistos:
        continue
    pila, c = [i], []
    vistos.add(i)
    while pila:
        x = pila.pop()
        c.append(x)
        for e in bm.verts[x].link_edges:
            o = e.other_vert(bm.verts[x]).index
            if zona[o] and o not in vistos:
                vistos.add(o)
                pila.append(o)
    if len(c) > 500:
        comps.append(np.array(c))
bm.free()
print("CALAMAR brazos encontrados:", len(comps), flush=True)

NBR = 6                                           # huesos por brazo
cadenas = []                                       # por brazo: lista de nombres
bpy.ops.object.mode_set(mode='EDIT')
ed = arm.data.edit_bones
raiz = ed["Bone"]
for n in ("Tent.001.L", "Tent.001.R"):             # las mazas ya traian su cadena, pero sin padre
    ed[n].parent = raiz
    ed[n].use_connect = False
for k, c in enumerate(comps):
    P = co[c]
    orden = np.argsort(-P[:, 1])                   # de la cabeza (y mayor) a la punta (y menor)
    trozos = np.array_split(orden, NBR)
    nodos = [Vector((P[orden[:60], 0].mean() * 0.4, -0.5, P[orden[:60], 2].mean() * 0.4))]
    for t in trozos:
        nodos.append(Vector(P[t].mean(axis=0)))
    nodos[-1] = Vector((nodos[-1].x, P[:, 1].min(), nodos[-1].z))
    nombres, previo = [], raiz
    for j in range(NBR):
        eb = ed.new("Arm.%d.%d" % (k + 1, j + 1))
        eb.head, eb.tail = nodos[j], nodos[j + 1]
        eb.parent = previo
        eb.use_connect = j > 0
        nombres.append(eb.name)
        previo = eb
    cadenas.append(nombres)
bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------------------------ 3. pesos
huesos = [b for b in arm.data.bones if b.name != "Bone"]
seg_nombre = [b.name for b in huesos]
A = np.array([b.head_local[:] for b in huesos])
B = np.array([b.tail_local[:] for b in huesos])
D = np.stack([dist_seg(co, A[i], B[i]) for i in range(len(huesos))], axis=1)       # (vertices, huesos)
K = 4
cerca = np.argsort(D, axis=1)[:, :K]
dk = np.take_along_axis(D, cerca, axis=1)
w = 1.0 / (dk + 0.015) ** 3
w /= w.sum(axis=1, keepdims=True)
# cabeza y manto: de la raiz; la transicion a los brazos va de y=-0.35 a y=-0.65
wraiz = np.clip((co[:, 1] + 0.65) / 0.30, 0.0, 1.0)
for g in [b.name for b in arm.data.bones]:
    body.vertex_groups.new(name=g)
grupo = {g.name: g for g in body.vertex_groups}
for i in range(len(co)):
    if wraiz[i] > 0.0:
        grupo["Bone"].add([i], float(wraiz[i]), 'REPLACE')
    if wraiz[i] < 1.0:
        for j in range(K):
            grupo[seg_nombre[cerca[i, j]]].add([i], float(w[i, j] * (1.0 - wraiz[i])), 'ADD')
mod = body.modifiers.new("Armature", 'ARMATURE')
mod.object = arm
body.parent = arm
for o in ojos:
    o.vertex_groups.new(name="Bone").add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    o.modifiers.new("Armature", 'ARMATURE').object = arm
    o.parent = arm

def bbox_eval(etq):
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mm = ev.to_mesh()
    cc = np.array([v.co[:] for v in mm.vertices])
    ev.to_mesh_clear()
    print("CALAMAR bbox", etq, np.round(cc.min(axis=0), 2), np.round(cc.max(axis=0), 2), flush=True)


bbox_eval("en reposo, recien atado")

# ------------------------------------------------------------------ 4. animacion de nado (ciclo de FRAMES fotogramas, sin costura)
if arm.animation_data is None:
    arm.animation_data_create()
accion = bpy.data.actions.new("Nado")
arm.animation_data.action = accion
rad = math.radians
for pb in arm.pose.bones:       # el .blend trae una pose residual del rig humano: empezar de cero
    pb.rotation_mode = 'QUATERNION' if pb.name == "Bone" else 'XYZ'
    pb.location = (0.0, 0.0, 0.0)
    pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    pb.rotation_euler = (0.0, 0.0, 0.0)
    pb.scale = (1.0, 1.0, 1.0)


def onda(f, fase, amp_x, amp_z):
    t = 2.0 * math.pi * (f - 1) / FRAMES
    return amp_x * math.sin(t - fase), amp_z * math.sin(t - fase + 1.3)


for f in range(1, FRAMES + 1):
    for pb in arm.pose.bones:
        n = pb.name
        if n == "Bone":
            continue
        if n.startswith("Arm."):
            _, k, j = n.split(".")
            ax, az = onda(f, 0.7 * int(j) + 0.9 * int(k), rad(6.0), rad(4.0))
        else:                                                    # Tent.xxx.L/R y Vent.xxx.L/R: maza larga, onda suave que recorre los 42 huesos
            try:
                i = int(n.split(".")[1])
            except ValueError:
                i = 43
            ax, az = onda(f, 0.45 * i + (0.0 if n.endswith(".L") else 0.9), rad(1.5), rad(1.1))
        pb.rotation_euler = (ax, 0.0, az)
        pb.keyframe_insert("rotation_euler", frame=f)

bbox_eval('con la onda (fotograma 1)')
# cuerpo: cabeceo y balanceo suaves; la correccion de centrado se mete aqui (como en exportar_peces.py): pose' = M @ pose
e = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
escena.frame_set(1)
bpy.context.view_layer.update()
e = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
m = e.to_mesh()
c2 = np.array([v.co[:] for v in m.vertices])
e.to_mesh_clear()
centro = 0.5 * (c2.min(axis=0) + c2.max(axis=0))
M = Matrix.Translation(-Vector(centro))
print("CALAMAR centro previo", tuple(round(float(x), 3) for x in centro), flush=True)
rb = arm.pose.bones["Bone"]
rest = rb.bone.matrix_local.copy()
anterior = None
for f in range(1, FRAMES + 1):
    t = 2.0 * math.pi * (f - 1) / FRAMES
    base = Matrix.Rotation(rad(2.5) * math.sin(t), 4, 'X') @ Matrix.Rotation(rad(2.0) * math.sin(t + 1.6), 4, 'Z')
    nb = rest.inverted() @ M @ rest @ base
    loc, rot, esc = nb.decompose()
    if anterior is not None and rot.dot(anterior) < 0:
        rot.negate()
    anterior = rot
    rb.location, rb.rotation_quaternion, rb.scale = loc, rot, esc
    rb.keyframe_insert("location", frame=f)
    rb.keyframe_insert("rotation_quaternion", frame=f)
    rb.keyframe_insert("scale", frame=f)
escena.frame_start, escena.frame_end = 1, FRAMES
escena.render.fps = 24
escena.frame_set(1)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 5. materiales, textura y exportacion
e = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
m = e.to_mesh()
import pintar_calamar
pintada = pintar_calamar.pintar(m, os.path.join(TEX, "Calamar_c.png"))
e.to_mesh_clear()
mat_cuerpo, mat_ojo = bpy.data.materials.new("B_Calamar"), bpy.data.materials.new("B_Calamar_Ojo")      # un solo material de ojo para los dos
for o, mat in [(body, mat_cuerpo)] + [(x, mat_ojo) for x in ojos]:
    mat.use_nodes = True
    o.data.materials.clear()
    o.data.materials.append(mat)
if "--previa" in sys.argv:
    mat = body.data.materials[0]
    nt = mat.node_tree
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = pintada
    nt.links.new(tx.outputs["Color"], next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED').inputs["Base Color"])
    cam = bpy.data.cameras.new("previa")
    cam.type = 'ORTHO'
    cam.ortho_scale = 9.5
    oc = bpy.data.objects.new("previa", cam)
    escena.collection.objects.link(oc)
    escena.camera = oc
    escena.render.engine = 'BLENDER_WORKBENCH'
    escena.display.shading.light = 'FLAT'
    escena.display.shading.color_type = 'TEXTURE'
    escena.render.resolution_x, escena.render.resolution_y = 1400, 700
    base = sys.argv[sys.argv.index("--previa") + 1]
    for nombre, loc, rot, fr in (("lado", (-12, 0, 0), (90, 0, -90), 1), ("lado_b", (-12, 0, 0), (90, 0, -90), 13), ("arriba", (0, 0, 14), (0, 0, 0), 1)):
        oc.location = loc
        oc.rotation_euler = [rad(x) for x in rot]
        escena.frame_set(fr)
        escena.render.filepath = base.replace(".png", "_" + nombre + ".png")
        bpy.ops.render.render(write_still=True)
    escena.frame_set(1)

for x in bpy.context.view_layer.objects:
    x.select_set(False)
objs = [arm, body] + ojos
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "Calamar.fbx"), use_selection=True, global_scale=ESCALA_UNITY,
                         apply_scale_options='FBX_SCALE_ALL', bake_anim=True, bake_anim_use_all_actions=False,
                         bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0.0, add_leaf_bones=False,
                         object_types={'ARMATURE', 'MESH'}, path_mode='STRIP', use_tspace=True,
                         colors_type='NONE', use_armature_deform_only=True, bake_space_transform=False)
print("EXPORTADO Calamar", len(objs), "objetos", flush=True)
