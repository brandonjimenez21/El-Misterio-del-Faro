# Figura del antiguo cuidador hecha con el modelo del anciano de Alejandro (blender/characters.blend, objeto "old_man").
#  - Lo trae a la escena principal en la coleccion "Figura_Anciano" (se rehace cada vez).
#  - Lo escala a ALTURA m, con los pies en el origen y mirando hacia -Y (igual que la figura "Cuidador").
#  - Le baja los brazos (viene en pose T y sin huesos): gira los vertices de cada brazo alrededor del hombro,
#    con transicion suave en el hombro. Para verse de lejos / en un relampago es suficiente.
#  - Material de silueta M_Figura_Cuidador (las texturas del modelo no vienen dentro del .blend).
#  - Exporta Assets/Models/Faro/Figura_Anciano.fbx
# Uso: blender -b el_misterio_del_faro.blend --python scripts/figura_anciano.py -- --save
#      opciones: --angulo 78 (grados que baja los brazos)  --altura 1.78
import bpy, os, sys, math
from mathutils import Vector, Matrix

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
FUENTE = os.path.join(RAIZ, "blender", "characters.blend")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opcion(nombre, defecto):
    return float(args[args.index(nombre) + 1]) if nombre in args else defecto


ALTURA = opcion("--altura", 1.78)
ANGULO = opcion("--angulo", 78.0)

# --- coleccion limpia
col = bpy.data.collections.get("Figura_Anciano") or bpy.data.collections.new("Figura_Anciano")
if col.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(col)
for o in list(col.objects):
    me = o.data
    bpy.data.objects.remove(o, do_unlink=True)
    if me and me.users == 0:
        bpy.data.meshes.remove(me)

# --- traer la malla del anciano (copia, el .blend de Alejandro no se toca)
with bpy.data.libraries.load(FUENTE, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n == "old_man"]
ob = dst.objects[0]
ob.name = "Anciano"
ob.data.name = "Anciano"
col.objects.link(ob)
me = ob.data

# aplicar transformacion del objeto a los vertices
me.transform(ob.matrix_world)
ob.matrix_world = Matrix.Identity(4)
vs = me.vertices

# --- pies en el origen, centrado en x/y, escalado a la altura
xs = [v.co.x for v in vs]; ys = [v.co.y for v in vs]; zs = [v.co.z for v in vs]
cx, cy, z0 = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)
h = max(zs) - z0
k = ALTURA / h
for v in vs:
    v.co = Vector(((v.co.x - cx) * k, (v.co.y - cy) * k, (v.co.z - z0) * k))

# --- hacia donde mira: el modelo de Alejandro ya mira a -Y (comprobado con --render), como la figura "Cuidador".
#     Si algun dia se reexporta girado, usar --girar
if "--girar" in args:
    for v in vs:
        v.co = Vector((-v.co.x, -v.co.y, v.co.z))
print("ANCIANO: altura %.2f m" % ALTURA)

# --- bajar los brazos
# hombro: franja de los brazos en pose T (entre 0.65 y 0.81 de la altura del modelo original)
brazo = [v.co for v in vs if ALTURA * 0.65 < v.co.z < ALTURA * 0.83 and abs(v.co.x) > 0.2 * k]
z_hombro = sum(c.z for c in brazo) / len(brazo)
y_hombro = sum(c.y for c in brazo) / len(brazo)
x_hombro = 0.115 * k          # donde termina el torso (ancho medido del pecho ~0.12-0.14 en el original)
transicion = 0.07 * k         # ancho de la zona del hombro que se dobla poco a poco
z_min_brazo = ALTURA * 0.60   # por debajo (cinturon, farol, piernas) nada se mueve


def suave(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


for v in vs:
    c = v.co
    if c.z < z_min_brazo:
        continue
    lado = 1.0 if c.x > 0 else -1.0
    w = suave(x_hombro - transicion * 0.4, x_hombro + transicion, abs(c.x))
    if w <= 0.0:
        continue
    # menos efecto en la cabeza/cuello (cerca del centro y arriba)
    a = -lado * math.radians(ANGULO) * w
    piv = Vector((lado * x_hombro, y_hombro, z_hombro))
    d = c - piv
    # giro alrededor del eje Y (frente): x,z
    ca, sa = math.cos(a), math.sin(a)
    v.co = Vector((piv.x + d.x * ca - d.z * sa, c.y, piv.z + d.x * sa + d.z * ca))
    # un poco hacia delante, como si colgaran algo encorvados
    v.co.y -= 0.03 * w

me.update()
for p in me.polygons:
    p.use_smooth = True

# --- material de silueta (el mismo de la figura "Cuidador")
mat = bpy.data.materials.get("M_Figura_Cuidador")
if mat is None:
    mat = bpy.data.materials.new("M_Figura_Cuidador")
    mat.use_nodes = True
    b = mat.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.012, 0.014, 0.018, 1)
    b.inputs["Roughness"].default_value = 0.95
me.materials.clear()
me.materials.append(mat)

# fuera de la vista de la escena principal (es una pieza para exportar, no esta colocada en la isla)
ob.location = (0, 0, 0)
col.hide_render = True

# --- exportar
bpy.ops.object.select_all(action='DESELECT')
ob.hide_set(False)
ob.select_set(True)
bpy.context.view_layer.objects.active = ob
ruta = os.path.join(OUT, "Figura_Anciano.fbx")
bpy.ops.export_scene.fbx(filepath=ruta, use_selection=True, apply_scale_options='FBX_SCALE_ALL', bake_anim=False,
                         add_leaf_bones=False, object_types={'MESH'}, path_mode='STRIP', use_tspace=True)
xs = [v.co.x for v in vs]; zs = [v.co.z for v in vs]
print("ANCIANO exportado:", ruta, "| ancho %.2f m alto %.2f m, %d vertices" % (max(xs) - min(xs), max(zs) - min(zs), len(vs)))

# render de control (frente y perfil) para revisar la pose
if "--render" in args:
    out_dir = args[args.index("--render") + 1]
    escena = bpy.context.scene
    cam_d = bpy.data.cameras.new("CamRev"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = ALTURA * 1.3
    cam = bpy.data.objects.new("CamRev", cam_d); escena.collection.objects.link(cam)
    luz_d = bpy.data.lights.new("LuzRev", 'SUN'); luz_d.energy = 4
    luz = bpy.data.objects.new("LuzRev", luz_d); escena.collection.objects.link(luz)
    luz.rotation_euler = (math.radians(50), 0, math.radians(30))
    escena.camera = cam
    escena.render.resolution_x = 600; escena.render.resolution_y = 800
    escena.render.engine = 'BLENDER_WORKBENCH'
    escena.display.shading.light = 'STUDIO'; escena.display.shading.color_type = 'SINGLE'
    col.hide_render = False
    for c in escena.collection.children:
        if c != col:
            c.hide_render = True
    for nombre, pos, rot in (("frente", (0, -6, ALTURA / 2), (math.radians(90), 0, 0)),
                             ("perfil", (6, 0, ALTURA / 2), (math.radians(90), 0, math.radians(90)))):
        cam.location = pos; cam.rotation_euler = rot
        escena.render.filepath = os.path.join(out_dir, "anciano_%s.png" % nombre)
        bpy.ops.render.render(write_still=True)
    sys.exit(0)   # sin guardar: el render de control no debe quedar en el .blend

if "--save" in args:
    bpy.ops.wm.save_mainfile()
