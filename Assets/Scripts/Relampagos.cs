using System.Collections;
using UnityEngine;

/// <summary>
/// Relampagos aleatorios: destello doble de una luz direccional + subida breve de la luz ambiente.
/// El trueno (AudioSource opcional) suena con retraso segun la "distancia" del rayo.
/// </summary>
public class Relampagos : MonoBehaviour
{
    public Light luzDestello;
    [Header("Tiempo entre relampagos (segundos)")]
    public float intervaloMin = 14f;
    public float intervaloMax = 40f;
    [Header("Destello")]
    public float intensidadPico = 5f;
    public float ambienteExtra = 2.5f;
    [Header("Trueno (opcional)")]
    public AudioSource trueno;
    public Vector2 distanciaKm = new Vector2(0.4f, 3f);

    float ambienteBase;

    void Start()
    {
        ambienteBase = RenderSettings.ambientIntensity;
        if (luzDestello != null) luzDestello.intensity = 0f;
        StartCoroutine(Bucle());
    }

    IEnumerator Bucle()
    {
        while (true)
        {
            yield return new WaitForSeconds(Random.Range(intervaloMin, intervaloMax));
            yield return Destello();
        }
    }

    [ContextMenu("Probar relampago")]
    public void Probar() { StartCoroutine(Destello()); }

    IEnumerator Destello()
    {
        if (luzDestello == null) yield break;
        luzDestello.transform.rotation = Quaternion.Euler(Random.Range(15f, 55f), Random.Range(0f, 360f), 0f);
        float km = Random.Range(distanciaKm.x, distanciaKm.y);
        if (trueno != null) trueno.PlayDelayed(km * 1000f / 343f);
        // pulsos: (duracion, fuerza)
        float[,] pulsos = { { 0.07f, 1f }, { 0.06f, 0.15f }, { 0.10f, 0.8f }, { 0.05f, 0.1f }, { 0.22f, 0.45f } };
        for (int i = 0; i < pulsos.GetLength(0); i++)
        {
            Aplicar(pulsos[i, 1]);
            yield return new WaitForSeconds(pulsos[i, 0]);
        }
        // desvanecer
        for (float t = 0f; t < 0.25f; t += Time.deltaTime) { Aplicar(0.3f * (1f - t / 0.25f)); yield return null; }
        Aplicar(0f);
    }

    void Aplicar(float f)
    {
        luzDestello.intensity = intensidadPico * f;
        RenderSettings.ambientIntensity = ambienteBase + ambienteExtra * f;
    }

    void OnDisable() { RenderSettings.ambientIntensity = ambienteBase > 0f ? ambienteBase : 1f; }
}
