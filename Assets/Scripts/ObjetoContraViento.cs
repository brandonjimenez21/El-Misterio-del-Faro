using UnityEngine;

/// <summary>
/// Algo que se mece CONTRA el viento (el viento sopla hacia +X/+Z y esto se inclina hacia el otro lado),
/// y se queda inmovil de golpe cuando el viento se corta (ReaccionViento.Calmar).
/// Pensado para una cuerda, un cartel, una cadena: pequeño detalle "mal" sin explicacion.
/// </summary>
public class ObjetoContraViento : MonoBehaviour
{
    public Vector2 direccionViento = new Vector2(0.86f, 0.5f);
    public float grados = 7f;
    public float velocidad = 0.9f;
    float semilla;
    Quaternion baseRot;
    static readonly int idCalma = Shader.PropertyToID("_FaroCalma");

    void Start() { baseRot = transform.localRotation; semilla = Random.value * 20f; }

    void Update()
    {
        float calma = Shader.GetGlobalFloat(idCalma);
        float ola = 0.5f + 0.5f * Mathf.Sin(Time.time * velocidad + semilla);
        float a = grados * (0.4f + 0.6f * ola) * (1f - calma);
        // eje de giro perpendicular a la direccion del viento: se inclina HACIA el viento con signo negativo
        Vector3 eje = new Vector3(direccionViento.y, 0f, -direccionViento.x).normalized;
        transform.localRotation = Quaternion.AngleAxis(-a, eje) * baseRot;
    }
}
