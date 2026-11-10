using UnityEngine;

/// <summary>
/// Oleaje y marea del oceano: las olas cambian de tamano y fuerza con el tiempo
/// (equivale a los drivers del oceano en Blender) y el nivel del mar sube y baja despacio (marea).
/// La cubierta del muelle esta a y=1.22; con estos valores la cresta mas alta queda por debajo.
/// </summary>
[ExecuteAlways]
public class OceanoOlas : MonoBehaviour
{
    public Material material;
    [Header("Tamano de las olas")] public float tamanoBase = 0.95f;
    public float tamanoVariacion = 0.2f;
    [Header("Fuerza (picos)")] public float fuerzaBase = 1.15f;
    public float fuerzaVariacion = 0.3f;
    [Tooltip("Segundos que dura un ciclo grande de cambio")] public float periodo = 45f;
    [Header("Marea (sube y baja el nivel del mar)")]
    public float amplitudMarea = 0.3f;
    [Tooltip("Segundos que dura un ciclo completo de marea")] public float periodoMarea = 180f;
    public float nivelBase = -0.55f;

    void Update()
    {
        if (material == null) return;
        float t = Application.isPlaying ? Time.time : (float)UnityEditor_Time();
        float w = 2f * Mathf.PI / periodo;
        material.SetFloat("_Amp", tamanoBase + tamanoVariacion * Mathf.Sin(t * w) + 0.1f * Mathf.Sin(t * w * 3.3f + 1.3f));
        material.SetFloat("_Fuerza", fuerzaBase + fuerzaVariacion * Mathf.Sin(t * w * 1.4f + 0.7f));
        var p = transform.position;
        p.y = nivelBase + amplitudMarea * Mathf.Sin(t * 2f * Mathf.PI / periodoMarea);
        transform.position = p;
    }

    static double UnityEditor_Time()
    {
#if UNITY_EDITOR
        return UnityEditor.EditorApplication.timeSinceStartup;
#else
        return Time.time;
#endif
    }
}
