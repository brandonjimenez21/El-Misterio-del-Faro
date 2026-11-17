# Horneado comun (color, normal, metal/rugosidad) y exportacion FBX con materiales B_<objeto>, sobre las utilidades de
# exportar_unity.py. Lo usan exportar_vikingo.py y piedras_puzle2.py.
import bpy, os, math, time

_RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exportar_unity.py")
exec(compile(open(_RUTA, encoding="utf-8").read().split("# ---------------------------------------------------------------- LUNA")[0], _RUTA, "exec"))
bk.margin = 16          # margen ancho alrededor de cada isla de UV: los mipmaps lejanos no se manchan de negro


def desplegar_hd(obj):
    """UV nuevas bien empaquetadas (hay que re-exportar el FBX)"""
    only(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    try:
        bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    except Exception:
        pass
    bpy.ops.object.mode_set(mode='OBJECT')


def hornear(o, size, modo='hd'):
    """modo 'hd' = UV nuevas; 'unity' = las mismas UV deterministas de exportar_unity.py (no hace falta re-exportar el FBX)"""
    t0 = time.time()
    mats = uniq_mats(o)
    if not mats:
        return False
    if len(o.data.uv_layers) == 0:
        o.data.uv_layers.new(name="UVMap")
    (desplegar_hd if modo == 'hd' else unwrap)(o)
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
    print("HORNEADO", o.name, size, "%.0f s" % (time.time() - t0), flush=True)
    return True


def exportar_fbx(nombre, objs, anim=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    VL.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, nombre + ".fbx"), use_selection=True,
                             apply_scale_options='FBX_SCALE_ALL', bake_anim=anim, add_leaf_bones=False,
                             object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=True, colors_type='NONE')
    print("EXPORTADO", nombre, len(objs), flush=True)
