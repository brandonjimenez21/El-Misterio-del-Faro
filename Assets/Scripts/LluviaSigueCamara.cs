using UnityEngine;

/// <summary>
/// Mantiene los sistemas de particulas de lluvia y de viento sobre la camara principal (asi funcionan con cualquier
/// personaje) y apaga la lluvia dentro de la cabana y la torre (zonas con BoxCollider marcadas como interior).
/// </summary>
public class LluviaSigueCamara : MonoBehaviour
{
    [Header("Particulas")]
    public ParticleSystem lluvia;
    public ParticleSystem polvoViento;
    [Tooltip("Altura sobre la camara desde donde cae la lluvia")] public float altura = 16f;

    [Header("Intensidad")]
    [Range(0f, 1f)] public float intensidad = 1f;
    public float emisionLluvia = 1800f;
    public float emisionViento = 40f;
    [Tooltip("Fuerza lateral del viento sobre la lluvia")] public float viento = 3f;

    [Header("Interior")]
    [Tooltip("Zonas donde NO llueve (cabana, torre). Se usan los limites de sus colliders")]
    public Collider[] zonasInterior;
    public float suavizado = 3f;

    float factorInterior = 1f;   // 1 = fuera, 0 = dentro
    Transform cam;

    void LateUpdate()
    {
        if (cam == null) { if (Camera.main != null) cam = Camera.main.transform; else return; }
        Vector3 p = cam.position;
        bool dentro = false;
        if (zonasInterior != null)
            foreach (var z in zonasInterior) if (z != null && z.bounds.Contains(p)) { dentro = true; break; }
        factorInterior = Mathf.MoveTowards(factorInterior, dentro ? 0f : 1f, Time.deltaTime * suavizado);

        if (lluvia != null)
        {
            lluvia.transform.position = p + Vector3.up * altura;
            var em = lluvia.emission; em.rateOverTimeMultiplier = emisionLluvia * intensidad * factorInterior;
            var f = lluvia.forceOverLifetime; f.enabled = true; f.x = viento * 8f; f.y = 0f; f.z = viento * 3f; f.space = ParticleSystemSimulationSpace.World;
            if (!lluvia.isPlaying) lluvia.Play();
        }
        if (polvoViento != null)
        {
            polvoViento.transform.position = p;
            var em = polvoViento.emission; em.rateOverTimeMultiplier = emisionViento * Mathf.Max(0.2f, factorInterior);
            if (!polvoViento.isPlaying) polvoViento.Play();
        }
    }
}
