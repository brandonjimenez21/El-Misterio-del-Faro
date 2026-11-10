// Camino oculto: cinta pegada al terreno que se "revela" de principio a fin (_Revelado 0..1).
// UV0.x = a lo ancho (0..1), UV0.y = a lo largo (0 en el cruce con el camino principal, 1 en el extremo).
// En el frente de revelado brilla un poco (luz del faro). Con _Revelado = 0 no se ve nada.
Shader "Faro/CaminoOculto"
{
    Properties
    {
        _Color ("Color tierra", Color) = (0.20, 0.14, 0.09, 1)
        _ColorPiedras ("Color guijarros", Color) = (0.38, 0.34, 0.28, 1)
        _Detalle ("Detalle (guijarros)", 2D) = "white" {}
        _Escala ("Escala del detalle (1/m)", Float) = 0.9
        _Revelado ("Revelado (0..1)", Range(0, 1)) = 0
        _Frente ("Ancho del frente (0..1)", Range(0.01, 0.4)) = 0.12
        _ColorBrillo ("Color del frente", Color) = (0.6, 0.85, 1, 1)
        _Brillo ("Intensidad del frente", Range(0, 6)) = 2.5
        _Opacidad ("Opacidad", Range(0, 1)) = 0.95
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Transparent" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off
        Offset -2, -2
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
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_Detalle); SAMPLER(sampler_Detalle);
            CBUFFER_START(UnityPerMaterial)
                half4 _Color, _ColorPiedras, _ColorBrillo;
                float _Escala, _Revelado, _Frente, _Brillo, _Opacidad;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 positionWS : TEXCOORD1; half fogFactor : TEXCOORD2; };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs vp = GetVertexPositionInputs(IN.positionOS.xyz);
                OUT.positionCS = vp.positionCS;
                OUT.positionWS = vp.positionWS;
                OUT.uv = IN.uv;
                OUT.fogFactor = ComputeFogFactor(vp.positionCS.z);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float2 w = IN.positionWS.xz * _Escala;
                half3 d1 = SAMPLE_TEXTURE2D(_Detalle, sampler_Detalle, w).rgb;
                half3 d2 = SAMPLE_TEXTURE2D(_Detalle, sampler_Detalle, w * 0.31 + 0.5).rgb;
                half ruido = d1.r * 0.6 + d2.r * 0.4;

                // forma: bordes irregulares que se funden con el suelo
                half lado = 1.0 - abs(IN.uv.x - 0.5) * 2.0;
                half borde = smoothstep(0.08, 0.5, lado + (ruido - 0.5) * 0.7);

                // revelado a lo largo del camino (con borde irregular), el frente brilla
                float p = IN.uv.y + (ruido - 0.5) * 0.06;
                float limite = _Revelado * (1.0 + _Frente) - _Frente * 0.0;
                half vis = saturate((limite - p) / max(_Frente, 0.001));
                half frente = saturate(1.0 - abs(vis - 0.5) * 2.0) * step(0.001, _Revelado) * step(_Revelado, 0.999);
                half alfa = borde * vis * _Opacidad;
                if (alfa < 0.002) discard;

                half3 alb = lerp(_Color.rgb, _ColorPiedras.rgb, smoothstep(0.55, 0.8, d1.r * d2.r * 2.2));
                alb *= 0.6 + 0.8 * ruido;

                InputData id = (InputData)0;
                id.positionWS = IN.positionWS;
                id.normalWS = half3(0, 1, 0);
                id.viewDirectionWS = GetWorldSpaceNormalizeViewDir(IN.positionWS);
                id.shadowCoord = TransformWorldToShadowCoord(IN.positionWS);
                id.fogCoord = InitializeInputDataFog(float4(IN.positionWS, 1.0), IN.fogFactor);
                id.bakedGI = SampleSH(id.normalWS);
                id.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(IN.positionCS);
                id.shadowMask = half4(1, 1, 1, 1);
                SurfaceData sd = (SurfaceData)0;
                sd.albedo = alb;
                sd.smoothness = 0.1;
                sd.occlusion = 1;
                sd.alpha = alfa;
                sd.emission = _ColorBrillo.rgb * _Brillo * frente * borde;
                sd.normalTS = half3(0, 0, 1);
                half4 c = UniversalFragmentPBR(id, sd);
                c.rgb = MixFog(c.rgb, id.fogCoord);
                return half4(c.rgb, alfa);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
