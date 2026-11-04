"""Cinemática, validación estructural, despiece y secuencias de (des)montaje.

Separación explícita (Parte VIII, §32):
* **Animación visual**: interpolaciones del frontend entre estados calculados aquí.
* **Cinemática**: este módulo (transformaciones rígidas a partir de valores de articulación).
* **Simulación física**: ``fisica_freno.py`` (fuerzas y pares con fórmulas verificables).
"""

from __future__ import annotations

import math
from collections import defaultdict, deque

import numpy as np

from fabrica_autopartes.simulador.modelos import (
    Articulacion,
    Ensamblaje,
    NodoJerarquia,
    TipoArticulacion,
    Vector3,
)


class ErrorEnsamblaje(ValueError):
    """Inconsistencia estructural o valor de articulación inválido."""


# ----------------------------------------------------------------------- álgebra
def matriz_rotacion_euler(grados: Vector3) -> np.ndarray:
    rx, ry, rz = (math.radians(g) for g in grados)
    cx, sx, cy, sy, cz, sz = (
        math.cos(rx),
        math.sin(rx),
        math.cos(ry),
        math.sin(ry),
        math.cos(rz),
        math.sin(rz),
    )
    mx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    my = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    mz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return mz @ my @ mx  # convención XYZ intrínseca (igual que three.js por defecto)


def matriz_rotacion_eje(eje: Vector3, grados: float) -> np.ndarray:
    """Fórmula de Rodrigues."""
    k = np.asarray(eje, dtype=float)
    k = k / np.linalg.norm(k)
    a = math.radians(grados)
    kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(a) * kx + (1 - math.cos(a)) * (kx @ kx)


def homogenea(rot: np.ndarray, tras: np.ndarray | Vector3) -> np.ndarray:
    m = np.eye(4)
    m[:3, :3] = rot
    m[:3, 3] = np.asarray(tras, dtype=float)
    return m


def euler_desde_matriz(r: np.ndarray) -> Vector3:
    """Inversa de ``matriz_rotacion_euler`` (XYZ). Fuera de gimbal lock."""
    sy = -r[2, 0]
    sy = max(-1.0, min(1.0, sy))
    ry = math.asin(sy)
    if abs(math.cos(ry)) > 1e-9:
        rx = math.atan2(r[2, 1], r[2, 2])
        rz = math.atan2(r[1, 0], r[0, 0])
    else:  # gimbal lock
        rx, rz = math.atan2(-r[1, 2], r[1, 1]), 0.0
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


# --------------------------------------------------------------- validación
def validar_ensamblaje(ens: Ensamblaje) -> list[str]:
    """Devuelve la lista de errores estructurales (vacía si el ensamblaje es íntegro)."""
    errores: list[str] = []
    ids = [p.id for p in ens.piezas]
    if len(ids) != len(set(ids)):
        errores.append("Identificadores de pieza duplicados")
    nodos = [p.geometria.nodo_glb for p in ens.piezas]
    if len(nodos) != len(set(nodos)):
        errores.append("Nodos GLB duplicados")
    subconjuntos = {s.id for s in ens.subconjuntos}
    conjunto = set(ids)
    for p in ens.piezas:
        if p.subconjunto not in subconjuntos:
            errores.append(f"{p.id}: subconjunto inexistente '{p.subconjunto}'")
        for r in p.relacionadas + p.retirar_antes:
            if r not in conjunto:
                errores.append(f"{p.id}: referencia a pieza inexistente '{r}'")
        if p.id in p.retirar_antes:
            errores.append(f"{p.id}: se referencia a sí misma en retirar_antes")
    arts = {a.id: a for a in ens.articulaciones}
    hijos: dict[str, int] = defaultdict(int)
    for a in ens.articulaciones:
        if a.hijo not in conjunto:
            errores.append(f"{a.id}: hijo inexistente '{a.hijo}'")
        if a.padre is not None and a.padre not in conjunto:
            errores.append(f"{a.id}: padre inexistente '{a.padre}'")
        if a.maestra is not None and a.maestra not in arts:
            errores.append(f"{a.id}: articulación maestra inexistente '{a.maestra}'")
        hijos[a.hijo] += 1
    for pid, n in hijos.items():
        if n > 1:
            errores.append(f"{pid}: es hijo de {n} articulaciones (máximo 1)")
    for p in ens.piezas:
        if hijos.get(p.id, 0) == 0:
            errores.append(f"{p.id}: no está vinculada por ninguna articulación")
    try:
        _orden_cadena(ens)
    except ErrorEnsamblaje as exc:
        errores.append(str(exc))
    try:
        secuencia_desmontaje(ens)
    except ErrorEnsamblaje as exc:
        errores.append(str(exc))
    return errores


def _orden_cadena(ens: Ensamblaje) -> list[Articulacion]:
    """Articulaciones ordenadas de la raíz a las hojas; detecta ciclos padre→hijo."""
    por_hijo = {a.hijo: a for a in ens.articulaciones}
    orden: list[Articulacion] = []
    estado: dict[str, int] = {}

    def visitar(pieza_id: str) -> None:
        if estado.get(pieza_id) == 2:
            return
        if estado.get(pieza_id) == 1:
            raise ErrorEnsamblaje(f"Ciclo en la cadena cinemática que involucra '{pieza_id}'")
        estado[pieza_id] = 1
        art = por_hijo.get(pieza_id)
        if art is not None:
            if art.padre is not None:
                visitar(art.padre)
            orden.append(art)
        estado[pieza_id] = 2

    for p in ens.piezas:
        visitar(p.id)
    return orden


# --------------------------------------------------------------- cinemática
def resolver_valores(ens: Ensamblaje, valores: dict[str, float]) -> dict[str, float]:
    """Valida los valores enviados (no confía en el cliente) y resuelve las compuestas."""
    arts = {a.id: a for a in ens.articulaciones}
    resueltos: dict[str, float] = {}
    for art_id, valor in valores.items():
        if art_id not in arts:
            raise ErrorEnsamblaje(f"Articulación inexistente: '{art_id}'")
        a = arts[art_id]
        if a.tipo in (TipoArticulacion.FIJA, TipoArticulacion.COMPUESTA):
            raise ErrorEnsamblaje(f"'{art_id}' no es una articulación accionable ({a.tipo})")
        if not math.isfinite(valor):
            raise ErrorEnsamblaje(f"Valor no finito para '{art_id}'")
        if a.limites is not None and not (a.limites.minimo <= valor <= a.limites.maximo):
            raise ErrorEnsamblaje(
                f"'{art_id}' fuera de límites: {valor} ∉ [{a.limites.minimo}, {a.limites.maximo}] {a.unidad}"
            )
        resueltos[art_id] = valor
    for a in ens.articulaciones:
        if a.tipo in (TipoArticulacion.ROTACIONAL, TipoArticulacion.PRISMATICA):
            resueltos.setdefault(a.id, a.valor_inicial)
    for a in ens.articulaciones:
        if a.tipo == TipoArticulacion.COMPUESTA:
            assert a.maestra is not None and a.relacion is not None
            resueltos[a.id] = a.relacion * resueltos.get(a.maestra, 0.0)
    return resueltos


def transformaciones(ens: Ensamblaje, valores: dict[str, float] | None = None) -> dict[str, np.ndarray]:
    """Matriz 4×4 global de cada pieza para los valores de articulación dados.

    El movimiento de cada articulación se aplica en el marco del ensamblaje y se propaga a
    los descendientes (cadena padre → hijo).
    """
    res = resolver_valores(ens, valores or {})
    base = {
        p.id: homogenea(matriz_rotacion_euler(p.transformacion.rotacion_grados), p.transformacion.posicion)
        for p in ens.piezas
    }
    movimiento: dict[str, np.ndarray] = {}
    for a in _orden_cadena(ens):
        padre = movimiento.get(a.padre, np.eye(4)) if a.padre else np.eye(4)
        valor = res.get(a.id, 0.0)
        if a.tipo == TipoArticulacion.FIJA or valor == 0.0:
            local = np.eye(4)
        elif a.unidad == "grados":
            o = np.asarray(a.origen)
            r = matriz_rotacion_eje(a.eje, valor)
            local = homogenea(r, o - r @ o)
        else:
            local = homogenea(np.eye(3), np.asarray(a.eje) * valor)
        movimiento[a.hijo] = padre @ local
    return {pid: movimiento.get(pid, np.eye(4)) @ m for pid, m in base.items()}


def lecturas(ens: Ensamblaje, valores: dict[str, float] | None = None) -> dict[str, dict]:
    """Posición (m) y orientación (grados) legibles para el panel de lecturas."""
    salida = {}
    for pid, m in transformaciones(ens, valores).items():
        salida[pid] = {
            "posicion": [round(float(c), 6) for c in m[:3, 3]],
            "rotacion_grados": [round(c, 4) for c in euler_desde_matriz(m[:3, :3])],
        }
    return salida


# ------------------------------------------------------------ despiece
def posiciones_despiece(ens: Ensamblaje, factor: float = 1.0) -> dict[str, Vector3]:
    """Posición de cada pieza en el despiece (factor 0 = ensamblado, 1 = despiece completo).

    Se calcula a partir de la posición ensamblada, por lo que el proceso es reversible:
    restar el mismo desplazamiento devuelve exactamente la posición original.
    """
    if not (0.0 <= factor <= 1.0):
        raise ErrorEnsamblaje("El factor de despiece debe estar en [0, 1]")
    salida: dict[str, Vector3] = {}
    for p in ens.piezas:
        d = np.asarray(p.direccion_despiece, dtype=float)
        d = d / np.linalg.norm(d)
        pos = np.asarray(p.transformacion.posicion) + d * p.distancia_despiece_m * factor
        salida[p.id] = (float(pos[0]), float(pos[1]), float(pos[2]))
    return salida


def secuencia_desmontaje(ens: Ensamblaje) -> list[str]:
    """Orden topológico estable de desmontaje a partir de ``retirar_antes`` (algoritmo de Kahn)."""
    orden_catalogo = {p.id: i for i, p in enumerate(ens.piezas)}
    dependientes: dict[str, list[str]] = defaultdict(list)
    pendientes = {p.id: len(p.retirar_antes) for p in ens.piezas}
    for p in ens.piezas:
        for previa in p.retirar_antes:
            dependientes[previa].append(p.id)
    cola = deque(sorted((pid for pid, n in pendientes.items() if n == 0), key=lambda x: orden_catalogo[x]))
    orden: list[str] = []
    while cola:
        actual = cola.popleft()
        orden.append(actual)
        listos = []
        for siguiente in dependientes[actual]:
            pendientes[siguiente] -= 1
            if pendientes[siguiente] == 0:
                listos.append(siguiente)
        cola.extend(sorted(listos, key=lambda x: orden_catalogo[x]))
    if len(orden) != len(ens.piezas):
        faltan = sorted(set(pendientes) - set(orden))
        raise ErrorEnsamblaje(f"Ciclo en las dependencias de desmontaje: {faltan}")
    return orden


def secuencia_reensamblaje(ens: Ensamblaje) -> list[str]:
    return list(reversed(secuencia_desmontaje(ens)))


def que_retirar_primero(ens: Ensamblaje, pieza_id: str) -> list[str]:
    """Cierre transitivo de ``retirar_antes`` en orden de desmontaje."""
    ens.pieza(pieza_id)
    necesarias: set[str] = set()
    pila = list(ens.pieza(pieza_id).retirar_antes)
    while pila:
        actual = pila.pop()
        if actual not in necesarias:
            necesarias.add(actual)
            pila.extend(ens.pieza(actual).retirar_antes)
    return [p for p in secuencia_desmontaje(ens) if p in necesarias]


def jerarquia(ens: Ensamblaje) -> NodoJerarquia:
    raiz = NodoJerarquia(id=ens.id, nombre=ens.nombre, tipo="ensamblaje")
    for s in ens.subconjuntos:
        nodo = NodoJerarquia(id=s.id, nombre=s.nombre, tipo="subconjunto")
        nodo.hijos = [
            NodoJerarquia(id=p.id, nombre=p.nombre, tipo="pieza") for p in ens.piezas if p.subconjunto == s.id
        ]
        raiz.hijos.append(nodo)
    return raiz
