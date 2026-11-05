"""Primitivas geométricas de la motocicleta: revolución, tubo, extrusión de perfil 2D, engranaje y rin.

Solo dependen de numpy, trimesh y manifold3d (sin scipy). Todas devuelven mallas cerradas
(watertight) con caras orientadas hacia fuera. Los puntos de perfil y de trayectoria se reciben
como parámetros numéricos con prefijo ``c_`` (``c_x0``, ``c_y0``, ``c_z0``, ``c_x1``, …) porque
``Geometria.parametros`` solo admite números.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import trimesh


def leer_puntos(q: dict[str, float], claves: tuple[str, ...]) -> np.ndarray:
    """Reúne ``c_<clave><i>`` (i = 0, 1, …) en un arreglo (n, len(claves))."""
    filas = []
    i = 0
    while f"c_{claves[0]}{i}" in q:
        filas.append([q[f"c_{k}{i}"] for k in claves])
        i += 1
    if not filas:
        raise ValueError(f"No hay puntos 'c_{claves[0]}0…' en los parámetros")
    return np.asarray(filas, dtype=float)


def codificar_puntos(puntos: object, claves: tuple[str, ...]) -> dict[str, float]:
    """Inversa de ``leer_puntos``: arreglo (n, k) → ``{c_x0: …, c_y0: …}`` redondeado a 1e-6."""
    arr = np.asarray(puntos, dtype=float)
    return {f"c_{k}{i}": round(float(fila[j]), 6) for i, fila in enumerate(arr) for j, k in enumerate(claves)}


def _cerrar(vertices: object, caras: object) -> trimesh.Trimesh:
    m = trimesh.Trimesh(
        vertices=np.asarray(vertices, dtype=float), faces=np.asarray(caras, dtype=np.int64), process=False
    )
    if m.volume < 0:
        m.invert()
    return m


def _union(*mallas: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.union(list(mallas), engine="manifold")


def _diferencia(a: trimesh.Trimesh, b: trimesh.Trimesh) -> trimesh.Trimesh:
    return trimesh.boolean.difference([a, b], engine="manifold")


# ---------------------------------------------------------------- revolución
def revolucion(perfil: np.ndarray, secciones: int = 48, cerrado: bool = False) -> trimesh.Trimesh:
    """Sólido de revolución alrededor del eje Z. ``perfil`` = filas (radio, z).

    Perfil abierto: debe empezar y terminar en radio 0 (sólido). Perfil cerrado
    (``cerrado=True``): lazo sin tocar el eje (p. ej. sección de un neumático).
    """
    n = secciones
    ang = 2 * math.pi * np.arange(n) / n
    c, s = np.cos(ang), np.sin(ang)
    vertices: list[tuple[float, float, float]] = []
    inicio: list[tuple[bool, int]] = []
    for r, z in perfil:
        if r <= 1e-9:
            inicio.append((True, len(vertices)))
            vertices.append((0.0, 0.0, float(z)))
        else:
            inicio.append((False, len(vertices)))
            vertices.extend((float(r * c[k]), float(r * s[k]), float(z)) for k in range(n))
    if not cerrado and not (inicio[0][0] and inicio[-1][0]):
        raise ValueError("El perfil abierto debe empezar y terminar en el eje (radio 0)")
    pares = [(i, i + 1) for i in range(len(perfil) - 1)]
    if cerrado:
        pares.append((len(perfil) - 1, 0))
    caras: list[tuple[int, int, int]] = []
    for i, j in pares:
        (apice_i, a), (apice_j, b) = inicio[i], inicio[j]
        for k in range(n):
            k2 = (k + 1) % n
            if apice_i and apice_j:
                continue
            if apice_i:
                caras.append((a, b + k, b + k2))
            elif apice_j:
                caras.append((a + k, b, a + k2))
            else:
                caras += [(a + k, b + k, b + k2), (a + k, b + k2, a + k2)]
    return _cerrar(vertices, caras)


def perfil_neumatico(
    radio_exterior: float, radio_talon: float, semiancho: float, n_puntos: int = 20
) -> np.ndarray:
    """Sección cerrada (radio, z) tipo superelipse: el radio máximo es exactamente ``radio_exterior``."""
    centro = (radio_exterior + radio_talon) / 2
    a = (radio_exterior - radio_talon) / 2
    e = 2.0 / 2.6
    pts = []
    for k in range(n_puntos):
        fi = 2 * math.pi * k / n_puntos
        cf, sf = math.cos(fi), math.sin(fi)
        pts.append(
            (centro + a * math.copysign(abs(cf) ** e, cf), semiancho * math.copysign(abs(sf) ** e, sf))
        )
    return np.asarray(pts)


# ---------------------------------------------------------------------- tubo
def _chaikin(p: np.ndarray, iteraciones: int) -> np.ndarray:
    for _ in range(iteraciones):
        nuevo = [p[0]]
        for a, b in itertools.pairwise(p):
            nuevo += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        nuevo.append(p[-1])
        p = np.asarray(nuevo)
    return p


def tubo(
    puntos: np.ndarray, radio: float, secciones: int = 12, suavizado: int = 2, radio_fin: float | None = None
) -> trimesh.Trimesh:
    """Tubo de sección circular a lo largo de una polilínea 3D suavizada (corte de esquinas)."""
    p = _chaikin(np.asarray(puntos, dtype=float), suavizado)
    keep = [0] + [i for i in range(1, len(p)) if np.linalg.norm(p[i] - p[i - 1]) > 1e-9]
    p = p[keep]
    m = len(p)
    t = np.zeros_like(p)
    t[0] = p[1] - p[0]
    t[-1] = p[-1] - p[-2]
    for i in range(1, m - 1):
        t[i] = p[i + 1] - p[i - 1]
    t /= np.linalg.norm(t, axis=1)[:, None]
    eje = np.eye(3)[int(np.argmin(np.abs(t[0])))]
    nrm = np.cross(t[0], eje)
    nrm /= np.linalg.norm(nrm)
    normales = [nrm]
    for i in range(1, m):
        nrm = normales[-1] - np.dot(normales[-1], t[i]) * t[i]
        nrm = nrm / np.linalg.norm(nrm)
        normales.append(nrm)
    ang = 2 * math.pi * np.arange(secciones) / secciones
    vertices: list[np.ndarray] = []
    for i in range(m):
        b = np.cross(t[i], normales[i])
        r = radio if radio_fin is None else radio + (radio_fin - radio) * i / (m - 1)
        for a in ang:
            vertices.append(p[i] + r * (math.cos(a) * normales[i] + math.sin(a) * b))
    caras: list[tuple[int, int, int]] = []
    for i in range(m - 1):
        a0, b0 = i * secciones, (i + 1) * secciones
        for k in range(secciones):
            k2 = (k + 1) % secciones
            caras += [(a0 + k, b0 + k, b0 + k2), (a0 + k, b0 + k2, a0 + k2)]
    c0, c1 = len(vertices), len(vertices) + 1
    vertices += [p[0], p[-1]]
    for k in range(secciones):
        k2 = (k + 1) % secciones
        caras.append((c0, k, k2))
        caras.append((c1, (m - 1) * secciones + k2, (m - 1) * secciones + k))
    return _cerrar(vertices, caras)


# ----------------------------------------------------------------- extrusión
def _area_con_signo(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def triangular_poligono(p: np.ndarray) -> list[tuple[int, int, int]]:
    """Triangulación por recorte de orejas de un polígono simple antihorario (índices de ``p``)."""
    idx = list(range(len(p)))
    tris: list[tuple[int, int, int]] = []
    while len(idx) > 3:
        m = len(idx)
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = p[i0], p[i1], p[i2]
            cruz = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if cruz <= 1e-12:
                continue
            dentro = False
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                q = p[j]
                d1 = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
                d2 = (c[0] - b[0]) * (q[1] - b[1]) - (c[1] - b[1]) * (q[0] - b[0])
                d3 = (a[0] - c[0]) * (q[1] - c[1]) - (a[1] - c[1]) * (q[0] - c[0])
                if d1 >= -1e-12 and d2 >= -1e-12 and d3 >= -1e-12:
                    dentro = True
                    break
            if dentro:
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            raise ValueError("Polígono no simple o con vértices colineales: no se puede triangular")
    tris.append((idx[0], idx[1], idx[2]))
    return tris


def extrusion(poligono: np.ndarray, espesor: float) -> trimesh.Trimesh:
    """Prisma de perfil 2D (plano XY) y espesor en Z, centrado en z = 0."""
    p = np.asarray(poligono, dtype=float)
    if _area_con_signo(p) < 0:
        p = p[::-1]
    n = len(p)
    h = espesor / 2
    vertices = [(x, y, -h) for x, y in p] + [(x, y, h) for x, y in p]
    caras: list[tuple[int, int, int]] = []
    for a, b, c in triangular_poligono(p):
        caras.append((a + n, b + n, c + n))
        caras.append((c, b, a))
    for i in range(n):
        j = (i + 1) % n
        caras += [(i, j, j + n), (i, j + n, i + n)]
    return _cerrar(vertices, caras)


# ----------------------------------------------------------------- engranaje
def poligono_engranaje(n_dientes: int, radio_punta: float, radio_raiz: float) -> np.ndarray:
    """Contorno de un piñón/corona de ``n_dientes`` dientes trapezoidales (antihorario)."""
    paso = 2 * math.pi / n_dientes
    pts = []
    for i in range(n_dientes):
        a0 = i * paso
        for da, r in ((-0.30, radio_raiz), (-0.14, radio_punta), (0.14, radio_punta), (0.30, radio_raiz)):
            pts.append((r * math.cos(a0 + da * paso), r * math.sin(a0 + da * paso)))
    return np.asarray(pts)


def engranaje(
    n_dientes: int,
    radio_punta: float,
    radio_raiz: float,
    espesor: float,
    radio_agujero: float,
    n_aligeramientos: int = 0,
    radio_aligeramiento: float = 0.0,
    radio_circulo_aligeramiento: float = 0.0,
) -> trimesh.Trimesh:
    m = extrusion(poligono_engranaje(n_dientes, radio_punta, radio_raiz), espesor)
    m = _union(m)  # normaliza a una malla manifold
    huecos = [trimesh.creation.cylinder(radius=radio_agujero, height=espesor * 3, sections=24)]
    for i in range(n_aligeramientos):
        a = 2 * math.pi * i / n_aligeramientos
        h = trimesh.creation.cylinder(radius=radio_aligeramiento, height=espesor * 3, sections=20)
        h.apply_translation(
            (radio_circulo_aligeramiento * math.cos(a), radio_circulo_aligeramiento * math.sin(a), 0)
        )
        huecos.append(h)
    return _diferencia(m, _union(*huecos) if len(huecos) > 1 else huecos[0])


# ----------------------------------------------------------------------- rin
def rin_rayos(
    radio_exterior: float,
    ancho: float,
    n_rayos: int,
    radio_cubo: float,
    ancho_rayo: float,
    espesor_rayo: float,
    radio_agujero: float,
) -> trimesh.Trimesh:
    """Rin de ``n_rayos`` rayos: aro (sección rectangular), cubo central y rayos radiales."""
    h = ancho / 2
    espesor_aro = 0.012
    aro = revolucion(
        np.array(
            [
                (radio_exterior - espesor_aro, -h),
                (radio_exterior, -h),
                (radio_exterior, h),
                (radio_exterior - espesor_aro, h),
            ]
        ),
        secciones=72,
        cerrado=True,
    )
    cubo = trimesh.creation.cylinder(radius=radio_cubo, height=0.03, sections=32)
    partes = [aro, cubo]
    r0 = radio_cubo * 0.6
    r1 = radio_exterior - espesor_aro + 0.004
    for i in range(n_rayos):
        ang = 2 * math.pi * i / n_rayos
        caja = trimesh.creation.box(extents=(r1 - r0, ancho_rayo, espesor_rayo))
        caja.apply_translation(((r0 + r1) / 2, 0, 0))
        rot = trimesh.transformations.rotation_matrix(ang, (0, 0, 1))
        caja.apply_transform(rot)
        partes.append(caja)
    m = _union(*partes)
    agujero = trimesh.creation.cylinder(radius=radio_agujero, height=ancho * 3, sections=24)
    return _diferencia(m, agujero)
