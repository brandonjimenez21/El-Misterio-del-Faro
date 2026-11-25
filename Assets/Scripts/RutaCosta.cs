using UnityEngine;

/// <summary>
/// Contorno de la costa (isla + muelle + rocas) en polares alrededor de "centro": radios[i] = distancia de la orilla en la direccion i.
/// Lo calcula el menu Faro > Importar > Peces y tiburon a partir de las mallas; lo usan los peces y el tiburon (NadoCosta) para
/// rodear la isla entera y para saber si el jugador esta cerca de la orilla.
/// </summary>
public class RutaCosta : MonoBehaviour
{
    public Vector2 centro;
    public float[] radios = new float[0];

    public float Radio(float ang)
    {
        int n = radios.Length;
        if (n == 0) return 100f;
        float t = Mathf.Repeat(ang / (2f * Mathf.PI), 1f) * n;
        int i = (int)t;
        return Mathf.Lerp(radios[i % n], radios[(i + 1) % n], t - i);
    }

    /// <summary>punto a "margen" metros mar adentro de la orilla (y = 0)</summary>
    public Vector3 Punto(float ang, float margen)
    {
        float r = Radio(ang) + margen;
        return new Vector3(centro.x + Mathf.Cos(ang) * r, 0f, centro.y + Mathf.Sin(ang) * r);
    }

    public float Angulo(Vector3 p) { return Mathf.Atan2(p.z - centro.y, p.x - centro.x); }

    /// <summary>metros hasta la orilla: negativo = tierra adentro, positivo = en el mar</summary>
    public float DistanciaACosta(Vector3 p)
    {
        float d = new Vector2(p.x - centro.x, p.z - centro.y).magnitude;
        return d - Radio(Angulo(p));
    }

    void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.cyan;
        for (int m = 0; m < 2; m++)
        {
            float margen = m * 14f;
            Vector3 a = Punto(0f, margen);
            for (int i = 1; i <= 240; i++)
            {
                Vector3 b = Punto(i / 240f * 2f * Mathf.PI, margen);
                Gizmos.DrawLine(a, b);
                a = b;
            }
            Gizmos.color = Color.yellow;
        }
    }
}
