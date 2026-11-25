using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// <summary>
/// "Tension" del jugador (0 = tranquilo .. 1 = terror), calculada a partir de lo que hay cerca, y su traduccion en ruido visual de camara:
/// grano de pelicula, aberracion cromatica en los bordes, vineta que se cierra, distorsion suave y un leve zoom involuntario en los sustos.
/// Los efectos viven en un Volume propio (creado al empezar) cuyo peso sigue a la tension: mezcla con el perfil normal, sin tocarlo.
/// Otros sistemas pueden dar sustos con TensionJugador.Pulso(0.4f) o fijar un minimo con 'minimoManual'. LinternaTension tambien la lee.
/// </summary>
public class TensionJugador : MonoBehaviour
{
    public static TensionJugador Instancia { get; private set; }
    /// <summary>Tension actual 0..1 (0 si no hay sistema)</summary>
    public static float Valor { get { return Instancia != null ? Mathf.Clamp01(Instancia.valor + Instancia.pulso) : 0f; } }
    /// <summary>Susto puntual: sube la tension un momento (0..1) y la deja caer rapido</summary>
    public static void Pulso(float fuerza) { if (Instancia != null) Instancia.pulso = Mathf.Clamp01(Instancia.pulso + fuerza); }

    [Header("Fuentes (valor de tension que da cada una)")]
    [Range(0f, 1f)] public float basePorNoche = 0.06f;
    [Range(0f, 1f)] public float tiburonAcechando = 0.30f;
    [Range(0f, 1f), Tooltip("Mas cerca del tiburon, mas sube hasta este valor")] public float tiburonCerca = 0.70f;
    public Vector2 distanciaTiburon = new Vector2(8f, 38f);
    [Range(0f, 1f)] public float calamarVisible = 0.80f;
    [Range(0f, 1f)] public float calamarAcecho = 0.30f;
    [Range(0f, 1f)] public float figuraVisible = 0.55f;
    [Range(0f, 1f)] public float sinAliento = 0.20f;
    [Range(0f, 1f), Tooltip("Pulso que da cada relampago")] public float pulsoRelampago = 0.10f;
    [Range(0f, 1f), Tooltip("Pulso cuando aparece la figura del cuidador")] public float pulsoFigura = 0.45f;
    [Range(0f, 1f), Tooltip("Para pruebas y guion: la tension no baja de aqui")] public float minimoManual = 0f;

    [Header("Dinamica")]
    public float subida = 0.7f;               // por segundo
    public float bajada = 0.07f;              // el miedo se queda
    public float caidaPulso = 1.2f;

    [Header("Efectos a tension maxima")]
    [Range(0f, 1f)] public float grano = 0.55f;
    [Range(0f, 1f)] public float aberracion = 0.50f;
    [Range(0f, 1f)] public float vineta = 0.45f;
    [Range(0f, 1f)] public float distorsion = 0.22f;
    [Tooltip("Zoom involuntario (grados de FOV) con un susto")] public float zoomSusto = 5f;
    [Tooltip("Respiracion del FOV con tension alta (grados)")] public float respiracion = 0.5f;

    float valor, pulso, objetivo, fovBase;
    float proxCheck;
    Volume volumen;
    VolumeProfile perfil;
    FilmGrain fg; ChromaticAberration ca; Vignette vg; LensDistortion ld;
    JugadorControl jugador;
    CalamarRocas calamar;
    NadoCosta[] tiburones;
    FiguraDistante figura;
    Camera cam;

    void OnEnable()
    {
        Instancia = this;
        Relampagos.AlRelampago += AlRelampago;
        FiguraDistante.AlAparecer += AlAparecer;
    }
    void OnDisable()
    {
        if (Instancia == this) Instancia = null;
        Relampagos.AlRelampago -= AlRelampago;
        FiguraDistante.AlAparecer -= AlAparecer;
    }
    void OnDestroy()
    {
        if (volumen != null) Destroy(volumen.gameObject);
        if (perfil != null) Destroy(perfil);
    }

    void AlRelampago() { Pulso(pulsoRelampago); }
    void AlAparecer(Vector3 p, float t) { Pulso(pulsoFigura); }

    void Start()
    {
        jugador = GetComponent<JugadorControl>();
        cam = Camera.main;
        if (cam != null) fovBase = cam.fieldOfView;
        var go = new GameObject("Volumen_Tension");
        go.transform.SetParent(transform, false);
        volumen = go.AddComponent<Volume>();
        volumen.isGlobal = true; volumen.priority = 50f; volumen.weight = 0f;
        perfil = ScriptableObject.CreateInstance<VolumeProfile>();
        fg = perfil.Add<FilmGrain>(true);
        fg.type.Override(FilmGrainLookup.Thin1); fg.intensity.Override(grano); fg.response.Override(0.8f);
        ca = perfil.Add<ChromaticAberration>(true); ca.intensity.Override(aberracion);
        vg = perfil.Add<Vignette>(true); vg.intensity.Override(vineta); vg.smoothness.Override(0.55f); vg.color.Override(Color.black);
        ld = perfil.Add<LensDistortion>(true); ld.intensity.Override(-distorsion); ld.scale.Override(1f);
        volumen.sharedProfile = perfil;
        BuscarFuentes();
    }

    void BuscarFuentes()
    {
        calamar = FindFirstObjectByType<CalamarRocas>();
        tiburones = FindObjectsByType<NadoCosta>(FindObjectsSortMode.None);
        figura = FindFirstObjectByType<FiguraDistante>();
    }

    void Update()
    {
        proxCheck -= Time.deltaTime;
        if (proxCheck <= 0f) { proxCheck = 0.25f; objetivo = Calcular(); }
        float obj = Mathf.Max(objetivo, minimoManual);
        valor = Mathf.MoveTowards(valor, obj, (obj > valor ? subida : bajada) * Time.deltaTime);
        pulso = Mathf.MoveTowards(pulso, 0f, caidaPulso * Time.deltaTime);
        float t = Mathf.Clamp01(valor + pulso);

        // los efectos entran despacio (curva) y casi no se notan con poca tension
        if (volumen != null) volumen.weight = t * t * (3f - 2f * t);
        if (cam != null)
            cam.fieldOfView = fovBase - zoomSusto * pulso * pulso + Mathf.Sin(Time.time * 0.9f) * respiracion * valor * 0.5f;
    }

    float Calcular()
    {
        float v = basePorNoche;
        Vector3 p = transform.position;
        if (tiburones != null)
            foreach (var s in tiburones)
            {
                if (s == null || !s.acechaJugador || !s.Acechando) continue;
                float d = Vector3.Distance(p, s.transform.position);
                float k = Mathf.InverseLerp(distanciaTiburon.y, distanciaTiburon.x, d);
                v = Mathf.Max(v, Mathf.Lerp(tiburonAcechando, tiburonCerca, k));
            }
        if (calamar != null)
        {
            var f = calamar.fase;
            if (f == CalamarRocas.Fase.Surgiendo || f == CalamarRocas.Fase.Embistiendo || f == CalamarRocas.Fase.Arriba) v = Mathf.Max(v, calamarVisible);
            else if (f == CalamarRocas.Fase.Hundiendo) v = Mathf.Max(v, calamarAcecho);
            else
            {
                Vector3 d = p - calamar.torre; d.y = 0f;
                if (d.magnitude < calamar.radioActivacion * 1.6f) v = Mathf.Max(v, calamarAcecho);      // se acerca a la torre: algo huele mal
            }
        }
        if (figura != null && figura.Visible) v = Mathf.Max(v, figuraVisible);
        if (jugador != null && jugador.SinAliento) v = Mathf.Max(v, sinAliento) + 0.05f;
        return Mathf.Clamp01(v);
    }
}
