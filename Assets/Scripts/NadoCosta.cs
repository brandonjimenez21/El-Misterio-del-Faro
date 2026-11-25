using UnityEngine;

/// <summary>
/// Hace que un animal (banco de arenques, tiburon) rodee la isla entera siguiendo la costa (RutaCosta) a "margen" metros de la orilla.
/// El oceano es opaco: solo se ve lo que asoma (lomo de los arenques, aleta y silueta del tiburon).
/// Con "acechaJugador" (tiburon): mientras el jugador esta lejos del agua patrulla la isla; cuando el jugador se acerca a la orilla
/// (o al muelle) aparece cerca: si esta lejos y fuera de la vista se coloca a "aparecerA" metros, y luego pasa una y otra vez
/// por delante, pegado a la costa. Cuando el jugador se aleja, vuelve a su ronda.
/// </summary>
public class NadoCosta : MonoBehaviour
{
    public RutaCosta ruta;
    [Tooltip("Metros mar adentro desde la orilla")] public float margen = 10f;
    [Tooltip("Metros por segundo; negativo = sentido contrario")] public float velocidad = 1.4f;
    [Tooltip("Donde empieza, en grados alrededor de la isla")] public float faseInicial = 0f;
    [Tooltip("Altura del origen sobre el nivel del agua (m)")] public float profundidad = -0.5f;
    [Tooltip("Cuanto sube y baja con las olas (m)")] public float vaiven = 0.08f;
    [Tooltip("Cuanto se mueve de lado a lado al nadar (grados); 0 para los arenques, que ya van animados")] public float coletazo = 0f;
    public float frecuenciaColetazo = 0.4f;

    [Header("Acecho (tiburon)")]
    public bool acechaJugador = false;
    [Tooltip("El jugador cuenta como cerca de la costa a menos de estos metros de la orilla")] public float distanciaAviso = 14f;
    [Tooltip("Deja de acechar cuando el jugador se aleja mas de esto de la orilla")] public float distanciaOlvido = 22f;
    [Tooltip("Metros de la orilla a los que pasa mientras acecha")] public float margenAcecho = 5f;
    public float velocidadAcecho = 2.4f;
    [Tooltip("Cuanto sube hacia la superficie mientras acecha (m)")] public float subidaAcecho = 0f;
    [Tooltip("Cuanto se aleja a cada lado del jugador antes de dar la vuelta (m)")] public float vaivenAcecho = 16f;
    [Tooltip("Si esta mas lejos que esto (m de costa) y no se le ve, aparece cerca")] public float distanciaSalto = 40f;
    [Tooltip("A cuantos metros del jugador aparece")] public float aparecerA = 24f;
    public Transform jugador;
    public Transform oceano;

    public bool Acechando { get; private set; }
    float angulo, sentido = 1f, margenActual, semilla, subida;
    static readonly int idNivelMar = Shader.PropertyToID("_FaroNivelMar");
    Quaternion rumbo;
    Camera camara;

    void Start()
    {
        if (ruta == null) ruta = GetComponentInParent<RutaCosta>();
        if (oceano == null) { var o = GameObject.Find("Oceano"); if (o != null) oceano = o.transform; }
        camara = Camera.main;
        if (jugador == null && camara != null) jugador = camara.transform;
        semilla = Random.value * 20f;
        Colocar();
    }

    /// <summary>pone el animal en su posicion inicial (tambien lo llama el importador en modo edicion)</summary>
    public void Colocar()
    {
        if (ruta == null) ruta = GetComponentInParent<RutaCosta>();
        if (ruta == null) return;
        if (oceano == null) { var o = GameObject.Find("Oceano"); if (o != null) oceano = o.transform; }
        angulo = faseInicial * Mathf.Deg2Rad;
        sentido = velocidad < 0f ? -1f : 1f;
        margenActual = margen;
        rumbo = Quaternion.LookRotation(Tangente(), Vector3.up);
        Poner(0f);
    }

    void LateUpdate()
    {
        if (ruta == null) return;
        float v = Mathf.Abs(velocidad);
        float margenMeta = margen;
        if (acechaJugador && jugador != null)
        {
            float dCosta = ruta.DistanciaACosta(jugador.position);
            if (!Acechando && dCosta > -distanciaAviso) Acechando = true;
            else if (Acechando && dCosta < -distanciaOlvido) { Acechando = false; sentido = velocidad < 0f ? -1f : 1f; }
            if (Acechando)
            {
                margenMeta = margenAcecho;
                float angJ = ruta.Angulo(jugador.position);
                float r = ruta.Radio(angJ) + margenAcecho;
                // + = el jugador queda delante yendo en sentido positivo
                float arco = Mathf.DeltaAngle(angulo * Mathf.Rad2Deg, angJ * Mathf.Rad2Deg) * Mathf.Deg2Rad * r;
                if (Mathf.Abs(arco) > distanciaSalto && !SeVe(transform.position))
                {
                    // aparece a un lado del jugador, en el que no este mirando
                    float dAng = aparecerA / r;
                    float lado = arco > 0f ? -1f : 1f;                      // el lado por el que venia
                    if (SeVe(Altura(ruta.Punto(angJ + lado * dAng, margenAcecho)))) lado = -lado;
                    if (!SeVe(Altura(ruta.Punto(angJ + lado * dAng, margenAcecho))))
                    {
                        angulo = angJ + lado * dAng;
                        margenActual = margenAcecho;
                        sentido = -lado;
                        rumbo = Quaternion.LookRotation(Tangente(), Vector3.up);
                        arco = -lado * aparecerA;
                    }
                }
                if (Mathf.Abs(arco) > vaivenAcecho) sentido = Mathf.Sign(arco);       // hacia el jugador; al pasarse da la vuelta
                v = Mathf.Abs(arco) > distanciaSalto ? velocidadAcecho * 3f : velocidadAcecho;
            }
        }
        margenActual = Mathf.MoveTowards(margenActual, margenMeta, 1.5f * Time.deltaTime);
        subida = Mathf.MoveTowards(subida, Acechando ? subidaAcecho : 0f, 0.12f * Time.deltaTime);
        angulo += sentido * v * Time.deltaTime / Mathf.Max(5f, ruta.Radio(angulo) + margenActual);
        Poner(Time.deltaTime);
    }

    Vector3 Tangente()
    {
        Vector3 t = ruta.Punto(angulo + sentido * 0.02f, margenActual) - ruta.Punto(angulo - sentido * 0.02f, margenActual);
        t.y = 0f;
        return t.sqrMagnitude > 1e-6f ? t.normalized : Vector3.forward;
    }

    Vector3 Altura(Vector3 p)
    {
        p.y = (oceano != null ? oceano.position.y : 0f) + profundidad;
        return p;
    }

    void Poner(float dt)
    {
        Vector3 p = Altura(ruta.Punto(angulo, margenActual));
        if (acechaJugador && oceano != null) Shader.SetGlobalFloat(idNivelMar, oceano.position.y);     // para Faro/BajoElAgua
        p.y += subida + vaiven * Mathf.Sin(Time.time * 0.7f + semilla);
        transform.position = p;
        var meta = Quaternion.LookRotation(Tangente(), Vector3.up);
        rumbo = dt > 0f ? Quaternion.Slerp(rumbo, meta, 1f - Mathf.Exp(-1.6f * dt)) : meta;      // gira con suavidad al dar la vuelta
        float lado = coletazo * Mathf.Sin(Time.time * frecuenciaColetazo * 2f * Mathf.PI + semilla);
        transform.rotation = rumbo * Quaternion.Euler(0f, lado, 0f);
    }

    bool SeVe(Vector3 p)
    {
        if (camara == null) camara = Camera.main;
        if (camara == null) return false;
        Vector3 v = camara.WorldToViewportPoint(p);
        if (v.z <= 0f || v.z > 90f) return false;            // detras, o tan lejos que la niebla lo tapa
        return v.x > -0.15f && v.x < 1.15f && v.y > -0.15f && v.y < 1.15f;
    }
}
