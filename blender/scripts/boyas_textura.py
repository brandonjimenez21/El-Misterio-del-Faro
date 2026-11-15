# Boyas con textura: material procedural (pintura descascarillada, oxido, banda de color, suciedad y algas en la parte baja),
# UV (todas las boyas tienen la misma malla) y horneado de color + normal a Assets/Textures/T_Boya_{Roja,Blanca}_{c,n}.png.
# Despues: exportar_atrezzo.py para el FBX y asignar las texturas a M_Atrezzo_BoyaRoja / M_Atrezzo_BoyaBlanca en Unity.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/boyas_textura.py -- --save
import bpy, os, sys, math
RUTA = os.path.join(os.path.dirname(os.path.abspath(bpy.data.filepath)), "scripts", "exportar_unity.py")
exec(compile(open(RUTA, encoding="utf-8").read().split("# ---------------------------------------------------------------- LUNA")[0], RUTA, "exec"))
TEXD = os.path.join(RAIZ, "Assets", "Textures")
TAM = 1024


def procedural(nombre, base, banda):
    m = bpy.data.materials[nombre]
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    N, L = nt.nodes, nt.links
    sal = N.new('ShaderNodeOutputMaterial')
    bsdf = N.new('ShaderNodeBsdfPrincipled')
    L.new(bsdf.outputs['BSDF'], sal.inputs['Surface'])
    tc = N.new('ShaderNodeTexCoord')
    sep = N.new('ShaderNodeSeparateXYZ')
    L.new(tc.outputs['Object'], sep.inputs['Vector'])

    def ruido(esc, det=8.0, rug=0.55, desp=0.0):
        n = N.new('ShaderNodeTexNoise')
        n.inputs['Scale'].default_value = esc
        n.inputs['Detail'].default_value = det
        n.inputs['Roughness'].default_value = rug
        if desp:
            mp = N.new('ShaderNodeMapping')
            mp.inputs['Location'].default_value = (desp, desp * 0.7, desp * 1.3)
            L.new(tc.outputs['Object'], mp.inputs['Vector'])
            L.new(mp.outputs['Vector'], n.inputs['Vector'])
        else:
            L.new(tc.outputs['Object'], n.inputs['Vector'])
        return n.outputs['Fac']

    def rampa(fac, a, b, ca=(0, 0, 0, 1), cb=(1, 1, 1, 1)):
        r = N.new('ShaderNodeValToRGB')
        r.color_ramp.elements[0].position = a
        r.color_ramp.elements[0].color = ca
        r.color_ramp.elements[1].position = b
        r.color_ramp.elements[1].color = cb
        L.new(fac, r.inputs['Fac'])
        return r.outputs['Color']

    def mezcla(fac, a, b):
        x = N.new('ShaderNodeMix')
        x.data_type = 'RGBA'
        x.inputs[0].default_value = 1.0
        if isinstance(fac, (int, float)):
            x.inputs[0].default_value = fac
        else:
            L.new(fac, x.inputs[0])
        for idx, v in ((6, a), (7, b)):
            if isinstance(v, tuple):
                x.inputs[idx].default_value = v
            else:
                L.new(v, x.inputs[idx])
        return x.outputs[2]

    def mates(op, a, b=None):
        x = N.new('ShaderNodeMath')
        x.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                x.inputs[i].default_value = v
            else:
                L.new(v, x.inputs[i])
        return x.outputs[0]

    z = sep.outputs['Z']
    gran = ruido(7.0)                                           # desgaste a gran escala
    fino = ruido(55.0, 4.0)                                     # picaduras y raspones
    chip = rampa(mates('ADD', mates('MULTIPLY', gran, 0.6), mates('MULTIPLY', fino, 0.5)), 0.62, 0.76)    # 1 = pintura saltada
    # banda de color (franja alrededor del ecuador, con borde irregular)
    zb = mates('ADD', z, mates('MULTIPLY', ruido(30.0, 2.0), 0.05))
    b1 = rampa(zb, 0.15, 0.17)
    b2 = rampa(zb, 0.33, 0.31)
    banda_m = mates('MULTIPLY', b1, b2)
    # suciedad / algas en la parte baja y chorreras
    baja = rampa(mates('ADD', z, mates('MULTIPLY', ruido(9.0, 6.0), 0.35)), 0.30, -0.05)
    alga = rampa(ruido(14.0, 6.0, 0.6, 3.0), 0.45, 0.62)
    pintura = mezcla(banda_m, base, banda)
    pintura = mezcla(mates('MULTIPLY', baja, 0.55), pintura, (0.035, 0.05, 0.03, 1))
    pintura = mezcla(mates('MULTIPLY', alga, mates('MULTIPLY', baja, 0.9)), pintura, (0.02, 0.06, 0.025, 1))
    oxido_t = rampa(ruido(20.0, 5.0, 0.6, 7.0), 0.3, 0.75, (0.1, 0.035, 0.02, 1), (0.28, 0.11, 0.05, 1))
    col = mezcla(chip, pintura, oxido_t)
    # el vastago y la anilla de arriba (z > 0.5) son de hierro oxidado
    herr = rampa(z, 0.47, 0.5)
    col = mezcla(herr, col, oxido_t)
    L.new(col, bsdf.inputs['Base Color'])
    rug = mezcla(chip, (0.4, 0.4, 0.4, 1), (0.85, 0.85, 0.85, 1))
    r2 = N.new('ShaderNodeRGBToBW')
    L.new(rug, r2.inputs['Color'])
    L.new(r2.outputs[0], bsdf.inputs['Roughness'])
    bump = N.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.6
    bump.inputs['Distance'].default_value = 0.01
    L.new(mates('ADD', mates('MULTIPLY', fino, 0.6), mates('MULTIPLY', chip, 0.8)), bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return m


roja = procedural("M_Atrezzo_BoyaRoja", (0.38, 0.05, 0.04, 1), (0.6, 0.58, 0.52, 1))
blanca = procedural("M_Atrezzo_BoyaBlanca", (0.62, 0.62, 0.57, 1), (0.38, 0.05, 0.04, 1))

grupos = {"Roja": ["Boya_1", "Boya_3", "Boya_Muelle_1"], "Blanca": ["Boya_2", "Boya_Muelle_2"]}
for tipo, nombres in grupos.items():
    objs = [bpy.data.objects[n] for n in nombres]
    for o in objs:
        unwrap(o)
    o = objs[0]
    mats = uniq_mats(o)
    for kind in ('color', 'normal'):
        img = new_img("boya_%s_%s" % (tipo, kind), TAM, kind == 'color')
        only(o)
        bake_pass(kind, img, mats)
        save_img(img, os.path.join(TEXD, "T_Boya_%s_%s.png" % (tipo, "c" if kind == 'color' else "n")))
        bpy.data.images.remove(img)
    print("BOYA HORNEADA", tipo)
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
