using UnityEngine;

/// <summary>
/// Optimizacion: apaga los bloques de pasto (hijos) que estan lejos de la camara. Revisa solo 2 veces por segundo.
/// </summary>
public class PastoDistancia : MonoBehaviour
{
    [Tooltip("Distancia maxima a la que se dibuja el pasto (m)")] public float distanciaMax = 70f;
    [Tooltip("Solo se tocan los hijos cuyo nombre empieza asi")] public string prefijo = "Pasto";
    public float intervalo = 0.5f;

    Renderer[] bloques;
    float proximo;

    void OnEnable()
    {
        var lista = new System.Collections.Generic.List<Renderer>();
        foreach (var r in GetComponentsInChildren<Renderer>(true)) if (r.name.StartsWith(prefijo)) lista.Add(r);
        bloques = lista.ToArray();
    }

    void Update()
    {
        if (Time.time < proximo) return;
        proximo = Time.time + intervalo;
        var cam = Camera.main; if (cam == null) return;
        Vector3 p = cam.transform.position;
        float d2 = distanciaMax * distanciaMax;
        foreach (var r in bloques)
        {
            if (r == null) continue;
            r.enabled = r.bounds.SqrDistance(p) < d2;
        }
    }

    void OnDisable()
    {
        if (bloques == null) return;
        foreach (var r in bloques) if (r != null) r.enabled = true;
    }
}
