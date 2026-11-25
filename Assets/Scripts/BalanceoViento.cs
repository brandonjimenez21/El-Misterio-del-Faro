using UnityEngine;

/// <summary>
/// Balanceo con el viento para cosas colgadas (ropa del tendedero, cuerdas, carteles): el pivote es el punto de donde cuelga.
/// Sigue las rafagas del viento global (_FaroRafaga) y se queda quieto de golpe cuando el viento se corta (_FaroCalma).
/// </summary>
public class BalanceoViento : MonoBehaviour
{
    [Tooltip("Direccion del viento en XZ (la misma del pasto)")] public Vector2 direccionViento = new Vector2(0.86f, 0.5f);
    [Tooltip("Inclinacion media empujada por el viento (grados)")] public float inclinacion = 9f;
    [Tooltip("Amplitud del vaiven (grados)")] public float vaiven = 7f;
    public float velocidad = 1.3f;

    Quaternion baseRot;
    float semilla;
    static readonly int idCalma = Shader.PropertyToID("_FaroCalma");
    static readonly int idRafaga = Shader.PropertyToID("_FaroRafaga");

    void Start() { baseRot = transform.localRotation; semilla = Random.value * 50f; }

    void Update()
    {
        float calma = Shader.GetGlobalFloat(idCalma);
        float rafaga = Shader.GetGlobalFloat(idRafaga);
        float t = Time.time * velocidad + semilla;
        float racha = 0.6f + 0.4f * Mathf.Sin(t * 0.37f) * Mathf.Sin(t * 0.23f + 1.3f);
        float a = (inclinacion * racha + vaiven * (Mathf.Sin(t) * 0.7f + Mathf.Sin(t * 2.3f) * 0.3f)) * (1f + rafaga) * (1f - calma);
        // se inclina a favor del viento: giro alrededor del eje horizontal perpendicular al viento
        Vector3 eje = new Vector3(direccionViento.y, 0f, -direccionViento.x).normalized;
        transform.rotation = Quaternion.AngleAxis(a, eje) * (transform.parent != null ? transform.parent.rotation * baseRot : baseRot);
    }
}
