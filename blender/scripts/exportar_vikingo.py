# Hornea y exporta la coleccion Vikingo_Antiguo (creada por vikingos.py) -> Assets/Models/Faro/Vikingo_Antiguo.fbx y
# texturas <objeto>_c/_n/_m.png en Assets/Models/Faro/Tex. NO guarda el .blend.
# Uso: blender -b el_misterio_del_faro.blend --python scripts/exportar_vikingo.py [-- Vik_Objeto ...]   (sin nombres: todos)
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hornear_lib as hl

TAM = {"Vik_Piedra_Barco": 4096, "Vik_Roca_Grabados": 4096, "Vik_Barco_Piedras": 4096, "Vik_Piedra_Sendero": 2048,
       "Vik_Piedra_Faro": 2048, "Vik_Piedra_Caida": 2048, "Vik_Mojon": 2048, "Vik_Altar": 2048, "Vik_Proa_Dragon": 2048,
       "Vik_Cuadernas": 1024, "Vik_Escudo": 1024, "Vik_Espada": 512}
col = bpy.data.collections["Vikingo_Antiguo"]
solo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
objs = [o for o in col.objects if o.type == 'MESH' and len(o.data.polygons) > 0]
for o in objs:
    if solo and o.name not in solo:
        # no se hornea, pero necesita el material plano y unas UV para exportar
        if len(o.data.uv_layers) == 0:
            o.data.uv_layers.new(name="UVMap")
        hl.desplegar_hd(o)
        o.data.materials.clear()
        o.data.materials.append(hl.plain_mat(o.name))
        continue
    hl.hornear(o, TAM.get(o.name, 1024))
hl.exportar_fbx("Vikingo_Antiguo", list(col.objects))
