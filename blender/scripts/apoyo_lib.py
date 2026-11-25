# Vuelve a apoyar en el terreno las piezas sueltas (rocas, guijarros, ramas) de unos objetos cuando el terreno cambia:
# cada pieza sube o baja lo mismo que cambio el suelo debajo de ella. Lo usan relieve_terreno.py y pasto_y_rocas.py.
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def arbol(malla, matriz):
    """BVH de una malla, en coordenadas del mundo"""
    b = bmesh.new()
    b.from_mesh(malla)
    b.transform(matriz)
    t = BVHTree.FromBMesh(b)
    b.free()
    return t


def reapoyar(objetos, antes, ahora):
    """mueve en vertical cada pieza suelta de 'objetos' segun la diferencia entre el terreno 'antes' y 'ahora' (BVH). Devuelve cuantas movio."""
    abajo = Vector((0, 0, -1))
    hecho = 0
    for o in objetos:
        b = bmesh.new()
        b.from_mesh(o.data)
        pend = set(b.verts)
        cambio = False
        while pend:
            pieza, cola = [], [pend.pop()]
            while cola:
                v = cola.pop()
                pieza.append(v)
                for e in v.link_edges:
                    w = e.other_vert(v)
                    if w in pend:
                        pend.discard(w)
                        cola.append(w)
            cx = sum(v.co.x for v in pieza) / len(pieza)
            cy = sum(v.co.y for v in pieza) / len(pieza)
            zmin = min(v.co.z for v in pieza)
            r0 = antes.ray_cast(Vector((cx, cy, zmin + 3.0)), abajo)
            r1 = ahora.ray_cast(Vector((cx, cy, zmin + 4.0)), abajo)
            if r0[0] is None or r1[0] is None:
                continue
            dz = r1[0].z - r0[0].z
            if 0.005 < abs(dz) < 1.5:
                for v in pieza:
                    v.co.z += dz
                hecho += 1
                cambio = True
        if cambio:
            b.to_mesh(o.data)
        b.free()
    return hecho
