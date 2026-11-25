# Exporta los brazos del protagonista de Alejandro (blender/protagonist.blend) a Unity: Assets/Models/Faro/Personajes/Protagonista.fbx
# El .blend trae brazos con esqueleto (IK en antebrazos, copias de rotacion en dedos) y 5 acciones utiles, pero SIN textura (apuntaba a un
# archivo externo) y SIN linterna (la mano derecha esta cerrada alrededor de un asa invisible). Aqui:
#   1. aplica el desplazamiento de la malla (protag_arms) a sus vertices, para que quede igual al de la armadura
#   2. separa la malla en dos materiales segun los pesos: manga (tela encerada oscura) y mano (piel palida)
#   3. construye una linterna de aceite en la mano derecha, colgando del asa que ya sujetan los dedos, atada al hueso Wrist.R
#   4. limpia acciones (se van las de 1 fotograma) y NLA, y exporta todas las acciones con la pose final (IK/constraints horneados)
# Ejes del modelo: adelante = -Y, arriba = +Z, el origen esta a la altura del pecho (hombros en z=0.52, manos en 0.2-0.5).
# NO guarda el .blend.   Uso: blender -b blender/protagonist.blend --python blender/scripts/exportar_protagonista.py
import bpy, bmesh, math, os
from math import radians
import numpy as np
from mathutils import Matrix, Vector

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro", "Personajes")
os.makedirs(OUT, exist_ok=True)
arm = bpy.data.objects["Armature"]
malla = bpy.data.objects["protag_arms"]
escena = bpy.context.scene

# ------------------------------------------------------------------ 1. malla con su desplazamiento aplicado
mw = malla.matrix_world.copy()
malla.parent = None
malla.data.transform(mw)
malla.matrix_world = Matrix.Identity(4)
malla.parent = arm
malla.matrix_parent_inverse = Matrix.Identity(4)
for p in malla.data.polygons:
    p.use_smooth = True


def mat(nombre, color, rugosidad, metal=0.0, emision=None, fuerza=0.0):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    pr = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    pr.inputs["Base Color"].default_value = (*color, 1.0)
    pr.inputs["Roughness"].default_value = rugosidad
    pr.inputs["Metallic"].default_value = metal
    if emision is not None:
        pr.inputs["Emission Color"].default_value = (*emision, 1.0)
        pr.inputs["Emission Strength"].default_value = fuerza
    return m


# ------------------------------------------------------------------ 2. materiales por pesos: mano (muneca y dedos) / manga
PIEL = ("Wrist", "Middle", "Ring", "Index", "Thumb", "Pinky")
grupos_piel = {g.index for g in malla.vertex_groups if g.name.startswith(PIEL)}
malla.data.materials.clear()
malla.data.materials.append(mat("B_Prota_Manga", (0.075, 0.085, 0.090), 0.55))     # tela encerada gris azulada, casi negra
malla.data.materials.append(mat("B_Prota_Piel", (0.62, 0.50, 0.44), 0.6))          # piel palida y fria
peso_piel = np.zeros(len(malla.data.vertices))
peso_tot = np.zeros(len(malla.data.vertices))
for i, v in enumerate(malla.data.vertices):
    for g in v.groups:
        peso_tot[i] += g.weight
        if g.group in grupos_piel:
            peso_piel[i] += g.weight
en_piel = peso_piel > 0.5 * np.maximum(peso_tot, 1e-6)
for p in malla.data.polygons:
    mano_pos = abs(sum(malla.data.vertices[v].co.x for v in p.vertices) / len(p.vertices)) > 0.345    # mas alla de la muneca (reposo en T)
    p.material_index = 1 if mano_pos else 0                      # corte recto en la muneca: por pesos salia dentado
print("PROTA caras de piel:", sum(1 for p in malla.data.polygons if p.material_index == 1), "de", len(malla.data.polygons), flush=True)

# ------------------------------------------------------------------ 2b. mangas largas
# Las mangas de Alejandro acaban en el hombro con un remate plano (modelo pensado para verse desde atras). En primera persona se veria ese
# corte flotando delante de la camara, asi que se abre el remate y se alarga cada manga ~0.9 hacia atras (4 tramos), siguiendo el eje del
# brazo y heredando los pesos del borde, para que salgan por debajo de la pantalla.
# Con la pose de primera persona (brazos hacia delante, hombros por debajo del borde de la pantalla) el corte del hombro no se ve, y la
# extrusion automatica daba mallas rotas en el brazo derecho: queda desactivada. (Pensada para un remate aplastado: ver historial de git.)
EXTENDER_MANGAS = False
LARGO_MANGA, TRAMOS = 0.7, 4
bm = bmesh.new()
bm.from_mesh(malla.data)
dl = bm.verts.layers.deform.verify()
mwm = malla.matrix_world
for signo in ((-1, 1) if EXTENDER_MANGAS else ()):
    arriba = [f for f in bm.faces if (mwm @ f.calc_center_median()).z > 0.50 and (mwm @ f.calc_center_median()).x * signo > 0 and abs((mwm @ f.calc_center_median()).x) < 0.3]   # el remate del hombro esta aplastado: se corta mas abajo, donde la manga es un tubo limpio
    bmesh.ops.delete(bm, geom=arriba, context='FACES_ONLY')
    def centro(z0, z1):
        vs = [mwm @ v.co for v in bm.verts if z0 <= (mwm @ v.co).z < z1 and (mwm @ v.co).x * signo > 0 and abs((mwm @ v.co).x) < 0.3]
        return sum(vs, Vector()) / len(vs)
    eje = (centro(0.47, 0.50) - centro(0.38, 0.42)).normalized()                    # eje del tubo (del codo al hombro)
    borde = [e for e in bm.edges if e.is_boundary and all((mwm @ v.co).z > 0.42 and (mwm @ v.co).x * signo > 0 and abs((mwm @ v.co).x) < 0.3 for v in e.verts)]
    print("PROTA manga", signo, "eje", tuple(round(c, 2) for c in eje), "aristas de borde", len(borde), flush=True)
    for k in range(TRAMOS):
        r = bmesh.ops.extrude_edge_only(bm, edges=borde)
        nv = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, vec=malla.matrix_world.inverted().to_3x3() @ (eje * LARGO_MANGA / TRAMOS), verts=nv)
        borde = [g for g in r["geom"] if isinstance(g, bmesh.types.BMEdge) and g.is_boundary]
        for f in {f for v in nv for f in v.link_faces}:
            f.material_index = 0
            f.smooth = True
sin_peso = [v for v in bm.verts if len(v[dl]) == 0 and (mwm @ v.co).z > 0.5]
print("PROTA vertices de manga sin peso:", len(sin_peso), flush=True)
if sin_peso:                                                       # por si la extrusion no copia los pesos: del vertice con peso mas cercano
    con = [v for v in bm.verts if len(v[dl]) > 0 and (mwm @ v.co).z > 0.5]
    for v in sin_peso:
        w = min(con, key=lambda u: (u.co - v.co).length)
        for g, val in w[dl].items():
            v[dl][g] = val
bm.to_mesh(malla.data)
bm.free()
malla.data.update()

# ------------------------------------------------------------------ 2c. brazo derecho hacia delante
# Poses de primera persona. Los brazos de Alejandro estan pensados para verse desde atras: el izquierdo adelantado a la altura del pecho
# (visto desde dentro parece un sonambulo) y el derecho colgando recto. Se recolocan las manos (el IK recoloca codos y antebrazos),
# conservando el giro y el balanceo originales de la mano izquierda en Reposo y Marcha:
#   izquierda: bajada y algo pegada al cuerpo (brazo relajado)
#   derecha:   REFLEJO de la izquierda ya bajada (antebrazo hacia delante, mano en el mismo giro: palma abajo, dedos hacia delante), un poco
#              mas alta; con los dedos cerrados queda un puno sobre una barra transversal (X): el asa de la linterna.
def canales(act):
    return [f for l in act.layers for st in l.strips for cb in st.channelbags for f in cb.fcurves]


F = Matrix.Diagonal((-1.0, 1.0, 1.0, 1.0))
BAJA_IZQ = Vector((0.04, 0.20, -0.04))        # base de la mano derecha (reflejo de la izquierda original + esto): x izq +, y atras +, z arriba +
SUBE_DER = Vector((0.0, 0.0, 0.07))
# Mano izquierda: cuelga relajada junto al muslo (no adelantada). Objetivo absoluto + el balanceo original de la toma; el codo (polo del IK)
# queda atras, hacia fuera y abajo, como en un brazo que cuelga con el codo algo flexionado.
CAIDA_HOMBRO_IZQ = 70.0     # grados (signo: prueba en la salida 'Forearm.L')
MANO_IZQ_REPOSO = Vector((0.22, 0.04, -0.06))
CODO_IZQ_REPOSO = Vector((0.27, 0.12, 0.18))
for nombre in ("Holding_Lantern_Idle", "Holding_Lantern_Walking"):
    act = bpy.data.actions[nombre]
    arm.animation_data.action = act
    frames = sorted({int(round(k.co[0])) for f in canales(act) if f.data_path == 'pose.bones["Control.Hand.L"].location' for k in f.keyframe_points})
    original = {}
    for fr in frames:
        escena.frame_set(fr)
        bpy.context.view_layer.update()
        original[fr] = {h: arm.pose.bones[h].matrix.copy() for h in ("Control.Hand.L", "Control.Elbow.L")}
    f0 = frames[0]
    for fr in frames:
        escena.frame_set(fr)
        # brazo izquierdo: el hombro se gira hacia abajo para que el codo cuelgue junto al cuerpo (el IK solo mueve el antebrazo)
        brazo = arm.pose.bones["Arm.L"]
        brazo.rotation_mode = 'QUATERNION'
        brazo.rotation_quaternion = (1, 0, 0, 0)
        bpy.context.view_layer.update()
        c = brazo.head.copy()
        base_m = brazo.matrix.copy()
        d = arm.pose.bones["Forearm.L"].head - c
        d.z = 0.0
        eje_g = Vector((0, 0, 1)).cross(d.normalized())               # perpendicular al brazo, horizontal: girar alrededor baja/sube el codo
        mejor = None
        for sg in (1, -1):
            g = Matrix.Translation(c) @ Matrix.Rotation(sg * radians(CAIDA_HOMBRO_IZQ), 4, eje_g) @ Matrix.Translation(-c)
            z_codo = (g @ arm.pose.bones["Forearm.L"].head).z
            if mejor is None or z_codo < mejor[0]:
                mejor = (z_codo, g)
        brazo.matrix = mejor[1] @ base_m
        bpy.context.view_layer.update()
        brazo.keyframe_insert("rotation_quaternion", frame=fr)
        for izq, der in (("Control.Hand.L", "Control.Hand.R"), ("Control.Elbow.L", "Control.Elbow.R")):
            orig = original[fr][izq]
            es_mano = izq.startswith("Control.Hand")
            # derecha: reflejo de la izquierda original (ya probado)
            mi = orig.copy()
            mi.translation = mi.translation + (BAJA_IZQ if es_mano else Vector((0, 0, -0.04)))
            md = F @ mi @ F
            if es_mano:
                md.translation = md.translation + SUBE_DER
            # izquierda: pose colgante propia
            ml = orig.copy()
            base = MANO_IZQ_REPOSO if es_mano else CODO_IZQ_REPOSO
            ml.translation = base + (orig.translation - original[f0][izq].translation)
            for pb, m in ((arm.pose.bones[izq], ml), (arm.pose.bones[der], md)):
                pb.matrix = m
                bpy.context.view_layer.update()
                pb.keyframe_insert("location", frame=fr)
                pb.keyframe_insert("rotation_quaternion", frame=fr)
    print("PROTA manos recolocadas en", nombre, "fotogramas", frames, flush=True)
# Puno derecho: los dedos derechos de Alejandro van casi en reposo (abiertos) porque su agarre depende de la mano original. Se calcula la pose
# de los dedos izquierdos con la curvatura al maximo (los huesos izquierdos obedecen a Control.Fingers.L) y se copia al lado derecho
# (rig simetrico: el mismo giro local cierra la mano contraria).
CURVA_PUNO = 0.92
PUNO_DERECHO = False        # desactivado a peticion del usuario: se prefiere la mano derecha original (dedos de Alejandro)
PREF = ("Index", "Middle", "Ring", "Pinky", "Thumb")
dedos = [] if not PUNO_DERECHO else [b.name for b in arm.pose.bones if b.name.endswith(".L") and b.name.startswith(PREF) and b.name[:-2] + ".R" in arm.pose.bones]
arm.animation_data.action = None
ctl = arm.pose.bones["Control.Fingers.L"]
ctl.location = (0.0, 0.0, CURVA_PUNO)
bpy.context.view_layer.update()
base_puno = {}
for n in dedos:
    pb = arm.pose.bones[n]
    rel = pb.bone.matrix_local if pb.parent is None else pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
    pose_rel = pb.matrix if pb.parent is None else pb.parent.matrix.inverted() @ pb.matrix
    base_puno[n[:-2] + ".R"] = (rel.inverted() @ pose_rel).to_quaternion()
for nombre in ("Holding_Lantern_Idle", "Holding_Lantern_Walking"):
    act = bpy.data.actions[nombre]
    arm.animation_data.action = act
    frames = sorted({int(round(k.co[0])) for f in canales(act) if f.data_path == 'pose.bones["Control.Hand.L"].location' for k in f.keyframe_points})
    for fr in frames:
        escena.frame_set(fr)
        for n, q in base_puno.items():
            pb = arm.pose.bones[n]
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=fr)
print("PROTA puno derecho: huesos", len(base_puno), flush=True)
arm.animation_data.action = bpy.data.actions["Holding_Lantern_Idle"]
escena.frame_set(0)
bpy.context.view_layer.update()
for n in ("Forearm.L", "Wrist.L", "Forearm.R", "Wrist.R"):
    print("PROTA", n, tuple(round(c, 3) for c in (arm.matrix_world @ arm.pose.bones[n].head)), flush=True)

# ------------------------------------------------------------------ 3. linterna de aceite en la mano derecha
acc = bpy.data.actions["Holding_Lantern_Idle"]
if arm.animation_data is None:
    arm.animation_data_create()
arm.animation_data.action = acc
escena.frame_set(0)
bpy.context.view_layer.update()
# el asa (barra horizontal en X) pasa por dentro de los dedos curvados: punto medio de las falanges 03 de indice a menique
pts = [arm.pose.bones[n].head for n in ("Index.03.R", "Middle.03.R", "Ring.03.R", "Pinky.03.R")]
agarre = sum(pts, Vector()) / len(pts)
agarre.z += 0.012
print("PROTA agarre de la linterna", tuple(round(c, 3) for c in agarre), flush=True)

ESC = 0.95                                                       # linterna de ~29 cm (la lectura en pantalla pide algo mas que el real)
bm = bmesh.new()


def tubo(p0, p1, radio, seg=6, mat_i=0):
    p0, p1 = Vector(p0) * ESC, Vector(p1) * ESC
    d = p1 - p0
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radio * ESC, radius2=radio * ESC, depth=d.length,
                              matrix=Matrix.Translation((p0 + p1) / 2) @ rot)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat_i


def cono(radio_a, radio_b, z0, z1, seg=16, mat_i=0):
    r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radio_a * ESC, radius2=radio_b * ESC, depth=(z1 - z0) * ESC,
                              matrix=Matrix.Translation((0, 0, (z0 + z1) / 2 * ESC)))
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat_i


cono(0.056, 0.020, -0.092, -0.064, mat_i=0)                      # tapa conica
cono(0.018, 0.014, -0.064, -0.050, seg=10, mat_i=0)              # chimenea
cono(0.046, 0.046, -0.200, -0.092, mat_i=1)                      # cristal (emisivo, ambar)
cono(0.054, 0.050, -0.218, -0.200, mat_i=0)                      # base
for k in range(4):                                               # barras verticales
    a = k * math.pi / 2 + math.pi / 4
    x, y = math.cos(a) * 0.047, math.sin(a) * 0.047
    tubo((x, y, -0.200), (x, y, -0.092), 0.0036)
r = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.016 * ESC)      # llama
bmesh.ops.scale(bm, vec=(0.8, 0.8, 1.6), verts=r["verts"])
bmesh.ops.translate(bm, vec=(0, 0, -0.148 * ESC), verts=r["verts"])
for f in {f for v in r["verts"] for f in v.link_faces}:
    f.material_index = 2
# asa: semicirculo en el plano XZ desde los lados de la tapa hasta la barra que sujeta la mano (z = 0)
z_tapa, alto, rad = -0.080, 0.080, 0.050
ant = None
for i in range(13):
    a = math.pi * i / 12
    p = (math.cos(a) * rad, 0.0, z_tapa + math.sin(a) * alto)
    if ant is not None:
        tubo(ant, p, 0.0030, seg=5)
    ant = p
tubo((-0.016, 0, 0.0), (0.016, 0, 0.0), 0.0040, seg=6)           # barra del agarre (dentro del puno)

lm = bpy.data.meshes.new("Linterna_Mano")
bm.to_mesh(lm)
bm.free()
lm.materials.append(mat("B_Linterna_Hierro", (0.035, 0.035, 0.040), 0.45, metal=0.85))
lm.materials.append(mat("B_Linterna_Cristal", (1.0, 0.62, 0.24), 0.2, emision=(1.0, 0.55, 0.18), fuerza=1.5))
lm.materials.append(mat("B_Linterna_Llama", (1.0, 0.85, 0.45), 0.2, emision=(1.0, 0.80, 0.35), fuerza=6.0))
for p in lm.polygons:
    p.use_smooth = True
lin = bpy.data.objects.new("Linterna_Mano", lm)
escena.collection.objects.link(lin)
# atar al hueso de la muneca derecha manteniendo la posicion del agarre en la pose de reposo de la animacion
lin.parent = arm
lin.parent_type = 'BONE'
lin.parent_bone = "Wrist.R"
lin.matrix_parent_inverse = Matrix.Identity(4)
lin.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
W0 = lin.matrix_world.copy()
lin.matrix_parent_inverse = W0.inverted() @ Matrix.Translation(agarre)
bpy.context.view_layer.update()
print("PROTA linterna en", tuple(round(c, 3) for c in lin.matrix_world.translation), flush=True)

# ------------------------------------------------------------------ 4. acciones utiles y exportacion
USAR = ["Holding_Lantern_Idle", "Holding_Lantern_Walking", "Grab_Object", "Hold_RightH_VerticalO_Balance", "Hold_RightH_HorizontalO_Balance"]
for a in list(bpy.data.actions):
    a.use_fake_user = False
    if a.name not in USAR:
        bpy.data.actions.remove(a)
for a in bpy.data.actions:
    a.use_fake_user = True            # las que quedan se exportan todas como tomas
for t in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(t)
arm.animation_data.action = bpy.data.actions["Holding_Lantern_Idle"]
# La mano izquierda de Alejandro esta cerrada en pinza (Control.Fingers.L z = 0.735 en todas las tomas): esa pose es para cuando el jugador
# interactue con un objeto. En reposo y al andar se deja relajada (curvatura 0.28 de 1); la pinza queda solo en Grab_Object.
MANO_IZQ_RELAJADA = 0.5
for nombre in ("Holding_Lantern_Idle", "Holding_Lantern_Walking", "Hold_RightH_VerticalO_Balance", "Hold_RightH_HorizontalO_Balance"):
    act = bpy.data.actions[nombre]
    for fc in [f for l in act.layers for st in l.strips for cb in st.channelbags for f in cb.fcurves]:
        if fc.data_path == 'pose.bones["Control.Fingers.L"].location' and fc.array_index == 2:
            for k in fc.keyframe_points:
                k.co[1] = MANO_IZQ_RELAJADA
                k.handle_left[1] = k.handle_right[1] = MANO_IZQ_RELAJADA
            fc.update()
            print("PROTA mano izquierda relajada en", nombre, flush=True)
print("PROTA acciones:", [(a.name, tuple(round(x) for x in a.frame_range)) for a in bpy.data.actions], flush=True)
for x in bpy.context.view_layer.objects:
    x.select_set(False)
for o in (arm, malla, lin):
    o.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "Protagonista.fbx"), use_selection=True, global_scale=1.0,
                         apply_scale_options='FBX_SCALE_ALL', bake_anim=True, bake_anim_use_all_actions=True,
                         bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0.0, add_leaf_bones=False,
                         object_types={'ARMATURE', 'MESH'}, path_mode='STRIP', use_tspace=True,
                         colors_type='NONE', use_armature_deform_only=True, bake_space_transform=False)
print("EXPORTADO Protagonista", flush=True)

# Depuracion visual (FARO_RENDER=carpeta): vistas lateral y superior de la pose de Reposo, con el esqueleto a la vista
if os.environ.get("FARO_RENDER"):
    from math import radians
    escena.frame_set(0)
    bpy.context.view_layer.update()
    arm.show_in_front = True
    arm.data.display_type = 'STICK'
    escena.render.engine = 'BLENDER_WORKBENCH'
    escena.render.resolution_x, escena.render.resolution_y = 900, 700
    cam = bpy.data.objects.new("DbgCam", bpy.data.cameras.new("DbgCam"))
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 1.6
    escena.collection.objects.link(cam)
    escena.camera = cam
    for nom, loc, rot in (("lado", (4, -0.1, 0.45), (90, 0, 90)), ("arriba", (0, -0.2, 4), (0, 0, 0)), ("frente", (0, -4, 0.45), (90, 0, 0))):
        cam.location, cam.rotation_euler = loc, [radians(a) for a in rot]
        escena.render.filepath = os.path.join(os.environ["FARO_RENDER"], "dbg_" + nom + ".png")
        bpy.ops.render.render(write_still=True)
