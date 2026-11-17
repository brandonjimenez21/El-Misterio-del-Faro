using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Pone en Unity lo que hornea Blender para la capa vikinga y las rocas del puzle 2:
///   blender/scripts/exportar_vikingo.py   -> Vikingo_Antiguo.fbx + Tex/Vik_*_c/_n/_m.png
///   blender/scripts/piedras_puzle2.py     -> Puzle2_IslaAlterada.fbx + Tex/Poste_*, Roca_*, Placa_*, Estela_Mareas
/// Menu: Faro > Importar > Vikingo y puzle 2 (se puede repetir tras cada horneado; no duplica nada).
///   1. texturas: tamano completo (4096 donde se horneo a 4096), trilineal y anisotropico -> no se emborronan de lejos
///   2. materiales B_<objeto> (URP/Lit): color + normal + mascara metal/suavidad + detalle fino de piedra o madera
///   3. coloca Vikingo_Antiguo en la escena junto a Puzle2_IslaAlterada (mismos ajustes: estatico, sombras, colisiones)
/// "Faro > Importar > Texturas horneadas nitidas" pasa a trilineal TODAS las texturas de Assets/Models/Faro/Tex.
/// </summary>
public static class ImportarVikingo
{
    const string TEX = "Assets/Models/Faro/Tex/";
    const string MAT = "Assets/Materials/Faro/";
    const string FBX_VIK = "Assets/Models/Faro/Vikingo_Antiguo.fbx";
    const string FBX_P2 = "Assets/Models/Faro/Puzle2_IslaAlterada.fbx";

    static readonly string[] vikingo =
    {
        "Vik_Piedra_Sendero", "Vik_Piedra_Barco", "Vik_Piedra_Faro", "Vik_Piedra_Caida", "Vik_Barco_Piedras", "Vik_Mojon",
        "Vik_Espada", "Vik_Escudo", "Vik_Altar", "Vik_Roca_Grabados", "Vik_Proa_Dragon", "Vik_Cuadernas",
    };
    // las caras talladas que quedan a contraluz de la luna se aclaran un poco para que las runas se lean sin linterna
    static readonly Dictionary<string, float> brillo = new Dictionary<string, float>
    {
        { "Vik_Piedra_Sendero", 1.3f }, { "Vik_Piedra_Barco", 1.4f }, { "Vik_Piedra_Faro", 1.15f }, { "Vik_Piedra_Caida", 1.2f }, { "Vik_Roca_Grabados", 1.4f },
    };
    static readonly string[] puzle2 =
    {
        "Poste_1_Reflejo_Base", "Poste_1_Reflejo_Cabeza", "Poste_2_Origen_Base", "Poste_2_Origen_Cabeza", "Poste_3_Fin_Base",
        "Poste_3_Fin_Cabeza", "Roca_Bloqueo_Sendero", "Roca_Normal", "Placa_Inscripcion", "Estela_Mareas",
    };
    // que textura de detalle fino lleva cada pieza que no es de piedra ("" = ninguna)
    static readonly Dictionary<string, string> detalleEspecial = new Dictionary<string, string>
    {
        { "Vik_Proa_Dragon", "T_Det_Madera" }, { "Vik_Cuadernas", "T_Det_Madera" }, { "Vik_Escudo", "T_Det_Madera" }, { "Vik_Espada", "" },
    };

    [MenuItem("Faro/Importar/Vikingo y puzle 2")]
    public static void Ejecutar()
    {
        Texturas();
        Materiales();
        Colocar();
        AssetDatabase.SaveAssets();
        Debug.Log("[Faro] Vikingo y puzle 2 importados");
    }

    static List<string> Todos()
    {
        var l = new List<string>(vikingo);
        l.AddRange(puzle2);
        return l;
    }

    // ---------------------------------------------------------------- texturas
    public static void Texturas()
    {
        AssetDatabase.Refresh();
        AssetDatabase.StartAssetEditing();
        try
        {
            foreach (var n in Todos())
                foreach (var suf in new[] { "_c", "_n", "_m" })
                    Ajustar(TEX + n + suf + ".png", suf, true);
        }
        finally { AssetDatabase.StopAssetEditing(); }
    }

    [MenuItem("Faro/Importar/Texturas horneadas nitidas")]
    public static void TexturasNitidas()
    {
        AssetDatabase.StartAssetEditing();
        int n = 0;
        try
        {
            foreach (var g in AssetDatabase.FindAssets("t:Texture2D", new[] { "Assets/Models/Faro/Tex" }))
            {
                var ti = AssetImporter.GetAtPath(AssetDatabase.GUIDToAssetPath(g)) as TextureImporter;
                if (ti == null || (ti.filterMode == FilterMode.Trilinear && ti.anisoLevel >= 4)) continue;
                ti.filterMode = FilterMode.Trilinear;
                ti.anisoLevel = Mathf.Max(ti.anisoLevel, 4);
                ti.SaveAndReimport();
                n++;
            }
        }
        finally { AssetDatabase.StopAssetEditing(); }
        Debug.Log("[Faro] Texturas pasadas a trilineal: " + n);
    }

    static void Ajustar(string ruta, string suf, bool tamanoCompleto)
    {
        var ti = AssetImporter.GetAtPath(ruta) as TextureImporter;
        if (ti == null) return;
        ti.GetSourceTextureWidthAndHeight(out int w, out int h);
        int max = Mathf.Clamp(Mathf.NextPowerOfTwo(Mathf.Max(w, h)), 256, 4096);
        if (suf == "_m") max = Mathf.Min(max, 2048);        // la mascara no necesita tanta resolucion
        bool cambia = false;
        if (tamanoCompleto && ti.maxTextureSize != max) { ti.maxTextureSize = max; cambia = true; }
        if (ti.filterMode != FilterMode.Trilinear) { ti.filterMode = FilterMode.Trilinear; cambia = true; }
        if (ti.anisoLevel < 8) { ti.anisoLevel = 8; cambia = true; }
        if (!ti.mipmapEnabled) { ti.mipmapEnabled = true; cambia = true; }
        if (suf == "_n" && ti.textureType != TextureImporterType.NormalMap) { ti.textureType = TextureImporterType.NormalMap; cambia = true; }
        if (suf == "_m" && ti.sRGBTexture) { ti.sRGBTexture = false; cambia = true; }
        if (cambia) ti.SaveAndReimport();
    }

    // ---------------------------------------------------------------- materiales
    public static void Materiales()
    {
        var lit = Shader.Find("Universal Render Pipeline/Lit");
        var remapVik = new Dictionary<string, Material>();
        foreach (var n in Todos())
        {
            var c = AssetDatabase.LoadAssetAtPath<Texture2D>(TEX + n + "_c.png");
            if (c == null) { Debug.LogWarning("[Faro] Falta la textura de " + n); continue; }
            string ruta = MAT + "B_" + n + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(ruta);
            if (m == null)
            {
                m = new Material(lit) { name = "B_" + n };
                AssetDatabase.CreateAsset(m, ruta);
            }
            m.SetTexture("_BaseMap", c);
            m.SetTexture("_MainTex", c);
            float br = brillo.TryGetValue(n, out var bv) ? bv : 1f;
            m.SetColor("_BaseColor", new Color(br, br, br, 1f));
            var nm = AssetDatabase.LoadAssetAtPath<Texture2D>(TEX + n + "_n.png");
            m.SetTexture("_BumpMap", nm);
            m.SetFloat("_BumpScale", 1f);
            Clave(m, "_NORMALMAP", nm != null);
            var mk = AssetDatabase.LoadAssetAtPath<Texture2D>(TEX + n + "_m.png");
            m.SetTexture("_MetallicGlossMap", mk);
            Clave(m, "_METALLICSPECGLOSSMAP", mk != null);
            m.SetFloat("_Metallic", mk != null ? 1f : 0f);
            m.SetFloat("_Smoothness", mk != null ? 1f : 0.3f);
            m.SetFloat("_SmoothnessTextureChannel", 0f);
            // detalle fino: se ve al pegarse a la piedra (la textura horneada llega a ~1 mm por pixel en las estelas)
            string det = detalleEspecial.TryGetValue(n, out var d) ? d : "T_Det_Piedra";
            var dc = det == "" ? null : AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Textures/" + det + ".png");
            var dn = det == "" ? null : AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/Textures/" + det + "_N.png");
            m.SetTexture("_DetailAlbedoMap", dc);
            m.SetTexture("_DetailNormalMap", dn);
            Clave(m, "_DETAIL_SCALED", dc != null);
            Clave(m, "_DETAIL_MULX2", false);
            if (dc != null)
            {
                float t = Mathf.Clamp(Mathf.Round(MetrosPorUV(n) / 1.2f), 1f, 24f);     // un tile de detalle cada ~1.2 m
                m.SetTextureScale("_DetailAlbedoMap", new Vector2(t, t));
                m.SetFloat("_DetailAlbedoMapScale", 0.35f);
                m.SetFloat("_DetailNormalMapScale", 0.6f);
            }
            EditorUtility.SetDirty(m);
            if (n.StartsWith("Vik_")) remapVik["B_" + n] = m;
        }
        // el FBX vikingo usa estos materiales (el del puzle 2 ya los tenia enlazados por nombre)
        var mi = AssetImporter.GetAtPath(FBX_VIK) as ModelImporter;
        if (mi != null)
        {
            var p2 = AssetImporter.GetAtPath(FBX_P2) as ModelImporter;
            if (p2 != null)
            {
                mi.globalScale = p2.globalScale; mi.useFileScale = p2.useFileScale; mi.bakeAxisConversion = p2.bakeAxisConversion;
                mi.importNormals = p2.importNormals; mi.importTangents = p2.importTangents; mi.meshCompression = p2.meshCompression;
                mi.isReadable = p2.isReadable; mi.generateSecondaryUV = p2.generateSecondaryUV;
            }
            mi.importCameras = false; mi.importLights = false; mi.importAnimation = false; mi.animationType = ModelImporterAnimationType.None;
            foreach (var kv in remapVik)
                mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), kv.Key), kv.Value);
            mi.SaveAndReimport();
        }
    }

    static void Clave(Material m, string k, bool on) { if (on) m.EnableKeyword(k); else m.DisableKeyword(k); }

    // cuantos metros de piedra caben en una unidad de UV (aprox.: raiz del area de la malla / cobertura del despliegue)
    static float MetrosPorUV(string nombre)
    {
        foreach (var ruta in new[] { FBX_VIK, FBX_P2, "Assets/Models/Faro/Puzle1_Muelle.fbx" })
            foreach (var o in AssetDatabase.LoadAllAssetsAtPath(ruta))
            {
                var me = o as Mesh;
                if (me == null || me.name != nombre) continue;
                var v = me.vertices; var t = me.triangles;
                double a = 0;
                for (int i = 0; i < t.Length; i += 3) a += Vector3.Cross(v[t[i + 1]] - v[t[i]], v[t[i + 2]] - v[t[i]]).magnitude * 0.5;
                return Mathf.Sqrt((float)a / 0.6f);
            }
        return 4f;
    }

    // ---------------------------------------------------------------- escena
    public static void Colocar()
    {
        var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(FBX_VIK);
        if (fbx == null) { Debug.LogWarning("[Faro] No esta " + FBX_VIK); return; }
        var p2 = GameObject.Find("Puzle2_IslaAlterada");
        if (p2 == null) { Debug.LogWarning("[Faro] No encuentro Puzle2_IslaAlterada en la escena"); return; }
        var go = GameObject.Find("Vikingo_Antiguo");
        if (go == null)
        {
            go = (GameObject)PrefabUtility.InstantiatePrefab(fbx, p2.transform.parent);
            Undo.RegisterCreatedObjectUndo(go, "Vikingo antiguo");
        }
        go.transform.localPosition = p2.transform.localPosition;
        go.transform.localRotation = p2.transform.localRotation;
        go.transform.localScale = p2.transform.localScale;
        go.transform.SetSiblingIndex(p2.transform.GetSiblingIndex() + 1);
        // mismos ajustes que una roca del puzle 2
        var modelo = p2.transform.Find("Roca_Normal") ?? p2.transform.GetChild(0);
        var rm = modelo.GetComponent<MeshRenderer>();
        foreach (var r in go.GetComponentsInChildren<MeshRenderer>(true))
        {
            GameObjectUtility.SetStaticEditorFlags(r.gameObject, GameObjectUtility.GetStaticEditorFlags(modelo.gameObject));
            r.gameObject.layer = modelo.gameObject.layer;
            if (rm != null)
            {
                r.shadowCastingMode = rm.shadowCastingMode; r.receiveShadows = rm.receiveShadows;
                r.receiveGI = rm.receiveGI; r.lightProbeUsage = rm.lightProbeUsage; r.reflectionProbeUsage = rm.reflectionProbeUsage;
            }
            // colision en todo lo que el jugador puede pisar o chocar (las estelas no se atraviesan); espada y escudo no estorban
            bool pequeno = r.name == "Vik_Espada" || r.name == "Vik_Escudo";
            var mc = r.GetComponent<MeshCollider>();
            if (!pequeno && mc == null) mc = r.gameObject.AddComponent<MeshCollider>();
            if (mc != null) mc.sharedMesh = r.GetComponent<MeshFilter>().sharedMesh;
        }
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(go.scene);
    }
}
