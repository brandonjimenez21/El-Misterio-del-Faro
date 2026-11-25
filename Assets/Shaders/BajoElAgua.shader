// Lo que queda de un animal (tiburon) BAJO la superficie del oceano. El oceano es opaco, asi que este material se pone como
// segundo material del mismo objeto y dibuja, despues del agua, solo los pixeles que quedan detras de ella:
//   - ZTest Greater: unicamente lo que esta tapado
//   - Stencil = 2: unicamente donde lo que tapa es el agua (Faro/Oceano escribe 2), no una roca ni el muelle
// Se desvanece con la profundidad. Normalmente apenas se entreve; con cada relampago (global _FaroRelampago, de Relampagos.cs)
// se enciende y deja ver el dibujo entero.
Shader "Faro/BajoElAgua"
{
    Properties
    {
        _BaseMap ("Textura", 2D) = "white" {}
        _Tinte ("Tinte bajo el agua", Color) = (0.72, 0.82, 0.95, 1)
        _Visible ("Cuanto se ve sin relampago", Range(0, 1)) = 0.3
        _VisibleRelampago ("Cuanto se ve con relampago", Range(0, 1)) = 0.95
        _Brillo ("Brillo sin relampago", Range(0, 2)) = 0.4
        _BrilloRelampago ("Brillo con relampago", Range(0, 6)) = 3.2
        _Turbidez ("Cuanto se pierde por metro de profundidad", Range(0.02, 2)) = 0.15
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Transparent-5" }
        Pass
        {
            Name "BajoElAgua"
            Tags { "LightMode"="UniversalForward" }
            ZTest Greater
            ZWrite Off
            Cull Back
            Blend SrcAlpha OneMinusSrcAlpha
            Stencil { Ref 2 Comp Equal }
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _Tinte;
                float _Visible, _VisibleRelampago, _Brillo, _BrilloRelampago, _Turbidez;
            CBUFFER_END
            float _FaroRelampago;      // global (Relampagos.cs)
            float _FaroNivelMar;       // global (NadoCosta.cs)

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; float3 positionWS : TEXCOORD1; float fog : TEXCOORD2; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                half3 tex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv).rgb;
                float rayo = saturate(_FaroRelampago);
                float hondo = max(0.0, _FaroNivelMar - i.positionWS.y);
                float a = exp(-hondo * _Turbidez) * lerp(_Visible, _VisibleRelampago, rayo);
                half3 col = tex * _Tinte.rgb * lerp(_Brillo, _BrilloRelampago, rayo);
                col = lerp(MixFog(col, i.fog), col, rayo * 0.7);      // el destello atraviesa la niebla
                return half4(col, saturate(a));
            }
            ENDHLSL
        }
    }
}
