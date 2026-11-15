// Charco de lluvia (URP, transparente): refleja el cielo / sondas de reflejo con Fresnel, anillos de gotas que caen,
// bordes que se funden con el suelo mojado (uv.x: 0 en el borde, 1 en el centro; lo genera narrativa_exterior.py)
// y destello con los relampagos (global _FaroRelampago).
Shader "Faro/Charco"
{
    Properties
    {
        _ColorAgua ("Color del agua (fondo)", Color) = (0.015, 0.018, 0.02, 1)
        _Opacidad ("Opacidad", Range(0, 1)) = 0.85
        _Reflejo ("Fuerza del reflejo", Range(0, 3)) = 1.3
        _Gotas ("Densidad de gotas", Range(0, 12)) = 5
        _FuerzaGotas ("Fuerza de los anillos", Range(0, 1)) = 0.35
        _VelGotas ("Velocidad de las gotas", Range(0, 3)) = 1.1
        _Borde ("Ancho del borde difuso", Range(0.05, 1)) = 0.55
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent-20" "RenderPipeline"="UniversalPipeline" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off
        Offset -1, -1
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile _ _REFLECTION_PROBE_BLENDING
            #pragma multi_compile _ _REFLECTION_PROBE_BOX_PROJECTION
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _ColorAgua;
                float _Opacidad, _Reflejo, _Gotas, _FuerzaGotas, _VelGotas, _Borde;
            CBUFFER_END
            float _FaroRelampago;
            float _FaroLluvia, _FaroCharcos;   // globales (ClimaAgua.cs): fuerza de la lluvia y agua acumulada

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float2 uv : TEXCOORD1;
                half fogFactor : TEXCOORD2;
            };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionWS = TransformObjectToWorld(IN.positionOS.xyz);
                OUT.positionCS = TransformWorldToHClip(OUT.positionWS);
                OUT.uv = IN.uv;
                OUT.fogFactor = ComputeFogFactor(OUT.positionCS.z);
                return OUT;
            }

            float2 Hash22(float2 p)
            {
                float3 p3 = frac(float3(p.xyx) * float3(0.1031, 0.1030, 0.0973));
                p3 += dot(p3, p3.yzx + 33.33);
                return frac((p3.xx + p3.yz) * p3.zy);
            }

            // una capa de gotas: cada celda tiene una gota que cae en un momento distinto y abre un anillo
            float2 Anillos(float2 p, float t)
            {
                float2 c = floor(p);
                float2 r = Hash22(c);
                float2 f = frac(p) - 0.5 - (r - 0.5) * 0.5;
                float fase = frac(t + r.x * 7.0);
                float d = length(f);
                float radio = fase * 0.45;
                float onda = sin((d - radio) * 55.0) * saturate(1.0 - abs(d - radio) * 12.0) * (1.0 - fase) * (1.0 - fase);
                return f / max(d, 1e-3) * onda;
            }

            float Ruido(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                float a = Hash22(i).x, b = Hash22(i + float2(1, 0)).x, c = Hash22(i + float2(0, 1)).x, d = Hash22(i + float2(1, 1)).x;
                return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float2 p = IN.positionWS.xz;
                float t = _Time.y * _VelGotas;
                float2 n2 = Anillos(p * _Gotas, t) + Anillos(p * _Gotas * 1.37 + 17.3, t * 1.13 + 0.5) * 0.7;
                float fg = _FuerzaGotas * _FaroLluvia;     // con lluvia floja casi no hay anillos
                float3 N = normalize(float3(n2.x * fg, 1.0, n2.y * fg));
                float3 V = normalize(_WorldSpaceCameraPos - IN.positionWS);
                float fres = 0.03 + 0.97 * pow(1.0 - saturate(dot(N, V)), 5.0);
                float3 R = reflect(-V, N);
                float2 suv = GetNormalizedScreenSpaceUV(IN.positionCS);
                half3 refl = GlossyEnvironmentReflection(R, IN.positionWS, 0.02h, 1.0h, suv);
                half3 col = lerp(_ColorAgua.rgb, refl * _Reflejo, saturate(fres * 1.4));
                // brillo de la luna y del relampago sobre el agua
                Light L = GetMainLight();
                float spec = pow(saturate(dot(N, normalize(L.direction + V))), 400.0);
                col += L.color * spec * 3.0;
                col += half3(0.5, 0.56, 0.75) * _FaroRelampago * (0.15 + fres);
                // borde irregular: se funde con el suelo mojado. El charco crece desde el centro a medida que se junta agua
                float borde = IN.uv.x + (Ruido(p * 3.1) - 0.5) * 0.35;
                float lleno = lerp(0.9, -0.05, saturate(_FaroCharcos));
                float a = smoothstep(lleno, lleno + _Borde, borde) * _Opacidad;
                col = MixFog(col, IN.fogFactor);
                return half4(col, a);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
