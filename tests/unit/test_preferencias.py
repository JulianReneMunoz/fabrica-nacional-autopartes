"""Preferencias de largo plazo (ADR-033): vocabularios cerrados, intención de memoria y aislamiento
por usuario."""

from __future__ import annotations

import pytest
from langgraph.store.memory import InMemoryStore

from fabrica_autopartes.services.preferencias import (
    consultar_preferencias,
    decidir_memoria,
    descarta_datos_personales,
    describir_preferencias,
    extraer_preferencias,
    guardar_preferencias,
    pregunta_dato_personal,
)

CASO_2A = (
    "Trabajo en compras de repuestos, prefiero respuestas breves y me interesan las motocicletas. Recuérdalo."
)


def test_caso_2a_extrae_las_tres_preferencias_canonicas() -> None:
    assert extraer_preferencias(CASO_2A) == {
        "area_laboral": "compras de repuestos",
        "formato_respuesta": "breve",
        "linea_producto": "motocicletas",
    }
    assert decidir_memoria(CASO_2A) == "guardar"
    assert not descarta_datos_personales(CASO_2A)


def test_autopresentacion_con_nombre_y_empresa_no_extrae_nada() -> None:
    mensaje = "Me llamo Ana y trabajo en Empresa X. Recuérdalo."
    assert extraer_preferencias(mensaje) == {}
    assert decidir_memoria(mensaje) == "guardar"  # para responder el aviso de la Ley 1581
    assert descarta_datos_personales(mensaje)


@pytest.mark.parametrize(
    ("mensaje", "esperado"),
    [
        ("Trabajo en el área de servicio técnico, recuérdalo", {"area_laboral": "servicio técnico"}),
        (
            "Trabajo en LOGÍSTICA y prefiero respuestas detalladas, guárdalo",
            {"area_laboral": "logística", "formato_respuesta": "detallada"},
        ),
        ("Me interesan los repuestos, recuerda que", {"linea_producto": "repuestos"}),
        ("Trabajo en Empresa X, recuérdalo", {}),
        ("Me interesan los aviones, recuérdalo", {}),
    ],
)
def test_solo_valores_del_vocabulario_cerrado(mensaje: str, esperado: dict[str, str]) -> None:
    assert extraer_preferencias(mensaje) == esperado


def test_datos_de_contacto_nunca_llegan_a_las_preferencias() -> None:
    prefs = extraer_preferencias(
        "Prefiero respuestas breves, escribe a ana@gmail.com o al 3001234567. Recuérdalo."
    )
    assert prefs == {"formato_respuesta": "breve"}
    assert all("@" not in v and not any(c.isdigit() for c in v) for v in prefs.values())


@pytest.mark.parametrize(
    "mensaje",
    [
        "Prefiero respuestas breves, guárdalo",
        "Prefiero respuestas breves, guárdala",
        "Guarda esto: prefiero respuestas breves",
        "Guarda que prefiero respuestas breves",
        "Guarda mis preferencias: prefiero respuestas breves",
        "Recuerda que prefiero respuestas breves",
    ],
)
def test_ordenes_explicitas_de_guardar(mensaje: str) -> None:
    assert decidir_memoria(mensaje) == "guardar"


@pytest.mark.parametrize(
    "mensaje",
    [
        "¿Fanalca guarda relación con Honda?",
        "Recuerda que la garantía cubre motores, ¿cuánto dura?",
        "Me interesan las motocicletas, ¿qué modelos hay?",
        "Prefiero respuestas breves",
    ],
)
def test_sin_orden_o_sin_nada_que_guardar_no_activa_la_memoria(mensaje: str) -> None:
    assert decidir_memoria(mensaje) is None


def test_consulta_de_preferencias() -> None:
    assert decidir_memoria("¿Qué preferencias tengo guardadas?") == "consultar"


@pytest.mark.parametrize(
    "mensaje", ["¿Dónde trabajo?", "¿Dónde trabajo yo?", "¿Cómo me llamo?", "¿Cuál es mi nombre?"]
)
def test_preguntas_por_datos_personales(mensaje: str) -> None:
    assert pregunta_dato_personal(mensaje)


@pytest.mark.parametrize(
    "mensaje", ["¿Dónde trabajó el fundador de Fanalca?", "¿Cómo se llamaba antes la empresa?"]
)
def test_preguntas_sobre_fanalca_no_son_datos_personales(mensaje: str) -> None:
    assert not pregunta_dato_personal(mensaje)


def test_store_aisla_usuarios_aunque_compartan_prefijo() -> None:
    store = InMemoryStore()
    guardar_preferencias(store, "u1", {"linea_producto": "motocicletas"})
    guardar_preferencias(store, "u10", {"linea_producto": "autopartes", "formato_respuesta": "detallada"})
    assert consultar_preferencias(store, "u1") == {"linea_producto": "motocicletas"}
    assert consultar_preferencias(store, "u10") == {
        "linea_producto": "autopartes",
        "formato_respuesta": "detallada",
    }
    assert consultar_preferencias(store, "u2") == {}


def test_descripcion_en_orden_fijo() -> None:
    texto = describir_preferencias({"linea_producto": "motocicletas", "area_laboral": "compras"})
    assert texto == "área laboral: compras; línea de producto: motocicletas"


def test_user_id_vacio_se_rechaza() -> None:
    with pytest.raises(ValueError):
        consultar_preferencias(InMemoryStore(), "")
