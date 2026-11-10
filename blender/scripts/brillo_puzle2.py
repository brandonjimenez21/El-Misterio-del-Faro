# Los postes de piedra, la placa, la estela y las rocas del sendero salian casi negros en Unity: su color horneado era
# demasiado oscuro (media 0.13-0.25) para una luna tan tenue. Este script
#   1) sube el brillo de su material en Blender (nodo Mezclar-Multiplicar antes del Base Color, ganancia segun lo oscuro que sea),
#   2) vuelve a hornear SOLO estos objetos (mismo procedimiento y mismas UV que exportar_unity.py),
#   3) re-exporta los FBX de sus colecciones (Puzle2_IslaAlterada y Puzle1_Muelle).
# Uso: blender -b el_misterio_del_faro.blend --python brillo_puzle2.py -- [--save]
# (--save guarda el material ya con la ganancia; el horneado no pisa los demas objetos)
import bpy, os, sys, math, traceback
import numpy as np

_S0 = bpy.context.scene
_ORIG = (_S0.render.engine, _S0.cycles.device, _S0.cycles.samples, _S0.cycles.use_denoising,
         _S0.render.bake.margin, _S0.render.bake.target, _S0.render.bake.use_clear)
RUTA_EXP = os.path.join(os.path.dirname(os.path.abspath(bpy.data.filepath)), "scripts", "exportar_unity.py")
fuente = open(RUTA_EXP, encoding="utf-8").read().split("# ---------------------------------------------------------------- LUNA")[0]
exec(compile(fuente, RUTA_EXP, "exec"))      # define S, VL, bk, only, new_img, uniq_mats, bake_pass, save_img, pack_mask, unwrap, size_for, plain_mat, TEX, OUT

OBJETOS = ["Poste_1_Reflejo_Base", "Poste_1_Reflejo_Cabeza", "Poste_2_Origen_Base", "Poste_2_Origen_Cabeza",
           "Poste_3_Fin_Base", "Poste_3_Fin_Cabeza", "Placa_Inscripcion", "Roca_Bloqueo_Sendero", "Roca_Normal", "Estela_Mareas"]
OBJETIVO = float(sys.argv[sys.argv.index("--objetivo") + 1]) if "--objetivo" in sys.argv else 0.30   # brillo medio (sRGB) deseado
# brillo medio (sRGB) de la textura de color ORIGINAL (medido antes de aplicar ninguna ganancia)
MEDIA_ORIGINAL = {"Poste_1_Reflejo_Base": 0.203, "Poste_1_Reflejo_Cabeza": 0.239, "Poste_2_Origen_Base": 0.203,
                  "Poste_2_Origen_Cabeza": 0.258, "Poste_3_Fin_Base": 0.205, "Poste_3_Fin_Cabeza": 0.247,
                  "Placa_Inscripcion": 0.128, "Roca_Bloqueo_Sendero": 0.147, "Roca_Normal": 0.21, "Estela_Mareas": 0.181}


def ganancia(obj, g):
    """multiplica el Base Color de los materiales del objeto por g (en lineal). Los materiales se hacen unicos por objeto
    (varios objetos comparten material y la ganancia se acumularia)."""
    for slot in obj.material_slots:
        if slot.material is None:
            continue
        base = slot.material.name.split("__")[0]
        slot.material = slot.material.copy()
        slot.material.name = base + "__" + obj.name
        nt = slot.material.node_tree
        for n in [n for n in nt.nodes if n.name.startswith("GananciaBrillo")]:      # limpiar ganancias previas
            src = n.inputs[6].links[0].from_socket if n.inputs[6].is_linked else None
            for d in [l.to_socket for l in n.outputs[2].links]:
                if src is not None:
                    nt.links.new(src, d)
                else:
                    d.default_value = n.inputs[6].default_value
            nt.nodes.remove(n)
        for n in list(nt.nodes):
            if n.type != 'BSDF_PRINCIPLED':
                continue
            sock = n.inputs["Base Color"]
            mix = nt.nodes.new('ShaderNodeMix')
            mix.name = "GananciaBrillo"
            mix.data_type = 'RGBA'
            mix.blend_type = 'MULTIPLY'
            mix.inputs[0].default_value = 1.0
            mix.inputs[7].default_value = (g, g, g, 1.0)
            mix.location = (n.location.x - 220, n.location.y + 200)
            if sock.is_linked:
                nt.links.new(sock.links[0].from_socket, mix.inputs[6])
            else:
                mix.inputs[6].default_value = sock.default_value
            nt.links.new(mix.outputs[2], sock)


O = bpy.data.objects
hechos = []
for nombre in OBJETOS:
    o = O.get(nombre)
    if o is None or o.type != 'MESH':
        print("BRILLO falta", nombre)
        continue
    mu = MEDIA_ORIGINAL[nombre]
    g = min(max(1.0, (OBJETIVO / mu) ** 2.2), 8.0)
    ganancia(o, g)
    hechos.append(o)
    print("BRILLO", nombre, "media", mu, "ganancia", round(g, 2))

if "--save" in sys.argv:
    _S0.render.engine, _S0.cycles.device, _S0.cycles.samples, _S0.cycles.use_denoising = _ORIG[:4]   # no dejar los ajustes del horneado
    _S0.render.bake.margin, _S0.render.bake.target, _S0.render.bake.use_clear = _ORIG[4:]
    bpy.ops.wm.save_mainfile()               # guarda los materiales con ganancia (antes de sustituirlos por los planos)

# ---------------------------------------------------------------- re-hornear solo estos (misma UV determinista que exportar_unity)
colecciones = {}
for o in hechos:
    for c in o.users_collection:
        colecciones.setdefault(c.name, c)
for n, o in enumerate(hechos):
    try:
        mats = uniq_mats(o)
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
        print("HORNEADO", o.name, size)
    except Exception:
        print("HORNEADO FALLO", o.name, traceback.format_exc())

# los demas objetos de esas colecciones solo necesitan material plano B_<nombre> y sus UV deterministas
for cname, c in colecciones.items():
    for o in c.objects:
        if o.type != 'MESH' or o in hechos or len(o.data.polygons) == 0:
            continue
        unwrap(o)
        o.data.materials.clear()
        o.data.materials.append(plain_mat(o.name))
    objs = list(c.objects)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    VL.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, cname + ".fbx"), use_selection=True,
                             apply_scale_options='FBX_SCALE_ALL', bake_anim=True, add_leaf_bones=False,
                             object_types={'EMPTY', 'MESH'}, path_mode='STRIP', use_tspace=True)
    print("FBX REEXPORTADO", cname, len(objs))
