using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Saca capturas de la camara principal (con post-proceso) desde unas vistas fijas, para comparar cambios visuales.
/// La camara vuelve a su sitio al terminar. Menu: Faro > Capturas > Vistas de referencia (las guarda en Capturas/ junto a Assets).
/// Las capturas se ponen en cola y se dibuja UN fotograma por paso del editor: dibujar varios seguidos en un mismo paso
/// cuelga el backend DX12 del editor ("Unrecoverable GPU device error"). Por eso Una() vuelve enseguida y la imagen
/// aparece un momento despues (CapturaFaro.Pendientes dice cuantas faltan).
/// </summary>
public static class CapturaFaro
{
    // nombre, posicion de la camara, punto al que mira
    static readonly (string, Vector3, Vector3)[] vistas =
    {
        ("A_muelle", new Vector3(0f, 3.63f, 53f), new Vector3(-0.4f, 2.8f, 43f)),
        ("B_farol", new Vector3(-4f, 4.2f, 62f), new Vector3(2f, 5.0f, 55f)),
        ("C_playa", new Vector3(7f, 3.6f, 37f), new Vector3(2.6f, 2.6f, 30.6f)),
        ("D_cabana", new Vector3(-22f, 9.5f, -80f), new Vector3(-8f, 10f, -98f)),
    };

    // vistas para revisar el terreno y la hierba (a la altura de los ojos, mirando al suelo, ladera y rocas)
    static readonly (string, Vector3, Vector3)[] vistasTerreno =
    {
        ("T1_prado", new Vector3(-10f, 9.04f, 20f), new Vector3(-24f, 7.93f, 6f)),
        ("T2_ladera_hierba", new Vector3(-8f, 4.85f, 30f), new Vector3(-12f, 6.5f, 26f)),
        ("T3_camino", new Vector3(1f, 5.4f, 30f), new Vector3(1.5f, 4.0f, 14f)),
        ("T4_rocas", new Vector3(20f, 7.5f, 40f), new Vector3(34f, 6f, 20f)),
        ("T5_pies", new Vector3(-10f, 9.04f, 20f), new Vector3(-11.2f, 7.4f, 18.8f)),
        ("T6_sendero", new Vector3(-2f, 9.1f, 8f), new Vector3(-1f, 8.3f, -8f)),
    };

    class Pedido
    {
        public string carpeta, nombre; public Vector3 pos, mira; public int ancho, alto;
        public System.Action antes, despues;
    }

    static readonly Queue<Pedido> cola = new Queue<Pedido>();
    static Pedido actual;
    static int paso;
    static RenderTexture rt;
    static Vector3 p0; static Quaternion r0;
    static RenderTexture previo;
    const int ESPERA = 3;          // pasos del editor que se dejan pasar entre un dibujado y el siguiente

    /// <summary>capturas que faltan por hacer (0 = todas guardadas)</summary>
    public static int Pendientes { get { return cola.Count + (actual != null ? 1 : 0); } }

    [MenuItem("Faro/Capturas/Vistas del terreno")]
    static void MenuTerreno()
    {
        string carpeta = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Application.dataPath), "Capturas");
        Terreno(carpeta, System.DateTime.Now.ToString("MMdd_HHmm"));
        EditorUtility.RevealInFinder(carpeta);
    }

    public static void Terreno(string carpeta, string prefijo, int ancho = 1280, int alto = 720)
    {
        foreach (var v in vistasTerreno) Una(carpeta, prefijo + "_" + v.Item1, v.Item2, v.Item3, ancho, alto);
    }

    [MenuItem("Faro/Capturas/Vistas de referencia")]
    static void Menu()
    {
        string carpeta = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Application.dataPath), "Capturas");
        Vistas(carpeta, System.DateTime.Now.ToString("MMdd_HHmm"));
        EditorUtility.RevealInFinder(carpeta);
    }

    public static void Vistas(string carpeta, string prefijo, int ancho = 1280, int alto = 720)
    {
        foreach (var v in vistas) Una(carpeta, prefijo + "_" + v.Item1, v.Item2, v.Item3, ancho, alto);
    }

    /// <summary>pone una captura en cola. 'antes' se ejecuta justo antes de dibujarla (p. ej. cambiar la lluvia) y 'despues' al guardarla.</summary>
    public static void Una(string carpeta, string nombre, Vector3 pos, Vector3 mira, int ancho = 1280, int alto = 720,
                           System.Action antes = null, System.Action despues = null)
    {
        cola.Enqueue(new Pedido { carpeta = carpeta, nombre = nombre, pos = pos, mira = mira, ancho = ancho, alto = alto, antes = antes, despues = despues });
        EditorApplication.update -= Paso;
        EditorApplication.update += Paso;
    }

    static void Paso()
    {
        var cam = Camera.main;
        if (actual == null)
        {
            if (cola.Count == 0 || cam == null)
            {
                if (cam == null && cola.Count > 0) { Debug.LogWarning("[Faro] No hay camara principal"); cola.Clear(); }
                EditorApplication.update -= Paso;
                return;
            }
            actual = cola.Dequeue();
            paso = 0;
            return;
        }
        paso++;
        if (paso == ESPERA)
        {
            // primer dibujado (puede usar datos del fotograma anterior: no se guarda)
            if (actual.antes != null) actual.antes();
            System.IO.Directory.CreateDirectory(actual.carpeta);
            p0 = cam.transform.position; r0 = cam.transform.rotation;
            cam.transform.position = actual.pos; cam.transform.LookAt(actual.mira);
            rt = new RenderTexture(actual.ancho, actual.alto, 24, RenderTextureFormat.ARGB32);
            previo = cam.targetTexture;
            cam.targetTexture = rt;
            cam.Render();
            cam.targetTexture = previo;
        }
        else if (paso == ESPERA * 2)
        {
            // segundo dibujado: este se guarda
            cam.targetTexture = rt;
            cam.Render();
            RenderTexture.active = rt;
            var tex = new Texture2D(actual.ancho, actual.alto, TextureFormat.RGB24, false);
            tex.ReadPixels(new Rect(0, 0, actual.ancho, actual.alto), 0, 0); tex.Apply();
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(actual.carpeta, actual.nombre + ".png"), tex.EncodeToPNG());
            RenderTexture.active = null; cam.targetTexture = previo;
            Object.DestroyImmediate(rt); Object.DestroyImmediate(tex);
            cam.transform.position = p0; cam.transform.rotation = r0;
            var d = actual.despues;
            actual = null;
            if (d != null) d();
        }
    }
}
