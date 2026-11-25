using UnityEngine;
using UnityEngine.Events;

/// <summary>
/// Calamar gigante de las rocas del Puzle 2. Mientras el jugador esta lejos, el cuerpo esta hundido detras de las rocas altas y solo se ven
/// los tentaculos saliendo del mar y trepando por ellas (reposo, animacion lenta). Cuando el jugador llega a la torre (el poste de piedra
/// del Puzle 2) el calamar SURGE: el cuerpo sube, el manto rompe el agua por detras de las rocas, los tentaculos se agitan rapido y se
/// lanza hacia delante. Pasado un rato se hunde otra vez y se rearma cuando el jugador se aleja.
/// El modelo mira hacia +Z local (los tentaculos van delante). Todo el movimiento es de este objeto; la animacion de nado la pone el Animator.
/// </summary>
public class CalamarRocas : MonoBehaviour
{
    [Header("Disparador")]
    [Tooltip("Punto de la torre (poste de piedra del Puzle 2); solo cuenta la distancia horizontal")] public Vector3 torre = new Vector3(24f, 0f, -1.8f);
    [Tooltip("El jugador activa al calamar a menos de estos metros de la torre")] public float radioActivacion = 24f;
    [Tooltip("Se rearma cuando el jugador se aleja mas de esto")] public float radioRearme = 55f;
    public Transform jugador;

    [Header("Poses (mundo)")]
    public Vector3 posOculto = new Vector3(64f, -6f, -9f);
    public Vector3 posSurge = new Vector3(46f, 30f, -7f);
    public Vector3 posEmbestida = new Vector3(35f, 45f, -3.3f);
    [Tooltip("Direccion de los tentaculos en cada fase (se normaliza)")]
    public Vector3 rumboOculto = new Vector3(-1f, 1.9f, 0f);
    public Vector3 rumboSurge = new Vector3(-1f, 0.85f, 0.05f);
    public Vector3 rumboEmbestida = new Vector3(-1f, 0.6f, 0.10f);

    [Header("Tiempos (s) y animacion")]
    public float tiempoSubida = 4f;
    public float tiempoEmbestida = 1.4f;
    public float tiempoArriba = 18f;
    public float tiempoHundido = 7f;
    public float velocidadAnimReposo = 0.5f;
    public float velocidadAnimSurge = 1.9f;
    public float oleaje = 0.4f;

    [Header("Eventos (sonido, temblor de camara...)")]
    public UnityEvent alSurgir;
    public UnityEvent alEmbestir;
    public UnityEvent alHundirse;

    public enum Fase { Oculto, Surgiendo, Embistiendo, Arriba, Hundiendo }
    public Fase fase { get; private set; } = Fase.Oculto;

    Animator anim;
    float t0;
    bool armado = true;
    Vector3 pDesde, pHasta;
    Quaternion qDesde, qHasta;
    static readonly int idNivelMar = Shader.PropertyToID("_FaroNivelMar");
    Transform oceano;

    void Start()
    {
        anim = GetComponent<Animator>();
        if (jugador == null && Camera.main != null) jugador = Camera.main.transform;
        var o = GameObject.Find("Oceano");
        if (o != null) oceano = o.transform;
        PonerReposo();
    }

    /// <summary>pose de reposo: cuerpo hundido, tentaculos subiendo por las rocas (tambien la llama el importador en modo edicion)</summary>
    public void PonerReposo()
    {
        fase = Fase.Oculto;
        transform.position = posOculto;
        transform.rotation = Rumbo(rumboOculto);
        if (anim == null) anim = GetComponent<Animator>();
        if (anim != null) anim.speed = velocidadAnimReposo;
    }

    static Quaternion Rumbo(Vector3 d) { return Quaternion.LookRotation(d.normalized, Vector3.up); }

    void Ir(Fase f, Vector3 pos, Quaternion rot)
    {
        fase = f;
        t0 = Time.time;
        pDesde = transform.position; qDesde = transform.rotation;
        pHasta = pos; qHasta = rot;
    }

    float DistTorre()
    {
        if (jugador == null) return float.MaxValue;
        var d = jugador.position - torre; d.y = 0f;
        return d.magnitude;
    }

    [ContextMenu("Surgir ahora")]
    public void Surgir()
    {
        if (fase != Fase.Oculto) return;
        armado = false;
        Ir(Fase.Surgiendo, posSurge, Rumbo(rumboSurge));
        if (anim != null) anim.speed = velocidadAnimSurge;
        alSurgir?.Invoke();
    }

    void Update()
    {
        if (oceano != null) Shader.SetGlobalFloat(idNivelMar, oceano.position.y);
        float d = DistTorre();
        if (fase == Fase.Oculto)
        {
            if (!armado && d > radioRearme) armado = true;
            if (armado && d < radioActivacion) Surgir();
            // respira: sube y baja con las olas
            transform.position = posOculto + Vector3.up * (Mathf.Sin(Time.time * 0.7f) * oleaje);
            return;
        }
        float dur = fase == Fase.Surgiendo ? tiempoSubida : fase == Fase.Embistiendo ? tiempoEmbestida : fase == Fase.Hundiendo ? tiempoHundido : tiempoArriba;
        float u = Mathf.Clamp01((Time.time - t0) / dur);
        float e = u * u * (3f - 2f * u);
        switch (fase)
        {
            case Fase.Surgiendo:
                Mover(e);
                if (u >= 1f) { Ir(Fase.Embistiendo, posEmbestida, Rumbo(rumboEmbestida)); alEmbestir?.Invoke(); }
                break;
            case Fase.Embistiendo:
                // arranque brusco, frenada suave
                Mover(1f - (1f - u) * (1f - u));
                if (u >= 1f) { fase = Fase.Arriba; t0 = Time.time; pDesde = pHasta = posEmbestida; }
                break;
            case Fase.Arriba:
                transform.position = posEmbestida + Vector3.up * (Mathf.Sin(Time.time * 0.8f) * oleaje * 2f);
                if (u >= 1f) { Ir(Fase.Hundiendo, posOculto, Rumbo(rumboOculto)); alHundirse?.Invoke(); if (anim != null) anim.speed = velocidadAnimReposo; }
                break;
            case Fase.Hundiendo:
                Mover(e);
                if (u >= 1f) PonerReposo();
                break;
        }
    }

    void Mover(float e)
    {
        transform.position = Vector3.Lerp(pDesde, pHasta, e);
        transform.rotation = Quaternion.Slerp(qDesde, qHasta, e);
    }

    void OnDrawGizmosSelected()
    {
        Gizmos.color = Color.red;
        Gizmos.DrawWireSphere(new Vector3(torre.x, 14f, torre.z), radioActivacion);
        Gizmos.color = Color.cyan;
        Gizmos.DrawWireSphere(posOculto, 3f); Gizmos.DrawWireSphere(posSurge, 3f); Gizmos.DrawWireSphere(posEmbestida, 3f);
    }
}
