using UnityEngine;

/// <summary>
/// Hace que un objeto (bote, boya) flote: sigue la altura del oceano (mareas y olas grandes de ClimaAgua) y se balancea suavemente con las olas.
/// </summary>
public class FlotaConMarea : MonoBehaviour
{
    [Tooltip("Objeto Oceano (el que tiene OceanoOlas). Si esta vacio se busca por nombre")]
    public Transform oceano;
    [Tooltip("Cuanto subir sobre el nivel del agua (m)")] public float desfase = 0f;
    public float cabeceo = 2.5f;      // grados de balanceo
    public float velocidad = 0.6f;
    public float oscilacionVertical = 0.06f;

    float yBase, semilla, nivelInicial, olaSuave;
    Quaternion rotBase;

    void Start()
    {
        if (oceano == null) { var o = GameObject.Find("Oceano"); if (o != null) oceano = o.transform; }
        yBase = transform.position.y;
        rotBase = transform.rotation;
        semilla = Random.value * 20f;
        nivelInicial = oceano != null ? oceano.position.y : 0f;
    }

    void LateUpdate()
    {
        float t = Time.time * velocidad + semilla;
        float nivel = oceano != null ? oceano.position.y - nivelInicial : 0f;   // solo el cambio de marea
        var p = transform.position;
        float ola = Mathf.Lerp(olaSuave, ClimaAgua.AlturaOla(p), 1f - Mathf.Exp(-Time.deltaTime * 4f));   // la ola grande lo levanta
        olaSuave = ola;
        p.y = yBase + nivel + desfase + ola + Mathf.Sin(t * 1.3f) * oscilacionVertical;
        transform.position = p;
        transform.rotation = rotBase * Quaternion.Euler(Mathf.Sin(t) * cabeceo, 0f, Mathf.Sin(t * 0.8f + 1f) * cabeceo * 0.7f);
    }
}
