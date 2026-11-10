# Trae las paredes interiores/pisos (Plane*) y la puerta (PuertaVar2_*) de Lighthouse.blend (companero)
# a la coleccion Faro_Cabana, como hijos de Faro_Cabana_Raiz (misma escala/posicion/giro que nuestro faro).
import bpy, os
RAIZ = bpy.data.objects["Faro_Cabana_Raiz"]
COL = bpy.data.collections["Faro_Cabana"]
ruta = os.path.join(os.path.dirname(bpy.data.filepath), "Lighthouse.blend")
nombres = ["Plane", "Plane.001", "Plane.002", "Plane.003", "Plane.004", "Plane.005",
           "PuertaVar2_Clavos", "PuertaVar2_Cuerpo", "PuertaVar2_Herraje", "PuertaVar2_Marco", "PuertaVar2_Tablas"]
nombres = [n for n in nombres if n not in bpy.data.objects]
with bpy.data.libraries.load(ruta, link=False) as (src, dst):
    dst.objects = [n for n in nombres if n in src.objects]
for o in dst.objects:
    if o is None:
        continue
    o.name = "Faro_" + o.name if o.name.startswith("Plane") else o.name
    COL.objects.link(o)
    o.parent = RAIZ
    o.matrix_parent_inverse.identity()
    print("IMPORTADO", o.name, tuple(round(v, 2) for v in o.matrix_world.translation))
bpy.ops.wm.save_mainfile()
print("PAREDES OK")
