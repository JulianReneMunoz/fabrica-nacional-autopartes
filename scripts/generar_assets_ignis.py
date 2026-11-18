"""Recursos descargables de IGNIS.

- ``--solo-recursos``: plano 2D ilustrativo (matplotlib), publicable. IGNIS no ofrece cotizaciones: el PDF
  de cotización de ejemplo se retiró.
- Sin opciones: mallas de relieve demostrativas (mapa de alturas por luminancia de los mockups de
  data/referencias_mockups/) en data/mallas_demostrativas/. Ambas carpetas están ignoradas por git y fuera
  de web/public: no son un diseño industrial y no se publican.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageFilter


def reconstruir_malla_3d_desde_imagen(
    ruta_imagen: Path,
    resolucion: int = 260,
    escala_ancho: float = 3.6,
    escala_alto: float = 2.4,
    profundidad_max: float = 0.85,
) -> trimesh.Trimesh:
    """Malla de relieve procedural y demostrativa: alturas derivadas de la luminancia de la imagen, cara
    posterior cerrada y colores por vértice tomados de la imagen. No representa un diseño industrial."""
    if ruta_imagen.exists():
        img = Image.open(ruta_imagen).convert("RGB")
        # Si es el mockup completo 16:9 con el chat a la derecha, se recorta el 60 % izquierdo (el visor 3D)
        w, h = img.size
        if w / h > 1.65:
            img = img.crop((int(w * 0.04), int(h * 0.06), int(w * 0.58), int(h * 0.92)))
        img_resized = img.resize((resolucion, resolucion), Image.Resampling.LANCZOS)
        # Mapa de profundidad suavizado a partir de luminancia + canal rojo (llamas/luces sobresalen)
        img_blur = img_resized.filter(ImageFilter.GaussianBlur(radius=2))
        arr_rgb = np.asarray(img_resized, dtype=np.float32) / 255.0
        arr_depth = np.asarray(img_blur, dtype=np.float32) / 255.0
    else:
        # Fallback sintético con patrón de llamas si aún no se ha copiado el archivo .jpg
        x = np.linspace(-1, 1, resolucion)
        y = np.linspace(-1, 1, resolucion)
        xv, yv = np.meshgrid(x, y)
        r = np.exp(-(xv**2 + yv**2) * 1.8)
        g = np.exp(-(xv**2 + yv**2) * 3.2) * 0.45
        b = np.zeros_like(xv) + 0.05
        arr_rgb = np.stack([r, g, b], axis=-1).astype(np.float32)
        arr_depth = arr_rgb.copy()

    # Calcular máscara de silueta (el fondo industrial oscuro tiene baja luminancia en los bordes)
    luminancia = 0.35 * arr_depth[:, :, 0] + 0.45 * arr_depth[:, :, 1] + 0.20 * arr_depth[:, :, 2]
    # Realzar volumen en el centro del chasis/robot
    yy, xx = np.meshgrid(np.linspace(-1, 1, resolucion), np.linspace(-1, 1, resolucion), indexing="ij")
    domo_central = np.clip(1.0 - 0.65 * (xx**2 + yy**2), 0.15, 1.0)
    z_map = (luminancia * 0.75 + domo_central * 0.45) * profundidad_max

    # Grilla de vértices: cara frontal con relieve y cara posterior cerrada
    xs = np.linspace(-escala_ancho / 2, escala_ancho / 2, resolucion)
    ys = np.linspace(escala_alto, 0.0, resolucion)
    grid_x, grid_y = np.meshgrid(xs, ys)

    verts_front = np.column_stack([grid_x.ravel(), grid_y.ravel(), z_map.ravel()])
    verts_back = np.column_stack([grid_x.ravel(), grid_y.ravel(), -z_map.ravel() * 0.35])

    colores_rgba = np.zeros((resolucion * resolucion, 4), dtype=np.uint8)
    colores_rgba[:, :3] = (arr_rgb.reshape(-1, 3) * 255).astype(np.uint8)
    colores_rgba[:, 3] = 255

    # Generar triángulos de la malla de alta densidad
    caras_front = []
    for i in range(resolucion - 1):
        for j in range(resolucion - 1):
            idx = i * resolucion + j
            caras_front.append([idx, idx + resolucion, idx + 1])
            caras_front.append([idx + 1, idx + resolucion, idx + resolucion + 1])

    caras_front_np = np.array(caras_front, dtype=np.int64)
    offset = len(verts_front)
    caras_back_np = caras_front_np[:, ::-1] + offset

    vertices_totales = np.vstack([verts_front, verts_back])
    caras_totales = np.vstack([caras_front_np, caras_back_np])
    colores_totales = np.vstack(
        [colores_rgba, (colores_rgba * np.array([0.4, 0.4, 0.45, 1.0])).astype(np.uint8)]
    )

    malla = trimesh.Trimesh(vertices=vertices_totales, faces=caras_totales, process=True)
    malla.visual.vertex_colors = colores_totales
    return malla


def exportar_mallas_relieve_demostrativas() -> Path:
    """Escribe las mallas de relieve en data/mallas_demostrativas/ (ignorado por git), fuera de web/public:
    derivan de imágenes de referencia y no se publican."""
    raiz = Path(__file__).resolve().parent.parent
    dir_imagenes = raiz / "data" / "referencias_mockups"
    destino = raiz / "data" / "mallas_demostrativas"
    destino.mkdir(parents=True, exist_ok=True)

    print("Generando malla de relieve demostrativa (modo automóvil)...")
    malla_auto = reconstruir_malla_3d_desde_imagen(
        dir_imagenes / "ignis_car_render.jpg", resolucion=240, escala_ancho=3.8, escala_alto=2.2
    )
    print("Generando malla de relieve demostrativa (modo robot)...")
    malla_robot = reconstruir_malla_3d_desde_imagen(
        dir_imagenes / "ignis_robot_render.jpg", resolucion=240, escala_ancho=3.2, escala_alto=3.4
    )

    escena = trimesh.Scene()
    escena.add_geometry(malla_auto, node_name="relieve_auto", geom_name="relieve_auto")
    escena.add_geometry(malla_robot, node_name="relieve_robot", geom_name="relieve_robot")
    (destino / "relieve_demostrativo.glb").write_bytes(escena.export(file_type="glb"))
    malla_auto.export(file_obj=str(destino / "relieve_auto.obj"), file_type="obj")
    malla_robot.export(file_obj=str(destino / "relieve_robot.obj"), file_type="obj")

    total_caras = len(malla_auto.faces) + len(malla_robot.faces)
    print(f"Mallas demostrativas en {destino} ({total_caras:,} triángulos); no se publican.")
    return destino


# --- Plano técnico 2D ilustrativo (PNG) -----------------------------------------------------------
LEYENDA_PLANO = "Plano ilustrativo, no es un diseño de fabricación"
# Ejes del superdeportivo genérico, en milímetros (frente hacia +x).
EJE_TRASERO_MM = 900.0
EJE_DELANTERO_MM = 3600.0
RADIO_RUEDA_MM = 340.0

# Perfil lateral en cuña: punto inicial y tramos cuadráticos (control, destino), en milímetros.
_PERFIL_INICIO = (60.0, 120.0)
_PERFIL_TRAMOS: list[tuple[tuple[float, float], tuple[float, float]]] = [
    ((2200.0, 100.0), (4400.0, 90.0)),  # bajo de carrocería
    ((4520.0, 100.0), (4500.0, 250.0)),  # trompa
    ((4480.0, 360.0), (4380.0, 380.0)),
    ((3600.0, 520.0), (2800.0, 640.0)),  # capó en cuña
    ((2450.0, 1000.0), (2050.0, 1110.0)),  # parabrisas
    ((1600.0, 1180.0), (1200.0, 1020.0)),  # techo
    ((650.0, 880.0), (100.0, 850.0)),  # tapa del motor
    ((0.0, 820.0), (10.0, 600.0)),  # cola
    ((20.0, 200.0), (60.0, 120.0)),
]


def _muestrear_perfil(muestras_por_tramo: int = 40) -> tuple[list[float], list[float]]:
    """Puntos del perfil (curvas de Bézier cuadráticas) para dibujarlo y medir sus cotas reales."""
    xs, ys = [_PERFIL_INICIO[0]], [_PERFIL_INICIO[1]]
    actual = _PERFIL_INICIO
    for (cx, cy), (dx, dy) in _PERFIL_TRAMOS:
        for i in range(1, muestras_por_tramo + 1):
            t = i / muestras_por_tramo
            a, b, c = (1 - t) ** 2, 2 * t * (1 - t), t**2
            xs.append(a * actual[0] + b * cx + c * dx)
            ys.append(a * actual[1] + b * cy + c * dy)
        actual = (dx, dy)
    return xs, ys


def _mm(valor: float) -> str:
    return f"{round(valor / 10) * 10:,.0f}".replace(",", " ")


def generar_plano_2d_png(destino: Path) -> Path:
    """Plano lateral ilustrativo de IGNIS (1600×1000 px) con cotas medidas sobre el propio dibujo."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Arc, Circle, Polygon, Rectangle

    blanco, azul = "#ffffff", "#1b4f9c"
    xs, ys = _muestrear_perfil()
    x_min, x_max, alto = min(xs), max(xs), max(ys)
    largo, entre_ejes = x_max - x_min, EJE_DELANTERO_MM - EJE_TRASERO_MM

    fig = plt.figure(figsize=(16, 10), dpi=100, facecolor=azul)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_facecolor(azul)
    ax.set_xlim(-560, 5040)  # 5600 mm de ancho ↔ 3500 mm de alto: misma proporción 16:10 del lienzo
    ax.set_ylim(-1150, 2350)
    ax.set_aspect("equal")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    ax.set_xticks(range(-500, 5001, 100), minor=True)
    ax.set_yticks(range(-1100, 2301, 100), minor=True)
    ax.set_xticks(range(-500, 5001, 500))
    ax.set_yticks(range(-1000, 2301, 500))
    ax.grid(which="minor", color=blanco, alpha=0.07, linewidth=0.5)
    ax.grid(which="major", color=blanco, alpha=0.16, linewidth=0.8)
    linea = {"color": blanco, "linewidth": 2.2, "solid_capstyle": "round", "solid_joinstyle": "round"}
    fina = {"color": blanco, "linewidth": 1.0}

    # Suelo, carrocería y detalles.
    ax.plot([-300, 4800], [0, 0], color=blanco, linewidth=1.0, linestyle=(0, (8, 6)), alpha=0.7)
    ax.plot(xs, ys, zorder=2, **linea)
    ax.add_patch(
        Polygon(
            [(2700, 700), (2110, 1060), (1600, 1110), (1250, 990), (1200, 760)],
            closed=True,
            fill=False,
            edgecolor=blanco,
            linewidth=1.6,
            zorder=2,
        )
    )
    ax.plot([2700, 2620, 2540], [700, 420, 230], zorder=2, **fina)  # corte de puerta tijera
    ax.plot([1620, 1580, 1620], [980, 520, 230], zorder=2, **fina)
    # Toma de aire lateral entre el corte de puerta y el paso de rueda trasero.
    ax.add_patch(Polygon([(1540, 470), (1360, 520), (1360, 350)], closed=True, fill=False, zorder=2, **fina))
    ax.plot([4180, 4440], [330, 300], zorder=2, color=blanco, linewidth=3.0)  # faro
    ax.plot([4050, 4560], [70, 70], zorder=2, color=blanco, linewidth=2.6)  # splitter
    ax.plot([0, 420], [230, 200], zorder=2, **fina)  # difusor

    # Alerón sobre dos pilares.
    ax.add_patch(
        Polygon([(70, 1080), (540, 1110), (560, 1140), (60, 1125)], closed=True, fill=False, zorder=2, **fina)
    )
    for x in (220, 420):
        ax.plot([x, x + 20], [870, 1095], zorder=2, **fina)

    # Ruedas: el disco tapa la carrocería, con rin de 10 radios y arco de paso de rueda.
    for cx in (EJE_TRASERO_MM, EJE_DELANTERO_MM):
        ax.add_patch(
            Circle((cx, RADIO_RUEDA_MM), RADIO_RUEDA_MM, facecolor=azul, edgecolor=blanco, lw=2.2, zorder=3)
        )
        ax.add_patch(Circle((cx, RADIO_RUEDA_MM), 235, fill=False, edgecolor=blanco, lw=1.2, zorder=4))
        ax.add_patch(Circle((cx, RADIO_RUEDA_MM), 45, fill=False, edgecolor=blanco, lw=1.2, zorder=4))
        for k in range(10):
            ang = k * np.pi / 5
            ax.plot(
                [cx + 50 * np.cos(ang), cx + 230 * np.cos(ang)],
                [RADIO_RUEDA_MM + 50 * np.sin(ang), RADIO_RUEDA_MM + 230 * np.sin(ang)],
                color=blanco,
                linewidth=1.0,
                zorder=4,
            )
        ax.add_patch(
            Arc(
                (cx, RADIO_RUEDA_MM),
                2 * 400,
                2 * 400,
                theta1=8,
                theta2=172,
                edgecolor=blanco,
                lw=1.6,
                zorder=3,
            )
        )
        ax.plot([cx, cx], [-80, RADIO_RUEDA_MM * 2 + 40], color=blanco, lw=0.8, linestyle="-.", alpha=0.8)

    # Cotas.
    def cota_horizontal(x0: float, x1: float, y: float, texto: str) -> None:
        for x in (x0, x1):
            ax.plot([x, x], [y - 60, -40 if y < 0 else y + 60], color=blanco, lw=0.8, alpha=0.8)
        ax.annotate(
            "", xy=(x0, y), xytext=(x1, y), arrowprops={"arrowstyle": "<|-|>", "color": blanco, "lw": 1.2}
        )
        ax.text((x0 + x1) / 2, y - 45, texto, color=blanco, ha="center", va="top", fontsize=15)

    cota_horizontal(EJE_TRASERO_MM, EJE_DELANTERO_MM, -260, f"Distancia entre ejes {_mm(entre_ejes)} mm")
    cota_horizontal(x_min, x_max, -620, f"Largo total {_mm(largo)} mm")
    x_alto = x_max + 260
    ax.plot([1600, x_alto + 60], [alto, alto], color=blanco, lw=0.8, alpha=0.8)
    ax.plot([x_max + 40, x_alto + 60], [0, 0], color=blanco, lw=0.8, alpha=0.8)
    ax.annotate(
        "",
        xy=(x_alto, 0),
        xytext=(x_alto, alto),
        arrowprops={"arrowstyle": "<|-|>", "color": blanco, "lw": 1.2},
    )
    ax.text(
        x_alto + 50,
        alto / 2,
        f"Alto {_mm(alto)} mm",
        color=blanco,
        rotation=90,
        ha="left",
        va="center",
        fontsize=15,
    )
    ax.text(
        2 * RADIO_RUEDA_MM + EJE_DELANTERO_MM - 300,
        RADIO_RUEDA_MM * 2 + 120,
        f"Ø rueda {_mm(2 * RADIO_RUEDA_MM)} mm",
        color=blanco,
        ha="center",
        fontsize=13,
    )

    # Cajetín.
    caja_x, caja_y, caja_w, caja_h = 2700, 1500, 2240, 760
    ax.add_patch(Rectangle((caja_x, caja_y), caja_w, caja_h, fill=False, edgecolor=blanco, lw=1.8))
    for y in (caja_y + 260, caja_y + 500):
        ax.plot([caja_x, caja_x + caja_w], [y, y], color=blanco, lw=1.0)
    ax.text(
        caja_x + 60,
        caja_y + 630,
        "IGNIS — Plano técnico 2D",
        color=blanco,
        fontsize=24,
        weight="bold",
        va="center",
    )
    ax.text(caja_x + 60, caja_y + 380, "Fanalca / TAAML 2026-2S", color=blanco, fontsize=17, va="center")
    ax.text(caja_x + 60, caja_y + 175, LEYENDA_PLANO, color=blanco, fontsize=14, style="italic", va="center")
    ax.text(
        caja_x + 60,
        caja_y + 65,
        "Vista lateral · Cotas en milímetros",
        color=blanco,
        fontsize=12,
        va="center",
    )

    destino.parent.mkdir(parents=True, exist_ok=True)
    # Sin metadatos de software ni de fecha: el archivo es reproducible.
    fig.savefig(destino, dpi=100, facecolor=azul, metadata={"Software": None})
    plt.close(fig)
    return destino


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Genera los recursos descargables de IGNIS.")
    parser.add_argument(
        "--solo-recursos",
        action="store_true",
        help="Genera solo el plano 2D PNG en web/public/assets/ (sin modelos 3D).",
    )
    args = parser.parse_args()
    if args.solo_recursos:
        dir_assets = Path(__file__).resolve().parent.parent / "web" / "public" / "assets"
        print(f"Plano 2D generado: {generar_plano_2d_png(dir_assets / 'blueprint_2d.png')}")
    else:
        exportar_mallas_relieve_demostrativas()
