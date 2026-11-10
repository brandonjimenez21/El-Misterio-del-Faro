# Optimiza y texturiza la isla ("IslandModel"):
#  1) reduce la malla (Decimate) comprobando cuanto se aleja de la original,
#  2) crea un material procedural realista (roca estratificada, hierba y musgo en lo llano,
#     arena humeda en la orilla, tierra) usando posicion/pendiente/altura del terreno,
#  3) lo hornea a 2 texturas (color 4096 y normal 2048) y deja un material ligero con solo esas 2 imagenes.
# Uso:  blender -b archivo.blend --python texturizar_isla.py
import bpy, bmesh, math, os, sys, time
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

S = bpy.context.scene
VL = bpy.context.view_layer
RUT = os.path.dirname(bpy.data.filepath)
TEX = os.path.join(RUT, "texturas")
os.makedirs(TEX, exist_ok=True)
SCRATCH = sys.argv[-1] if sys.argv[-1].endswith("scratchpad") else None
RATIO = 0.5                    # fraccion de triangulos que se conserva
RES_COLOR, RES_NORMAL = 4096, 2048

I = bpy.data.objects["IslandModel"]


def solo(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    VL.objects.active = o


# ------------------------------------------------------------------ 1) optimizar la malla (solo la primera vez)
t0 = time.time()
for mm in [x for x in bpy.data.materials if x.name.startswith("M_Isla")]:
    bpy.data.materials.remove(mm)
for im in [x for x in bpy.data.images if x.name.startswith("Isla_")]:
    bpy.data.images.remove(im)
tris0 = sum(len(p.vertices) - 2 for p in I.data.polygons)
YA_OPTIMIZADA = bool(I.get("optimizada"))
orig = I.copy()
orig.data = I.data.copy()
orig.name = "Isla_original_tmp"
S.collection.objects.link(orig)
bpy.context.view_layer.update()
solo(I)
mod = I.modifiers.new("Reducir", 'DECIMATE')
mod.decimate_type = 'COLLAPSE'
mod.ratio = 1.0 if YA_OPTIMIZADA else RATIO      # la reduccion se hace solo la primera vez
mod.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=mod.name)
I["optimizada"] = True
tris1 = sum(len(p.vertices) - 2 for p in I.data.polygons)

# desviacion de la malla reducida respecto a la original (en metros, ya con la escala)
dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(orig, dg)
mw = I.matrix_world
mwo = orig.matrix_world
dist = []
for v in list(I.data.vertices)[::4]:
    loc, nor, idx, d = bvh.find_nearest(mwo.inverted() @ (mw @ v.co))
    if loc is not None:
        dist.append((mwo @ loc - mw @ v.co).length)
dist.sort()
print("OPT triangulos", tris0, "->", tris1, "| desviacion media %.3f m, p99 %.3f m, max %.3f m" % (
    sum(dist) / len(dist), dist[int(len(dist) * .99)], dist[-1]))
bpy.data.objects.remove(orig, do_unlink=True)

# ------------------------------------------------------------------ 2) UV nuevas
solo(I)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
for uv in list(I.data.uv_layers):
    I.data.uv_layers.remove(uv)
I.data.uv_layers.new(name="UVMap")
bpy.ops.uv.smart_project(angle_limit=math.radians(70), island_margin=0.004)
bpy.ops.object.mode_set(mode='OBJECT')

# ------------------------------------------------------------------ 3) material procedural
m = bpy.data.materials.new("M_Isla_proc")
m.use_nodes = True
nt = m.node_tree
nt.nodes.clear()
N = nt.nodes.new
L = nt.links.new


def nd(t, x=0, y=0, **kw):
    n = N(t)
    n.location = (x, y)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def val(n, name, v):
    n.inputs[name].default_value = v
    return n


def rng(src, a, b, c=0.0, d=1.0, x=0, y=0):
    n = nd('ShaderNodeMapRange', x, y)
    n.clamp = True
    val(n, 'From Min', a)
    val(n, 'From Max', b)
    val(n, 'To Min', c)
    val(n, 'To Max', d)
    L(src, n.inputs['Value'])
    return n


geo = nd('ShaderNodeNewGeometry', -1400, 0)
sp = nd('ShaderNodeSeparateXYZ', -1200, 200)
sn = nd('ShaderNodeSeparateXYZ', -1200, -100)
L(geo.outputs['Position'], sp.inputs['Vector'])
L(geo.outputs['Normal'], sn.inputs['Vector'])
Z = sp.outputs['Z']
PEND = sn.outputs['Z']                       # 1 = suelo llano, 0 = pared vertical

# ruidos a varias escalas
n_gran = nd('ShaderNodeTexNoise', -1000, 600, noise_dimensions='3D')
val(n_gran, 'Scale', 0.045); val(n_gran, 'Detail', 6); val(n_gran, 'Roughness', 0.55)
n_med = nd('ShaderNodeTexNoise', -1000, 400, noise_dimensions='3D')
val(n_med, 'Scale', 0.5); val(n_med, 'Detail', 8); val(n_med, 'Roughness', 0.6)
n_fino = nd('ShaderNodeTexNoise', -1000, 200, noise_dimensions='3D')
val(n_fino, 'Scale', 5.0); val(n_fino, 'Detail', 10); val(n_fino, 'Roughness', 0.65)
vor = nd('ShaderNodeTexVoronoi', -1000, 0, voronoi_dimensions='3D', feature='DISTANCE_TO_EDGE')
val(vor, 'Scale', 0.22)
vor2 = nd('ShaderNodeTexVoronoi', -1000, -250, voronoi_dimensions='3D', feature='F1')
val(vor2, 'Scale', 1.3)
wav = nd('ShaderNodeTexWave', -1000, -500, wave_type='BANDS', bands_direction='Z')
val(wav, 'Scale', 0.55); val(wav, 'Distortion', 6); val(wav, 'Detail', 3)
for n in (n_gran, n_med, n_fino, vor, vor2, wav):
    L(geo.outputs['Position'], n.inputs['Vector'])

# --- roca: estratos + grietas + manchas
rampR = nd('ShaderNodeValToRGB', -750, 100)
rampR.color_ramp.elements[0].position = 0.0
rampR.color_ramp.elements[0].color = (0.055, 0.05, 0.045, 1)
rampR.color_ramp.elements[1].position = 1.0
rampR.color_ramp.elements[1].color = (0.30, 0.27, 0.23, 1)
mixh = nd('ShaderNodeMath', -900, -100, operation='ADD')
mixh.use_clamp = True
L(wav.outputs['Fac'], mixh.inputs[0])
L(n_med.outputs['Fac'], mixh.inputs[1])
mixh2 = nd('ShaderNodeMath', -800, -100, operation='MULTIPLY')
L(mixh.outputs[0], mixh2.inputs[0]); mixh2.inputs[1].default_value = 0.55
L(mixh2.outputs[0], rampR.inputs['Fac'])
crack = rng(vor.outputs['Distance'], 0.0, 0.07, 0.25, 1.0, -750, -150)       # oscurece las grietas
rock = nd('ShaderNodeMix', -550, 100, data_type='RGBA', blend_type='MULTIPLY')
val(rock, 'Factor', 1.0)
L(rampR.outputs['Color'], rock.inputs[6])
gc = nd('ShaderNodeCombineColor', -600, -150)
for k in ('Red', 'Green', 'Blue'):
    L(crack.outputs[0], gc.inputs[k])
L(gc.outputs[0], rock.inputs[7])

# --- hierba / musgo
ramG = nd('ShaderNodeValToRGB', -750, 450)
ramG.color_ramp.elements[0].color = (0.025, 0.055, 0.012, 1)
ramG.color_ramp.elements[1].color = (0.11, 0.13, 0.035, 1)
nm = nd('ShaderNodeMath', -850, 450, operation='MULTIPLY')
L(n_med.outputs['Fac'], nm.inputs[0]); L(n_fino.outputs['Fac'], nm.inputs[1])
nmx = nd('ShaderNodeMath', -800, 520, operation='ADD'); nmx.use_clamp = True
L(nm.outputs[0], nmx.inputs[0]); L(n_gran.outputs['Fac'], nmx.inputs[1])
L(nmx.outputs[0], ramG.inputs['Fac'])

# --- tierra seca (manchas)
dirt = nd('ShaderNodeRGB', -750, 300)
dirt.outputs[0].default_value = (0.085, 0.06, 0.038, 1)

# --- arena humeda en la orilla
ramS = nd('ShaderNodeValToRGB', -750, -400)
ramS.color_ramp.elements[0].color = (0.16, 0.135, 0.095, 1)
ramS.color_ramp.elements[1].color = (0.42, 0.37, 0.27, 1)
L(n_fino.outputs['Fac'], ramS.inputs['Fac'])

# mascaras
# hierba: llano, por encima de la orilla; el ruido rompe el borde
cx = nd('ShaderNodeMath', -500, 700, operation='ADD')
L(PEND, cx.inputs[0])
cxm = nd('ShaderNodeMath', -620, 740, operation='MULTIPLY'); cxm.inputs[1].default_value = 0.35
L(n_gran.outputs['Fac'], cxm.inputs[0])
L(cxm.outputs[0], cx.inputs[1])
mg = rng(cx.outputs[0], 0.86, 1.02, 0.0, 1.0, -380, 700)
zc = nd('ShaderNodeMath', -620, 800, operation='ADD')
L(Z, zc.inputs[0])
zn = nd('ShaderNodeMath', -740, 820, operation='MULTIPLY'); zn.inputs[1].default_value = 3.0
L(n_med.outputs['Fac'], zn.inputs[0])
L(zn.outputs[0], zc.inputs[1])
mz = rng(zc.outputs[0], 1.5, 3.2, 0.0, 1.0, -480, 820)
hier = nd('ShaderNodeMath', -250, 740, operation='MULTIPLY')
L(mg.outputs[0], hier.inputs[0]); L(mz.outputs[0], hier.inputs[1])
# tierra: parches dentro de la hierba
mdirt = rng(n_gran.outputs['Fac'], 0.58, 0.72, 0.0, 0.8, -380, 300)
# arena: baja y poco empinado
sz = nd('ShaderNodeMath', -620, -300, operation='ADD')
L(Z, sz.inputs[0])
szn = nd('ShaderNodeMath', -740, -330, operation='MULTIPLY'); szn.inputs[1].default_value = 1.2
L(n_med.outputs['Fac'], szn.inputs[0]); L(szn.outputs[0], sz.inputs[1])
ms = rng(sz.outputs[0], 2.8, 1.0, 0.0, 1.0, -480, -300)
ps = rng(PEND, 0.55, 0.85, 0.0, 1.0, -480, -380)
sand = nd('ShaderNodeMath', -250, -330, operation='MULTIPLY')
L(ms.outputs[0], sand.inputs[0]); L(ps.outputs[0], sand.inputs[1])

# mezcla: roca -> tierra -> hierba -> arena
c1 = nd('ShaderNodeMix', -150, 100, data_type='RGBA')
L(mdirt.outputs[0], c1.inputs[0]); L(rock.outputs[2], c1.inputs[6]); L(dirt.outputs[0], c1.inputs[7])
cdirt = nd('ShaderNodeMath', -250, 600, operation='MULTIPLY')
L(hier.outputs[0], cdirt.inputs[0]); cdirt.inputs[1].default_value = 1.0
c2 = nd('ShaderNodeMix', 40, 100, data_type='RGBA')
L(hier.outputs[0], c2.inputs[0]); L(c1.outputs[2], c2.inputs[6]); L(ramG.outputs['Color'], c2.inputs[7])
c3 = nd('ShaderNodeMix', 230, 100, data_type='RGBA')
L(sand.outputs[0], c3.inputs[0]); L(c2.outputs[2], c3.inputs[6]); L(ramS.outputs['Color'], c3.inputs[7])
# variacion de tono global suave
c4 = nd('ShaderNodeMix', 420, 100, data_type='RGBA', blend_type='OVERLAY')
val(c4, 'Factor', 0.35)
L(c3.outputs[2], c4.inputs[6])
gn = nd('ShaderNodeCombineColor', 300, -50)
for k in ('Red', 'Green', 'Blue'):
    L(n_gran.outputs['Fac'], gn.inputs[k])
L(gn.outputs[0], c4.inputs[7])
COLOR = c4.outputs[2]

# ------------------------------------------------------------------ caminos: mascara vista desde arriba
from mathutils import geometry as mgeo


def puntos_curva(o, paso=0.5):
    pts = []
    for sp in o.data.splines:
        if sp.type == 'BEZIER':
            bp = sp.bezier_points
            n = len(bp)
            for i in range(n - 1):
                seg = mgeo.interpolate_bezier(o.matrix_world @ bp[i].co, o.matrix_world @ bp[i].handle_right,
                                              o.matrix_world @ bp[i + 1].handle_left, o.matrix_world @ bp[i + 1].co, 24)
                pts += [(p.x, p.y) for p in seg]
        else:
            pts += [((o.matrix_world @ p.co.to_3d()).x, (o.matrix_world @ p.co.to_3d()).y) for p in sp.points]
    # remuestrear cada `paso` metros
    out = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= paso:
            out.append(p)
    return out


_b = [I.matrix_world @ Vector(c) for c in I.bound_box]
MX0, MX1 = min(v.x for v in _b) - 1.0, max(v.x for v in _b) + 1.0
MY0, MY1 = min(v.y for v in _b) - 1.0, max(v.y for v in _b) + 1.0
MW, MH = MX1 - MX0, MY1 - MY0
NX = 1600
NY = int(round(NX * MH / MW))
mask = np.zeros((NY, NX), dtype=np.float32)
px = MW / NX
xs_ = MX0 + (np.arange(NX) + 0.5) * px
ys_ = MY0 + (np.arange(NY) + 0.5) * (MH / NY)
col_c = bpy.data.collections.get("Caminos")
n_seg = 0
if col_c:
    for cu in col_c.objects:
        if cu.type != 'CURVE':
            continue
        hw = float(cu.get("ancho", 2.0)) / 2.0
        inten = float(cu.get("intensidad", 1.0))
        pts = puntos_curva(cu)
        for (x0_, y0_), (x1_, y1_) in zip(pts[:-1], pts[1:]):
            r = hw * 1.6
            i0 = max(0, int((min(x0_, x1_) - r - MX0) / px)); i1 = min(NX, int((max(x0_, x1_) + r - MX0) / px) + 1)
            j0 = max(0, int((min(y0_, y1_) - r - MY0) / (MH / NY))); j1 = min(NY, int((max(y0_, y1_) + r - MY0) / (MH / NY)) + 1)
            if i1 <= i0 or j1 <= j0:
                continue
            gx, gy = np.meshgrid(xs_[i0:i1], ys_[j0:j1])
            dx, dy = x1_ - x0_, y1_ - y0_
            L2 = dx * dx + dy * dy + 1e-9
            tt = np.clip(((gx - x0_) * dx + (gy - y0_) * dy) / L2, 0, 1)
            d = np.hypot(gx - (x0_ + tt * dx), gy - (y0_ + tt * dy))
            wob = (np.sin(0.7 * gx + 1.3) * np.sin(0.9 * gy + 0.4) * 0.5 + np.sin(2.1 * gx - 0.5 * gy) * 0.3 + np.sin(3.3 * gy + 1.1 * gx) * 0.2)
            d = d + 0.30 * hw * wob
            f = 1.0 - np.clip((d - hw * 0.55) / (hw * 0.6), 0, 1)
            f = f * f * (3 - 2 * f) * inten
            sub = mask[j0:j1, i0:i1]
            np.maximum(sub, f.astype(np.float32), out=sub)
            n_seg += 1
print("CAMINOS segmentos", n_seg, "mascara", NX, "x", NY, "cubre", round(float((mask > 0.5).mean() * 100), 1), "% de la caja")
img_m = bpy.data.images.new("Isla_caminos_tmp", NX, NY, alpha=False)
img_m.colorspace_settings.name = 'Non-Color'
rgba = np.empty((NY, NX, 4), dtype=np.float32)
rgba[..., 0] = rgba[..., 1] = rgba[..., 2] = mask
rgba[..., 3] = 1.0
img_m.pixels.foreach_set(rgba.ravel())
img_m.pack()

tex_m = nd('ShaderNodeTexImage', 700, 400)
tex_m.image = img_m
tex_m.interpolation = 'Linear'
tex_m.extension = 'EXTEND'
mu_ = nd('ShaderNodeMapRange', 500, 700); mu_.clamp = False
val(mu_, 'From Min', MX0); val(mu_, 'From Max', MX1); val(mu_, 'To Min', 0.0); val(mu_, 'To Max', 1.0)
mv_ = nd('ShaderNodeMapRange', 500, 800); mv_.clamp = False
val(mv_, 'From Min', MY0); val(mv_, 'From Max', MY1); val(mv_, 'To Min', 0.0); val(mv_, 'To Max', 1.0)
L(sp.outputs['X'], mu_.inputs['Value'])
L(sp.outputs['Y'], mv_.inputs['Value'])
cxy = nd('ShaderNodeCombineXYZ', 600, 750)
L(mu_.outputs[0], cxy.inputs['X'])
L(mv_.outputs[0], cxy.inputs['Y'])
L(cxy.outputs[0], tex_m.inputs['Vector'])
M_CAM = tex_m.outputs['Color']
mcam = nd('ShaderNodeSeparateColor', 800, 400)
L(M_CAM, mcam.inputs['Color'])
MASK = mcam.outputs['Red']

# color del camino: tierra apisonada con guijarros claros
pebble = nd('ShaderNodeTexVoronoi', 700, 150, voronoi_dimensions='3D', feature='F1')
val(pebble, 'Scale', 7.0)
L(geo.outputs['Position'], pebble.inputs['Vector'])
rampP = nd('ShaderNodeValToRGB', 900, 150)
rampP.color_ramp.elements[0].position = 0.15
rampP.color_ramp.elements[0].color = (0.42, 0.35, 0.26, 1)      # guijarros
rampP.color_ramp.elements[1].position = 0.55
rampP.color_ramp.elements[1].color = (0.20, 0.145, 0.095, 1)      # tierra
L(pebble.outputs['Distance'], rampP.inputs['Fac'])
rampV = nd('ShaderNodeMix', 1100, 150, data_type='RGBA', blend_type='MULTIPLY')
val(rampV, 'Factor', 0.7)
L(rampP.outputs['Color'], rampV.inputs[6])
gn2 = nd('ShaderNodeCombineColor', 1000, 0)
for k in ('Red', 'Green', 'Blue'):
    L(n_med.outputs['Fac'], gn2.inputs[k])
L(gn2.outputs[0], rampV.inputs[7])
cp = nd('ShaderNodeMix', 1250, 150, data_type='RGBA')
L(MASK, cp.inputs[0]); L(COLOR, cp.inputs[6]); L(rampV.outputs[2], cp.inputs[7])
COLOR = cp.outputs[2]

# relieve (bump): grietas de roca, grano fino y mullido en la hierba
hr = nd('ShaderNodeMath', 0, -450, operation='MULTIPLY'); hr.use_clamp = True
L(crack.outputs[0], hr.inputs[0]); hr.inputs[1].default_value = 1.0
h1 = nd('ShaderNodeMath', 150, -450, operation='ADD'); h1.use_clamp = True
L(hr.outputs[0], h1.inputs[0]); L(n_med.outputs['Fac'], h1.inputs[1])
h2 = nd('ShaderNodeMix', 300, -450, data_type='FLOAT')
L(hier.outputs[0], h2.inputs[0]); L(h1.outputs[0], h2.inputs[2]); L(n_fino.outputs['Fac'], h2.inputs[3])
bump = nd('ShaderNodeBump', 480, -450)
val(bump, 'Strength', 0.9); val(bump, 'Distance', 0.6)
h3 = nd('ShaderNodeMix', 400, -450, data_type='FLOAT')
L(MASK, h3.inputs[0]); L(h2.outputs[0], h3.inputs[2]); L(pebble.outputs['Distance'], h3.inputs[3])
L(h3.outputs[0], bump.inputs['Height'])

bsdf = nd('ShaderNodeBsdfPrincipled', 700, 0)
val(bsdf, 'Roughness', 0.9)
L(COLOR, bsdf.inputs['Base Color'])
L(bump.outputs['Normal'], bsdf.inputs['Normal'])
out = nd('ShaderNodeOutputMaterial', 950, 0)
L(bsdf.outputs['BSDF'], out.inputs['Surface'])

I.data.materials.clear()
I.data.materials.append(m)

# ------------------------------------------------------------------ 4) hornear
S.render.engine = 'CYCLES'
S.cycles.device = 'CPU'
S.cycles.samples = 1
S.cycles.use_denoising = False
bk = S.render.bake
bk.target = 'IMAGE_TEXTURES'
bk.use_clear = True
bk.margin = 16
bk.margin_type = 'EXTEND'
bk.normal_space = 'TANGENT'
bk.use_pass_direct = False
bk.use_pass_indirect = False
bk.use_selected_to_active = False


def hornear(kind, size, srgb, nombre):
    img = bpy.data.images.new(nombre, size, size, alpha=False)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    em = None
    if kind == 'color':
        em = nt.nodes.new('ShaderNodeEmission')
        L(COLOR, em.inputs['Color'])
        L(em.outputs[0], out.inputs['Surface'])
    imn = nt.nodes.new('ShaderNodeTexImage')
    imn.image = img
    nt.nodes.active = imn
    imn.select = True
    solo(I)
    bpy.ops.object.bake(type='EMIT' if kind == 'color' else 'NORMAL')
    nt.nodes.remove(imn)
    if em:
        nt.nodes.remove(em)
        L(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return img


t1 = time.time()
img_c = hornear('color', RES_COLOR, True, "Isla_c")
print("BAKE color", round(time.time() - t1), "s")
t1 = time.time()
img_n = hornear('normal', RES_NORMAL, False, "Isla_n")
print("BAKE normal", round(time.time() - t1), "s")

ruta_c = os.path.join(TEX, "Isla_c.jpg")
ruta_n = os.path.join(TEX, "Isla_n.png")
img_c.filepath_raw = ruta_c
img_c.file_format = 'JPEG'
S.render.image_settings.quality = 92
img_c.save()
img_n.filepath_raw = ruta_n
img_n.file_format = 'PNG'
img_n.save()

# ------------------------------------------------------------------ 5) material final ligero (3 imagenes pequenas)

def detalle_tileable(path, n=1024, seed=3):
    """ruido de grano fino que se repite sin costuras (espectro 1/f en FFT) para dar nitidez de cerca"""
    rng_ = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    r = np.sqrt(fx ** 2 + fy ** 2)
    r[0, 0] = 1.0
    sp = (rng_.normal(size=(n, n)) + 1j * rng_.normal(size=(n, n))) / (r ** 1.15)
    sp[0, 0] = 0
    a_ = np.real(np.fft.ifft2(sp))
    a_ = (a_ - a_.min()) / (a_.max() - a_.min())
    a_ = np.clip((a_ - 0.5) * 2.2 + 0.5, 0, 1)
    px = np.empty((n, n, 4), dtype=np.float32)
    px[..., 0] = px[..., 1] = px[..., 2] = a_
    px[..., 3] = 1.0
    im = bpy.data.images.new("Isla_detalle", n, n, alpha=False)
    im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = path
    im.file_format = 'PNG'
    im.save()
    return im


bpy.data.materials.remove(m)
ruta_d = os.path.join(TEX, "Isla_detalle.png")
img_d = detalle_tileable(ruta_d)
mf = bpy.data.materials.new("M_Isla")
mf.use_nodes = True
ft = mf.node_tree
ft.nodes.clear()
F = ft.nodes.new
FL = ft.links.new
b = F('ShaderNodeBsdfPrincipled')
b.inputs['Roughness'].default_value = 0.92
uv = F('ShaderNodeUVMap')
uv.uv_map = "UVMap"
mp_ = F('ShaderNodeMapping')
mp_.inputs['Scale'].default_value = (55.0, 55.0, 1.0)     # el detalle se repite ~55 veces sobre la isla
FL(uv.outputs['UV'], mp_.inputs['Vector'])
td = F('ShaderNodeTexImage')
td.image = img_d
td.extension = 'REPEAT'
FL(mp_.outputs['Vector'], td.inputs['Vector'])
tc = F('ShaderNodeTexImage')
tc.image = img_c
tn = F('ShaderNodeTexImage')
tn.image = img_n
nmap = F('ShaderNodeNormalMap')
mixc = F('ShaderNodeMix')
mixc.data_type = 'RGBA'
mixc.blend_type = 'OVERLAY'
mixc.inputs[0].default_value = 0.55
FL(tc.outputs['Color'], mixc.inputs[6])
FL(td.outputs['Color'], mixc.inputs[7])
FL(mixc.outputs[2], b.inputs['Base Color'])
FL(tn.outputs['Color'], nmap.inputs['Color'])
bmp = F('ShaderNodeBump')
bmp.inputs['Strength'].default_value = 0.35
bmp.inputs['Distance'].default_value = 0.05
FL(td.outputs['Color'], bmp.inputs['Height'])
FL(nmap.outputs['Normal'], bmp.inputs['Normal'])
FL(bmp.outputs['Normal'], b.inputs['Normal'])
o2 = F('ShaderNodeOutputMaterial')
FL(b.outputs['BSDF'], o2.inputs['Surface'])
I.data.materials.clear()
I.data.materials.append(mf)
for im, nombre in ((img_c, "Isla_c.jpg"), (img_n, "Isla_n.png"), (img_d, "Isla_detalle.png")):
    im.name = nombre
    im.filepath = "//texturas/" + nombre          # ruta relativa al .blend
    im.reload()
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 6) Luna: version ligera SOLO en el visor (el render y el horneado usan la completa)
luna = bpy.data.objects.get("Luna")
if luna and not any(md.type == 'DECIMATE' for md in luna.modifiers):
    md = luna.modifiers.new("Visor_ligero", 'DECIMATE')
    md.ratio = 0.12
    md.show_render = False
    md.show_viewport = True
    print("LUNA visor ligero: 12 %")

bpy.ops.object.select_all(action='DESELECT')
if SCRATCH:
    bpy.ops.wm.save_as_mainfile(filepath=SCRATCH + r"\faro_textura.blend", copy=True)
else:
    bpy.ops.wm.save_mainfile()
print("TEXTURA OK", round(time.time() - t0), "s")
