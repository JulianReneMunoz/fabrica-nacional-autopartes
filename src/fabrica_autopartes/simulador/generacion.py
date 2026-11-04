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
from fabrica_autopartes.simulador.cinematica import (
    ErrorEnsamblaje,
    homogenea,
    matriz_rotacion_euler,
    validar_ensamblaje,
)
from fabrica_autopartes.simulador.modelos import Ensamblaje, Pieza

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
}


def _diferencia(a: trimesh.Trimesh, b: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.difference([a, b], engine="manifold")


def _union(*mallas: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.union(list(mallas), engine="manifold")


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
    else:  # pragma: no cover - el modelo Pydantic restringe las primitivas
        raise ErrorEnsamblaje(f"Primitiva no soportada: {g.primitiva}")
    material = trimesh.visual.material.PBRMaterial(
        name=f"mat_{pieza.tipo}",
        baseColorFactor=COLORES.get(pieza.tipo, (128, 128, 128, 255)),
        metallicFactor=0.6 if pieza.tipo not in ("pastilla", "pinza") else 0.2,
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


def generar(salida: Path, parametros: ParametrosFreno | None = None) -> dict:
    """Genera ``freno_disco.glb`` y ``freno_disco.manifiesto.json`` de forma reproducible."""
    salida.mkdir(parents=True, exist_ok=True)
    ens = construir_freno(parametros)
    escena, mallas = construir_escena(ens)
    datos = escena.export(file_type="glb")
    ruta_glb = salida / ens.archivo_glb
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
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("GLB generado: %s (%d bytes, %d piezas)", ruta_glb, len(datos), len(mallas))
    return manifiesto
