// Niebla volumetrica ligera (la usa NieblaVolumetricaFeature, no se asigna a objetos).
// Recorre el rayo de cada pixel a traves de la bruma y suma la luz que la niebla dispersa hacia la camara:
//   - luces puntuales y focos (faroles, linterna, haz del faro): halo en la bruma y haces recortados por sus sombras
//   - luna y relampago (direccionales): la bruma se ilumina y las rocas proyectan sombra dentro de ella
// Pasadas: 0 = trazar (media resolucion), 1 y 2 = desenfoque que respeta bordes, 3 = sumar a la imagen.
Shader "Hidden/Faro/NieblaVolumetrica"
{
    SubShader
    {
        Tags { "RenderPipeline" = "UniversalPipeline" }
        ZTest Always ZWrite Off Cull Off

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

        struct Attributes { uint vertexID : SV_VertexID; };
        struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };

        Varyings Vert(Attributes i)
        {
            Varyings o;
            o.positionCS = GetFullScreenTriangleVertexPosition(i.vertexID);
            o.uv = GetFullScreenTriangleTexCoord(i.vertexID);
            return o;
        }

        TEXTURE2D(_NieblaTex);     // sampler_LinearClamp y sampler_PointClamp ya los declara URP
        float4 _NieblaTam;          // 1/ancho, 1/alto, ancho, alto de la textura de niebla

        float ProfundidadLineal(float2 uv)
        {
            return LinearEyeDepth(SampleSceneDepth(uv), _ZBufferParams);
        }

        // desenfoque gaussiano en una direccion que no mezcla a traves de los bordes
        half4 Desenfocar(float2 uv, float2 paso)
        {
            static const float pesos[4] = { 0.324, 0.232, 0.0855, 0.0205 };
            float centro = ProfundidadLineal(uv);
            float3 suma = SAMPLE_TEXTURE2D(_NieblaTex, sampler_LinearClamp, uv).rgb * pesos[0];
            float peso = pesos[0];
            for (int k = 1; k < 4; k++)
            {
                for (int signo = -1; signo <= 1; signo += 2)
                {
                    float2 uvk = uv + paso * (k * signo);
                    float pr = ProfundidadLineal(uvk);
                    // no mezclar a traves de un borde (un poste delante de la bruma lejana)
                    float w = pesos[k] * saturate(1.0 - abs(pr - centro) / (0.12 * centro + 0.05));
                    suma += SAMPLE_TEXTURE2D(_NieblaTex, sampler_LinearClamp, uvk).rgb * w;
                    peso += w;
                }
            }
            return half4(suma / peso, 1);
        }
        ENDHLSL

        // ------------------------------------------------------------------ 0: trazar
        Pass
        {
            Name "Trazar"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE
            #pragma multi_compile _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            int _Pasos;
            float _Distancia;           // hasta donde se traza (m)
            float _Densidad;            // cuanta luz dispersa la bruma por metro
            float _Extincion;           // cuanto se apaga la luz dispersada con la distancia
            float _AlturaBase;          // por debajo de esta altura la bruma tiene densidad completa
            float _CaidaAltura;         // cuanto se aclara por metro por encima
            float _IntLocales;          // luces puntuales y focos
            float _IntLuna;             // luz principal (luna)
            float _IntDireccionales;    // otras direccionales (relampago)
            float _Anisotropia;         // 0 = igual en todas direcciones; 0.6 = brilla mas mirando hacia la luz
            float _MaxAtenuacion;       // limite del brillo junto a una luz (evita puntos quemados)
            float _Ruido;               // 0..1 cuanto varia la densidad (jirones de bruma)
            float _EscalaRuido;
            float3 _VientoRuido;

            float Hash3(float3 p)
            {
                p = frac(p * 0.3183099 + 0.1);
                p *= 17.0;
                return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
            }

            float Ruido3(float3 x)
            {
                float3 i = floor(x), f = frac(x);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(lerp(Hash3(i), Hash3(i + float3(1, 0, 0)), f.x),
                                 lerp(Hash3(i + float3(0, 1, 0)), Hash3(i + float3(1, 1, 0)), f.x), f.y),
                            lerp(lerp(Hash3(i + float3(0, 0, 1)), Hash3(i + float3(1, 0, 1)), f.x),
                                 lerp(Hash3(i + float3(0, 1, 1)), Hash3(i + float3(1, 1, 1)), f.x), f.y), f.z);
            }

            // Henyey-Greenstein normalizada (vale 1 cuando g = 0)
            float Fase(float cosAng, float g)
            {
                float g2 = g * g;
                return (1.0 - g2) / pow(max(1.0 + g2 - 2.0 * g * cosAng, 1e-3), 1.5);
            }

            half4 Frag(Varyings i) : SV_Target
            {
                float2 uv = i.uv;
                float prof = SampleSceneDepth(uv);
            #if !UNITY_REVERSED_Z
                prof = lerp(UNITY_NEAR_CLIP_VALUE, 1.0, prof);
            #endif
                float3 destino = ComputeWorldSpacePosition(uv, prof, UNITY_MATRIX_I_VP);
                float3 origen = GetCameraPositionWS();
                float3 rayo = destino - origen;
                float largo = length(rayo);
                float3 dir = rayo / max(largo, 1e-4);
                float total = min(largo, _Distancia);

                // desfase fijo por pixel: reparte las muestras para que no se vean "rebanadas" (el desenfoque lo alisa)
                float desfase = InterleavedGradientNoise(i.positionCS.xy, 0);

                InputData inputData = (InputData)0;
                inputData.normalizedScreenSpaceUV = uv;

                float3 luz = 0;
                float pasos = max(_Pasos, 1);
                for (int s = 0; s < _Pasos; s++)
                {
                    // muestras mas juntas cerca de la camara
                    float u0 = s / pasos, u1 = (s + 1) / pasos;
                    float t0 = total * u0 * u0, t1 = total * u1 * u1;
                    float t = lerp(t0, t1, desfase);
                    float dt = t1 - t0;
                    float3 p = origen + dir * t;

                    float dens = _Densidad * exp(-max(p.y - _AlturaBase, 0.0) * _CaidaAltura);
                    if (_Ruido > 0.001)
                    {
                        float n = Ruido3(p * _EscalaRuido + _VientoRuido * _Time.y);
                        dens *= lerp(1.0, saturate(n * 1.9 - 0.15), _Ruido);
                    }
                    float trans = exp(-_Extincion * t);
                    float3 suma = 0;

                    // luna (con su sombra: las rocas y la torre recortan la bruma)
                    if (_IntLuna > 0.0)
                    {
                        Light luna = GetMainLight(TransformWorldToShadowCoord(p), p, half4(1, 1, 1, 1));
                        suma += luna.color * luna.shadowAttenuation * Fase(dot(dir, luna.direction), _Anisotropia) * _IntLuna;
                    }

                    inputData.positionWS = p;
                #if USE_CLUSTER_LIGHT_LOOP
                    // otras direccionales (relampago): toda la bruma se enciende en el destello
                    if (_IntDireccionales > 0.0)
                    {
                        for (uint d = 0; d < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); d++)
                        {
                            Light l = GetAdditionalLight(d, p);
                            suma += l.color * _IntDireccionales;
                        }
                    }
                #endif
                    // luces puntuales y focos, con sus sombras
                    if (_IntLocales > 0.0)
                    {
                        uint cuenta = GetAdditionalLightsCount();
                        LIGHT_LOOP_BEGIN(cuenta)
                            Light l = GetAdditionalLight(lightIndex, p, half4(1, 1, 1, 1));
                            float at = min(l.distanceAttenuation, _MaxAtenuacion);
                            suma += l.color * (at * l.shadowAttenuation * Fase(dot(dir, l.direction), _Anisotropia * 0.5) * _IntLocales);
                        LIGHT_LOOP_END
                    }

                    luz += suma * (dens * dt * trans);
                }
                return half4(luz, 1);
            }
            ENDHLSL
        }

        // ------------------------------------------------------------------ 1 y 2: desenfoque que respeta bordes
        Pass
        {
            Name "DesenfoqueH"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            half4 Frag(Varyings i) : SV_Target { return Desenfocar(i.uv, float2(_NieblaTam.x * 1.5, 0)); }
            ENDHLSL
        }

        Pass
        {
            Name "DesenfoqueV"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            half4 Frag(Varyings i) : SV_Target { return Desenfocar(i.uv, float2(0, _NieblaTam.y * 1.5)); }
            ENDHLSL
        }

        // ------------------------------------------------------------------ 3: sumar a la imagen
        Pass
        {
            Name "Componer"
            Blend One One
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            float _Fuerza;

            half4 Frag(Varyings i) : SV_Target
            {
                float2 uv = i.uv;
                float centro = ProfundidadLineal(uv);
                // ampliar desde media resolucion sin que la bruma lejana "manche" los bordes de lo que esta delante:
                // si los 4 vecinos estan a profundidad parecida se interpola; si no, se toma el mas parecido
                float2 f = uv * _NieblaTam.zw - 0.5;
                float2 esquina = (floor(f) + 0.5) * _NieblaTam.xy;
                float mejor = 1e9, peor = 0;
                float2 uvMejor = uv;
                for (int y = 0; y <= 1; y++)
                    for (int x = 0; x <= 1; x++)
                    {
                        float2 uvk = esquina + float2(x, y) * _NieblaTam.xy;
                        float dif = abs(ProfundidadLineal(uvk) - centro);
                        if (dif < mejor) { mejor = dif; uvMejor = uvk; }
                        peor = max(peor, dif);
                    }
                float3 niebla = peor < 0.1 * centro + 0.05
                    ? SAMPLE_TEXTURE2D(_NieblaTex, sampler_LinearClamp, uv).rgb
                    : SAMPLE_TEXTURE2D(_NieblaTex, sampler_PointClamp, uvMejor).rgb;
                return half4(niebla * _Fuerza, 0);
            }
            ENDHLSL
        }
    }
}
