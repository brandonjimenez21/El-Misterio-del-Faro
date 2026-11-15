# Envejecido del resto del muelle (postes y pilotes torcidos) y de la torre / cabana / metales (capas de desgaste en los
# materiales procedurales de texturizar_faro.py: desconchado, chorretones de oxido y suciedad, sal, musgo, tejas rotas...).
# Uso: blender -b el_misterio_del_faro.blend --python scripts/envejecer_estructuras.py -- --save
# Idempotente: la geometria se marca con 'envejecido2' y los materiales con un nodo "Desgaste_Fin".
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Matrix

RUTA = os.path.join(os.path.dirname(os.path.abspath(bpy.data.filepath)), "scripts", "texturizar_faro.py")
exec(compile(open(RUTA, encoding="utf-8").read().split("# ------------------------------------------------------------------ materiales")[0], RUTA, "exec"))

rnd = random.Random(1887)


# ------------------------------------------------------------------ geometria del muelle
def componentes(bm):
    visto, out = set(), []
    for v in bm.verts:
        if v.index in visto:
            continue
        pila, vs = [v], []
        visto.add(v.index)
        while pila:
            x = pila.pop()
            vs.append(x)
            for e in x.link_edges:
                w = e.other_vert(x)
                if w.index not in visto:
                    visto.add(w.index)
                    pila.append(w)
        out.append(vs)
    return out


def caja(vs):
    xs = [v.co.x for v in vs]; ys = [v.co.y for v in vs]; zs = [v.co.z for v in vs]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def girar(vs, pivote, eje, ang):
    R = Matrix.Rotation(ang, 3, eje)
    for v in vs:
        v.co = pivote + R @ (v.co - pivote)


def torcer_postes():
    o = bpy.data.objects["Muelle_Barandas"]
    if o.get("envejecido2"):
        return
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    n = 0
    for vs in componentes(bm):
        lo, hi = caja(vs)
        d = hi - lo
        if len(vs) == 8 and d.z > 0.8 and d.x < 0.4 and d.y < 0.4:       # poste vertical
            pie = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
            a = rnd.uniform(0, 2 * math.pi)
            eje = Vector((math.cos(a), math.sin(a), 0))
            girar(vs, pie, eje, math.radians(rnd.gauss(0, 2.2)))
            # cabeza astillada en algunos: una esquina de arriba mas baja
            if rnd.random() < 0.35:
                arriba = sorted(vs, key=lambda v: -v.co.z)[:4]
                rnd.choice(arriba).co.z -= rnd.uniform(0.03, 0.09)
            n += 1
    bm.to_mesh(o.data); bm.free(); o.data.update()
    o["envejecido2"] = 1
    print("POSTES", n)


def torcer_pilotes():
    o = bpy.data.objects["Muelle_Pilotes"]
    if o.get("envejecido2"):
        return
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    comps = componentes(bm)
    info = [(vs,) + caja(vs) for vs in comps]
    pilotes = [(vs, lo, hi) for vs, lo, hi in info if (hi.z - lo.z) > 1.8 and (hi.x - lo.x) < 0.6 and (hi.y - lo.y) < 0.6]
    resto = [(vs, lo, hi) for vs, lo, hi in info if (hi.z - lo.z) <= 1.8 or (hi.x - lo.x) >= 0.6 or (hi.y - lo.y) >= 0.6]
    usados = set()
    for vs, lo, hi in pilotes:
        c = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2))
        tope = Vector((c.x, c.y, hi.z))
        a = rnd.uniform(0, 2 * math.pi)
        eje = Vector((math.cos(a), math.sin(a), 0))
        ang = math.radians(rnd.gauss(0, 1.8))
        grupo = list(vs)
        # lo que va pegado al pilote (musgo, percebes) se mueve con el
        for i, (vs2, lo2, hi2) in enumerate(resto):
            if i in usados:
                continue
            c2 = Vector(((lo2.x + hi2.x) / 2, (lo2.y + hi2.y) / 2))
            if (c2 - c).length < 0.4 and lo2.z >= lo.z - 0.2 and hi2.z <= hi.z + 0.2:
                grupo += vs2
                usados.add(i)
        girar(grupo, tope, eje, ang)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    o["envejecido2"] = 1
    print("PILOTES", len(pilotes), "pegados", len(usados))


torcer_postes()
torcer_pilotes()


# ------------------------------------------------------------------ capas de desgaste en los materiales
def base_y_normal(nt):
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    col = b.inputs['Base Color'].links[0].from_socket
    nrm = b.inputs['Normal'].links[0].from_socket if b.inputs['Normal'].links else None
    return b, col, nrm


def bump_encima(k, altura, nrm, fuerza, dist):
    bb = k.n('ShaderNodeBump')
    bb.inputs['Strength'].default_value = fuerza
    bb.inputs['Distance'].default_value = dist
    k.l(altura, bb.inputs['Height'])
    if nrm is not None:
        k.l(nrm, bb.inputs['Normal'])
    return bb.outputs['Normal']


def umbral(k, v, a, b):
    """smoothstep aproximado: (v-a)/(b-a) recortado"""
    return k.mat_('MULTIPLY', k.mat_('SUBTRACT', v, a, True), 1.0 / (b - a), True)


def rampa_z(k, z, z0, z1, v0, v1):
    mr = k.n('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = z0
    mr.inputs['From Max'].default_value = z1
    mr.inputs['To Min'].default_value = v0
    mr.inputs['To Max'].default_value = v1
    mr.clamp = True
    k.l(z, mr.inputs['Value'])
    return mr.outputs[0]


def azar_bloque(k, vec, ancho, alto, desfase):
    """valor aleatorio 0..1 por bloque (misma reticula que el ladrillo del material)"""
    c, _ = k.ladrillo(vec, (0, 0, 0), (1, 1, 1), (0, 0, 0), ancho, alto, desfase, 0.0)
    s = k.n('ShaderNodeSeparateColor')
    k.l(c, s.inputs[0])
    return s.outputs[0]


def marcar(k, sock, b):
    k.l(sock, b.inputs['Base Color'])
    k.nt.nodes[-1].name = "Desgaste_Fin"


def ya(m):
    return m.node_tree.nodes.get("Desgaste_Fin") is not None


def desgaste_torre(m):
    nt = m.node_tree; k = K(nt)
    b, col, nrm = base_y_normal(nt)
    x, y, z = k.xyz(k.pos())
    ang = k.mat_('ARCTAN2', k.mat_('SUBTRACT', y, TC[1]), k.mat_('SUBTRACT', x, TC[0]))
    u = k.mat_('MULTIPLY', ang, 7.0)
    vec = k.comb(u, z)
    # cada sillar con su tono
    r = azar_bloque(k, vec, 1.15, 0.55, 0.5)
    col = k.mix(col, k.rampa(r, (0.78, 0.76, 0.73), (1.12, 1.10, 1.06)), 1.0, 'MULTIPLY')
    # encalado desconchado: placas donde se ve la piedra oscura de debajo
    pel = k.noise(k.comb(k.mat_('MULTIPLY', u, 0.9), k.mat_('MULTIPLY', z, 0.9), 3.0), 1.6, 9.0, 0.65)
    zona = k.noise(k.comb(k.mat_('MULTIPLY', u, 0.12), k.mat_('MULTIPLY', z, 0.10), 6.0), 1.0, 3.0, 0.5)   # solo en algunas zonas grandes
    mpel = k.mat_('MULTIPLY', umbral(k, pel, 0.50, 0.54), umbral(k, zona, 0.52, 0.60), True)
    col = k.mix(col, k.mix(col, (0.36, 0.32, 0.28), 1.0, 'MULTIPLY'), mpel)
    # chorretones verticales (oxido y suciedad que bajan de la galeria y de las ventanas)
    est = k.noise(k.comb(k.mat_('MULTIPLY', u, 2.6), k.mat_('MULTIPLY', z, 0.05), 0.0), 1.0, 5.0, 0.55)
    var = k.noise(k.comb(k.mat_('MULTIPLY', u, 0.5), k.mat_('MULTIPLY', z, 0.25), 9.0), 1.0, 3.0, 0.5)
    mest = k.mat_('MULTIPLY', k.mat_('MULTIPLY', umbral(k, est, 0.48, 0.62), umbral(k, var, 0.35, 0.55)), rampa_z(k, z, 12.0, 47.0, 0.4, 1.0), True)
    col = k.mix(col, (0.22, 0.13, 0.075), k.mat_('MULTIPLY', mest, 0.9), 'MULTIPLY')
    # sal / salitre blanco en la base
    sal = k.noise(k.comb(k.mat_('MULTIPLY', u, 2.5), k.mat_('MULTIPLY', z, 2.5), 5.0), 1.0, 7.0, 0.6)
    msal = k.mat_('MULTIPLY', umbral(k, sal, 0.5, 0.62), rampa_z(k, z, 7.4, 10.5, 0.85, 0.0), True)
    col = k.mix(col, (0.62, 0.62, 0.58), msal)
    marcar(k, col, b)
    k.l(bump_encima(k, k.mat_('ADD', mpel, k.mat_('MULTIPLY', sal, 0.2)), nrm, 0.5, 0.02), b.inputs['Normal'])


def desgaste_madera_cabana(m, tablas=True):
    nt = m.node_tree; k = K(nt)
    b, col, nrm = base_y_normal(nt)
    x, y, z = k.xyz(k.pos())
    uw = k.mat_('ADD', x, y)
    # madera curtida: tira al gris plateado a manchas
    gris = k.noise(k.comb(k.mat_('MULTIPLY', uw, 0.6), k.mat_('MULTIPLY', z, 0.4), 2.0), 1.0, 6.0, 0.6)
    col = k.mix(col, (0.20, 0.18, 0.16), k.mat_('MULTIPLY', umbral(k, gris, 0.45, 0.7), 0.45))
    # chorretones oscuros desde el alero
    est = k.noise(k.comb(k.mat_('MULTIPLY', uw, 4.0), k.mat_('MULTIPLY', z, 0.08), 0.0), 1.0, 5.0, 0.55)
    col = k.mix(col, (0.25, 0.22, 0.19), k.mat_('MULTIPLY', umbral(k, est, 0.48, 0.64), 0.9), 'MULTIPLY')
    # humedad y podredumbre abajo (salpicaduras de lluvia) y musgo pegado al suelo
    bord = k.noise(k.comb(k.mat_('MULTIPLY', uw, 3.0), k.mat_('MULTIPLY', z, 3.0), 4.0), 1.0, 6.0, 0.6)
    hum = k.mat_('MULTIPLY', rampa_z(k, z, 7.3, 9.6, 1.0, 0.0), k.mat_('ADD', 0.6, k.mat_('MULTIPLY', bord, 0.8)), True)
    col = k.mix(col, (0.38, 0.36, 0.33), hum, 'MULTIPLY')
    musgo = k.mat_('MULTIPLY', rampa_z(k, z, 7.3, 8.3, 1.0, 0.0), umbral(k, bord, 0.42, 0.55), True)
    col = k.mix(col, (0.06, 0.09, 0.04), musgo)
    marcar(k, col, b)
    if tablas:
        k.l(bump_encima(k, k.mat_('ADD', k.mat_('MULTIPLY', gris, 0.5), musgo), nrm, 0.4, 0.02), b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.9


def desgaste_teja(m):
    nt = m.node_tree; k = K(nt)
    b, col, nrm = base_y_normal(nt)
    x, y, z = k.xyz(k.pos())
    r = azar_bloque(k, k.comb(x, y), 0.36, 0.42, 0.5)
    # tejas sueltas mas claras / mas oscuras y algunas que faltan (hueco negro)
    col = k.mix(col, k.rampa(r, (0.7, 0.68, 0.66), (1.15, 1.1, 1.05)), 1.0, 'MULTIPLY')
    falta = umbral(k, r, 0.93, 0.94)
    # liquen amarillento en manchas pequenas y mas musgo
    vor = k.n('ShaderNodeTexVoronoi')
    vor.inputs['Scale'].default_value = 7.0
    k.l(k.comb(x, y, z), vor.inputs['Vector'])
    liq = k.mat_('MULTIPLY', umbral(k, vor.outputs['Distance'], 0.32, 0.18), umbral(k, k.noise(k.comb(x, y, z), 0.8, 3.0, 0.5), 0.45, 0.6), True)
    col = k.mix(col, (0.42, 0.40, 0.27), k.mat_('MULTIPLY', liq, 0.8))
    mus = k.noise(k.comb(k.mat_('MULTIPLY', x, 1.3), k.mat_('MULTIPLY', y, 1.3), 1.0), 1.0, 7.0, 0.6)
    col = k.mix(col, (0.07, 0.11, 0.05), k.mat_('MULTIPLY', umbral(k, mus, 0.55, 0.68), 0.85))
    col = k.mix(col, (0.012, 0.010, 0.009), falta)
    marcar(k, col, b)
    k.l(bump_encima(k, k.mat_('SUBTRACT', k.mat_('MULTIPLY', r, 0.3), falta), nrm, 0.9, 0.05), b.inputs['Normal'])


def desgaste_metal(m, cobre_=False, laton=False):
    nt = m.node_tree; k = K(nt)
    b, col, nrm = base_y_normal(nt)
    x, y, z = k.xyz(k.pos())
    r = k.noise(k.comb(k.mat_('MULTIPLY', x, 3.0), k.mat_('MULTIPLY', y, 3.0), k.mat_('MULTIPLY', z, 3.0)), 1.0, 9.0, 0.7)
    est = k.noise(k.comb(k.mat_('MULTIPLY', k.mat_('ADD', x, y), 9.0), k.mat_('MULTIPLY', z, 0.5), 0.0), 1.0, 4.0, 0.5)
    if cobre_:
        # cardenillo que chorrea hacia abajo
        mv = k.mat_('MAXIMUM', umbral(k, r, 0.42, 0.55), umbral(k, est, 0.55, 0.7))
        col = k.mix(col, (0.12, 0.36, 0.30), mv)
        mo = None
    elif laton:
        mo = umbral(k, r, 0.45, 0.62)
        col = k.mix(col, (0.16, 0.14, 0.08), mo)
    else:
        mo = k.mat_('MAXIMUM', umbral(k, r, 0.40, 0.52), k.mat_('MULTIPLY', umbral(k, est, 0.55, 0.7), 0.8))
        oxido = k.rampa(k.noise(k.comb(k.mat_('MULTIPLY', x, 20.0), k.mat_('MULTIPLY', y, 20.0), k.mat_('MULTIPLY', z, 20.0)), 1.0, 5.0, 0.6),
                        (0.16, 0.06, 0.025), (0.42, 0.18, 0.07))
        col = k.mix(col, oxido, mo)
    marcar(k, col, b)
    if mo is not None:
        # donde hay oxido: nada metalico y muy rugoso
        met = rampa_z(k, mo, 0.0, 1.0, b.inputs['Metallic'].default_value, 0.05)
        rou = rampa_z(k, mo, 0.0, 1.0, b.inputs['Roughness'].default_value, 0.92)
        k.l(met, b.inputs['Metallic'])
        k.l(rou, b.inputs['Roughness'])
        k.l(bump_encima(k, mo, nrm, 0.35, 0.01), b.inputs['Normal'])


TRABAJO = (("Tower.", desgaste_torre),
           ("SmallBuilding.", lambda m: desgaste_madera_cabana(m, True)),
           ("BuildingWood.", lambda m: desgaste_madera_cabana(m, False)),
           ("TowerWoodDecor.", lambda m: desgaste_madera_cabana(m, False)),
           ("Roof tiles.", desgaste_teja),
           ("TowerTop.", lambda m: desgaste_metal(m, cobre_=True)),
           ("lightFrame.", lambda m: desgaste_metal(m, laton=True)),
           ("lantern.", desgaste_metal),
           ("Puerta_Hierro", desgaste_metal),
           ("Escalera_Hierro", desgaste_metal),
           ("Puerta_Madera", lambda m: desgaste_madera_cabana(m, True)))
for pref, fn in TRABAJO:
    for mm in [x for x in bpy.data.materials if x.name.startswith(pref) and x.node_tree]:
        if ya(mm):
            print("ya", mm.name)
            continue
        fn(mm)
        print("DESGASTE", mm.name)

if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
