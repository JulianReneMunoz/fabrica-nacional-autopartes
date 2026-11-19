"""Agente IGNIS del Módulo 2 (Fanalca - Grupo 11): moderación antes del router, router por reglas, memoria
por hilo, herramienta ``@tool`` determinista a datos estructurados (ficha de motos, ficha corporativa y
estadísticas) y blindaje de los fragmentos recuperados. Se usa a través de ``ServicioAsistente``.

El texto de la respuesta es para el cliente: oraciones completas, sin identificadores, URL, JSON ni jerga. La
evidencia técnica (citas, fuentes de datos, ruta, puntaje, blindaje y moderación) viaja aparte, en el
resultado.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from langchain_core.tools import tool
from langgraph.store.base import BaseStore
from pydantic import BaseModel, Field

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.knowledge.base import BaseConocimiento
from fabrica_autopartes.llm.extractivo import RECHAZO
from fabrica_autopartes.pipelines.sinonimos import expandir_consulta
from fabrica_autopartes.pipelines.texto import (
    MARCA_PERFIL,
    anonimizar_datos_personales,
    omitir_autopresentaciones,
    pulir_respuesta,
    sin_tildes,
)
from fabrica_autopartes.repositories.auditoria import RepositorioMemoriaIgnis
from fabrica_autopartes.services.cortesia import (
    AUTOPRESENTACION_SIN_PREFERENCIAS,
    MEMORIA_NO_DISPONIBLE,
    SIN_PREFERENCIAS,
    clasificar_cortesia,
    responder_cortesia,
    texto_preferencias_consultadas,
    texto_preferencias_guardadas,
)
from fabrica_autopartes.services.ficha_fanalca import (
    ARCHIVO_FICHA,
    TEXTO_NO_PUBLICADO,
    FuenteDato,
    SeccionFicha,
    cargar_ficha,
    redactar_ficha,
    seccion_ficha,
)
from fabrica_autopartes.services.moderacion import moderar
from fabrica_autopartes.services.preferencias import (
    consultar_preferencias,
    decidir_memoria,
    descarta_datos_personales,
    extraer_preferencias,
    guardar_preferencias,
    pregunta_dato_personal,
    tiene_autopresentacion,
)
from fabrica_autopartes.services.redactor_ignis import (
    AVISO_BLINDAJE,
    CIERRE_PLANO,
    SEGUIMIENTO_DOCUMENTAL,
    SEGUIMIENTO_FICHA,
    SEGUIMIENTO_MIXTO,
    fuentes_datos_estadisticas,
    fuentes_datos_moto,
    redactar_documental,
    redactar_estadisticas,
    redactar_ficha_moto,
)

RAIZ_REPO = Path(__file__).resolve().parents[3]
NORMATIVA_DATOS = "Ley 1581 de 2012"

# Ruta directo: preguntas por datos personales del propio usuario («¿Cómo me llamo?»).
AVISO_DATO_PERSONAL = (
    "Esa es información personal, y por cuidar tu privacidad no la guardo ni la consulto. Yo solo te doy "
    "información de Fanalca: sus negocios, las motocicletas Honda, las autopartes y su trabajo en "
    "sostenibilidad. ¿Te ayudo con algo de eso?"
)
SIN_PREFERENCIAS_RECONOCIDAS = (
    "No encontré una preferencia que pueda guardar. Puedo recordar cómo prefieres las respuestas, tu área de "
    "trabajo o qué productos te interesan."
)
# Marca que reemplaza el mensaje del cliente en el historial y en el título del hilo cuando se bloquea.
MARCA_MODERADO = "[mensaje moderado: {categoria}]"

# Adjuntos fijos servidos como estáticos del visor (web/public → web/dist, montado en /app). Son recursos
# ilustrativos generados por scripts/generar_assets_ignis.py: se marcan con origen «demostrativo». IGNIS no
# tiene precios, cotizaciones ni catálogo de repuestos: no hay adjunto de cotización.
ADJUNTO_PLANO_2D = "/app/assets/blueprint_2d.png"

# Contrato con el frontend (web/src/ignisCliente.ts): cada adjunto es un objeto, no una cadena.
ADJUNTOS: dict[str, dict[str, str]] = {
    "plano": {
        "url": ADJUNTO_PLANO_2D,
        "titulo": "Plano técnico 2D",
        "tipo": "plano",
        "formato": "PNG",
        "origen": "demostrativo",
    },
}
_PIDE_PLANO = ("plano", "3d", "modelo", "descarga")


def _adjunto(clave: str) -> dict[str, str]:
    """Copia del adjunto: quien la reciba no puede alterar el diccionario compartido."""
    return dict(ADJUNTOS[clave])


# --- 1. Herramienta determinista a datos estructurados: @tool de LangChain con esquema Pydantic ---
TipoConsulta = Literal["ficha_moto", "estadisticas_corpus", "unidades_negocio", "ficha_empresa"]


class ConsultaDatosFanalcaInput(BaseModel):
    tipo_consulta: TipoConsulta = Field(
        description="Tipo de dato estructurado exacto a consultar en los catálogos YAML/JSON de Fanalca."
    )
    filtro: str = Field(default="cb160f", description="Identificador o filtro opcional de consulta.")


class ResultadoEstructuradoFanalca(BaseModel):
    fuente_archivo: str
    datos_exactos: dict[str, Any]
    verificado: bool = True


def _leer_datos_estructurados(tipo_consulta: TipoConsulta) -> ResultadoEstructuradoFanalca:
    """Lectura determinista sobre archivos YAML/JSON de Fanalca sin inventar cifras."""
    if tipo_consulta == "ficha_moto":
        ruta = RAIZ_REPO / "data" / "catalogo" / "motos_honda.yaml"
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        return ResultadoEstructuradoFanalca(
            fuente_archivo="data/catalogo/motos_honda.yaml", datos_exactos=datos
        )

    if tipo_consulta == "ficha_empresa":
        return ResultadoEstructuradoFanalca(
            fuente_archivo=ARCHIVO_FICHA, datos_exactos=cargar_ficha().model_dump()
        )

    if tipo_consulta == "estadisticas_corpus":
        ruta = RAIZ_REPO / "data" / "gold" / "estadisticas.json"
        datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        return ResultadoEstructuradoFanalca(fuente_archivo="data/gold/estadisticas.json", datos_exactos=datos)

    ruta_etapas = RAIZ_REPO / "data" / "gold" / "metricas_etapas.json"
    datos = json.loads(ruta_etapas.read_text(encoding="utf-8")) if ruta_etapas.exists() else {}
    return ResultadoEstructuradoFanalca(fuente_archivo="data/gold/metricas_etapas.json", datos_exactos=datos)


@tool(
    "consultar_datos_estructurados_fanalca",
    args_schema=ConsultaDatosFanalcaInput,
    response_format="content_and_artifact",
)
def consultar_datos_estructurados_fanalca(
    tipo_consulta: TipoConsulta, filtro: str = "cb160f"
) -> tuple[str, ResultadoEstructuradoFanalca]:
    """Consulta los datos estructurados de Fanalca (ficha de motos, ficha corporativa y estadísticas del
    corpus) y devuelve los datos exactos con su archivo de origen, sin calcular ni redactar."""
    resultado = _leer_datos_estructurados(tipo_consulta)
    return resultado.model_dump_json(), resultado


def _consultar_datos(tipo_consulta: TipoConsulta) -> ResultadoEstructuradoFanalca:
    """Invoca la herramienta como lo hace un agente (llamada de herramienta) y devuelve su artefacto: el
    modelo Pydantic con los datos exactos, sin pasar por JSON."""
    mensaje = consultar_datos_estructurados_fanalca.invoke(
        {
            "type": "tool_call",
            "id": f"ignis-{tipo_consulta}",
            "name": consultar_datos_estructurados_fanalca.name,
            "args": {"tipo_consulta": tipo_consulta},
        }
    )
    return ResultadoEstructuradoFanalca.model_validate(mensaje.artifact)


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


_CLAVES_ESTRUCTURADO = [
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
_CLAVES_RAG = [
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
_CLAVES_MOTO = ("moto", "cb", "cilindraje", "freno", "llanta")


def decidir_ruta_router(mensaje: str) -> DecisionRouter:
    texto = mensaje.strip().lower()

    # 1. Cortesía (saludos, gracias, despedidas, «¿eres humano?», fuera de tema): textos fijos sin búsqueda.
    if categoria := clasificar_cortesia(mensaje):
        return DecisionRouter(
            ruta="directo",
            score_confianza=0.99,
            justificacion=f"Cortesía ({categoria}); respuesta directa sin invocar RAG ni tools.",
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

    # 2b. Precios, cotizaciones, inventario, NIT u horarios: IGNIS no tiene esa información (texto fijo).
    seccion = seccion_ficha(mensaje)
    if seccion == "no_publicado":
        return DecisionRouter(
            ruta="directo",
            score_confianza=0.97,
            justificacion="Precio, cotización o dato no publicado por Fanalca; texto fijo sin búsqueda.",
        )

    tiene_estructurado = any(k in texto for k in _CLAVES_ESTRUCTURADO)
    tiene_rag = any(k in texto for k in _CLAVES_RAG)

    if (tiene_estructurado and tiene_rag) or "compara" in texto:
        return DecisionRouter(
            ruta="mixto",
            score_confianza=0.92,
            justificacion=(
                "Consulta híbrida que exige cruzar catálogo estructurado + evidencia documental RAG."
            ),
        )
    if seccion is not None:
        return DecisionRouter(
            ruta="herramienta_estructurada",
            score_confianza=0.94,
            justificacion=f"Dato corporativo de la ficha de Fanalca (sección {seccion}).",
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


# --- 4. Búsqueda de IGNIS: sinónimos, exclusiones y preferencia por el español (no cambia el M1) ---
RUTA_EXCLUSIONES = RAIZ_PROYECTO / "config" / "ignis_exclusiones.yaml"
_PALABRAS_INGLES = {"the", "what", "is", "are", "of", "and", "how", "where", "which", "does"}


@lru_cache(maxsize=2)
def documentos_excluidos(ruta: Path = RUTA_EXCLUSIONES) -> frozenset[str]:
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    return frozenset(entrada["id"] for entrada in (datos or {}).get("documentos", []))


def _consulta_en_ingles(consulta: str) -> bool:
    palabras = re.findall(r"[a-z]+", sin_tildes(consulta))
    return sum(p in _PALABRAS_INGLES for p in palabras) >= 2


def filtrar_para_ignis(consulta: str, fragmentos: list[Fragmento], k: int) -> list[Fragmento]:
    """Quita los documentos excluidos y, con una consulta en español, usa fragmentos en inglés solo si no hay
    ninguno en español."""
    excluidos = documentos_excluidos()
    utiles = [f for f in fragmentos if f.documento_id not in excluidos]
    if not _consulta_en_ingles(consulta) and any(f.idioma == "es" for f in utiles):
        utiles = [f for f in utiles if f.idioma == "es"]
    return utiles[:k]


# --- 5. Agente IGNIS ---
def _cita(frag: Fragmento) -> dict[str, str]:
    return {"id": frag.id, "url": frag.url, "titulo": frag.titulo, "origen": frag.origen}


def _cita_de_fuente(fuente: FuenteDato) -> dict[str, str]:
    return {"id": fuente.fragmento_id, "url": fuente.url, "titulo": fuente.titulo, "origen": fuente.origen}


def _citas_de_fuentes(fuentes: list[FuenteDato]) -> list[dict[str, str]]:
    citas: list[dict[str, str]] = []
    for fuente in fuentes:
        if all(c["id"] != fuente.fragmento_id for c in citas):
            citas.append(_cita_de_fuente(fuente))
    return citas


def _fuentes_datos_ficha(fuentes: list[FuenteDato]) -> dict[str, Any]:
    return {
        "archivo": ARCHIVO_FICHA,
        "descripcion": "Ficha corporativa de Fanalca construida a partir del corpus, con la fuente de cada "
        "dato",
        "origen": ", ".join(sorted({f.origen for f in fuentes})) or "demostrativo",
        "urls": sorted({f.url for f in fuentes}),
    }


def _como_texto(prefs: Mapping[Any, str]) -> dict[str, str]:
    """Preferencias con claves ``str`` (las del Store son ``Literal``) para los textos de cortesía."""
    return {str(clave): valor for clave, valor in prefs.items()}


def _es_pregunta_de_moto(mensaje: str) -> bool:
    bajo = mensaje.lower()
    return any(w in bajo for w in _CLAVES_MOTO)


class AgenteIgnisM2:
    """Turno de IGNIS. No guarda nombres, empresas ni datos de contacto (Ley 1581 de 2012): los mensajes del
    usuario se registran sin autopresentaciones (nombre, empresa) ni correos, teléfonos o documentos, y los
    mensajes bloqueados por la moderación se registran solo con su categoría."""

    def __init__(
        self, base: BaseConocimiento, memoria: RepositorioMemoriaIgnis, store: BaseStore | None = None
    ) -> None:
        self.kb = base
        self.memoria = memoria
        # Store de largo plazo (ADR-033): preferencias por usuario en el namespace ("preferencias", user_id).
        self.store = store

    def _buscar_fragmentos(self, consulta: str, k: int) -> list[Fragmento]:
        """Búsqueda de IGNIS sobre el buscador común: se piden más candidatos para poder filtrar."""
        candidatos = [r.fragmento for r in self.kb.buscar(expandir_consulta(consulta), k=k * 4 + 6)]
        return filtrar_para_ignis(consulta, candidatos, k)

    def _preferencias(self, user_id: str) -> dict[str, str]:
        if self.store is None:
            return {}
        return _como_texto(consultar_preferencias(self.store, user_id))

    def _turno_memoria(self, mensaje: str, user_id: str) -> tuple[str, bool]:
        """Guarda o consulta preferencias del usuario; nunca guarda texto libre ni datos personales. Devuelve
        el texto y si se avisó de datos personales descartados (para ``normativa``)."""
        if self.store is None:
            return MEMORIA_NO_DISPONIBLE, False
        if decidir_memoria(mensaje) == "consultar":
            guardadas = consultar_preferencias(self.store, user_id)
            if not guardadas:
                return SIN_PREFERENCIAS, False
            return texto_preferencias_consultadas(_como_texto(guardadas)), False
        prefs = extraer_preferencias(mensaje)
        if not prefs:
            if tiene_autopresentacion(mensaje):
                return AUTOPRESENTACION_SIN_PREFERENCIAS, True
            return SIN_PREFERENCIAS_RECONOCIDAS, False
        guardar_preferencias(self.store, user_id, prefs)
        descartados = descarta_datos_personales(mensaje)
        return texto_preferencias_guardadas(_como_texto(prefs), descartados), descartados

    def _documental(
        self, mensaje: str, k: int, max_oraciones: int, entradas: tuple[str, ...] | None = None
    ) -> tuple[str, list[dict[str, str]], bool]:
        """Texto documental (vacío si no hay evidencia), citas de los fragmentos usados y alerta del
        blindaje."""
        fragmentos = self._buscar_fragmentos(mensaje, k=k)
        visibles, alerta = [], False
        for frag in fragmentos:
            texto_visible, alerta_frag = neutralizar_fragmento_rag(frag.texto)
            visibles.append(texto_visible)
            alerta = alerta or alerta_frag
        texto, usados = redactar_documental(mensaje, fragmentos, visibles, max_oraciones, entradas)
        return texto, [_cita(f) for f in usados], alerta

    def ejecutar_turno(self, mensaje: str, thread_id: str, user_id: str) -> dict[str, Any]:
        """Turno de IGNIS. ``user_id`` es el usuario seudónimo de la sesión (ADR-033): no tiene valor por
        defecto para que ningún llamador comparta preferencias por omisión."""
        historial = self.memoria.obtener_historial(thread_id)
        semilla = f"{thread_id}:{len(historial) // 2}"

        # Moderación antes del router (caso 6): sin búsqueda, herramientas ni citas; se guarda la categoría.
        moderacion = moderar(mensaje, historial, semilla)
        if moderacion.bloqueada and moderacion.categoria is not None:
            categoria = moderacion.categoria
            marca = MARCA_MODERADO.format(categoria=categoria)
            self.memoria.guardar_turno(thread_id, "user", marca)
            meta_bloqueo = {
                "ruta": "bloqueado_salvaguarda",
                "citas": [],
                "bloqueada": True,
                "categoria_moderacion": categoria,
            }
            self.memoria.guardar_turno(thread_id, "assistant", moderacion.texto, meta_bloqueo)
            resultado_bloqueado: dict[str, Any] = {
                "respuesta": moderacion.texto,
                "thread_id": thread_id,
                "ruta_router": "bloqueado_salvaguarda",
                "score_router": 1.0,
                "justificacion_router": f"Moderación antes del router: {categoria}.",
                "citas": [],
                "archivos_adjuntos": [],
                "fuentes_datos": [],
                "blindaje_activado": categoria == "manipulacion",
                "bloqueada": True,
                "categoria_moderacion": categoria,
                "mensaje_registrado": marca,
            }
            if categoria in {"datos_de_terceros", "insulto_y_datos_de_terceros"}:
                resultado_bloqueado["normativa"] = NORMATIVA_DATOS
            return resultado_bloqueado

        decision = decidir_ruta_router(mensaje)

        citas: list[dict[str, str]] = []
        archivos: list[dict[str, str]] = []
        fuentes_datos: list[dict[str, Any]] = []
        # Textos fijos que van después del cuerpo (ya limpios): no pasan por el recorte de pulir_respuesta.
        sufijos: list[str] = []
        blindaje_indirecto = False
        normativa: str | None = None
        cortesia: str | None = None

        if decision.ruta == "directo":
            if pregunta_dato_personal(mensaje) and not clasificar_cortesia(mensaje):
                respuesta = AVISO_DATO_PERSONAL
                normativa = NORMATIVA_DATOS
            elif (categoria_cortesia := clasificar_cortesia(mensaje)) is not None:
                cortesia = categoria_cortesia
                prefs = self._preferencias(user_id) if categoria_cortesia == "saludo" else {}
                respuesta = responder_cortesia(categoria_cortesia, mensaje, historial, semilla, prefs)
            else:
                respuesta = TEXTO_NO_PUBLICADO

        elif decision.ruta == "memoria_store":
            respuesta, avisa = self._turno_memoria(mensaje, user_id)
            normativa = NORMATIVA_DATOS if avisa else None

        elif decision.ruta == "herramienta_estructurada":
            seccion = seccion_ficha(mensaje)
            if seccion is not None:
                respuesta, fuentes = redactar_ficha(mensaje, seccion)
                citas = _citas_de_fuentes(fuentes)
                fuentes_datos.append(_fuentes_datos_ficha(fuentes))
                if seccion in {"presentacion", "negocios", "plantas"}:
                    sufijos.append(SEGUIMIENTO_FICHA)
            elif _es_pregunta_de_moto(mensaje):
                res_tool = _consultar_datos("ficha_moto")
                respuesta = redactar_ficha_moto(mensaje, res_tool.datos_exactos)
                fuentes_datos.append(fuentes_datos_moto(res_tool.datos_exactos, res_tool.fuente_archivo))
            else:
                res_tool = _consultar_datos("estadisticas_corpus")
                respuesta = redactar_estadisticas(mensaje, res_tool.datos_exactos)
                fuentes_datos.append(
                    fuentes_datos_estadisticas(res_tool.datos_exactos, res_tool.fuente_archivo)
                )

        elif decision.ruta == "mixto":
            cifra, citas_cifra = self._cifra_mixta(mensaje, fuentes_datos)
            documental, citas_doc, blindaje_indirecto = self._documental(
                mensaje, k=3, max_oraciones=2, entradas=("En sus documentos, Fanalca cuenta lo siguiente.",)
            )
            if documental:
                citas = citas_cifra + [c for c in citas_doc if c not in citas_cifra]
                respuesta = f"{cifra} {documental}"
                if any(k in mensaje.lower() for k in _PIDE_PLANO):
                    archivos.append(_adjunto("plano"))
                    sufijos.append(CIERRE_PLANO)
                else:
                    sufijos.append(SEGUIMIENTO_MIXTO)
            else:
                # Sin evidencia documental no se afirma nada de los documentos ni se adjuntan recursos.
                citas = citas_cifra
                respuesta = f"{cifra} {RECHAZO}"

        else:  # rag_documental
            documental, citas, blindaje_indirecto = self._documental(mensaje, k=3, max_oraciones=3)
            if not documental:
                respuesta = RECHAZO
            elif any(k in mensaje.lower() for k in _PIDE_PLANO):
                archivos.append(_adjunto("plano"))
                respuesta = documental
                sufijos.append(CIERRE_PLANO)
            else:
                respuesta = documental
                sufijos.append(SEGUIMIENTO_DOCUMENTAL)

        if blindaje_indirecto:
            sufijos.append(AVISO_BLINDAJE)
        # Filtro de salida común solo sobre el cuerpo (el texto llega limpio al chat, a los subtítulos y a la
        # voz); los textos fijos van después, así el recorte a 600 caracteres nunca quita el aviso del
        # blindaje.
        respuesta = " ".join([pulir_respuesta(respuesta, respaldo=RECHAZO), *sufijos])

        # Ley 1581: solo se limpia el mensaje del usuario; la respuesta sale del corpus y las herramientas.
        # En la ruta de perfil se guarda solo el marcador; en las demás se omiten autopresentaciones,
        # correos, teléfonos y documentos.
        if decision.ruta == "memoria_store" and decidir_memoria(mensaje) == "guardar":
            mensaje_guardado = MARCA_PERFIL
        else:
            mensaje_guardado = anonimizar_datos_personales(omitir_autopresentaciones(mensaje))
        metadatos_turno: dict[str, Any] = {"ruta": decision.ruta, "citas": citas}
        if cortesia:
            metadatos_turno["cortesia"] = cortesia
        self.memoria.guardar_turno(thread_id, "user", mensaje_guardado)
        self.memoria.guardar_turno(thread_id, "assistant", respuesta, metadatos_turno)

        resultado: dict[str, Any] = {
            "respuesta": respuesta,
            "thread_id": thread_id,
            "ruta_router": decision.ruta,
            "score_router": decision.score_confianza,
            "justificacion_router": decision.justificacion,
            "citas": citas,
            "archivos_adjuntos": archivos,
            "fuentes_datos": fuentes_datos,
            "blindaje_activado": blindaje_indirecto,
            "bloqueada": False,
        }
        if normativa:
            resultado["normativa"] = normativa
        return resultado

    def _cifra_mixta(
        self, mensaje: str, fuentes_datos: list[dict[str, Any]]
    ) -> tuple[str, list[dict[str, str]]]:
        """Oración con el dato estructurado de la ruta mixta: ficha corporativa, ficha de la moto o
        estadísticas (según la pregunta). Agrega la procedencia a ``fuentes_datos`` y devuelve las citas de la
        ficha."""
        seccion: SeccionFicha | None = seccion_ficha(mensaje, permitir_documentos=True)
        if seccion is not None and seccion != "no_publicado":
            texto, fuentes = redactar_ficha(mensaje, seccion)
            fuentes_datos.append(_fuentes_datos_ficha(fuentes))
            return texto, _citas_de_fuentes(fuentes)
        tipo: Literal["ficha_moto", "estadisticas_corpus"] = (
            "ficha_moto" if _es_pregunta_de_moto(mensaje) else "estadisticas_corpus"
        )
        res_tool = _consultar_datos(tipo)
        if tipo == "ficha_moto":
            fuentes_datos.append(fuentes_datos_moto(res_tool.datos_exactos, res_tool.fuente_archivo))
            return redactar_ficha_moto(mensaje, res_tool.datos_exactos), []
        fuentes_datos.append(fuentes_datos_estadisticas(res_tool.datos_exactos, res_tool.fuente_archivo))
        return redactar_estadisticas(mensaje, res_tool.datos_exactos), []
