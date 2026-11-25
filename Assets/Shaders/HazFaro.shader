// Haz de luz del faro: cono aditivo con bordes suaves, que se apaga con la distancia y flota polvo/niebla dentro.
// UV0.v = distancia desde la lampara (0..1). Aditivo, sin escribir profundidad.
Shader "Faro/HazFaro"
{
    Properties
    {
        _Color ("Color", Color) = (1.0, 0.85, 0.55, 1)
        _Intensidad ("Intensidad", Float) = 1.0
        _Borde ("Dureza del borde", Float) = 1.6
        _Alcance ("Cuanto llega (1 = todo)", Range(0.1, 2)) = 1.0
        _Cerca ("Se desvanece cerca de la camara (m)", Float) = 12
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Transparent+10" }
        Blend One One
        ZWrite Off
        Cull Off
        Pass
        {
            Name "Haz"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
                float _Intensidad, _Borde, _Alcance, _Cerca;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 positionWS : TEXCOORD1; float3 normalWS : TEXCOORD2; };

            float hash21(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
            float vnoise(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(hash21(i), hash21(i + float2(1, 0)), f.x), lerp(hash21(i + float2(0, 1)), hash21(i + float2(1, 1)), f.x), f.y);
            }

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                VertexPositionInputs vp = GetVertexPositionInputs(IN.positionOS.xyz);
                OUT.positionCS = vp.positionCS;
                OUT.positionWS = vp.positionWS;
                OUT.normalWS = TransformObjectToWorldNormal(IN.normalOS);
                OUT.uv = IN.uv;
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 V = normalize(_WorldSpaceCameraPos - IN.positionWS);
                float3 N = normalize(IN.normalWS);
                // el cono visto de lado es mas denso en el centro: el borde se desvanece
                float f = pow(saturate(abs(dot(N, V))), _Borde);
                float t = IN.uv.y / _Alcance;
                float largo = saturate(1.0 - t);
                largo = largo * largo;
                float arranque = smoothstep(0.0, 0.03, IN.uv.y);
                // polvo en suspension que se desplaza
                float2 q = IN.positionWS.xz * 0.07 + IN.positionWS.y * 0.03 + _Time.y * 0.05;
                float polvo = 0.65 + 0.7 * vnoise(q) * vnoise(q * 2.3 + 5.0);
                float cerca = smoothstep(0.0, _Cerca, distance(IN.positionWS, _WorldSpaceCameraPos));
                float a = f * largo * arranque * polvo * cerca * _Intensidad;
                return half4(_Color.rgb * a, 1);
            }
            ENDHLSL
        }
    }
}
