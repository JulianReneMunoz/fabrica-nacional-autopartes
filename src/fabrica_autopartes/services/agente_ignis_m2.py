"""Agente IGNIS del Módulo 2 (Fanalca - Grupo 11): router por reglas, memoria por hilo, consulta determinista
a datos estructurados y blindaje de los fragmentos recuperados. Se usa a través de ``ServicioAsistente``."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from langgraph.store.base import BaseStore
from pydantic import BaseModel, Field

from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm.extractivo import RECHAZO
from fabrica_autopartes.llm.salvaguardas import detectar_inyeccion
from fabrica_autopartes.pipelines.texto import (
    MARCA_PERFIL,
    anonimizar_datos_personales,
    omitir_autopresentaciones,
)
from fabrica_autopartes.repositories.auditoria import RepositorioMemoriaIgnis
from fabrica_autopartes.services.preferencias import (
    consultar_preferencias,
    decidir_memoria,
    descarta_datos_personales,
    describir_preferencias,
    extraer_preferencias,
    guardar_preferencias,
    pregunta_dato_personal,
)

RAIZ_REPO = Path(__file__).resolve().parents[3]

# TODO(PR b, #44 del plan): reemplazar por el ``user_id`` seudónimo de la sesión (HMAC del alias). Mientras no
# haya sesiones, todas las consultas de /ignis/stream comparten este usuario de demostración.
USUARIO_DEMO = "demo"

# Ruta memoria_store: orden de recordar que no trae preferencias del vocabulario cerrado.
AVISO_LEY_1581 = (
    "IGNIS no guarda nombres, empresas ni datos de contacto (Ley 1581 de 2012); solo recuerda "
    "preferencias de una lista cerrada: área laboral, formato de respuesta y línea de producto."
)

# Ruta directo: preguntas por datos personales del propio usuario («¿Cómo me llamo?»).
AVISO_DATO_PERSONAL = (
    "Esa es información personal, y por cuidar tu privacidad no la guardo ni la consulto. Yo solo te doy "
    "información de Fanalca: sus negocios, las motocicletas Honda, las autopartes y su trabajo en "
    "sostenibilidad. ¿Te ayudo con algo de eso?"
)

# Adjuntos fijos servidos como estáticos del visor (web/public → web/dist, montado en /app). Son recursos
# ilustrativos generados por scripts/generar_assets_ignis.py: se marcan con origen «demostrativo».
ADJUNTO_PLANO_2D = "/app/assets/blueprint_2d.png"
ADJUNTO_COTIZACION_PDF = "/app/assets/resumen_cotizacion.pdf"

# Contrato con el frontend (web/src/ignisCliente.ts): cada adjunto es un objeto, no una cadena.
ADJUNTOS: dict[str, dict[str, str]] = {
    "plano": {
        "url": ADJUNTO_PLANO_2D,
        "titulo": "Plano técnico 2D",
        "tipo": "plano",
        "formato": "PNG",
        "origen": "demostrativo",
    },
    "cotizacion": {
        "url": ADJUNTO_COTIZACION_PDF,
        "titulo": "Presupuesto / Cotización",
        "tipo": "cotizacion",
        "formato": "PDF",
        "origen": "demostrativo",
    },
}


def _adjunto(clave: str) -> dict[str, str]:
    """Copia del adjunto: quien la reciba no puede alterar el diccionario compartido."""
    return dict(ADJUNTOS[clave])


# --- 1. Esquemas Pydantic de la consulta determinista a datos estructurados (función, no @tool) ---
class ConsultaDatosFanalcaInput(BaseModel):
    tipo_consulta: Literal["ficha_moto", "estadisticas_corpus", "unidades_negocio"] = Field(
        description="Tipo de dato estructurado exacto a consultar en los catálogos YAML/JSON de Fanalca."
    )
    filtro: str = Field(default="cb160f", description="Identificador o filtro opcional de consulta.")


class ResultadoEstructuradoFanalca(BaseModel):
    fuente_archivo: str
    datos_exactos: dict[str, Any]
    verificado: bool = True


def consultar_datos_estructurados_fanalca(entrada: ConsultaDatosFanalcaInput) -> ResultadoEstructuradoFanalca:
    """Consulta determinista sobre archivos YAML/JSON de Fanalca sin inventar cifras."""
    if entrada.tipo_consulta == "ficha_moto":
        ruta = RAIZ_REPO / "data" / "catalogo" / "motos_honda.yaml"
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        return ResultadoEstructuradoFanalca(
            fuente_archivo="data/catalogo/motos_honda.yaml", datos_exactos=datos
        )

    if entrada.tipo_consulta == "estadisticas_corpus":
        ruta = RAIZ_REPO / "data" / "gold" / "estadisticas.json"
        datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        return ResultadoEstructuradoFanalca(fuente_archivo="data/gold/estadisticas.json", datos_exactos=datos)

    ruta_etapas = RAIZ_REPO / "data" / "gold" / "metricas_etapas.json"
    datos = json.loads(ruta_etapas.read_text(encoding="utf-8")) if ruta_etapas.exists() else {}
    return ResultadoEstructuradoFanalca(fuente_archivo="data/gold/metricas_etapas.json", datos_exactos=datos)


# --- 2. Blindaje contra inyección indirecta en los fragmentos recuperados ---
PATRONES_INYECCION_DOCUMENTAL = [
    re.compile(r"ignora\s+(todas\s+)?las\s+instrucciones\s+anteriores", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?(the\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(of\s+)?the\s+above", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
]
# Apertura o cierre del delimitador (también parcial, sin «>»): un fragmento no puede cerrar el bloque pasivo.
PATRON_ETIQUETA_PASIVA = re.compile(r"<\s*/?\s*datos_pasivos_documento\b[^<>]*>?", re.IGNORECASE)
MARCA_INSTRUCCION = "[INSTRUCCIÓN OCULTA NEUTRALIZADA POR BLINDAJE RAG]"
MARCA_ETIQUETA = "[ETIQUETA NEUTRALIZADA]"


def neutralizar_fragmento_rag(texto: str, max_caracteres: int | None = None) -> tuple[str, bool]:
    """Neutraliza instrucciones ocultas y delimitadores incrustados; luego recorta a ``max_caracteres``.

    Devuelve el texto sin envolver (apto para mostrarse al usuario) y si se activó el blindaje. El recorte va
    después de neutralizar: un corte previo podría partir un patrón y dejarlo sin detectar.
    """
    alerta = False
    texto_limpio = texto
    for patron in PATRONES_INYECCION_DOCUMENTAL:
        texto_limpio, n = patron.subn(MARCA_INSTRUCCION, texto_limpio)
        alerta = alerta or n > 0
    texto_limpio, n = PATRON_ETIQUETA_PASIVA.subn(MARCA_ETIQUETA, texto_limpio)
    alerta = alerta or n > 0
    if max_caracteres is not None and len(texto_limpio) > max_caracteres:
        texto_limpio = texto_limpio[:max_caracteres] + "..."
    return texto_limpio, alerta


def sanitizar_fragmento_rag(texto: str, doc_id: str, max_caracteres: int | None = None) -> tuple[str, bool]:
    """Delimita el documento como dato pasivo (para un LLM) tras neutralizarlo y recortarlo.

    El recorte ocurre antes de envolver, para no cortar el delimitador de cierre.
    """
    texto_limpio, alerta = neutralizar_fragmento_rag(texto, max_caracteres)
    bloque_pasivo = f"<datos_pasivos_documento id='{doc_id}'>\n{texto_limpio}\n</datos_pasivos_documento>"
    return bloque_pasivo, alerta


# --- 3. Router por reglas de palabras clave (ruta, puntaje fijo y justificación) ---
class DecisionRouter(BaseModel):
    ruta: Literal["directo", "memoria_store", "herramienta_estructurada", "rag_documental", "mixto"]
    score_confianza: float
    justificacion: str


def decidir_ruta_router(mensaje: str) -> DecisionRouter:
    texto = mensaje.strip().lower()

    # 1. Saludos o preguntas triviales -> sin búsqueda BM25 ni consulta de datos estructurados
    if (
        re.match(r"^(hola|buenos\s+d[ií]as|buenas\s+tardes|buenas\s+noches|qu[eé]\s+tal|gracias|ok)\b", texto)
        and len(texto) < 35
    ):
        return DecisionRouter(
            ruta="directo",
            score_confianza=0.99,
            justificacion="Saludo o cortesía trivial; respuesta directa sin invocar RAG ni tools.",
        )

    # 1b. Preguntas por datos personales del propio usuario («¿Cómo me llamo?»): no se guardan (Ley 1581),
    # así que se responde el aviso sin buscar en el corpus.
    if pregunta_dato_personal(mensaje):
        return DecisionRouter(
            ruta="directo",
            score_confianza=0.97,
            justificacion="Pregunta por un dato personal que IGNIS no guarda (Ley 1581); aviso sin RAG.",
        )

    # 2. Memoria de largo plazo: solo con una orden explícita que traiga algo que guardar (o una
    # autopresentación, para explicar la Ley 1581) o con la consulta «¿qué preferencias tengo?».
    # «Prefiero» o «me interesa» por sí solos no desvían la pregunta.
    if modo := decidir_memoria(mensaje):
        return DecisionRouter(
            ruta="memoria_store",
            score_confianza=0.95,
            justificacion=(
                "Orden explícita de recordar preferencias en el Store de largo plazo."
                if modo == "guardar"
                else "Consulta de las preferencias del usuario en el Store de largo plazo (search)."
            ),
        )

    tiene_estructurado = any(
        k in texto
        for k in [
            "csv",
            "json",
            "yaml",
            "estadística",
            "estadisticas",
            "unidades",
            "cilindraje",
            "cb 160f",
            "cb160f",
            "fragmentos totales",
            "cuántos",
            "cuantas",
        ]
    )
    tiene_rag = any(
        k in texto
        for k in [
            "política",
            "politica",
            "calidad",
            "sostenibilidad",
            "fanalvías",
            "fanalvias",
            "fundación",
            "fundacion",
            "autopartes",
            "corpus",
            "documento",
            "sede",
            "historia",
            "fanalca",
        ]
    )

    if (tiene_estructurado and tiene_rag) or "compara" in texto:
        return DecisionRouter(
            ruta="mixto",
            score_confianza=0.92,
            justificacion=(
                "Consulta híbrida que exige cruzar catálogo estructurado + evidencia documental RAG."
            ),
        )
    if tiene_estructurado:
        return DecisionRouter(
            ruta="herramienta_estructurada",
            score_confianza=0.94,
            justificacion="Consulta numérica/ficha técnica atendida con una consulta determinista.",
        )
    return DecisionRouter(
        ruta="rag_documental",
        score_confianza=0.88,
        justificacion="Consulta de conocimiento empresarial dirigida al recuperador documental con citas.",
    )


# --- 4. Agente IGNIS ---
def _cita(frag: Fragmento) -> dict[str, str]:
    return {"id": frag.id, "url": frag.url, "titulo": frag.titulo, "origen": frag.origen}


def _procedencia(res: ResultadoEstructuradoFanalca) -> str:
    """Origen de los datos estructurados mostrados: URL de las fuentes del catálogo u orígenes del corpus."""
    datos = res.datos_exactos
    fuentes = datos.get("fuentes")
    if isinstance(fuentes, dict):
        urls = sorted({f["url"] for f in fuentes.values() if isinstance(f, dict) and f.get("url")})
        if urls:
            return f"Origen: catálogo curado con fuente y estado por campo ({', '.join(urls)})."
    origenes = datos.get("origenes")
    if isinstance(origenes, dict) and origenes:
        n_urls = len(datos.get("urls") or [])
        return f"Origen: corpus Gold ({', '.join(sorted(origenes))}) de {n_urls} URL."
    return f"Origen: demostrativo (`{res.fuente_archivo}` sin URL de fuente)."


class AgenteIgnisM2:
    """Turno de IGNIS. No guarda nombres, empresas ni datos de contacto (Ley 1581 de 2012): los mensajes del
    usuario se registran sin autopresentaciones (nombre, empresa) ni correos, teléfonos o documentos."""

    def __init__(
        self, base: BaseConocimiento, memoria: RepositorioMemoriaIgnis, store: BaseStore | None = None
    ) -> None:
        self.kb = base
        self.memoria = memoria
        # Store de largo plazo (ADR-033): preferencias por usuario en el namespace ("preferencias", user_id).
        self.store = store

    def _buscar_fragmentos(self, consulta: str, k: int) -> list[Fragmento]:
        return [r.fragmento for r in self.kb.buscar(consulta, k=k)]

    def _turno_memoria(self, mensaje: str, user_id: str) -> str:
        """Guarda o consulta preferencias del usuario; nunca guarda texto libre ni datos personales."""
        if self.store is None:
            return "La memoria de largo plazo no está disponible en este momento."
        if decidir_memoria(mensaje) == "consultar":
            guardadas = consultar_preferencias(self.store, user_id)
            if not guardadas:
                return "No hay preferencias guardadas para este usuario."
            return f"Preferencias guardadas: {describir_preferencias(guardadas)}."
        prefs = extraer_preferencias(mensaje)
        if not prefs:
            return f"No se guardó ninguna preferencia. {AVISO_LEY_1581}"
        guardar_preferencias(self.store, user_id, prefs)
        respuesta = f"Preferencias guardadas para próximas conversaciones: {describir_preferencias(prefs)}."
        if descarta_datos_personales(mensaje):
            respuesta += " No se guardan nombres, empresas ni datos de contacto (Ley 1581 de 2012)."
        return respuesta

    def ejecutar_turno(self, mensaje: str, thread_id: str, user_id: str = USUARIO_DEMO) -> dict[str, Any]:
        # Salvaguarda de entrada directa
        if detectar_inyeccion(mensaje):
            respuesta = (
                "Solicitud bloqueada por el blindaje de seguridad de IGNIS: "
                "intento de manipulación de instrucciones detectado."
            )
            return {
                "respuesta": respuesta,
                "thread_id": thread_id,
                "ruta_router": "bloqueado_salvaguarda",
                "citas": [],
                "archivos_adjuntos": [],
                "blindaje_activado": True,
                "bloqueada": True,
            }

        decision = decidir_ruta_router(mensaje)

        citas: list[dict[str, str]] = []
        archivos: list[dict[str, str]] = []
        blindaje_indirecto = False

        if decision.ruta == "directo" and pregunta_dato_personal(mensaje):
            respuesta = AVISO_DATO_PERSONAL
        elif decision.ruta == "directo":
            respuesta = (
                "Hola. Soy IGNIS, la unidad de atención de Fábrica Nacional de Autopartes (Fanalca). "
                "¿Deseas consultar el corpus documental, las fichas técnicas o descargar el plano 2D "
                "o la cotización de ejemplo?"
            )

        elif decision.ruta == "memoria_store":
            respuesta = self._turno_memoria(mensaje, user_id)

        elif decision.ruta == "herramienta_estructurada":
            tipo: Literal["ficha_moto", "estadisticas_corpus"] = (
                "ficha_moto"
                if any(w in mensaje.lower() for w in ["moto", "cb", "cilindraje"])
                else "estadisticas_corpus"
            )
            res_tool = consultar_datos_estructurados_fanalca(ConsultaDatosFanalcaInput(tipo_consulta=tipo))
            resumen_json = json.dumps(res_tool.datos_exactos, ensure_ascii=False)[:420]
            respuesta = (
                "Dato exacto leído mediante consulta determinista con validación Pydantic "
                f"desde `{res_tool.fuente_archivo}`: {resumen_json}. {_procedencia(res_tool)}"
            )

        elif decision.ruta == "mixto":
            res_tool = consultar_datos_estructurados_fanalca(
                ConsultaDatosFanalcaInput(tipo_consulta="estadisticas_corpus")
            )
            fragmentos = self._buscar_fragmentos(mensaje, k=2)
            evidencias = []
            for frag in fragmentos:
                texto_visible, alerta = neutralizar_fragmento_rag(frag.texto, max_caracteres=180)
                blindaje_indirecto = blindaje_indirecto or alerta
                citas.append(_cita(frag))
                evidencias.append(f"[{frag.id}] ({frag.url}): {texto_visible}")
            cifras = (
                f"Enrutamiento Mixto ejecutado. 1) Cifras estructuradas (`{res_tool.fuente_archivo}`): "
                f"{json.dumps(res_tool.datos_exactos, ensure_ascii=False)[:220]}. {_procedencia(res_tool)} "
            )
            if evidencias:
                respuesta = cifras + f"2) Evidencia documental en corpus Fanalca: {' | '.join(evidencias)}"
                archivos.extend([_adjunto("plano"), _adjunto("cotizacion")])
            else:
                # Sin evidencia no se afirma nada documental ni se adjuntan recursos.
                respuesta = cifras + f"2) Evidencia documental: {RECHAZO}"

        else:  # rag_documental
            fragmentos = self._buscar_fragmentos(mensaje, k=3)
            if not fragmentos:
                respuesta = RECHAZO
            else:
                partes = []
                for frag in fragmentos:
                    texto_visible, alerta = neutralizar_fragmento_rag(frag.texto, max_caracteres=220)
                    blindaje_indirecto = blindaje_indirecto or alerta
                    citas.append(_cita(frag))
                    partes.append(f"Según [{frag.id}] ({frag.titulo}): {texto_visible}")
                respuesta = " ".join(partes)
                bajo = mensaje.lower()
                if any(k in bajo for k in ["plano", "3d", "modelo", "descarga", "cotiza"]):
                    archivos.append(_adjunto("plano"))
                if any(k in bajo for k in ["cotiza", "presupuesto"]):
                    archivos.append(_adjunto("cotizacion"))

        # Ley 1581: solo se limpia el mensaje del usuario; la respuesta sale del corpus y las herramientas.
        # En la ruta de perfil se guarda solo el marcador; en las demás se omiten autopresentaciones,
        # correos, teléfonos y documentos.
        if decision.ruta == "memoria_store" and decidir_memoria(mensaje) == "guardar":
            mensaje_guardado = MARCA_PERFIL
        else:
            mensaje_guardado = anonimizar_datos_personales(omitir_autopresentaciones(mensaje))
        self.memoria.guardar_turno(thread_id, "user", mensaje_guardado)
        self.memoria.guardar_turno(thread_id, "assistant", respuesta, {"ruta": decision.ruta, "citas": citas})

        return {
            "respuesta": respuesta,
            "thread_id": thread_id,
            "ruta_router": decision.ruta,
            "score_router": decision.score_confianza,
            "justificacion_router": decision.justificacion,
            "citas": citas,
            "archivos_adjuntos": archivos,
            "blindaje_activado": blindaje_indirecto,
            "bloqueada": False,
        }
