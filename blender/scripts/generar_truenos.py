# Genera 4 truenos sinteticos (restallido seco + retumbo largo) en Assets/Audio/Truenos/Trueno_1..4.wav
# Uso: python generar_truenos.py   (necesita numpy)  -- sustituye por audios reales cuando los tengas.
import numpy as np, wave, os
SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Assets", "Audio", "Truenos")
os.makedirs(OUT, exist_ok=True)

def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s; y[i] = s
    return y

def trueno(seed, dur, crack, rumble_hz):
    r = np.random.default_rng(seed); n = int(SR * dur); t = np.arange(n) / SR
    ruido = r.standard_normal(n)
    # retumbo: ruido grave (dos pasadas) con modulacion lenta irregular (rodamiento) y cola larga
    grave = lowpass(lowpass(ruido, rumble_hz), rumble_hz * 1.3)
    rodar = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * (0.35 + 0.2 * r.random()) * t + r.random() * 6)) * np.abs(np.sin(2 * np.pi * 0.9 * t + r.random() * 6))
    cola = np.exp(-t / (dur * 0.33))
    ataque = np.clip(t / 0.35, 0, 1) ** 1.5
    env = rodar * cola * ataque
    y = grave * env
    y /= np.max(np.abs(y)) + 1e-9
    # restallido inicial (ruido de banda media, muy corto) segun cercania
    nc = int(SR * 0.45); tc = np.arange(nc) / SR
    c = (lowpass(r.standard_normal(nc), 2500) - lowpass(r.standard_normal(nc), 200)) * np.exp(-tc / 0.07)
    c /= np.max(np.abs(c)) + 1e-9
    y[:nc] += crack * c
    # pequenos golpes secundarios
    for k in range(3):
        o = int(SR * r.uniform(0.5, dur * 0.5)); l = int(SR * 0.6)
        if o + l < n:
            g = lowpass(r.standard_normal(l), 180) * np.exp(-np.arange(l) / SR / 0.2); y[o:o + l] += 0.5 * g / (np.max(np.abs(g)) + 1e-9) * cola[o]
    y = np.tanh(1.6 * y) / np.tanh(1.6)
    y /= np.max(np.abs(y)); y *= 0.9
    fade = int(SR * 0.4); y[-fade:] *= np.linspace(1, 0, fade)
    return y

cfg = [(11, 9.0, 0.9, 140), (23, 11.0, 0.35, 110), (37, 7.5, 0.7, 170), (51, 13.0, 0.2, 90)]
for i, (seed, dur, crack, hz) in enumerate(cfg, 1):
    y = trueno(seed, dur, crack, hz)
    st = np.stack([y, np.roll(y, 40) * 0.95], axis=1)       # leve diferencia entre canales
    pcm = (st * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, "Trueno_%d.wav" % i), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print("TRUENO", i, dur, "s")
