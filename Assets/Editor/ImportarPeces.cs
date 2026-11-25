using System.IO;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

/// <summary>
/// Pone en Unity lo que exporta blender/scripts/exportar_peces.py (modelos de Alejandro):
///   Assets/Models/Faro/Peces/Arenques.fbx (6 arenques con esqueleto y nado en bucle), Tiburon.fbx, Lubina.fbx y Calamar.fbx (cada uno con esqueleto y su nado en bucle), con sus texturas en Peces/Tex.
/// Menu: Faro > Importar > Peces y tiburon (se puede repetir; no duplica nada).
///   1. texturas (normal map, trilineal)   2. materiales B_Arenque_Cuerpo / B_Arenque_Ojos / B_Tiburon (URP/Lit)
///   3. FBX: materiales asignados, rig generico y clip de nado en bucle   4. objeto "Peces" en la escena con el contorno de la costa (RutaCosta), 8 bancos que rodean la isla y el tiburon que acecha (NadoCosta)
/// El oceano es opaco: de los animales solo se ve lo que asoma (lomo de los arenques, aleta del tiburon).
/// </summary>
public static class ImportarPeces
{
    const string DIR = "Assets/Models/Faro/Peces/";
    const string MAT = "Assets/Materials/Faro/";
    const string CTRL = "Assets/Models/Faro/Peces/Arenques.controller";
    const string CTRL_TIB = "Assets/Models/Faro/Peces/Tiburon.controller";
    const string CTRL_LUB = "Assets/Models/Faro/Peces/Lubina.controller";
    const string CTRL_CAL = "Assets/Models/Faro/Peces/Calamar.controller";

    [MenuItem("Faro/Importar/Peces y tiburon")]
    public static void Ejecutar()
    {
        AssetDatabase.Refresh();
        foreach (var g in AssetDatabase.FindAssets("t:Texture2D", new[] { DIR + "Tex" }))
        {
            string ruta = AssetDatabase.GUIDToAssetPath(g);
            var ti = AssetImporter.GetAtPath(ruta) as TextureImporter;
            if (ti == null) continue;
            bool normal = ruta.EndsWith("_n.png");
            bool cambia = false;
            if (normal && ti.textureType != TextureImporterType.NormalMap) { ti.textureType = TextureImporterType.NormalMap; cambia = true; }
            if (ti.filterMode != FilterMode.Trilinear) { ti.filterMode = FilterMode.Trilinear; cambia = true; }
            if (ti.anisoLevel < 4) { ti.anisoLevel = 4; cambia = true; }
            if (cambia) ti.SaveAndReimport();
        }

        var cuerpo = Material("B_Arenque_Cuerpo", "Arenque_Cuerpo_c", "Arenque_Cuerpo_n", 0.55f, 0.35f);   // plateado y mojado
        var ojos = Material("B_Arenque_Ojos", "Arenque_Ojos_c", null, 0.8f, 0f);
        var tib = Material("B_Tiburon", "Tiburon_c", null, 0.3f, 0f);
        // la cabeza de hueso tiene que leerse de noche: la propia textura emite un poco (lo negro sigue negro)
        tib.SetTexture("_EmissionMap", AssetDatabase.LoadAssetAtPath<Texture2D>(DIR + "Tex/Tiburon_c.png"));
        tib.SetColor("_EmissionColor", new Color(0.16f, 0.17f, 0.19f));
        tib.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;     // como al marcar "Emission" en el inspector
        tib.EnableKeyword("_EMISSION");
        EditorUtility.SetDirty(tib);
        // segundo material del tiburon: lo que queda bajo el agua se entreve a traves de la superficie y se enciende con los relampagos
        string rutaBajo = MAT + "M_Tiburon_BajoAgua.mat";
        var bajo = AssetDatabase.LoadAssetAtPath<Material>(rutaBajo);
        if (bajo == null) { bajo = new Material(Shader.Find("Faro/BajoElAgua")) { name = "M_Tiburon_BajoAgua" }; AssetDatabase.CreateAsset(bajo, rutaBajo); }
        bajo.shader = Shader.Find("Faro/BajoElAgua");
        bajo.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(DIR + "Tex/Tiburon_c.png"));
        bajo.SetColor("_Tinte", new Color(0.72f, 0.82f, 0.95f));
        bajo.SetFloat("_Visible", 0.3f);              // sin relampago apenas se entreve la silueta
        bajo.SetFloat("_VisibleRelampago", 0.95f);    // con relampago se ve el dibujo entero
        bajo.SetFloat("_Brillo", 0.4f);
        bajo.SetFloat("_BrilloRelampago", 3.2f);
        bajo.SetFloat("_Turbidez", 0.15f);
        EditorUtility.SetDirty(bajo);

        var lub = Material("B_Lubina", "Lubina_c", null, 0.45f, 0f);
        var lubOjo = Material("B_Lubina_Ojo", null, null, 0.9f, 0f);       // ojo palido, sin textura
        lubOjo.SetColor("_BaseColor", new Color(0.86f, 0.86f, 0.78f));
        lubOjo.SetColor("_EmissionColor", new Color(0.30f, 0.30f, 0.26f));
        lubOjo.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
        lubOjo.EnableKeyword("_EMISSION");
        EditorUtility.SetDirty(lubOjo);

        // calamar gigante: piel pintada (blender/scripts/pintar_calamar.py), ojos que brillan palidos en la oscuridad
        var cal = Material("B_Calamar", "Calamar_c", null, 0.4f, 0f);
        cal.SetTexture("_EmissionMap", AssetDatabase.LoadAssetAtPath<Texture2D>(DIR + "Tex/Calamar_c.png"));
        cal.SetColor("_EmissionColor", new Color(0.14f, 0.14f, 0.16f));
        cal.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
        cal.EnableKeyword("_EMISSION");
        EditorUtility.SetDirty(cal);
        var calOjo = Material("B_Calamar_Ojo", null, null, 0.95f, 0f);
        calOjo.SetColor("_BaseColor", new Color(0.80f, 0.82f, 0.70f));
        calOjo.SetColor("_EmissionColor", new Color(0.55f, 0.60f, 0.42f));
        calOjo.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
        calOjo.EnableKeyword("_EMISSION");
        EditorUtility.SetDirty(calOjo);
        string rutaBajoCal = MAT + "M_Calamar_BajoAgua.mat";
        var bajoCal = AssetDatabase.LoadAssetAtPath<Material>(rutaBajoCal);
        if (bajoCal == null) { bajoCal = new Material(Shader.Find("Faro/BajoElAgua")) { name = "M_Calamar_BajoAgua" }; AssetDatabase.CreateAsset(bajoCal, rutaBajoCal); }
        bajoCal.shader = Shader.Find("Faro/BajoElAgua");
        bajoCal.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>(DIR + "Tex/Calamar_c.png"));
        bajoCal.SetColor("_Tinte", new Color(0.72f, 0.82f, 0.95f));
        bajoCal.SetFloat("_Visible", 0.3f);
        bajoCal.SetFloat("_VisibleRelampago", 0.95f);
        bajoCal.SetFloat("_Brillo", 0.4f);
        bajoCal.SetFloat("_BrilloRelampago", 3.2f);
        bajoCal.SetFloat("_Turbidez", 0.15f);
        EditorUtility.SetDirty(bajoCal);

        Modelo(DIR + "Arenques.fbx", cuerpo, ojos);
        Modelo(DIR + "Tiburon.fbx", tib);
        Modelo(DIR + "Lubina.fbx", lub, lubOjo);
        Modelo(DIR + "Calamar.fbx", cal, calOjo);
        var ctrl = Controlador(CTRL, "Arenques.fbx");
        var ctrlTib = Controlador(CTRL_TIB, "Tiburon.fbx");
        var ctrlLub = Controlador(CTRL_LUB, "Lubina.fbx");
        Controlador(CTRL_CAL, "Calamar.fbx");
        Colocar(ctrl, ctrlTib, ctrlLub);
        ColocarCalamar.Ejecutar();        // el calamar va aparte: vive en las rocas del Puzle 2, no en el anillo de peces
        AssetDatabase.SaveAssets();
        Debug.Log("[Faro] Peces y tiburon importados");
    }

    static Material Material(string nombre, string color, string normal, float suavidad, float metal)
    {
        string ruta = MAT + nombre + ".mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(ruta);
        if (m == null) { m = new Material(Shader.Find("Universal Render Pipeline/Lit")) { name = nombre }; AssetDatabase.CreateAsset(m, ruta); }
        var c = color != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(DIR + "Tex/" + color + ".png") : null;
        m.SetTexture("_BaseMap", c);
        m.SetTexture("_MainTex", c);
        m.SetColor("_BaseColor", Color.white);
        var n = normal != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(DIR + "Tex/" + normal + ".png") : null;
        m.SetTexture("_BumpMap", n);
        if (n != null) m.EnableKeyword("_NORMALMAP"); else m.DisableKeyword("_NORMALMAP");
        m.SetFloat("_Smoothness", suavidad);
        m.SetFloat("_Metallic", metal);
        EditorUtility.SetDirty(m);
        return m;
    }

    static void Modelo(string ruta, params Material[] materiales)
    {
        var mi = AssetImporter.GetAtPath(ruta) as ModelImporter;
        if (mi == null) { Debug.LogWarning("[Faro] Falta " + ruta); return; }
        mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        mi.SearchAndRemapMaterials(ModelImporterMaterialName.BasedOnMaterialName, ModelImporterMaterialSearch.Everywhere);
        void Remap(string nom, Material m)
        {
            if (m != null) mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), nom), m);
        }
        foreach (var m in materiales) Remap(m.name, m);       // en el FBX los materiales se llaman igual que los de Unity
        mi.animationType = ModelImporterAnimationType.Generic;
        mi.importAnimation = true;
        mi.importCameras = false; mi.importLights = false;
        mi.bakeAxisConversion = false;      // la orientacion (cabeza a -Y, lomo a +Z) ya viene corregida dentro de la animacion desde Blender (exportar_peces.py)
        mi.SaveAndReimport();
        // el clip entero en bucle
        mi = AssetImporter.GetAtPath(ruta) as ModelImporter;
        var clips = mi.defaultClipAnimations;
        if (clips.Length > 0)
        {
            foreach (var c in clips) { c.loopTime = true; c.loopPose = true; c.name = "Nado"; }
            mi.clipAnimations = new[] { clips[0] };
            mi.SaveAndReimport();
        }
    }

    static AnimatorController Controlador(string rutaCtrl, string fbx)
    {
        var ctrl = AssetDatabase.LoadAssetAtPath<AnimatorController>(rutaCtrl);
        if (ctrl != null) return ctrl;
        AnimationClip clip = null;
        foreach (var o in AssetDatabase.LoadAllAssetsAtPath(DIR + fbx))
            if (o is AnimationClip c && !c.name.StartsWith("__preview__")) { clip = c; break; }
        if (clip == null) { Debug.LogWarning("[Faro] " + fbx + " no tiene clip de animacion"); return null; }
        return AnimatorController.CreateAnimatorControllerAtPathWithClip(rutaCtrl, clip);
    }

    // ---------------------------------------------------------------- contorno de la costa
    /// <summary>distancia de la orilla en cada direccion desde el centro de la isla (isla + muelle + bote + rocas + naufragio)</summary>
    static void Contorno(RutaCosta ruta, Transform ignorar)
    {
        const int N = 180;
        float nivel = GameObject.Find("Oceano").transform.position.y;
        var isla = GameObject.Find("Isla");
        var c = isla.GetComponent<Renderer>().bounds.center;
        var centro = new Vector2(c.x, c.z);
        var r = new float[N];
        foreach (var mr in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
        {
            string n = mr.name;
            if (n.StartsWith("Oceano") || n.StartsWith("Niebla") || n.StartsWith("Boya") || mr.transform.IsChildOf(ignorar)) continue;
            var b = mr.bounds;
            if (b.max.y < nivel - 0.2f || b.min.y > nivel + 0.5f || b.extents.x > 150f) continue;      // solo lo que toca el agua
            var mf = mr.GetComponent<MeshFilter>();
            if (mf == null || mf.sharedMesh == null) continue;
            float minY = mr.gameObject == isla ? nivel - 0.1f : nivel - 1.5f;       // de la isla, solo lo emergido; del resto, tambien los pilotes
            var tr = mr.transform;
            foreach (var v in mf.sharedMesh.vertices)
            {
                Vector3 w = tr.TransformPoint(v);
                if (w.y < minY) continue;
                float dx = w.x - centro.x, dz = w.z - centro.y;
                int i = (int)(Mathf.Repeat(Mathf.Atan2(dz, dx) / (2f * Mathf.PI), 1f) * N) % N;
                float d = Mathf.Sqrt(dx * dx + dz * dz);
                if (d > r[i]) r[i] = d;
            }
        }
        // ensanchar (lo estrecho, como el muelle, no se corta al interpolar) y suavizar sin bajar nunca del contorno real
        var ancho = new float[N];
        for (int i = 0; i < N; i++)
            for (int k = -2; k <= 2; k++) ancho[i] = Mathf.Max(ancho[i], r[(i + k + N) % N]);
        var s = (float[])ancho.Clone();
        for (int p = 0; p < 6; p++)
        {
            var t = new float[N];
            for (int i = 0; i < N; i++) t[i] = Mathf.Max(ancho[i], 0.25f * s[(i - 1 + N) % N] + 0.5f * s[i] + 0.25f * s[(i + 1) % N]);
            s = t;
        }
        ruta.centro = centro;
        ruta.radios = s;
    }

    // ---------------------------------------------------------------- escena
    static void Colocar(AnimatorController ctrl, AnimatorController ctrlTib, AnimatorController ctrlLub)
    {
        var viejo = GameObject.Find("Peces");
        if (viejo != null) Object.DestroyImmediate(viejo);
        var raiz = new GameObject("Peces");
        var ruta = raiz.AddComponent<RutaCosta>();
        Contorno(ruta, raiz.transform);
        var arenques = AssetDatabase.LoadAssetAtPath<GameObject>(DIR + "Arenques.fbx");
        var tiburon = AssetDatabase.LoadAssetAtPath<GameObject>(DIR + "Tiburon.fbx");
        var lubina = AssetDatabase.LoadAssetAtPath<GameObject>(DIR + "Lubina.fbx");

        // cardumenes repartidos alrededor de toda la isla: 10 grupos de 3 bancos pegados (18 arenques de ~55 cm por grupo, 180 en total).
        // El origen del modelo esta por debajo de los peces (nadan entre 1.7 y 3.6 m sobre el), asi que con -3.0 m el lomo de los de
        // arriba rompe la superficie
        if (arenques != null)
        {
            const int GRUPOS = 10, POR_GRUPO = 3;
            for (int gr = 0; gr < GRUPOS; gr++)
            {
                float margenG = 6f + 4f * ((gr * 3) % 4);              // 6 .. 18 m de la orilla
                float velG = (gr % 2 == 0 ? 1f : -1f) * (1.1f + 0.15f * (gr % 3));
                float faseG = gr * 360f / GRUPOS + 12f;
                for (int k = 0; k < POR_GRUPO; k++)
                {
                    var g = (GameObject)PrefabUtility.InstantiatePrefab(arenques, raiz.transform);
                    g.name = "Banco_Arenques_" + (gr + 1) + "_" + (k + 1);
                    float esc = 0.9f + 0.2f * ((gr + k * 2) % 3);
                    g.transform.localScale = Vector3.one * esc;
                    var an = g.GetComponent<Animator>();
                    if (an == null) an = g.AddComponent<Animator>();
                    an.runtimeAnimatorController = ctrl;
                    an.applyRootMotion = false;
                    an.cullingMode = AnimatorCullingMode.CullCompletely;       // lo que no se ve no gasta
                    var n = g.AddComponent<NadoCosta>();
                    n.ruta = ruta;
                    n.margen = margenG + (k - 1) * 2.5f;
                    n.velocidad = velG;
                    n.faseInicial = faseG + k * 1.6f;                  // ~2.5 m por detras del anterior
                    n.profundidad = -3.0f * esc;
                    n.vaiven = 0.15f;
                    n.Colocar();
                }
            }
        }
        // bancos de lubinas rayadas (~0.9 m): 14 bancos de 5 sueltos, mas cerca de la orilla que los arenques, en los dos sentidos.
        // El origen del modelo esta en el centro del pez: a -0.05 m asoma la aleta dorsal
        if (lubina != null)
        {
            const int BANCOS = 14, POR_BANCO = 5;
            for (int b = 0; b < BANCOS; b++)
            {
                var banco = new GameObject("Banco_Lubinas_" + (b + 1));
                banco.transform.SetParent(raiz.transform, false);
                var n = banco.AddComponent<NadoCosta>();
                n.ruta = ruta;
                n.margen = 4f + 3f * ((b * 5) % 6);                       // 4 .. 19 m de la orilla
                n.velocidad = (b % 2 == 0 ? 1f : -1f) * (0.9f + 0.12f * (b % 4));
                n.faseInicial = b * 360f / BANCOS + 7f;
                n.profundidad = -0.05f;
                n.vaiven = 0.12f;
                for (int k = 0; k < POR_BANCO; k++)
                {
                    var g = (GameObject)PrefabUtility.InstantiatePrefab(lubina, banco.transform);
                    g.name = "Lubina_" + (k + 1);
                    // posiciones fijas (sin azar: el importador se puede repetir y siempre queda igual): racimo de ~3 x 4 m
                    float ax = ((b * 7 + k * 5) % 9 - 4) * 0.35f, az = ((b * 3 + k * 4) % 9 - 4) * 0.55f, ay = ((b + k * 3) % 5 - 2) * 0.12f;
                    g.transform.localPosition = new Vector3(ax, ay, az);
                    g.transform.localScale = Vector3.one * (0.85f + 0.1f * ((b + k) % 4));
                    var an = g.GetComponent<Animator>();
                    if (an == null) an = g.AddComponent<Animator>();
                    an.runtimeAnimatorController = ctrlLub;
                    an.applyRootMotion = false;
                    an.cullingMode = AnimatorCullingMode.CullCompletely;
                    g.AddComponent<DesfaseNado>().desfase = ((b * 5 + k * 3) % 10) / 10f;
                }
                n.Colocar();
            }
        }
        // megalodon de 20 m: da la vuelta a la isla mar adentro y, si el jugador se acerca a la orilla, viene a pasar por delante
        if (tiburon != null)
        {
            var g = (GameObject)PrefabUtility.InstantiatePrefab(tiburon, raiz.transform);
            g.name = "Tiburon";
            var n = g.AddComponent<NadoCosta>();
            n.ruta = ruta;
            n.margen = 30f;
            n.velocidad = 2.6f;
            n.faseInicial = 250f;        // empieza al otro lado de la isla (el muelle esta a 90)
            n.profundidad = -1.4f;       // el lomo queda a ras de agua (lo cubre la espuma) y asoma ~1.1 m de aleta dorsal
            n.subidaAcecho = 0.3f;       // al acechar sube: el lomo sale del agua
            n.coletazo = 0f;             // el nado ya lo anima el esqueleto (clip "Swimming" de Alejandro)
            n.vaiven = 0.12f;
            var anT = g.GetComponent<Animator>();
            if (anT == null) anT = g.AddComponent<Animator>();
            anT.runtimeAnimatorController = ctrlTib;
            anT.applyRootMotion = false;
            anT.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            foreach (var r in g.GetComponentsInChildren<Renderer>())
                r.sharedMaterials = new[] { r.sharedMaterial, AssetDatabase.LoadAssetAtPath<Material>(MAT + "M_Tiburon_BajoAgua.mat") };
            n.acechaJugador = true;
            n.margenAcecho = 13f;
            n.velocidadAcecho = 3.4f;
            n.vaivenAcecho = 34f;
            n.distanciaSalto = 70f;
            n.aparecerA = 42f;
            n.Colocar();
        }
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(raiz.scene);
    }
}

