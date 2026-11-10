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
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _ColorBase, _ColorPunta;
                float _Variacion, _Viento, _VelViento, _DistIni, _DistFin;
            CBUFFER_END

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
                float rafaga = sin(t * 0.7 + pw.x * 0.045 + pw.z * 0.03) * 0.5 + 0.5;
                float oscila = sin(t * 2.3 + pw.x * 0.9 + pw.z * 0.7 + IN.uv.x * 6.28);
                float fuerza = _Viento * h * h * (0.35 + 0.65 * rafaga);
                pw.x += (oscila * 0.6 + 0.8 * rafaga) * fuerza;
                pw.z += cos(t * 1.9 + pw.z * 0.8 + IN.uv.x * 3.0) * 0.4 * fuerza;
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
                half3 base = lerp(_ColorBase.rgb, _ColorPunta.rgb, IN.uv.y);
                half var = lerp(1.0, 0.6 + 0.8 * frac(IN.uv.x * 7.31), _Variacion);
                half3 alb = base * var;
                InputData id = (InputData)0;
                id.positionWS = IN.positionWS;
                id.normalWS = normalize(half3(0, 1, 0));                    // iluminacion suave "de cesped": normal hacia arriba
                id.viewDirectionWS = GetWorldSpaceNormalizeViewDir(IN.positionWS);
                id.shadowCoord = TransformWorldToShadowCoord(IN.positionWS);
                id.fogCoord = InitializeInputDataFog(float4(IN.positionWS, 1.0), IN.fogFactor);
                id.bakedGI = SampleSH(id.normalWS);
                id.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(IN.positionCS);
                id.shadowMask = half4(1, 1, 1, 1);
                SurfaceData sd = (SurfaceData)0;
                sd.albedo = alb;
                sd.smoothness = 0.05;
                sd.occlusion = lerp(0.55, 1.0, IN.uv.y);                    // base mas oscura
                sd.alpha = 1;
                sd.normalTS = half3(0, 0, 1);
                half4 c = UniversalFragmentPBR(id, sd);
                c.rgb = MixFog(c.rgb, id.fogCoord);
                return half4(c.rgb, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
