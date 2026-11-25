# Boyas: sombreado suave y una subdivision para que ya no se vean facetadas (conserva las UV).
# Uso: blender -b el_misterio_del_faro.blend --python scripts/boyas_suaves.py -- --save
import bpy, sys
for n in ("Boya_1", "Boya_2", "Boya_3", "Boya_Muelle_1", "Boya_Muelle_2"):
    o = bpy.data.objects[n]
    if o.data.get("suavizada"):
        continue
    md = o.modifiers.new("Sub", 'SUBSURF')
    md.levels = 1
    md.render_levels = 1
    bpy.context.view_layer.objects.active = o
    for ob in bpy.context.selected_objects:
        ob.select_set(False)
    o.select_set(True)
    bpy.ops.object.modifier_apply(modifier=md.name)
    for p in o.data.polygons:
        p.use_smooth = True
    o.data["suavizada"] = 1
    print("SUAVE", n, len(o.data.polygons))
if "--save" in sys.argv:
    bpy.ops.wm.save_mainfile()
