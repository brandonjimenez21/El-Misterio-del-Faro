using UnityEngine;

/// <summary>
/// Hace parpadear suavemente una luz de fuego/aceite (llama de lampara, brasas de la caldera).
/// Opcionalmente tambien mueve la emision de un material (por ejemplo las brasas).
/// </summary>
[RequireComponent(typeof(Light))]
public class LuzParpadeo : MonoBehaviour
{
    [Tooltip("Cuanto varia la intensidad (0.2 = +-20 %)")] public float variacion = 0.25f;
    [Tooltip("Velocidad del parpadeo")] public float velocidad = 3f;
    [Tooltip("Mueve un poco la luz para que las sombras 'bailen'")] public float movimiento = 0.03f;
    [Header("Opcional: emision de un material")]
    public Renderer rendererEmisivo;
    public Color colorEmision = new Color(1f, 0.35f, 0.08f);
    public float intensidadEmision = 2f;

    Light luz;
    float intensidadBase;
    Vector3 posBase;
    float semilla;
    MaterialPropertyBlock bloque;

    void Awake()
    {
        luz = GetComponent<Light>();
        intensidadBase = luz.intensity;
        posBase = transform.localPosition;
        semilla = Random.value * 100f;
        if (rendererEmisivo != null) bloque = new MaterialPropertyBlock();
    }

    void Update()
    {
        float t = Time.time * velocidad + semilla;
        float n = Mathf.PerlinNoise(t, semilla) * 0.7f + Mathf.PerlinNoise(t * 2.7f, semilla + 5f) * 0.3f;   // 0..1
        float f = 1f + (n - 0.5f) * 2f * variacion;
        luz.intensity = intensidadBase * f;
        if (movimiento > 0f)
            transform.localPosition = posBase + new Vector3(Mathf.PerlinNoise(t, 1f) - 0.5f, Mathf.PerlinNoise(t, 2f) - 0.5f, Mathf.PerlinNoise(t, 3f) - 0.5f) * movimiento;
        if (rendererEmisivo != null)
        {
            rendererEmisivo.GetPropertyBlock(bloque);
            bloque.SetColor("_EmissionColor", colorEmision * intensidadEmision * f);
            rendererEmisivo.SetPropertyBlock(bloque);
        }
    }
}
