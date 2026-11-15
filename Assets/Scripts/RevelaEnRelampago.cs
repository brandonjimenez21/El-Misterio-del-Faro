using UnityEngine;

/// <summary>
/// Cosas que cambian durante un relampago: en el primer fotograma del destello se activa/desactiva un objeto o se mueve,
/// y cuando vuelve la oscuridad ya esta distinto. El jugador no ve el cambio, solo nota que "algo esta distinto".
/// Cada cambio puede exigir que hayan pasado N relampagos y tiene su probabilidad.
/// </summary>
public class RevelaEnRelampago : MonoBehaviour
{
    public enum Tipo { Activar, Desactivar, Alternar, Girar, Mover }

    [System.Serializable]
    public class Cambio
    {
        public GameObject objeto;
        public Tipo tipo = Tipo.Activar;
        [Tooltip("No ocurre antes de este numero de relampagos")] public int despuesDeRelampagos = 1;
        [Range(0f, 1f)] public float probabilidad = 1f;
        [Tooltip("Para Girar: grados en Y. Para Mover: desplazamiento en metros")] public Vector3 valor = new Vector3(0f, 35f, 0f);
        [Tooltip("Solo se aplica una vez")] public bool unaVez = true;
        [HideInInspector] public bool hecho;
    }

    public Cambio[] cambios;
    int contador;

    void OnEnable() { Relampagos.AlRelampago += AlRelampago; }
    void OnDisable() { Relampagos.AlRelampago -= AlRelampago; }

    void AlRelampago()
    {
        contador++;
        if (cambios == null) return;
        foreach (var c in cambios)
        {
            if (c == null || c.objeto == null) continue;
            if (c.unaVez && c.hecho) continue;
            if (contador < c.despuesDeRelampagos) continue;
            if (Random.value > c.probabilidad) continue;
            c.hecho = true;
            var t = c.objeto.transform;
            switch (c.tipo)
            {
                case Tipo.Activar: c.objeto.SetActive(true); break;
                case Tipo.Desactivar: c.objeto.SetActive(false); break;
                case Tipo.Alternar: c.objeto.SetActive(!c.objeto.activeSelf); break;
                case Tipo.Girar: t.Rotate(c.valor, Space.World); break;
                case Tipo.Mover: t.position += c.valor; break;
            }
        }
    }
}
