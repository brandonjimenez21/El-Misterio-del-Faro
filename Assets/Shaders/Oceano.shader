// Oceano nocturno para "El Misterio del Faro" (URP). Olas de Gerstner animadas en el vertice,
// reflejo del cielo (Fresnel), brillo de la luna (luz direccional principal), espuma en crestas y niebla de URP.
Shader "Faro/Oceano"
{
    Properties
    {
        _ColorProfundo ("Color profundo", Color) = (0.004, 0.02, 0.032, 1)
        _ColorCresta ("Color cresta", Color) = (0.03, 0.09, 0.105, 1)
        _ColorCielo ("Color reflejado del cielo", Color) = (0.10, 0.14, 0.20, 1)
        _ColorEspuma ("Color espuma", Color) = (0.2, 0.26, 0.3, 1)
        _Amp ("Tamano de las olas", Range(0, 4)) = 1
        _Fuerza ("Fuerza (picos) de las olas", Range(0, 2)) = 1
        _Velocidad ("Velocidad", Range(0, 3)) = 1
        _Brillo ("Brillo de la luna (exponente)", Range(8, 600)) = 220
        _BrilloInt ("Intensidad del brillo", Range(0, 20)) = 5
        _Detalle ("Ondas finas", Range(0, 0.3)) = 0.07
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _ColorProfundo, _ColorCresta, _ColorCielo, _ColorEspuma;
                float _Amp, _Fuerza, _Velocidad, _Brillo, _BrilloInt, _Detalle;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float h : TEXCOORD2;
                half fogFactor : TEXCOORD3;
            };

            // una ola de Gerstner: acumula desplazamiento, tangente y binormal
            void Ola(float2 dir, float wl, float amp, float vel, float2 p, float t,
                     inout float3 disp, inout float3 tang, inout float3 bin)
            {
                float k = 6.2831853 / wl;
                float c = sqrt(9.8 / k) * vel;
                float2 d = normalize(dir);
                float f = k * (dot(d, p) - c * t);
                float a = amp * _Amp;
                float q = saturate(_Fuerza * 0.55) / (k * max(a, 0.001) * 4.0);
                q = min(q, _Fuerza * 0.9);
                float s = sin(f), co = cos(f);
                disp += float3(d.x * q * a * co, a * s, d.y * q * a * co);
                tang += float3(-d.x * d.x * q * k * a * s, d.x * k * a * co, -d.x * d.y * q * k * a * s);
                bin += float3(-d.x * d.y * q * k * a * s, d.y * k * a * co, -d.y * d.y * q * k * a * s);
            }

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 wp = TransformObjectToWorld(IN.positionOS.xyz);
                float2 p = wp.xz;
                float t = _Time.y * _Velocidad;
                float3 disp = 0, tang = float3(1, 0, 0), bin = float3(0, 0, 1);
                Ola(float2(1.0, 0.12), 70.0, 0.30, 1.0, p, t, disp, tang, bin);   // mar de fondo (olas largas y altas)
                Ola(float2(1.0, 0.35), 38.0, 0.30, 1.0, p, t, disp, tang, bin);
                Ola(float2(0.8, -0.6), 21.0, 0.18, 1.0, p, t, disp, tang, bin);
                Ola(float2(-0.3, 1.0), 15.0, 0.09, 1.0, p, t, disp, tang, bin);
                Ola(float2(0.9, 0.9), 9.5, 0.04, 1.0, p, t, disp, tang, bin);   // >5 muestras por onda en la malla (1.6 m) para evitar aliasing
                wp += disp;
                OUT.h = disp.y;
                OUT.positionWS = wp;
                OUT.normalWS = normalize(cross(bin, tang));
                OUT.positionCS = TransformWorldToHClip(wp);
                OUT.fogFactor = ComputeFogFactor(OUT.positionCS.z);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 N = normalize(IN.normalWS);
                float t = _Time.y * _Velocidad;
                float2 p = IN.positionWS.xz;
                // ondas finas
                N.x += _Detalle * (sin(p.x * 1.7 + t * 1.3) + sin(p.y * 2.3 - t * 1.7 + p.x * 0.4));
                N.z += _Detalle * (sin(p.y * 1.9 - t * 1.1) + sin(p.x * 2.7 + t * 1.5 + p.y * 0.3));
                N = normalize(N);
                float3 V = normalize(_WorldSpaceCameraPos - IN.positionWS);
                float fres = 0.02 + 0.98 * pow(1.0 - saturate(dot(N, V)), 5.0);

                float alto = saturate(IN.h / (0.6 * max(_Amp, 0.01)) * 0.5 + 0.5);
                half3 col = lerp(_ColorProfundo.rgb, _ColorCresta.rgb, alto);
                col = lerp(col, _ColorCielo.rgb, fres * 0.8);

                // brillo de la luna sobre el agua
                Light L = GetMainLight();
                float3 H = normalize(L.direction + V);
                float spec = pow(saturate(dot(N, H)), _Brillo);
                col += L.color * spec * _BrilloInt * (0.25 + fres);

                // espuma suave en las crestas altas
                float espuma = smoothstep(0.50, 0.95, alto) * saturate(_Fuerza - 0.1);
                float ruido = 0.5 + 0.5 * sin(p.x * 0.9 + p.y * 1.3 + t * 0.6) * sin(p.y * 1.1 - p.x * 0.7 - t * 0.4);
                ruido = saturate(ruido + 0.25 * sin(p.x * 3.1 + t * 1.9) * sin(p.y * 2.7 - t * 1.4));
                col = lerp(col, _ColorEspuma.rgb, espuma * ruido * 0.85);

                col = MixFog(col, IN.fogFactor);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
