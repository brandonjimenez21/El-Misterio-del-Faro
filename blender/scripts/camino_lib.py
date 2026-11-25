# Camino principal de la isla (el unico pintado como tierra): forma compartida por
#   relieve_terreno.py  (cubeta pisada, hombros, baches donde se junta el agua, UV "Camino" para el shader)
#   pasto_y_rocas.py    (las matas de hierba empiezan justo donde acaba la tierra, y ralean hacia el borde)
# Asi el borde de tierra, el borde de la hierba y los charcos coinciden entre si (antes cada uno iba por su lado).
import math
import numpy as np
from mathutils import Vector, noise

CAMINO = [(0.0, -34.6), (0.5, -21.6), (1.0, -6.0), (2.1, 9.6), (1.0, 25.2), (-1.0, 40.8), (-1.9, 51.8), (3.9, 62.2),
          (7.1, 73.3), (11.7, 83.7), (14.3, 92.8), (11.0, 98.6), (6.0, 99.7)]
ALCANCE = 6.0          # la UV "Camino" guarda la distancia al eje hasta aqui (m)
BORDE_TIERRA = 1.3     # a esta distancia (ya ondulada) se acaba la tierra y empiezan las matas


def suave(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def dist_eje(x, y):
    """distancia exacta (m) al eje del camino principal"""
    m = 1e9
    for (ax, ay), (bx, by) in zip(CAMINO[:-1], CAMINO[1:]):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        m = min(m, math.hypot(x - ax - dx * t, y - ay - dy * t))
    return m


def dist_eje_np(X, Y):
    """igual que dist_eje, para arrays de numpy"""
    m = np.full(np.shape(X), 1e9)
    for (ax, ay), (bx, by) in zip(CAMINO[:-1], CAMINO[1:]):
        dx, dy = bx - ax, by - ay
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
        m = np.minimum(m, np.hypot(X - ax - dx * t, Y - ay - dy * t))
    return m


def ondulacion(x, y):
    """el borde del camino no es una linea recta: se ensancha y se estrecha (+-0.4 m) cada pocos metros"""
    return 0.38 * noise.noise(Vector((x / 2.8, y / 2.8, 8.3))) + 0.16 * noise.noise(Vector((x / 1.4 + 20.0, y / 1.4, 2.9)))


def dist_borde(x, y, d=None):
    """distancia al eje con el borde ondulado (la que usan la tierra, la hierba y la cubeta)"""
    if d is None:
        d = dist_eje(x, y)
    return max(0.0, d + ondulacion(x, y)) if d < ALCANCE + 1.0 else d


def cuenca(x, y):
    """0..1: baches del camino donde se junta el agua de lluvia (manchas de 1-2 m separadas entre si)"""
    n = noise.noise(Vector((x / 1.9, y / 1.9, 4.4))) + 0.35 * noise.noise(Vector((x / 0.8 + 13.0, y / 0.8, 6.1)))
    return suave(0.0, 0.48, n)
