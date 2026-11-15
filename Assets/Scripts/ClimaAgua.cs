using UnityEngine;

/// <summary>
/// Agua del clima: la lluvia cambia de fuerza (chaparrones), los charcos se van llenando mientras llueve
/// y de vez en cuando llega una ola grande desde el mar que sube por la costa y deja la orilla mojada.
/// Todo se pasa a los shaders como variables globales:
///   _FaroLluvia      fuerza de la lluvia ahora (0..1)                        -> anillos en charcos, mar y suelo
///   _FaroCharcos     cuanta agua se ha juntado (0..1)                         -> Charco.shader y charcos del suelo (IslaDetalle)
///   _FaroOla/_FaroOla2               la ola grande que viene (Oceano.shader)
///   _FaroOlaMojado/_FaroOlaMojado2   hasta donde mojo la ultima ola (IslaDetalle)
/// </summary>
[ExecuteAlways]
public class ClimaAgua : MonoBehaviour
{
    [Header("Lluvia")]
    public LluviaSigueCamara lluvia;
    [Range(0f, 1f)] public float lluviaMin = 0.55f;
    [Range(0f, 1f)] public float lluviaMax = 1f;
    [Tooltip("Segundos que tarda un ciclo de chaparron (la lluvia arrecia y afloja)")] public float periodoChaparron = 75f;

    [Header("Charcos")]
    [Tooltip("Agua acumulada al empezar (0..1)")] [Range(0f, 1f)] public float charcosInicio = 0.3f;
    [Tooltip("Segundos de lluvia fuerte para llenar los charcos del todo")] public float segundosLlenar = 260f;
    [Tooltip("Segundos sin lluvia para que se sequen del todo")] public float segundosSecar = 900f;

    [Header("Olas grandes")]
    public bool olasGrandes = true;
    [Tooltip("Segundos entre una ola grande y la siguiente (min, max)")] public Vector2 intervalo = new Vector2(35f, 85f);
    [Tooltip("Cuanto sube el agua en la ola grande (m, min y max)")] public Vector2 altura = new Vector2(0.9f, 1.45f);
    [Tooltip("Velocidad con la que avanza (m/s)")] public float velocidadOla = 7f;
    [Tooltip("Largo de la ola en la direccion en que avanza (m)")] public float anchoOla = 15f;
    [Tooltip("Largo de la ola a lo ancho (m)")] public float anchoLateral = 55f;
    [Tooltip("Desde que distancia antes de la costa aparece (m)")] public float distanciaInicio = 150f;
    [Tooltip("Cuantos metros pasa la costa antes de deshacerse")] public float pasaCosta = 22f;
    [Tooltip("Segundos que tarda en secarse lo que mojo")] public float secadoOla = 50f;
    [Tooltip("Probabilidad de que la ola vaya a la costa mas cercana a la camara (para que se vea)")] [Range(0f, 1f)] public float cercaDeLaCamara = 0.65f;
    [Tooltip("Centro de la isla (x, z)")] public Vector2 centroIsla = new Vector2(2.6f, -46f);
    [Tooltip("Puntos de la orilla (a nivel del mar) a donde pueden llegar las olas")] public Vector3[] puntosCosta;

    [Header("Estado (solo lectura)")]
    [Range(0f, 1f)] public float lluviaAhora = 1f;
    [Range(0f, 1f)] public float charcos;

    // ola en curso
    Vector2 dir = new Vector2(0f, 1f);
    float frente, xObjetivo, latCentro, fuerzaPico, fuerzaAhora, siguienteOla;
    bool activa;
    // lo que mojo la ultima ola
    Vector2 dirMojado = new Vector2(0f, 1f);
    float xMojado, latMojado, altoMojado, frenteMojado;
    bool iniciado, mojadoEsDeEstaOla;

    static ClimaAgua instancia;

    static readonly int idLluvia = Shader.PropertyToID("_FaroLluvia");
    static readonly int idCharcos = Shader.PropertyToID("_FaroCharcos");
    static readonly int idOla = Shader.PropertyToID("_FaroOla");
    static readonly int idOla2 = Shader.PropertyToID("_FaroOla2");
    static readonly int idMoj = Shader.PropertyToID("_FaroOlaMojado");
    static readonly int idMoj2 = Shader.PropertyToID("_FaroOlaMojado2");

    void OnEnable()
    {
        instancia = this;
        charcos = charcosInicio;
        iniciado = false;
    }

    void OnDisable()
    {
        if (instancia == this) instancia = null;
        Shader.SetGlobalFloat(idLluvia, 0f);
        Shader.SetGlobalFloat(idCharcos, 0f);
        Shader.SetGlobalVector(idOla, Vector4.zero);
        Shader.SetGlobalVector(idMoj2, Vector4.zero);
    }

    void Update()
    {
        if (!Application.isPlaying)
        {
            // en el editor: lluvia fuerte, charcos a medio llenar y sin olas (para ver la escena)
            lluviaAhora = lluviaMax;
            charcos = charcosInicio;
            activa = false; fuerzaAhora = 0f; altoMojado = 0f;
            Enviar();
            return;
        }
        if (!iniciado)
        {
            iniciado = true;
            siguienteOla = Time.time + Random.Range(12f, 25f);   // la primera llega pronto
        }
        float dt = Time.deltaTime;

        // chaparrones: dos senos lentos desfasados, nunca deja de llover
        float t = Time.time / Mathf.Max(periodoChaparron, 1f) * 2f * Mathf.PI;
        float k = 0.5f + 0.32f * Mathf.Sin(t) + 0.18f * Mathf.Sin(t * 2.71f + 1.9f);
        lluviaAhora = Mathf.Lerp(lluviaMin, lluviaMax, Mathf.Clamp01(k));
        if (lluvia != null) lluvia.intensidad = lluviaAhora;

        // los charcos se llenan con la lluvia y se secan despacio cuando afloja
        float llenar = lluviaAhora / Mathf.Max(segundosLlenar, 1f);
        float secar = (1f - lluviaAhora) / Mathf.Max(segundosSecar, 1f);
        charcos = Mathf.Clamp01(charcos + (llenar * (1f - charcos * 0.35f) - secar) * dt);

        // olas grandes
        if (olasGrandes && !activa && Time.time >= siguienteOla) Lanzar();
        if (activa)
        {
            frente += velocidadOla * dt;
            float desdeInicio = frente - (xObjetivo - distanciaInicio);
            float entra = Mathf.SmoothStep(0f, 1f, desdeInicio / 45f);                 // crece al salir del mar abierto
            float sale = 1f - Mathf.SmoothStep(0f, 1f, (frente - xObjetivo) / pasaCosta); // se deshace al pasar la orilla
            fuerzaAhora = fuerzaPico * entra * sale;
            // al llegar a la orilla, lo que moja pasa a ser esta ola
            if (frente >= xObjetivo - anchoOla)
            {
                if (!mojadoEsDeEstaOla)
                {
                    mojadoEsDeEstaOla = true;
                    dirMojado = dir; xMojado = xObjetivo; latMojado = latCentro; altoMojado = 0f; frenteMojado = float.MinValue;
                }
                altoMojado = Mathf.Max(altoMojado, fuerzaAhora);
                frenteMojado = Mathf.Max(frenteMojado, frente + anchoOla * 0.5f);
            }
            if (frente > xObjetivo + pasaCosta)
            {
                activa = false; fuerzaAhora = 0f;
                siguienteOla = Time.time + Random.Range(intervalo.x, intervalo.y);
            }
        }
        // lo mojado se seca poco a poco
        altoMojado *= Mathf.Exp(-dt / Mathf.Max(secadoOla, 1f));
        Enviar();
    }

    void Lanzar()
    {
        if (puntosCosta == null || puntosCosta.Length == 0) { siguienteOla = Time.time + intervalo.y; return; }
        Vector3 objetivo = puntosCosta[Random.Range(0, puntosCosta.Length)];
        var cam = Camera.main;
        if (cam != null && Random.value < cercaDeLaCamara)
        {
            float mejor = float.MaxValue;
            Vector2 c = new Vector2(cam.transform.position.x, cam.transform.position.z);
            foreach (var p in puntosCosta)
            {
                float d = (new Vector2(p.x, p.z) - c).sqrMagnitude;
                if (d < mejor) { mejor = d; objetivo = p; }
            }
        }
        Vector2 obj = new Vector2(objetivo.x, objetivo.z);
        Vector2 hacia = (centroIsla - obj).normalized;                       // del mar hacia la isla
        float giro = Random.Range(-28f, 28f) * Mathf.Deg2Rad;
        dir = new Vector2(hacia.x * Mathf.Cos(giro) - hacia.y * Mathf.Sin(giro), hacia.x * Mathf.Sin(giro) + hacia.y * Mathf.Cos(giro));
        xObjetivo = Vector2.Dot(dir, obj);
        latCentro = Vector2.Dot(new Vector2(-dir.y, dir.x), obj);
        frente = xObjetivo - distanciaInicio;
        fuerzaPico = Random.Range(altura.x, altura.y);
        mojadoEsDeEstaOla = false;
        activa = true;
    }

    void Enviar()
    {
        Shader.SetGlobalFloat(idLluvia, lluviaAhora);
        Shader.SetGlobalFloat(idCharcos, charcos);
        Shader.SetGlobalVector(idOla, new Vector4(dir.x, dir.y, frente, fuerzaAhora));
        Shader.SetGlobalVector(idOla2, new Vector4(anchoOla, latCentro, anchoLateral, 0f));
        Shader.SetGlobalVector(idMoj, new Vector4(dirMojado.x, dirMojado.y, xMojado, latMojado));
        Shader.SetGlobalVector(idMoj2, new Vector4(altoMojado, anchoLateral, frenteMojado, pasaCosta));
    }

    /// <summary>Cuanto sube el agua por la ola grande en un punto (m). Lo usan los objetos que flotan.</summary>
    public static float AlturaOla(Vector3 p)
    {
        var c = instancia;
        if (c == null || !c.activa || c.fuerzaAhora <= 0.001f) return 0f;
        Vector2 q = new Vector2(p.x, p.z);
        float x = Vector2.Dot(c.dir, q) - c.frente;
        float s = x > 0f ? c.anchoOla * 0.55f : c.anchoOla;     // el frente es mas empinado que la espalda
        float lt = (Vector2.Dot(new Vector2(-c.dir.y, c.dir.x), q) - c.latCentro) / c.anchoLateral;
        return c.fuerzaAhora * Mathf.Exp(-x * x / (s * s)) * Mathf.Exp(-lt * lt);
    }

    public static float LluviaAhora => instancia != null ? instancia.lluviaAhora : 0f;

    /// <summary>Lanza una ola grande ya (para probar).</summary>
    [ContextMenu("Lanzar ola grande ahora")]
    public void LanzarAhora() { if (Application.isPlaying) Lanzar(); }

#if UNITY_EDITOR
    /// <summary>Busca en la malla de la isla los puntos de la orilla (a nivel del mar), uno por sector alrededor del centro.</summary>
    [ContextMenu("Calcular puntos de la costa")]
    public void CalcularCosta()
    {
        var isla = GameObject.Find("Isla");
        if (isla == null) return;
        var mf = isla.GetComponent<MeshFilter>();
        var v = mf.sharedMesh.vertices;
        var b = isla.GetComponent<Renderer>().bounds;
        centroIsla = new Vector2(b.center.x, b.center.z);
        const int sectores = 24;
        var mejor = new Vector3[sectores];
        var dist = new float[sectores];
        for (int i = 0; i < sectores; i++) dist[i] = -1f;
        foreach (var lv in v)
        {
            var w = isla.transform.TransformPoint(lv);
            if (w.y < -0.9f || w.y > 0.2f) continue;
            var d = new Vector2(w.x, w.z) - centroIsla;
            int s = Mathf.Clamp((int)((Mathf.Atan2(d.y, d.x) + Mathf.PI) / (2f * Mathf.PI) * sectores), 0, sectores - 1);
            if (d.magnitude > dist[s]) { dist[s] = d.magnitude; mejor[s] = w; }
        }
        var lista = new System.Collections.Generic.List<Vector3>();
        for (int i = 0; i < sectores; i++) if (dist[i] > 0f) lista.Add(mejor[i]);
        puntosCosta = lista.ToArray();
        UnityEditor.EditorUtility.SetDirty(this);
    }
#endif
}
