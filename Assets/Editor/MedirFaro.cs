using System.Diagnostics;
using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Mide cuanto tarda en dibujarse un fotograma de la camara principal (1920x1080, con post-proceso) desde unas vistas fijas.
/// Sirve para comparar ajustes de rendimiento sin entrar en Play: Faro > Rendimiento > Medir vistas (resultado en la consola).
/// Dibuja UN fotograma por paso del editor (dibujar muchos seguidos en un mismo paso cuelga el backend DX12 del editor).
/// Es una medida relativa (ms por fotograma con la GPU a tope); los fps reales en el juego dependen ademas de los scripts.
/// </summary>
public static class MedirFaro
{
    public static readonly (string, Vector3, Vector3)[] vistas =
    {
        ("muelle", new Vector3(0f, 3.63f, 53f), new Vector3(0f, 12f, -40f)),
        ("prado", new Vector3(-10f, 9.6f, 20f), new Vector3(10f, 18f, -70f)),
        ("ladera", new Vector3(-30f, 9f, 10f), new Vector3(30f, 12f, -40f)),
        ("camino", new Vector3(1f, 5.4f, 30f), new Vector3(1.5f, 4.0f, 14f)),
    };

    const int CALENTAR = 6, MEDIR = 20;
    public static bool Ocupado { get; private set; }
    public static string Ultimo = "";

    static string etiqueta, archivo, linea;
    static int vista, paso;
    static float suma, minimo;
    static RenderTexture rt;
    static Texture2D tex;
    static Vector3 p0; static Quaternion r0;
    static System.Action alTerminar;

    [MenuItem("Faro/Rendimiento/Medir vistas")]
    static void Menu() { Iniciar("medida", null); }

    /// <summary>empieza a medir; el resultado sale en la consola, en MedirFaro.Ultimo y (si se da) se anade a 'archivoSalida'</summary>
    public static void Iniciar(string nombre, string archivoSalida, System.Action despues = null)
    {
        if (Ocupado || Camera.main == null) return;
        Ocupado = true; etiqueta = nombre; archivo = archivoSalida; alTerminar = despues;
        linea = ""; vista = 0; paso = 0; suma = 0; minimo = float.MaxValue;
        var cam = Camera.main;
        p0 = cam.transform.position; r0 = cam.transform.rotation;
        rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32);
        tex = new Texture2D(1, 1, TextureFormat.RGB24, false);
        EditorApplication.update += Paso;
    }

    static void Paso()
    {
        var cam = Camera.main;
        if (cam == null) { Fin(); return; }
        var v = vistas[vista];
        cam.transform.position = v.Item2; cam.transform.LookAt(v.Item3);
        var previo = cam.targetTexture;
        cam.targetTexture = rt;
        var sw = Stopwatch.StartNew();
        cam.Render();
        RenderTexture.active = rt;
        tex.ReadPixels(new Rect(0, 0, 1, 1), 0, 0);     // obliga a la GPU a terminar el fotograma
        RenderTexture.active = null;
        sw.Stop();
        cam.targetTexture = previo;
        cam.transform.position = p0; cam.transform.rotation = r0;
        float ms = (float)sw.Elapsed.TotalMilliseconds;
        if (paso >= CALENTAR) { suma += ms; minimo = Mathf.Min(minimo, ms); }
        paso++;
        if (paso >= CALENTAR + MEDIR)
        {
            linea += v.Item1 + " " + (suma / MEDIR).ToString("0.00") + " (min " + minimo.ToString("0.00") + ")  ";
            vista++; paso = 0; suma = 0; minimo = float.MaxValue;
            if (vista >= vistas.Length) Fin();
        }
    }

    static void Fin()
    {
        EditorApplication.update -= Paso;
        if (rt != null) Object.DestroyImmediate(rt);
        if (tex != null) Object.DestroyImmediate(tex);
        Ultimo = etiqueta + ": " + linea;
        UnityEngine.Debug.Log("[Faro] ms por fotograma (1080p) " + Ultimo);
        if (!string.IsNullOrEmpty(archivo)) File.AppendAllText(archivo, Ultimo + "\n");
        Ocupado = false;
        var a = alTerminar; alTerminar = null;
        if (a != null) a();
    }
}
