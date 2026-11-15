using System.Collections;
using UnityEngine;

/// <summary>
/// La figura del antiguo cuidador. Casi nunca se ve:
///  - Solo aparece durante un relampago (un destello), en uno de los puntos marcados que el jugador tenga en el campo de vision.
///  - En cada aparicion esta un poco mas cerca (hasta una distancia minima). Al siguiente relampago ya no esta, o esta en otro sitio.
///  - Si el jugador se acerca mucho o la mira fijamente fuera del destello, desaparece.
///  - Cuando aparece, el viento se corta de golpe (ReaccionViento).
/// La logica del juego puede poner 'activa' a false (p. ej. en el interior de la torre) y llamar a Aparecer() cuando quiera.
/// </summary>
public class FiguraDistante : MonoBehaviour
{
    [Header("Referencias")]
    public GameObject figura;
    [Tooltip("Sitios donde puede aparecer (en el suelo)")] public Transform[] puntos;
    public Transform jugador;

    [Header("Cuando aparece")]
    public bool activa = true;
    [Range(0f, 1f), Tooltip("Probabilidad de que un relampago la revele")] public float probabilidad = 0.45f;
    [Tooltip("Distancias a las que puede aparecer (m): se va acercando")] public Vector2 distancia = new Vector2(70f, 22f);
    [Tooltip("Relampagos con aparicion hasta llegar a la distancia minima")] public int pasosHastaCerca = 6;
    public float silencioViento = 7f;
    [Tooltip("Campo de vision (grados) en el que debe estar para revelarse")] public float campoVision = 70f;

    [Header("Desaparicion")]
    [Tooltip("Si el jugador se acerca mas que esto, desaparece (m)")] public float distanciaHuida = 12f;
    public float segundosMirada = 1.6f;

    int apariciones;
    bool visible;
    float mirando;
    Transform ultimoPunto;

    void Start()
    {
        if (jugador == null && Camera.main != null) jugador = Camera.main.transform;
        if (figura != null) figura.SetActive(false);
    }
    void OnEnable() { Relampagos.AlRelampago += AlRelampago; }
    void OnDisable() { Relampagos.AlRelampago -= AlRelampago; }

    void AlRelampago()
    {
        if (visible) { Ocultar(); return; }                // al siguiente destello ya no esta
        if (!activa || figura == null || puntos == null || puntos.Length == 0) return;
        if (Random.value > probabilidad) return;
        Aparecer();
    }

    /// <summary>Intenta mostrar a la figura en un punto visible; devuelve true si lo logro</summary>
    public bool Aparecer()
    {
        if (jugador == null) return false;
        float t = Mathf.Clamp01(apariciones / (float)Mathf.Max(1, pasosHastaCerca));
        float dObjetivo = Mathf.Lerp(distancia.x, distancia.y, t);
        Transform mejor = null; float mejorError = float.MaxValue;
        foreach (var p in puntos)
        {
            if (p == null || p == ultimoPunto) continue;
            Vector3 d = p.position - jugador.position;
            float dist = d.magnitude;
            float ang = Vector3.Angle(jugador.forward, new Vector3(d.x, 0f, d.z).normalized);
            if (ang > campoVision * 0.5f || dist < distanciaHuida * 1.5f) continue;     // tiene que estar en pantalla
            float err = Mathf.Abs(dist - dObjetivo);
            if (err < mejorError) { mejorError = err; mejor = p; }
        }
        if (mejor == null) return false;
        ultimoPunto = mejor;
        figura.transform.position = mejor.position;
        Vector3 hacia = jugador.position - mejor.position; hacia.y = 0f;
        if (hacia.sqrMagnitude > 0.01f) figura.transform.rotation = Quaternion.LookRotation(hacia) * Quaternion.Euler(0f, 180f + Random.Range(-14f, 14f), 0f);
        figura.SetActive(true);
        visible = true; mirando = 0f; apariciones++;
        if (ReaccionViento.Instancia != null) ReaccionViento.Instancia.Calmar(silencioViento);
        StartCoroutine(OcultarTrasDestello());
        return true;
    }

    IEnumerator OcultarTrasDestello()
    {
        // se queda mientras dura el destello (y un instante mas: el ojo todavia la "ve") y luego ya no esta
        yield return new WaitForSeconds(0.25f);
        while (Relampagos.EnDestello) yield return null;
        yield return new WaitForSeconds(Random.Range(0.1f, 0.35f));
        // si aun esta en pantalla y lejos, se queda un poco en la oscuridad: solo se ve su silueta contra el cielo
        // (no se oculta hasta que el jugador la mire o se acerque)
    }

    void Ocultar() { if (figura != null) figura.SetActive(false); visible = false; mirando = 0f; }

    void Update()
    {
        if (!visible || jugador == null) return;
        Vector3 d = figura.transform.position - jugador.position;
        if (d.magnitude < distanciaHuida) { Ocultar(); return; }
        // mirada directa: se desvanece mientras no haya destello
        float ang = Vector3.Angle(jugador.forward, d);
        if (ang < 12f && !Relampagos.EnDestello) mirando += Time.deltaTime; else mirando = Mathf.Max(0f, mirando - Time.deltaTime * 0.5f);
        if (mirando > segundosMirada) Ocultar();
    }
}
