// Niebla baja: capas horizontales semitransparentes con ruido que se desplaza con el viento.
// Se funden contra la geometria (profundidad), se desvanecen cerca de la camara y a lo lejos, y toman el color de la niebla global.
// UV0 en unidades de 40 m (ver blender/scripts/niebla_baja.py).
Shader "Faro/NieblaBaja"
{
    Properties
    {
        _Color ("Color (RGB) y opacidad maxima (A)", Color) = (0.2, 0.26, 0.35, 0.5)
        _Escala ("Escala del ruido", Float) = 1.0
        _Velocidad ("Velocidad", Float) = 0.015
        _Suavidad ("Fundido con la geometria (m)", Float) = 1.6
        _CercaIni ("Se desvanece de cerca (m)", Float) = 1.5
        _CercaFin ("Opaca a partir de (m)", Float) = 9.0
        _LejosIni ("Empieza a desvanecerse (m)", Float) = 90
        _LejosFin ("Invisible a (m)", Float) = 300
        _Cobertura ("Cobertura (mas = mas niebla)", Range(0, 1)) = 0.55
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Transparent" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off
        Cull Off
        Pass
        {
            Name "Niebla"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
                float _Escala, _Velocidad, _Suavidad, _CercaIni, _CercaFin, _LejosIni, _LejosFin;
                half _Cobertura;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 positionWS : TEXCOORD1; };

            float hash21(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
            float vnoise(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(hash21(i), hash21(i + float2(1, 0)), f.x), lerp(hash21(i + float2(0, 1)), hash21(i + float2(1, 1)), f.x), f.y);
            }
            float fbm(float2 p)
            {
                float a = 0.5, s = 0;
                for (int k = 0; k < 4; k++) { s += a * vnoise(p); p = p * 2.03 + 11.7; a *= 0.5; }
                return s;
            }

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs vp = GetVertexPositionInputs(IN.positionOS.xyz);
                OUT.positionCS = vp.positionCS;
                OUT.positionWS = vp.positionWS;
                OUT.uv = IN.uv;
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float t = _Time.y * _Velocidad;
                float2 p = IN.uv * _Escala;
                // dos capas de ruido que se cruzan: la niebla "respira" y avanza con el viento
                float n1 = fbm(p + float2(t * 1.0, t * 0.55));
                float n2 = fbm(p * 2.1 + float2(-t * 1.3, t * 0.8) + 4.3);
                float n = n1 * 0.65 + n2 * 0.35;
                float dens = smoothstep(1.0 - _Cobertura - 0.12, 1.0 - _Cobertura + 0.28, n);

                float dist = distance(IN.positionWS, _WorldSpaceCameraPos);
                float cerca = smoothstep(_CercaIni, _CercaFin, dist);
                float lejos = 1.0 - smoothstep(_LejosIni, _LejosFin, dist);

                // fundido contra lo que hay detras de la capa (suelo, pilotes, rocas): sin cortes duros
                float2 suv = GetNormalizedScreenSpaceUV(IN.positionCS);
                float prof = LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams);
                float mia = LinearEyeDepth(IN.positionCS.z, _ZBufferParams);
                float suave = saturate((prof - mia) / max(_Suavidad, 0.01));

                half a = _Color.a * dens * cerca * lejos * suave;
                return half4(_Color.rgb, a);
            }
            ENDHLSL
        }
    }
}
