# Exporta los modelos de Alejandro (blender/herrings_swimming.blend y greenland_shark.blend) a Unity:
#   Assets/Models/Faro/Peces/Arenques.fbx  (6 arenques con esqueleto + animacion de nado en bucle, 250 fotogramas a 25 fps)
#   Assets/Models/Faro/Peces/Tiburon.fbx   (tiburon de Groenlandia con esqueleto y la animacion "Swimming" de Alejandro, 40 fotogramas a 24 fps)
#   Assets/Models/Faro/Peces/Lubina.fbx    (lubina rayada con esqueleto y "slow_swim_steady", 63 fotogramas; textura propia: pintar_lubina.py)
#   Assets/Models/Faro/Peces/Tex/*.png     (color y normal que venian empaquetados dentro del .blend)
# NO guarda el .blend. El eglefino (haddock.blend) no se exporta: son 5 escaneos fotogrametricos rotos (huecos y trozos sueltos).
# Uso: blender -b blender/herrings_swimming.blend --python blender/scripts/exportar_peces.py
#      blender -b blender/greenland_shark.blend   --python blender/scripts/exportar_peces.py
#      blender -b blender/stripped_bass.blend     --python blender/scripts/exportar_peces.py
import bpy, os

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(RAIZ, "Assets", "Models", "Faro", "Peces")
TEX = os.path.join(OUT, "Tex")
os.makedirs(TEX, exist_ok=True)
archivo = os.path.basename(bpy.data.filepath).lower()


def imagen_de(mat, socket):
    """imagen conectada a un socket del Principled (pasando por un Normal Map si hace falta)"""
    nt = mat.node_tree
    pr = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    ent = pr.inputs[socket]
    if not ent.is_linked:
        return None
    n = ent.links[0].from_node
    if n.type == 'NORMAL_MAP' and n.inputs['Color'].is_linked:
        n = n.inputs['Color'].links[0].from_node
    while n.type in ('MIX', 'MIX_RGB'):      # el tiburon mezcla dos texturas: se toma la primera conectada
        ent = [i for i in n.inputs if i.is_linked and i.type == 'RGBA']
        if not ent:
            return None
        n = ent[0].links[0].from_node
    return n.image if n.type == 'TEX_IMAGE' else None


def guardar(img, nombre):
    ruta = os.path.join(TEX, nombre + ".png")
    copia = img.copy()
    copia.filepath_raw = ruta
    copia.file_format = 'PNG'
    copia.save()
    bpy.data.images.remove(copia)
    print("TEXTURA", nombre, img.size[0], "x", img.size[1], flush=True)


def material_plano(nombre):
    m = bpy.data.materials.new("B_" + nombre)
    m.use_nodes = True
    return m


def sustituir(objs, por_material, texturas):
    """texturas: {material original: [(socket, sufijo), ...]}; por_material: {material original: nombre nuevo}"""
    for orig, lista in texturas.items():
        m = bpy.data.materials[orig]
        for socket, suf in lista:
            img = imagen_de(m, socket)
            if img:
                guardar(img, por_material[orig] + suf)
    nuevos = {k: material_plano(v) for k, v in por_material.items()}
    for o in objs:
        for i, s in enumerate(o.material_slots):
            if s.material and s.material.name in nuevos:
                o.data.materials[i] = nuevos[s.material.name]


def exportar(nombre, objs, escala, anim, ejes_en_malla=False):
    for x in bpy.context.view_layer.objects:
        x.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, nombre + ".fbx"), use_selection=True, global_scale=escala,
                             apply_scale_options='FBX_SCALE_ALL', bake_anim=anim, bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0.0, add_leaf_bones=False,
                             object_types={'ARMATURE', 'MESH', 'EMPTY'}, path_mode='STRIP', use_tspace=True,
                             colors_type='NONE', use_armature_deform_only=True,
                             bake_space_transform=ejes_en_malla)   # cambio de ejes Blender->Unity aplicado en la malla
    print("EXPORTADO", nombre, len(objs), "objetos", flush=True)


if "herrings" in archivo:
    # fuera la malla suelta (Object_24, un plano de 32 caras sin uso) y los materiales sobrantes
    malla = [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.polygons) > 100]
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o not in malla:
            bpy.data.objects.remove(o)
    # los arenques miden ~0.17 m: x3.2 -> ~0.55 m (mas grandes que uno real, para que se noten de noche desde la orilla)
    sustituir(malla, {"Atlantic_herring_body": "Arenque_Cuerpo", "Atlantic_herring_corneas": "Arenque_Ojos"},
              {"Atlantic_herring_body": [("Base Color", "_c"), ("Normal", "_n")], "Atlantic_herring_corneas": [("Base Color", "_c")]})
    objs = [o for o in bpy.data.objects if o.type in ('ARMATURE', 'MESH', 'EMPTY')]
    exportar("Arenques", objs, 3.2, True)
elif "shark" in archivo or "bass" in archivo:
    # Animales ya con esqueleto y animacion de Alejandro. Hay que dejarlos mirando a -Y (que en Unity es "adelante") con el lomo en +Z
    # y centrados, SIN tocar el objeto (NadoCosta pisa su giro): la correccion se mete en la animacion del hueso raiz
    # (que no tiene padre), asi el esqueleto, la malla y el clip salen ya orientados.
    import math, sys
    import numpy as np
    from mathutils import Matrix, Vector
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    es_tiburon = "shark" in archivo
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    for vacio in [x for x in bpy.data.objects if x.type == 'EMPTY']:      # vacios de Sketchfab
        bpy.data.objects.remove(vacio)
    malla = [o for o in bpy.data.objects if o.type == 'MESH']
    cuerpo = max(malla, key=lambda o: len(o.data.polygons))
    escena = bpy.context.scene
    accion = arm.animation_data.action
    f0, f1 = int(accion.frame_range[0]), int(accion.frame_range[1])

    def evaluar(o):
        escena.frame_set(f0)
        bpy.context.view_layer.update()
        e = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
        m = e.to_mesh()
        return e, m, np.array([v.co[:] for v in m.vertices], dtype=np.float64)

    if es_tiburon:
        # megalodon: cuerpo mas robusto (ancho y alto x1.3; en el reposo del modelo el largo va en Z). La malla y los huesos se escalan igual
        cuerpo.data.transform(Matrix.Diagonal((1.3, 1.3, 1.0, 1.0)))
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='EDIT')
        for eb in arm.data.edit_bones:
            eb.head.x *= 1.3; eb.head.y *= 1.3; eb.tail.x *= 1.3; eb.tail.y *= 1.3
        bpy.ops.object.mode_set(mode='OBJECT')

    # --- orientacion medida con datos, no a ojo
    e, me, co = evaluar(cuerpo)
    R = Matrix.Identity(4)
    if es_tiburon:
        # lomo = lado oscuro de la textura (la panza es blanca) -> +Z; cabeza = extremo ancho (la cola acaba en aleta fina) -> -Y
        img = imagen_de(bpy.data.materials["TexMap"], "Base Color")
        w, h = img.size
        px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, :, :3].mean(axis=2)
        uv = me.uv_layers.active.data
        zc = 0.5 * (co[:, 2].min() + co[:, 2].max())
        arriba, abajo = [], []
        for lp in me.loops:
            z = co[lp.vertex_index, 2] - zc
            if abs(z) < 0.08:
                continue
            u, v = uv[lp.index].uv
            (arriba if z > 0 else abajo).append(px[min(h - 1, int((v % 1.0) * h)), min(w - 1, int((u % 1.0) * w))])
        la, lb = float(np.mean(arriba)), float(np.mean(abajo))
        print("ANIMAL luminancia arriba %.3f abajo %.3f" % (la, lb), flush=True)
        if la > lb:
            R = Matrix.Rotation(math.pi, 4, 'Y') @ R
            print("ANIMAL estaba boca arriba: girado 180 sobre su eje largo", flush=True)
        c2 = np.array([(R @ Vector(p))[:] for p in co])
        y0, y1 = c2[:, 1].min(), c2[:, 1].max()
        largo = y1 - y0
        anch = lambda m: c2[m, 0].max() - c2[m, 0].min()
        a_mas, a_menos = anch(c2[:, 1] > y1 - 0.12 * largo), anch(c2[:, 1] < y0 + 0.12 * largo)
        print("ANIMAL ancho del extremo +Y %.3f, -Y %.3f" % (a_mas, a_menos), flush=True)
        if a_mas > a_menos:
            R = Matrix.Rotation(math.pi, 4, 'Z') @ R
            print("ANIMAL cabeza estaba en +Y: girado para que mire a -Y", flush=True)
    else:
        ojo = next(o for o in malla if o is not cuerpo)
        e2, m2, co_ojo = evaluar(ojo)
        e2.to_mesh_clear()
        print("ANIMAL ojo y medio %.3f, cuerpo y medio %.3f" % (co_ojo[:, 1].mean(), co[:, 1].mean()), flush=True)
        if co_ojo[:, 1].mean() > co[:, 1].mean():
            R = Matrix.Rotation(math.pi, 4, 'Z') @ R
            print("ANIMAL cabeza (ojo) en +Y: girado para que mire a -Y", flush=True)
        if abs(co[:, 2].max()) < abs(co[:, 2].min()):
            R = Matrix.Rotation(math.pi, 4, 'Y') @ R
            print("ANIMAL boca arriba: girado", flush=True)
    c2 = np.array([(R @ Vector(p))[:] for p in co])
    centro = 0.5 * (c2.min(axis=0) + c2.max(axis=0))
    M = Matrix.Translation(-Vector(centro)) @ R
    print("ANIMAL centro previo", tuple(round(float(x), 3) for x in centro), flush=True)
    e.to_mesh_clear()

    # --- meter la correccion en el hueso raiz, fotograma a fotograma: pose' = M @ pose  ->  base' = rest^-1 @ M @ rest @ base
    raiz = next(b for b in arm.pose.bones if b.parent is None)
    raiz.rotation_mode = 'QUATERNION'
    rest = raiz.bone.matrix_local.copy()
    bases = []
    for f in range(f0, f1 + 1):
        escena.frame_set(f)
        bpy.context.view_layer.update()
        bases.append(raiz.matrix_basis.copy())
    anterior = None
    for f, b in zip(range(f0, f1 + 1), bases):
        nb = rest.inverted() @ M @ rest @ b
        loc, rot, esc = nb.decompose()
        if anterior is not None and rot.dot(anterior) < 0:
            rot.negate()
        anterior = rot
        raiz.location, raiz.rotation_quaternion, raiz.scale = loc, rot, esc
        raiz.keyframe_insert("location", frame=f)
        raiz.keyframe_insert("rotation_quaternion", frame=f)
        raiz.keyframe_insert("scale", frame=f)
    escena.frame_set(f0)
    bpy.context.view_layer.update()

    # --- textura nueva sobre la malla ya orientada (el dibujo se define en el espacio del animal)
    e, me, co = evaluar(cuerpo)
    print("ANIMAL tras corregir: x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f" % (co[:, 0].min(), co[:, 0].max(), co[:, 1].min(), co[:, 1].max(), co[:, 2].min(), co[:, 2].max()), flush=True)
    if es_tiburon:
        import pintar_tiburon
        pintada = pintar_tiburon.pintar(me, os.path.join(TEX, "Tiburon_c.png"))
        sustituir(malla, {"TexMap": "Tiburon"}, {})
    else:
        import pintar_lubina
        pintada = pintar_lubina.pintar(me, os.path.join(TEX, "Lubina_c.png"))
        sustituir([cuerpo], {"striped_bass": "Lubina"}, {})
        ojo_mat = material_plano("Lubina_Ojo")
        if ojo.data.materials:
            ojo.data.materials[0] = ojo_mat
        else:
            ojo.data.materials.append(ojo_mat)
    e.to_mesh_clear()
    # vista previa de lado para revisar el dibujo sin abrir Unity
    if "--previa" in sys.argv:
        mat = cuerpo.data.materials[0]
        nt = mat.node_tree
        tx = nt.nodes.new("ShaderNodeTexImage")
        tx.image = pintada
        nt.links.new(tx.outputs["Color"], next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED').inputs["Base Color"])
        cam = bpy.data.cameras.new("previa")
        cam.type = 'ORTHO'
        cam.ortho_scale = 2.9 if es_tiburon else 0.5
        oc = bpy.data.objects.new("previa", cam)
        escena.collection.objects.link(oc)
        oc.location = (-5.0, 0.0, 0.0)
        oc.rotation_euler = (math.radians(90), 0.0, math.radians(-90))
        escena.camera = oc
        escena.render.engine = 'BLENDER_WORKBENCH'
        escena.display.shading.light = 'FLAT'
        escena.display.shading.color_type = 'TEXTURE'
        escena.render.resolution_x, escena.render.resolution_y = 1600, 700
        escena.render.filepath = sys.argv[sys.argv.index("--previa") + 1]
        bpy.ops.render.render(write_still=True)
    # megalodon: 2.5 m -> 20 m de largo; lubina: ~0.4 m -> ~1 m
    escena.frame_start, escena.frame_end = f0, f1       # el FBX exporta el rango de la escena: solo el ciclo de nado, no los 250 fotogramas
    exportar("Tiburon" if es_tiburon else "Lubina", [arm] + malla, 8.0 if es_tiburon else 2.5, True)
else:
    raise SystemExit("usar con herrings_swimming.blend, greenland_shark.blend o stripped_bass.blend")
