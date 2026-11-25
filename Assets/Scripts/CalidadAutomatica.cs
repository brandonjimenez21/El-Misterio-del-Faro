using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// <summary>
/// Calidad automatica: si el juego baja de los fps objetivo, reduce la calidad por niveles (y la vuelve a subir si sobra).
/// Pensado para que el juego vaya fluido en ordenadores mas lentos sin tocar nada a mano.
///   nivel 0 = calidad completa (la que esta configurada en PC_RPAsset y PC_Renderer)
///   cada nivel baja: resolucion interna (lo que mas se nota en fps), muestras de la niebla volumetrica,
///   hasta donde llega la hierba y hasta donde llegan las sombras de la luna.
/// Con "automatica" desmarcada se queda fijo en "nivel" (sirve para comparar a mano).
/// Al salir restaura los valores originales (en el editor no deja los ajustes cambiados).
/// </summary>
public class CalidadAutomatica : MonoBehaviour
{
    [Tooltip("Si esta marcado, sube y baja el nivel solo segun los fps")] public bool automatica = true;
    [Tooltip("Fps que se intentan mantener")] [Range(30f, 144f)] public float fpsObjetivo = 60f;
    [Tooltip("0 = calidad completa ... 4 = la mas ligera")] [Range(0, 4)] public int nivel = 0;
    [Tooltip("Nivel mas bajo al que puede llegar solo")] [Range(0, 4)] public int nivelMaximo = 4;
    [Tooltip("Escribe en la consola cada cambio de nivel")] public bool avisar = true;

    // por nivel:                              0      1      2      3      4
    static readonly float[] factorEscala = { 1.00f, 0.89f, 0.80f, 0.72f, 0.64f };   // multiplica la escala de render del asset
    static readonly int[] pasosNiebla =    {   48,    14,    12,    10,     8 };     // tope de muestras de la niebla volumetrica
    static readonly float[] recorteHierba ={ 0.00f, 0.00f, 0.15f, 0.30f, 0.45f };   // cuanto menos lejos llega la hierba
    static readonly float[] factorSombra = { 1.00f, 1.00f, 1.00f, 0.80f, 0.65f };   // distancia de las sombras de la luna

    /// <summary>Lo leen PastoDistancia y (como global _FaroRecorteHierba) los shaders de hierba e isla.</summary>
    public static float RecorteHierba { get; private set; }

    static readonly int idRecorte = Shader.PropertyToID("_FaroRecorteHierba");
    UniversalRenderPipelineAsset asset;
    float escalaBase, sombraBase;
    int aplicado = -1;
    float tiempo, espera, paciencia = 6f, sobra;
    int cuadros;

    void OnEnable()
    {
        asset = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
        if (asset != null) { escalaBase = asset.renderScale; sombraBase = asset.shadowDistance; }
        espera = 4f;            // los primeros segundos (carga, compilacion de shaders) no cuentan
        Aplicar();
    }

    void OnDisable()
    {
        if (asset != null) { asset.renderScale = escalaBase; asset.shadowDistance = sombraBase; }
        NieblaVolumetricaFeature.LimitePasos = 48;
        RecorteHierba = 0f;
        Shader.SetGlobalFloat(idRecorte, 0f);
        aplicado = -1;
    }

    void Aplicar()
    {
        nivel = Mathf.Clamp(nivel, 0, 4);
        if (nivel == aplicado) return;
        if (asset != null)
        {
            asset.renderScale = Mathf.Clamp(escalaBase * factorEscala[nivel], 0.5f, 2f);
            asset.shadowDistance = sombraBase * factorSombra[nivel];
        }
        NieblaVolumetricaFeature.LimitePasos = pasosNiebla[nivel];
        RecorteHierba = recorteHierba[nivel];
        Shader.SetGlobalFloat(idRecorte, RecorteHierba);
        if (avisar && aplicado >= 0) Debug.Log("[Faro] Calidad automatica: nivel " + nivel + " (0 = completa, 4 = ligera)");
        aplicado = nivel;
    }

    void Update()
    {
        Aplicar();              // por si se cambio "nivel" a mano en el Inspector
        if (!automatica) return;
        float dt = Time.unscaledDeltaTime;
        if (espera > 0f) { espera -= dt; tiempo = 0f; cuadros = 0; return; }
        if (dt > 0.25f) return; // tirones sueltos (cargas) no cuentan
        tiempo += dt; cuadros++;
        if (tiempo < 1.5f) return;
        float fps = cuadros / tiempo;
        tiempo = 0f; cuadros = 0;

        if (fps < fpsObjetivo - 3f && nivel < nivelMaximo)
        {
            // si ya habia subido y vuelve a faltar, la proxima vez espera mas antes de subir (evita ir y venir)
            if (sobra > 0f) paciencia = Mathf.Min(paciencia * 2f, 60f);
            nivel++; sobra = 0f; espera = 1.5f;
            Aplicar();
        }
        else if (nivel > 0 && fps > fpsObjetivo * 1.35f)
        {
            sobra += 1.5f;
            if (sobra >= paciencia) { nivel--; espera = 1.5f; Aplicar(); }
        }
        else sobra = 0f;
    }
}
