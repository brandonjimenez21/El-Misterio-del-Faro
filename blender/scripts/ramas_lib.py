# Librería común para ramas/troncos con UV en "unidades de tile" (v = metros recorridos / TILE; u da la vuelta entera al tronco).
# Con eso la textura de detalle de corteza (T_Det_Corteza) se repite cada TILE metros y no se estira, sea cual sea el grosor.
import math
from mathutils import Vector

TILE = 0.6


def tubo_curvo(bm, pts, radios, seg=8, tapa_base=False, v0=0.0, tile=TILE):
    """tubo siguiendo la polilinea pts con radios por punto. Devuelve la longitud recorrida."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    if n < 2:
        return 0.0
    tang = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        t = (b - a)
        tang.append(t.normalized() if t.length > 1e-6 else Vector((0, 0, 1)))
    ref = Vector((0, 0, 1)) if abs(tang[0].z) < 0.95 else Vector((1, 0, 0))
    x = tang[0].cross(ref).normalized()
    anillos = []
    larg = [0.0]
    for i in range(1, n):
        larg.append(larg[-1] + (pts[i] - pts[i - 1]).length)
    for i in range(n):
        x = (x - tang[i] * x.dot(tang[i]))
        x = x.normalized() if x.length > 1e-6 else tang[i].orthogonal().normalized()
        y = tang[i].cross(x)
        r = radios[i]
        anillos.append([bm.verts.new(pts[i] + (x * math.cos(2 * math.pi * k / seg) + y * math.sin(2 * math.pi * k / seg)) * r) for k in range(seg)])
    nU = max(1, round(2 * math.pi * (sum(radios) / n) / tile))
    uvl = bm.loops.layers.uv.verify()
    for i in range(n - 1):
        va = v0 + larg[i] / tile
        vb = v0 + larg[i + 1] / tile
        for k in range(seg):
            j = (k + 1) % seg
            f = bm.faces.new((anillos[i][k], anillos[i][j], anillos[i + 1][j], anillos[i + 1][k]))
            f.smooth = True
            uk = k / seg * nU
            uj = (k + 1) / seg * nU
            for lp, uv in zip(f.loops, ((uk, va), (uj, va), (uj, vb), (uk, vb))):
                lp[uvl].uv = uv
    if tapa_base:
        f = bm.faces.new(anillos[0][::-1])
        for lp in f.loops:
            lp[uvl].uv = (0.5, v0)
    return larg[-1]
