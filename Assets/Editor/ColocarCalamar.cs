using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

/// <summary>
/// Pone el calamar gigante (Peces/Calamar.fbx, ver blender/scripts/exportar_calamar.py) en las rocas altas del Puzle 2, al este de la isla,
/// con el script CalamarRocas: de reposo solo asoman los tentaculos trepando por las rocas y, al llegar el jugador al poste de piedra
/// (Puzle2_IslaAlterada/Poste_2_Origen_Base), surge. Menu: Faro > Importar > Calamar en las rocas (repetible; lo llama tambien ImportarPeces).
/// Todos los valores estan aqui: el importador los restablece.
/// </summary>
public static class ColocarCalamar
{
    const string DIR = "Assets/Models/Faro/Peces/";
    const string MAT = "Assets/Materials/Faro/";

    [MenuItem("Faro/Importar/Calamar en las rocas")]
    public static void Ejecutar()
    {
        var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(DIR + "Calamar.fbx");
        var ctrl = AssetDatabase.LoadAssetAtPath<AnimatorController>(DIR + "Calamar.controller");
        if (prefab == null || ctrl == null) { Debug.LogWarning("[Faro] Falta Calamar.fbx o su controlador: ejecuta antes Faro > Importar > Peces y tiburon"); return; }
        foreach (var n in new[] { "Calamar_Rocas", "Calamar" })        // "Calamar" = instancia suelta de versiones anteriores
        {
            var viejo = GameObject.Find(n);
            if (viejo != null) Object.DestroyImmediate(viejo);
        }
        var g = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
        g.name = "Calamar_Rocas";
        var an = g.GetComponent<Animator>();
        if (an == null) an = g.AddComponent<Animator>();
        an.runtimeAnimatorController = ctrl;
        an.applyRootMotion = false;
        an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        var bajo = AssetDatabase.LoadAssetAtPath<Material>(MAT + "M_Calamar_BajoAgua.mat");
        foreach (var r in g.GetComponentsInChildren<SkinnedMeshRenderer>())
        {
            r.updateWhenOffscreen = true;           // el cuerpo mide ~60 m y sus huesos se mueven: que los limites sigan a la animacion
            if (r.name == "body") r.sharedMaterials = new[] { r.sharedMaterial, bajo };
        }
        var c = g.AddComponent<CalamarRocas>();
        // el poste de piedra del Puzle 2 es "la torre": el calamar surge cuando el jugador llega a el
        var poste = GameObject.Find("Poste_2_Origen_Base");
        if (poste != null) { var p = poste.GetComponent<Renderer>().bounds.center; c.torre = new Vector3(p.x, 0f, p.z); }
        c.PonerReposo();
        UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(g.scene);
        Debug.Log("[Faro] Calamar colocado en las rocas del Puzle 2");
    }
}
