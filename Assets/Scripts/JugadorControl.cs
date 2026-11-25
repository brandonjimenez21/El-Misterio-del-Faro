using UnityEngine;
using UnityEngine.Events;
using UnityEngine.InputSystem;

/// <summary>Lo que el jugador puede agarrar/usar con E (puzles): cualquier componente del objeto o de sus padres que lo implemente.</summary>
public interface IInteractuable
{
    void Interactuar(JugadorControl jugador);
}

/// <summary>
/// Jugador en primera persona (proyecto con el Input System nuevo): mirar con raton o mando, andar y correr, cabeceo al caminar,
/// brazos del protagonista con la linterna (animaciones de Alejandro: Idle / Marcha / Agarrar / Sostener objeto), pasos segun el suelo
/// y limite del agua (no se mete mas alla de "profundidadMax" bajo el nivel del mar).
///   WASD / stick izq. = mover   Raton / stick der. = mirar   Shift = correr   E = agarrar/usar   F = linterna   Esc = soltar el raton
/// Jerarquia que arma Faro > Importar > Jugador y colisiones:  Jugador (CharacterController) > Cabeza > Main Camera > Brazos (modelo con Animator).
/// </summary>
[RequireComponent(typeof(CharacterController))]
public class JugadorControl : MonoBehaviour
{
    [Header("Referencias")]
    public Transform cabeza;
    public Animator brazos;
    public Light luzLinterna;
    [Tooltip("Cristal y llama de la linterna: su emision se apaga con la luz")] public Renderer[] emisivosLinterna;
    public AudioSource fuentePasos;
    public AudioSource fuenteLinterna;
    public Transform oceano;

    [Header("Movimiento")]
    public float velCaminar = 2.3f;
    public float velCorrer = 4.0f;
    public float aceleracion = 14f;
    public float gravedad = -20f;
    [Tooltip("Metros bajo el nivel del mar a los que se le deja llegar (vadear la orilla)")] public float profundidadMax = 0.5f;

    [Header("Resistencia")]
    [Tooltip("Segundos corriendo hasta quedar sin aliento")] public float duracionCarrera = 15f;
    [Tooltip("Segundos andando/parado para recuperarla entera")] public float tiempoRecarga = 10f;
    [Tooltip("Tras agotarse, no puede volver a correr hasta recuperar esta fraccion")] [Range(0f, 1f)] public float umbralRecuperar = 0.35f;
    [Tooltip("Barra de resistencia: solo aparece desde que se agota hasta que se recupera del todo")] public bool mostrarBarra = true;
    public AudioClip sonidoJadeo;
    public AudioSource fuenteJadeo;

    [Header("Mirada")]
    public float sensibilidadRaton = 0.085f;          // grados por pixel
    public float sensibilidadMando = 130f;            // grados por segundo
    public float limiteVertical = 82f;

    [Header("Cabeceo al caminar")]
    public float cabeceoAltura = 0.032f;
    public float cabeceoLado = 0.018f;
    public float pasoMetros = 0.78f;                  // metros por paso

    [Header("Linterna y pasos")]
    public bool linternaEncendida = true;
    public AudioClip pasosMadera, pasosGrava, pasosEscalera;
    [Range(0f, 1f)] public float volumenPasos = 0.5f;

    [Header("Interaccion")]
    public float alcance = 2.6f;
    public UnityEvent alAgarrar;

    public Vector3 Velocidad { get; private set; }
    public bool Corriendo { get; private set; }
    public float Nivel { get; private set; }
    /// <summary>1 = descansado, 0 = sin aliento</summary>
    public float Resistencia { get; private set; } = 1f;
    public bool SinAliento { get; private set; }

    CharacterController cc;
    bool barraActiva;
    float barraAlfa;
    float yaw, pitch, velY, fase, velAnim = 1f, velHoriz;
    Vector3 cabezaBase;
    Vector3 velXZ;
    bool cursorLibre;
    float[] intensidadesEmision;
    Color[] coloresEmision;
    float intensidadLuz;
    static readonly int idVelocidad = Animator.StringToHash("Velocidad");
    static readonly int idVelAnim = Animator.StringToHash("VelAnim");
    static readonly int idObjeto = Animator.StringToHash("Objeto");
    static readonly int idAgarrar = Animator.StringToHash("Agarrar");
    static readonly int idEmision = Shader.PropertyToID("_EmissionColor");
    MaterialPropertyBlock bloque;
    AudioClip pasosActual;

    void Awake()
    {
        cc = GetComponent<CharacterController>();
        if (cabeza != null) cabezaBase = cabeza.localPosition;
        if (luzLinterna != null) intensidadLuz = luzLinterna.intensity;
        bloque = new MaterialPropertyBlock();
        if (emisivosLinterna != null)
        {
            coloresEmision = new Color[emisivosLinterna.Length];
            for (int i = 0; i < emisivosLinterna.Length; i++)
                if (emisivosLinterna[i] != null && emisivosLinterna[i].sharedMaterial != null)
                    coloresEmision[i] = emisivosLinterna[i].sharedMaterial.GetColor(idEmision);
        }
    }

    void Start()
    {
        yaw = transform.eulerAngles.y;
        ultimoSeguro = transform.position;
        if (oceano == null) { var o = GameObject.Find("Oceano"); if (o != null) oceano = o.transform; }
        Nivel = oceano != null ? oceano.position.y : -0.3f;
        BloquearCursor(true);
        AplicarLinterna();
    }

    void BloquearCursor(bool si)
    {
        cursorLibre = !si;
        Cursor.lockState = si ? CursorLockMode.Locked : CursorLockMode.None;
        Cursor.visible = !si;
    }

    void Update()
    {
        var kb = Keyboard.current; var rat = Mouse.current; var pad = Gamepad.current;
        if (kb != null && kb.escapeKey.wasPressedThisFrame) BloquearCursor(cursorLibre);          // alterna
        if (cursorLibre && rat != null && rat.leftButton.wasPressedThisFrame) BloquearCursor(true);
        float dt = Time.deltaTime;

        // ---- mirar
        if (!cursorLibre)
        {
            Vector2 mirada = Vector2.zero;
            if (rat != null) mirada += rat.delta.ReadValue() * sensibilidadRaton;
            if (pad != null) mirada += pad.rightStick.ReadValue() * sensibilidadMando * dt;
            yaw += mirada.x;
            pitch = Mathf.Clamp(pitch - mirada.y, -limiteVertical, limiteVertical);
            transform.rotation = Quaternion.Euler(0f, yaw, 0f);
            if (cabeza != null) cabeza.localRotation = Quaternion.Euler(pitch, 0f, 0f);
        }

        // ---- mover
        Vector2 mov = Vector2.zero;
        if (kb != null && !cursorLibre)
        {
            if (kb.wKey.isPressed || kb.upArrowKey.isPressed) mov.y += 1f;
            if (kb.sKey.isPressed || kb.downArrowKey.isPressed) mov.y -= 1f;
            if (kb.dKey.isPressed || kb.rightArrowKey.isPressed) mov.x += 1f;
            if (kb.aKey.isPressed || kb.leftArrowKey.isPressed) mov.x -= 1f;
        }
        if (pad != null) mov += pad.leftStick.ReadValue();
        mov = Vector2.ClampMagnitude(mov, 1f);
        bool quiereCorrer = mov.y > 0.1f && ((kb != null && kb.leftShiftKey.isPressed) || (pad != null && pad.leftStickButton.isPressed));
        if (SinAliento && Resistencia >= umbralRecuperar) SinAliento = false;
        Corriendo = quiereCorrer && !SinAliento;
        if (Corriendo)
        {
            Resistencia -= dt / Mathf.Max(0.1f, duracionCarrera);
            if (Resistencia <= 0f)
            {
                Resistencia = 0f; SinAliento = true; Corriendo = false;
                if (fuenteJadeo != null && sonidoJadeo != null) fuenteJadeo.PlayOneShot(sonidoJadeo, 0.8f);
            }
        }
        else Resistencia = Mathf.Min(1f, Resistencia + dt / Mathf.Max(0.1f, tiempoRecarga) * (SinAliento ? 0.8f : 1f));
        if (SinAliento) barraActiva = true; else if (Resistencia >= 0.999f) barraActiva = false;
        barraAlfa = Mathf.MoveTowards(barraAlfa, barraActiva ? 1f : 0f, dt * 3f);
        Vector3 deseada = (transform.right * mov.x + transform.forward * mov.y) * (Corriendo ? velCorrer : velCaminar);
        velXZ = Vector3.MoveTowards(velXZ, deseada, aceleracion * dt);

        Vector3 paso = velXZ * dt;
        if (paso.sqrMagnitude > 1e-8f && !HaySuelo(transform.position + paso)) { velXZ = Vector3.zero; paso = Vector3.zero; }

        if (cc.isGrounded && velY < 0f) velY = -2f;
        velY += gravedad * dt;
        cc.Move(paso + Vector3.up * velY * dt);

        // red de seguridad: si por cualquier hueco acaba bajo el mar (o cayendo), vuelve al ultimo sitio seguro en tierra
        if (cc.isGrounded && transform.position.y > Nivel + 0.1f && Physics.Raycast(transform.position + Vector3.up * 0.5f, Vector3.down, 1.2f, ~0, QueryTriggerInteraction.Ignore))
        {
            segundosSeguro -= dt;
            if (segundosSeguro <= 0f) { ultimoSeguro = transform.position; segundosSeguro = 0.5f; }
        }
        if (transform.position.y < Nivel - 2.5f)
        {
            cc.enabled = false;
            transform.position = ultimoSeguro + Vector3.up * 0.1f;
            cc.enabled = true;
            velY = 0f; velXZ = Vector3.zero;
            TensionJugador.Pulso(0.35f);
        }
        Velocidad = new Vector3(velXZ.x, velY, velXZ.z);
        velHoriz = velXZ.magnitude;

        // ---- cabeceo, brazos y pasos
        float ritmo = velHoriz / Mathf.Max(0.1f, pasoMetros);          // pasos por segundo
        fase += ritmo * dt * Mathf.PI;                                 // un paso = medio ciclo
        if (cabeza != null)
        {
            float a = Mathf.Clamp01(velHoriz / velCaminar);
            cabeza.localPosition = cabezaBase + new Vector3(Mathf.Cos(fase) * cabeceoLado * a, Mathf.Abs(Mathf.Sin(fase)) * cabeceoAltura * a - cabeceoAltura * 0.5f * a, 0f);
        }
        if (brazos != null)
        {
            float n = Mathf.Clamp01(velHoriz / velCaminar);
            brazos.SetFloat(idVelocidad, velHoriz, 0.1f, dt);
            float objetivo = Mathf.Lerp(1.0f, 2.2f, velHoriz / velCorrer);
            velAnim = Mathf.MoveTowards(velAnim, objetivo, 4f * dt);
            brazos.SetFloat(idVelAnim, velAnim);
        }
        ActualizarPasos();

        // ---- acciones
        if (kb != null && !cursorLibre)
        {
            if (kb.fKey.wasPressedThisFrame) { linternaEncendida = !linternaEncendida; AplicarLinterna(); }
            if (kb.eKey.wasPressedThisFrame) Agarrar();
        }
        if (pad != null && pad.buttonWest.wasPressedThisFrame) Agarrar();
    }

    /// <summary>hay suelo bajo el destino y no esta demasiado hundido bajo el mar</summary>
    bool HaySuelo(Vector3 destino)
    {
        if (Physics.Raycast(destino + Vector3.up * 2.2f, Vector3.down, out var h, 9f, ~0, QueryTriggerInteraction.Ignore))
            return h.point.y > Nivel - profundidadMax;
        return false;
    }

    public void Agarrar()
    {
        if (brazos != null) brazos.SetTrigger(idAgarrar);
        alAgarrar?.Invoke();
        var cam = cabeza != null ? cabeza : transform;
        if (Physics.Raycast(cam.position, cam.forward, out var h, alcance, ~0, QueryTriggerInteraction.Collide))
        {
            var obj = h.collider.GetComponentInParent<IInteractuable>();
            if (obj != null) obj.Interactuar(this);
        }
    }

    /// <summary>0 = manos libres con la linterna, 1 = sostiene un objeto en vertical, 2 = en horizontal (animaciones Hold_RightH_*)</summary>
    public void SostenerObjeto(int tipo)
    {
        if (brazos != null) brazos.SetInteger(idObjeto, tipo);
    }

    float brillo = 1f;
    Vector3 ultimoSeguro;
    float segundosSeguro;
    /// <summary>Brillo de la llama (0 = apagada del todo, 1 = normal). Lo usa LinternaTension en los apagones; no cambia linternaEncendida.</summary>
    public void BrilloLlama(float k)
    {
        brillo = Mathf.Clamp01(k);
        AplicarEmision();
    }

    void AplicarLinterna()
    {
        if (luzLinterna != null) luzLinterna.enabled = linternaEncendida;
        if (fuenteLinterna != null) { if (linternaEncendida && !fuenteLinterna.isPlaying) fuenteLinterna.Play(); else if (!linternaEncendida) fuenteLinterna.Stop(); }
        AplicarEmision();
    }

    void AplicarEmision()
    {
        if (emisivosLinterna == null || coloresEmision == null || bloque == null) return;
        for (int i = 0; i < emisivosLinterna.Length; i++)
        {
            var r = emisivosLinterna[i];
            if (r == null) continue;
            r.GetPropertyBlock(bloque);
            bloque.SetColor(idEmision, linternaEncendida ? coloresEmision[i] * brillo : Color.black);
            r.SetPropertyBlock(bloque);
        }
    }

    void ActualizarPasos()
    {
        if (fuentePasos == null) return;
        bool anda = cc.isGrounded && velHoriz > 0.4f;
        AudioClip clip = null;
        if (anda && Physics.Raycast(transform.position + Vector3.up * 0.5f, Vector3.down, out var h, 2f, ~0, QueryTriggerInteraction.Ignore))
        {
            string n = h.collider.name;
            clip = n.StartsWith("Muelle") || n.Contains("Cubierta") || n.Contains("Embarcadero") || n.Contains("Puente") ? pasosMadera
                 : n.Contains("Escalera") ? pasosEscalera : pasosGrava;
            if (clip == null) clip = pasosGrava != null ? pasosGrava : pasosMadera;
        }
        if (clip == null) { if (fuentePasos.isPlaying) fuentePasos.Pause(); return; }
        if (clip != pasosActual) { pasosActual = clip; fuentePasos.clip = clip; fuentePasos.loop = true; fuentePasos.Play(); }
        else if (!fuentePasos.isPlaying) fuentePasos.UnPause();
        fuentePasos.volume = volumenPasos * Mathf.Clamp01(velHoriz / velCaminar);
        fuentePasos.pitch = Mathf.Lerp(0.85f, 1.25f, velHoriz / velCorrer);
    }

    void OnGUI()
    {
        if (!mostrarBarra || barraAlfa <= 0.01f) return;
        float w = Mathf.Min(320f, Screen.width * 0.3f), h = 8f;
        var r = new Rect((Screen.width - w) / 2f, Screen.height - 70f, w, h);
        var antes = GUI.color;
        GUI.color = new Color(0f, 0f, 0f, 0.55f * barraAlfa);
        GUI.DrawTexture(new Rect(r.x - 2f, r.y - 2f, r.width + 4f, r.height + 4f), Texture2D.whiteTexture);
        // roja mientras no puede correr, palida al recuperar
        var c = SinAliento ? new Color(0.75f, 0.2f, 0.15f) : new Color(0.85f, 0.82f, 0.7f);
        GUI.color = new Color(c.r, c.g, c.b, 0.9f * barraAlfa);
        GUI.DrawTexture(new Rect(r.x, r.y, r.width * Resistencia, r.height), Texture2D.whiteTexture);
        GUI.color = antes;
    }
}
