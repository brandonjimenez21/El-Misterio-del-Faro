# Materiales procedurales de epoca (siglo XIX) para el faro y la cabana. Usan coordenadas del MUNDO
# (nodo Geometry > Position), asi no dependen de los UV y sobreviven al horneado de exportar_unity.py.
#   - Torre: mamposteria de sillares encalada, mas oscura y humeda en la base.
#   - Cabana: tablas de madera vieja en vertical, vigas de madera oscura, tejado de teja de barro.
#   - Interior: piso y paredes de madera, losas de piedra en la torre.
#   - Metales: hierro forjado oxidado, laton (marco de la linterna), cobre con pátina (cubierta).
import bpy, math
from mathutils import Vector

O = bpy.data.objects
M = bpy.data.materials
TC = (-6.64, 89.52)                  # eje de la torre (xy)


def limpiar(m):
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    return nt, b


class K:
    """pequeño ayudante para crear nodos"""
    def __init__(self, nt):
        self.nt = nt

    def n(self, tipo, **kw):
        nd = self.nt.nodes.new(tipo)
        for k, v in kw.items():
            if k == 'op':
                nd.operation = v
            elif k == 'bl':
                nd.blend_type = v
            else:
                setattr(nd, k, v)
        return nd

    def l(self, a, b):
        self.nt.links.new(a, b)

    def pos(self):
        return self.n('ShaderNodeNewGeometry').outputs['Position']

    def xyz(self, v):
        s = self.n('ShaderNodeSeparateXYZ')
        self.l(v, s.inputs[0])
        return s.outputs[0], s.outputs[1], s.outputs[2]

    def mat_(self, op, a, b=None, clamp=False):
        nd = self.n('ShaderNodeMath', op=op)
        nd.use_clamp = clamp
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                nd.inputs[i].default_value = x
            else:
                self.l(x, nd.inputs[i])
        return nd.outputs[0]

    def comb(self, x, y, z=0.0):
        c = self.n('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            if isinstance(v, (int, float)):
                c.inputs[i].default_value = v
            else:
                self.l(v, c.inputs[i])
        return c.outputs[0]

    def mix(self, a, b, fac, bl='MIX'):
        m = self.n('ShaderNodeMix', data_type='RGBA', blend_type=bl)
        if isinstance(fac, (int, float)):
            m.inputs[0].default_value = fac
        else:
            self.l(fac, m.inputs[0])
        for i, x in ((6, a), (7, b)):
            if isinstance(x, tuple):
                m.inputs[i].default_value = x if len(x) == 4 else (x[0], x[1], x[2], 1.0)
            else:
                self.l(x, m.inputs[i])
        return m.outputs[2]

    def noise(self, vec, escala, detalle=5.0, rugosidad=0.55):
        nd = self.n('ShaderNodeTexNoise')
        nd.inputs['Scale'].default_value = escala
        nd.inputs['Detail'].default_value = detalle
        nd.inputs['Roughness'].default_value = rugosidad
        self.l(vec, nd.inputs['Vector'])
        return nd.outputs['Fac']

    def rampa(self, fac, a, b, lo=0.0, hi=1.0):
        r = self.n('ShaderNodeValToRGB')
        r.color_ramp.elements[0].position = lo
        r.color_ramp.elements[1].position = hi
        r.color_ramp.elements[0].color = (*a, 1)
        r.color_ramp.elements[1].color = (*b, 1)
        self.l(fac, r.inputs['Fac'])
        return r.outputs['Color']

    def ladrillo(self, vec, c1, c2, mortero, ancho, alto, desfase=0.0, junta=0.012):
        br = self.n('ShaderNodeTexBrick')
        br.offset = desfase
        br.offset_frequency = 2
        br.squash = 1.0
        br.inputs['Color1'].default_value = (*c1, 1)
        br.inputs['Color2'].default_value = (*c2, 1)
        br.inputs['Mortar'].default_value = (*mortero, 1)
        br.inputs['Scale'].default_value = 1.0
        br.inputs['Mortar Size'].default_value = junta
        br.inputs['Mortar Smooth'].default_value = 0.1
        br.inputs['Bias'].default_value = 0.0
        br.inputs['Brick Width'].default_value = ancho
        br.inputs['Row Height'].default_value = alto
        self.l(vec, br.inputs['Vector'])
        return br.outputs['Color'], br.outputs['Fac']

    def bump(self, altura, fuerza=0.4, dist=0.02):
        b = self.n('ShaderNodeBump')
        b.inputs['Strength'].default_value = fuerza
        b.inputs['Distance'].default_value = dist
        self.l(altura, b.inputs['Height'])
        return b.outputs['Normal']


def listo(b, color, normal=None, rough=0.8, metal=0.0, k=None):
    k.l(color, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if normal is not None:
        k.l(normal, b.inputs['Normal'])


def mat_obtener(nombre_ini):
    for m in M:
        if m.name.startswith(nombre_ini):
            return m
    return None


# ------------------------------------------------------------------ materiales
def tablas_verticales(m, c1, c2, mortero, ancho=0.20, rough=0.85):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    u = k.mat_('SUBTRACT', k.mat_('MULTIPLY', x, 1.4), k.mat_('MULTIPLY', y, 0.2))
    vec = k.comb(u, z)
    col, fac = k.ladrillo(vec, c1, c2, mortero, ancho, 6.0, 0.0, 0.012)
    veta = k.noise(k.comb(k.mat_('MULTIPLY', u, 45.0), k.mat_('MULTIPLY', z, 1.4)), 1.0, 6.0, 0.6)
    col = k.mix(col, (0.55, 0.50, 0.46), 0.0)
    oscuro = k.rampa(veta, (0.55, 0.52, 0.5), (1.15, 1.1, 1.05))
    col = k.mix(col, oscuro, 1.0, 'MULTIPLY')
    sucio = k.noise(k.mat_xyz if False else k.comb(k.mat_('MULTIPLY', x, 0.35), k.mat_('MULTIPLY', z, 0.12), k.mat_('MULTIPLY', y, 0.35)), 1.0, 4.0, 0.6)
    col = k.mix(col, (0.45, 0.45, 0.42), k.mat_('MULTIPLY', sucio, 0.35), 'MULTIPLY')
    n = k.bump(k.mat_('ADD', fac, k.mat_('MULTIPLY', veta, 0.3)), 0.5, 0.02)
    listo(b, col, n, rough, 0.0, k)


def madera_general(m, c1, c2, rough=0.8, escala=4.0, estirado=0.15):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    veta = k.noise(k.comb(k.mat_('MULTIPLY', x, 30.0 * estirado + 2), k.mat_('MULTIPLY', y, 30.0 * estirado + 2), k.mat_('MULTIPLY', z, 5.0)), escala, 6.0, 0.6)
    veta2 = k.noise(k.comb(x, y, z), 1.3, 5.0, 0.6)
    col = k.rampa(veta, c1, c2)
    col = k.mix(col, (0.7, 0.7, 0.68), k.mat_('MULTIPLY', veta2, 0.6), 'MULTIPLY')
    n = k.bump(veta, 0.5, 0.015)
    listo(b, col, n, rough, 0.0, k)


def piso_madera(m, c1, c2, mortero):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    uw = k.mat_('SUBTRACT', k.mat_('MULTIPLY', x, 0.6), k.mat_('MULTIPLY', y, 0.8))       # eje W
    ua = k.mat_('ADD', k.mat_('MULTIPLY', x, 0.8), k.mat_('MULTIPLY', y, 0.6))             # eje U
    vec = k.comb(uw, ua)
    col, fac = k.ladrillo(vec, c1, c2, mortero, 0.24, 2.4, 0.37, 0.012)
    veta = k.noise(k.comb(k.mat_('MULTIPLY', uw, 40.0), k.mat_('MULTIPLY', ua, 2.0)), 1.0, 6.0, 0.6)
    col = k.mix(col, k.rampa(veta, (0.55, 0.52, 0.5), (1.15, 1.1, 1.05)), 1.0, 'MULTIPLY')
    gasto = k.noise(k.comb(k.mat_('MULTIPLY', x, 0.5), k.mat_('MULTIPLY', y, 0.5), 0.0), 1.0, 4.0, 0.6)
    col = k.mix(col, (0.6, 0.58, 0.55), k.mat_('MULTIPLY', gasto, 0.5), 'MULTIPLY')
    n = k.bump(k.mat_('ADD', fac, k.mat_('MULTIPLY', veta, 0.3)), 0.5, 0.02)
    listo(b, col, n, 0.8, 0.0, k)


def piedra_losas(m, c1, c2, mortero):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    col, fac = k.ladrillo(k.comb(x, y), c1, c2, mortero, 1.1, 0.8, 0.5, 0.03)
    r = k.noise(k.comb(k.mat_('MULTIPLY', x, 2.0), k.mat_('MULTIPLY', y, 2.0), 0.0), 3.0, 6.0, 0.6)
    col = k.mix(col, k.rampa(r, (0.6, 0.6, 0.58), (1.1, 1.1, 1.08)), 1.0, 'MULTIPLY')
    n = k.bump(k.mat_('ADD', fac, k.mat_('MULTIPLY', r, 0.4)), 0.7, 0.03)
    listo(b, col, n, 0.9, 0.0, k)


def torre_piedra(m):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    ang = k.mat_('ARCTAN2', k.mat_('SUBTRACT', y, TC[1]), k.mat_('SUBTRACT', x, TC[0]))
    u = k.mat_('MULTIPLY', ang, 7.0)
    vec = k.comb(u, z)
    col, fac = k.ladrillo(vec, (0.60, 0.56, 0.49), (0.40, 0.37, 0.32), (0.22, 0.20, 0.18), 1.15, 0.55, 0.5, 0.03)
    # manchas de humedad / hollin (ruido grande) y estrias verticales
    mancha = k.noise(k.comb(k.mat_('MULTIPLY', u, 0.5), k.mat_('MULTIPLY', z, 0.25), 0.0), 1.0, 6.0, 0.6)
    estria = k.noise(k.comb(k.mat_('MULTIPLY', u, 3.0), k.mat_('MULTIPLY', z, 0.12), 0.0), 1.0, 4.0, 0.55)
    col = k.mix(col, (0.30, 0.28, 0.25), k.mat_('MULTIPLY', k.mat_('SUBTRACT', mancha, 0.35, True), 1.2, True))
    col = k.mix(col, (0.34, 0.33, 0.30), k.mat_('MULTIPLY', k.mat_('SUBTRACT', estria, 0.45, True), 1.3, True))
    # base humeda y verdosa (hasta ~ 4 m sobre el piso)
    base = k.n('ShaderNodeMapRange')
    base.inputs['From Min'].default_value = 7.4
    base.inputs['From Max'].default_value = 13.0
    base.inputs['To Min'].default_value = 1.0
    base.inputs['To Max'].default_value = 0.0
    base.clamp = True
    k.l(z, base.inputs['Value'])
    col = k.mix(col, (0.12, 0.15, 0.11), k.mat_('MULTIPLY', base.outputs[0], 0.7))
    n = k.bump(k.mat_('ADD', fac, k.mat_('MULTIPLY', mancha, 0.25)), 0.8, 0.04)
    listo(b, col, n, 0.88, 0.0, k)


def teja(m):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    col, fac = k.ladrillo(k.comb(x, y), (0.42, 0.17, 0.08), (0.30, 0.11, 0.05), (0.10, 0.05, 0.04), 0.36, 0.42, 0.5, 0.02)
    r = k.noise(k.comb(x, y, z), 2.5, 6.0, 0.6)
    col = k.mix(col, (0.55, 0.55, 0.5), k.mat_('MULTIPLY', r, 0.6), 'MULTIPLY')
    musgo = k.noise(k.comb(k.mat_('MULTIPLY', x, 0.7), k.mat_('MULTIPLY', y, 0.7), 0.0), 1.0, 5.0, 0.6)
    col = k.mix(col, (0.10, 0.16, 0.07), k.mat_('MULTIPLY', k.mat_('SUBTRACT', musgo, 0.5, True), 1.4, True))
    n = k.bump(fac, 0.8, 0.04)
    listo(b, col, n, 0.85, 0.0, k)


def metal(m, base, oxido, metalico=0.85, rough=0.55, mancha=0.5, escala=4.0):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    r = k.noise(k.comb(x, y, z), escala, 7.0, 0.6)
    r2 = k.noise(k.comb(k.mat_('MULTIPLY', x, 9.0), k.mat_('MULTIPLY', y, 9.0), k.mat_('MULTIPLY', z, 9.0)), 1.0, 6.0, 0.6)
    col = k.mix((*base, 1), (*oxido, 1), k.mat_('MULTIPLY', k.mat_('SUBTRACT', r, 0.45, True), 2.0 * mancha, True))
    n = k.bump(r2, 0.2, 0.01)
    listo(b, col, n, rough, metalico, k)


def cobre(m):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    r = k.noise(k.comb(k.mat_('MULTIPLY', x, 0.8), k.mat_('MULTIPLY', y, 0.8), k.mat_('MULTIPLY', z, 0.8)), 1.5, 6.0, 0.6)
    col = k.mix((0.34, 0.17, 0.09, 1), (0.10, 0.34, 0.28, 1), k.mat_('MULTIPLY', k.mat_('SUBTRACT', r, 0.38, True), 2.4, True))
    n = k.bump(r, 0.3, 0.02)
    listo(b, col, n, 0.5, 0.6, k)


def cuerda(m):
    nt, b = limpiar(m)
    k = K(nt)
    x, y, z = k.xyz(k.pos())
    r = k.noise(k.comb(k.mat_('MULTIPLY', x, 25.0), k.mat_('MULTIPLY', y, 25.0), k.mat_('MULTIPLY', z, 25.0)), 1.0, 5.0, 0.6)
    col = k.rampa(r, (0.30, 0.22, 0.12), (0.55, 0.45, 0.28))
    listo(b, col, k.bump(r, 0.6, 0.01), 0.95, 0.0, k)


def vidrio(m):
    nt, b = limpiar(m)
    k = K(nt)
    b.inputs['Base Color'].default_value = (0.12, 0.20, 0.22, 1)
    b.inputs['Roughness'].default_value = 0.08
    b.inputs['Metallic'].default_value = 0.0


# ------------------------------------------------------------------ aplicar
PARDO = ((0.22, 0.13, 0.07), (0.15, 0.085, 0.05))
for nombre, fn in (
        ("Tower.", torre_piedra),
        ("SmallBuilding.", lambda m: tablas_verticales(m, (0.26, 0.15, 0.085), (0.17, 0.10, 0.06), (0.03, 0.02, 0.015))),
        ("BuildingWood.", lambda m: madera_general(m, (0.07, 0.045, 0.03), (0.17, 0.10, 0.06), 0.8)),
        ("Roof tiles.", teja),
        ("TowerWoodDecor.", lambda m: madera_general(m, (0.20, 0.07, 0.04), (0.36, 0.14, 0.08), 0.7)),
        ("TowerTop.", cobre),
        ("Rope.", cuerda),
        ("lantern.", lambda m: metal(m, (0.05, 0.05, 0.055), (0.30, 0.11, 0.045), 0.85, 0.5)),
        ("lightFrame.", lambda m: metal(m, (0.55, 0.38, 0.13), (0.30, 0.20, 0.08), 0.95, 0.35, 0.25)),
        ("topLightGlass.", vidrio)):
    m = mat_obtener(nombre)
    if m is None:
        print("TEX falta material", nombre)
        continue
    # los ".001/.002" son copias del mismo material: se rehacen todos
    for mm in [x for x in M if x.name.startswith(nombre)]:
        fn(mm)
        print("TEX", mm.name)

# interior: pisos y paredes
mi = M.get("Interior_Madera_Piso") or M.new("Interior_Madera_Piso")
piso_madera(mi, (0.24, 0.14, 0.08), (0.17, 0.10, 0.06), (0.03, 0.02, 0.015))
mp = M.get("Interior_Madera_Pared") or M.new("Interior_Madera_Pared")
tablas_verticales(mp, (0.22, 0.13, 0.075), (0.15, 0.09, 0.05), (0.03, 0.02, 0.015), 0.22)
mt = M.get("Interior_Piedra_Torre") or M.new("Interior_Piedra_Torre")
piedra_losas(mt, (0.30, 0.29, 0.27), (0.22, 0.21, 0.20), (0.08, 0.08, 0.075))
mc = M.get("Interior_Techo_Madera") or M.new("Interior_Techo_Madera")
piso_madera(mc, (0.14, 0.085, 0.05), (0.10, 0.06, 0.035), (0.02, 0.015, 0.01))


def asignar(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)


for n, mm in (("Faro_Plane", mi), ("Faro_Plane.002", mi), ("Faro_Plane.004", mp), ("Faro_Plane.005", mc), ("Faro_Plane.001", mt)):
    if n in O:
        asignar(O[n], mm)

# puerta de la torre y escalera
mw = M.get("Puerta_Madera") or M.new("Puerta_Madera")
madera_general(mw, (0.09, 0.055, 0.035), (0.20, 0.12, 0.07), 0.75)
for n in ("PuertaVar2_Cuerpo", "PuertaVar2_Tablas", "PuertaVar2_Marco"):
    if n in O:
        asignar(O[n], mw)
mh = M.get("Puerta_Hierro") or M.new("Puerta_Hierro")
metal(mh, (0.05, 0.05, 0.055), (0.28, 0.10, 0.04), 0.85, 0.5)
for n in ("PuertaVar2_Clavos", "PuertaVar2_Herraje"):
    if n in O:
        asignar(O[n], mh)
me_ = M.get("Escalera_Madera")
if me_:
    madera_general(me_, (0.12, 0.07, 0.04), (0.26, 0.16, 0.09), 0.8)
mh2 = M.get("Escalera_Hierro")
if mh2:
    metal(mh2, (0.05, 0.05, 0.055), (0.28, 0.10, 0.04), 0.85, 0.5)

bpy.ops.wm.save_mainfile()
print("TEXTURAS FARO OK")
