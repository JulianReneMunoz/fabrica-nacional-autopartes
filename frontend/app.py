"""Interfaz de prueba (Streamlit) del sistema de conocimiento de Fanalca.

Ejecutar desde la raíz del repositorio:  ``uv run streamlit run frontend/app.py``
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as componentes

from fabrica_autopartes.core.config import RAIZ_PROYECTO, Configuracion
from fabrica_autopartes.core.excepciones import ErrorFNA
from fabrica_autopartes.llm.catalogo_prompts import catalogo
from fabrica_autopartes.pipelines.calidad import validar_fragmentos
from fabrica_autopartes.pipelines.graficas import ETAPAS, generar_graficas
from fabrica_autopartes.services.asistente import ServicioAsistente, es_rechazo
from fabrica_autopartes.services.maquinas import construir_biblioteca

# El estilo (tokens del visor, CSS, insignias, chips, tarjetas) vive en frontend/estilo.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import estilo as est

st.set_page_config(page_title="Fanalca · Base de conocimiento y Q&A", page_icon="⚙️", layout="wide")
URL_VISOR = os.environ.get("FNA_URL_VISOR", "http://127.0.0.1:8000/app/")
est.inyectar_estilo(est.cabecera_html(URL_VISOR))
TOKENS = est.leer_tokens()


@st.cache_resource
def obtener_servicio() -> ServicioAsistente:
    return ServicioAsistente(Configuracion())


servicio = obtener_servicio()
base = servicio.base

# ----------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header("⚙️ Configuración")
    proveedores = ["ollama", "openai", "anthropic", "claude_code", "extractivo"]
    proveedor = st.selectbox(
        "Proveedor LLM",
        proveedores,
        index=proveedores.index(servicio.config.proveedor_llm),
        help="'extractivo' es una línea base sin LLM para pruebas fuera de línea.",
    )
    modelo_defecto = {
        "ollama": servicio.config.modelo_llm,
        "openai": "gpt-4o-mini",
        "anthropic": "claude-haiku-5-5",
        "claude_code": "sonnet",
        "extractivo": "lexico-bm25",
    }[proveedor]
    modelo = st.text_input("Modelo", value=modelo_defecto)
    version = st.radio(
        "Versión de prompt",
        ["v1", "v2", "v3"],
        index=2,
        horizontal=True,
        help="v1 línea base · v2 reglas anti-alucinación · v3 JSON + few-shot + citas",
    )
    modo = st.selectbox(
        "Modo de contexto (Q&A)",
        ["auto", "completo", "seleccion"],
        help="completo = toda la base en el prompt de sistema (Módulo 1)",
    )
    opciones = {"proveedor": proveedor, "modelo": modelo, "version_prompt": version}
    st.divider()
    st.caption(
        "Prototipo técnico. Información pública del sitio oficial; no constituye un canal oficial de Fanalca."
    )


def ejecutar(funcion, *args, **kwargs):  # type: ignore[no-untyped-def]
    try:
        with st.spinner("Consultando el modelo…"):
            return funcion(*args, **kwargs)
    except ErrorFNA as exc:
        st.error(f"{exc.codigo}: {exc}")
    except Exception as exc:  # errores de conexión con Ollama/APIs
        st.error(f"No fue posible completar la operación: {exc}")
    return None


def origenes_de(fuentes):  # type: ignore[no-untyped-def]
    """Origen (scraping, lectura_web, semilla) de cada fragmento citado; solo lectura de la base Gold."""
    mapa: dict[str, str] = {}
    for f in fuentes:
        try:
            mapa[f.fragmento_id] = base.obtener(f.fragmento_id).origen
        except ErrorFNA:
            continue
    return mapa


st.markdown(
    est.encabezado_html(
        "Fábrica Nacional de Autopartes — Asistente de conocimiento",
        "Resumen · Preguntas frecuentes · Preguntas y respuestas ancladas a la base de conocimiento",
    ),
    unsafe_allow_html=True,
)

stats = base.estadisticas()
if stats.origenes.get("semilla"):
    st.warning(
        "La base actual proviene del **corpus semilla de demostración**. Para la entrega, "
        "ejecutar `uv run fabrica pipeline` (scraping → Silver/Gold → validación → gráficas)."
    )

(t_panel, t_proc, t_qa, t_res, t_faq, t_lab, t_eval, t_base, t_sim, t_aud) = st.tabs(
    [
        "📊 Panel",
        "🔄 Proceso de datos",
        "💬 Q&A",
        "📝 Resumen",
        "❓ FAQ",
        "🧪 Laboratorio de prompts",
        "✅ Evaluación",
        "🗂️ Base de conocimiento",
        "🧩 Simulador 3D",
        "🧾 Auditoría",
    ]
)

# ------------------------------------------------------------------------ panel
with t_panel:
    st.markdown(
        est.fila_chips(
            [
                est.chip("Documentos", stats.documentos, "dato"),
                est.chip("Fragmentos", stats.fragmentos, "dato"),
                est.chip("Tokens aprox.", f"{stats.tokens_aprox:,}".replace(",", "."), "dato"),
                est.chip("Fuentes (URL)", len(stats.urls), "dato"),
            ]
        )
        + '<p class="fna-procedencia">Procedencia: '
        + est.insignia("base_conocimiento", "capa gold")
        + " · ".join(f"{est.insignia(o)}{n} fragmentos" for o, n in stats.origenes.items())
        + "</p>",
        unsafe_allow_html=True,
    )
    izq, der = st.columns([3, 2])
    with izq:
        st.subheader("Fragmentos por sección")
        if stats.secciones:
            st.altair_chart(est.grafica_barras(stats.secciones, TOKENS), theme=None, width="stretch")
            st.caption(
                "Fuente: capa Gold (estadisticas.json) · una barra por sección, cifra al final de cada barra."
            )
    with der:
        st.subheader("Procedencia")
        st.dataframe(pd.DataFrame({"url": stats.urls}), hide_index=True, width="stretch")
    st.subheader("Últimas ejecuciones del pipeline")
    ejec = servicio.repo.listar_ejecuciones(10)
    if ejec:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "id": e.id,
                        "etapa": e.etapa,
                        "estado": e.estado,
                        "inicio": e.inicio,
                        "detalle": json.dumps(e.detalle, ensure_ascii=False),
                    }
                    for e in ejec
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Sin ejecuciones registradas. Ejecutar `uv run fabrica build`.")

# -------------------------------------------------------------------------- Q&A
with t_qa:
    st.subheader("Preguntas y respuestas")
    st.caption("El asistente responde solo con la base de conocimiento; si el dato no existe, lo indica.")
    if "historial" not in st.session_state:
        st.session_state.historial = []
    ejemplos = [
        "¿Dónde queda la sede principal de Fanalca?",
        "¿Qué cilindrajes de motocicletas Honda vende?",
        "¿Cuál es el horario de atención?",
    ]
    cols = st.columns(len(ejemplos))
    pregunta_ejemplo = None
    for col, ej in zip(cols, ejemplos, strict=True):
        if col.button(ej, width="stretch"):
            pregunta_ejemplo = ej
    pregunta = st.chat_input("Escribir una pregunta sobre Fanalca…") or pregunta_ejemplo
    if pregunta:
        r = ejecutar(servicio.responder, pregunta, canal="streamlit", modo_contexto=modo, **opciones)
        if r is not None:
            st.session_state.historial.append(r)
    if "busquedas_web" not in st.session_state:
        st.session_state.busquedas_web = {}
    for i, r in enumerate(reversed(st.session_state.historial[-10:])):
        st.markdown(
            est.tarjeta_respuesta(
                pregunta=r.pregunta,
                respuesta=r.respuesta,
                fundamentada=r.fundamentada,
                confianza=r.confianza,
                modo_contexto=r.modo_contexto,
                proveedor=r.proveedor,
                modelo=r.modelo,
                version_prompt=r.version_prompt,
                latencia_ms=r.latencia_ms,
                fuentes=r.fuentes,
                origenes=origenes_de(r.fuentes),
                es_rechazo=es_rechazo(r.respuesta),
            ),
            unsafe_allow_html=True,
        )
        # Búsqueda web complementaria (ADR-019): solo a petición y solo tras la frase de rechazo.
        if es_rechazo(r.respuesta):
            web = st.session_state.busquedas_web.get(r.pregunta)
            if web is None and st.button("Buscar en la web con Claude", key=f"web-{i}-{r.pregunta}"):
                web = ejecutar(servicio.buscar_web, r.pregunta)
                if web is not None:
                    st.session_state.busquedas_web[r.pregunta] = web
            if web is not None:
                st.warning(
                    f"**{web.etiqueta}** · {web.proveedor}/{web.modelo} · consulta {web.fecha_consulta}"
                )
                # El texto web es un DATO: texto plano, sin Markdown que cargue recursos externos.
                st.text(web.respuesta)
                for h in web.hallazgos:
                    st.text(f"- {h.dato} · {h.url} · consulta {h.fecha_consulta}")
                st.caption(
                    "Hallazgos pendientes de revisión humana; no se agregan a la base de conocimiento."
                )

# ---------------------------------------------------------------------- resumen
with t_res:
    st.subheader("Resumen ejecutivo de la empresa")
    enfoque = st.selectbox(
        "Enfoque",
        [
            "general: identidad, negocios, presencia y contacto",
            "negocios y productos",
            "historia y trayectoria",
            "sostenibilidad y fundación",
        ],
    )
    if st.button("Generar resumen", type="primary"):
        r = ejecutar(servicio.resumir, enfoque, canal="streamlit", **opciones)
        if r is not None:
            st.session_state.resumen = r
    if "resumen" in st.session_state:
        r = st.session_state.resumen
        st.markdown(r.resumen)
        st.caption(f"{r.proveedor} · {r.modelo} · prompt {r.version_prompt} · {r.latencia_ms} ms")
        st.download_button("Descargar (.md)", r.resumen, file_name="resumen_fanalca.md")

# -------------------------------------------------------------------------- FAQ
with t_faq:
    st.subheader("Preguntas frecuentes generadas")
    n = st.slider("Número de preguntas", 3, 15, 8)
    if st.button("Generar FAQ", type="primary"):
        r = ejecutar(servicio.generar_faq, n, canal="streamlit", **opciones)
        if r is not None:
            st.session_state.faq = r
    if "faq" in st.session_state:
        r = st.session_state.faq
        for adv in r.advertencias:
            st.warning(adv)
        for i, it in enumerate(r.items, 1):
            with st.expander(f"{i}. {it.pregunta}"):
                st.write(it.respuesta)
                if it.fuentes:
                    st.caption("Fuentes: " + ", ".join(it.fuentes))
        df = pd.DataFrame([i.model_dump() for i in r.items])
        st.download_button(
            "Exportar CSV", df.to_csv(index=False).encode("utf-8"), file_name="faq_fanalca.csv"
        )

# ---------------------------------------------------------- laboratorio prompts
with t_lab:
    st.subheader("Laboratorio de prompts (experimentación documentada)")
    st.caption("Comparar versiones de prompt con la misma pregunta y el mismo modelo.")
    pregunta_lab = st.text_input(
        "Pregunta de prueba", "¿Cuál es el horario de atención de la sede principal?"
    )
    versiones = st.multiselect("Versiones", ["v1", "v2", "v3"], default=["v1", "v2", "v3"])
    with st.expander("Ver plantillas del catálogo Q&A"):
        for v, vp in catalogo("qa").items():
            st.markdown(f"**{v} — {vp.nombre}** · técnica: _{vp.tecnica}_  \nHipótesis: {vp.hipotesis}")
            st.code(vp.sistema, language="markdown")
    if st.button("Comparar", type="primary") and versiones:
        columnas = st.columns(len(versiones))
        for col, v in zip(columnas, versiones, strict=True):
            with col:
                st.markdown(f"#### {v}")
                op = {**opciones, "version_prompt": v}
                r = ejecutar(servicio.responder, pregunta_lab, canal="laboratorio", modo_contexto=modo, **op)
                if r is not None:
                    st.write(r.respuesta)
                    st.caption(
                        f"fundamentada={r.fundamentada} · confianza={r.confianza} · {r.latencia_ms} ms"
                    )

# ------------------------------------------------------------------- evaluación
with t_eval:
    st.subheader("Evaluación con el banco de 24 preguntas")
    st.caption("19 respondibles, 3 ausentes en la fuente, 1 fuera de alcance y 1 intento de inyección.")
    if st.button("Ejecutar evaluación", type="primary"):
        from fabrica_autopartes.services.evaluacion import evaluar

        informe = ejecutar(evaluar, servicio, {**opciones, "modo_contexto": modo})
        if informe is not None:
            st.session_state.evaluacion = informe
    if "evaluacion" in st.session_state:
        inf = st.session_state.evaluacion
        m = inf["metricas"]
        st.markdown(
            est.fila_chips(
                [
                    est.chip("Exactitud respondibles", f"{m['exactitud_respondibles']:.0%}", "dato"),
                    est.chip("Rechazo correcto", f"{m['rechazo_correcto']:.0%}", "dato"),
                    est.chip("Fundamentadas", f"{m['tasa_fundamentada']:.0%}", "dato"),
                    est.chip("Latencia media", f"{m['latencia_media_ms']} ms"),
                ]
            )
            + '<p class="fna-procedencia">Procedencia: banco de 24 preguntas, ejecución local · '
            + est.insignia("base_conocimiento")
            + "</p>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            pd.DataFrame(inf["detalle"])[["id", "tipo", "acierto", "fundamentada", "pregunta", "respuesta"]],
            hide_index=True,
            width="stretch",
        )
    historico = servicio.repo.listar_evaluaciones()
    if historico:
        st.markdown("##### Histórico")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "id": e.id,
                        "fecha": e.fecha,
                        "proveedor": e.proveedor,
                        "modelo": e.modelo,
                        "prompt": e.version_prompt,
                        **e.metricas,
                    }
                    for e in historico
                ]
            ),
            hide_index=True,
            width="stretch",
        )

# -------------------------------------------------------------- base de conocimiento
with t_base:
    st.subheader("Exploración de la base de conocimiento (capa Gold)")
    c1, c2 = st.columns([3, 1])
    consulta = c1.text_input("Búsqueda (BM25)", placeholder="p. ej. garantía, plantas, Fundación")
    secciones = ["(todas)", *sorted(stats.secciones)]
    seccion = c2.selectbox("Sección", secciones)
    filtro = None if seccion == "(todas)" else seccion
    if consulta:
        filas = [
            {
                "id": r.fragmento.id,
                "puntaje": r.puntaje,
                "seccion": r.fragmento.seccion,
                "texto": r.fragmento.texto,
                "url": r.fragmento.url,
            }
            for r in base.buscar(consulta, 30)
            if not filtro or r.fragmento.seccion.startswith(filtro)
        ]
    else:
        filas = [
            {"id": f.id, "seccion": f.seccion, "tokens": f.tokens_aprox, "texto": f.texto, "url": f.url}
            for f in base.filtrar(seccion=filtro)
        ]
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch", height=360)
    d1, d2 = st.columns(2)
    d1.download_button(
        "Descargar base_conocimiento.txt", base.texto_consolidado(), file_name="base_conocimiento.txt"
    )
    informe = validar_fragmentos(base.fragmentos)
    d2.markdown(
        f"**Validación de calidad:** {'✅ aprobada' if informe.aprobado else '❌ con errores'} · "
        f"{informe.errores} errores · {informe.advertencias} advertencias"
    )

# -------------------------------------------------------------- proceso de datos
EXPLICACION_ETAPAS = {
    "01_rastreo": "El rastreador lee robots.txt y los sitemaps de autopartesfanalca.com.co y fanalca.com, "
    "respeta Crawl-delay (pausa mínima de 2 s) y descarta rutas excluidas. La gráfica cuenta URL "
    "descubiertas, visitadas, capturadas y descartadas.",
    "02_bronze_paginas": "Capa Bronze: el HTML crudo de cada página se guarda sin modificar con su "
    "metadato (URL, estado HTTP, fecha, hash). Es la evidencia trazable del scraping.",
    "03_reduccion": "Reducción por etapa: bytes de HTML → texto extraído (trafilatura/BeautifulSoup) → "
    "texto sin plantilla (menús, pies) → texto limpio y anonimizado.",
    "04_limpieza_paginas": "Capa Silver: caracteres por página antes y después de la limpieza; se eliminan "
    "duplicados y datos personales no corporativos.",
    "05_fragmentos_seccion": "Capa Gold: los documentos se dividen en fragmentos con sección, URL y origen; "
    "estos fragmentos alimentan la base semántica (BM25) y el sistema de preguntas y respuestas.",
    "06_tokens_fragmento": "Tamaño de los fragmentos en tokens aproximados frente al límite de 600 que "
    "admite la ventana de contexto configurada para el modelo local.",
}

with t_proc:
    st.subheader("Proceso de la información: del sitio oficial a la base de conocimiento")
    st.graphviz_chart(
        r"""digraph G { rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="@PAPEL@",
        fontname="Helvetica", fontsize=10, color="@TINTA2@"]; edge [color="@TINTA2@"];
        web [label="Sitios oficiales\nautopartesfanalca.com.co\nfanalca.com", fillcolor="@DATOFONDO@"];
        r [label="1. Rastreo\nrobots.txt · sitemap · pausa"]; b [label="2. Bronze\nHTML crudo + metadatos"];
        s [label="3–4. Silver\nextracción · limpieza · dedupe"];
        g [label="5–6. Gold\nfragmentos + procedencia"];
        kb [label="Base de conocimiento\nBM25 + LangChain", fillcolor="@ACENTOSUAVE@"];
        qa [label="Resumen · FAQ · Q&A\nAPI · MCP · Simulador"];
        web -> r -> b -> s -> g -> kb -> qa; }""".replace("@PAPEL@", TOKENS["papel"])
        .replace("@TINTA2@", TOKENS["tinta-2"])
        .replace("@DATOFONDO@", TOKENS["dato-fondo"])
        .replace("@ACENTOSUAVE@", TOKENS["acento-suave"])
    )
    ruta_metricas = servicio.config.dir_datos / "gold" / "metricas_etapas.json"
    dir_graficas = RAIZ_PROYECTO / "docs" / "graficas"
    if ruta_metricas.exists():
        metricas = json.loads(ruta_metricas.read_text(encoding="utf-8"))
        st.markdown(
            est.fila_chips(
                [
                    est.chip("Capturas Bronze", (metricas.get("bronze") or {}).get("capturas", 0), "dato"),
                    est.chip("Documentos Silver", metricas["silver"]["documentos"], "dato"),
                    est.chip("Fragmentos Gold", metricas["gold"]["fragmentos"], "dato"),
                    est.chip("Fuente", metricas["fuente"]),
                ]
            )
            + '<p class="fna-procedencia">Procedencia: '
            + est.insignia(str(metricas["fuente"]))
            + f"métricas de etapas ({ruta_metricas.name})</p>",
            unsafe_allow_html=True,
        )
        st.caption(f"Métricas generadas en {metricas['generado_en'][:19]} UTC · {ruta_metricas.name}")
        if metricas["fuente"] != "scraping":
            st.info(
                "Las gráficas muestran la base de demostración. Ejecutar `uv run fabrica pipeline` en "
                "Windows 11 (PowerShell o Claude Code) para regenerarlas con el scraping real."
            )
        if st.button("Regenerar gráficas desde las métricas actuales"):
            generar_graficas(ruta_metricas, dir_graficas)
            st.success("Gráficas regeneradas en docs/graficas")
    else:
        st.warning("No existen métricas: ejecutar `uv run fabrica build` o `uv run fabrica pipeline`.")
    for clave, titulo in ETAPAS:
        ruta_png = dir_graficas / f"{clave}.png"
        with st.expander(titulo, expanded=clave in ("01_rastreo", "03_reduccion")):
            st.markdown(EXPLICACION_ETAPAS[clave])
            if ruta_png.exists():
                st.image(str(ruta_png), width="stretch")

# ------------------------------------------------------------------ simulador 3D
with t_sim:
    st.subheader("Simulador 3D v2.0 y biblioteca de máquinas")
    url_visor = URL_VISOR
    st.markdown(
        f"El visor web (React Three Fiber) se sirve desde FastAPI en **{url_visor}**. "
        "Iniciar la API con `.\\scripts\\ejecutar_api.ps1` y compilar el visor con `npm run build` "
        "en `web/`. El modelo del freno es **demostrativo**: geometría procedural simplificada, "
        "no un diseño certificado."
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.link_button("Abrir biblioteca", url_visor + "#/")
    c2.link_button("Abrir freno 3D", url_visor + "#/maquina/freno")
    c3.link_button("Abrir motocicleta", url_visor + "#/maquina/moto_honda")
    c4.link_button("Recorrido de 30 s", url_visor + "#/maquina/freno?tour=1")
    for maquina in construir_biblioteca(base):
        with st.container(border=True):
            st.markdown(f"**{maquina.pregunta}**  \n{maquina.una_linea} · `{maquina.relacion}`")
            for dato in maquina.datos_empresa:
                st.markdown(est.ficha_dato(dato.origen, dato.texto, dato.url), unsafe_allow_html=True)
            for par in maquina.parametros:
                st.markdown(
                    est.ficha_dato(
                        par.procedencia,
                        f"{par.nombre}: {par.valor:,.0f} {par.unidad}".replace(",", "."),
                    ),
                    unsafe_allow_html=True,
                )
    if st.toggle("Incrustar el visor en esta pestaña", value=False):
        componentes.iframe(url_visor + "#/maquina/freno", height=900, scrolling=True)

# -------------------------------------------------------------------- auditoría
with t_aud:
    st.subheader("Auditoría de interacciones")
    tarea = st.selectbox("Tarea", ["(todas)", "qa", "faq", "resumen"])
    filas_aud, total = servicio.repo.listar_interacciones(1, 200, None if tarea == "(todas)" else tarea)
    st.caption(f"{total} interacciones registradas")
    if filas_aud:
        df = pd.DataFrame(
            [
                {
                    "id": f.id,
                    "fecha": f.fecha,
                    "tarea": f.tarea,
                    "canal": f.canal,
                    "entrada": f.entrada,
                    "salida": f.salida,
                    "proveedor": f.proveedor,
                    "modelo": f.modelo,
                    "prompt": f.version_prompt,
                    "fundamentada": f.fundamentada,
                    "latencia_ms": f.latencia_ms,
                }
                for f in filas_aud
            ]
        )
        st.dataframe(df, hide_index=True, width="stretch")
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        st.download_button("Exportar CSV", buf.getvalue().encode("utf-8"), file_name="auditoria.csv")
