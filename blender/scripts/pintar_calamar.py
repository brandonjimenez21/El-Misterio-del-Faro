# Pinta la piel del calamar gigante (las texturas que traia el .blend eran un atlas lila sin enlazar a ningun material).
# Estetica de terror (ver aspecto_estetica_terror.jpg): manto casi negro azulado con manchas de sangre oscura y trazos palidos de lapiz,
# brazos que van de vino oscuro a hueso palido hacia las puntas, y las mazas (tentaculos largos) de hueso en el extremo.
# Se define en el espacio del animal: tentaculos hacia -Y, manto hacia +Y. Lo usa exportar_calamar.py -> Peces/Tex/Calamar_c.png
import numpy as np
import pintar_comun as pc

NEGRO = np.array([0.020, 0.026, 0.040], dtype=np.float32)
VINO = np.array([0.15, 0.030, 0.040], dtype=np.float32)
SANGRE = np.array([0.30, 0.050, 0.055], dtype=np.float32)
HUESO = np.array([0.74, 0.72, 0.66], dtype=np.float32)
TRAZO = np.array([0.46, 0.46, 0.50], dtype=np.float32)


def pintar(me, ruta, tam=2048, semilla=5):
    pos, lleno, co = pc.rasterizar(me, tam)
    P = pos[lleno]
    y0, y1 = co[:, 1].min(), co[:, 1].max()
    u = (P[:, 1] - y0) / (y1 - y0)                    # 0 = punta de los tentaculos .. 1 = punta del manto
    ru = pc.ruido(P, semilla, 1.6)
    ru2 = pc.ruido(P * 2.7, semilla + 3, 1.6)
    ru3 = pc.ruido(P * 0.6, semilla + 9, 1.6)

    # manto (u grande) negro azulado; brazos (u pequeno) vino oscuro
    manto = pc.suave(0.50, 0.62, u)
    col = VINO + (NEGRO - VINO) * manto[:, None]
    # manchas de sangre (cromatoforos): mas en el manto
    mancha = pc.suave(0.60, 0.72, ru + 0.12 * (ru3 - 0.5))
    col += (SANGRE - col) * (mancha * (0.35 + 0.5 * manto))[:, None]
    # puntas palidas: brazos y mazas se blanquean hacia el final (hueso)
    punta = pc.suave(0.20, 0.0, u)
    col += (HUESO - col) * (punta * (0.55 + 0.4 * pc.suave(0.4, 0.7, ru2)))[:, None]
    # trazos palidos de lapiz: crestas finas del ruido, cortadas en tramos
    cresta = 1.0 - pc.suave(0.004, 0.016, np.abs(ru2 - 0.5))
    cortes = pc.suave(0.45, 0.60, ru3)
    col += (TRAZO - col) * (cresta * cortes * 0.85)[:, None]
    # grano
    col *= (0.86 + 0.28 * ru)[:, None]

    salida = pc.guardar(col, lleno, tam, ruta, "Calamar_pintado", NEGRO)
    print("CALAMAR pintado %d px, %.0f %% de la textura usada" % (tam, 100.0 * lleno.mean()), flush=True)
    return salida
