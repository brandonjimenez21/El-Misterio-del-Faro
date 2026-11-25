# Envejece el muelle (Escenario_Muelle): tablas irregulares en vez de cajas perfectas.
#  - Cubierta: cada tabla (caja de 8 vertices) se rehace con 15 segmentos, arqueo, alabeo, extremos astillados,
#    desniveles y algunas hundidas.
#  - Barandas: travesanos arqueados.
#  - Material (M_MaderaGris / M_MaderaMojada): color distinto por tabla, grietas, sal blanca y relieve mas fuerte.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/envejecer_muelle.py -- --save
# Si el objeto ya tiene la propiedad 'envejecido' no vuelve a tocar la geometria.
import bpy, bmesh, math, random, sys
from mathutils import Vector, Matrix

rnd = random.Random(1904)


def componentes(bm):
    visto = set()
    out = []
    for v in bm.verts:
        if v.index in visto:
            continue
        pila = [v]
        visto.add(v.index)
        vs = []
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


def caja_irregular(L, W, T, eje_largo_y, centro, material_idx, danio=1.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * L, v.co.y * W, v.co.z * T))
    b = 0.007 + rnd.uniform(0, 0.004)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=b, segments=1, affect='EDGES')
    largos = [e for e in bm.edges if abs(e.verts[0].co.x - e.verts[1].co.x) > 0.3 * L]
    bmesh.ops.subdivide_edges(bm, edges=largos, cuts=14, use_grid_fill=True)
    arqueo = rnd.gauss(0, 0.010) * danio
    copa = rnd.gauss(0, 0.005) * danio
    alabeo = rnd.gauss(0, 0.008) * danio
    ruido_f = rnd.uniform(0, 100)
    dano_a = rnd.random() < 0.40
    dano_b = rnd.random() < 0.40
    esq_a = rnd.choice((-1, 1))
    esq_b = rnd.choice((-1, 1))
    prof_a = rnd.uniform(0.04, 0.14)
    prof_b = rnd.uniform(0.04, 0.14)
    hundida = rnd.random() < 0.10
    hund = rnd.uniform(0.012, 0.04) * (1 if rnd.random() < 0.5 else -1) if hundida else 0.0
    for v in bm.verts:
        u = v.co.x / (L * 0.5)
        w = v.co.y / (W * 0.5)
        t = v.co.z / (T * 0.5)
        d = 0.0
        d += arqueo * (1 - u * u)
        d += copa * (w * w) * (0.5 + 0.5 * t)
        d += alabeo * u * w
        d += 0.0035 * math.sin(u * 5.1 + ruido_f) * (0.5 + 0.5 * t)
        d += hund * (u * 0.5 + 0.5) ** 2
        v.co.z += d
        if dano_a and u < -0.82 and w * esq_a > -0.1:
            f = (-0.82 - u) / 0.18
            v.co.x += f * prof_a * rnd.uniform(0.6, 1.0)
            v.co.z -= f * 0.01 * (0.5 + 0.5 * t)
        if dano_b and u > 0.82 and w * esq_b > -0.1:
            f = (u - 0.82) / 0.18
            v.co.x -= f * prof_b * rnd.uniform(0.6, 1.0)
            v.co.z -= f * 0.01 * (0.5 + 0.5 * t)
        v.co.z += rnd.uniform(-0.0012, 0.0012) * (0.5 + 0.5 * t)
        v.co.y += rnd.uniform(-0.0015, 0.0015)
    giro = math.radians(rnd.gauss(0, 0.9))
    dz = rnd.gauss(0, 0.007) * danio
    dy = rnd.gauss(0, 0.007)
    inclina = math.radians(rnd.gauss(0, 0.8))
    M = Matrix.Translation(Vector((0, dy, dz))) @ Matrix.Rotation(giro, 4, 'Z') @ Matrix.Rotation(inclina, 4, 'X')
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    if eje_largo_y:
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(math.pi / 2, 4, 'Z'), verts=bm.verts)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(centro), verts=bm.verts)
    for f in bm.faces:
        f.material_index = material_idx
    return bm


def envejecer_objeto(nombre, filtro):
    o = bpy.data.objects[nombre]
    if o.get("envejecido"):
        print("ya envejecido", nombre)
        return 0
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    comps = componentes(bm)
    n = 0
    nuevos = []
    borrar = []
    for vs in comps:
        if len(vs) != 8:
            continue
        xs = [v.co.x for v in vs]; ys = [v.co.y for v in vs]; zs = [v.co.z for v in vs]
        dx, dy, dz = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
        if not filtro(dx, dy, dz):
            continue
        c = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2))
        mat_idx = vs[0].link_faces[0].material_index if vs[0].link_faces else 0
        largo_y = dy > dx
        L, W = (dy, dx) if largo_y else (dx, dy)
        nuevos.append(caja_irregular(L, W, dz, largo_y, c, mat_idx))
        borrar.extend(vs)
        n += 1
    bmesh.ops.delete(bm, geom=borrar, context='VERTS')
    for nb in nuevos:
        me_tmp = bpy.data.meshes.new("tmp")
        nb.to_mesh(me_tmp)
        nb.free()
        bm.from_mesh(me_tmp)
        bpy.data.meshes.remove(me_tmp)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    o["envejecido"] = 1
    print("ENVEJECIDO", nombre, n, "piezas")
    return n


envejecer_objeto("Muelle_Cubierta", lambda dx, dy, dz: dz < 0.13 and ((dx > 1.0 and 0.1 < dy < 0.4) or (dy > 1.0 and 0.1 < dx < 0.4)))
envejecer_objeto("Muelle_Barandas", lambda dx, dy, dz: (dy > 1.5 and dx < 0.2 and dz < 0.25) or (dx > 1.5 and dy < 0.2 and dz < 0.25))

# ------------------------------------------------------------------ material: mas irregular
for nm in ("M_MaderaGris", "M_MaderaMojada"):
    m = bpy.data.materials[nm]
    nt = m.node_tree
    if nt.nodes.get("Envejecido_Fin"):
        continue
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    origen = bsdf.inputs["Base Color"].links[0].from_socket
    tc = N["Texture Coordinate"]
    sep = N.new('ShaderNodeSeparateXYZ')
    L.new(tc.outputs["Object"], sep.inputs["Vector"])

    def aleatorio_por_fila(eje, factor, desp):
        mul = N.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = factor
        L.new(sep.outputs[eje], mul.inputs[0])
        fl = N.new('ShaderNodeMath'); fl.operation = 'FLOOR'
        L.new(mul.outputs[0], fl.inputs[0])
        wn = N.new('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '1D'
        ad = N.new('ShaderNodeMath'); ad.operation = 'ADD'; ad.inputs[1].default_value = desp
        L.new(fl.outputs[0], ad.inputs[0])
        L.new(ad.outputs[0], wn.inputs["W"])
        return wn.outputs["Value"]

    ry = aleatorio_por_fila("Y", 3.7, 0.0)
    rampa_tabla = N.new('ShaderNodeValToRGB')
    rampa_tabla.color_ramp.elements[0].position = 0.0
    rampa_tabla.color_ramp.elements[0].color = (0.55, 0.50, 0.46, 1)
    rampa_tabla.color_ramp.elements[1].position = 1.0
    rampa_tabla.color_ramp.elements[1].color = (1.25, 1.1, 0.95, 1)
    L.new(ry, rampa_tabla.inputs["Fac"])
    mult1 = N.new('ShaderNodeMix'); mult1.data_type = 'RGBA'; mult1.blend_type = 'MULTIPLY'
    mult1.inputs[0].default_value = 1.0
    L.new(origen, mult1.inputs[6])
    L.new(rampa_tabla.outputs["Color"], mult1.inputs[7])
    mp = N.new('ShaderNodeMapping')
    mp.inputs["Scale"].default_value = (1.2, 22.0, 9.0)
    L.new(tc.outputs["Object"], mp.inputs["Vector"])
    vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs["Scale"].default_value = 3.0
    L.new(mp.outputs["Vector"], vor.inputs["Vector"])
    grieta = N.new('ShaderNodeValToRGB')
    grieta.color_ramp.elements[0].position = 0.0; grieta.color_ramp.elements[0].color = (1, 1, 1, 1)
    grieta.color_ramp.elements[1].position = 0.085; grieta.color_ramp.elements[1].color = (0, 0, 0, 1)
    L.new(vor.outputs["Distance"], grieta.inputs["Fac"])
    rr = aleatorio_por_fila("Y", 3.7, 11.0)
    solo = N.new('ShaderNodeMath'); solo.operation = 'GREATER_THAN'; solo.inputs[1].default_value = 0.45
    L.new(rr, solo.inputs[0])
    gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'
    L.new(grieta.outputs["Color"], gm.inputs[0]); L.new(solo.outputs[0], gm.inputs[1])
    # 1 - gm = cantidad de oscurecido (grieta=0 -> oscuro)
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(gm.outputs[0], inv.inputs[1])
    mult2 = N.new('ShaderNodeMix'); mult2.data_type = 'RGBA'
    L.new(inv.outputs[0], mult2.inputs[0])
    L.new(mult1.outputs[2], mult2.inputs[6])
    mult2.inputs[7].default_value = (0.012, 0.010, 0.008, 1)
    sal_n = N.new('ShaderNodeTexNoise'); sal_n.inputs["Scale"].default_value = 9.0; sal_n.inputs["Detail"].default_value = 7.0
    L.new(tc.outputs["Object"], sal_n.inputs["Vector"])
    sal_r = N.new('ShaderNodeValToRGB')
    sal_r.color_ramp.elements[0].position = 0.58; sal_r.color_ramp.elements[0].color = (0, 0, 0, 1)
    sal_r.color_ramp.elements[1].position = 0.78; sal_r.color_ramp.elements[1].color = (0.5, 0.5, 0.5, 1)
    L.new(sal_n.outputs["Fac"], sal_r.inputs["Fac"])
    sal = N.new('ShaderNodeMix'); sal.data_type = 'RGBA'; sal.name = "Envejecido_Fin"
    L.new(sal_r.outputs["Color"], sal.inputs[0])
    L.new(mult2.outputs[2], sal.inputs[6])
    sal.inputs[7].default_value = (0.42, 0.42, 0.38, 1)
    L.new(sal.outputs[2], bsdf.inputs["Base Color"])
    if "Bump" in N:
        N["Bump"].inputs["Strength"].default_value = 1.2
        N["Bump"].inputs["Distance"].default_value = 0.03
    print("MATERIAL", nm)

if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
