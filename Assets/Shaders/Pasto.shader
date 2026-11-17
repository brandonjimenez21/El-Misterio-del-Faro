// Pasto: matas de hierba hechas con tarjetas cruzadas y una textura de hojas finas recortada por alfa (T_Pasto_Matas, atlas 2x2).
// La geometria la genera blender/scripts/pasto_y_rocas.py:  UV0 = textura de la mata,  UV1 = (tinte aleatorio de la mata, altura 0..1).
//  - se mece con el viento (rafagas que recorren la isla; mas cuanto mas arriba de la hoja)
//  - volumen: base oscura (dentro de la mata llega poca luz), cada mata recibe la luz un poco distinta, puntas que brillan mojadas
//    con la lluvia y translucidez cuando se mira contra la luna
//  - recibe sombras y la luz de faroles/linterna como el resto (no proyecta sombra: seria caro y de noche no se nota)
//  - con la distancia las matas se hunden en el suelo para no hacer "saltos" cuando el bloque se oculta (PastoDistancia.cs)
// Rendimiento (la hierba era lo mas caro de la escena: cada tarjeta se iluminaba entera aunque quedara tapada por otra):
//  - pasada "Profundidad" (sin LightMode: URP la dibuja antes que ForwardLit): solo recorta por alfa y escribe profundidad
//  - ForwardLit con ZTest Equal: la iluminacion se calcula UNA vez por pixel, solo en la hoja que queda delante
//  - cola Geometry-10: la hierba se dibuja antes que el terreno, que asi no gasta su shader (caro) en lo que la hierba tapa
//  - el ruido de parches secos se calcula por vertice, no por pixel
Shader "Faro/Pasto"
{
    Properties
    {
        _MainTex ("Matas (RGB color, A recorte)", 2D) = "white" {}
        _Corte ("Recorte de alfa", Range(0.05, 0.9)) = 0.35
        _ColorBase ("Tinte en la base", Color) = (0.55, 0.6, 0.5, 1)
        _ColorPunta ("Tinte en la punta", Color) = (1, 1, 1, 1)
        _Brillo ("Brillo general", Range(0, 3)) = 1
        _Variacion ("Variacion de tinte entre matas", Range(0, 1)) = 0.5
        _Viento ("Fuerza del viento (m)", Range(0, 0.6)) = 0.14
        _VelViento ("Velocidad del viento", Range(0, 5)) = 1.6
        _DistIni ("Empieza a hundirse (m)", Float) = 38
        _DistFin ("Hundido del todo (m)", Float) = 54
        _ColorSeco ("Tinte de pasto seco", Color) = (1.5, 1.15, 0.55, 1)
        _ParchesSecos ("Cantidad de parches secos", Range(0, 1)) = 0.6
        _Translucidez ("Translucidez a contraluz", Range(0, 1.5)) = 0.55
        _SombraBase ("Oscuridad en la base", Range(0, 1)) = 0.7
    }
    SubShader
    {
        Tags { "RenderType"="TransparentCutout" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry-10" }
        Cull Off

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

        TEXTURE2D(_MainTex); SAMPLER(sampler_MainTex);
        float _FaroCalma, _FaroRafaga;   // globales (ReaccionViento.cs): 0 = viento normal; calma 1 = todo inmovil
        float _FaroLluvia;               // global (ClimaAgua.cs): fuerza de la lluvia
        float _FaroRecorteHierba;        // global (CalidadAutomatica.cs): 0 = distancia normal; 0.4 = la hierba llega un 40 % menos lejos
        CBUFFER_START(UnityPerMaterial)
            float4 _MainTex_ST;
            half4 _ColorBase, _ColorPunta, _ColorSeco;
            float _Corte, _Brillo, _Variacion, _Viento, _VelViento, _DistIni, _DistFin, _ParchesSecos, _Translucidez, _SombraBase;
        CBUFFER_END

        struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; float2 datos : TEXCOORD1; };

        // posicion en el mundo con viento y hundimiento. La usan las DOS pasadas: tiene que dar exactamente lo mismo en ambas
        // (ForwardLit dibuja con ZTest Equal), por eso va con "precise" y en una sola funcion.
        float3 PosMundo(Attributes IN)
        {
            precise float3 pw = TransformObjectToWorld(IN.positionOS.xyz);
            precise float h = IN.datos.y;
            precise float t = _Time.y * _VelViento;
            // rafagas que viajan por la isla (ola larga en la direccion del viento) + temblor corto por mata
            float2 dirV = float2(0.86, 0.5);
            precise float fase = dot(pw.xz, dirV);
            precise float rafaga = sin(fase * 0.09 - t * 0.9) * 0.5 + 0.5;
            rafaga = rafaga * rafaga * (3.0 - 2.0 * rafaga);
            rafaga = saturate(rafaga * 0.8 + 0.35 * sin(fase * 0.23 - t * 1.7 + 1.3) * 0.5 + 0.1);
            precise float oscila = sin(t * 2.3 + pw.x * 0.9 + pw.z * 0.7 + IN.datos.x * 6.28);
            precise float fuerza = _Viento * (1.0 - _FaroCalma) * (1.0 + _FaroRafaga) * h * (0.3 + 0.7 * rafaga);
            precise float2 empuje = dirV * (0.9 * rafaga + 0.25 * oscila) + float2(-dirV.y, dirV.x) * 0.35 * cos(t * 1.9 + pw.z * 0.8 + IN.datos.x * 3.0);
            pw.xz += empuje * fuerza;
            pw.y -= length(empuje) * fuerza * 0.35;   // al inclinarse la hoja baja un poco la punta
            // hundirse con la distancia
            precise float d = distance(pw, _WorldSpaceCameraPos);
            precise float rec = 1.0 - _FaroRecorteHierba;
            precise float k = 1.0 - smoothstep(_DistIni * rec, _DistFin * rec, d);
            pw.y -= h * 1.3 * (1.0 - k);
            return pw;
        }

        // recorte: alfa de la textura; una tarjeta vista de canto (desde arriba, o de frente en una ladera) se veria como una raya: se desvanece
        half Recorte(float2 uv, float3 pw)
        {
            half a = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, uv).a;
            half3 nTarjeta = normalize(cross(ddx(pw), ddy(pw)));
            half frente = abs(dot(nTarjeta, GetWorldSpaceNormalizeViewDir(pw)));
            return a * smoothstep(0.12, 0.42, frente) - _Corte;
        }
        ENDHLSL

        Pass
        {
            // sin LightMode (= SRPDefaultUnlit): URP la dibuja justo antes que ForwardLit. Solo profundidad.
            Name "Profundidad"
            ZWrite On
            ColorMask 0
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vertP
            #pragma fragment fragP

            struct VaryingsP { precise float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 positionWS : TEXCOORD1; };

            VaryingsP vertP(Attributes IN)
            {
                VaryingsP OUT;
                precise float3 pw = PosMundo(IN);
                OUT.positionWS = pw;
                OUT.positionCS = TransformWorldToHClip(pw);
                OUT.uv = TRANSFORM_TEX(IN.uv, _MainTex);
                return OUT;
            }

            half4 fragP(VaryingsP IN) : SV_Target
            {
                clip(Recorte(IN.uv, IN.positionWS));
                return 0;
            }
            ENDHLSL
        }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            ZWrite Off
            ZTest Equal        // solo el pixel que gano en la pasada de profundidad: nada de iluminar hojas tapadas
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fog
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ProbeVolumeVariants.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            float hash21(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
            float vnoise(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(hash21(i), hash21(i + float2(1, 0)), f.x), lerp(hash21(i + float2(0, 1)), hash21(i + float2(1, 1)), f.x), f.y);
            }

            struct Varyings
            {
                precise float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                half fogFactor : TEXCOORD2;
                half2 datos : TEXCOORD3;      // x = tinte de la mata, y = altura 0..1
                half2 zona : TEXCOORD4;       // x = parche seco (decenas de metros), y = variacion a media escala (unos 3 m)
            };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                precise float3 pw = PosMundo(IN);
                OUT.positionWS = pw;
                OUT.positionCS = TransformWorldToHClip(pw);
                OUT.uv = TRANSFORM_TEX(IN.uv, _MainTex);
                OUT.datos = IN.datos;
                OUT.fogFactor = ComputeFogFactor(OUT.positionCS.z);
                // ruido de zona: cambia tan despacio que basta calcularlo por vertice
                OUT.zona = half2(vnoise(pw.xz * 0.055), vnoise(pw.xz * 0.33 + 7.0));
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                half4 tex = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, IN.uv);
                float3 pw = IN.positionWS;
                half3 vista = GetWorldSpaceNormalizeViewDir(pw);
                half h = IN.datos.y;
                half tinte = IN.datos.x;
                half3 alb = tex.rgb * lerp(_ColorBase.rgb, _ColorPunta.rgb, h) * _Brillo;
                // parches de pasto seco (decenas de metros) y variacion a media escala (unos 3 m), iguales para todas las matas de la zona
                half parche = IN.zona.x;
                half medio = IN.zona.y;
                half seco = smoothstep(1.0 - 0.45 * _ParchesSecos - 0.15, 1.0 - 0.2 * _ParchesSecos, parche);
                alb = lerp(alb, alb * _ColorSeco.rgb, seco * 0.75 * h);
                alb *= 0.8 + 0.4 * medio;
                alb *= lerp(1.0, 0.65 + 0.7 * tinte, _Variacion);
                // lluvia: la hierba mojada es algo mas oscura y sus puntas brillan
                alb *= lerp(1.0, 0.85, _FaroLluvia);

                InputData id = (InputData)0;
                id.positionWS = pw;
                // iluminacion "de cesped": normal hacia arriba, pero cada mata un poco ladeada (asi el prado no recibe una luz uniforme)
                half2 lad = half2(tinte, frac(tinte * 7.31)) - 0.5;
                id.normalWS = normalize(half3(lad.x * 0.7, 1.0, lad.y * 0.7));
                id.viewDirectionWS = vista;
                id.shadowCoord = TransformWorldToShadowCoord(pw);
                id.fogCoord = InitializeInputDataFog(float4(pw, 1.0), IN.fogFactor);
                id.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(IN.positionCS);
                id.shadowMask = half4(1, 1, 1, 1);
                #if defined(PROBE_VOLUMES_L1) || defined(PROBE_VOLUMES_L2)
                    half3 vertexSH = 0;
                    id.bakedGI = SAMPLE_GI(vertexSH, GetAbsolutePositionWS(pw), id.normalWS, id.viewDirectionWS, IN.positionCS.xy, 0, 0);
                #else
                    id.bakedGI = SampleSH(id.normalWS);
                #endif
                SurfaceData sd = (SurfaceData)0;
                sd.albedo = alb;
                sd.smoothness = lerp(0.06, 0.34, _FaroLluvia) * h;
                sd.occlusion = lerp(1.0 - _SombraBase, 1.0, pow(h, 0.7));          // base mas oscura: da profundidad a la mata
                sd.alpha = 1;
                sd.normalTS = half3(0, 0, 1);
                half4 c = UniversalFragmentPBR(id, sd);
                // la luz directa tampoco llega bien a la base de la mata
                c.rgb *= lerp(1.0 - _SombraBase * 0.6, 1.0, smoothstep(0.0, 0.55, h));
                // translucidez: la luz principal (luna) atraviesa las hojas cuando se mira contra ella
                Light luz = GetMainLight(id.shadowCoord);
                half contra = pow(saturate(dot(id.viewDirectionWS, -luz.direction)), 3.0) * h;
                c.rgb += alb * luz.color * luz.shadowAttenuation * contra * _Translucidez;
                c.rgb = MixFog(c.rgb, id.fogCoord);
                return half4(c.rgb, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
