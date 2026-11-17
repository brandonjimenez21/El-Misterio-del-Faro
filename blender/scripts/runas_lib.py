# Tallas vikingas dibujadas con numpy: runas (futhark antiguo), bandas de serpiente, motivos (Mjolnir, barco, valknut,
# rueda solar) y petroglifos. Cada imagen es un mapa de PROFUNDIDAD de la talla (blanco = surco hondo, negro = piedra intacta)
# con perfil en V; los materiales de Blender lo usan como relieve + color (surco oscuro con restos de pigmento rojo).
# No depende de bpy: se puede probar con cualquier Python que tenga numpy.
#   python runas_lib.py <carpeta>      -> escribe todas las texturas T_V_*.png en la carpeta
import math, random, zlib, struct, sys, os
import numpy as np

# ------------------------------------------------------------------ futhark antiguo (celda: x 0..0.8, y 0..1)
RUNAS = {
    'f': [[(0.2, 0), (0.2, 1)], [(0.2, 0.45), (0.66, 0.72)], [(0.2, 0.7), (0.66, 0.97)]],
    'u': [[(0.16, 0), (0.16, 1), (0.62, 0.58), (0.62, 0)]],
    'T': [[(0.22, 0), (0.22, 1)], [(0.22, 0.78), (0.62, 0.52), (0.22, 0.26)]],                      # th (thurisaz)
    'a': [[(0.22, 0), (0.22, 1)], [(0.22, 1.0), (0.64, 0.74)], [(0.22, 0.72), (0.64, 0.46)]],
    'r': [[(0.2, 0), (0.2, 1), (0.62, 0.77), (0.2, 0.52), (0.62, 0)]],
    'k': [[(0.6, 0.82), (0.22, 0.5), (0.6, 0.18)]],
    'g': [[(0.12, 0), (0.68, 1)], [(0.12, 1), (0.68, 0)]],
    'w': [[(0.22, 0), (0.22, 1), (0.62, 0.77), (0.22, 0.54)]],
    'h': [[(0.15, 0), (0.15, 1)], [(0.65, 0), (0.65, 1)], [(0.15, 0.66), (0.65, 0.36)]],
    'n': [[(0.4, 0), (0.4, 1)], [(0.14, 0.66), (0.66, 0.4)]],
    'i': [[(0.4, 0), (0.4, 1)]],
    'j': [[(0.5, 0.96), (0.18, 0.73), (0.5, 0.5)], [(0.3, 0.5), (0.62, 0.27), (0.3, 0.04)]],
    'E': [[(0.4, 0), (0.4, 1)], [(0.4, 1), (0.66, 0.78)], [(0.4, 0), (0.14, 0.22)]],                 # eihwaz
    'p': [[(0.2, 0), (0.2, 1)], [(0.2, 1), (0.4, 0.82), (0.62, 1)], [(0.2, 0), (0.4, 0.18), (0.62, 0)]],
    'R': [[(0.4, 0), (0.4, 1)], [(0.4, 0.52), (0.1, 1)], [(0.4, 0.52), (0.7, 1)]],                   # algiz (-R final)
    's': [[(0.6, 1), (0.22, 0.7), (0.6, 0.36), (0.22, 0)]],
    't': [[(0.4, 0), (0.4, 1)], [(0.1, 0.7), (0.4, 1), (0.7, 0.7)]],
    'b': [[(0.2, 0), (0.2, 1), (0.62, 0.76), (0.2, 0.52), (0.62, 0.26), (0.2, 0)]],
    'e': [[(0.15, 0), (0.15, 1), (0.4, 0.72), (0.65, 1), (0.65, 0)]],
    'm': [[(0.15, 0), (0.15, 1), (0.65, 0.55)], [(0.65, 0), (0.65, 1), (0.15, 0.55)]],
    'l': [[(0.26, 0), (0.26, 1), (0.66, 0.68)]],
    'N': [[(0.4, 0.82), (0.66, 0.5), (0.4, 0.18), (0.14, 0.5), (0.4, 0.82)]],                        # ng (ingwaz)
    'd': [[(0.15, 0), (0.15, 1), (0.65, 0), (0.65, 1), (0.15, 0)]],
    'o': [[(0.12, 0), (0.66, 0.6), (0.4, 0.96), (0.14, 0.6), (0.68, 0)]],
    ':': [[(0.4, 0.3), (0.4, 0.34)], [(0.4, 0.66), (0.4, 0.7)]],                                     # separador de palabras
    'x': [[(0.25, 0.35), (0.55, 0.65)], [(0.25, 0.65), (0.55, 0.35)]],                               # separador en cruz
}
FUTHARK = "fuTarkgwhnijEpRstbemlNdo"


def transliterar(texto):
    """texto latino -> claves de RUNAS. 'th' -> T, 'ng' -> N, 'R' (mayuscula) = -R final, espacios -> ':'"""
    out, i = [], 0
    t = texto
    while i < len(t):
        c2 = t[i:i + 2].lower()
        c = t[i]
        if c2 == 'th':
            out.append('T'); i += 2; continue
        if c2 == 'ng':
            out.append('N'); i += 2; continue
        if c == 'R':
            out.append('R')
        elif c in ' :':
            out.append(':')
        else:
            c = c.lower()
            c = {'v': 'w', 'y': 'i', 'c': 'k', 'q': 'k'}.get(c, c)
            if c in RUNAS:
                out.append(c)
        i += 1
    return out


# ------------------------------------------------------------------ lienzo
def ruido_suave(h, w, celda, seed):
    """ruido de baja frecuencia 0..1 (rejilla aleatoria interpolada)"""
    rng = np.random.default_rng(seed)
    gh, gw = int(h / celda) + 3, int(w / celda) + 3
    g = rng.random((gh, gw)).astype(np.float32)
    yy = np.arange(h, dtype=np.float32) / celda
    xx = np.arange(w, dtype=np.float32) / celda
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = yy - y0, xx - x0
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0] * (1 - fx) + g[y0][:, x0 + 1] * fx
    b = g[y0 + 1][:, x0] * (1 - fx) + g[y0 + 1][:, x0 + 1] * fx
    return a * (1 - fy)[:, None] + b * fy[:, None]


class Lienzo:
    """coordenadas en pixeles con el origen ABAJO a la izquierda (y hacia arriba), como las UV"""

    def __init__(self, w, h, seed=1):
        self.w, self.h = int(w), int(h)
        self.a = np.zeros((self.h, self.w), np.float32)
        self.rnd = random.Random(seed)
        self.seed = seed

    def _seg(self, x0, y0, x1, y1, r0, r1, prof):
        r = max(r0, r1)
        xa, xb = int(max(0, min(x0, x1) - r - 2)), int(min(self.w, max(x0, x1) + r + 3))
        ya, yb = int(max(0, min(y0, y1) - r - 2)), int(min(self.h, max(y0, y1) + r + 3))
        if xa >= xb or ya >= yb:
            return
        yy, xx = np.mgrid[ya:yb, xa:xb].astype(np.float32)
        dx, dy = x1 - x0, y1 - y0
        l2 = dx * dx + dy * dy
        t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / l2, 0, 1) if l2 > 1e-9 else np.zeros_like(xx)
        d = np.hypot(xx - (x0 + t * dx), yy - (y0 + t * dy))
        rr = r0 + (r1 - r0) * t
        v = np.clip(1.3 * (1 - d / np.maximum(rr, 0.3)), 0, 1) * prof
        sub = self.a[ya:yb, xa:xb]
        np.maximum(sub, v, out=sub)

    def trazo(self, pts, ancho, prof=1.0, temblor=0.12, afinar=(1.0, 1.0), paso=7.0):
        """surco en V a lo largo de una polilinea. ancho en px (total). temblor: irregularidad de talla a mano (x ancho).
        afinar = (factor de ancho al principio, al final)"""
        pts = [(float(x), float(y)) for x, y in pts]
        # remuestrear
        fino = [pts[0]]
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            n = max(1, int(math.hypot(xb - xa, yb - ya) / paso))
            for k in range(1, n + 1):
                fino.append((xa + (xb - xa) * k / n, ya + (yb - ya) * k / n))
        n = len(fino)
        if n < 2:
            fino.append((fino[0][0] + 0.01, fino[0][1]))
            n = 2
        r = ancho / 2.0
        jit = [0.0] * n
        anch = [1.0] * n
        if temblor > 0:
            v = 0.0
            av = 0.0
            for i in range(n):
                v = v * 0.75 + self.rnd.uniform(-1, 1) * 0.25
                av = av * 0.8 + self.rnd.uniform(-1, 1) * 0.2
                jit[i] = v * temblor * ancho
                anch[i] = 1.0 + av * 1.2 * min(temblor * 4, 1.0) * 0.35
            jit[0] = jit[-1] = 0.0
        out = []
        for i in range(n):
            xa, ya = fino[max(i - 1, 0)]
            xb, yb = fino[min(i + 1, n - 1)]
            l = math.hypot(xb - xa, yb - ya) or 1.0
            nx, ny = -(yb - ya) / l, (xb - xa) / l
            f = i / (n - 1)
            out.append((fino[i][0] + nx * jit[i], fino[i][1] + ny * jit[i], r * anch[i] * (afinar[0] + (afinar[1] - afinar[0]) * f)))
        for (xa, ya, ra), (xb, yb, rb) in zip(out[:-1], out[1:]):
            self._seg(xa, ya, xb, yb, ra, rb, prof)

    def punto(self, x, y, r, prof=1.0):
        self._seg(x, y, x + 0.01, y, r, r, prof)

    def circulo(self, cx, cy, r, ancho, prof=1.0, a0=0.0, a1=2 * math.pi, temblor=0.1):
        n = max(12, int(abs(a1 - a0) * r / 9))
        self.trazo([(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)],
                   ancho, prof, temblor)

    def runa(self, clave, x, y, alto, ang=0.0, ancho=None, prof=1.0, temblor=0.1):
        """runa con el centro de su base en (x, y); 'ang' = direccion de escritura (rad); la runa crece hacia la izquierda de esa direccion"""
        ancho = ancho or alto * 0.11
        ca, sa = math.cos(ang), math.sin(ang)
        for pl in RUNAS[clave]:
            pts = []
            for gx, gy in pl:
                lx, ly = (gx - 0.4) * alto * 0.78, gy * alto
                pts.append((x + lx * ca - ly * sa, y + lx * sa + ly * ca))
            self.trazo(pts, ancho, prof, temblor, paso=max(4.0, alto / 10))

    def texto_curva(self, claves, curva, alto, ancho=None, inicio=0.0, fin=None, lado=1, prof=1.0):
        """escribe runas a lo largo de una polilinea (centradas en ella). lado = 1: la cabeza de la runa a la izquierda del avance."""
        s = [0.0]
        for (xa, ya), (xb, yb) in zip(curva[:-1], curva[1:]):
            s.append(s[-1] + math.hypot(xb - xa, yb - ya))
        total = s[-1]
        fin = total if fin is None else fin
        n = len(claves)
        if n == 0:
            return
        paso = (fin - inicio) / n

        def en(d):
            d = max(0.0, min(total, d))
            k = max(1, min(len(s) - 1, int(np.searchsorted(s, d))))
            f = (d - s[k - 1]) / max(s[k] - s[k - 1], 1e-6)
            xa, ya = curva[k - 1]
            xb, yb = curva[k]
            return xa + (xb - xa) * f, ya + (yb - ya) * f, math.atan2(yb - ya, xb - xa)

        for i, c in enumerate(claves):
            x, y, a = en(inicio + (i + 0.5) * paso)
            nx, ny = -math.sin(a) * lado, math.cos(a) * lado
            bx, by = x - nx * alto / 2, y - ny * alto / 2
            self.runa(c, bx, by, alto, a if lado == 1 else a + math.pi, ancho, prof)

    def desgastar(self, fuerza=0.5, celda=None, picado=0.25):
        """erosion desigual (zonas casi borradas) y picado fino del cincel"""
        celda = celda or self.w / 6.0
        n1 = ruido_suave(self.h, self.w, celda, self.seed + 11)
        n2 = ruido_suave(self.h, self.w, celda / 3.5, self.seed + 23)
        m = np.clip((n1 * 0.65 + n2 * 0.35 - 0.28) * 2.6, 0, 1)
        self.a *= (1 - fuerza) + fuerza * m
        if picado > 0:
            rng = np.random.default_rng(self.seed + 5)
            g = rng.random((self.h // 3 + 1, self.w // 3 + 1)).astype(np.float32)
            g = np.kron(g, np.ones((3, 3), np.float32))[:self.h, :self.w]
            self.a *= 1 - picado * g

    def guardar(self, ruta):
        a8 = (np.clip(self.a[::-1], 0, 1) * 255 + 0.5).astype(np.uint8)
        h, w = a8.shape
        crudo = b''.join(b'\x00' + a8[i].tobytes() for i in range(h))

        def trozo(t, d):
            return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
        with open(ruta, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n' + trozo(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0))
                    + trozo(b'IDAT', zlib.compress(crudo, 6)) + trozo(b'IEND', b''))


# ------------------------------------------------------------------ geometria auxiliar
def desplazar(curva, d):
    """polilinea paralela a distancia d (positivo = a la izquierda del avance); d puede ser lista"""
    out = []
    n = len(curva)
    for i in range(n):
        xa, ya = curva[max(i - 1, 0)]
        xb, yb = curva[min(i + 1, n - 1)]
        l = math.hypot(xb - xa, yb - ya) or 1.0
        dd = d[i] if isinstance(d, (list, tuple)) else d
        out.append((curva[i][0] - (yb - ya) / l * dd, curva[i][1] + (xb - xa) / l * dd))
    return out


def remuestrear(curva, paso):
    out = [curva[0]]
    for (xa, ya), (xb, yb) in zip(curva[:-1], curva[1:]):
        n = max(1, int(math.hypot(xb - xa, yb - ya) / paso))
        for k in range(1, n + 1):
            out.append((xa + (xb - xa) * k / n, ya + (yb - ya) * k / n))
    return out


def largo(curva):
    return sum(math.hypot(xb - xa, yb - ya) for (xa, ya), (xb, yb) in zip(curva[:-1], curva[1:]))


def rizo(p, ang, radio, giro, vueltas=0.6, encoge=0.55, n=26):
    """espiral que sale de p en direccion ang girando hacia 'giro' (+1 izquierda, -1 derecha)"""
    pts = [p]
    x, y = p
    a = ang
    r = radio
    paso_a = vueltas * 2 * math.pi / n
    for k in range(n):
        l = r * paso_a
        x += math.cos(a) * l
        y += math.sin(a) * l
        pts.append((x, y))
        a += giro * paso_a
        r *= encoge ** (1.0 / n * 2.2)
    return pts


# ------------------------------------------------------------------ motivos (centro cx, cy; tamano = alto total en px)
def mjolnir(L, cx, cy, t, g):
    P = lambda x, y: (cx + x * t, cy + (y - 0.5) * t)
    L.trazo([P(*p) for p in [(-0.07, 0.98), (0.07, 0.98), (0.09, 0.44), (0.40, 0.42), (0.42, 0.14), (0.0, 0.0), (-0.42, 0.14), (-0.40, 0.42), (-0.09, 0.44), (-0.07, 0.98)]], g)
    L.circulo(*P(0, 1.04), 0.06 * t, g * 0.8)
    L.trazo([P(-0.3, 0.3), P(0.3, 0.3)], g * 0.7)
    L.punto(*P(-0.16, 0.2), g * 0.9)
    L.punto(*P(0.16, 0.2), g * 0.9)
    L.trazo([P(0, 0.44), P(0, 0.3)], g * 0.6)


def valknut(L, cx, cy, t, g):
    R = t * 0.36
    for k in range(3):
        a = math.pi / 2 + k * 2 * math.pi / 3
        ox, oy = cx + math.cos(a) * t * 0.17, cy + math.sin(a) * t * 0.17
        tri = [(ox + R * math.cos(math.pi / 2 + j * 2 * math.pi / 3), oy + R * math.sin(math.pi / 2 + j * 2 * math.pi / 3)) for j in range(4)]
        L.trazo(tri, g)


def rueda_solar(L, cx, cy, t, g, rayos=True):
    r = t * 0.36
    L.circulo(cx, cy, r, g)
    L.trazo([(cx - r, cy), (cx + r, cy)], g * 0.9)
    L.trazo([(cx, cy - r), (cx, cy + r)], g * 0.9)
    if rayos:
        for k in range(12):
            a = k * math.pi / 6 + 0.26
            L.trazo([(cx + math.cos(a) * r * 1.14, cy + math.sin(a) * r * 1.14), (cx + math.cos(a) * r * 1.36, cy + math.sin(a) * r * 1.36)], g * 0.8)


def espiral(L, cx, cy, t, g, giro=1, vueltas=2.6):
    n = int(40 * vueltas)
    pts = []
    for k in range(n + 1):
        a = giro * k / n * vueltas * 2 * math.pi
        r = t * 0.5 * (0.06 + 0.94 * k / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    L.trazo(pts, g)


def barco_vikingo(L, cx, cy, t, g):
    """drakkar de perfil: casco curvo con roda y codaste en espiral, mastil, vela a rombos, escudos y remos. t = eslora en px"""
    P = lambda x, y: (cx + x * t, cy + y * t)
    casco = [P(-0.5 + k / 30, -0.05 - 0.13 * math.sin(math.pi * k / 30) ** 0.8) for k in range(31)]
    L.trazo(casco, g)
    borda = [P(-0.42 + 0.84 * k / 30, 0.02 - 0.07 * math.sin(math.pi * k / 30)) for k in range(31)]
    L.trazo(borda, g * 0.8)
    # roda (proa, derecha) con cabeza de dragon y codaste (popa) en espiral
    L.trazo([P(0.5, -0.05), P(0.53, 0.06), P(0.52, 0.2), P(0.48, 0.3)] + rizo(P(0.48, 0.3), math.radians(110), t * 0.05, 1, 0.55, 0.6, 14), g)
    L.trazo([P(0.52, 0.2), P(0.6, 0.22), P(0.57, 0.17)], g * 0.7)          # mandibula
    L.trazo([P(-0.5, -0.05), P(-0.53, 0.06), P(-0.52, 0.2)] + rizo(P(-0.52, 0.2), math.radians(80), t * 0.06, 1, 0.75, 0.5, 18), g)
    # mastil y vela
    L.trazo([P(0, -0.02), P(0, 0.52)], g * 0.9)
    L.trazo([P(-0.27, 0.48), P(0.27, 0.48), P(0.25, 0.14), P(-0.25, 0.14), P(-0.27, 0.48)], g * 0.8)
    for k in range(-3, 4):
        L.trazo([P(k * 0.09 - 0.17, 0.14), P(k * 0.09 + 0.17, 0.48)], g * 0.45, 0.7)
        L.trazo([P(k * 0.09 + 0.17, 0.14), P(k * 0.09 - 0.17, 0.48)], g * 0.45, 0.7)
    L.trazo([P(0, 0.52), P(0.47, 0.3)], g * 0.4, 0.7)
    L.trazo([P(0, 0.52), P(-0.5, 0.2)], g * 0.4, 0.7)
    for k in range(7):
        x = -0.33 + k * 0.11
        y = -0.03 - 0.07 * math.sin(math.pi * (x + 0.42) / 0.84)
        L.circulo(*P(x, y), t * 0.035, g * 0.6)
        L.trazo([P(x, y - 0.06), P(x - 0.05, y - 0.2)], g * 0.4, 0.7)


def barca_petroglifo(L, cx, cy, t, g, tripulantes=8, giro=0.0):
    """barca de la Edad de Bronce: quilla que se alarga en dos proas curvas, borda y rayitas de tripulantes"""
    ca, sa = math.cos(giro), math.sin(giro)
    P = lambda x, y: (cx + (x * ca - y * sa) * t, cy + (x * sa + y * ca) * t)
    quilla = [P(-0.62, 0.02)] + [P(-0.5 + k / 20, -0.04 * math.sin(math.pi * k / 20)) for k in range(21)]
    L.trazo(quilla + [P(0.56, 0.08), P(0.6, 0.2)] + rizo(P(0.6, 0.2), giro + math.radians(100), t * 0.05, 1, 0.5, 0.6, 12), g)
    L.trazo([P(-0.45, 0.1)] + [P(-0.4 + 0.8 * k / 20, 0.09 - 0.03 * math.sin(math.pi * k / 20)) for k in range(21)] + [P(0.47, 0.16)], g * 0.8)
    L.trazo([P(-0.45, 0.1), P(-0.5, 0.22), P(-0.47, 0.3)], g * 0.8)
    for k in range(tripulantes):
        x = -0.34 + 0.68 * k / max(tripulantes - 1, 1)
        L.trazo([P(x, 0.1), P(x + 0.01, 0.2)], g * 0.7)
    for k in range(5):
        x = -0.4 + 0.8 * k / 4
        L.trazo([P(x, 0.0), P(x, 0.07)], g * 0.5, 0.8)


def figura(L, cx, cy, t, g, arma=None, brazos=1):
    """figura humana de palotes (t = alto). brazos = 1 alzados, 0 abiertos"""
    P = lambda x, y: (cx + x * t, cy + y * t)
    L.trazo([P(0, 0.42), P(0, 0.8)], g * 1.3)
    L.circulo(*P(0, 0.89), 0.075 * t, g)
    L.trazo([P(-0.14, 0.0), P(-0.1, 0.22), P(0, 0.42), P(0.1, 0.22), P(0.14, 0.0)], g)
    if brazos:
        L.trazo([P(-0.24, 0.92), P(-0.18, 0.72), P(0, 0.7), P(0.18, 0.72), P(0.24, 0.92)], g)
    else:
        L.trazo([P(-0.3, 0.62), P(0, 0.7), P(0.3, 0.62)], g)
    if arma == 'lanza':
        L.trazo([P(0.25, 0.1), P(0.25, 1.12)], g * 0.8)
        L.trazo([P(0.21, 1.02), P(0.25, 1.14), P(0.29, 1.02)], g * 0.8)
    elif arma == 'hacha':
        L.trazo([P(0.24, 0.92), P(0.3, 1.12)], g * 0.8)
        L.trazo([P(0.3, 1.12), P(0.42, 1.1), P(0.4, 0.98), P(0.28, 1.04)], g * 0.8)
    elif arma == 'escudo':
        L.circulo(*P(-0.26, 0.62), 0.12 * t, g * 0.8)
        L.punto(*P(-0.26, 0.62), g * 0.8)


def huella(L, cx, cy, t, g, ang=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for k in range(25):
        a = k / 24 * 2 * math.pi
        x, y = 0.2 * math.cos(a) * (1.0 + 0.25 * math.sin(a)), 0.5 * math.sin(a)
        pts.append((cx + (x * ca - y * sa) * t, cy + (x * sa + y * ca) * t))
    L.trazo(pts, g)


# ------------------------------------------------------------------ texturas completas
TEXTOS = {
    # "Ulf levanto esta piedra por su hermano. El mar se lo llevo."
    'memorial': "ulfR raisti stain thansi aftiR bruthur sin x hafit tok han",
    # "Mientras el faro (viti) arda, el draugr (el ahogado que vuelve) duerme."
    'faro': "methan witi brennR x sefR draugR",
    # "El mar da, el mar quita."
    'mar': "haf gefR x haf tekR",
    # "No sigas adelante."
    'aviso': "gak aigi lengra",
    # "Nueve noches colgo (Odin)... nueve hombres dio (la isla) al mar."
    'nueve': "niu naetr x niu menn gaf haf",
}


def contorno_piedra(ancho, alto, hombro=0.62, asim=0.0, p=2.2, n=120):
    """silueta de la losa en metros (x centrado, z desde el suelo): [(x, z)] de abajo-izquierda, por arriba, hasta abajo-derecha"""
    zh = alto * hombro
    izq, der = [], []
    for k in range(n + 1):
        z = alto * k / n
        estrecha = 1.0 - 0.10 * (z / alto)                 # algo mas estrecha arriba
        ensancha = 1.0 - 0.07 * max(0.0, 1 - z / (alto * 0.25)) ** 2
        if z <= zh:
            a, xc = ancho / 2 * estrecha * ensancha, 0.0
        else:
            f = (z - zh) / (alto - zh)
            a = ancho / 2 * estrecha * max(0.0, 1 - f ** p) ** (1 / p)
            xc = asim * f * f * (3 - 2 * f)
        izq.append((xc - a, z))
        der.append((xc + a, z))
    return izq + der[::-1]


def tex_piedra_runica(ruta, ancho, alto, texto, motivo, seed, hombro=0.62, asim=0.0, px_m=880.0, banda=0.15, margen=0.085,
                      desgaste=0.5, segundo=None):
    """cara de una piedra runica: serpiente en arco con la inscripcion dentro y un motivo en el centro.
    La imagen cubre x en [-ancho*0.54, ancho*0.54] y z en [0, alto*1.03] (misma proyeccion que usa el material)."""
    W, H = int(ancho * 1.08 * px_m), int(alto * 1.03 * px_m)
    L = Lienzo(W, H, seed)
    X = lambda x: (x + ancho * 0.54) * px_m
    Z = lambda z: z * px_m
    cont = contorno_piedra(ancho, alto, hombro, asim)
    cont_px = [(X(x), Z(z)) for x, z in cont]
    # linea central de la banda: la silueta de una losa mas pequena (metida hacia dentro), desde cierta altura del suelo
    z_ini = 0.36
    ins = margen + banda / 2
    zh = alto * hombro
    cont_in = contorno_piedra(ancho - 2 * ins, alto - ins, zh / (alto - ins), asim * 0.8, 2.0, 160)
    dentro = remuestrear([(X(x), Z(z)) for x, z in cont_in if z > z_ini], 6)
    for _ in range(4):
        dentro = [dentro[0]] + [((a[0] + 2 * b[0] + c[0]) / 4, (a[1] + 2 * b[1] + c[1]) / 4) for a, b, c in zip(dentro[:-2], dentro[1:-1], dentro[2:])] + [dentro[-1]]
    # cola (inicio, abajo a la izquierda) y cabeza (final, abajo a la derecha) se curvan hacia dentro
    a0 = math.atan2(dentro[0][1] - dentro[3][1], dentro[0][0] - dentro[3][0])
    cola = rizo(dentro[0], a0, banda * px_m * 1.05, 1, 0.62, 0.5, 22)[1:]
    a1 = math.atan2(dentro[-1][1] - dentro[-4][1], dentro[-1][0] - dentro[-4][0])
    cabeza = rizo(dentro[-1], a1, banda * px_m * 2.4, -1, 0.2, 0.95, 12)[1:]
    centro = cola[::-1] + dentro + cabeza
    centro = remuestrear(centro, 5)
    n = len(centro)
    nc, nh = int(largo(cola) / 5), int(largo(cabeza) / 5)
    medio = []
    for i in range(n):
        if i < nc:
            f = (i / max(nc, 1)) ** 0.7
            medio.append(banda * px_m / 2 * (0.08 + 0.92 * f))
        elif i > n - nh:
            f = (i - (n - nh)) / max(nh, 1)
            medio.append(banda * px_m / 2 * (1.0 + 0.35 * math.sin(math.pi * min(f * 1.2, 1.0)) - 0.92 * max(0.0, f - 0.6) / 0.4))
        else:
            medio.append(banda * px_m / 2)
    g = 0.011 * px_m
    L.trazo(desplazar(centro, medio), g, temblor=0.08)
    L.trazo(desplazar(centro, [-m for m in medio]), g, temblor=0.08)
    # ojo y lengua de la serpiente
    ic = n - int(nh * 0.5)
    L.punto(centro[ic][0], centro[ic][1], g * 1.2)
    L.circulo(centro[ic][0], centro[ic][1], g * 2.4, g * 0.6)
    ang_f = math.atan2(centro[-1][1] - centro[-4][1], centro[-1][0] - centro[-4][0])
    L.trazo([centro[-1], (centro[-1][0] + math.cos(ang_f + 0.4) * g * 5, centro[-1][1] + math.sin(ang_f + 0.4) * g * 5)], g * 0.6)
    L.trazo([centro[-1], (centro[-1][0] + math.cos(ang_f - 0.4) * g * 5, centro[-1][1] + math.sin(ang_f - 0.4) * g * 5)], g * 0.6)
    # inscripcion dentro de la banda (entre la cola y la cabeza)
    claves = transliterar(texto)
    tramo = centro[nc + 4:n - nh - 4]
    alto_r = banda * px_m * 0.62
    cabe = int(largo(tramo) / (alto_r * 0.72))
    while len(claves) < cabe - 6:
        claves = claves + ['x'] + transliterar(texto)
    claves = claves[:cabe]
    L.texto_curva(claves, tramo, alto_r, alto_r * 0.115, lado=-1)
    # motivo central y cazoletas
    cx, cz = X(asim * 0.3), Z(alto * (hombro + 0.02))
    t = (ancho - 2 * (margen + banda) - 0.12) * px_m
    if motivo == 'mjolnir':
        mjolnir(L, cx, cz, t * 0.95, g)
    elif motivo == 'barco':
        barco_vikingo(L, cx, cz - t * 0.1, t * 0.9, g * 0.9)
    elif motivo == 'valknut':
        valknut(L, cx, cz, t * 0.95, g)
    elif motivo == 'sol':
        rueda_solar(L, cx, cz, t * 0.85, g)
    if segundo:
        # segunda inscripcion en vertical por el centro, bajo el motivo
        claves2 = transliterar(segundo)
        alto2 = alto_r * 1.05
        z1 = cz - t * 0.62
        z0 = max(Z(0.5), z1 - len(claves2) * alto2 * 0.74)
        claves2 = claves2[:int((z1 - z0) / (alto2 * 0.74))]
        linea = [(cx, z1 - (z1 - z0) * k / 20) for k in range(21)]
        L.trazo([(cx - alto2 * 0.62, z1 + 4), (cx - alto2 * 0.62, z0 - 4)], g * 0.8)
        L.trazo([(cx + alto2 * 0.62, z1 + 4), (cx + alto2 * 0.62, z0 - 4)], g * 0.8)
        L.texto_curva(claves2, linea, alto2, alto2 * 0.115, lado=1)
    L.desgastar(desgaste)
    L.guardar(ruta)
    return W, H


def tex_banda(ruta, texto, seed, W=4096, H=512, nudos=False):
    """banda horizontal que se repite (para rodear un poste): dos lineas y runas entre ellas"""
    L = Lienzo(W, H, seed)
    g = H * 0.03
    for y in (H * 0.13, H * 0.87):
        L.trazo([(0, y), (W, y)], g, temblor=0.0)
        L.trazo([(0, y + (g * 1.9 if y < H / 2 else -g * 1.9)), (W, y + (g * 1.9 if y < H / 2 else -g * 1.9))], g * 0.5, 0.8, temblor=0.0)
    alto = H * 0.5
    if nudos:
        # trenza de dos cabos (entrelazado sencillo)
        n = 16
        for fase in (0.0, math.pi):
            pts = [(W * k / (n * 24), H / 2 + math.sin(2 * math.pi * k / 24 * 1.0 + fase) * H * 0.23) for k in range(n * 24 + 1)]
            L.trazo(pts, g * 1.5, temblor=0.0)
            L.trazo([(x, y + g * 2.6) for x, y in pts], g * 0.6, 0.8, temblor=0.0)
            L.trazo([(x, y - g * 2.6) for x, y in pts], g * 0.6, 0.8, temblor=0.0)
        for k in range(n * 2):
            L.punto(W * (k + 0.5) / (n * 2), H / 2, g * 1.1)
    else:
        claves = transliterar(texto)
        cabe = int(round(W / (alto * 0.74)))
        base = list(claves)
        while len(claves) < cabe:
            claves = claves + ['x'] + base
        claves = claves[:cabe]
        paso = W / cabe
        for i, c in enumerate(claves):
            L.runa(c, (i + 0.5) * paso, H / 2 - alto / 2, alto, 0.0, alto * 0.11)
    L.desgastar(0.4, celda=H * 0.9, picado=0.2)
    # que siga repitiendo: funde el desgaste de los dos extremos
    m = 48
    f = np.linspace(0, 1, m, dtype=np.float32)[None, :]
    mezcla = L.a[:, :m] * f + L.a[:, -m:] * (1 - f)
    L.a[:, :m] = np.maximum(L.a[:, :m] * f, mezcla * (1 - f) + L.a[:, :m] * f)
    L.guardar(ruta)


def tex_anillo(ruta, texto, seed, S=2048):
    """serpiente del mundo (Jormungandr) que se muerde la cola, con la inscripcion dentro y un valknut en el centro"""
    L = Lienzo(S, S, seed)
    c = S / 2
    g = S * 0.011
    r_ext, r_int = S * 0.44, S * 0.33
    a_boca = -math.pi / 2
    hueco = 0.5
    L.circulo(c, c, r_ext, g, a0=a_boca + hueco, a1=a_boca + 2 * math.pi - 0.04)
    L.circulo(c, c, r_int, g, a0=a_boca + hueco, a1=a_boca + 2 * math.pi - 0.04)
    # cabeza (se abre y muerde) y cola (se afila dentro de la boca)
    rm = (r_ext + r_int) / 2
    P = lambda a, r: (c + r * math.cos(a), c + r * math.sin(a))
    a_c = a_boca + 2 * math.pi - 0.04
    # cabeza: los dos bordes se abren y se cierran en el hocico, que muerde la cola
    L.trazo([P(a_c - 0.02, r_ext), P(a_c + 0.08, r_ext + S * 0.016), P(a_c + 0.2, r_ext + S * 0.006), P(a_c + 0.3, rm + S * 0.022)], g, temblor=0.05)
    L.trazo([P(a_c - 0.02, r_int), P(a_c + 0.08, r_int - S * 0.016), P(a_c + 0.2, r_int - S * 0.006), P(a_c + 0.3, rm - S * 0.022)], g, temblor=0.05)
    L.punto(*P(a_c + 0.07, rm + S * 0.022), g * 1.3)
    L.circulo(*P(a_c + 0.07, rm + S * 0.022), g * 2.6, g * 0.6)
    # cola: se afila y entra en la boca
    L.trazo([P(a_boca + hueco, r_ext), P(a_boca + 0.36, rm + S * 0.014), P(a_boca + 0.2, rm)], g, afinar=(1.0, 0.5), temblor=0.05)
    L.trazo([P(a_boca + hueco, r_int), P(a_boca + 0.36, rm - S * 0.014), P(a_boca + 0.2, rm)], g, afinar=(1.0, 0.5), temblor=0.05)
    # escamas: rayitas en el borde exterior
    for k in range(70):
        a = a_boca + 0.55 + (2 * math.pi - 0.7) * k / 69
        L.trazo([P(a, r_ext + g * 1.8), P(a + 0.025, r_ext + g * 4.0)], g * 0.55, 0.75)
    # inscripcion (se lee desde dentro: el pie de las runas hacia el centro)
    claves = transliterar(texto)
    alto = (r_ext - r_int) * 0.52
    arco = [P(a_boca + 2 * math.pi - 0.16 - (2 * math.pi - 0.78) * k / 240, rm) for k in range(241)]
    cabe = int(largo(arco) / (alto * 0.78))
    base = list(claves)
    while len(claves) < cabe - 3:
        claves = claves + ['x'] + base
    claves = claves[:cabe]
    L.texto_curva(claves, arco, alto, alto * 0.12, lado=-1)
    valknut(L, c, c - S * 0.01, S * 0.5, g * 1.1)
    for k in range(9):          # nueve cazoletas (los nueve mundos)
        a = math.pi / 2 + k * 2 * math.pi / 9
        L.punto(*P(a, r_int - S * 0.04), g * 1.5)
    L.desgastar(0.45)
    L.guardar(ruta)


def tex_petroglifos(ruta, seed, W=2048, H=1280, texto=None):
    """panel de grabados antiguos (barcas, rueda solar, figuras, espirales, huellas, cazoletas) y, anadida despues por los
    vikingos, una linea de runas abajo"""
    L = Lienzo(W, H, seed)
    g = W * 0.0075
    r = L.rnd
    barca_petroglifo(L, W * 0.3, H * 0.74, W * 0.36, g, 9, 0.05)
    barca_petroglifo(L, W * 0.72, H * 0.6, W * 0.3, g, 7, -0.06)
    barca_petroglifo(L, W * 0.4, H * 0.42, W * 0.24, g * 0.9, 5, 0.1)
    rueda_solar(L, W * 0.78, H * 0.82, H * 0.3, g)
    espiral(L, W * 0.12, H * 0.5, H * 0.2, g, 1)
    espiral(L, W * 0.9, H * 0.4, H * 0.14, g, -1, 2.0)
    figura(L, W * 0.57, H * 0.3, H * 0.2, g, 'lanza')
    figura(L, W * 0.66, H * 0.29, H * 0.18, g, 'hacha')
    figura(L, W * 0.2, H * 0.27, H * 0.17, g, 'escudo', 0)
    figura(L, W * 0.58, H * 0.79, H * 0.13, g * 0.8, None)
    figura(L, W * 0.84, H * 0.27, H * 0.22, g * 1.1, None)       # la figura grande, apartada, con los brazos alzados
    huella(L, W * 0.06, H * 0.3, H * 0.1, g * 0.8, 0.3)
    huella(L, W * 0.1, H * 0.34, H * 0.1, g * 0.8, 0.2)
    for _ in range(26):
        L.punto(r.uniform(0.04, 0.96) * W, r.uniform(0.2, 0.95) * H, g * r.uniform(1.2, 2.2), r.uniform(0.6, 1.0))
    if texto:
        claves = transliterar(texto)
        alto = H * 0.085
        x0, x1 = W * 0.08, W * 0.92
        cabe = int((x1 - x0) / (alto * 0.8))
        base = list(claves)
        while len(claves) < cabe - 3:
            claves = claves + ['x'] + base
        claves = claves[:cabe]
        L.trazo([(x0 - 10, H * 0.045), (x1 + 10, H * 0.045)], g * 0.8)
        L.trazo([(x0 - 10, H * 0.155), (x1 + 10, H * 0.155)], g * 0.8)
        L.texto_curva(claves, [(x0 + (x1 - x0) * k / 40, H * 0.1) for k in range(41)], alto, alto * 0.12, lado=1)
    L.desgastar(0.55, picado=0.3)
    L.guardar(ruta)


# piedras runicas: nombre -> (ancho, alto, texto, motivo, hombro, asimetria, semilla, segundo texto)
PIEDRAS = {
    'Sendero': (1.05, 2.25, TEXTOS['memorial'], 'barco', 0.64, 0.05, 11, None),
    'Barco': (1.35, 3.1, TEXTOS['faro'], 'mjolnir', 0.66, -0.08, 23, TEXTOS['nueve']),
    'Faro': (0.95, 1.9, TEXTOS['mar'], 'valknut', 0.6, 0.04, 37, None),
    'Caida': (1.1, 2.4, TEXTOS['memorial'], 'sol', 0.62, 0.0, 51, None),
}


def generar_todo(carpeta):
    os.makedirs(carpeta, exist_ok=True)
    for nombre, (an, al, tx, mo, ho, asi, se, seg) in PIEDRAS.items():
        w, h = tex_piedra_runica(os.path.join(carpeta, "T_V_Piedra_%s.png" % nombre), an, al, tx, mo, se, ho, asi, segundo=seg,
                                 desgaste=0.62 if nombre == 'Caida' else 0.48)
        print("TALLA", nombre, w, h)
    tex_banda(os.path.join(carpeta, "T_V_Banda_Futhark.png"), FUTHARK, 3)
    tex_banda(os.path.join(carpeta, "T_V_Banda_Faro.png"), TEXTOS['faro'], 5)
    tex_banda(os.path.join(carpeta, "T_V_Banda_Nudos.png"), "", 7, nudos=True)
    tex_anillo(os.path.join(carpeta, "T_V_Anillo_Serpiente.png"), TEXTOS['aviso'], 9)
    tex_petroglifos(os.path.join(carpeta, "T_V_Petroglifos.png"), 13, texto=TEXTOS['mar'])
    print("TALLAS OK")


if __name__ == "__main__":
    generar_todo(sys.argv[1] if len(sys.argv) > 1 else ".")
