using System.Collections;
using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Sonido de ambiente de la isla. Va en el objeto "Sonido" y crea solo sus AudioSource al empezar.
///  - Lluvia: dos capas en bucle (fuerte y suave) que siguen a los chaparrones de ClimaAgua.
///    Dentro de la cabana o la torre baja de volumen y suena apagada (filtro de graves).
///  - Olas: varias fuentes que se colocan en los puntos de la costa mas cercanos a la camara.
///    Cuando rompe una ola grande (ClimaAgua.AlRomperOla) suena un golpe de agua fuerte en ese punto.
///  - Faroles: el siseo del farol de gas en cada luz de aceite cercana.
///  - Cuervos: de vez en cuando, desde uno de los arboles secos.
///  - Terror: susurros donde aparece la figura (FiguraDistante.AlAparecer) y respiracion del jugador
///    cuando la figura ya esta cerca; una "ballena" muy lejana y grave cada pocos minutos.
/// Todos los clips son opcionales: si falta uno, esa parte no suena.
/// </summary>
public class SonidoAmbiente : MonoBehaviour
{
    [Header("Referencias (se buscan solas si estan vacias)")]
    public ClimaAgua clima;
    public LluviaSigueCamara lluviaCamara;

    [Header("Lluvia")]
    public AudioClip lluviaFuerte;
    public AudioClip lluviaSuave;
    [Range(0f, 1f)] public float volumenLluvia = 0.8f;
    [Tooltip("Volumen que queda bajo techo (0..1 del de fuera)")] [Range(0f, 1f)] public float lluviaBajoTecho = 0.4f;
    [Tooltip("Frecuencia de corte del filtro bajo techo (Hz): mas bajo = mas apagado")] public float corteBajoTecho = 900f;

    [Header("Olas en la orilla")]
    public AudioClip olas;
    [Range(0f, 1f)] public float volumenOlas = 0.75f;
    [Tooltip("Cuantos puntos de la costa suenan a la vez (los mas cercanos a la camara)")] [Range(1, 6)] public int fuentesOlas = 3;
    public float distanciaOlas = 110f;
    [Range(0f, 1f)] public float volumenOlaGrande = 1f;

    [Header("Faroles de aceite / gas")]
    public AudioClip farol;
    [Range(0f, 1f)] public float volumenFarol = 0.35f;
    [Tooltip("Luces que sisean (por defecto: las que tengan LuzParpadeo y no esten en la torre ni sean brasas)")] public Transform[] faroles;
    public float distanciaFarol = 9f;

    [Header("Cuervos")]
    public AudioClip cuervos;
    [Range(0f, 1f)] public float volumenCuervos = 0.45f;
    [Tooltip("Desde donde graznan (por defecto los arboles secos)")] public Transform[] posicionesCuervos;
    [Tooltip("Segundos entre graznidos (min, max)")] public Vector2 intervaloCuervos = new Vector2(80f, 220f);

    [Header("Terror")]
    public AudioClip susurros;
    [Range(0f, 1f)] public float volumenSusurros = 0.4f;
    public AudioClip respiracion;
    [Range(0f, 1f)] public float volumenRespiracion = 0.55f;
    [Tooltip("A partir de esta cercania (0..1) de la figura, el jugador respira agitado")] [Range(0f, 1f)] public float cercaniaRespiracion = 0.5f;
    public AudioClip ballena;
    [Range(0f, 1f)] public float volumenBallena = 0.22f;
    [Tooltip("Segundos entre llamadas lejanas (min, max)")] public Vector2 intervaloBallena = new Vector2(180f, 420f);
    [Tooltip("Tono de la ballena (mas bajo = mas grave e inquietante)")] public float tonoBallena = 0.7f;

    // fuentes
    AudioSource srcFuerte, srcSuave, srcOlaGrande, srcCuervos, srcSusurros, srcRespiracion, srcBallena;
    AudioLowPassFilter filtroFuerte, filtroSuave;
    readonly List<AudioSource> srcOlas = new List<AudioSource>();
    readonly List<Vector3> destinoOlas = new List<Vector3>();
    float proxOlas, proxCuervos, proxBallena;
    bool olasColocadas;
    Coroutine corOla, corSusurro;
    Transform oyente;

    void Awake()
    {
        if (clima == null) clima = FindAnyObjectByType<ClimaAgua>();
        if (lluviaCamara == null) lluviaCamara = FindAnyObjectByType<LluviaSigueCamara>();
    }

    void OnEnable()
    {
        ClimaAgua.AlRomperOla += OlaGrande;
        FiguraDistante.AlAparecer += FiguraAparece;
    }

    void OnDisable()
    {
        ClimaAgua.AlRomperOla -= OlaGrande;
        FiguraDistante.AlAparecer -= FiguraAparece;
    }

    void Start()
    {
        // lluvia (2D, en bucle)
        if (lluviaFuerte != null) { srcFuerte = Fuente("Lluvia_Fuerte", lluviaFuerte, 0f, true, false); filtroFuerte = srcFuerte.gameObject.AddComponent<AudioLowPassFilter>(); }
        if (lluviaSuave != null) { srcSuave = Fuente("Lluvia_Suave", lluviaSuave, 0f, true, false); filtroSuave = srcSuave.gameObject.AddComponent<AudioLowPassFilter>(); }

        // olas (3D, en bucle, cada una empieza en un momento distinto del clip)
        if (olas != null)
        {
            for (int i = 0; i < fuentesOlas; i++)
            {
                var s = Fuente("Olas_" + i, olas, 1f, true, true);
                s.minDistance = 8f; s.maxDistance = distanciaOlas; s.rolloffMode = AudioRolloffMode.Linear;
                s.pitch = Random.Range(0.94f, 1.04f);
                srcOlas.Add(s); destinoOlas.Add(s.transform.position);
            }
            srcOlaGrande = Fuente("Ola_Grande", olas, 1f, false, false);
            srcOlaGrande.minDistance = 12f; srcOlaGrande.maxDistance = distanciaOlas * 1.5f; srcOlaGrande.rolloffMode = AudioRolloffMode.Linear;
            srcOlaGrande.gameObject.AddComponent<AudioLowPassFilter>().cutoffFrequency = 2600f;   // golpe sordo y pesado
        }

        // faroles (3D, en bucle, pegados a cada luz)
        if (farol != null)
        {
            if (faroles == null || faroles.Length == 0) faroles = BuscarFaroles();
            foreach (var f in faroles)
            {
                if (f == null) continue;
                var s = Fuente("Siseo_Farol", farol, 1f, true, true, f);
                s.volume = volumenFarol; s.minDistance = 1.2f; s.maxDistance = distanciaFarol; s.rolloffMode = AudioRolloffMode.Linear;
                s.pitch = Random.Range(0.9f, 1.1f);
            }
        }

        // sueltos
        if (cuervos != null)
        {
            if (posicionesCuervos == null || posicionesCuervos.Length == 0) posicionesCuervos = BuscarArboles();
            srcCuervos = Fuente("Cuervos", cuervos, 1f, false, false);
            srcCuervos.minDistance = 10f; srcCuervos.maxDistance = 140f; srcCuervos.rolloffMode = AudioRolloffMode.Linear;
        }
        if (susurros != null) { srcSusurros = Fuente("Susurros", susurros, 1f, false, false); srcSusurros.minDistance = 3f; srcSusurros.maxDistance = 90f; srcSusurros.rolloffMode = AudioRolloffMode.Linear; srcSusurros.spread = 120f; }
        if (respiracion != null) srcRespiracion = Fuente("Respiracion", respiracion, 0f, false, false);
        if (ballena != null)
        {
            srcBallena = Fuente("Ballena_Lejana", ballena, 0.35f, false, false);   // un poco "en el espacio", sin saber de donde viene
            srcBallena.pitch = tonoBallena;
            srcBallena.gameObject.AddComponent<AudioLowPassFilter>().cutoffFrequency = 700f;
            srcBallena.gameObject.AddComponent<AudioReverbFilter>().reverbPreset = AudioReverbPreset.Mountains;
        }

        proxCuervos = Time.time + Random.Range(intervaloCuervos.x * 0.3f, intervaloCuervos.y * 0.5f);
        proxBallena = Time.time + Random.Range(intervaloBallena.x * 0.4f, intervaloBallena.y * 0.6f);
    }

    AudioSource Fuente(string nombre, AudioClip clip, float espacial, bool bucle, bool empezarYa, Transform padre = null)
    {
        var go = new GameObject(nombre);
        go.transform.SetParent(padre != null ? padre : transform, false);
        var s = go.AddComponent<AudioSource>();
        s.clip = clip; s.loop = bucle; s.playOnAwake = false; s.spatialBlend = espacial; s.dopplerLevel = 0f;
        s.volume = 0f;
        if (bucle) { s.time = Random.Range(0f, clip.length * 0.9f); s.Play(); }
        return s;
    }

    void Update()
    {
        if (oyente == null) { var l = FindAnyObjectByType<AudioListener>(); if (l != null) oyente = l.transform; else return; }
        float fuera = lluviaCamara != null ? lluviaCamara.FactorExterior : 1f;

        // --- lluvia: la capa fuerte entra con el chaparron, la suave queda de fondo
        float lluvia = clima != null ? ClimaAgua.LluviaAhora : 0.8f;
        float k = Mathf.InverseLerp(0.45f, 1f, lluvia);
        float techo = Mathf.Lerp(lluviaBajoTecho, 1f, fuera);
        float corte = Mathf.Lerp(corteBajoTecho, 22000f, fuera * fuera);
        if (srcFuerte != null) { srcFuerte.volume = volumenLluvia * Mathf.Lerp(0.3f, 1f, k) * techo; filtroFuerte.cutoffFrequency = corte; }
        if (srcSuave != null) { srcSuave.volume = volumenLluvia * Mathf.Lerp(0.55f, 0.25f, k) * techo; filtroSuave.cutoffFrequency = corte; }

        // --- olas: cada medio segundo se eligen los puntos de costa mas cercanos; las fuentes se deslizan hacia ellos
        if (srcOlas.Count > 0)
        {
            if (Time.time >= proxOlas) { proxOlas = Time.time + 0.5f; ElegirCosta(); }
            for (int i = 0; i < srcOlas.Count; i++)
            {
                var s = srcOlas[i];
                s.transform.position = Vector3.MoveTowards(s.transform.position, destinoOlas[i], 25f * Time.deltaTime);
                // bajo techo el mar se oye pero apagado (no hay filtro en estas: basta con bajar)
                s.volume = Mathf.MoveTowards(s.volume, volumenOlas * Mathf.Lerp(0.45f, 1f, fuera), Time.deltaTime * 0.5f);
            }
        }

        // --- cuervos
        if (srcCuervos != null && Time.time >= proxCuervos)
        {
            proxCuervos = Time.time + Random.Range(intervaloCuervos.x, intervaloCuervos.y);
            if (posicionesCuervos != null && posicionesCuervos.Length > 0 && !srcCuervos.isPlaying)
            {
                var p = posicionesCuervos[Random.Range(0, posicionesCuervos.Length)];
                if (p != null)
                {
                    srcCuervos.transform.position = p.position + Vector3.up * 3f;
                    srcCuervos.volume = volumenCuervos * Mathf.Lerp(0.5f, 1f, fuera);
                    srcCuervos.pitch = Random.Range(0.88f, 1.02f);
                    srcCuervos.Play();
                }
            }
        }

        // --- ballena lejana
        if (srcBallena != null && Time.time >= proxBallena)
        {
            proxBallena = Time.time + Random.Range(intervaloBallena.x, intervaloBallena.y);
            Vector2 r = Random.insideUnitCircle.normalized * 250f;
            srcBallena.transform.position = oyente.position + new Vector3(r.x, -5f, r.y);
            srcBallena.volume = volumenBallena * Mathf.Lerp(0.5f, 1f, fuera);
            srcBallena.Play();
        }
    }

    void ElegirCosta()
    {
        if (clima == null || clima.puntosCosta == null || clima.puntosCosta.Length == 0) return;
        var p = oyente.position;
        var orden = new List<Vector3>(clima.puntosCosta);
        orden.Sort((a, b) => (a - p).sqrMagnitude.CompareTo((b - p).sqrMagnitude));
        for (int i = 0; i < srcOlas.Count; i++)
        {
            var d = orden[Mathf.Min(i, orden.Count - 1)];
            if (!olasColocadas) srcOlas[i].transform.position = d;   // primera vez: sin deslizar
            destinoOlas[i] = d;
        }
        olasColocadas = true;
    }

    // ---------- eventos

    void OlaGrande(Vector3 punto, float fuerza)
    {
        if (srcOlaGrande == null) return;
        if (corOla != null) StopCoroutine(corOla);
        corOla = StartCoroutine(GolpeOla(punto, fuerza));
    }

    IEnumerator GolpeOla(Vector3 punto, float fuerza)
    {
        // no hay un sonido de "golpe" propio: se usa un trozo del oleaje, mas grave y fuerte, que entra de golpe y se arrastra
        var s = srcOlaGrande;
        s.transform.position = punto;
        s.time = Random.Range(0f, Mathf.Max(0f, s.clip.length - 10f));
        s.pitch = Random.Range(0.72f, 0.82f);
        s.Play();
        float pico = volumenOlaGrande * Mathf.Lerp(0.6f, 1f, fuerza);
        for (float t = 0f; t < 0.35f; t += Time.deltaTime) { s.volume = pico * t / 0.35f; yield return null; }
        yield return new WaitForSeconds(2.2f);
        for (float t = 0f; t < 4f; t += Time.deltaTime) { s.volume = pico * (1f - t / 4f); yield return null; }
        s.Stop();
    }

    void FiguraAparece(Vector3 pos, float cercania)
    {
        if (srcSusurros != null)
        {
            if (corSusurro != null) StopCoroutine(corSusurro);
            corSusurro = StartCoroutine(Susurrar(pos, cercania));
        }
        if (srcRespiracion != null && cercania >= cercaniaRespiracion && !srcRespiracion.isPlaying)
        {
            srcRespiracion.volume = volumenRespiracion * Mathf.Lerp(0.6f, 1f, cercania);
            srcRespiracion.pitch = Random.Range(0.95f, 1.08f);
            srcRespiracion.PlayDelayed(Random.Range(0.6f, 1.4f));   // el jugador "reacciona" un instante despues
        }
    }

    IEnumerator Susurrar(Vector3 pos, float cercania)
    {
        // un trozo corto de los susurros, desde donde esta la figura; cuanto mas cerca, mas se oye
        var s = srcSusurros;
        s.transform.position = pos + Vector3.up * 1.6f;
        s.time = Random.Range(0f, Mathf.Max(0f, s.clip.length - 6f));
        s.pitch = Random.Range(0.9f, 1f);
        s.Play();
        float pico = volumenSusurros * Mathf.Lerp(0.5f, 1f, cercania);
        float dur = Random.Range(2.5f, 4.5f);
        for (float t = 0f; t < 0.6f; t += Time.deltaTime) { s.volume = pico * t / 0.6f; yield return null; }
        yield return new WaitForSeconds(dur);
        for (float t = 0f; t < 1.5f; t += Time.deltaTime) { s.volume = pico * (1f - t / 1.5f); yield return null; }
        s.Stop();
    }

    // ---------- busquedas por defecto

    static Transform[] BuscarFaroles()
    {
        var lista = new List<Transform>();
        foreach (var l in FindObjectsByType<LuzParpadeo>(FindObjectsSortMode.None))
        {
            string n = l.name.ToLower();
            if (n.Contains("brasas") || n.Contains("reflejo")) continue;   // la caldera y los reflejos no sisean
            lista.Add(l.transform);
        }
        return lista.ToArray();
    }

    static Transform[] BuscarArboles()
    {
        var lista = new List<Transform>();
        foreach (var t in FindObjectsByType<Transform>(FindObjectsSortMode.None))
            if (t.name.StartsWith("Arbol_Seco")) lista.Add(t);
        return lista.ToArray();
    }
}
