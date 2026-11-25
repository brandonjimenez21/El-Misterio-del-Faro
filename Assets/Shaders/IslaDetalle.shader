// Isla con detalle: usa la textura horneada en Blender (color + normal) y le suma, sin tocar la malla,
//  - roca: detalle "triplanar" (se proyecta por el mundo, sin estirarse en paredes y "dedos") en 3 escalas,
//  - pasto: detalle de hebras proyectado desde arriba en las zonas verdes, en 3 escalas,
//  - variacion de color a gran escala (rompe la repeticion), humedad en la costa y oclusion por el relieve del detalle.
// Con la distancia el detalle NO se apaga: a partir de _DistDetalle se cambia por capas mas grandes (roca x0.21 / x0.8,
// suelo x0.19) que siguen teniendo relieve y contraste vistas de lejos y no dejan ver la repeticion; solo se apaga del todo
// en _DistLejos (ya dentro de la niebla). La escala fina solo cerca de la camara.
// v2: recibe la luz horneada de los Adaptive Probe Volumes (APV), el SSAO, las sombras suaves del pipeline y las reflection probes.
// _Modo = 1 sirve para rocas sueltas (usa _Color en vez de la textura horneada).
// Camino principal (_CaminoDatos = 1, la malla trae la UV3 "Camino" de relieve_terreno.py): la tierra sigue el trazado real
// (no la textura horneada, que la dejaba como una tira de borde recto), a los lados hay una franja de hierba pisada con tierra
// entre medias, y los charcos de lluvia salen en los baches de la malla (varios charcos separados que crecen, no todo el camino).
Shader "Faro/IslaDetalle"
{
    Properties
    {
        _BaseMap ("Color horneado", 2D) = "white" {}
        _BumpMap ("Normal horneado", 2D) = "bump" {}
        _Color ("Color (rocas sueltas)", Color) = (0.2, 0.19, 0.17, 1)
        _DetRoca ("Detalle roca", 2D) = "white" {}
        _DetRocaN ("Detalle roca (normal)", 2D) = "bump" {}
        _DetPasto ("Detalle pasto", 2D) = "white" {}
        _DetPastoN ("Detalle pasto (normal)", 2D) = "bump" {}
        _EscalaRoca ("Escala roca grande (1/m)", Float) = 0.3
        _EscalaRoca2 ("Escala roca media (1/m)", Float) = 1.4
        _EscalaRoca3 ("Escala roca fina (1/m)", Float) = 6.5
        _EscalaPasto ("Escala pasto (1/m)", Float) = 0.9
        _EscalaPasto3 ("Escala pasto fina (1/m)", Float) = 4.2
        _FuerzaColor ("Fuerza del detalle (color)", Range(0, 1.5)) = 0.9
        _FuerzaNormal ("Fuerza del detalle (normal)", Range(0, 2)) = 1.6
        _TerHierba ("Capa hierba (RGB color, A altura)", 2D) = "white" {}
        _TerHierbaN ("Capa hierba (normal)", 2D) = "bump" {}
        _TerTierra ("Capa tierra (RGB color, A altura)", 2D) = "white" {}
        _TerTierraN ("Capa tierra (normal)", 2D) = "bump" {}
        _TerArena ("Capa arena (RGB color, A altura)", 2D) = "white" {}
        _TerArenaN ("Capa arena (normal)", 2D) = "bump" {}
        _EscalaTerreno ("Escala de las capas de terreno (1/m)", Float) = 0.5
        _VientoArbol ("Viento sobre el objeto (m, 0 = quieto)", Range(0, 0.6)) = 0
        _DistDetalle ("Distancia a la que el detalle cercano cambia por el lejano (m)", Float) = 90
        _DistLejos ("Hasta donde llega el detalle lejano (m)", Float) = 420
        _LejosSuelo ("Cuanto se nota la capa lejana del suelo", Range(0, 1)) = 0.7
        _DistFino ("Distancia del detalle fino (m)", Float) = 28
        _VariacionMacro ("Variacion de color a gran escala", Range(0, 1)) = 0.5
        _NivelMar ("Nivel del mar (y)", Float) = -0.7
        _AltoMojado ("Altura de la franja mojada (m)", Float) = 1.1
        _Modo ("0 = isla, 1 = roca suelta", Float) = 0
        _RelieveDatos ("La malla trae datos de relieve en UV2 (relieve_terreno.py)", Float) = 0
        _CaminoDatos ("La malla trae el camino en UV3 (relieve_terreno.py)", Float) = 0
        _SombraHierba ("Suelo oscurecido bajo las matas de hierba", Range(0, 1)) = 0
        _DistHierba ("Hasta donde hay matas de hierba (m)", Float) = 54
        _Debug ("Depuracion de mascaras", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
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
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BLENDING
            #pragma multi_compile_fragment _ _REFLECTION_PROBE_BOX_PROJECTION
            #pragma multi_compile _ _CLUSTER_LIGHT_LOOP
            #pragma multi_compile_fog
            #include_with_pragmas "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ProbeVolumeVariants.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_BumpMap); SAMPLER(sampler_BumpMap);
            TEXTURE2D(_DetRoca); SAMPLER(sampler_DetRoca);
            TEXTURE2D(_DetRocaN); SAMPLER(sampler_DetRocaN);
            TEXTURE2D(_DetPasto); SAMPLER(sampler_DetPasto);
            TEXTURE2D(_DetPastoN); SAMPLER(sampler_DetPastoN);
            TEXTURE2D(_TerHierba); SAMPLER(sampler_TerHierba);
            TEXTURE2D(_TerHierbaN); SAMPLER(sampler_TerHierbaN);
            TEXTURE2D(_TerTierra); SAMPLER(sampler_TerTierra);
            TEXTURE2D(_TerTierraN); SAMPLER(sampler_TerTierraN);
            TEXTURE2D(_TerArena); SAMPLER(sampler_TerArena);
            TEXTURE2D(_TerArenaN); SAMPLER(sampler_TerArenaN);
            float _FaroCalma, _FaroRafaga;   // globales (ReaccionViento.cs)
            float _FaroLluvia, _FaroCharcos;                // globales (ClimaAgua.cs): fuerza de la lluvia y agua acumulada
            float _FaroRecorteHierba;                       // global (CalidadAutomatica.cs): cuanto menos lejos llegan las matas (0 = normal)
            float _FaroRelampago;                           // global (Relampagos.cs)
            float4 _FaroOlaMojado, _FaroOlaMojado2;         // hasta donde mojo la ultima ola grande (ClimaAgua.cs)
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _Color;
                float _EscalaRoca, _EscalaRoca2, _EscalaRoca3, _EscalaPasto, _EscalaPasto3, _FuerzaColor, _FuerzaNormal;
                float _DistDetalle, _DistFino, _VariacionMacro, _NivelMar, _AltoMojado, _Modo, _EscalaTerreno, _Debug, _VientoArbol, _RelieveDatos, _SombraHierba, _DistHierba, _DistLejos, _LejosSuelo, _CaminoDatos;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float4 tangentOS : TANGENT; float2 uv : TEXCOORD0; float2 uv1 : TEXCOORD1; float2 uv2 : TEXCOORD2; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                half3 normalWS : TEXCOORD2;
                half4 tangentWS : TEXCOORD3;
                half fogFactor : TEXCOORD4;
                half4 datos : TEXCOORD5;     // x = pendiente original (antes del relieve), y = cuanto subio/bajo el suelo (0.5 = nada)
                                             // z = camino principal (1 en el eje ... 0 a 6 m), w = baches del camino (0..1)
            };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                float3 pwv = TransformObjectToWorld(IN.positionOS.xyz);
                if (_VientoArbol > 0.0)
                {
                    // arboles / ramas: se mecen mas cuanto mas arriba del pie del objeto
                    float hv = max(pwv.y - unity_ObjectToWorld._m13, 0.0);
                    float tv = _Time.y;
                    float2 dv = float2(0.86, 0.5);
                    float fv = dot(unity_ObjectToWorld._m03_m23, dv);
                    float rv = sin(fv * 0.09 - tv * 0.9) * 0.5 + 0.5;
                    float amp = _VientoArbol * (1.0 - _FaroCalma) * (1.0 + _FaroRafaga) * hv * hv * 0.06 * (0.35 + 0.65 * rv);
                    pwv.xz += dv * amp * (1.0 + 0.3 * sin(tv * 1.7 + hv * 0.8 + fv)) ;
                    pwv.y -= amp * 0.2;
                }
                VertexPositionInputs vp = GetVertexPositionInputs(TransformWorldToObject(pwv));
                VertexNormalInputs vn = GetVertexNormalInputs(IN.normalOS, IN.tangentOS);
                OUT.positionCS = vp.positionCS;
                OUT.positionWS = vp.positionWS;
                OUT.uv = TRANSFORM_TEX(IN.uv, _BaseMap);
                OUT.normalWS = vn.normalWS;
                OUT.tangentWS = half4(vn.tangentWS, IN.tangentOS.w * GetOddNegativeScale());
                OUT.fogFactor = ComputeFogFactor(vp.positionCS.z);
                OUT.datos = half4(IN.uv1, IN.uv2 * _CaminoDatos);
                return OUT;
            }

            // normal de detalle triplanar (mezcla "whiteout") sobre la normal base Nb
            half3 TriNormal(TEXTURE2D_PARAM(tex, smp), float3 p, float scale, half3 Nb, half3 w, half fuerza)
            {
                half3 tx = UnpackNormalScale(SAMPLE_TEXTURE2D(tex, smp, p.zy * scale), fuerza);
                half3 ty = UnpackNormalScale(SAMPLE_TEXTURE2D(tex, smp, p.xz * scale), fuerza);
                half3 tz = UnpackNormalScale(SAMPLE_TEXTURE2D(tex, smp, p.xy * scale), fuerza);
                tx = half3(tx.xy + Nb.zy, abs(tx.z) * Nb.x);
                ty = half3(ty.xy + Nb.xz, abs(ty.z) * Nb.y);
                tz = half3(tz.xy + Nb.xy, abs(tz.z) * Nb.z);
                return normalize(tx.zyx * w.x + ty.xzy * w.y + tz.xyz * w.z);
            }

            // ruido y gotas para los charcos
            float2 Hash22(float2 q)
            {
                float3 p3 = frac(float3(q.xyx) * float3(0.1031, 0.1030, 0.0973));
                p3 += dot(p3, p3.yzx + 33.33);
                return frac((p3.xx + p3.yz) * p3.zy);
            }
            float Ruido(float2 q)
            {
                float2 i = floor(q), f = frac(q);
                f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(Hash22(i).x, Hash22(i + float2(1, 0)).x, f.x), lerp(Hash22(i + float2(0, 1)).x, Hash22(i + float2(1, 1)).x, f.x), f.y);
            }
            float2 Anillos(float2 q, float t)
            {
                float2 r = Hash22(floor(q));
                float2 f = frac(q) - 0.5 - (r - 0.5) * 0.5;
                float fase = frac(t + r.x * 7.0);
                float d = length(f);
                float radio = fase * 0.45;
                float onda = sin((d - radio) * 55.0) * saturate(1.0 - abs(d - radio) * 12.0) * (1.0 - fase) * (1.0 - fase);
                return f / max(d, 1e-3) * onda;
            }
            half3 TriColor(TEXTURE2D_PARAM(tex, smp), float3 p, float scale, half3 w)
            {
                return SAMPLE_TEXTURE2D(tex, smp, p.zy * scale).rgb * w.x
                     + SAMPLE_TEXTURE2D(tex, smp, p.xz * scale).rgb * w.y
                     + SAMPLE_TEXTURE2D(tex, smp, p.xy * scale).rgb * w.z;
            }

            // muestra una capa de terreno dos veces (la segunda girada y a otra escala) y las alterna con un ruido de baja frecuencia:
            // la repeticion deja de verse sin emborronar el detalle
            half4 CapaColor(TEXTURE2D_PARAM(tex, smp), float2 uv, half k)
            {
                float2 uv2 = float2(uv.x * 0.8 - uv.y * 0.6, uv.x * 0.6 + uv.y * 0.8) * 0.53 + 0.31;
                return lerp(SAMPLE_TEXTURE2D(tex, smp, uv), SAMPLE_TEXTURE2D(tex, smp, uv2), k);
            }
            half3 CapaNormal(TEXTURE2D_PARAM(tex, smp), float2 uv, half k, half fuerza)
            {
                float2 uv2 = float2(uv.x * 0.8 - uv.y * 0.6, uv.x * 0.6 + uv.y * 0.8) * 0.53 + 0.31;
                half3 a = UnpackNormalScale(SAMPLE_TEXTURE2D(tex, smp, uv), fuerza);
                half3 b = UnpackNormalScale(SAMPLE_TEXTURE2D(tex, smp, uv2), fuerza);
                return lerp(a, b, k);
            }

            // igual que CapaColor, pero en las pendientes anade las proyecciones laterales (ejes X y Z) para que no se estire
            half4 CapaColorT(TEXTURE2D_PARAM(tex, smp), float3 p, half3 w, float2 uv, half k, float esc)
            {
                half4 c = CapaColor(TEXTURE2D_ARGS(tex, smp), uv, k);
                if (w.y > 0.985) return c;
                half4 sx = SAMPLE_TEXTURE2D(tex, smp, p.zy * esc);
                half4 sz = SAMPLE_TEXTURE2D(tex, smp, p.xy * esc);
                return c * w.y + sx * w.x + sz * w.z;
            }


            half4 frag(Varyings IN) : SV_Target
            {
                float3 pw = IN.positionWS;
                half3 Ng = normalize(IN.normalWS);
                half3 T = normalize(IN.tangentWS.xyz);
                half3 B = cross(Ng, T) * IN.tangentWS.w;
                half4 baseS = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, IN.uv);
                half3 alb = lerp(baseS.rgb, _Color.rgb, _Modo);
                half3 nT = lerp(UnpackNormal(SAMPLE_TEXTURE2D(_BumpMap, sampler_BumpMap, IN.uv)), half3(0, 0, 1), _Modo);
                half3 Nb = normalize(TransformTangentToWorld(nT, half3x3(T, B, Ng)));

                // distancia -> las capas cercanas dejan paso a las lejanas (mas grandes); la escala fina se apaga antes
                float dist = distance(pw, _WorldSpaceCameraPos);
                half lejos = smoothstep(_DistDetalle * 0.4, _DistDetalle, dist);        // 0 = capas cercanas, 1 = capas lejanas
                half fade = 1.0 - smoothstep(_DistLejos * 0.6, _DistLejos, dist);       // el detalle solo desaparece muy lejos
                half fino = 1.0 - smoothstep(_DistFino * 0.5, _DistFino, dist);

                half3 w = pow(abs(Ng), 4.0); w /= (w.x + w.y + w.z + 1e-4);
                // con relieve en la malla, QUE material va en cada sitio se sigue decidiendo con la pendiente original (si no, saldria arena en cada repisa de roca)
                half nyC = lerp(Ng.y, IN.datos.x, _RelieveDatos);
                half hueco = (0.5 - IN.datos.y) * _RelieveDatos;      // > 0 en los hoyos del terreno, < 0 en las lomas
                half llano = smoothstep(0.72, 0.9, Ng.y);
                half3 N = Nb;
                half cavidad = 1.0;
                half suav = 0.12;
                half3 dbg = 0;
                half pasto;      // pasto (isla) o musgo (roca suelta): se usa mas abajo para el tinte seco
                half tipoCharco = 0;   // cuanto junta agua el suelo (camino de tierra mucho, arena algo, hierba poco, roca nada)
                half hS = 1;           // altura del relieve de la capa de suelo (lo bajo se llena antes)
                half caminoM = 0;      // cuanto es camino principal (0..1): ahi los charcos van a los baches de la malla
                if (_Modo > 0.5)
                {
                    // ---------- roca suelta: roca triplanar + musgo en las caras de arriba
                    pasto = llano * 0.35;
                    half3 detC = 1;
                    if (fade > 0.001)
                    {
                        half3 r1 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw, _EscalaRoca, w);
                        half3 r2 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw + 17.3, _EscalaRoca2, w);
                        half3 rocaC = r1 * r2 * 1.9;
                        half3 nr = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw, _EscalaRoca2, Nb, w, _FuerzaNormal * fade);
                        nr = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw + 17.3, _EscalaRoca * 1.7, nr, w, _FuerzaNormal * 0.7 * fade);
                        half3 p1 = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, pw.xz * _EscalaPasto).rgb;
                        half3 p2 = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, pw.xz * _EscalaPasto * 0.23 + 0.37).rgb;
                        half3 pastoC = p1 * p2 * 2.2;
                        half3 tp = UnpackNormalScale(SAMPLE_TEXTURE2D(_DetPastoN, sampler_DetPastoN, pw.xz * _EscalaPasto), _FuerzaNormal * fade);
                        half3 np = normalize(Nb + half3(tp.x, 0, tp.y) * 0.8);
                        if (fino > 0.001)
                        {
                            half3 r3 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw + 41.7, _EscalaRoca3, w);
                            rocaC *= lerp(1.0, r3 * 1.9, fino * 0.65);
                            nr = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw + 41.7, _EscalaRoca3, nr, w, _FuerzaNormal * 0.75 * fino);
                        }
                        detC = lerp(rocaC, pastoC, pasto);
                        N = normalize(lerp(nr, np, pasto));
                        half lum = dot(detC, half3(0.33, 0.34, 0.33));
                        cavidad = lerp(1.0, saturate(lum * 1.25), 0.55 * fade);
                        detC = lerp(1.0, detC, _FuerzaColor * fade);
                        suav = lerp(0.2, 0.1, pasto);
                    }
                    alb *= detC;
                }
                else
                {
                    // ---------- isla: la textura horneada (muy poca resolucion) solo decide QUE material va en cada sitio
                    float2 uvT = pw.xz * _EscalaTerreno;
                    half macroN = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, pw.xz * 0.043 + 0.17).g;   // ruido de baja frecuencia
                    half borde = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, pw.xz * 1.3).g;             // ruido fino: bordes irregulares
                    half kAlt = smoothstep(0.42, 0.58, macroN);          // que muestra de cada capa domina (anti-repeticion)
                    half verde = smoothstep(-0.03, 0.0, baseS.g - baseS.r * 1.1 + (borde - 0.5) * 0.03);   // el camino y la orilla son claramente no verdes
                    half lumB = dot(baseS.rgb, half3(0.3, 0.59, 0.11));
                    half suelo2 = smoothstep(0.5, 0.74, nyC);                    // pendientes suaves/medias tambien son suelo (hierba, tierra, arena)
                    half otro = (1.0 - verde) * suelo2;
                    half wG = verde * suelo2;
                    half wD = otro * smoothstep(0.56 + (borde - 0.5) * 0.12, 0.44, lumB);       // oscuro y calido = camino de tierra
                    half wS = otro - wD;                                                          // claro = arena
                    if (IN.datos.z > 0.001)
                    {
                        // camino principal: dentro de su franja la tierra la pone el trazado (borde ondulado), no la textura horneada
                        half corredor = smoothstep(0.02, 0.2, IN.datos.z);
                        wG += wD * corredor;
                        wD *= 1.0 - corredor;
                        half dC = (1.0 - IN.datos.z) * 6.0 + (borde - 0.5) * 0.45 + (Ruido(pw.xz * 1.9 + 5.3) - 0.5) * 0.55;   // metros al eje, con el borde roto por ruido
                        half nucleo = 1.0 - smoothstep(0.65, 1.35, dC);                  // tierra pisada
                        half franja = 1.0 - smoothstep(1.2, 2.7, dC);                   // hierba pisada: la tierra asoma entre las hebras
                        half pesoC = nucleo + (1.0 - nucleo) * franja * 0.6;
                        half t = wG * pesoC;
                        wD += t;
                        wG -= t;
                        caminoM = franja * suelo2;
                    }
                    dbg = half3(wG, wD, wS);
                    half wR = 1.0 - (wG + wD + wS);                                               // el resto (pendientes) = roca

                    half3 albG = 0, albR = alb; half3 nG = Nb; half3 nR = Nb; half hSuelo = 1; half suelo = 0.12;
                    if (wR < 0.999)
                    {
                        half4 cG = 0, cD = 0, cS = 0;
                        half3 nGt = 0, nDt = 0, nSt = 0;
                        half fN = _FuerzaNormal * fade;
                        // de lejos la capa de 2 m se queda en un color liso: se mezcla la misma capa 5 veces mas grande (girada)
                        float2 uvL = float2(uvT.x * 0.8 + uvT.y * 0.6, uvT.y * 0.8 - uvT.x * 0.6) * 0.19 + 0.43;
                        half kL = lejos * _LejosSuelo * fade;
                        if (wG > 0.002) { cG = CapaColorT(TEXTURE2D_ARGS(_TerHierba, sampler_TerHierba), pw, w, uvT, kAlt, _EscalaTerreno); nGt = CapaNormal(TEXTURE2D_ARGS(_TerHierbaN, sampler_TerHierbaN), uvT, kAlt, fN);
                            if (kL > 0.001) { cG = lerp(cG, SAMPLE_TEXTURE2D(_TerHierba, sampler_TerHierba, uvL), kL); nGt = lerp(nGt, UnpackNormalScale(SAMPLE_TEXTURE2D(_TerHierbaN, sampler_TerHierbaN, uvL), fN * 1.4), kL); } }
                        if (wD > 0.002) { cD = CapaColorT(TEXTURE2D_ARGS(_TerTierra, sampler_TerTierra), pw, w, uvT, kAlt, _EscalaTerreno); nDt = CapaNormal(TEXTURE2D_ARGS(_TerTierraN, sampler_TerTierraN), uvT, kAlt, fN);
                            if (kL > 0.001) { cD = lerp(cD, SAMPLE_TEXTURE2D(_TerTierra, sampler_TerTierra, uvL), kL); nDt = lerp(nDt, UnpackNormalScale(SAMPLE_TEXTURE2D(_TerTierraN, sampler_TerTierraN, uvL), fN * 1.4), kL); } }
                        if (wS > 0.002) { cS = CapaColorT(TEXTURE2D_ARGS(_TerArena, sampler_TerArena), pw, w, uvT, kAlt, _EscalaTerreno); nSt = CapaNormal(TEXTURE2D_ARGS(_TerArenaN, sampler_TerArenaN), uvT, kAlt, fN);
                            if (kL > 0.001) { cS = lerp(cS, SAMPLE_TEXTURE2D(_TerArena, sampler_TerArena, uvL), kL); nSt = lerp(nSt, UnpackNormalScale(SAMPLE_TEXTURE2D(_TerArenaN, sampler_TerArenaN, uvL), fN * 1.4), kL); } }
                        // mezcla por altura: la capa mas "alta" en cada pixel gana y el borde es nitido (grava que asoma entre la hierba...)
                        half3 b = half3(wG, wD, wS);
                        half3 hh = half3(cG.a, cD.a, cS.a) * 0.9 + b;
                        half mh = max(hh.x, max(hh.y, hh.z)) - 0.38;
                        half3 bb = max(hh - mh, 0.0) * step(0.002, b);
                        bb /= (bb.x + bb.y + bb.z + 1e-4);
                        // bajo las matas de hierba (Faro/Pasto) el suelo esta en sombra: se oscurece hasta donde llegan las matas
                        half distMatas = _DistHierba * (1.0 - _FaroRecorteHierba);
                        half bajoMatas = 1.0 - _SombraHierba * (1.0 - smoothstep(distMatas * 0.7, distMatas, dist));
                        albG = cG.rgb * lerp(bajoMatas, 1.0, caminoM * 0.6) * bb.x + cD.rgb * 1.5 * bb.y + cS.rgb * 0.55 * bb.z;
                        nG = nGt * bb.x + nDt * 0.6 * bb.y + nSt * bb.z;
                        hSuelo = cG.a * bb.x + cD.a * bb.y + cS.a * bb.z;
                        suelo = 0.1 * bb.x + lerp(0.2, 0.3, cD.a) * bb.y + 0.2 * bb.z;
                        // tinte suave de la textura horneada (cambios de color a gran escala pintados en Blender)
                        albG *= lerp(1.0, saturate(baseS.rgb / max(lumB, 0.08)), 0.18);
                        // las capas se proyectan desde arriba: la normal se tuerce sobre la normal base
                        nG = normalize(Nb + half3(nG.x, 0, nG.y) * 0.9);
                    }
                    if (wR > 0.001 && fade > 0.001)
                    {
                        // la normal horneada trae grietas grandes "de baldosa": se atenua y el relieve lo ponen las capas de detalle
                        half3 Nroca = normalize(lerp(Ng, Nb, 0.3));
                        half3 rocaC = 1;
                        nR = Nroca;
                        half fNr = _FuerzaNormal * fade;
                        if (lejos < 0.999)
                        {
                            // capas cercanas (tiles de 3.3 m y 0.7 m)
                            half3 r1 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw, _EscalaRoca, w);
                            half3 r2 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw + 17.3, _EscalaRoca2, w);
                            rocaC = r1 * r2 * 1.9;
                            nR = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw, _EscalaRoca2, nR, w, fNr * 2.2 * (1.0 - lejos));
                            nR = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw + 17.3, _EscalaRoca * 1.7, nR, w, fNr * 1.5 * (1.0 - lejos));
                        }
                        if (lejos > 0.001)
                        {
                            // capas lejanas (tiles de 16 m y 4 m): la roca sigue teniendo vetas, bloques y relieve vista desde lejos
                            half3 l1 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw + 7.9, _EscalaRoca * 0.21, w);
                            half3 l2 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw + 23.1, _EscalaRoca * 0.8, w);
                            rocaC = lerp(rocaC, l1 * l2 * 1.9, lejos);
                            nR = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw + 23.1, _EscalaRoca * 0.8, nR, w, fNr * 2.4 * lejos);
                            nR = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw + 7.9, _EscalaRoca * 0.21, nR, w, fNr * 1.8 * lejos);
                        }
                        nR = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw * 0.37 + 5.1, _EscalaRoca2, nR, w, fNr * 1.6);   // relieve grande
                        if (fino > 0.001)
                        {
                            half3 r3 = TriColor(TEXTURE2D_ARGS(_DetRoca, sampler_DetRoca), pw + 41.7, _EscalaRoca3, w);
                            rocaC *= lerp(1.0, r3 * 1.9, fino * 0.65);
                            nR = TriNormal(TEXTURE2D_ARGS(_DetRocaN, sampler_DetRocaN), pw + 41.7, _EscalaRoca3, nR, w, _FuerzaNormal * 0.75 * fino);
                        }
                        half3 suave = SAMPLE_TEXTURE2D_LOD(_BaseMap, sampler_BaseMap, IN.uv, 4.0).rgb;
                        albR = lerp(alb, suave, 0.94) * lerp(1.0, rocaC, _FuerzaColor * fade);
                        // estratos horizontales irregulares, chorreras verticales oscuras, liquen en las caras que miran arriba y humedad cerca del mar
                        half estr = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, float2(pw.x * 0.05 + pw.z * 0.05, pw.y * 0.55)).g;
                        albR *= 0.8 + 0.4 * estr;
                        half chorro = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, float2((pw.x + pw.z) * 0.9, pw.y * 0.06)).g;
                        albR *= lerp(1.0, 0.62, smoothstep(0.55, 0.8, chorro) * (1.0 - llano) * 0.8);
                        half liq = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, pw.xz * 0.21 + pw.y * 0.1).g;
                        half liqM = smoothstep(0.5, 0.75, liq) * smoothstep(0.25, 0.6, Ng.y) * (1.0 - llano);
                        albR = lerp(albR, albR * half3(0.55, 0.85, 0.5) + half3(0.0, 0.012, 0.0), liqM * 0.85);
                        albR *= lerp(0.6, 1.0, smoothstep(_NivelMar, _NivelMar + 3.0, pw.y));
                        half lum = dot(rocaC, half3(0.33, 0.34, 0.33));
                        cavidad = lerp(1.0, saturate(lum * 1.45), 0.8 * fade);
                    }
                    alb = albR * wR + albG * (1.0 - wR);
                    N = normalize(nR * wR + nG * (1.0 - wR));
                    cavidad *= lerp(1.0, lerp(0.55, 1.0, hSuelo), (1.0 - wR));
                    cavidad *= saturate(1.0 - hueco * 0.7 * (1.0 - wR));       // los hoyos del terreno reciben menos luz del cielo
                    suav = lerp(suelo, 0.2, wR);
                    pasto = wG;
                    tipoCharco = wD * 1.0 + wS * 0.75 + wG * 0.45;
                    hS = hSuelo;
                }

                // variacion de color a gran escala (decenas de metros): manchas de roca mas clara/oscura y pasto mas seco o mas verde
                if (_Modo < 0.5)
                {
                    half mac = SAMPLE_TEXTURE2D(_DetPasto, sampler_DetPasto, pw.xz * 0.021 + 0.5).g;
                    half mac2 = SAMPLE_TEXTURE2D(_DetRoca, sampler_DetRoca, pw.xz * 0.047 + 0.2).g;
                    half claro = lerp(0.82, 1.2, smoothstep(0.25, 0.75, mac));
                    alb *= lerp(1.0, claro, _VariacionMacro);
                    half seco = smoothstep(0.55, 0.8, mac2) * pasto * _VariacionMacro;
                    alb = lerp(alb, alb * half3(1.22, 1.06, 0.72), seco * 0.7);
                }

                // ---------- lluvia: todo esta mojado (mas oscuro y con brillo; la roca mas que la hierba)
                half humedad = saturate(_FaroLluvia * 0.6 + _FaroCharcos * 0.6);
                half poroso = lerp(1.0, 0.45, pasto);
                alb *= lerp(1.0, 0.78, humedad * poroso);
                suav = lerp(suav, max(suav, lerp(lerp(0.4, 0.3, caminoM), 0.22, pasto)), humedad);

                // ---------- charcos: en lo llano y en los huecos se junta el agua; crecen mientras llueve (_FaroCharcos)
                half3 dbgCharco = 0;
                half charcoF = 0;
                half3 Nagua = half3(0, 1, 0);
                if (_FaroCharcos > 0.001 && tipoCharco > 0.01)
                {
                    half plano = smoothstep(0.93, 0.985, lerp(Ng.y, max(nyC, Ng.y), _RelieveDatos));
                    dbgCharco.b = plano;
                    // profundidad del hueco: ruido de dos escalas (charcos grandes y pequenos) + relieve de la capa de suelo
                    half hondo = 1.0 - (Ruido(pw.xz * 0.33 + 3.7) * 0.55 + Ruido(pw.xz * 0.95 + 9.1) * 0.3 + Ruido(pw.xz * 2.6 + 1.3) * 0.15);
                    hondo += (0.5 - hS) * 0.3;      // las piedras y matas mas altas asoman dentro del charco
                    hondo += hueco * 0.9;           // el agua se junta en los hoyos del terreno y deja secas las lomas
                    if (caminoM > 0.001)
                    {
                        // camino principal: el agua va a los baches de la malla (IN.datos.w), primero al fondo; las piedras asoman
                        half hondoC = 0.40 + IN.datos.w * 0.52 + (0.5 - hS) * 0.22 + (Ruido(pw.xz * 2.6 + 1.3) - 0.5) * 0.1;
                        hondo = lerp(hondo, hondoC, caminoM);
                    }
                    half umbral = 1.0 - _FaroCharcos * 0.4 * tipoCharco * plano;
                    half charco = smoothstep(umbral, umbral + 0.025, hondo) * plano;
                    half barro = smoothstep(umbral - lerp(0.07, 0.16, caminoM), umbral, hondo) * plano;   // borde embarrado alrededor
                    dbgCharco.rg = half2(charco, barro);
                    alb *= lerp(1.0, 0.62, barro);
                    suav = lerp(suav, lerp(0.8, 0.6, caminoM), barro);
                    if (charco > 0.001)
                    {
                        // agua: casi negra, espejo, plana con anillos de gotas
                        float tg = _Time.y * 1.1;
                        float2 g = Anillos(pw.xz * 4.5, tg) + Anillos(pw.xz * 6.2 + 17.3, tg * 1.13 + 0.5) * 0.7;
                        Nagua = normalize(half3(g.x * 0.35 * _FaroLluvia, 1.0, g.y * 0.35 * _FaroLluvia));
                        charcoF = charco;
                        alb = lerp(alb, alb * 0.25 + half3(0.004, 0.005, 0.006), charco);
                        suav = lerp(suav, 0.97, charco);
                        N = normalize(lerp(N, Nagua, charco));
                        cavidad = lerp(cavidad, 1.0, charco);
                    }
                }

                // franja mojada junto al agua: mas oscura y brillante; la ultima ola grande la sube por donde paso
                half altoOla = 0;
                if (_FaroOlaMojado2.x > 0.01)
                {
                    float xp = dot(_FaroOlaMojado.xy, pw.xz);
                    float lt = (dot(float2(-_FaroOlaMojado.y, _FaroOlaMojado.x), pw.xz) - _FaroOlaMojado.w) / _FaroOlaMojado2.y;
                    altoOla = _FaroOlaMojado2.x * exp(-lt * lt) * (1.0 - saturate((xp - _FaroOlaMojado.z) / _FaroOlaMojado2.w)) * step(xp, _FaroOlaMojado2.z);
                    altoOla *= 0.85 + 0.3 * Ruido(pw.xz * 0.8);      // borde irregular
                }
                half mojado = 1.0 - smoothstep(0.0, _AltoMojado + altoOla * 1.15, pw.y - _NivelMar);
                alb *= lerp(1.0, 0.58, mojado);
                suav = lerp(suav, 0.72, mojado);

                InputData id = (InputData)0;
                id.positionWS = pw;
                id.normalWS = NormalizeNormalPerPixel(N);
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
                sd.metallic = 0;
                sd.smoothness = suav;
                sd.occlusion = cavidad;
                sd.alpha = 1;
                sd.normalTS = half3(0, 0, 1);
                half4 c = UniversalFragmentPBR(id, sd);
                if (charcoF > 0.001)
                {
                    // el charco es un espejo: refleja el cielo nocturno con Fresnel (mas cuanto mas rasante se mira)
                    half3 Rw = reflect(-id.viewDirectionWS, Nagua);
                    half fresW = 0.04 + 0.96 * pow(1.0 - saturate(dot(Nagua, id.viewDirectionWS)), 5.0);
                    half3 cielo = GlossyEnvironmentReflection(Rw, pw, 0.03h, 1.0h, id.normalizedScreenSpaceUV);
                    c.rgb += cielo * fresW * charcoF * 1.2;
                    c.rgb += half3(0.5, 0.56, 0.75) * _FaroRelampago * (0.1 + fresW) * charcoF;   // destello del relampago
                }
                c.rgb = MixFog(c.rgb, id.fogCoord);
                if (_Debug > 3.5) return half4(IN.datos.z, IN.datos.w, caminoM, 1);
                if (_Debug > 2.5) return half4(dbgCharco, 1);
                if (_Debug > 1.5) return half4(alb, 1);
                if (_Debug > 0.5) return half4(dbg, 1);
                return half4(c.rgb, 1);
            }
            ENDHLSL
        }
        UsePass "Universal Render Pipeline/Lit/ShadowCaster"
        UsePass "Universal Render Pipeline/Lit/DepthOnly"
        UsePass "Universal Render Pipeline/Lit/DepthNormals"
    }
    FallBack Off
}
