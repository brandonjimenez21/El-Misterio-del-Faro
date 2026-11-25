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
        _Orilla ("Ancho de la espuma de orilla (m)", Range(0, 4)) = 1.6
        _OrillaInt ("Intensidad de la espuma de orilla", Range(0, 1.5)) = 0.9
        _ZonaQuieta ("Zona quieta: x, z, radio, ancho del borde (radio 0 = apagada)", Vector) = (0, 0, 0, 4)
        _AnillosInt ("Anillos sin causa en la zona quieta", Range(0, 2)) = 0
    }
    SubShader
    {
        // Cola transparente (pero sin mezcla) para leer la profundidad de lo opaco y pintar espuma donde el agua toca algo
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Transparent-10" }
        ZWrite On
        // marca en el stencil los pixeles donde lo que se ve es agua: Faro/BajoElAgua (tiburon) solo se dibuja ahi, detras de la superficie
        Stencil { Ref 2 Comp Always Pass Replace }
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
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _ColorProfundo, _ColorCresta, _ColorCielo, _ColorEspuma;
                float _Amp, _Fuerza, _Velocidad, _Brillo, _BrilloInt, _Detalle, _Orilla, _OrillaInt, _AnillosInt;
                float4 _ZonaQuieta;
            CBUFFER_END
            // globales de ClimaAgua.cs: ola grande (dir.xy, frente, altura) y (largo, centro lateral, ancho lateral, -); fuerza de la lluvia
            float4 _FaroOla, _FaroOla2;
            float _FaroLluvia, _FaroRelampago;

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float h : TEXCOORD2;
                float jac : TEXCOORD5;
                float quieta : TEXCOORD6;
                float olaG : TEXCOORD7;        // 0..1 dentro de la ola grande
                float olaH : TEXCOORD8;        // cuanto sube el agua por la ola grande (m)
                half fogFactor : TEXCOORD3;
                float4 screenPos : TEXCOORD4;
            };

            // una ola de Gerstner: acumula desplazamiento, tangente y binormal
            static float gMulAmp = 1.0;      // la ola grande hace crecer tambien el oleaje que lleva encima
            void Ola(float2 dir, float wl, float amp, float vel, float2 p, float t,
                     inout float3 disp, inout float3 tang, inout float3 bin)
            {
                float k = 6.2831853 / wl;
                float c = sqrt(9.8 / k) * vel;
                float2 d = normalize(dir);
                float f = k * (dot(d, p) - c * t);
                float a = amp * _Amp * gMulAmp;
                float q = saturate(_Fuerza * 0.55) / (k * max(a, 0.001) * 4.0);
                q = min(q, _Fuerza * 0.9);
                float s = sin(f), co = cos(f);
                disp += float3(d.x * q * a * co, a * s, d.y * q * a * co);
                tang += float3(-d.x * d.x * q * k * a * s, d.x * k * a * co, -d.x * d.y * q * k * a * s);
                bin += float3(-d.x * d.y * q * k * a * s, d.y * k * a * co, -d.y * d.y * q * k * a * s);
            }

            float Hash2(float2 q) { q = frac(q * float2(0.1031, 0.1030)); q += dot(q, q.yx + 33.33); return frac((q.x + q.y) * q.x); }
            float Ruido2(float2 q)
            {
                float2 i = floor(q), f = frac(q);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(Hash2(i), Hash2(i + float2(1, 0)), f.x), lerp(Hash2(i + float2(0, 1)), Hash2(i + float2(1, 1)), f.x), f.y);
            }
            float Fbm2(float2 q) { return Ruido2(q) * 0.5 + Ruido2(q * 2.07 + 5.3) * 0.3 + Ruido2(q * 4.3 + 1.7) * 0.2; }

            // gotas de lluvia sobre el mar: cada celda tiene una gota que cae en un momento distinto y abre un anillo
            float2 Hash22(float2 q)
            {
                float3 p3 = frac(float3(q.xyx) * float3(0.1031, 0.1030, 0.0973));
                p3 += dot(p3, p3.yzx + 33.33);
                return frac((p3.xx + p3.yz) * p3.zy);
            }
            float2 Anillos(float2 q, float t)
            {
                float2 r = Hash22(floor(q));
                float2 f = frac(q) - 0.5 - (r - 0.5) * 0.5;
                float fase = frac(t + r.x * 7.0);
                float d = length(f);
                float radio = fase * 0.45;
                float onda = sin((d - radio) * 50.0) * saturate(1.0 - abs(d - radio) * 11.0) * (1.0 - fase) * (1.0 - fase);
                return f / max(d, 1e-3) * onda;
            }

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 wp = TransformObjectToWorld(IN.positionOS.xyz);
                float2 p = wp.xz;
                float t = _Time.y * _Velocidad;
                float3 disp = 0, tang = float3(1, 0, 0), bin = float3(0, 0, 1);
                // ola grande que viene del mar (ClimaAgua.cs): un bulto de agua que avanza, con el frente mas empinado que la espalda
                float olaH = 0.0, olaE = 0.0;
                float2 dHola = 0;
                if (_FaroOla.w > 0.001)
                {
                    float2 dO = _FaroOla.xy, pO = float2(-dO.y, dO.x);
                    float x = dot(dO, p) - _FaroOla.z;
                    float s = x > 0.0 ? _FaroOla2.x * 0.55 : _FaroOla2.x;
                    float l = (dot(pO, p) - _FaroOla2.y) / _FaroOla2.z;
                    olaE = exp(-x * x / (s * s)) * exp(-l * l);
                    olaH = _FaroOla.w * olaE;
                    // pendiente de la ola (para la normal): derivada a lo largo y a lo ancho
                    float dx = olaH * (-2.0 * x / (s * s));
                    float dl = olaH * (-2.0 * l / _FaroOla2.z);
                    dHola = dO * dx + pO * dl;
                    gMulAmp = 1.0 + 0.55 * olaE * saturate(_FaroOla.w);
                }
                Ola(float2(1.0, 0.12), 70.0, 0.30, 1.0, p, t, disp, tang, bin);   // mar de fondo (olas largas y altas)
                Ola(float2(1.0, 0.35), 38.0, 0.30, 1.0, p, t, disp, tang, bin);
                Ola(float2(0.8, -0.6), 21.0, 0.18, 1.0, p, t, disp, tang, bin);
                Ola(float2(-0.3, 1.0), 15.0, 0.09, 1.0, p, t, disp, tang, bin);
                Ola(float2(0.9, 0.9), 9.5, 0.04, 1.0, p, t, disp, tang, bin);   // >5 muestras por onda en la malla (1.6 m) para evitar aliasing
                Ola(float2(0.6, -0.8), 12.5, 0.07, 1.0, p, t, disp, tang, bin);   // oleaje de viento (tormenta)
                Ola(float2(1.0, -0.2), 8.5, 0.035, 1.0, p, t, disp, tang, bin);
                disp.y += olaH;
                tang.y += dHola.x;
                bin.y += dHola.y;
                OUT.olaG = saturate(olaE * saturate(_FaroOla.w * 1.2));
                OUT.olaH = olaH;
                // zona quieta: el agua se aplana por completo en un charco (algo no la deja moverse)
                float kq = _ZonaQuieta.z > 0.0 ? 1.0 - smoothstep(_ZonaQuieta.z - _ZonaQuieta.w, _ZonaQuieta.z + _ZonaQuieta.w, distance(wp.xz, _ZonaQuieta.xy)) : 0.0;
                disp *= 1.0 - kq * 0.985;
                tang = lerp(tang, float3(1, 0, 0), kq);
                bin = lerp(bin, float3(0, 0, 1), kq);
                OUT.quieta = kq;
                wp += disp;
                OUT.h = disp.y;
                OUT.jac = tang.x * bin.z - tang.z * bin.x;      // < 1 donde las olas se "amontonan": ahi rompe la espuma
                OUT.positionWS = wp;
                OUT.normalWS = normalize(cross(bin, tang));
                OUT.positionCS = TransformWorldToHClip(wp);
                OUT.screenPos = ComputeScreenPos(OUT.positionCS);
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
                float distCam = distance(IN.positionWS, _WorldSpaceCameraPos);
                // lluvia: anillos de gotas cerca de la camara (lejos no se distinguen)
                float cercaLl = _FaroLluvia * (1.0 - smoothstep(12.0, 40.0, distCam));
                if (cercaLl > 0.01)
                {
                    float tl = _Time.y * 1.3;
                    float2 g = Anillos(p * 2.2, tl) + Anillos(p * 3.1 + 11.7, tl * 1.17 + 0.4) * 0.8;
                    N.xz += g * 0.5 * cercaLl;
                }
                N = normalize(N);
                float3 V = normalize(_WorldSpaceCameraPos - IN.positionWS);
                // en la zona quieta no hay ondas finas ni brillo: un espejo negro
                N = normalize(lerp(N, float3(0, 1, 0), IN.quieta * 0.97));
                float fres = 0.02 + 0.98 * pow(1.0 - saturate(dot(N, V)), 5.0);

                float alto = saturate((IN.h - IN.olaH * (1.0 - IN.quieta)) / (0.6 * max(_Amp, 0.01)) * 0.5 + 0.5);   // altura del oleaje sin el bulto de la ola grande
                half3 col = lerp(_ColorProfundo.rgb, _ColorCresta.rgb, alto);
                col = lerp(col, _ColorCielo.rgb, fres * 0.8);

                // brillo de la luna sobre el agua
                Light L = GetMainLight();
                float3 H = normalize(L.direction + V);
                float spec = pow(saturate(dot(N, H)), _Brillo);
                col += L.color * spec * _BrilloInt * (0.25 + fres);

                // espuma suave en las crestas altas
                float espuma = smoothstep(0.50, 0.95, alto) * saturate(_Fuerza - 0.1);
                float rompe = (1.0 - smoothstep(0.18, 0.62, IN.jac)) * saturate(_Fuerza - 0.2);      // crestas que rompen
                espuma = saturate(max(espuma, rompe * 1.2));
                float ruido = 0.5 + 0.5 * sin(p.x * 0.9 + p.y * 1.3 + t * 0.6) * sin(p.y * 1.1 - p.x * 0.7 - t * 0.4);
                ruido = saturate(ruido + 0.25 * sin(p.x * 3.1 + t * 1.9) * sin(p.y * 2.7 - t * 1.4));
                col = lerp(col, _ColorEspuma.rgb, espuma * smoothstep(0.15, 0.75, ruido) * 0.9);
                // ola grande: agua mas clara y verdosa en la cara que se levanta y espuma que se rompe en la cresta
                if (IN.olaG > 0.01)
                {
                    float2 dO = _FaroOla.xy;
                    float s = _FaroOla2.x;
                    float xr = dot(dO, p) - _FaroOla.z;                                   // > 0 delante de la cresta, < 0 detras
                    float zona = smoothstep(0.15, 0.5, IN.olaG);
                    // la cara que se levanta deja pasar algo de luz: agua mas clara y verdosa
                    float cara = saturate(1.0 - abs(xr - 0.25 * s) / (0.45 * s));
                    col = lerp(col, _ColorCresta.rgb * 1.9 + half3(0.0, 0.014, 0.01), cara * IN.olaG * 0.4 * (1.0 - fres));
                    // la cresta rompe en una linea de espuma y detras queda agua blanca en jirones
                    float lineaC = exp(-pow((xr + 0.1 * s) / (0.2 * s), 2.0));
                    float estelaC = smoothstep(0.0, -0.25 * s, xr) * exp(-pow(xr / (1.1 * s), 2.0));
                    float enc1 = Fbm2(p * 0.8 + dO * t * 0.5);
                    float enc2 = Fbm2(p * float2(1.9, 2.4) - dO * t * 0.3 + 7.1);
                    float blanca = lineaC * smoothstep(0.3, 0.55, enc1) + estelaC * smoothstep(0.52, 0.74, enc2) * 0.45;
                    col = lerp(col, _ColorEspuma.rgb * 1.6, saturate(blanca * zona) * 0.9);
                }

                // espuma de orilla: donde el agua esta cerca de algo opaco (costa, rocas, pilotes) segun la profundidad
                float2 suv = IN.screenPos.xy / IN.screenPos.w;
                float escena = LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams);
                float dif = max(escena - IN.screenPos.w, 0.0);
                // la ola que llega empuja la espuma hacia arriba (mas ancha en la cresta) y al retirarse deja jirones
                float subida = saturate(IN.h / (0.5 * max(_Amp, 0.01)) * 0.5 + 0.5);
                float ancho = max(_Orilla, 0.01) * (0.55 + 1.1 * subida + 0.9 * IN.olaG);   // la ola grande sube por la costa hecha espuma
                float cerca = 1.0 - smoothstep(0.0, ancho, dif);
                float ondas = 0.55 + 0.45 * sin(dif * 7.0 - t * 2.2 + p.x * 0.35 + p.y * 0.3);   // franjas que avanzan hacia la orilla
                // encaje de espuma (celdas que se abren y cierran) en vez de manchas lisas
                float enc = Fbm2(p * 1.6 + float2(t * 0.15, -t * 0.11));
                float encaje = smoothstep(0.38, 0.62, enc + 0.25 * cerca);
                float orilla = cerca * lerp(ondas, 1.0, subida * 0.6) * encaje * _OrillaInt;
                // golpe contra la roca o el pilote: estallido blanco cuando sube la ola
                float golpe = (1.0 - smoothstep(0.0, ancho * 0.35, dif)) * smoothstep(0.55, 0.9, subida);
                // estela: espuma vieja que se aleja de la costa en hilos
                float estela = (1.0 - smoothstep(ancho, ancho * 3.5, dif)) * smoothstep(0.55, 0.75, Fbm2(p * float2(0.7, 2.2) + t * 0.08)) * 0.45;
                col = lerp(col, _ColorEspuma.rgb * 1.5, saturate(max(orilla, estela * _OrillaInt)));
                col = lerp(col, _ColorEspuma.rgb * 2.2, saturate(golpe * _OrillaInt));

                // zona quieta: mas oscura, y anillos que se expanden desde su centro sin que nada los provoque
                col *= lerp(1.0, 0.32, IN.quieta);
                float rr = distance(p, _ZonaQuieta.xy);
                float anillo = pow(saturate(0.5 + 0.5 * sin(rr * 2.4 - _Time.y * 1.1)), 8.0) * exp(-rr * 0.16) * smoothstep(0.4, 1.2, rr);
                col += _ColorCielo.rgb * 1.6 * anillo * IN.quieta * _AnillosInt;

                // el relampago se refleja en el mar (sobre todo de lado, donde el agua es espejo)
                col += half3(0.45, 0.5, 0.65) * _FaroRelampago * fres * 0.9;

                col = MixFog(col, IN.fogFactor);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
