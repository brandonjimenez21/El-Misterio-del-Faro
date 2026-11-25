using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

/// <summary>
/// Arma el jugador en primera persona con los brazos del protagonista de Alejandro (blender/scripts/exportar_protagonista.py ->
/// Assets/Models/Faro/Personajes/Protagonista.fbx) y le pone suelo a la escena. Menu: Faro > Importar > Jugador y colisiones (repetible).
///   1. materiales (manga, piel, linterna) y clips del FBX: Idle y Marcha en bucle, Agarrar, SostenerV / SostenerH
///   2. AnimatorController "Brazos": Idle <-> Marcha por "Velocidad", Agarrar por trigger, Sostener por "Objeto" (1 vertical, 2 horizontal)
///   3. MeshCollider en lo que se pisa (isla, muelle, faro, rocas, puzle 2, caminos ocultos, atrezzo): la escena no tenia colisiones
///   4. objeto "Jugador" (CharacterController) > Cabeza > Main Camera > Brazos, con luz y sonido de la linterna, y JugadorControl
/// El importador restablece todos los valores: los ajustes van en este script, no a mano en el inspector.
/// </summary>
public static class ImportarJugador
{
    const string FBX = "Assets/Models/Faro/Personajes/Protagonista.fbx";
    const string CTRL = "Assets/Models/Faro/Personajes/Brazos.controller";
    const string MAT = "Assets/Materials/Faro/";

    [MenuItem("Faro/Importar/Jugador y colisiones")]
    public static void Ejecutar()
    {
        AssetDatabase.Refresh();
        var manga = Material("B_Prota_Manga", new Color(0.075f, 0.085f, 0.09f), 0.45f, 0f);
        var piel = Material("B_Prota_Piel", new Color(0.62f, 0.50f, 0.44f), 0.4f, 0f);
        var hierro = Material("B_Linterna_Hierro", new Color(0.035f, 0.035f, 0.04f), 0.5f, 0.8f);
        var cristal = Material("B_Linterna_Cristal", new Color(1f, 0.62f, 0.24f), 0.7f, 0f);
        Emisivo(cristal, new Color(1f, 0.55f, 0.18f) * 1.6f);
        var llama = Material("B_Linterna_Llama", new Color(1f, 0.85f, 0.45f), 0.7f, 0f);
        Emisivo(llama, new Color(1f, 0.80f, 0.35f) * 6f);
        Modelo(manga, piel, hierro, cristal, llama);
        var ctrl = Controlador();
        ColocarColisiones();
        Bloqueo();
        Jugador(ctrl);
        AssetDatabase.SaveAssets();
        Debug.Log("[Faro] Jugador y colisiones listos");
    }

    // ------------------------------------------------------------------ materiales y modelo
    static Material Material(string nombre, Color c, float suavidad, float metal)
    {
        string ruta = MAT + nombre + ".mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(ruta);
        if (m == null) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = nombre }; AssetDatabase.CreateAsset(m, ruta); }
        m.SetColor("_BaseColor", c);
        m.SetFloat("_Smoothness", suavidad);
        m.SetFloat("_Metallic", metal);
        EditorUtility.SetDirty(m);
        return m;
    }

    static void Emisivo(Material m, Color c)
    {
        m.SetColor("_EmissionColor", c);
        m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;     // URP quita _EMISSION si no se pone antes
        m.EnableKeyword("_EMISSION");
        EditorUtility.SetDirty(m);
    }

    static string NombreClip(string toma)
    {
        if (toma.Contains("Idle")) return "Idle";
        if (toma.Contains("Walking")) return "Marcha";
        if (toma.Contains("Grab")) return "Agarrar";
        if (toma.Contains("Vertical")) return "SostenerV";
        if (toma.Contains("Horizontal")) return "SostenerH";
        return null;
    }

    static void Modelo(params Material[] materiales)
    {
        var mi = AssetImporter.GetAtPath(FBX) as ModelImporter;
        if (mi == null) { Debug.LogWarning("[Faro] Falta " + FBX + " (blender/scripts/exportar_protagonista.py)"); return; }
        mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        mi.SearchAndRemapMaterials(ModelImporterMaterialName.BasedOnMaterialName, ModelImporterMaterialSearch.Everywhere);
        foreach (var m in materiales) mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), m.name), m);
        mi.animationType = ModelImporterAnimationType.Generic;
        mi.importAnimation = true;
        mi.importCameras = false; mi.importLights = false;
        mi.bakeAxisConversion = false;
        mi.SaveAndReimport();
        mi = AssetImporter.GetAtPath(FBX) as ModelImporter;
        var clips = new List<ModelImporterClipAnimation>();
        foreach (var c in mi.defaultClipAnimations)
        {
            string n = NombreClip(c.takeName);
            if (n == null) continue;
            c.name = n;
            c.loopTime = n != "Agarrar";
            c.loopPose = c.loopTime;
            clips.Add(c);
        }
        mi.clipAnimations = clips.ToArray();
        mi.SaveAndReimport();
    }

    static AnimationClip Clip(string nombre)
    {
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath(FBX))
            if (o is AnimationClip c && c.name == nombre) return c;
        return null;
    }

    // ------------------------------------------------------------------ animator
    static AnimatorController Controlador()
    {
        var ctrl = AssetDatabase.LoadAssetAtPath<AnimatorController>(CTRL);
        if (ctrl == null) ctrl = AnimatorController.CreateAnimatorControllerAtPath(CTRL);
        // se rehace entero (no se puede borrar el asset por el MCP)
        var sm = ctrl.layers[0].stateMachine;
        foreach (var s in sm.states) sm.RemoveState(s.state);
        foreach (var t in sm.anyStateTransitions) sm.RemoveAnyStateTransition(t);
        ctrl.parameters = new AnimatorControllerParameter[0];
        ctrl.AddParameter("Velocidad", AnimatorControllerParameterType.Float);
        ctrl.AddParameter("VelAnim", AnimatorControllerParameterType.Float);
        ctrl.parameters[1].defaultFloat = 1f;
        ctrl.AddParameter("Objeto", AnimatorControllerParameterType.Int);
        ctrl.AddParameter("Agarrar", AnimatorControllerParameterType.Trigger);
        var ps = ctrl.parameters; ps[1].defaultFloat = 1f; ctrl.parameters = ps;

        var idle = sm.AddState("Idle"); idle.motion = Clip("Idle");
        var marcha = sm.AddState("Marcha"); marcha.motion = Clip("Marcha");
        marcha.speedParameterActive = true; marcha.speedParameter = "VelAnim";
        var agarrar = sm.AddState("Agarrar"); agarrar.motion = Clip("Agarrar");
        var sostV = sm.AddState("SostenerV"); sostV.motion = Clip("SostenerV");
        var sostH = sm.AddState("SostenerH"); sostH.motion = Clip("SostenerH");
        sm.defaultState = idle;

        Transicion(idle, marcha, 0.20f, false, 0f).AddCondition(AnimatorConditionMode.Greater, 0.15f, "Velocidad");
        Transicion(marcha, idle, 0.25f, false, 0f).AddCondition(AnimatorConditionMode.Less, 0.15f, "Velocidad");
        var any = sm.AddAnyStateTransition(agarrar);
        any.hasExitTime = false; any.duration = 0.15f; any.canTransitionToSelf = false;
        any.AddCondition(AnimatorConditionMode.If, 0f, "Agarrar");
        var tAg = agarrar.AddTransition(idle); tAg.hasExitTime = true; tAg.exitTime = 0.92f; tAg.duration = 0.25f;
        foreach (var par in new[] { (sostV, 1), (sostH, 2) })
        {
            var a = sm.AddAnyStateTransition(par.Item1);
            a.hasExitTime = false; a.duration = 0.3f; a.canTransitionToSelf = false;
            a.AddCondition(AnimatorConditionMode.Equals, par.Item2, "Objeto");
            var s = par.Item1.AddTransition(idle);
            s.hasExitTime = false; s.duration = 0.3f;
            s.AddCondition(AnimatorConditionMode.NotEqual, par.Item2, "Objeto");
        }
        EditorUtility.SetDirty(ctrl);
        return ctrl;
    }

    static AnimatorStateTransition Transicion(AnimatorState de, AnimatorState a, float dur, bool salida, float t)
    {
        var tr = de.AddTransition(a);
        tr.hasExitTime = salida; tr.exitTime = t; tr.duration = dur;
        return tr;
    }

    // ------------------------------------------------------------------ suelo
    static void ColocarColisiones()
    {
        int n = 0;
        void Poner(Transform raiz, System.Func<MeshRenderer, bool> filtro)
        {
            if (raiz == null) return;
            foreach (var mr in raiz.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mf = mr.GetComponent<MeshFilter>();
                if (mf == null || mf.sharedMesh == null || mr.GetComponent<Collider>() != null) continue;
                string nom = mr.name;
                if (nom.StartsWith("Oceano") || nom.StartsWith("Niebla") || nom.Contains("Huella") || nom.Contains("Humo") || nom.Contains("Haz")) continue;
                if (filtro != null && !filtro(mr)) continue;
                var mc = mr.gameObject.AddComponent<MeshCollider>();
                mc.sharedMesh = mf.sharedMesh;
                n++;
            }
        }
        Transform T(string nombre) { var g = GameObject.Find(nombre); return g != null ? g.transform : null; }
        Poner(T("Isla"), null);
        Poner(T("Escenario_Muelle"), null);
        Poner(T("Faro_Cabana"), null);
        Poner(T("Puzle2_IslaAlterada"), null);
        Poner(T("Caminos_Ocultos"), null);
        Poner(T("Atrezzo_Exterior"), m => m.bounds.size.magnitude > 0.8f);
        Poner(T("Vegetacion_Isla"), m => m.name.StartsWith("Roca_") && m.bounds.size.magnitude > 3f);       // las rocas gordas; la hierba y los arboles no
        Physics.SyncTransforms();
        Debug.Log("[Faro] " + n + " colisionadores de malla anadidos");
    }

    // ------------------------------------------------------------------ bloqueo del sendero (Puzle 2)
    /// <summary>
    /// La roca Roca_Bloqueo_Sendero corta el camino al faro hasta resolver el Puzle 2, pero la isla es abierta y se la podia rodear.
    /// Se le suma un muro invisible de orilla a orilla a su altura (Muro_Sendero) y el script BloqueoSendero, que los quita con Abrir().
    /// </summary>
    static void Bloqueo()
    {
        var roca = GameObject.Find("Roca_Bloqueo_Sendero");
        if (roca == null) return;
        var viejo = GameObject.Find("Muro_Sendero");
        if (viejo != null) Object.DestroyImmediate(viejo);
        var b = roca.GetComponent<Renderer>().bounds;
        var muro = new GameObject("Muro_Sendero");
        muro.transform.SetParent(roca.transform.parent, true);
        muro.transform.position = new Vector3(b.center.x, 10f, b.center.z);
        var bc = muro.AddComponent<BoxCollider>();
        bc.size = new Vector3(260f, 60f, 2.5f);          // de mar a mar y muy alto: no se salta ni se rodea
        var bs = roca.GetComponent<BloqueoSendero>();
        if (bs == null) bs = roca.AddComponent<BloqueoSendero>();
        bs.muro = muro;
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(roca.scene);
    }

    // ------------------------------------------------------------------ jugador
    static void Jugador(AnimatorController ctrl)
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(FBX);
        if (prefab == null) return;
        var cam = Camera.main;
        if (cam == null) { Debug.LogWarning("[Faro] No hay Main Camera"); return; }
        for (int i = cam.transform.childCount - 1; i >= 0; i--)          // los brazos cuelgan de la camara: no caen con el Jugador viejo
            if (cam.transform.GetChild(i).name == "Brazos") Object.DestroyImmediate(cam.transform.GetChild(i).gameObject);
        var viejo = GameObject.Find("Jugador");
        float yaw = cam.transform.eulerAngles.y;
        Vector3 pies;
        if (viejo != null)
        {
            yaw = viejo.transform.eulerAngles.y; pies = viejo.transform.position;
            cam.transform.SetParent(null, true);
            Object.DestroyImmediate(viejo);
        }
        else
        {
            var p = cam.transform.position;
            pies = new Vector3(p.x, p.y - 1.74f, p.z);
            if (Physics.Raycast(new Vector3(p.x, 60f, p.z), Vector3.down, out var h, 200f, ~0, QueryTriggerInteraction.Ignore)) pies.y = h.point.y + 0.02f;
        }

        var j = new GameObject("Jugador") { layer = 2 };            // Ignore Raycast: los rayos de suelo y de alcance no chocan con el propio jugador
        j.transform.SetPositionAndRotation(pies, Quaternion.Euler(0f, yaw, 0f));
        var cc = j.AddComponent<CharacterController>();
        cc.height = 1.85f; cc.radius = 0.3f; cc.center = new Vector3(0f, 0.925f, 0f);
        cc.stepOffset = 0.45f; cc.slopeLimit = 55f; cc.skinWidth = 0.05f; cc.minMoveDistance = 0f;

        var cabeza = new GameObject("Cabeza") { layer = 2 };
        cabeza.transform.SetParent(j.transform, false);
        cabeza.transform.localPosition = new Vector3(0f, 1.74f, 0f);
        cam.transform.SetParent(cabeza.transform, false);
        cam.transform.localPosition = Vector3.zero; cam.transform.localRotation = Quaternion.identity;
        cam.nearClipPlane = 0.03f;

        // brazos: el origen del modelo esta a la altura del pecho (hombros 0.52 sobre el origen) y la camara a ~0.72 sobre el
        var brazos = (GameObject)PrefabUtility.InstantiatePrefab(prefab, cam.transform);
        brazos.name = "Brazos";
        // el modelo (Blender: exportar_protagonista.py) ya trae el brazo izquierdo relajado y el derecho doblado con la linterna: solo hay que
        // ponerlo bajo la camara para que las manos queden en el tercio inferior de la pantalla,
        // una a cada lado, y los hombros fuera de cuadro. Valores hallados midiendo las munecas en pantalla.
        brazos.transform.localRotation = Quaternion.Euler(-10f, 0f, 0f);
        brazos.transform.localScale = Vector3.one;
        brazos.transform.localPosition = new Vector3(0f, -0.78f, 0.45f);
        var an = brazos.GetComponent<Animator>();
        if (an == null) an = brazos.AddComponent<Animator>();
        an.runtimeAnimatorController = ctrl;
        an.applyRootMotion = false;
        an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        foreach (var r in brazos.GetComponentsInChildren<Renderer>())
        {
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            if (r is SkinnedMeshRenderer sk) sk.updateWhenOffscreen = true;
        }
        SetLayer(cabeza.transform, 2);

        // linterna: luz y sonido en el cristal
        Transform lin = null;
        foreach (var t in brazos.GetComponentsInChildren<Transform>(true)) if (t.name == "Linterna_Mano") lin = t;
        Light luz = null; AudioSource sonido = null; Renderer[] emisivos = null;
        if (lin != null)
        {
            var rr = lin.GetComponent<Renderer>();
            if (lin.GetComponent<LinternaPendulo>() == null) lin.gameObject.AddComponent<LinternaPendulo>();
            var go = new GameObject("Luz_Linterna_Mano");
            go.transform.SetParent(lin, false);
            go.transform.position = rr != null ? rr.bounds.center : lin.position;
            luz = go.AddComponent<Light>();
            luz.type = LightType.Point; luz.color = new Color(1f, 0.6f, 0.28f); luz.intensity = 4f; luz.range = 12f;
            luz.shadows = LightShadows.Soft;
            var pa = go.AddComponent<LuzParpadeo>();
            pa.variacion = 0.16f; pa.velocidad = 4.5f; pa.movimiento = 0.004f;
            go.AddComponent<LinternaTension>();                    // parpadeos y apagones segun la tension (TensionJugador)
            sonido = go.AddComponent<AudioSource>();
            sonido.clip = AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/SFX/325421__taxmanforever__gas-lantern-lit-loop.wav");
            sonido.loop = true; sonido.playOnAwake = false; sonido.spatialBlend = 1f; sonido.volume = 0.10f; sonido.minDistance = 0.6f; sonido.maxDistance = 7f;
            emisivos = new[] { rr };
        }

        var pasos = j.AddComponent<AudioSource>();
        pasos.playOnAwake = false; pasos.loop = true; pasos.spatialBlend = 0f;
        var jc = j.AddComponent<JugadorControl>();
        j.AddComponent<TensionJugador>();                           // tension 0..1: ruido de camara y linterna
        jc.cabeza = cabeza.transform;
        jc.brazos = an;
        jc.luzLinterna = luz;
        jc.emisivosLinterna = emisivos;
        jc.fuentePasos = pasos;
        jc.fuenteLinterna = sonido;
        var jadeo = j.AddComponent<AudioSource>();
        jadeo.playOnAwake = false; jadeo.spatialBlend = 0f;
        jc.fuenteJadeo = jadeo;
        jc.sonidoJadeo = AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/SFX/635222__nithaelizabethjohn__breath03.wav");
        jc.pasosMadera = AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/SFX/406750__kretopi__steponwood-014.wav");
        jc.pasosGrava = AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/SFX/164865__sunboy__gravel-steps.wav");
        jc.pasosEscalera = AssetDatabase.LoadAssetAtPath<AudioClip>("Assets/SFX/153164__argos22__stairs_steps.wav");
        var oc = GameObject.Find("Oceano"); if (oc != null) jc.oceano = oc.transform;
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(j.scene);
    }

    static void SetLayer(Transform t, int capa)
    {
        t.gameObject.layer = capa;
        foreach (Transform h in t) SetLayer(h, capa);
    }
}
