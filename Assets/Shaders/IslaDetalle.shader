// Isla con detalle: usa la textura horneada en Blender (color + normal) y le suma, sin tocar la malla,
//  - roca: detalle "triplanar" (se proyecta por el mundo, sin estirarse en paredes y "dedos") en dos escalas,
//  - pasto: detalle de hebras proyectado desde arriba en las zonas verdes.
// El detalle se desvanece con la distancia (barato y sin repeticiones visibles).
// _Modo = 1 sirve para rocas sueltas (usa _Color en vez de la textura horneada).
Shader "Faro/IslaDetalle"
{
    Properties
    {
        _BaseMap ("Color horneado", 2D) = "white" {}
        _BumpMap ("Normal horneado", 2D) = "bump" {}
        _Color ("Color (rocas sueltas)", Color) = (0.2, 0.19, 0.17, 1)
        _DetRoca ("Detalle roca", 2D) = "white" {}
        _DetRocaN ("Detalle roca (normal)", 2D) = "bump" {}
        _DetPasto ("Detalle pasto", 2D) = "white" {}
        _DetPastoN ("Detalle pasto (normal)", 2D) = "bump" {}
        _EscalaRoca ("Escala roca grande (1/m)", Float) = 0.3
        _EscalaRoca2 ("Escala roca fina (1/m)", Float) = 1.4
        _EscalaPasto ("Escala pasto (1/m)", Float) = 0.9
        _FuerzaColor ("Fuerza del detalle (color)", Range(0, 1.5)) = 0.9
        _FuerzaNormal ("Fuerza del detalle (normal)", Range(0, 2)) = 1.6
        _DistDetalle ("Distancia del detalle (m)", Float) = 90
        _Modo ("0 = isla, 1 = roca suelta", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_BumpMap); SAMPLER(sampler_BumpMap);
            TEXTURE2D(_DetRoca); SAMPLER(sampler_DetRoca);
            TEXTURE2D(_DetRocaN); SAMPLER(sampler_DetRocaN);
            TEXTURE2D(_DetPasto); SAMPLER(sampler_DetPasto);
            TEXTURE2D(_DetPastoN); SAMPLER(sampler_DetPastoN);
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _Color;
                float _EscalaRoca, _EscalaRoca2, _EscalaPasto, _FuerzaColor, _FuerzaNormal, _DistDetalle, _Modo;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float4 tangentOS : TANGENT; float2 uv : TEXCOORD0; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                half3 normalWS : TEXCOORD2;
                half4 tangentWS : TEXCOORD3;
                half fogFactor : TEXCOORD4;
            };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs vp = GetVertexPositionInputs(IN.positionOS.xyz);
                VertexNormalInputs vn = GetVertexNormalInputs(IN.normalOS, IN.tangentOS);
                OUT.positionCS = vp.positionCS;
                OUT.positionWS = vp.positionWS;
                OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
                OUT.normalWS = vn.normalWS;
                OUT.tangentWS = half4(vn.tangentWS, IN.tangentOS.w * GetOddNegativeScale());
                OUT.fogFactor = ComputeFogFactor(vp.positionCS.z);
                return OUT;
            }

            // normal de detalle triplanar (mezcla "whiteout") sobre la normal base Nb
            half3 TriNormal(TEXTURE2D_PARAM(tex, smp), float3 p, float scale, half3 Nb, half3 w, half fuerza)
            {
                half3 tx = UnpackNormalScale(SAMPLE_TEXTURE2D(tex, smp, p.zy * scale), fuerza);
                half3 ty = UnpackNormalScale(SAMPLE_TEXTURE2D(tex, smp, p.xz * scale), fuerza);
                half3 tz = UnpackNormalScale(SAMPLE_TEXTURE2D(tex, smp, p.xy * scale), fuerza);
                tx = half3(tx.xy + Nb.zy, abs(tx.z) * Nb.x);
                ty = half3(ty.xy + Nb.xz, abs(ty.z) * Nb.y);
                tz = half3(tz.xy + Nb.xy, abs(tz.z) * Nb.z);
                return normalize(tx.zyx * w.x + ty.xzy * w.y + tz.xyz * w.z);
            }
            half3 TriColor(TEXTURE2D_PARAM(tex, smp), float3 p, float scale, half3 w)
            {
                return SAMPLE_TEXTURE2D(tex, smp, p.zy * scale).rgb * w.x
                     + SAMPLE_TEXTURE2D(tex, smp, p.xz * scale).rgb * w.y
                     + SAMPLE_TEXTURE2D(tex, smp, p.xy * scale).rgb * w.z;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 pw = IN.positionWS;
                half3 Ng = normalize(IN.normalWS);
                half3 T = normalize(IN.tangentWS.xyz);
                half3 B = cross(Ng, T) * IN.tangentWS.w;
                half4 baseS = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv);
                half3 alb = lerp(baseS.rgb, _Color.rgb, _Modo);
                half3 nT = lerp(UnpackNormal(SAMPLE_TEXTURE2D(_BumpMap, sampler_BumpMap, IN.uv)), half3(0, 0, 1), _Modo);
                half3 Nb = normalize(TransformTangentToWorld(nT, half3x3(T, B, Ng)));

                // distancia -> el detalle se va apagando
                float dist = distance(pw, _WorldSpaceCameraPos);
                half fade = 1.0 - smoothstep(_DistDetalle * 0.55, _DistDetalle, dist);

                // mascara de pasto: zonas verdes de la textura y poco empinadas (en rocas sueltas, solo una capa de musgo arriba)
                half verde = smoothstep(0.012, 0.05, baseS.g - baseS.r * 1.1);
                half llano = smoothstep(0.72, 0.9, Ng.y);
                half pasto = lerp(verde * llano, llano * 0.35, _Modo);
                half roca = 1.0 - pasto;
                // en la roca se suaviza la textura horneada (las franjas de estratos eran demasiado regulares); el detalle pone la textura fina
                if (_Modo < 0.5)
                {
                    half3 suave = SAMPLE_TEXTURE2D_LOD(_BaseMap, sampler_BaseMap, IN.uv, 4.0).rgb;
                    alb = lerp(alb, suave, roca * 0.8);
                }

                half3 w = pow(abs(Ng), 4.0); w /= (w.x + w.y + w.z + 1e-4);
                half3 N = Nb;
                half3 detC = 1;
                half suav = 0.12;
                if (fade > 0.001)
                {
                    // roca: dos escalas para romper la repeticion
                    half3 r1 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw, _EscalaRoca, w);
                    half3 r2 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw + 17.3, _EscalaRoca2, w);
                    half3 rocaC = r1 * r2 * 1.9;
                    half3 nr = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw, _EscalaRoca2, Nb, w, _FuerzaNormal * fade);
                    nr = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw + 17.3, _EscalaRoca * 1.7, nr, w, _FuerzaNormal * 0.7 * fade);
                    // pasto: proyeccion desde arriba
                    half3 p1 = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, pw.xz * _EscalaPasto).rgb;
                    half3 p2 = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, pw.xz * _EscalaPasto * 0.23 + 0.37).rgb;
                    half3 pastoC = p1 * p2 * 2.2;
                    half3 tp = UnpackNormalScale(SAMPLE_TEXTURE2D(_DetPastoN, sampler_DetPastoN, pw.xz * _EscalaPasto), _FuerzaNormal * fade);
                    half3 np = normalize(Nb + half3(tp.x, 0, tp.y) * 0.8);
                    detC = lerp(rocaC, pastoC, pasto);
                    N = normalize(lerp(nr, np, pasto));
                    detC = lerp(1.0, detC, _FuerzaColor * fade);
                    suav = lerp(0.2, 0.1, pasto);
                }
                alb *= detC;

                InputData id = (InputData)0;
                id.positionWS = pw;
                id.normalWS = NormalizeNormalPerPixel(N);
                id.viewDirectionWS = GetWorldSpaceNormalizeViewDir(pw);
                id.shadowCoord = TransformWorldToShadowCoord(pw);
                id.fogCoord = InitializeInputDataFog(float4(pw, 1.0), IN.fogFactor);
                id.bakedGI = SampleSH(id.normalWS);
                id.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(IN.positionCS);
                id.shadowMask = half4(1, 1, 1, 1);

                SurfaceData sd = (SurfaceData)0;
                sd.albedo = alb;
                sd.metallic = 0;
                sd.smoothness = suav;
                sd.occlusion = 1;
                sd.alpha = 1;
                sd.normalTS = half3(0, 0, 1);
                half4 c = UniversalFragmentPBR(id, sd);
                c.rgb = MixFog(c.rgb, id.fogCoord);
                return half4(c.rgb, 1);
            }
            ENDHLSL
        }
        UsePass "Universal Render Pipeline/Lit/ShadowCaster"
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
        UsePass "Universal Render Pipeline/Lit/DepthNormals"
    }
    FallBack Off
}
