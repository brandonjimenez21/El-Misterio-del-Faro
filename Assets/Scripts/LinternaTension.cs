using System.Collections;
using UnityEngine;

/// <summary>
/// La linterna reacciona a la tension (TensionJugador): con miedo el parpadeo se acelera y crece, hay tartamudeos cortos (la luz cae y vuelve)
/// y, con tension alta, apagones de un par de segundos en los que la isla se queda a oscuras salvo por los relampagos; la llama vuelve con un
/// par de sobresaltos. Se pone en Luz_Linterna_Mano (junto a LuzParpadeo). Los apagones no cambian 'linternaEncendida' (F sigue mandando).
/// </summary>
[RequireComponent(typeof(Light))]
public class LinternaTension : MonoBehaviour
{
    [Header("Parpadeo continuo")]
    [Tooltip("Multiplicador de la variacion del parpadeo con tension maxima")] public float variacionMax = 3.2f;
    [Tooltip("Multiplicador de la velocidad del parpadeo con tension maxima")] public float velocidadMax = 2.0f;

    [Header("Tartamudeos (caidas rapidas)")]
    [Tooltip("Tension a partir de la cual empiezan")] [Range(0f, 1f)] public float umbralTartamudeo = 0.25f;
    [Tooltip("Segundos entre tartamudeos con tension 0.25 y con tension 1")] public Vector2 intervaloTartamudeo = new Vector2(14f, 3.5f);

    [Header("Apagones")]
    [Range(0f, 1f)] public float umbralApagon = 0.62f;
    [Tooltip("Segundos minimos entre apagones")] public float enfriamiento = 22f;
    [Tooltip("Probabilidad por segundo de un apagon cuando se cumple todo")] [Range(0f, 1f)] public float probabilidadApagon = 0.12f;
    public Vector2 duracionApagon = new Vector2(0.9f, 2.6f);
    [Tooltip("Si es verdadero el apagon tambien baja el sonido de la llama")] public bool silenciaLlama = true;

    LuzParpadeo parpadeo;
    JugadorControl jugador;
    float variacionBase, velocidadBase, sigTartamudeo, sigApagon, volumenLlama;
    bool enCurso;

    void Awake()
    {
        parpadeo = GetComponent<LuzParpadeo>();
        if (parpadeo != null) { variacionBase = parpadeo.variacion; velocidadBase = parpadeo.velocidad; }
    }

    void Start()
    {
        jugador = GetComponentInParent<JugadorControl>();
        if (jugador == null) jugador = FindFirstObjectByType<JugadorControl>();
        if (jugador != null && jugador.fuenteLinterna != null) volumenLlama = jugador.fuenteLinterna.volume;
        sigApagon = Time.time + enfriamiento * 0.5f;
        Reprogramar();
    }

    void OnDisable() { if (parpadeo != null) parpadeo.factor = 1f; }

    void Reprogramar()
    {
        float t = Mathf.InverseLerp(umbralTartamudeo, 1f, TensionJugador.Valor);
        sigTartamudeo = Time.time + Mathf.Lerp(intervaloTartamudeo.x, intervaloTartamudeo.y, t) * Random.Range(0.7f, 1.3f);
    }

    void Update()
    {
        float t = TensionJugador.Valor;
        if (parpadeo != null)
        {
            parpadeo.variacion = variacionBase * Mathf.Lerp(1f, variacionMax, t);
            parpadeo.velocidad = velocidadBase * Mathf.Lerp(1f, velocidadMax, t);
        }
        if (enCurso || jugador == null || !jugador.linternaEncendida) return;

        if (t >= umbralApagon && Time.time >= sigApagon && Random.value < probabilidadApagon * Time.deltaTime)
        {
            sigApagon = Time.time + enfriamiento * Random.Range(1f, 1.6f);
            StartCoroutine(Apagon());
        }
        else if (t >= umbralTartamudeo && Time.time >= sigTartamudeo)
        {
            Reprogramar();
            StartCoroutine(Tartamudeo());
        }
    }

    /// <summary>Provoca ya un apagon (para la logica del juego)</summary>
    public void ApagonAhora() { if (!enCurso) StartCoroutine(Apagon()); }

    void Poner(float k)
    {
        if (parpadeo != null) parpadeo.factor = k;
        if (jugador != null)
        {
            jugador.BrilloLlama(k);
            if (silenciaLlama && jugador.fuenteLinterna != null) jugador.fuenteLinterna.volume = volumenLlama * Mathf.Lerp(0.15f, 1f, k);
        }
    }

    IEnumerator Tartamudeo()
    {
        enCurso = true;
        int n = Random.Range(1, 3);
        for (int i = 0; i < n; i++)
        {
            Poner(Random.Range(0.1f, 0.45f));
            yield return new WaitForSeconds(Random.Range(0.04f, 0.13f));
            Poner(1f);
            yield return new WaitForSeconds(Random.Range(0.05f, 0.18f));
        }
        enCurso = false;
    }

    IEnumerator Apagon()
    {
        enCurso = true;
        // se va con una caida y un ultimo destello
        Poner(0.3f); yield return new WaitForSeconds(0.07f);
        Poner(0.75f); yield return new WaitForSeconds(0.05f);
        Poner(0f);
        TensionJugador.Pulso(0.12f);
        yield return new WaitForSeconds(Random.Range(duracionApagon.x, duracionApagon.y));
        // vuelve a trompicones
        int n = Random.Range(2, 4);
        for (int i = 0; i < n; i++)
        {
            Poner(Random.Range(0.25f, 0.6f)); yield return new WaitForSeconds(Random.Range(0.05f, 0.12f));
            Poner(0f); yield return new WaitForSeconds(Random.Range(0.06f, 0.22f));
        }
        for (float e = 0f; e < 0.35f; e += Time.deltaTime) { Poner(Mathf.SmoothStep(0f, 1f, e / 0.35f)); yield return null; }
        Poner(1f);
        enCurso = false;
    }
}
