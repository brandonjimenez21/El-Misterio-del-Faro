using UnityEngine;

/// <summary>
/// Linterna de mano que cuelga y se balancea como un pendulo. El modelo la trae atada a la muneca (se inclinaba con el brazo); aqui se la
/// vuelve a colgar hacia abajo desde el punto de agarre (el origen del objeto) y se le da inercia: el balanceo lo provoca la aceleracion de la
/// mano (pasos, giros de camara, el gesto de agarrar) mas un vaiven leve de respiracion. Se pone en el objeto Linterna_Mano.
/// </summary>
public class LinternaPendulo : MonoBehaviour
{
    [Tooltip("Rigidez del hilo: mas alto = oscila mas rapido (frecuencia ~ sqrt(rigidez))")] public float rigidez = 26f;
    [Tooltip("Frenado del balanceo")] public float amortiguacion = 2.6f;
    [Tooltip("Cuanto empuja la aceleracion de la mano")] public float empuje = 0.55f;
    [Tooltip("Inclinacion maxima (0.6 = ~30 grados)")] public float maximo = 0.7f;
    [Tooltip("Vaiven de reposo (respiracion)")] public float reposo = 0.035f;
    [Tooltip("Donde cuelga en reposo respecto a la vista: x = hacia la derecha, y = hacia delante (separa la linterna del antebrazo)")] public Vector2 inclinacionReposo = new Vector2(0.7f, -0.3f);

    Vector3 abajoLocal = Vector3.down;     // eje del objeto que apunta de la mano hacia el cuerpo de la linterna
    Vector3 desp, vel, posPrev, velPrev;
    bool listo;

    void Start() { Preparar(); }

    /// <summary>tambien la usa el editor para colgar la linterna en las capturas</summary>
    public void Preparar()
    {
        var r = GetComponent<Renderer>();
        var mf = GetComponent<MeshFilter>();
        Vector3 c = Vector3.zero;
        if (r is SkinnedMeshRenderer sk && sk.sharedMesh != null) c = sk.sharedMesh.bounds.center;
        else if (mf != null && mf.sharedMesh != null) c = mf.sharedMesh.bounds.center;
        if (c.sqrMagnitude > 1e-6f) abajoLocal = c.normalized;
        posPrev = transform.position;
    }

    void LateUpdate() { Actualizar(); }

    public void Actualizar()
    {
        float dt = Mathf.Max(Time.deltaTime, 1e-4f);
        dt = Mathf.Min(dt, 0.05f);
        Vector3 p = transform.position;
        Vector3 v = (p - posPrev) / dt;
        Vector3 acc = listo ? (v - velPrev) / dt : Vector3.zero;
        posPrev = p; velPrev = v; listo = true;
        acc = Vector3.ClampMagnitude(acc, 60f);

        // desp = desplazamiento horizontal del cuerpo de la linterna respecto a la vertical (1 = 45 grados aprox.)
        Vector3 fuerza = -rigidez * desp - amortiguacion * vel - empuje * new Vector3(acc.x, 0f, acc.z) * 0.12f;
        float t = Time.time;
        fuerza += new Vector3(Mathf.Sin(t * 1.3f), 0f, Mathf.Cos(t * 1.7f)) * reposo * rigidez;
        vel += fuerza * dt;
        desp += vel * dt;
        desp = Vector3.ClampMagnitude(new Vector3(desp.x, 0f, desp.z), maximo);

        Vector3 sesgo = Vector3.zero;
        var cam = Camera.main;
        if (cam != null)
        {
            var f = cam.transform.forward; f.y = 0f; f = f.sqrMagnitude > 1e-4f ? f.normalized : Vector3.forward;
            var d = cam.transform.right; d.y = 0f; d = d.sqrMagnitude > 1e-4f ? d.normalized : Vector3.right;
            sesgo = d * inclinacionReposo.x + f * inclinacionReposo.y;
        }
        Vector3 abajoMundo = (Vector3.down + desp + sesgo).normalized;
        Vector3 actual = transform.TransformDirection(abajoLocal);
        transform.rotation = Quaternion.FromToRotation(actual, abajoMundo) * transform.rotation;
    }
}
