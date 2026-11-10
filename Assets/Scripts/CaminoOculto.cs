using System.Collections;
using UnityEngine;
using UnityEngine.Events;

/// <summary>
/// Camino oculto de la isla (cueva, puente, embarcadero del farero). Empieza invisible y se revela poco a poco.
/// Para el puzle final: llama a Revelar() (por ejemplo desde un trigger o un boton).
/// En el editor puedes arrastrar "revelado" para ver como queda, o usar el menu del componente: "Probar revelado".
/// </summary>
[ExecuteAlways]
[RequireComponent(typeof(Renderer))]
public class CaminoOculto : MonoBehaviour
{
    [Range(0f, 1f)] public float revelado = 0f;
    [Tooltip("Segundos que tarda en revelarse entero")] public float duracion = 6f;
    [Tooltip("Se ejecuta cuando termina de revelarse (por ejemplo, abrir la cueva o activar el puente)")]
    public UnityEvent alRevelarse;

    Renderer rend;
    MaterialPropertyBlock bloque;
    static readonly int IdRevelado = Shader.PropertyToID("_Revelado");
    Coroutine rutina;

    void OnEnable() { Aplicar(); }
    void OnValidate() { Aplicar(); }

    void Aplicar()
    {
        if (rend == null) rend = GetComponent<Renderer>();
        if (bloque == null) bloque = new MaterialPropertyBlock();
        rend.GetPropertyBlock(bloque);
        bloque.SetFloat(IdRevelado, revelado);
        rend.SetPropertyBlock(bloque);
        rend.enabled = revelado > 0.001f || !Application.isPlaying;   // en juego, mientras esta oculto ni se dibuja
    }

    [ContextMenu("Probar revelado")]
    public void Revelar() { Mover(1f); }

    [ContextMenu("Ocultar")]
    public void Ocultar() { Mover(0f); }

    void Mover(float destino)
    {
        if (!Application.isPlaying) { revelado = destino; Aplicar(); return; }
        if (rutina != null) StopCoroutine(rutina);
        rutina = StartCoroutine(Animar(destino));
    }

    IEnumerator Animar(float destino)
    {
        float velocidad = 1f / Mathf.Max(0.1f, duracion);
        while (!Mathf.Approximately(revelado, destino))
        {
            revelado = Mathf.MoveTowards(revelado, destino, Time.deltaTime * velocidad);
            Aplicar();
            yield return null;
        }
        if (destino >= 1f) alRevelarse?.Invoke();
    }
}
