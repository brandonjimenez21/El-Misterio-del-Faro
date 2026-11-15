using System.Collections;
using UnityEngine;

/// <summary>
/// Controla el viento global de pasto y arboles (shaders Faro/Pasto y Faro/IslaDetalle).
/// - Calmar(): el viento se corta de golpe (todo queda inmovil) durante unos segundos: "algo esta cerca".
/// - Cada relampago provoca una rafaga breve.
/// Otros scripts (la figura, el faro) llaman a Calmar().
/// </summary>
public class ReaccionViento : MonoBehaviour
{
    public static ReaccionViento Instancia { get; private set; }

    [Header("Rafaga con cada relampago")]
    public float rafagaRelampago = 1.2f;
    public float duracionRafaga = 2.2f;
    [Header("Calma de golpe")]
    [Tooltip("Tiempo en el que el viento se apaga del todo (s)")] public float tiempoCorte = 0.25f;
    [Tooltip("Tiempo en el que vuelve despues de la calma (s)")] public float tiempoVuelta = 4f;

    static readonly int idCalma = Shader.PropertyToID("_FaroCalma");
    static readonly int idRafaga = Shader.PropertyToID("_FaroRafaga");

    float calma, rafaga;
    float calmaHasta;

    void Awake() { Instancia = this; Aplicar(); }
    void OnEnable() { Relampagos.AlRelampago += AlRelampago; }
    void OnDisable() { Relampagos.AlRelampago -= AlRelampago; Shader.SetGlobalFloat(idCalma, 0f); Shader.SetGlobalFloat(idRafaga, 0f); }

    void AlRelampago() { StartCoroutine(Rafaga()); }

    IEnumerator Rafaga()
    {
        float pico = rafagaRelampago;
        for (float t = 0f; t < duracionRafaga; t += Time.deltaTime)
        {
            rafaga = pico * Mathf.Sin(Mathf.PI * Mathf.Clamp01(t / duracionRafaga));
            yield return null;
        }
        rafaga = 0f;
    }

    /// <summary>Corta el viento durante 'segundos' (despues vuelve poco a poco)</summary>
    public void Calmar(float segundos) { calmaHasta = Mathf.Max(calmaHasta, Time.time + segundos); }

    void Update()
    {
        float objetivo = Time.time < calmaHasta ? 1f : 0f;
        float vel = objetivo > calma ? 1f / Mathf.Max(0.01f, tiempoCorte) : 1f / Mathf.Max(0.01f, tiempoVuelta);
        calma = Mathf.MoveTowards(calma, objetivo, vel * Time.deltaTime);
        Aplicar();
    }

    void Aplicar()
    {
        Shader.SetGlobalFloat(idCalma, calma);
        Shader.SetGlobalFloat(idRafaga, rafaga);
    }
}
