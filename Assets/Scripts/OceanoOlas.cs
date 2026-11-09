using UnityEngine;

/// <summary>
/// Hace que las olas del oceano cambien de tamano y fuerza con el tiempo
/// (equivale a los drivers del oceano en Blender).
/// </summary>
[ExecuteAlways]
public class OceanoOlas : MonoBehaviour
{
    public Material material;
    [Header("Tamano de las olas")] public float tamanoBase = 0.8f;
    public float tamanoVariacion = 0.35f;
    [Header("Fuerza (picos)")] public float fuerzaBase = 0.9f;
    public float fuerzaVariacion = 0.35f;
    [Tooltip("Segundos que dura un ciclo grande de cambio")] public float periodo = 60f;

    void Update()
    {
        if (material == null) return;
        float t = Application.isPlaying ? Time.time : (float)UnityEditor_Time();
        float w = 2f * Mathf.PI / periodo;
        material.SetFloat("_Amp", tamanoBase + tamanoVariacion * Mathf.Sin(t * w) + 0.12f * Mathf.Sin(t * w * 3.3f + 1.3f));
        material.SetFloat("_Fuerza", fuerzaBase + fuerzaVariacion * Mathf.Sin(t * w * 1.4f + 0.7f));
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
