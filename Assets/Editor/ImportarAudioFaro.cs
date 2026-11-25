using UnityEditor;
using UnityEngine;

/// <summary>
/// Ajustes de importacion de los sonidos de Assets/SFX (se aplican solos al importar o reimportar):
///  - Clips largos (ambiente: lluvia, olas, susurros, pasos en grava...): Streaming + Vorbis calidad 50 %.
///    Asi no se cargan enteros en memoria (algunos pesan 50-100 MB en .wav).
///  - Clips cortos (pasos, respiracion, cuervos...): comprimidos en memoria, se cargan al instante.
///  - Los que suenan en 3D se pasan a mono (el sonido 3D no usa el estereo y ocupan la mitad).
/// Menu: Faro > Sonido > Reimportar audios de SFX
/// </summary>
public class ImportarAudioFaro : AssetPostprocessor
{
    const string Carpeta = "Assets/SFX/";
    // nombres (o parte) de los clips que se usan en 3D
    static readonly string[] Mono3D = { "waves", "gas-lantern", "crows", "whispers", "whale", "steps", "steponwood", "breath" };

    void OnPreprocessAudio()
    {
        if (!assetPath.StartsWith(Carpeta)) return;
        var imp = (AudioImporter)assetImporter;
        string n = System.IO.Path.GetFileName(assetPath).ToLower();
        long bytes = new System.IO.FileInfo(assetPath).Length;
        bool largo = bytes > 3 * 1024 * 1024;   // > ~15 s de audio en .wav
        // el siseo del farol suena en muchas luces a la vez: mejor en memoria que una lectura de disco por cada una
        if (n.Contains("gas-lantern")) largo = false;

        var s = imp.defaultSampleSettings;
        s.compressionFormat = AudioCompressionFormat.Vorbis;
        s.quality = largo ? 0.5f : 0.7f;
        s.loadType = largo ? AudioClipLoadType.Streaming : AudioClipLoadType.CompressedInMemory;
        s.preloadAudioData = !largo;
        s.sampleRateSetting = AudioSampleRateSetting.OptimizeSampleRate;
        imp.defaultSampleSettings = s;

        bool mono = false;
        foreach (var m in Mono3D) if (n.Contains(m)) { mono = true; break; }
        imp.forceToMono = mono;
        imp.loadInBackground = largo;
    }

    [MenuItem("Faro/Sonido/Reimportar audios de SFX")]
    static void Reimportar()
    {
        foreach (var guid in AssetDatabase.FindAssets("t:AudioClip", new[] { "Assets/SFX" }))
            AssetDatabase.ImportAsset(AssetDatabase.GUIDToAssetPath(guid), ImportAssetOptions.ForceUpdate);
        Debug.Log("[Faro] Audios de SFX reimportados");
    }
}
