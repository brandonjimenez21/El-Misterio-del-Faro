using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// <summary>
/// Prueba de la calidad automatica (CalidadAutomatica.cs): Faro > Rendimiento > Probar calidad automatica.
/// Entra en Play, mide los fps, obliga a bajar de nivel pidiendo unos fps imposibles, comprueba que vuelve a subir y sale de Play.
/// El resultado queda en la consola y en Temp/PruebaCalidadFaro.txt. Sobrevive a la recarga de scripts al entrar en Play.
/// </summary>
[InitializeOnLoad]
public static class PruebaCalidadFaro
{
    const string CLAVE = "Faro.PruebaCalidad";
    public static string Archivo { get { return Path.Combine(Path.GetDirectoryName(Application.dataPath), "Temp", "PruebaCalidadFaro.txt"); } }

    static double t0; static int f0, fase; static CalidadAutomatica ca;

    static PruebaCalidadFaro()
    {
        EditorApplication.playModeStateChanged += Cambio;
        if (SessionState.GetBool(CLAVE, false) && EditorApplication.isPlaying) Empezar();
    }

    [MenuItem("Faro/Rendimiento/Probar calidad automatica")]
    public static void Iniciar()
    {
        File.WriteAllText(Archivo, "");
        SessionState.SetBool(CLAVE, true);
        if (EditorApplication.isPlaying) Empezar(); else EditorApplication.EnterPlaymode();
    }

    static void Linea(string s) { File.AppendAllText(Archivo, s + "\n"); Debug.Log("[Faro] " + s); }

    static void Cambio(PlayModeStateChange c)
    {
        if (!SessionState.GetBool(CLAVE, false)) return;
        if (c == PlayModeStateChange.EnteredPlayMode) Empezar();
        if (c == PlayModeStateChange.EnteredEditMode)
        {
            var a = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
            Linea("fuera de Play (fase " + fase + "): escala " + a.renderScale.ToString("0.00") + " sombras " + a.shadowDistance.ToString("0") + "  FIN");
            SessionState.SetBool(CLAVE, false);
            EditorApplication.update -= Paso;
        }
    }

    static void Empezar()
    {
        fase = 0; t0 = EditorApplication.timeSinceStartup;
        EditorApplication.update -= Paso;
        EditorApplication.update += Paso;
    }

    static string Estado()
    {
        var a = GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
        return "nivel " + ca.nivel + ", escala " + a.renderScale.ToString("0.00") + ", sombras " + a.shadowDistance.ToString("0") + " m, pasos de niebla " + NieblaVolumetricaFeature.LimitePasos + ", recorte de hierba " + CalidadAutomatica.RecorteHierba;
    }

    static void Paso()
    {
        if (!EditorApplication.isPlaying) return;
        if (ca == null) ca = Object.FindFirstObjectByType<CalidadAutomatica>();
        if (ca == null) return;
        double t = EditorApplication.timeSinceStartup - t0;
        if (fase == 0 && t > 6) { fase = 1; t0 = EditorApplication.timeSinceStartup; f0 = Time.frameCount; }
        else if (fase == 1 && t > 4) { Linea("calidad completa: " + ((Time.frameCount - f0) / t).ToString("0") + " fps (" + Screen.width + "x" + Screen.height + ") | " + Estado()); ca.fpsObjetivo = 1000f; fase = 2; t0 = EditorApplication.timeSinceStartup; }
        else if (fase == 2 && t > 16) { Linea("pidiendo 1000 fps durante 16 s: " + Estado()); fase = 3; t0 = EditorApplication.timeSinceStartup; f0 = Time.frameCount; }
        else if (fase == 3 && t > 4) { Linea("nivel mas ligero: " + ((Time.frameCount - f0) / t).ToString("0") + " fps"); ca.fpsObjetivo = 60f; fase = 4; t0 = EditorApplication.timeSinceStartup; }
        else if (fase == 4 && t > 45) { Linea("de vuelta a 60 fps durante 45 s: " + Estado()); fase = 5; EditorApplication.ExitPlaymode(); }
    }
}
