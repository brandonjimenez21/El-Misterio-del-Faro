using UnityEngine;

/// <summary>
/// Salpicaduras de las gotas al chocar con el suelo, el muelle y los tejados, alrededor de la camara (sobre todo delante).
/// La escena no tiene colliders: la altura de lo que hay debajo sale de un mapa de alturas horneado en el editor
/// (menu del componente "Hornear mapa de alturas"), guardado como textura en Assets/Textures/Lluvia.
/// Sobre el mar no salpica (alli los anillos de las gotas los pinta el shader del oceano).
/// </summary>
public class SalpicadurasLluvia : MonoBehaviour
{
    public ParticleSystem salpicaduras;
    public LluviaSigueCamara lluvia;
    [Tooltip("Mapa de alturas (R = altura en m) horneado con el menu del componente")] public Texture2D alturas;
    [Tooltip("Zona que cubre el mapa (x, z minimos y tamano)")] public Rect zona;

    [Header("Salpicaduras")]
    [Tooltip("Salpicaduras por segundo con lluvia fuerte")] public float porSegundo = 450f;
    [Tooltip("Radio alrededor de la camara (m)")] public float radio = 16f;
    [Tooltip("Medio angulo del sector delante de la camara (grados)")] public float angulo = 75f;
    [Tooltip("Objeto Oceano (sube y baja con la marea). Si esta vacio se busca por nombre")] public Transform oceano;
    [Tooltip("Margen sobre el nivel del mar por el oleaje: por debajo no salpica (es agua)")] public float margenMar = 0.45f;
    public Vector2 tamano = new Vector2(0.16f, 0.34f);
    public float vida = 0.2f;

    float[] h;
    int ancho, alto;
    float acumulado;
    Transform cam;

    void Start()
    {
        if (alturas == null) { enabled = false; return; }
        if (oceano == null) { var o = GameObject.Find("Oceano"); if (o != null) oceano = o.transform; }
        ancho = alturas.width; alto = alturas.height;
        var datos = alturas.GetPixelData<float>(0);
        h = datos.ToArray();
    }

    float Altura(float x, float z)
    {
        float u = (x - zona.xMin) / zona.width * (ancho - 1);
        float v = (z - zona.yMin) / zona.height * (alto - 1);
        if (u < 0f || v < 0f || u >= ancho - 1 || v >= alto - 1) return float.NegativeInfinity;
        int i = (int)u, j = (int)v;
        float fu = u - i, fv = v - j;
        float a = h[j * ancho + i], b = h[j * ancho + i + 1], c = h[(j + 1) * ancho + i], d = h[(j + 1) * ancho + i + 1];
        // en los bordes de tejados y del muelle no se interpola entre alturas muy distintas: se usa la mas cercana
        float mx = Mathf.Max(Mathf.Max(a, b), Mathf.Max(c, d)), mn = Mathf.Min(Mathf.Min(a, b), Mathf.Min(c, d));
        if (mx - mn > 0.6f)
            return fu < 0.5f ? (fv < 0.5f ? a : c) : (fv < 0.5f ? b : d);
        return Mathf.Lerp(Mathf.Lerp(a, b, fu), Mathf.Lerp(c, d, fu), fv);
    }

    void LateUpdate()
    {
        if (salpicaduras == null || h == null) return;
        if (cam == null) { if (Camera.main != null) cam = Camera.main.transform; else return; }
        float fuerza = lluvia != null ? lluvia.LluviaEnCamara : 1f;
        acumulado += porSegundo * fuerza * Time.deltaTime;
        int n = Mathf.Min((int)acumulado, 60);
        acumulado -= (int)acumulado;
        if (n <= 0) return;

        Vector3 p0 = cam.position;
        Vector3 fw = cam.forward; fw.y = 0f;
        float rumbo = fw.sqrMagnitude > 1e-4f ? Mathf.Atan2(fw.z, fw.x) : 0f;
        var ep = new ParticleSystem.EmitParams();
        ep.applyShapeToPosition = false;
        float mar = (oceano != null ? oceano.position.y : -0.55f) + margenMar;
        for (int k = 0; k < n; k++)
        {
            // area uniforme en el sector delante de la camara (y unas pocas detras, por si gira rapido)
            float ang = rumbo + (Random.value < 0.85f ? Random.Range(-angulo, angulo) : Random.Range(-180f, 180f)) * Mathf.Deg2Rad;
            float r = Mathf.Lerp(0.7f, radio, Mathf.Sqrt(Random.value));
            float x = p0.x + Mathf.Cos(ang) * r, z = p0.z + Mathf.Sin(ang) * r;
            float y = Altura(x, z);
            if (y < mar) continue;                                                       // es mar (o arena bajo el agua)
            if (y < mar + 1.6f && y < mar + ClimaAgua.AlturaOla(new Vector3(x, y, z))) continue;   // la ola grande la cubre ahora
            ep.position = new Vector3(x, y + 0.01f, z);
            ep.startSize = Random.Range(tamano.x, tamano.y);
            ep.startLifetime = vida * Random.Range(0.8f, 1.2f);
            ep.velocity = Vector3.zero;
            salpicaduras.Emit(ep, 1);
        }
    }

#if UNITY_EDITOR
    /// <summary>
    /// Pone colliders temporales a todo lo opaco de la escena, lanza rayos hacia abajo en una rejilla y guarda
    /// la altura del primer impacto (suelo, muelle o tejado) en una textura. Luego quita los colliders.
    /// </summary>
    [ContextMenu("Hornear mapa de alturas")]
    public void HornearAlturas()
    {
        const float paso = 0.5f;
        var isla = GameObject.Find("Isla");
        if (isla == null) { Debug.LogWarning("No se encontro la Isla"); return; }
        var b = isla.GetComponent<Renderer>().bounds;
        b.Expand(new Vector3(10f, 0f, 10f));
        zona = new Rect(b.min.x, b.min.z, b.size.x, b.size.z);
        int w = Mathf.CeilToInt(zona.width / paso) + 1, hh = Mathf.CeilToInt(zona.height / paso) + 1;

        var temporales = new System.Collections.Generic.List<MeshCollider>();
        foreach (var r in Object.FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None))
        {
            if (!r.enabled || !r.gameObject.activeInHierarchy) continue;
            var m = r.sharedMaterial;
            if (m == null || m.renderQueue >= 2450) continue;                       // transparente / recortado fino (pasto) no
            if (m.shader.name.Contains("Pasto") || m.shader.name.Contains("Oceano")) continue;
            if (!r.bounds.Intersects(b)) continue;
            var mf = r.GetComponent<MeshFilter>();
            if (mf == null || mf.sharedMesh == null || r.GetComponent<Collider>() != null) continue;
            var mc = r.gameObject.AddComponent<MeshCollider>();
            mc.sharedMesh = mf.sharedMesh;
            temporales.Add(mc);
        }
        Physics.SyncTransforms();
        var datos = new float[w * hh];
        float techo = b.max.y + 50f;
        for (int j = 0; j < hh; j++)
            for (int i = 0; i < w; i++)
            {
                var o = new Vector3(zona.xMin + i * paso, techo, zona.yMin + j * paso);
                datos[j * w + i] = Physics.Raycast(o, Vector3.down, out var hit, techo + 50f) ? hit.point.y : -50f;
            }
        foreach (var mc in temporales) Object.DestroyImmediate(mc);

        zona = new Rect(zona.xMin, zona.yMin, (w - 1) * paso, (hh - 1) * paso);
        var tex = new Texture2D(w, hh, TextureFormat.RFloat, false, true) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Point };
        tex.SetPixelData(datos, 0);
        tex.Apply(false, false);
        const string ruta = "Assets/Textures/Lluvia/AlturasLluvia.asset";
        var viejo = UnityEditor.AssetDatabase.LoadAssetAtPath<Texture2D>(ruta);
        if (viejo != null) { UnityEditor.EditorUtility.CopySerialized(tex, viejo); UnityEditor.AssetDatabase.SaveAssets(); }
        else UnityEditor.AssetDatabase.CreateAsset(tex, ruta);
        alturas = UnityEditor.AssetDatabase.LoadAssetAtPath<Texture2D>(ruta);
        UnityEditor.EditorUtility.SetDirty(this);
        Debug.Log($"Mapa de alturas de la lluvia: {w}x{hh}, {temporales.Count} mallas");
    }
#endif
}
