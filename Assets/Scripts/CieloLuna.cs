using UnityEngine;

/// <summary>
/// Coloca la luna del cielo (shader Faro/CieloNocturno) en la direccion opuesta a la luz de la luna,
/// asi la luz direccional y el disco de la luna siempre coinciden.
/// </summary>
[ExecuteAlways]
public class CieloLuna : MonoBehaviour
{
    public Material cielo;
    public Light luz;

    void OnEnable() { Aplicar(); }
    void OnValidate() { Aplicar(); }
    void Update() { Aplicar(); }

    public void Aplicar()
    {
        if (cielo == null || luz == null) return;
        Vector3 d = -luz.transform.forward;
        cielo.SetVector("_DirLuna", new Vector4(d.x, d.y, d.z, 0f));
    }
}
