using UnityEngine;

/// <summary>Empieza la animacion de nado en un punto distinto del ciclo, para que los peces de un banco no se muevan todos a la vez.</summary>
[RequireComponent(typeof(Animator))]
public class DesfaseNado : MonoBehaviour
{
    [Range(0f, 1f)] public float desfase;

    void Start()
    {
        var an = GetComponent<Animator>();
        if (an != null && an.runtimeAnimatorController != null) an.Play(0, 0, desfase);
    }
}
