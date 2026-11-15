// Pasto ligero: hojas sueltas (1 triangulo cada una) que se mecen con el viento, con color de la base a la punta.
// UV0 = (tinte aleatorio, altura de la hoja 0..1). Se ilumina con la luz de la luna y las luces cercanas (como el resto).
// Las hojas se agachan con la distancia para no hacer "saltos" cuando el bloque se oculta.
Shader "Faro/Pasto"
{
    Properties
    {
        _ColorBase ("Color de la base", Color) = (0.015, 0.03, 0.008, 1)
        _ColorPunta ("Color de la punta", Color) = (0.12, 0.17, 0.045, 1)
        _Variacion ("Variacion de tinte", Range(0, 1)) = 0.5
        _Viento ("Fuerza del viento (m)", Range(0, 0.6)) = 0.14
        _VelViento ("Velocidad del viento", Range(0, 5)) = 1.6
        _DistIni ("Empieza a agacharse (m)", Float) = 38
        _DistFin ("Agachado del todo (m)", Float) = 54
        _ColorSeco ("Tinte de pasto seco", Color) = (1.5, 1.15, 0.55, 1)
        _ParchesSecos ("Cantidad de parches secos", Range(0, 1)) = 0.6
        _Translucidez ("Translucidez a contraluz", Range(0, 1.5)) = 0.55
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Cull Off
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
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
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            float _FaroCalma, _FaroRafaga;   // globales (ReaccionViento.cs): 0 = viento normal; calma 1 = todo inmovil
            CBUFFER_START(UnityPerMaterial)
                half4 _ColorBase, _ColorPunta, _ColorSeco;
                float _Variacion, _Viento, _VelViento, _DistIni, _DistFin, _ParchesSecos, _Translucidez;
            CBUFFER_END

            float hash21(float2 p) { p = frac(p * float2(123.34, 456.21)); p += dot(p, p + 45.32); return frac(p.x * p.y); }
            float vnoise(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(hash21(i), hash21(i + float2(1, 0)), f.x), lerp(hash21(i + float2(0, 1)), hash21(i + float2(1, 1)), f.x), f.y);
            }

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                half fogFactor : TEXCOORD2;
            };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 pw = TransformObjectToWorld(IN.positionOS.xyz);
                float h = IN.uv.y;
                float t = _Time.y * _VelViento;
                // oleaje de viento: rafaga larga + temblor corto; mas fuerte cuanto mas arriba de la hoja
                // rafagas que viajan por la isla (ola larga en la direccion del viento) + temblor corto por hoja
                float2 dirV = float2(0.86, 0.5);
                float fase = dot(pw.xz, dirV);
                float rafaga = sin(fase * 0.09 - t * 0.9) * 0.5 + 0.5;
                rafaga = rafaga * rafaga * (3.0 - 2.0 * rafaga);
                rafaga = saturate(rafaga * 0.8 + 0.35 * sin(fase * 0.23 - t * 1.7 + 1.3) * 0.5 + 0.1);
                float oscila = sin(t * 2.3 + pw.x * 0.9 + pw.z * 0.7 + IN.uv.x * 6.28);
                float fuerza = _Viento * (1.0 - _FaroCalma) * (1.0 + _FaroRafaga) * h * h * (0.3 + 0.7 * rafaga);
                float2 empuje = dirV * (0.9 * rafaga + 0.25 * oscila) + float2(-dirV.y, dirV.x) * 0.35 * cos(t * 1.9 + pw.z * 0.8 + IN.uv.x * 3.0);
                pw.xz += empuje * fuerza;
                pw.y -= length(empuje) * fuerza * 0.35;   // al inclinarse la hoja baja un poco la punta
                // agacharse con la distancia
                float d = distance(pw, _WorldSpaceCameraPos);
                float k = 1.0 - smoothstep(_DistIni, _DistFin, d);
                pw.y -= h * 0.5 * (1.0 - k);
                OUT.positionWS = pw;
                OUT.positionCS = TransformWorldToHClip(pw);
                OUT.uv = IN.uv;
                OUT.fogFactor = ComputeFogFactor(OUT.positionCS.z);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 pw = IN.positionWS;
                half3 base = lerp(_ColorBase.rgb, _ColorPunta.rgb, IN.uv.y);
                // parches de pasto seco (decenas de metros) y variacion a media escala (unos 3 m), iguales para todas las hojas de la zona
                half parche = vnoise(pw.xz * 0.055);
                half medio = vnoise(pw.xz * 0.33 + 7.0);
                half seco = smoothstep(1.0 - 0.45 * _ParchesSecos - 0.15, 1.0 - 0.2 * _ParchesSecos, parche);
                base = lerp(base, base * _ColorSeco.rgb, seco * 0.75);
                base *= 0.8 + 0.4 * medio;
                half var = lerp(1.0, 0.6 + 0.8 * frac(IN.uv.x * 7.31), _Variacion);
                half3 alb = base * var;
                InputData id = (InputData)0;
                id.positionWS = pw;
                id.normalWS = normalize(half3(0, 1, 0));                    // iluminacion suave "de cesped": normal hacia arriba
                id.viewDirectionWS = GetWorldSpaceNormalizeViewDir(pw);
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
                sd.smoothness = 0.05;
                sd.occlusion = lerp(0.45, 1.0, pow(IN.uv.y, 0.8));          // base mas oscura
                sd.alpha = 1;
                sd.normalTS = half3(0, 0, 1);
                half4 c = UniversalFragmentPBR(id, sd);
                // translucidez: la luz principal (luna) atraviesa las hojas cuando se mira contra ella
                Light luz = GetMainLight(id.shadowCoord);
                half contra = pow(saturate(dot(id.viewDirectionWS, -luz.direction)), 3.0) * IN.uv.y;
                c.rgb += alb * luz.color * luz.shadowAttenuation * contra * _Translucidez;
                c.rgb = MixFog(c.rgb, id.fogCoord);
                return half4(c.rgb, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
