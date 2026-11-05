"""Generación procedural de geometría y exportación glTF binario (GLB) + manifiesto.

Herramienta elegida: ``trimesh`` + ``manifold3d`` (booleanas robustas). Justificación frente a
las alternativas evaluadas (prompt maestro v2, Parte VIII, §34):

* Blender por CLI: excelente para render, pero no se instala con ``uv`` y añade ~300 MB.
* CadQuery/FreeCAD: B-Rep paramétrico real, pero dependencias nativas pesadas (OCP) y
  frágiles en Windows sin Conda (Conda está excluido del proyecto).
* trimesh + manifold3d: ruedas binarias para Windows/Linux, se instala con ``uv``, exporta GLB
  directamente y produce mallas cerradas verificables (volumen, estanqueidad).

Uso: ``uv run fabrica simulador generar`` (o ``--salida <carpeta>``).
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import cast

import numpy as np
import trimesh

from fabrica_autopartes.core.registro import obtener_registro
from fabrica_autopartes.simulador.catalogo_freno import ParametrosFreno, construir_freno
from fabrica_autopartes.simulador.catalogo_moto_honda import construir_moto
from fabrica_autopartes.simulador.cinematica import (
    ErrorEnsamblaje,
    homogenea,
    matriz_rotacion_euler,
    validar_ensamblaje,
)
from fabrica_autopartes.simulador.modelos import Ensamblaje, Pieza
from fabrica_autopartes.simulador.primitivas_moto import (
    engranaje,
    extrusion,
    leer_puntos,
    revolucion,
    rin_rayos,
    tubo,
)

log = obtener_registro(__name__)

COLORES = {  # RGBA 0-255, solo para identificar materiales en visores genéricos
    "cubo": (120, 124, 130, 255),
    "disco": (150, 152, 156, 255),
    "esparrago": (90, 92, 96, 255),
    "soporte": (70, 74, 80, 255),
    "pinza": (200, 40, 46, 255),
    "piston": (210, 212, 216, 255),
    "pastilla": (60, 52, 46, 255),
    "pasador": (180, 182, 186, 255),
    "tornillo": (40, 42, 46, 255),
    # Motocicleta de referencia genérica (colores neutros, sin identidad de marca)
    "cilindro_motor": (176, 180, 186, 255),
    "biela": (160, 164, 170, 255),
    "ciguenal": (110, 114, 120, 255),
    "valvula": (196, 198, 202, 255),
    "bujia": (230, 226, 214, 255),
    "carcasa": (96, 100, 108, 255),
    "engranaje": (140, 144, 150, 255),
    "cadena": (52, 54, 58, 255),
    "estructura": (46, 50, 58, 255),
    "tanque": (176, 52, 48, 255),
    "sillin": (34, 34, 38, 255),
    "tubo_suspension": (188, 190, 196, 255),
    "botella": (120, 124, 132, 255),
    "amortiguador": (214, 168, 40, 255),
    "basculante": (70, 74, 82, 255),
    "rin": (150, 154, 160, 255),
    "llanta": (26, 26, 28, 255),
    "unidad_hidraulica": (84, 88, 96, 255),
    "luz": (236, 232, 200, 255),
    "instrumento": (40, 44, 52, 255),
    "escape": (130, 126, 120, 255),
}
_MATE = frozenset({"llanta", "sillin", "tanque", "estructura"})


def _diferencia(a: trimesh.Trimesh, b: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.difference([a, b], engine="manifold")


def _union(*mallas: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.union(list(mallas), engine="manifold")


def _prisma_trapecio(
    c_a: tuple[float, float], r_a: float, c_b: tuple[float, float], r_b: float, altura: float
) -> trimesh.Trimesh:
    """Prisma recto sobre el trapecio tangente a dos circunferencias (ejes alineados en X)."""
    d = c_a[0] - c_b[0]
    nx = (r_b - r_a) / d
    ny = math.sqrt(1.0 - nx * nx)
    cuadro = [
        (c_a[0] + r_a * nx, c_a[1] + r_a * ny),
        (c_b[0] + r_b * nx, c_b[1] + r_b * ny),
        (c_b[0] + r_b * nx, c_b[1] - r_b * ny),
        (c_a[0] + r_a * nx, c_a[1] - r_a * ny),
    ]
    h = altura / 2
    v = [(x, y, -h) for x, y in cuadro] + [(x, y, h) for x, y in cuadro]
    caras = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7)]
    for i in range(4):
        j = (i + 1) % 4
        caras += [(i, j, j + 4), (i, j + 4, i + 4)]
    m = trimesh.Trimesh(vertices=np.array(v), faces=np.array(caras), process=True)
    if m.volume < 0:
        m.invert()
    return m


def _cadena(q: dict[str, float]) -> trimesh.Trimesh:
    """Lazo de cadena: contorno de dos circunferencias unidas por tangentes, con hueco interior."""
    d, ra, rb, g, ancho = q["distancia"], q["radio_pinon"], q["radio_corona"], q["grosor"], q["ancho"]

    def contorno(r1: float, r2: float, h: float) -> trimesh.Trimesh:
        a = trimesh.creation.cylinder(radius=r1, height=h, sections=48)
        a.apply_translation((d / 2, 0, 0))
        b = trimesh.creation.cylinder(radius=r2, height=h, sections=48)
        b.apply_translation((-d / 2, 0, 0))
        return _union(a, b, _prisma_trapecio((d / 2, 0.0), r1, (-d / 2, 0.0), r2, h))

    return _diferencia(contorno(ra, rb, ancho), contorno(ra - g, rb - g, ancho * 1.5))


def construir_malla(pieza: Pieza) -> trimesh.Trimesh:
    g = pieza.geometria
    q = g.parametros
    if g.primitiva == "cilindro":
        m = trimesh.creation.cylinder(radius=q["radio"], height=q["largo"], sections=48)
    elif g.primitiva == "caja":
        m = trimesh.creation.box(extents=(q["ancho"], q["alto"], q["largo"]))
    elif g.primitiva == "cubo":
        cuerpo = trimesh.creation.cylinder(radius=q["radio"], height=q["largo"], sections=64)
        brida = trimesh.creation.cylinder(radius=q["radio_brida"], height=q["espesor_brida"], sections=64)
        brida.apply_translation((0, 0, q["largo"] / 2 - q["espesor_brida"] / 2))
        m = _union(cuerpo, brida)
    elif g.primitiva == "disco_ventilado":
        m = trimesh.creation.annulus(
            r_min=q["radio_interior"], r_max=q["radio_exterior"], height=q["espesor"], sections=96
        )
        n = int(q["n_agujeros"])
        agujeros = []
        for i in range(n):
            a = 2 * math.pi * i / n
            c = trimesh.creation.cylinder(radius=q["radio_agujeros"], height=q["espesor"] * 1.5, sections=16)
            c.apply_translation(
                (q["radio_circulo_agujeros"] * math.cos(a), q["radio_circulo_agujeros"] * math.sin(a), 0)
            )
            agujeros.append(c)
        m = _diferencia(m, cast(trimesh.Trimesh, trimesh.util.concatenate(agujeros)))
    elif g.primitiva == "pinza":
        z_min = -(q["ranura_largo"] / 2 + q["largo_interior"])
        z_max = q["ranura_largo"] / 2 + q["largo_exterior"]
        cuerpo = trimesh.creation.box(extents=(q["ancho"], q["alto"], z_max - z_min))
        cuerpo.apply_translation((0, 0, (z_max + z_min) / 2))
        ranura = trimesh.creation.box(extents=(q["ancho"] * 1.2, q["ranura_alto"] + 0.002, q["ranura_largo"]))
        ranura.apply_translation((0, -q["alto"] / 2 + q["ranura_alto"] / 2 - 0.001, 0))
        cilindro = trimesh.creation.cylinder(
            radius=q["radio_cilindro"], height=q["largo_interior"] - 0.006, sections=48
        )
        cilindro.apply_translation(
            (0, -0.008, -(q["ranura_largo"] / 2 + (q["largo_interior"] - 0.006) / 2) + 0.0005)
        )
        m = _diferencia(_diferencia(cuerpo, ranura), cilindro)
    elif g.primitiva == "tornillo":
        vastago = trimesh.creation.cylinder(radius=q["radio"], height=q["largo"], sections=24)
        cabeza = trimesh.creation.cylinder(radius=q["radio_cabeza"], height=q["alto_cabeza"], sections=6)
        cabeza.apply_translation((0, 0, -q["largo"] / 2 - q["alto_cabeza"] / 2 + 0.0005))
        m = _union(vastago, cabeza)
    elif g.primitiva == "anillo":
        m = trimesh.creation.annulus(
            r_min=q["radio_interior"], r_max=q["radio_exterior"], height=q["espesor"]
        )
    elif g.primitiva == "toro":
        m = trimesh.creation.torus(
            major_radius=q["radio_mayor"], minor_radius=q["radio_menor"], major_sections=96, minor_sections=24
        )
    elif g.primitiva == "elipsoide":
        m = trimesh.creation.icosphere(subdivisions=3, radius=1.0)
        m.apply_scale([q["radio_x"], q["radio_y"], q["radio_z"]])
    elif g.primitiva == "manivela":
        eje = trimesh.creation.cylinder(radius=q["radio_eje"], height=q["largo_eje"], sections=32)
        muneca = trimesh.creation.cylinder(radius=q["radio_muneca"], height=q["largo_muneca"], sections=32)
        muneca.apply_translation((0, q["excentricidad"], 0))
        z_brazo = q["largo_muneca"] / 2 + q["espesor_brazo"] / 2
        brazos = []
        for signo in (-1, 1):
            b = trimesh.creation.cylinder(radius=q["radio_brazo"], height=q["espesor_brazo"], sections=48)
            b.apply_translation((0, 0, signo * z_brazo))
            brazos.append(b)
        m = _union(eje, muneca, *brazos)
    elif g.primitiva == "cadena":
        m = _cadena(q)
    elif g.primitiva == "cilindro_corte":
        tubo_motor = trimesh.creation.annulus(
            r_min=q["radio_interior"], r_max=q["radio_exterior"], height=q["largo"], sections=64
        )
        n_aletas = int(q.get("n_aletas", 0))
        r_max = q["radio_exterior"]
        if n_aletas:  # aletas de refrigeración repartidas a lo largo del eje
            r_max = q["radio_aleta"]
            partes = [tubo_motor]
            paso = (q["largo"] - q.get("tapa", 0.0) - q["alto_aleta"] - 0.004) / max(n_aletas - 1, 1)
            for i in range(n_aletas):
                aleta = trimesh.creation.annulus(
                    r_min=q["radio_exterior"] - 0.002, r_max=r_max, height=q["alto_aleta"], sections=64
                )
                aleta.apply_translation((0, 0, -q["largo"] / 2 + q["alto_aleta"] / 2 + 0.002 + i * paso))
                partes.append(aleta)
            tubo_motor = _union(*partes)
        if q.get("tapa", 0.0) > 0:  # techo cerrado (culata)
            techo = trimesh.creation.cylinder(radius=q["radio_exterior"], height=q["tapa"], sections=64)
            techo.apply_translation((0, 0, q["largo"] / 2 - q["tapa"] / 2))
            tubo_motor = _union(tubo_motor, techo)
        mitad = trimesh.creation.box(extents=(r_max * 4, r_max * 2, q["largo"] * 2))
        mitad.apply_translation((0, r_max, 0))
        m = _diferencia(tubo_motor, mitad)
    elif g.primitiva == "revolucion":
        m = revolucion(
            leer_puntos(q, ("r", "z")),
            secciones=int(q.get("n_secciones", 48)),
            cerrado=bool(q.get("n_cerrado", 0)),
        )
    elif g.primitiva == "tubo":
        m = tubo(
            leer_puntos(q, ("x", "y", "z")),
            q["radio"],
            secciones=int(q.get("n_secciones", 12)),
            suavizado=int(q.get("n_suavizado", 2)),
        )
    elif g.primitiva == "extrusion":
        m = extrusion(leer_puntos(q, ("x", "y")), q["espesor"])
    elif g.primitiva == "engranaje":
        m = engranaje(
            int(q["n_dientes"]),
            q["radio_punta"],
            q["radio_raiz"],
            q["espesor"],
            q["radio_agujero"],
            int(q.get("n_aligeramientos", 0)),
            q.get("radio_aligeramiento", 0.0),
            q.get("radio_circulo_aligeramiento", 0.0),
        )
    elif g.primitiva == "rin_rayos":
        m = rin_rayos(
            q["radio_exterior"],
            q["ancho"],
            int(q["n_rayos"]),
            q["radio_cubo"],
            q["ancho_rayo"],
            q["espesor_rayo"],
            q["radio_agujero"],
        )
    else:  # pragma: no cover - el modelo Pydantic restringe las primitivas
        raise ErrorEnsamblaje(f"Primitiva no soportada: {g.primitiva}")
    material = trimesh.visual.material.PBRMaterial(
        name=f"mat_{pieza.tipo}",
        baseColorFactor=COLORES.get(pieza.tipo, (128, 128, 128, 255)),
        metallicFactor=(0.2 if pieza.tipo in ("pastilla", "pinza") else 0.05 if pieza.tipo in _MATE else 0.6),
        roughnessFactor=0.45,
    )
    m.visual = trimesh.visual.TextureVisuals(material=material)
    m.metadata["name"] = pieza.id
    return m


def construir_escena(ens: Ensamblaje) -> tuple[trimesh.Scene, dict[str, trimesh.Trimesh]]:
    errores = validar_ensamblaje(ens)
    if errores:
        raise ErrorEnsamblaje("; ".join(errores))
    escena = trimesh.Scene()
    mallas: dict[str, trimesh.Trimesh] = {}
    for p in ens.piezas:
        malla = construir_malla(p)
        if not malla.is_watertight:
            raise ErrorEnsamblaje(f"La malla de '{p.id}' no es cerrada (watertight)")
        mallas[p.id] = malla
        t = homogenea(matriz_rotacion_euler(p.transformacion.rotacion_grados), p.transformacion.posicion)
        escena.add_geometry(malla, node_name=p.geometria.nodo_glb, geom_name=p.id, transform=t)
    return escena, mallas


def mallas_en_posicion_armada(
    ens: Ensamblaje, mallas: dict[str, trimesh.Trimesh]
) -> dict[str, trimesh.Trimesh]:
    """Copias de las mallas con la transformación base de cada pieza aplicada (posición armada)."""
    salida: dict[str, trimesh.Trimesh] = {}
    for p in ens.piezas:
        c = mallas[p.id].copy()
        c.apply_transform(
            homogenea(matriz_rotacion_euler(p.transformacion.rotacion_grados), p.transformacion.posicion)
        )
        salida[p.id] = c
    return salida


def distancia_minima_mallas(
    a: trimesh.Trimesh, b: trimesh.Trimesh, tolerancia_m: float = 0.002, maximo_puntos: int = 6000
) -> float:
    """Distancia mínima entre las superficies de dos mallas (0 si se solapan).

    Se muestrean puntos de superficie (semilla fija) y vértices de ambas mallas, se descartan los
    que quedan fuera de la caja envolvente de la otra ampliada, y se calcula la distancia mínima
    entre los restantes con numpy (sin scipy). Si no se detecta cercanía, se comprueba el solape
    por volumen (intersección booleana), que cubre las piezas incrustadas una dentro de otra.
    """
    holgura = tolerancia_m + 0.02
    lo_a, hi_a = a.bounds
    lo_b, hi_b = b.bounds
    hueco = np.maximum(0.0, np.maximum(lo_a - hi_b, lo_b - hi_a))
    cota = float(np.linalg.norm(hueco))
    if cota > holgura:
        return cota

    def puntos(m: trimesh.Trimesh, otra: trimesh.Trimesh) -> np.ndarray:
        n = int(np.clip(m.area / (0.0015**2), 500, maximo_puntos))
        muestra = trimesh.sample.sample_surface(m, n, seed=7)[0]
        todos = np.vstack([muestra, m.vertices])
        lo, hi = otra.bounds
        dentro = np.all((todos >= lo - holgura) & (todos <= hi + holgura), axis=1)
        return cast(np.ndarray, todos[dentro])

    pa, pb = puntos(a, b), puntos(b, a)
    minimo = np.inf
    if len(pa) and len(pb):
        pb32 = pb.astype(np.float32)
        for i in range(0, len(pa), 800):
            bloque = pa[i : i + 800].astype(np.float32)
            d2 = ((bloque[:, None, :] - pb32[None, :, :]) ** 2).sum(axis=2)
            minimo = min(minimo, float(d2.min()))
        minimo = math.sqrt(minimo)
    if minimo <= tolerancia_m:
        return minimo
    try:
        inter = trimesh.boolean.intersection([a, b], engine="manifold")
        if len(inter.faces) and abs(float(inter.volume)) > 1e-12:
            return 0.0
    except Exception:
        pass
    return float(max(minimo, cota)) if np.isfinite(minimo) else cota


def verificar_conectividad(
    ens: Ensamblaje, mallas: dict[str, trimesh.Trimesh] | None = None, tolerancia_m: float = 0.002
) -> list[str]:
    """Comprueba que cada pieza toque (o se solape con) la pieza en la que se monta.

    Cada pieza declara su montaje en ``metadatos["montada_en"]``. Un ensamblaje que no declara
    ningún montaje (p. ej. el freno de disco) no se comprueba y devuelve una lista vacía. En uno
    que sí los declara, todas las piezas salvo una (la raíz) deben declararlo, el árbol de montaje
    no puede tener ciclos y la distancia mínima entre cada par debe ser ≤ ``tolerancia_m``.
    """
    montajes = {p.id: p.metadatos["montada_en"] for p in ens.piezas if "montada_en" in p.metadatos}
    if not montajes:
        return []
    errores: list[str] = []
    ids = {p.id for p in ens.piezas}
    raices = [p.id for p in ens.piezas if p.id not in montajes]
    if len(raices) != 1:
        errores.append(
            f"Debe haber exactamente una pieza raíz sin 'montada_en' (hay {len(raices)}: {raices})"
        )
    for hijo, padre in montajes.items():
        if padre not in ids:
            errores.append(f"{hijo}: montada en pieza inexistente '{padre}'")
        if padre == hijo:
            errores.append(f"{hijo}: montada en sí misma")
    for pid in montajes:  # ciclos en el árbol de montaje
        visto: set[str] = set()
        actual = pid
        while actual in montajes and actual not in visto:
            visto.add(actual)
            actual = montajes[actual]
        if actual in visto:
            errores.append(f"{pid}: ciclo en el árbol de montaje")
    if errores:
        return errores
    if mallas is None:
        mallas = {p.id: construir_malla(p) for p in ens.piezas}
    armadas = mallas_en_posicion_armada(ens, mallas)
    for hijo, padre in montajes.items():
        d = distancia_minima_mallas(armadas[hijo], armadas[padre], tolerancia_m)
        if d > tolerancia_m:
            errores.append(
                f"{hijo} flota: dista {d * 1000:.1f} mm de la pieza en la que se monta ('{padre}'); "
                f"tolerancia {tolerancia_m * 1000:.0f} mm"
            )
    return errores


ENSAMBLAJES_GENERABLES = ("freno_disco", "moto_honda")


def construir_ensamblaje(
    ensamblaje: str = "freno_disco", parametros: ParametrosFreno | None = None
) -> Ensamblaje:
    """Construye un ensamblaje del catálogo por su identificador (``parametros`` solo aplica al freno)."""
    if ensamblaje == "freno_disco":
        return construir_freno(parametros)
    if ensamblaje == "moto_honda":
        if parametros is not None:
            raise ErrorEnsamblaje("Los parámetros del freno no aplican a 'moto_honda'")
        return construir_moto()
    raise ErrorEnsamblaje(f"Ensamblaje desconocido: '{ensamblaje}' (disponibles: {ENSAMBLAJES_GENERABLES})")


def generar(salida: Path, parametros: ParametrosFreno | None = None, ensamblaje: str = "freno_disco") -> dict:
    """Genera ``<ensamblaje>.glb`` y ``<ensamblaje>.manifiesto.json`` de forma reproducible.

    Por defecto se genera el freno de disco (comportamiento original). El nombre del archivo en
    disco es el último componente de ``archivo_glb`` del ensamblaje.
    """
    salida.mkdir(parents=True, exist_ok=True)
    ens = construir_ensamblaje(ensamblaje, parametros)
    escena, mallas = construir_escena(ens)
    datos = escena.export(file_type="glb")
    ruta_glb = salida / Path(ens.archivo_glb).name
    ruta_glb.write_bytes(datos)
    manifiesto = {
        "ensamblaje": ens.id,
        "version": ens.version,
        "archivo": ens.archivo_glb,
        "sha256": hashlib.sha256(datos).hexdigest(),
        "bytes": len(datos),
        "unidades": "m",
        "eje_arriba": "Y",
        "generador": f"trimesh {trimesh.__version__} + manifold3d",
        "advertencia": ens.advertencia,
        "parametros": ens.parametros,
        "procedencia_parametros": ens.procedencia_parametros,
        "piezas": [
            {
                "id": pid,
                "nodo": ens.pieza(pid).geometria.nodo_glb,
                "vertices": len(m.vertices),
                "caras": len(m.faces),
                "volumen_m3": round(float(m.volume), 9),
                "cerrada": bool(m.is_watertight),
                "limites_locales_m": np.round(m.bounds, 6).tolist(),
            }
            for pid, m in mallas.items()
        ],
    }
    (salida / f"{ens.id}.manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )
    log.info("GLB generado: %s (%d bytes, %d piezas)", ruta_glb, len(datos), len(mallas))
    return manifiesto
