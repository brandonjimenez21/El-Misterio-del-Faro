using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RenderGraphModule;
using UnityEngine.Rendering.Universal;

/// <summary>
/// Niebla volumetrica ligera para URP (Renderer Feature). Se anade en PC_Renderer > Add Renderer Feature.
/// Hace que la bruma se ilumine alrededor de las luces (faroles, linterna, haz del faro, relampago, luna)
/// y que las sombras recorten haces dentro de ella. Se calcula a media resolucion y se desenfoca,
/// asi que cuesta poco. Va antes del post-proceso para que el Bloom tambien la haga brillar.
///
/// Cualquier luz puntual o foco nuevo (por ejemplo la linterna de mano del jugador) aparece sola en la bruma:
/// no hay que configurar nada en la luz. Si ademas la luz tiene sombras, sus haces se recortan.
/// </summary>
public class NieblaVolumetricaFeature : ScriptableRendererFeature
{
    [System.Serializable]
    public class Ajustes
    {
        public bool activa = true;
        [Tooltip("Tambien en la ventana Scene del editor")] public bool enVistaEscena = true;

        [Header("Calidad / rendimiento")]
        [Tooltip("Calcular a media resolucion (recomendado: 4 veces mas barato)")] public bool mediaResolucion = true;
        [Tooltip("Muestras por pixel. 16 = rapido, 24 = equilibrado, 40 = maxima calidad")] [Range(8, 48)] public int pasos = 24;
        [Tooltip("Hasta que distancia de la camara se calcula (m)")] [Range(20f, 200f)] public float distancia = 80f;

        [Header("Bruma")]
        [Tooltip("Cuanta luz dispersa la bruma por metro")] [Range(0f, 0.2f)] public float densidad = 0.03f;
        [Tooltip("Cuanto se apaga con la distancia")] [Range(0f, 0.1f)] public float extincion = 0.012f;
        [Tooltip("Hasta esta altura la bruma es igual de densa (m)")] public float alturaBase = 4f;
        [Tooltip("Cuanto se aclara por cada metro por encima")] [Range(0f, 0.3f)] public float caidaAltura = 0.03f;
        [Tooltip("Jirones: cuanto varia la densidad (0 = uniforme)")] [Range(0f, 1f)] public float ruido = 0.45f;
        [Tooltip("Tamano de los jirones (m)")] [Range(1f, 30f)] public float tamanoRuido = 7f;
        [Tooltip("Hacia donde y a que velocidad se mueven los jirones (m/s)")] public Vector3 viento = new Vector3(0.9f, 0.05f, 0.35f);

        [Header("Luces")]
        [Tooltip("Faroles, linternas y focos")] [Range(0f, 4f)] public float lucesLocales = 0.4f;
        [Tooltip("Luna")] [Range(0f, 1f)] public float luna = 0.022f;
        [Tooltip("Relampago: toda la bruma se enciende en el destello")] [Range(0f, 1f)] public float relampago = 0.045f;
        [Tooltip("0 = brilla igual desde cualquier lado; mas alto = brilla mas al mirar hacia la luz")] [Range(0f, 0.9f)] public float anisotropia = 0.55f;
        [Tooltip("Limite del brillo pegado a una luz (evita puntos quemados)")] [Range(0.2f, 8f)] public float brilloMaximo = 1.2f;
        [Tooltip("Dentro de la cabana o la torre la bruma baja a esta fraccion")] [Range(0f, 1f)] public float interior = 0.3f;
    }

    public Ajustes ajustes = new Ajustes();
    [Tooltip("Assets/Shaders/NieblaVolumetrica.shader")] public Shader shader;

    /// <summary>1 = la camara esta fuera, 0 = dentro de la cabana o la torre. Lo actualiza LluviaSigueCamara.</summary>
    public static float FactorExterior = 1f;

    /// <summary>Tope de muestras por pixel. Lo baja CalidadAutomatica en equipos lentos (48 = sin tope).</summary>
    public static int LimitePasos = 48;

    Material material;
    Pase pase;

    public override void Create()
    {
        if (shader == null) shader = Shader.Find("Hidden/Faro/NieblaVolumetrica");
        if (shader != null) material = CoreUtils.CreateEngineMaterial(shader);
        pase = new Pase { renderPassEvent = RenderPassEvent.BeforeRenderingPostProcessing };
    }

    public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
    {
        if (material == null || !ajustes.activa) return;
        var tipo = renderingData.cameraData.cameraType;
        if (tipo != CameraType.Game && !(tipo == CameraType.SceneView && ajustes.enVistaEscena)) return;
        pase.material = material;
        pase.ajustes = ajustes;
        pase.ConfigureInput(ScriptableRenderPassInput.Depth);
        renderer.EnqueuePass(pase);
    }

    protected override void Dispose(bool disposing)
    {
        CoreUtils.Destroy(material);
        material = null;
    }

    class Pase : ScriptableRenderPass
    {
        public Material material;
        public Ajustes ajustes;

        class Datos
        {
            public Material material;
            public int pasada;
            public TextureHandle fuente;
        }

        static MaterialPropertyBlock bloque;
        static readonly int idNieblaTex = Shader.PropertyToID("_NieblaTex");
        static readonly int idNieblaTam = Shader.PropertyToID("_NieblaTam");
        static readonly int idPasos = Shader.PropertyToID("_Pasos");
        static readonly int idDistancia = Shader.PropertyToID("_Distancia");
        static readonly int idDensidad = Shader.PropertyToID("_Densidad");
        static readonly int idExtincion = Shader.PropertyToID("_Extincion");
        static readonly int idAlturaBase = Shader.PropertyToID("_AlturaBase");
        static readonly int idCaidaAltura = Shader.PropertyToID("_CaidaAltura");
        static readonly int idIntLocales = Shader.PropertyToID("_IntLocales");
        static readonly int idIntLuna = Shader.PropertyToID("_IntLuna");
        static readonly int idIntDireccionales = Shader.PropertyToID("_IntDireccionales");
        static readonly int idAnisotropia = Shader.PropertyToID("_Anisotropia");
        static readonly int idMaxAtenuacion = Shader.PropertyToID("_MaxAtenuacion");
        static readonly int idRuido = Shader.PropertyToID("_Ruido");
        static readonly int idEscalaRuido = Shader.PropertyToID("_EscalaRuido");
        static readonly int idVientoRuido = Shader.PropertyToID("_VientoRuido");
        static readonly int idFuerza = Shader.PropertyToID("_Fuerza");

        public override void RecordRenderGraph(RenderGraph grafo, ContextContainer frameData)
        {
            var recursos = frameData.Get<UniversalResourceData>();
            if (recursos.isActiveTargetBackBuffer || material == null) return;

            var desc = grafo.GetTextureDesc(recursos.activeColorTexture);
            int div = ajustes.mediaResolucion ? 2 : 1;
            desc.width = Mathf.Max(1, desc.width / div);
            desc.height = Mathf.Max(1, desc.height / div);
            desc.format = GraphicsFormat.B10G11R11_UFloatPack32;
            desc.msaaSamples = MSAASamples.None;
            desc.clearBuffer = false;
            desc.filterMode = FilterMode.Bilinear;
            desc.wrapMode = TextureWrapMode.Clamp;
            desc.name = "_NieblaVolumetrica_A";
            var texA = grafo.CreateTexture(desc);
            desc.name = "_NieblaVolumetrica_B";
            var texB = grafo.CreateTexture(desc);

            var a = ajustes;
            float exterior = Application.isPlaying ? Mathf.Clamp01(FactorExterior) : 1f;
            material.SetVector(idNieblaTam, new Vector4(1f / desc.width, 1f / desc.height, desc.width, desc.height));
            material.SetInt(idPasos, Mathf.Min(a.pasos, Mathf.Max(4, LimitePasos)));
            material.SetFloat(idDistancia, a.distancia);
            material.SetFloat(idDensidad, a.densidad);
            material.SetFloat(idExtincion, a.extincion);
            material.SetFloat(idAlturaBase, a.alturaBase);
            material.SetFloat(idCaidaAltura, a.caidaAltura);
            material.SetFloat(idIntLocales, a.lucesLocales);
            material.SetFloat(idIntLuna, a.luna);
            material.SetFloat(idIntDireccionales, a.relampago);
            material.SetFloat(idAnisotropia, a.anisotropia);
            material.SetFloat(idMaxAtenuacion, a.brilloMaximo);
            material.SetFloat(idRuido, a.ruido);
            material.SetFloat(idEscalaRuido, 1f / Mathf.Max(0.5f, a.tamanoRuido));
            material.SetVector(idVientoRuido, a.viento / Mathf.Max(0.5f, a.tamanoRuido));
            material.SetFloat(idFuerza, Mathf.Lerp(a.interior, 1f, exterior));

            Pasada(grafo, recursos, "Niebla volumetrica: trazar", 0, TextureHandle.nullHandle, texA, AccessFlags.WriteAll);
            Pasada(grafo, recursos, "Niebla volumetrica: desenfoque H", 1, texA, texB, AccessFlags.WriteAll);
            Pasada(grafo, recursos, "Niebla volumetrica: desenfoque V", 2, texB, texA, AccessFlags.WriteAll);
            Pasada(grafo, recursos, "Niebla volumetrica: componer", 3, texA, recursos.activeColorTexture, AccessFlags.ReadWrite);
        }

        void Pasada(RenderGraph grafo, UniversalResourceData recursos, string nombre, int pasada, TextureHandle fuente, TextureHandle destino, AccessFlags acceso)
        {
            using (var b = grafo.AddRasterRenderPass<Datos>(nombre, out var d))
            {
                d.material = material;
                d.pasada = pasada;
                d.fuente = fuente;
                if (fuente.IsValid()) b.UseTexture(fuente, AccessFlags.Read);
                if (recursos.cameraDepthTexture.IsValid()) b.UseTexture(recursos.cameraDepthTexture, AccessFlags.Read);
                b.UseAllGlobalTextures(true);       // mapas de sombras y datos de luces
                b.SetRenderAttachment(destino, 0, acceso);
                b.SetRenderFunc((Datos datos, RasterGraphContext ctx) =>
                {
                    if (bloque == null) bloque = new MaterialPropertyBlock();
                    bloque.Clear();
                    if (datos.fuente.IsValid()) bloque.SetTexture(idNieblaTex, datos.fuente);
                    ctx.cmd.DrawProcedural(Matrix4x4.identity, datos.material, datos.pasada, MeshTopology.Triangles, 3, 1, bloque);
                });
            }
        }
    }
}
