"""Evaluación de recuperadores con embeddings deterministas (sin modelos, sin Chroma y sin red)."""

from __future__ import annotations

import json
from pathlib import Path

from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.embeddings import (
    EmbeddingsDeterministas,
    FuncionEmbeddings,
    IndiceVectorialMemoria,
)
from fabrica_autopartes.knowledge.recuperacion import IndiceBM25, Resultado
from fabrica_autopartes.services import evaluacion_recuperacion as er


def _fragmento(id_: str, texto: str) -> Fragmento:
    return Fragmento(
        id=id_,
        documento_id=id_,
        url=f"https://fanalca.com/{id_}",
        titulo="",
        seccion="general",
        texto=texto,
        tokens_aprox=len(texto.split()),
        orden=0,
    )


FRAGMENTOS = [
    _fragmento("sede", "La sede principal queda en la Calle 13 # 31A, Acopi, Yumbo"),
    _fragmento("telefono", "Teléfono de contacto: 651 5343"),
    _fragmento("historia", "Fanalca se constituyó el 31 de mayo de 1958"),
    _fragmento("otro", "Motocicletas, tubos de acero y autopartes"),
]
PREGUNTAS = [
    {
        "id": "P01",
        "tipo": "respondible",
        "pregunta": "¿Dónde queda la sede principal?",
        "hechos": ["calle 13", "acopi", "yumbo"],
        "minimo": 2,
    },
    {
        "id": "P02",
        "tipo": "respondible",
        "pregunta": "¿Cuál es el teléfono?",
        "hechos": ["651 5343", "contacto"],
        "minimo": 1,
    },
    {
        "id": "P03",
        "tipo": "respondible",
        "pregunta": "¿Cuándo se constituyó Fanalca?",
        "hechos": ["31 de mayo", "1958"],
        "minimo": 1,
    },
    {
        "id": "P04",
        "tipo": "respondible",
        "pregunta": "¿Cuántos empleados tiene?",
        "hechos": ["4321"],
        "minimo": 1,
    },
    {"id": "P20", "tipo": "ausente", "pregunta": "¿Precio de la acción?", "hechos": [], "minimo": 1},
]


class _Fijo:
    """Recuperador con un orden fijo de identificadores, para comprobar las métricas."""

    def __init__(self, ids: list[str]) -> None:
        self.ids = ids

    def buscar(self, consulta: str, k: int = 5) -> list[Resultado]:
        por_id = {f.id: f for f in FRAGMENTOS}
        return [Resultado(por_id[i], 1.0) for i in self.ids[:k]]


def test_relevancia_por_hechos_y_minimo() -> None:
    assert er.fragmentos_relevantes(PREGUNTAS[0], FRAGMENTOS) == ["sede"]
    assert er.fragmentos_relevantes(PREGUNTAS[3], FRAGMENTOS) == []


def test_metricas_hit_y_mrr() -> None:
    # Orden fijo: P01 → rango 4, P02 → rango 2, P03 → rango 3; P04 se excluye y P20 no es respondible.
    r = er.metricas_recuperador(_Fijo(["otro", "telefono", "historia", "sede"]), PREGUNTAS, FRAGMENTOS)
    assert r["preguntas_evaluadas"] == 3
    assert r["excluidas_sin_relevante"] == ["P04"]
    assert [d["rango"] for d in r["detalle"]] == [4, 2, 3]
    assert r["metricas"] == {
        "hit@3": round(2 / 3, 4),
        "hit@5": 1.0,
        "mrr@10": round((1 / 4 + 1 / 2 + 1 / 3) / 3, 4),
    }


def test_casos_prefijos_exigen_relevancia_exclusiva_y_dos_hechos() -> None:
    duplicada = {**PREGUNTAS[2], "id": "P05", "pregunta": "¿En qué año se fundó?"}  # mismo fragmento que P03
    suelta = {"id": "P06", "tipo": "respondible", "pregunta": "¿Autopartes?", "hechos": ["autopartes"]}
    casos = er.casos_prefijos([suelta, PREGUNTAS[2], duplicada, PREGUNTAS[0]], FRAGMENTOS)
    # P06 tiene un solo hecho presente; P05 comparte su único fragmento relevante con P03.
    assert [(c, f.id) for c, f in casos] == [
        ("¿Cuándo se constituyó Fanalca?", "historia"),
        ("¿Dónde queda la sede principal?", "sede"),
    ]


def test_metricas_sin_preguntas_evaluables() -> None:
    r = er.metricas_recuperador(_Fijo([]), [PREGUNTAS[3]], FRAGMENTOS)
    assert r["preguntas_evaluadas"] == 0 and r["metricas"]["hit@3"] == 0.0


def test_experimento_prefijos_produce_dos_matrices() -> None:
    casos = er.casos_prefijos(PREGUNTAS, FRAGMENTOS)
    assert [f.id for _, f in casos] == ["sede", "telefono", "historia"]
    datos = er.experimento_prefijos(EmbeddingsDeterministas(), casos)
    for variante in ("con_prefijos", "sin_prefijos"):
        assert len(datos[variante]["matriz"]) == 3
        assert datos[variante]["margen"] == round(
            datos[variante]["diagonal_media"] - datos[variante]["fuera_diagonal_media"], 4
        )
    # Los prefijos agregan tokens comunes: con el modelo simulado la similitud media sube.
    assert datos["con_prefijos"]["fuera_diagonal_media"] > datos["sin_prefijos"]["fuera_diagonal_media"]


def test_medir_indexacion_descarta_calentamiento_y_usa_la_mediana() -> None:
    llamadas: list[str] = []

    def crear(dispositivo: str) -> FuncionEmbeddings:
        llamadas.append(dispositivo)
        return EmbeddingsDeterministas()

    indexaciones: list[int] = []

    def indexar(funcion: FuncionEmbeddings) -> int:
        indexaciones.append(1)
        return IndiceVectorialMemoria(FRAGMENTOS, funcion).indexar(FRAGMENTOS)

    t = er.medir_indexacion(crear, indexar, ["cpu"], repeticiones=3, calentamiento=1)
    assert llamadas == ["cpu"] and len(indexaciones) == 4
    assert len(t["cpu"]["repeticiones_s"]) == 3 and t["cpu"]["fragmentos_indexados"] == 4
    assert t["cpu"]["mediana_s"] == sorted(t["cpu"]["repeticiones_s"])[1]


def test_evaluacion_completa_y_persistencia(tmp_path: Path) -> None:
    principales: list[bool] = []

    def crear_indice(funcion: FuncionEmbeddings, principal: bool) -> IndiceVectorialMemoria:
        principales.append(principal)
        return IndiceVectorialMemoria([], funcion)

    prefijos, recuperadores = er.evaluar_base_semantica(
        FRAGMENTOS,
        PREGUNTAS,
        IndiceBM25(FRAGMENTOS),
        lambda d: EmbeddingsDeterministas(),
        crear_indice,
        "cpu",
        ["cpu"],
        repeticiones=1,
        calentamiento=1,
    )
    assert principales == [True, False, False]
    assert set(recuperadores["comparacion"]) == {"bm25", "semantico"}
    assert recuperadores["comparacion"]["bm25"]["metricas"]["hit@3"] == 1.0
    md = er.guardar_resultado(
        "recuperadores", recuperadores, er.markdown_recuperadores(recuperadores), tmp_path
    )
    assert "| bm25 |" in md.read_text(encoding="utf-8") and "Mediana" in md.read_text(encoding="utf-8")
    assert json.loads(md.with_suffix(".json").read_text(encoding="utf-8"))["entorno"]["dispositivo"] == "cpu"
    md_p = er.guardar_resultado("prefijos_c6", prefijos, er.markdown_prefijos(prefijos), tmp_path)
    assert "Con prefijos" in md_p.read_text(encoding="utf-8")
