using System.Collections;
using UnityEngine;
using UnityEngine.Events;

/// <summary>
/// Roca que corta el sendero al faro hasta resolver el Puzle 2 (los tres postes de navegacion). Mientras esta cerrada, el muro invisible
/// "Muro_Sendero" (de orilla a orilla) impide rodearla. Abrir() la hunde despacio en el suelo (piedra deslizandose) y quita el muro.
/// Llamalo desde el puzle: GetComponent&lt;BloqueoSendero&gt;().Abrir(). En el editor, menu del componente: "Abrir ahora".
/// </summary>
public class BloqueoSendero : MonoBehaviour
{
    public GameObject muro;
    [Tooltip("Metros que baja la roca al abrirse")] public float hundimiento = 9f;
    public float duracion = 7f;
    public UnityEvent alAbrirse;
    public bool Abierto { get; private set; }

    [ContextMenu("Abrir ahora")]
    public void Abrir()
    {
        if (Abierto) return;
        Abierto = true;
        StartCoroutine(Hundir());
    }

    IEnumerator Hundir()
    {
        var a = transform.position; var b = a + Vector3.down * hundimiento;
        for (float t = 0f; t < duracion; t += Time.deltaTime)
        {
            float u = t / duracion;
            transform.position = Vector3.Lerp(a, b, u * u * (3f - 2f * u)) + new Vector3(Mathf.Sin(t * 40f), 0f, Mathf.Cos(t * 37f)) * 0.03f * (1f - u);
            yield return null;
        }
        transform.position = b;
        if (muro != null) muro.SetActive(false);
        var c = GetComponent<Collider>(); if (c != null) c.enabled = false;
        alAbrirse?.Invoke();
    }
}
