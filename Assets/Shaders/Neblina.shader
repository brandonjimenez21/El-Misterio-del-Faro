// Bruma baja para particulas (URP): sprite suave con mezcla alfa, sin iluminacion ni niebla propia.
Shader "Faro/Neblina"
{
    Properties
    {
        _MainTex ("Textura", 2D) = "white" {}
        _Color ("Color", Color) = (0.55, 0.65, 0.78, 1)
        _Suavizado ("Suavizado contra el suelo (m)", Range(0.1, 12)) = 4
    }
    SubShader
    {
        Tags { "Queue"="Transparent" "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "IgnoreProjector"="True" }
        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off Cull Off
        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            TEXTURE2D(_MainTex); SAMPLER(sampler_MainTex);
            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                half4 _Color;
                float _Suavizado;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; float4 screen : TEXCOORD1; };

            Varyings vert(Attributes IN)
            {
                Varyings OUT;
                OUT.positionCS = TransformObjectToHClip(IN.positionOS.xyz);
                OUT.uv = TRANSFORM_TEX(IN.uv, _MainTex);
                OUT.color = IN.color;
                OUT.screen = ComputeScreenPos(OUT.positionCS);
                return OUT;
            }

            half4 frag(Varyings IN) : SV_Target
            {
                half4 t = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, IN.uv);
                float2 suv = IN.screen.xy / IN.screen.w;
                float escena = LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams);
                float mia = IN.screen.w;
                float fade = saturate((escena - mia) / _Suavizado);
                half a = t.a * IN.color.a * _Color.a * fade;
                return half4(_Color.rgb * IN.color.rgb, a);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
