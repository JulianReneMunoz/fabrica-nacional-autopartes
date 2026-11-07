"""Evaluación de la recuperación (ADR-023): prefijos de nomic, BM25 frente a semántico y tiempos.

Criterio de relevancia (sin anotación manual): un fragmento es relevante para una pregunta ``respondible``
si contiene al menos ``minimo`` de sus ``hechos`` (comparados sin tildes ni mayúsculas, igual que en
``services/evaluacion.py``). Las preguntas sin ningún fragmento relevante se excluyen y se informan.

Métricas: hit@k (proporción de preguntas con un fragmento relevante entre los k primeros) y MRR@10
(promedio de 1/rango del primer relevante; 0 si no aparece entre los 10 primeros).
"""

from __future__ import annotations

import json
import statistics
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.embeddings import FuncionEmbeddings, texto_indexable
from fabrica_autopartes.knowledge.recuperacion import Recuperador
from fabrica_autopartes.services.evaluacion import hechos_presentes

DIR_RESULTADOS = RAIZ_PROYECTO / "evaluacion" / "resultados"
PROFUNDIDAD_MRR = 10
CASOS_PREFIJOS = 3
MIN_HECHOS_PREFIJOS = 2


# ------------------------------------------------------------------ relevancia
def fragmentos_relevantes(pregunta: dict[str, Any], fragmentos: Sequence[Fragmento]) -> list[str]:
    minimo = int(pregunta.get("minimo", 1))
    hechos = list(pregunta.get("hechos", []))
    return [f.id for f in fragmentos if len(hechos_presentes(texto_indexable(f), hechos)) >= minimo]


def preguntas_respondibles(preguntas: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for p in preguntas if p.get("tipo") == "respondible"]


# --------------------------------------------------------------- comparación
def metricas_recuperador(
    recuperador: Recuperador,
    preguntas: Sequence[dict[str, Any]],
    fragmentos: Sequence[Fragmento],
    ks: Sequence[int] = (3, 5),
) -> dict[str, Any]:
    detalle: list[dict[str, Any]] = []
    excluidas: list[str] = []
    for p in preguntas_respondibles(preguntas):
        relevantes = set(fragmentos_relevantes(p, fragmentos))
        if not relevantes:
            excluidas.append(p["id"])
            continue
        ids = [r.fragmento.id for r in recuperador.buscar(p["pregunta"], PROFUNDIDAD_MRR)]
        rango = next((i for i, fid in enumerate(ids, 1) if fid in relevantes), None)
        detalle.append({"id": p["id"], "rango": rango, "relevantes": len(relevantes), "top3": ids[:3]})
    n = len(detalle)
    metricas: dict[str, float] = {}
    for k in ks:
        metricas[f"hit@{k}"] = (
            round(sum(1 for d in detalle if d["rango"] and d["rango"] <= k) / n, 4) if n else 0.0
        )
    metricas[f"mrr@{PROFUNDIDAD_MRR}"] = (
        round(sum(1 / d["rango"] for d in detalle if d["rango"]) / n, 4) if n else 0.0
    )
    return {
        "preguntas_evaluadas": n,
        "excluidas_sin_relevante": excluidas,
        "metricas": metricas,
        "detalle": detalle,
    }


def comparar_recuperadores(
    recuperadores: dict[str, Recuperador],
    preguntas: Sequence[dict[str, Any]],
    fragmentos: Sequence[Fragmento],
) -> dict[str, Any]:
    return {nombre: metricas_recuperador(r, preguntas, fragmentos) for nombre, r in recuperadores.items()}


# -------------------------------------------------------- experimento de prefijos
def casos_prefijos(
    preguntas: Sequence[dict[str, Any]],
    fragmentos: Sequence[Fragmento],
    n: int = CASOS_PREFIJOS,
) -> list[tuple[str, Fragmento]]:
    """Elige ``n`` pares (consulta, fragmento) con relevancia exclusiva.

    Cada fragmento es relevante para su consulta y para ninguna otra del conjunto, de modo que la
    diagonal de la matriz es la única respuesta correcta. Se recorren las preguntas ``respondible`` en
    orden; solo cuentan fragmentos con al menos ``MIN_HECHOS_PREFIJOS`` hechos presentes, y se toma el que
    contiene más (a igualdad, el primero del archivo).
    """
    elegidas: list[tuple[dict[str, Any], Fragmento, set[str]]] = []
    for p in preguntas_respondibles(preguntas):
        relevantes = set(fragmentos_relevantes(p, fragmentos))
        if not relevantes or any(f.id in relevantes for _, f, _ in elegidas):
            continue
        hechos = list(p.get("hechos", []))
        aptos = [
            (len(hechos_presentes(texto_indexable(f), hechos)), f)
            for f in fragmentos
            if f.id in relevantes and all(f.id not in r for _, _, r in elegidas)
        ]
        # Evidencia fuerte: al menos dos hechos presentes (un número suelto, como «450», coincide por azar).
        aptos = [(c, f) for c, f in aptos if c >= MIN_HECHOS_PREFIJOS]
        candidato = max(aptos, key=lambda par: par[0])[1] if aptos else None
        if candidato is not None:
            elegidas.append((p, candidato, relevantes))
        if len(elegidas) == n:
            break
    return [(p["pregunta"], f) for p, f, _ in elegidas]


def _resumen_matriz(m: np.ndarray) -> dict[str, Any]:
    n = m.shape[0]
    fuera = m[~np.eye(n, dtype=bool)]
    diagonal = float(np.mean(np.diag(m)))
    fuera_media = float(np.mean(fuera)) if fuera.size else 0.0
    return {
        "matriz": [[round(float(x), 4) for x in fila] for fila in m],
        "diagonal_media": round(diagonal, 4),
        "fuera_diagonal_media": round(fuera_media, 4),
        "margen": round(diagonal - fuera_media, 4),
        "aciertos_top1": int(sum(int(np.argmax(m[i]) == i) for i in range(n))),
    }


def experimento_prefijos(
    funcion: FuncionEmbeddings, casos: Sequence[tuple[str, Fragmento]]
) -> dict[str, Any]:
    """Similitud coseno consulta × fragmento con y sin prefijos (``search_query``/``search_document``)."""
    consultas = [c for c, _ in casos]
    textos = [texto_indexable(f) for _, f in casos]
    resultado: dict[str, Any] = {
        "consultas": consultas,
        "fragmentos": [f.id for _, f in casos],
    }
    for etiqueta, con in (("con_prefijos", True), ("sin_prefijos", False)):
        m = funcion.consultas(consultas, con_prefijo=con) @ funcion.documentos(textos, con_prefijo=con).T
        resultado[etiqueta] = _resumen_matriz(m)
    return resultado


# ------------------------------------------------------------------- tiempos
def medir_indexacion(
    crear_funcion: Callable[[str], FuncionEmbeddings],
    indexar: Callable[[FuncionEmbeddings], int],
    dispositivos: Sequence[str],
    repeticiones: int = 3,
    calentamiento: int = 1,
) -> dict[str, Any]:
    """Tiempo de indexación por dispositivo: ``calentamiento`` ejecuciones descartadas y la mediana de
    ``repeticiones`` (la carga del modelo se mide aparte)."""
    resultados: dict[str, Any] = {}
    for dispositivo in dispositivos:
        inicio = time.perf_counter()
        funcion = crear_funcion(dispositivo)
        carga = time.perf_counter() - inicio
        for _ in range(calentamiento):
            indexar(funcion)
        tiempos: list[float] = []
        total = 0
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            total = indexar(funcion)
            tiempos.append(time.perf_counter() - inicio)
        resultados[dispositivo] = {
            **funcion.descripcion(),
            "carga_modelo_s": round(carga, 3),
            "calentamiento": calentamiento,
            "repeticiones_s": [round(t, 3) for t in tiempos],
            "mediana_s": round(statistics.median(tiempos), 3),
            "fragmentos_indexados": total,
        }
    return resultados


# ------------------------------------------------------------- orquestación
class IndiceIndexable(Recuperador, Protocol):
    def indexar(self, fragmentos: list[Fragmento]) -> int: ...


def evaluar_base_semantica(
    fragmentos: list[Fragmento],
    preguntas: Sequence[dict[str, Any]],
    indice_bm25: Recuperador,
    crear_funcion: Callable[[str], FuncionEmbeddings],
    crear_indice: Callable[[FuncionEmbeddings, bool], IndiceIndexable],
    dispositivo: str,
    dispositivos_tiempo: Sequence[str],
    repeticiones: int = 3,
    calentamiento: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Experimento de prefijos (C6) y comparación BM25 frente a semántico con tiempos por dispositivo.

    ``crear_indice(funcion, principal)`` construye el índice de la comparación (``principal=True``) o uno
    desechable para medir tiempos. Devuelve ``(prefijos, recuperadores)``, listos para ``guardar_resultado``.
    """
    funcion = crear_funcion(dispositivo)
    indice = crear_indice(funcion, True)
    indice.indexar(fragmentos)
    entorno = funcion.descripcion()
    prefijos = {"entorno": entorno, **experimento_prefijos(funcion, casos_prefijos(preguntas, fragmentos))}
    recuperadores = {
        "entorno": entorno,
        "comparacion": comparar_recuperadores(
            {"bm25": indice_bm25, "semantico": indice}, preguntas, fragmentos
        ),
        "tiempos_indexacion": medir_indexacion(
            crear_funcion,
            lambda f: crear_indice(f, False).indexar(fragmentos),
            dispositivos_tiempo,
            repeticiones,
            calentamiento,
        ),
    }
    return prefijos, recuperadores


# --------------------------------------------------------------- persistencia
def marca_tiempo() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def guardar_resultado(
    nombre: str, datos: dict[str, Any], markdown: str, directorio: Path = DIR_RESULTADOS
) -> Path:
    directorio.mkdir(parents=True, exist_ok=True)
    base = directorio / f"{marca_tiempo()}_{nombre}"
    base.with_suffix(".json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    base.with_suffix(".md").write_text(markdown, encoding="utf-8")
    return base.with_suffix(".md")


def markdown_prefijos(datos: dict[str, Any]) -> str:
    lineas = [
        "# Experimento C6: prefijos de nomic-embed-text-v1.5",
        "",
        f"Modelo: `{datos['entorno']['modelo']}` @ `{datos['entorno']['revision']}` · dispositivo: "
        f"`{datos['entorno']['dispositivo']}`.",
        "Similitud coseno entre cada consulta (filas) y cada fragmento (columnas);",
        "la diagonal es el par correcto.",
        "",
    ]
    for i, (c, f) in enumerate(zip(datos["consultas"], datos["fragmentos"], strict=True), 1):
        lineas.append(f"- Q{i}: «{c}» → fragmento `{f}`")
    for etiqueta, titulo in (("con_prefijos", "Con prefijos"), ("sin_prefijos", "Sin prefijos")):
        r = datos[etiqueta]
        lineas += ["", f"## {titulo}", "", "| | " + " | ".join(f"`{f}`" for f in datos["fragmentos"]) + " |"]
        lineas.append("|---" * (len(datos["fragmentos"]) + 1) + "|")
        for i, fila in enumerate(r["matriz"], 1):
            lineas.append(f"| Q{i} | " + " | ".join(f"{x:.4f}" for x in fila) + " |")
    lineas += [
        "",
        "## Resumen",
        "",
        "| Variante | Diagonal media | Fuera de diagonal | Margen | Aciertos top-1 |",
        "|---|---|---|---|---|",
    ]
    for etiqueta, titulo in (("con_prefijos", "Con prefijos"), ("sin_prefijos", "Sin prefijos")):
        r = datos[etiqueta]
        lineas.append(
            f"| {titulo} | {r['diagonal_media']:.4f} | {r['fuera_diagonal_media']:.4f} | {r['margen']:.4f} | "
            f"{r['aciertos_top1']}/{len(r['matriz'])} |"
        )
    return "\n".join(lineas) + "\n"


def markdown_recuperadores(datos: dict[str, Any]) -> str:
    comparacion = datos["comparacion"]
    nombres = list(comparacion)
    primero = comparacion[nombres[0]]
    excluidas = ", ".join(primero["excluidas_sin_relevante"]) or "ninguna"
    lineas = [
        "# Comparación de recuperadores: BM25 frente a semántico (nomic + Chroma)",
        "",
        f"Banco: `evaluacion/preguntas.yaml`; {primero['preguntas_evaluadas']} preguntas `respondible`"
        f" evaluadas (excluidas sin fragmento relevante: {excluidas}).",
        "Relevante: fragmento con al menos `minimo` de los `hechos` de la pregunta.",
        "",
        "| Recuperador | hit@3 | hit@5 | MRR@10 |",
        "|---|---|---|---|",
    ]
    for n in nombres:
        m = comparacion[n]["metricas"]
        lineas.append(f"| {n} | {m['hit@3']:.4f} | {m['hit@5']:.4f} | {m[f'mrr@{PROFUNDIDAD_MRR}']:.4f} |")
    lineas += [
        "",
        "## Rango del primer fragmento relevante por pregunta",
        "",
        "| Pregunta | " + " | ".join(nombres) + " |",
    ]
    lineas.append("|---" * (len(nombres) + 1) + "|")
    for i, d in enumerate(primero["detalle"]):
        celdas = [str(comparacion[n]["detalle"][i]["rango"] or "—") for n in nombres]
        lineas.append(f"| {d['id']} | " + " | ".join(celdas) + " |")
    tiempos = datos.get("tiempos_indexacion") or {}
    if tiempos:
        t0 = next(iter(tiempos.values()))
        n, cal, n_reps = t0["fragmentos_indexados"], t0["calentamiento"], len(t0["repeticiones_s"])
        lineas += [
            "",
            f"## Tiempo de indexación ({n} fragmentos; {cal} calentamiento descartado, mediana de {n_reps})",
            "",
            "| Dispositivo | Carga del modelo (s) | Repeticiones (s) | Mediana (s) |",
            "|---|---|---|---|",
        ]
        for disp, t in tiempos.items():
            reps = ", ".join(f"{x:.3f}" for x in t["repeticiones_s"])
            lineas.append(f"| {disp} | {t['carga_modelo_s']:.3f} | {reps} | {t['mediana_s']:.3f} |")
    entorno = datos.get("entorno")
    if entorno:
        lineas += ["", "Entorno: " + ", ".join(f"{k}={v}" for k, v in entorno.items())]
    return "\n".join(lineas) + "\n"
