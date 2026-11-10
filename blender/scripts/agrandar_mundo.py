# Agranda isla, montanas, faro/cabana, muelle, caminos y oceano por un factor F (los objetos/props NO cambian de tamano;
# solo se recolocan en su sitio proporcional, conservando su altura sobre el suelo). Se aplica UNA vez.
import bpy
from mathutils import Vector
F = 1.3
PIV = Vector((0.0, 46.0, -0.55))     # xy centro de la isla, z nivel del mar (el mar no sube ni baja)
S = bpy.context.scene
if S.get("escala_mundo"):
    raise SystemExit("ya aplicado (escala_mundo=%s)" % S["escala_mundo"])
O = bpy.data.objects
bpy.context.view_layer.update()
I = O["IslandModel"]

def ground(x, y):
    inv = I.matrix_world.inverted()
    dl = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
    h, l, n, i = I.ray_cast(inv @ Vector((x, y, 500.0)), dl)
    return (I.matrix_world @ l).z if h else None

# props = objetos de los puzles sin padre (los hijos siguen a su padre)
props = [o for c in ("Puzle1_Muelle", "Puzle2_IslaAlterada", "Puzle3_InteriorFaro") for o in bpy.data.collections[c].objects
         if o.parent is None and o.name not in ("Luna", "Candado_Cuerpo")]
antes = {}
for o in props:
    g = ground(o.location.x, o.location.y)
    antes[o.name] = (o.location.z - g) if g is not None else None

def escalar_pos(p):
    return PIV + (p - PIV) * F

# --- mundo: posicion respecto al pivote y tamano
mundo = [O["IslandModel"], O["IslandModel.001"], O["Faro_Cabana_Raiz"], O["Muelle_Conjunto"], O["Candado_Cuerpo"]]
mundo += [o for o in bpy.data.collections["Caminos"].objects]
for o in mundo:
    o.location = escalar_pos(o.location) if o.name != "Candado_Cuerpo" else escalar_pos(o.location)
    if o.name != "Candado_Cuerpo":
        o.scale = o.scale * F
# oceano: solo en xy (las olas mantienen su altura)
oc = O["Oceano"]
oc.location.x = PIV.x + (oc.location.x - PIV.x) * F
oc.location.y = PIV.y + (oc.location.y - PIV.y) * F
oc.scale.x *= F; oc.scale.y *= F
bpy.context.view_layer.update()

# --- props: xy proporcional, misma altura sobre el nuevo suelo
for o in props:
    nx = PIV.x + (o.location.x - PIV.x) * F
    ny = PIV.y + (o.location.y - PIV.y) * F
    g = ground(nx, ny)
    h = antes[o.name]
    nz = (g + h) if (g is not None and h is not None) else (PIV.z + (o.location.z - PIV.z) * F)
    o.location = (nx, ny, nz)
S["escala_mundo"] = F
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_mainfile()
print("AGRANDAR OK", F)
