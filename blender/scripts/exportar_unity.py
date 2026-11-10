# Hornea texturas y exporta los FBX para Unity (muelle, puzles, faro y cabana, isla).
# Uso: blender -b el_misterio_del_faro.blend --python exportar_unity.py   (NO guarda el .blend)
import bpy, math, os, sys, time, traceback, shutil, tempfile
import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath)))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro")
TEX = os.path.join(OUT, "Tex")
os.makedirs(TEX, exist_ok=True)
LOG = open(os.path.join(tempfile.gettempdir(), "exportar_unity_log.txt"), "w", buffering=1)


def log(*a):
    LOG.write(" ".join(str(x) for x in a) + "\n")


S = bpy.context.scene
VL = bpy.context.view_layer
S.render.engine = 'CYCLES'
S.cycles.device = 'CPU'
S.cycles.samples = 1
S.cycles.use_denoising = False
bk = S.render.bake
bk.target = 'IMAGE_TEXTURES'
bk.use_clear = True
bk.margin = 8
try:
    bk.margin_type = 'EXTEND'
except Exception:
    pass
bk.normal_space = 'TANGENT'
bk.use_pass_direct = False
bk.use_pass_indirect = False


def only(*objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    VL.objects.active = objs[-1]


def new_img(name, size, srgb):
    img = bpy.data.images.new(name, size, size, alpha=False)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    return img


def uniq_mats(obj):
    out = []
    for m in obj.data.materials:
        if m and m not in out and m.node_tree:
            out.append(m)
    return out


def bake_pass(kind, img, mats, extra_img_mats=None):
    state = []
    for m in mats:
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        added = []
        if kind in ('color', 'metal', 'rough') and b:
            em = nt.nodes.new('ShaderNodeEmission')
            added.append(em)
            sock = b.inputs[{'color': 'Base Color', 'metal': 'Metallic', 'rough': 'Roughness'}[kind]]
            if sock.links:
                nt.links.new(sock.links[0].from_socket, em.inputs['Color'])
            else:
                v = sock.default_value
                em.inputs['Color'].default_value = tuple(v) if hasattr(v, '__len__') else (v, v, v, 1)
            nt.links.new(em.outputs[0], out.inputs['Surface'])
        state.append((nt, out, b, added))
    for m in (extra_img_mats if extra_img_mats is not None else mats):
        nt = m.node_tree
        imn = nt.nodes.new('ShaderNodeTexImage')
        imn.image = img
        nt.nodes.active = imn
        imn.select = True
        state.append((nt, None, None, [imn]))
    bpy.ops.object.bake(type='NORMAL' if kind == 'normal' else 'EMIT')
    for nt, out, b, added in state:
        for n in added:
            nt.nodes.remove(n)
        if b and out:
            nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])


def save_img(img, path):
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()


def pack_mask(metal, rough, size, path):
    m = np.empty(size * size * 4, dtype=np.float32)
    r = np.empty(size * size * 4, dtype=np.float32)
    metal.pixels.foreach_get(m)
    rough.pixels.foreach_get(r)
    m = m.reshape(-1, 4)
    r = r.reshape(-1, 4)
    out = np.zeros_like(m)
    out[:, 0] = m[:, 0]
    out[:, 3] = 1.0 - r[:, 0]
    out[:, 3] = np.clip(out[:, 3], 0, 1)
    img = bpy.data.images.new("mask_tmp", size, size, alpha=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(out.ravel())
    img.alpha_mode = 'CHANNEL_PACKED'
    save_img(img, path)
    bpy.data.images.remove(img)


def unwrap(obj):
    only(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.012)
    bpy.ops.object.mode_set(mode='OBJECT')


def size_for(obj):
    md = max(obj.dimensions)
    return 2048 if md > 6 else (1024 if md > 1.2 else 512)


def plain_mat(name):
    m = bpy.data.materials.new("B_" + name)
    m.use_nodes = True
    m.diffuse_color = (0.5, 0.5, 0.5, 1)
    return m


# ---------------------------------------------------------------- LUNA (alta -> baja)
def bake_moon():
    high = bpy.data.objects["Luna"]
    loc = high.location.copy()
    coll = high.users_collection[0]
    high.name = "Luna_high"
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0, location=loc)
    low = bpy.context.active_object
    low.name = "Luna"
    low.scale = high.scale
    low.rotation_euler = high.rotation_euler
    bpy.ops.object.shade_smooth()
    for uc in list(low.users_collection):
        uc.objects.unlink(low)
    coll.objects.link(low)
    size = 2048
    tmp = bpy.data.materials.new("tmp_luna")
    tmp.use_nodes = True
    low.data.materials.append(tmp)
    bk.use_selected_to_active = True
    bk.cage_extrusion = 0.15 * max(high.scale)
    bk.max_ray_distance = 0.0
    hm = uniq_mats(high)
    imgs = {}
    for kind in ('color', 'normal'):
        img = new_img("Luna_" + kind, size, kind == 'color')
        only(high, low)
        bake_pass(kind, img, hm, extra_img_mats=[tmp])
        imgs[kind] = img
        save_img(img, os.path.join(TEX, "Luna_%s.png" % ('c' if kind == 'color' else 'n')))
    # mascara constante (rugosa, no metalica)
    mask = np.zeros((size * size, 4), dtype=np.float32)
    mask[:, 3] = 0.05
    mi = bpy.data.images.new("mask_tmp", size, size, alpha=True)
    mi.colorspace_settings.name = 'Non-Color'
    mi.pixels.foreach_set(mask.ravel())
    save_img(mi, os.path.join(TEX, "Luna_m.png"))
    bpy.data.images.remove(mi)
    bk.use_selected_to_active = False
    bpy.data.objects.remove(high)
    low.data.materials.clear()
    low.data.materials.append(plain_mat("Luna"))
    for i in imgs.values():
        bpy.data.images.remove(i)
    log("MOON OK")


t0 = time.time()
try:
    bake_moon()
except Exception:
    log("MOON FAIL", traceback.format_exc())

# ---------------------------------------------------------------- resto de objetos
COLS = ("Puzle", "Escenario", "Faro_Cabana")
objs = [o for c in bpy.data.collections if c.name.startswith(COLS) for o in c.objects
        if o.type == 'MESH' and o.name != "Luna" and len(o.data.polygons) > 0]
log("TOTAL", len(objs))
for n, o in enumerate(objs):
    try:
        t1 = time.time()
        mats = uniq_mats(o)
        if not mats:
            log("SKIP", o.name)
            continue
        size = size_for(o)
        unwrap(o)
        res = {}
        for kind in ('color', 'normal', 'metal', 'rough'):
            img = new_img("%s_%s" % (o.name, kind), size, kind == 'color')
            only(o)
            bake_pass(kind, img, mats)
            res[kind] = img
        save_img(res['color'], os.path.join(TEX, o.name + "_c.png"))
        save_img(res['normal'], os.path.join(TEX, o.name + "_n.png"))
        pack_mask(res['metal'], res['rough'], size, os.path.join(TEX, o.name + "_m.png"))
        for i in res.values():
            bpy.data.images.remove(i)
        o.data.materials.clear()
        o.data.materials.append(plain_mat(o.name))
        log("OK", n, o.name, size, round(time.time() - t1, 1), "s")
    except Exception:
        log("FAIL", o.name, traceback.format_exc())

# ---------------------------------------------------------------- exportar FBX (materiales B_<objeto>)
def exportar(nombre, objetos):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objetos:
        o.select_set(True)
    VL.objects.active = objetos[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, nombre + ".fbx"), use_selection=True,
                             apply_scale_options='FBX_SCALE_ALL', bake_anim=True, add_leaf_bones=False,
                             object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=True)
    log("EXPORTED", nombre, len(objetos))


for c in bpy.data.collections:
    if c.name.startswith(COLS):
        exportar(c.name, list(c.objects))

# isla: usa las texturas ya horneadas en blender/texturas (color 4096, normal 2048, detalle repetible)
isla = bpy.data.objects["IslandModel"]
isla.data.materials.clear()
isla.data.materials.append(plain_mat("IslandModel"))
for f in ("Isla_c.jpg", "Isla_n.png", "Isla_detalle.png"):
    shutil.copyfile(os.path.join(os.path.dirname(bpy.data.filepath), "texturas", f), os.path.join(TEX, f))
exportar("Isla", [isla])
log("DONE", round(time.time() - t0), "s")
