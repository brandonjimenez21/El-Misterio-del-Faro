// Cielo nocturno para "El Misterio del Faro" (URP): degradado, estrellas, luna con halo, nubes finas y
// horizonte que se funde con el color de la niebla. La luna se coloca en la direccion de _DirLuna
// (la actualiza el script CieloLuna a partir de la luz direccional).
Shader "Faro/CieloNocturno"
{
    Properties
    {
        _ColorZenit ("Color del cenit", Color) = (0.012, 0.022, 0.06, 1)
        _ColorHorizonte ("Color del horizonte", Color) = (0.11, 0.15, 0.21, 1)
        _ColorLuna ("Color de la luna", Color) = (0.85, 0.92, 1.0, 1)
        _DirLuna ("Direccion de la luna", Vector) = (0.5, 0.6, 0.6, 0)
        _TamLuna ("Tamano de la luna (radianes)", Range(0.01, 0.12)) = 0.045
        _BrilloLuna ("Brillo de la luna", Range(0, 6)) = 2.2
        _Estrellas ("Estrellas", Range(0, 3)) = 1.2
        _Nubes ("Nubes", Range(0, 1)) = 0.55
        _VelNubes ("Velocidad de nubes", Range(0, 0.1)) = 0.012
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" "RenderPipeline"="UniversalPipeline" }
        Cull Off ZWrite Off
        Pass
        {
            Name "Cielo"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _ColorZenit, _ColorHorizonte, _ColorLuna;
                float4 _DirLuna;
                float _TamLuna, _BrilloLuna, _Estrellas, _Nubes, _VelNubes;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 dir : TEXCOORD0; };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.dir = IN.positionOS.xyz;
                return OUT;
            }

            float hash13(float3 p)
            {
                p = frac(p * 0.1031);
                p += dot(p, p.zyx + 31.32);
                return frac((p.x + p.y) * p.z);
            }

            float vnoise(float2 p)
            {
                float2 i = floor(p), f = frac(p);
                f = f * f * (3.0 - 2.0 * f);
                float a = hash13(float3(i, 1.0)), b = hash13(float3(i + float2(1, 0), 1.0));
                float c = hash13(float3(i + float2(0, 1), 1.0)), d = hash13(float3(i + float2(1, 1), 1.0));
                return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
            }

            float fbm(float2 p)
            {
                float v = 0, a = 0.5;
                for (int i = 0; i < 5; i++) { v += a * vnoise(p); p = p * 2.03 + 7.1; a *= 0.5; }
                return v;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                float3 d = normalize(IN.dir);
                float3 m = normalize(_DirLuna.xyz);
                float h = d.y;

                // degradado cielo
                half3 col = lerp(_ColorHorizonte.rgb, _ColorZenit.rgb, pow(saturate(h), 0.45));

                // estrellas (celdas 3D con jitter), mas tenues cerca del horizonte
                float3 sp = d * 140.0;
                float3 id = floor(sp);
                float3 f = frac(sp) - 0.5;
                float r = hash13(id);
                float3 off = (float3(hash13(id + 3.1), hash13(id + 7.7), hash13(id + 11.3)) - 0.5) * 0.6;
                float estrella = step(0.9935, r) * smoothstep(0.16, 0.0, length(f - off));
                float parpadeo = 0.7 + 0.3 * sin(_Time.y * (2.0 + r * 5.0) + r * 40.0);
                float fadeH = smoothstep(0.02, 0.35, h);
                col += estrella * parpadeo * fadeH * _Estrellas * lerp(half3(0.8, 0.9, 1.0), half3(1.0, 0.9, 0.75), frac(r * 97.0));

                // nubes finas que se desplazan lentamente (proyeccion plana)
                float2 cp = d.xz / (h + 0.35) * 1.6 + _Time.y * _VelNubes * float2(1.0, 0.4);
                float nube = smoothstep(0.45, 0.85, fbm(cp)) * smoothstep(-0.02, 0.25, h) * _Nubes;

                // luna: disco con manchas, halo
                float cosA = dot(d, m);
                float ang = acos(clamp(cosA, -1.0, 1.0));
                float disco = smoothstep(_TamLuna, _TamLuna * 0.93, ang);
                float3 ex = normalize(cross(m, float3(0, 1, 0)));
                float3 ey = cross(ex, m);
                float2 mp = float2(dot(d, ex), dot(d, ey)) / _TamLuna;
                float manchas = fbm(mp * 3.2 + 4.0);
                half3 lunaCol = _ColorLuna.rgb * (0.78 + 0.35 * manchas) * _BrilloLuna;
                float halo = pow(saturate(cosA), 60.0) * 0.30 + pow(saturate(cosA), 700.0) * 0.5 + pow(saturate(cosA), 8.0) * 0.05;
                half3 haloCol = _ColorLuna.rgb * halo * _BrilloLuna * 0.5;

                // las nubes tapan estrellas y se iluminan junto a la luna
                col *= (1.0 - nube * 0.8);
                half3 nubeCol = lerp(half3(0.035, 0.05, 0.075), _ColorLuna.rgb * 0.5, saturate(pow(saturate(cosA), 6.0)));
                col += nube * nubeCol;
                col += haloCol * (1.0 - nube * 0.7);
                col = lerp(col, lunaCol, disco * (1.0 - nube * 0.85));

                // horizonte hacia el color de la niebla (para que no se note el corte) y mar oscuro abajo
                col = lerp(unity_FogColor.rgb, col, smoothstep(-0.02, 0.22, h));
                col = lerp(col, unity_FogColor.rgb * 0.7, saturate(-h * 6.0));
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
