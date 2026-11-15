using System.Collections;
using UnityEngine;

/// <summary>
/// La luz del faro como "personaje".
///  Apagado   : sin luz (estado inicial: el jugador va a encenderlo).
///  Fantasma  : sigue apagado, pero de vez en cuando se enciende un instante solo, apunta hacia el jugador y se apaga.
///  Encendido : gira lentamente; de vez en cuando se detiene, apunta al jugador con retraso (como si lo buscara) y reanuda.
/// La logica del juego llama a Encender() / Apagar() / ModoFantasma().
/// </summary>
public class FaroBaliza : MonoBehaviour
{
    public enum Estado { Apagado, Fantasma, Encendido }

    [Header("Referencias")]
    [Tooltip("Lo que gira: contiene el haz y la luz")] public Transform pivote;
    public Light luz;
    public Renderer haz;
    [Tooltip("A quien busca el haz (por defecto la camara principal)")] public Transform objetivo;

    [Header("Estado")]
    public Estado estado = Estado.Fantasma;

    [Header("Encendido normal")]
    public float velocidadGiro = 14f;                  // grados por segundo
    [Tooltip("Cada cuantos segundos se detiene a buscar al jugador (min, max)")] public Vector2 intervaloBusqueda = new Vector2(35f, 80f);
    [Tooltip("Cuanto tarda el haz en alcanzar al jugador (menos = mas agresivo)")] public float retrasoBusqueda = 2.2f;
    public float tiempoFijo = 4.5f;

    [Header("Fantasma (apagado con apariciones)")]
    public Vector2 intervaloFantasma = new Vector2(40f, 110f);
    public Vector2 duracionFantasma = new Vector2(0.5f, 2.2f);

    [Header("Aspecto")]
    public float intensidadLuz = 250f;                 // spot de largo alcance (las luces puntuales del juego van de 2 a 10)
    public float intensidadHaz = 1.0f;

    public static event System.Action AlApuntarJugador;   // por si luego se engancha un sonido
    public static event System.Action AlEncenderFantasma;

    float brillo;               // 0..1 actual
    float objetivoBrillo;
    float angulo;
    float velAng;
    float proxBusqueda;
    bool buscando;
    float proxFantasma;
    MaterialPropertyBlock bloque;
    static readonly int idIntensidad = Shader.PropertyToID("_Intensidad");

    void Start()
    {
        if (pivote == null) pivote = transform;
        if (objetivo == null && Camera.main != null) objetivo = Camera.main.transform;
        bloque = new MaterialPropertyBlock();
        angulo = pivote.eulerAngles.y;
        Reprogramar();
        AplicarBrillo(0f);
    }

    void Reprogramar()
    {
        proxBusqueda = Time.time + Random.Range(intervaloBusqueda.x, intervaloBusqueda.y);
        proxFantasma = Time.time + Random.Range(intervaloFantasma.x, intervaloFantasma.y);
    }

    public void Encender() { estado = Estado.Encendido; Reprogramar(); }
    public void Apagar() { estado = Estado.Apagado; }
    public void ModoFantasma() { estado = Estado.Fantasma; Reprogramar(); }

    void Update()
    {
        if (objetivo == null && Camera.main != null) objetivo = Camera.main.transform;
        switch (estado)
        {
            case Estado.Apagado: objetivoBrillo = 0f; break;
            case Estado.Fantasma:
                if (!buscando && Time.time >= proxFantasma) StartCoroutine(Fantasma());
                if (!buscando) objetivoBrillo = 0f;
                break;
            case Estado.Encendido:
                if (!buscando)
                {
                    objetivoBrillo = 1f;
                    angulo += velocidadGiro * Time.deltaTime;
                    pivote.rotation = Quaternion.Euler(0f, angulo, 0f);
                    if (Time.time >= proxBusqueda) StartCoroutine(Busqueda());
                }
                break;
        }
        // el brillo sube rapido y baja rapido (parece electrico/viejo)
        brillo = Mathf.MoveTowards(brillo, objetivoBrillo, Time.deltaTime * (objetivoBrillo > brillo ? 6f : 4f));
        AplicarBrillo(brillo);
    }

    float AnguloHacia(Transform t)
    {
        Vector3 d = t.position - pivote.position; d.y = 0f;
        return Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
    }

    IEnumerator Fantasma()
    {
        buscando = true;
        if (AlEncenderFantasma != null) AlEncenderFantasma();
        // se enciende solo y apunta hacia el jugador, con parpadeos
        if (objetivo != null) { angulo = AnguloHacia(objetivo) + Random.Range(-40f, 40f); pivote.rotation = Quaternion.Euler(0f, angulo, 0f); }
        float dur = Random.Range(duracionFantasma.x, duracionFantasma.y);
        float fin = Time.time + dur;
        objetivoBrillo = 1f;
        while (Time.time < fin)
        {
            if (objetivo != null) angulo = Mathf.MoveTowardsAngle(angulo, AnguloHacia(objetivo), 18f * Time.deltaTime);
            pivote.rotation = Quaternion.Euler(0f, angulo, 0f);
            objetivoBrillo = Random.value < 0.12f ? 0f : 1f;     // parpadeo
            yield return null;
        }
        objetivoBrillo = 0f;
        buscando = false;
        proxFantasma = Time.time + Random.Range(intervaloFantasma.x, intervaloFantasma.y);
    }

    IEnumerator Busqueda()
    {
        buscando = true;
        // frena el giro y se desliza hacia el jugador con retraso
        float velocidad = 0f;
        bool avisado = false;
        float t0 = Time.time;
        while (Time.time - t0 < 2.5f + tiempoFijo && objetivo != null)
        {
            float meta = AnguloHacia(objetivo);
            angulo = Mathf.SmoothDampAngle(angulo, meta, ref velocidad, retrasoBusqueda);
            pivote.rotation = Quaternion.Euler(0f, angulo, 0f);
            if (!avisado && Mathf.Abs(Mathf.DeltaAngle(angulo, meta)) < 4f) { avisado = true; if (AlApuntarJugador != null) AlApuntarJugador(); }
            yield return null;
        }
        // se apaga de golpe un momento y sigue girando
        objetivoBrillo = 0f;
        yield return new WaitForSeconds(Random.Range(0.8f, 1.8f));
        buscando = false;
        proxBusqueda = Time.time + Random.Range(intervaloBusqueda.x, intervaloBusqueda.y);
    }

    void AplicarBrillo(float b)
    {
        bool activo = b > 0.002f;
        if (luz != null) { luz.enabled = activo; luz.intensity = intensidadLuz * b; }
        if (haz != null)
        {
            haz.enabled = activo;
            haz.GetPropertyBlock(bloque);
            bloque.SetFloat(idIntensidad, intensidadHaz * b);
            haz.SetPropertyBlock(bloque);
        }
    }

    [ContextMenu("Probar fantasma")] void ProbarFantasma() { StartCoroutine(Fantasma()); }
}
