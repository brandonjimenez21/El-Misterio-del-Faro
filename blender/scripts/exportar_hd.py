# Re-hornea una o varias colecciones con mas resolucion y mejor empaquetado, y re-exporta su FBX (materiales B_<objeto>).
# NO guarda el .blend.  Uso: blender -b el_misterio_del_faro.blend --python scripts/exportar_hd.py -- Faro_Cabana [Otra ...]
import bpy, os, sys
RUTA = os.path.join(os.path.dirname(os.path.abspath(bpy.data.filepath)), "scripts", "exportar_unity.py")
exec(compile(open(RUTA, encoding="utf-8").read().split("# ---------------------------------------------------------------- LUNA")[0], RUTA, "exec"))
bk.margin = 16
FIJOS = {"Muelle_Cubierta": 4096, "Muelle_Pilotes": 4096, "Muelle_Barandas": 2048, "Muelle_Cajas": 2048,
         "Muelle_Barriles": 2048, "Muelle_Amarre": 2048, "Muelle_Cartel": 2048}


def tam(o):
    if o.name in FIJOS:
        return FIJOS[o.name]
    md = max(o.dimensions)
    return 4096 if md > 15 else (2048 if md > 5 else (1024 if md > 1.0 else 512))


def unwrap2(obj):
    only(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    try:
        bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    except Exception:
        pass
    bpy.ops.object.mode_set(mode='OBJECT')


for nombre in sys.argv[sys.argv.index("--") + 1:]:
    col = bpy.data.collections[nombre]
    for o in [o for o in col.objects if o.type == 'MESH' and len(o.data.polygons) > 0]:
        mats = uniq_mats(o)
        if not mats:
            continue
        size = tam(o)
        unwrap2(o)
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
        print("HORNEADO", o.name, size, flush=True)
    bpy.ops.object.select_all(action='DESELECT')
    objs = list(col.objects)
    for o in objs:
        o.select_set(True)
    VL.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, nombre + ".fbx"), use_selection=True,
                             apply_scale_options='FBX_SCALE_ALL', bake_anim=True, add_leaf_bones=False,
                             object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=True)
    print("EXPORTADO", nombre, flush=True)
