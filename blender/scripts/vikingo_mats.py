# Materiales procedurales de la capa vikinga (piedra antigua con liquen, musgo, grietas y TALLAS; madera podrida) y
# utilidades comunes de vikingos.py y piedras_puzle2.py. Se importa desde esos scripts (necesita bpy).
#   piedra(nombre, ..., talla={...})  -> material de piedra; la talla es una imagen de runas_lib.py proyectada sobre el objeto
#   Las manchas usan coordenadas del MUNDO (no dependen de los UV y sobreviven al horneado); la talla usa coordenadas del OBJETO.
#   Atributo de vertice "Suelo" (float, metros sobre el suelo): humedad y musgo al pie de la piedra.
import bpy, os, math, sys

D = bpy.data
AQUI = os.path.dirname(os.path.abspath(__file__))
_ruta = os.path.join(AQUI, "texturizar_faro.py")
exec(compile(open(_ruta, encoding="utf-8").read().split("# ------------------------------------------------------------------ materiales")[0], _ruta, "exec"))
sys.path.insert(0, AQUI)
import runas_lib

TALLAS = os.path.join(os.path.dirname(AQUI), "texturas", "vikingo")


def generar_tallas():
    runas_lib.generar_todo(TALLAS)


def imagen_talla(nombre):
    ruta = os.path.join(TALLAS, nombre + ".png")
    img = D.images.get(nombre + ".png")
    if img is None:
        img = D.images.load(ruta)
    else:
        img.filepath = ruta
        img.reload()
    img.colorspace_settings.name = 'Non-Color'
    try:
        img.filepath = bpy.path.relpath(ruta)
    except Exception:
        pass
    return img


def mr(k, v, a, b, va=0.0, vb=1.0):
    n = k.n('ShaderNodeMapRange')
    n.clamp = True
    n.interpolation_type = 'SMOOTHSTEP'
    for nombre, x in (('From Min', a), ('From Max', b), ('To Min', va), ('To Max', vb)):
        n.inputs[nombre].default_value = x
    if isinstance(v, (int, float)):
        n.inputs['Value'].default_value = v
    else:
        k.l(v, n.inputs['Value'])
    return n.outputs[0]


def voronoi(k, vec, escala, feature='F1', salida='Distance'):
    n = k.n('ShaderNodeTexVoronoi')
    n.feature = feature
    n.inputs['Scale'].default_value = escala
    k.l(vec, n.inputs['Vector'])
    return n.outputs[salida]


def vmath(k, op, a, b):
    n = k.n('ShaderNodeVectorMath', op=op)
    for i, x in enumerate((a, b)):
        if x is None:
            continue
        if isinstance(x, tuple):
            n.inputs[i].default_value = x
        elif isinstance(x, (int, float)):
            n.inputs[i].default_value = (x, x, x)
        else:
            k.l(x, n.inputs[i])
    return n.outputs[0]


def gris(c, f):
    return (c[0] * f, c[1] * f, c[2] * f)


def _talla_nodos(k, talla):
    """devuelve la profundidad de la talla (0..1) segun la proyeccion pedida"""
    tc = k.n('ShaderNodeTexCoord')
    ox, oy, oz = k.xyz(tc.outputs['Object'])
    nx, ny, nz = k.xyz(tc.outputs['Normal'])
    img = k.n('ShaderNodeTexImage')
    img.image = imagen_talla(talla['imagen'])
    img.interpolation = 'Cubic'
    modo = talla.get('modo', 'frente')
    if modo == 'frente':
        # cara delantera de la losa (mira a -Y del objeto): u = x, v = z
        an, al = talla['ancho'], talla['alto']
        u = k.mat_('ADD', k.mat_('DIVIDE', k.mat_('SUBTRACT', ox, talla.get('cx', 0.0)), an), 0.5)
        v = k.mat_('DIVIDE', k.mat_('SUBTRACT', oz, talla.get('z0', 0.0)), al)
        img.extension = 'CLIP'
        k.l(k.comb(u, v, 0.0), img.inputs['Vector'])
        cara = mr(k, k.mat_('MULTIPLY', ny, -1.0), 0.25, 0.6)
        return k.mat_('MULTIPLY', img.outputs['Color'], cara)
    if modo == 'cilindro':
        # banda alrededor del eje Z del objeto entre z0 y z1; la costura queda en -Y
        cx, cy = talla.get('cx', 0.0), talla.get('cy', 0.0)
        ang = k.mat_('ARCTAN2', k.mat_('SUBTRACT', ox, cx), k.mat_('SUBTRACT', oy, cy))
        u = k.mat_('ADD', k.mat_('MULTIPLY', ang, talla.get('rep', 1) / (2 * math.pi)), 0.5)
        v = k.mat_('DIVIDE', k.mat_('SUBTRACT', oz, talla['z0']), talla['z1'] - talla['z0'])
        img.extension = 'REPEAT'
        k.l(k.comb(u, v, 0.0), img.inputs['Vector'])
        dentro = k.mat_('MULTIPLY', k.mat_('GREATER_THAN', v, 0.0), k.mat_('LESS_THAN', v, 1.0))
        lado = mr(k, k.mat_('ABSOLUTE', nz), 0.75, 0.5)          # solo en las caras laterales
        return k.mat_('MULTIPLY', k.mat_('MULTIPLY', img.outputs['Color'], dentro), lado)
    raise ValueError(modo)


def piedra(nombre, claro=(0.165, 0.165, 0.17), oscuro=(0.055, 0.057, 0.063), calido=0.3, liquen=1.0, musgo=1.0,
           tallas=None, pigmento=(0.21, 0.036, 0.018), grietas=1.0, escala=1.0, musgo_arriba=0.19, musgo_pie=0.12, humedad=0.7):
    """piedra antigua. tallas = lista de dicts (ver _talla_nodos). escala < 1 hace las manchas mas grandes.
    musgo_arriba / musgo_pie: cuanto musgo extra en las caras que miran al cielo / junto al suelo (losas tumbadas: bajarlo)."""
    m = D.materials.get(nombre) or D.materials.new(nombre)
    nt, b = limpiar(m)
    k = K(nt)
    geo = k.n('ShaderNodeNewGeometry')
    pos = vmath(k, 'SCALE', geo.outputs['Position'], None)
    pos.node.inputs['Scale'].default_value = escala
    gx, gy, gz = k.xyz(geo.outputs['Normal'])
    x, y, z = k.xyz(pos)
    suelo_at = k.n('ShaderNodeAttribute')
    suelo_at.attribute_name = "Suelo"
    suelo = suelo_at.outputs['Fac']

    # ---- color base: manchas grandes, vetas medias, grano fino y motas minerales
    n_g = k.noise(pos, 0.42, 5.0, 0.6)
    n_m = k.noise(pos, 2.4, 7.0, 0.68)
    n_f = k.noise(pos, 46.0, 3.0, 0.6)
    col = k.rampa(n_g, oscuro, claro, 0.3, 0.72)
    tibio = k.noise(vmath(k, 'ADD', pos, (31.0, 7.0, 3.0)), 0.8, 3.0, 0.5)
    col = k.mix(col, gris((1.12, 1.0, 0.84), 1.0), k.mat_('MULTIPLY', mr(k, tibio, 0.45, 0.7), calido * 0.55), 'MULTIPLY')
    col = k.mix(col, k.rampa(n_m, (0.62, 0.62, 0.63), (1.22, 1.22, 1.2), 0.25, 0.78), 1.0, 'MULTIPLY')
    col = k.mix(col, k.rampa(n_f, (0.8, 0.8, 0.8), (1.14, 1.14, 1.14), 0.3, 0.7), 1.0, 'MULTIPLY')
    motas = voronoi(k, pos, 150.0)
    col = k.mix(col, gris(oscuro, 0.5), k.mat_('MULTIPLY', mr(k, motas, 0.22, 0.1), 0.55))
    motas2 = voronoi(k, vmath(k, 'ADD', pos, (3.3, 1.7, 9.1)), 95.0)
    col = k.mix(col, gris(claro, 1.5), k.mat_('MULTIPLY', mr(k, motas2, 0.16, 0.06), 0.4))

    # ---- grietas finas (bordes de celdas deformadas; solo asoman algunas) y picaduras
    deform = k.n('ShaderNodeTexNoise')
    deform.inputs['Scale'].default_value = 1.7
    deform.inputs['Detail'].default_value = 4.0
    k.l(pos, deform.inputs['Vector'])
    desv = vmath(k, 'SCALE', deform.outputs['Color'], None)
    desv.node.inputs['Scale'].default_value = 0.7
    p_g = vmath(k, 'ADD', pos, desv)
    borde = voronoi(k, p_g, 1.15, 'DISTANCE_TO_EDGE')
    puerta = mr(k, k.noise(vmath(k, 'ADD', pos, (11.0, 5.0, 2.0)), 0.6, 2.0, 0.5), 0.47, 0.6)
    grieta = k.mat_('MULTIPLY', k.mat_('MULTIPLY', mr(k, borde, 0.02, 0.003), puerta), grietas)
    n_p = k.noise(pos, 11.0, 5.0, 0.72)
    pica = mr(k, n_p, 0.66, 0.75)
    col = k.mix(col, gris(oscuro, 0.35), k.mat_('MULTIPLY', grieta, 0.9))
    col = k.mix(col, gris(oscuro, 0.6), k.mat_('MULTIPLY', pica, 0.6))

    # ---- chorreras oscuras de lluvia en las caras verticales
    ch = k.noise(k.comb(k.mat_('MULTIPLY', x, 3.6), k.mat_('MULTIPLY', y, 3.6), k.mat_('MULTIPLY', z, 0.2)), 1.0, 5.0, 0.62)
    vertical = mr(k, k.mat_('ABSOLUTE', gz), 0.75, 0.35)
    col = k.mix(col, gris((0.52, 0.53, 0.55), 1.0), k.mat_('MULTIPLY', k.mat_('MULTIPLY', mr(k, ch, 0.5, 0.68), vertical), 0.85), 'MULTIPLY')

    # ---- tallas: surco hondo y oscuro, con restos del pigmento rojo con que se pintaban
    alt_talla = None
    if tallas:
        for t in tallas:
            d = _talla_nodos(k, t)
            alt_talla = d if alt_talla is None else k.mat_('MAXIMUM', alt_talla, d)
        col = k.mix(col, gris(oscuro, 0.4), k.mat_('MULTIPLY', mr(k, alt_talla, 0.05, 0.6), 0.88))
        resto = mr(k, k.noise(vmath(k, 'ADD', pos, (5.0, 13.0, 1.0)), 3.2, 4.0, 0.6), 0.44, 0.6)
        col = k.mix(col, pigmento, k.mat_('MULTIPLY', k.mat_('MULTIPLY', mr(k, alt_talla, 0.25, 0.8), resto), 0.8))

    # ---- liquen: costras gris verdoso y ocre de borde irregular
    fino = k.noise(pos, 17.0, 4.0, 0.7)
    l1 = k.mat_('ADD', k.noise(vmath(k, 'ADD', pos, (2.0, 9.0, 4.0)), 1.5, 5.0, 0.7), k.mat_('MULTIPLY', k.mat_('SUBTRACT', fino, 0.5), 0.3))
    m_l1 = k.mat_('MULTIPLY', mr(k, l1, 0.585, 0.63), 0.85 * liquen)
    col = k.mix(col, k.mix((0.20, 0.225, 0.165), (0.29, 0.31, 0.25), fino), m_l1)
    l2 = k.mat_('ADD', k.noise(vmath(k, 'ADD', pos, (17.0, 3.0, 8.0)), 2.3, 5.0, 0.7), k.mat_('MULTIPLY', k.mat_('SUBTRACT', fino, 0.5), 0.3))
    m_l2 = k.mat_('MULTIPLY', mr(k, l2, 0.655, 0.685), 0.8 * liquen)
    col = k.mix(col, (0.25, 0.17, 0.045), m_l2)

    # ---- humedad al pie y musgo (arriba de las caras que miran al cielo y junto al suelo)
    pie = mr(k, suelo, 0.05, 0.75, 1.0, 0.0)
    col = k.mix(col, gris((0.6, 0.61, 0.61), 1.0), k.mat_('MULTIPLY', pie, humedad), 'MULTIPLY')
    n_mu = k.mat_('ADD', k.noise(vmath(k, 'ADD', pos, (8.0, 1.0, 6.0)), 2.8, 5.0, 0.7), k.mat_('MULTIPLY', k.mat_('SUBTRACT', fino, 0.5), 0.35))
    arriba = mr(k, gz, 0.25, 0.8)
    cuanto = k.mat_('ADD', k.mat_('MULTIPLY', arriba, musgo_arriba), k.mat_('MULTIPLY', pie, musgo_pie))
    m_mu = k.mat_('MULTIPLY', mr(k, k.mat_('ADD', n_mu, cuanto), 0.66, 0.74), min(musgo, 1.0))
    if musgo <= 0:
        m_mu = k.mat_('MULTIPLY', m_mu, 0.0)
    col_mu = k.mix((0.022, 0.04, 0.012), (0.06, 0.085, 0.022), k.noise(pos, 60.0, 2.0, 0.5))
    col = k.mix(col, col_mu, m_mu)

    # ---- relieve
    alt = k.mat_('ADD', k.mat_('MULTIPLY', n_m, 0.5), k.mat_('MULTIPLY', n_f, 0.12))
    alt = k.mat_('SUBTRACT', alt, k.mat_('MULTIPLY', grieta, 0.5))
    alt = k.mat_('SUBTRACT', alt, k.mat_('MULTIPLY', pica, 0.3))
    alt = k.mat_('ADD', alt, k.mat_('MULTIPLY', m_l1, 0.08))
    alt = k.mat_('ADD', alt, k.mat_('MULTIPLY', m_mu, 0.45))
    normal = k.bump(alt, 0.7, 0.02)
    if alt_talla is not None:
        bt = k.n('ShaderNodeBump')
        bt.inputs['Strength'].default_value = 1.0
        bt.inputs['Distance'].default_value = 0.016
        bt.invert = True
        k.l(alt_talla, bt.inputs['Height'])
        k.l(normal, bt.inputs['Normal'])
        normal = bt.outputs['Normal']
    k.l(col, b.inputs['Base Color'])
    k.l(normal, b.inputs['Normal'])
    rug = k.mat_('ADD', 0.84, k.mat_('MULTIPLY', k.mat_('MAXIMUM', m_mu, m_l1), 0.14))
    k.l(rug, b.inputs['Roughness'])
    b.inputs['Metallic'].default_value = 0.0
    m.diffuse_color = (*claro, 1)
    return m


def talla_pintada(nombre, fondo=(0.035, 0.03, 0.03), pigmento=(0.20, 0.034, 0.018)):
    """material de las figuras de los postes (antes 'tinta' negra plana): surco oscuro con restos de pigmento rojo y liquen"""
    m = D.materials.get(nombre) or D.materials.new(nombre)
    nt, b = limpiar(m)
    k = K(nt)
    pos = k.pos()
    resto = mr(k, k.noise(pos, 3.0, 5.0, 0.65), 0.4, 0.62)
    fino = k.noise(pos, 40.0, 3.0, 0.6)
    col = k.mix(fondo, pigmento, k.mat_('MULTIPLY', resto, 0.85))
    col = k.mix(col, k.rampa(fino, (0.7, 0.7, 0.7), (1.25, 1.25, 1.25)), 1.0, 'MULTIPLY')
    liq = mr(k, k.noise(vmath(k, 'ADD', pos, (2.0, 9.0, 4.0)), 1.5, 5.0, 0.7), 0.6, 0.64)
    col = k.mix(col, (0.2, 0.22, 0.16), k.mat_('MULTIPLY', liq, 0.6))
    listo(b, col, k.bump(fino, 0.5, 0.01), 0.9, 0.0, k)
    m.diffuse_color = (*pigmento, 1)
    return m


def musgo(nombre):
    """musgo y hongos de repisa: verde oscuro apagado (antes era un verde chillon plano)"""
    m = D.materials.get(nombre) or D.materials.new(nombre)
    nt, b = limpiar(m)
    k = K(nt)
    pos = k.pos()
    n1 = k.noise(pos, 5.0, 5.0, 0.7)
    n2 = k.noise(pos, 70.0, 2.0, 0.6)
    gx, gy, gz = k.xyz(k.n('ShaderNodeNewGeometry').outputs['Normal'])
    col = k.rampa(n1, (0.022, 0.038, 0.012), (0.075, 0.10, 0.03), 0.3, 0.75)
    col = k.mix(col, (0.11, 0.095, 0.035), k.mat_('MULTIPLY', mr(k, k.noise(vmath(k, 'ADD', pos, (4.0, 4.0, 4.0)), 2.0, 3.0, 0.5), 0.55, 0.7), 0.6))   # partes secas
    col = k.mix(col, k.rampa(n2, (0.6, 0.6, 0.6), (1.3, 1.3, 1.3)), 1.0, 'MULTIPLY')
    col = k.mix(col, (0.012, 0.016, 0.008), k.mat_('MULTIPLY', mr(k, gz, 0.1, -0.5), 0.8))     # por debajo, oscuro
    listo(b, col, k.bump(k.mat_('ADD', n2, k.mat_('MULTIPLY', n1, 0.5)), 0.9, 0.012), 1.0, 0.0, k)
    m.diffuse_color = (0.05, 0.08, 0.02, 1)
    return m


def madera_vieja(nombre, tono=(0.105, 0.095, 0.082)):
    """madera gris, agrietada y podrida (veta a lo largo del eje Z del objeto)"""
    m = D.materials.get(nombre) or D.materials.new(nombre)
    nt, b = limpiar(m)
    k = K(nt)
    tc = k.n('ShaderNodeTexCoord')
    ox, oy, oz = k.xyz(tc.outputs['Object'])
    pos = k.pos()
    veta = k.noise(k.comb(k.mat_('MULTIPLY', ox, 38.0), k.mat_('MULTIPLY', oy, 38.0), k.mat_('MULTIPLY', oz, 2.2)), 1.0, 6.0, 0.62)
    grande = k.noise(pos, 1.4, 4.0, 0.6)
    col = k.rampa(veta, gris(tono, 0.5), gris(tono, 1.5), 0.3, 0.72)
    col = k.mix(col, k.rampa(grande, (0.6, 0.6, 0.62), (1.2, 1.18, 1.1)), 1.0, 'MULTIPLY')
    raja = mr(k, k.noise(k.comb(k.mat_('MULTIPLY', ox, 60.0), k.mat_('MULTIPLY', oy, 60.0), k.mat_('MULTIPLY', oz, 1.1)), 1.0, 3.0, 0.5), 0.63, 0.7)
    col = k.mix(col, (0.012, 0.01, 0.009), k.mat_('MULTIPLY', raja, 0.9))
    suelo_at = k.n('ShaderNodeAttribute')
    suelo_at.attribute_name = "Suelo"
    pie = mr(k, suelo_at.outputs['Fac'], 0.0, 0.9, 1.0, 0.0)
    col = k.mix(col, (0.45, 0.47, 0.45), k.mat_('MULTIPLY', pie, 0.8), 'MULTIPLY')
    verd = k.mat_('MULTIPLY', mr(k, k.mat_('ADD', k.noise(vmath(k, 'ADD', pos, (8.0, 1.0, 6.0)), 3.0, 5.0, 0.7), k.mat_('MULTIPLY', pie, 0.25)), 0.6, 0.7), 0.85)
    col = k.mix(col, (0.035, 0.055, 0.02), verd)
    sal = mr(k, k.noise(vmath(k, 'ADD', pos, (1.0, 21.0, 6.0)), 4.0, 5.0, 0.7), 0.62, 0.75)
    col = k.mix(col, (0.3, 0.3, 0.28), k.mat_('MULTIPLY', sal, 0.35))
    alt = k.mat_('SUBTRACT', k.mat_('MULTIPLY', veta, 0.6), k.mat_('MULTIPLY', raja, 0.8))
    listo(b, col, k.bump(alt, 0.8, 0.012), 0.88, 0.0, k)
    m.diffuse_color = (*tono, 1)
    return m


def hierro_oxidado(nombre):
    """hierro comido por el oxido (espada, umbo del escudo): costras naranja oscuro, picado"""
    m = D.materials.get(nombre) or D.materials.new(nombre)
    nt, b = limpiar(m)
    k = K(nt)
    pos = k.pos()
    n1 = k.noise(pos, 9.0, 6.0, 0.7)
    n2 = k.noise(pos, 55.0, 3.0, 0.6)
    col = k.rampa(n1, (0.035, 0.018, 0.012), (0.16, 0.06, 0.022), 0.3, 0.75)
    col = k.mix(col, (0.03, 0.03, 0.033), k.mat_('MULTIPLY', mr(k, k.noise(vmath(k, 'ADD', pos, (3.0, 3.0, 3.0)), 5.0, 3.0, 0.5), 0.55, 0.7), 0.7))
    col = k.mix(col, k.rampa(n2, (0.65, 0.65, 0.65), (1.3, 1.3, 1.3)), 1.0, 'MULTIPLY')
    listo(b, col, k.bump(k.mat_('ADD', n1, k.mat_('MULTIPLY', n2, 0.4)), 1.0, 0.006), 0.82, 0.25, k)
    m.diffuse_color = (0.12, 0.05, 0.02, 1)
    return m


def atributo_suelo(me, alturas):
    """escribe el atributo de vertice 'Suelo' (metros sobre el suelo)"""
    at = me.attributes.get("Suelo")
    if at is None:
        at = me.attributes.new("Suelo", 'FLOAT', 'POINT')
    at.data.foreach_set("value", alturas)
