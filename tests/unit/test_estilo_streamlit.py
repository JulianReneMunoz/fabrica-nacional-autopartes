"""Pruebas del estilo de Streamlit (fase 7d): tokens del visor, CSS, componentes y selectores."""

from __future__ import annotations

import importlib
import re
import sys
import tomllib
from html.parser import HTMLParser
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "frontend"))
est = importlib.import_module("estilo")

ETIQUETAS_PERMITIDAS = {
    "article", "h4", "p", "div", "span", "b", "strong", "ul", "li", "code", "a", "br",
}  # fmt: skip


class _Etiquetas(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.etiquetas: set[str] = set()
        self.atributos: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.etiquetas.add(tag)
        self.atributos.extend(attrs)


def analizar(fragmento: str) -> _Etiquetas:
    p = _Etiquetas()
    p.feed(fragmento)
    return p


class _Fuente:
    def __init__(self, fragmento_id: str, titulo: str, url: str) -> None:
        self.fragmento_id, self.titulo, self.url = fragmento_id, titulo, url


# --------------------------------------------------------------------------- tokens
def test_tokens_reales_se_leen_del_visor() -> None:
    tokens = est.leer_tokens()
    assert tokens["acento"] == "#eb6834"
    assert tokens["papel"] == "#fcfcfb"
    assert tokens["tinta"] == "#0b0b0b"
    assert tokens["borde"] == "1px solid var(--tinta)"  # valor compuesto con var() intacto
    assert (
        "Segoe UI" in tokens["sans"] and "Consolas" in tokens["mono"]
    )  # listas de fuentes con comillas y comas


def test_parseo_ignora_comentarios_y_exige_root() -> None:
    minimo = {t: "x" for t in est.TOKENS_REQUERIDOS}
    cuerpo = "\n".join(f"  --{n}: {v}; /* comentario; con punto y coma */" for n, v in minimo.items())
    texto = f"/* cabecera */ :root {{\n{cuerpo}\n  /* --acento: #000000; */\n}}"
    assert est.parsear_tokens(texto) == minimo
    with pytest.raises(est.ErrorTokens, match=r":root"):
        est.parsear_tokens("body { color: red; }")


def test_parseo_falla_si_falta_un_token_requerido() -> None:
    texto = ":root { --papel: #fff; }"
    with pytest.raises(est.ErrorTokens, match="ausentes"):
        est.parsear_tokens(texto)


def test_archivo_inexistente_da_error_claro(tmp_path: Path) -> None:
    with pytest.raises(est.ErrorTokens, match="No se pudo leer"):
        est.leer_tokens(tmp_path / "no_existe.css")


def test_config_toml_coincide_con_los_tokens() -> None:
    config = tomllib.loads((RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    esperado = est.tema_streamlit(est.leer_tokens())
    for clave, valor in esperado.items():
        assert config["theme"][clave].lower() == valor.lower(), clave
    assert config["theme"]["font"] == "sans serif"
    assert config["browser"]["gatherUsageStats"] is False
    contenido = (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8").lower()
    assert not re.search(r"(secret|password|api[_-]?key)", contenido)


def test_css_no_define_colores_propios() -> None:
    css = (RAIZ / "frontend" / "estilo.css").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css), "todo color debe salir de un token"
    assert not re.search(r"\brgba?\(", css)


def test_css_generado_declara_todos_los_tokens_y_solo_usa_variables_existentes() -> None:
    tokens = est.leer_tokens()
    css = est.generar_css(tokens)
    for nombre in tokens:
        assert f"--{nombre}:" in css
    usadas = set(
        re.findall(r"var\(--([a-z0-9-]+)\)", (RAIZ / "frontend" / "estilo.css").read_text(encoding="utf-8"))
    )
    assert usadas <= set(tokens), usadas - set(tokens)


# ------------------------------------------------------- selectores internos de Streamlit
def test_css_referencia_solo_selectores_listados() -> None:
    css = est.generar_css(est.leer_tokens())
    assert est.selectores_usados(css) == set(est.SELECTORES_STREAMLIT)


def test_version_de_streamlit_es_la_probada() -> None:
    import streamlit

    assert streamlit.__version__.startswith(est.VERSION_STREAMLIT_PROBADA + "."), (
        f"Streamlit {streamlit.__version__} no es la validada ({est.VERSION_STREAMLIT_PROBADA}): "
        "revisar frontend/estilo.css con las capturas y actualizar VERSION_STREAMLIT_PROBADA"
    )


def test_selectores_existen_en_el_paquete_de_streamlit() -> None:
    import streamlit

    js = Path(streamlit.__file__).parent / "static" / "static" / "js"
    if not js.exists():
        pytest.skip("Streamlit sin los recursos estáticos del cliente")
    bundle = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in js.glob("*.js"))
    ausentes = []
    for sel in est.SELECTORES_STREAMLIT:
        if sel.startswith(("stBaseButton-", "stBaseLinkButton-")):
            # Se construyen como `stBaseButton-${tipo}`: se verifica la plantilla y el tipo.
            prefijo, tipo = sel.split("-", 1)
            presente = f"{prefijo}-${{" in bundle and re.search(rf"[\"'`]{tipo}[\"'`]", bundle)
        else:
            presente = re.search(rf"[\"'`]{re.escape(sel)}[\"'`]", bundle)
        if not presente:
            ausentes.append(sel)
    assert not ausentes, f"Streamlit ya no emite estos data-testid: {ausentes}"


# ---------------------------------------------------------------------------- insignias
@pytest.mark.parametrize(
    ("fuente", "texto", "clase"),
    [
        ("scraping", "scraping", "fna-fuente-scraping"),
        ("lectura_web", "lectura web", "fna-fuente-lectura_web"),
        ("base_conocimiento", "base de conocimiento", "fna-fuente-base_conocimiento"),
        ("semilla", "semilla", "fna-fuente-semilla"),
        ("ficha", "ficha", "fna-fuente-ficha"),
        ("supuesto", "supuesto didáctico", "fna-fuente-supuesto"),
        ("no_publicado", "no publicado", "fna-fuente-no_publicado"),
        ("demostrativo", "supuesto didáctico", "fna-fuente-supuesto"),  # alias del visor
        ("publicado", "ficha", "fna-fuente-ficha"),
    ],
)
def test_insignia_texto_y_clase_como_en_el_visor(fuente: str, texto: str, clase: str) -> None:
    h = est.insignia(fuente)
    assert clase in h and f">{texto}</span>" in h


def test_insignia_desconocida_y_hostil_se_escapa() -> None:
    h = est.insignia('<img src=x onerror="alert(1)">')
    assert "<img" not in h and "&lt;img" in h and "fna-fuente-otra" in h
    assert analizar(h).etiquetas == {"span"}


def test_css_de_insignia_es_una_linea() -> None:
    css = (RAIZ / "frontend" / "estilo.css").read_text(encoding="utf-8")
    bloque = re.search(r"\.fna-insignia \{(.*?)\}", css, flags=re.S)
    assert bloque is not None and "white-space: nowrap" in bloque.group(1)


# -------------------------------------------------------------------------------- chips
def test_chip_variantes() -> None:
    assert 'data-variante="neutro"' in est.chip("a", 1)
    assert "fna-chip-dato" in est.chip("a", 1, "dato")
    supuesto = est.chip("a", 1, "supuesto")
    assert "fna-chip-supuesto" in supuesto and "supuesto didáctico" in supuesto
    ok = est.chip("estado", "bien", "estado", ok=True)
    assert "fna-chip-ok" in ok and "✓" in ok and "bien" in ok
    mal = est.chip("estado", "mal", "estado", ok=False)
    assert "fna-chip-alerta" in mal and "✕" in mal and "mal" in mal  # ícono + texto, nunca solo color
    with pytest.raises(ValueError):
        est.chip("a", 1, "inexistente")


def test_chip_escapa_etiqueta_y_valor() -> None:
    h = est.chip("<script>", '"><b onclick=1>', "dato")
    assert "<script" not in h and "<b onclick" not in h


# -------------------------------------------------------------------------- enlaces y md
@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "data:text/html,<b>", "//evil.example", "ftp://x", ""]
)
def test_urls_no_http_no_generan_href(url: str) -> None:
    assert not est.url_segura(url)
    assert "href" not in est.enlace(url, "texto")


def test_url_https_genera_enlace_seguro_y_escapado() -> None:
    h = est.enlace('https://fanalca.com/?a="><img src=x>', "t")
    assert 'rel="noopener noreferrer"' in h and "<img" not in h and "&quot;" in h


def test_markdown_minimo_negrita_listas_y_escape() -> None:
    h = est.markdown_a_html("Hola **mundo** <script>x</script>\n\n- uno\n- **dos**")
    assert "<strong>mundo</strong>" in h and "<ul><li>uno</li><li><strong>dos</strong></li></ul>" in h
    assert "<script" not in h and "&lt;script&gt;" in h
    assert analizar(h).etiquetas <= ETIQUETAS_PERMITIDAS


# --------------------------------------------------------------------- tarjeta del Q&A
def _tarjeta(**extra: object) -> str:
    datos: dict[str, object] = {
        "pregunta": "¿Dónde queda la sede?",
        "respuesta": "En **Yumbo**.",
        "fundamentada": True,
        "confianza": "alta",
        "modo_contexto": "seleccion",
        "proveedor": "extractivo",
        "modelo": "lexico-bm25",
        "version_prompt": "v3",
        "latencia_ms": 12,
        "fuentes": [_Fuente("nosotros#001", "Nosotros", "https://fanalca.com/nosotros/")],
        "origenes": {"nosotros#001": "scraping"},
    }
    datos.update(extra)
    return est.tarjeta_respuesta(**datos)  # type: ignore[arg-type]


def test_tarjeta_contiene_pregunta_respuesta_chips_e_insignia_con_url() -> None:
    h = _tarjeta()
    for esperado in ("¿Dónde queda la sede?", "<strong>Yumbo</strong>", "con respaldo", "confianza", "alta"):
        assert esperado in h
    assert "fna-fuente-scraping" in h and ">scraping</span>" in h
    assert 'href="https://fanalca.com/nosotros/"' in h and "nosotros#001" in h
    assert "12 ms" in h and "lexico-bm25" in h and "seleccion" in h


def test_tarjeta_sin_origen_conocido_usa_base_de_conocimiento() -> None:
    assert "fna-fuente-base_conocimiento" in _tarjeta(origenes={})


def test_tarjeta_rechazo_usa_estilo_de_estado_no_error() -> None:
    h = _tarjeta(
        respuesta="La información solicitada no se encuentra en la base de conocimiento de Fanalca.",
        fundamentada=False,
        fuentes=[],
        es_rechazo=True,
    )
    assert "fna-rechazo" in h and "fna-fuente-no_publicado" in h and "sin respaldo" in h
    assert "Fuentes (" not in h


def test_tarjeta_con_contenido_hostil_queda_escapada() -> None:
    hostil = '<script>alert("x")</script>'
    h = _tarjeta(
        pregunta=hostil,
        respuesta=f"{hostil} **<img src=x onerror=alert(1)>**",
        modelo='"><svg onload=alert(1)>',
        fuentes=[
            _Fuente("<b>id</b>#001", hostil, 'javascript:alert("x")'),
            _Fuente("a#002", '"><img src=x onerror=alert(2)>', 'https://x.example/?q="><iframe src=y>'),
        ],
        origenes={"a#002": "<svg onload=1>"},
    )
    analizado = analizar(h)
    assert analizado.etiquetas <= ETIQUETAS_PERMITIDAS, analizado.etiquetas - ETIQUETAS_PERMITIDAS
    assert "<script" not in h and "<img" not in h and "<svg" not in h and "<iframe" not in h
    assert 'href="javascript' not in h
    nombres = {n for n, _ in analizado.atributos}
    assert not {n for n in nombres if n and n.startswith("on")}, nombres
    assert all(v is None or not v.lower().startswith("javascript") for _, v in analizado.atributos)


# ------------------------------------------------------------------- cabecera y gráficas
def test_cabecera_lleva_marca_y_enlace_a_la_biblioteca() -> None:
    h = est.cabecera_html("http://127.0.0.1:8000/app/")
    assert "FNA" in h and "v2.0" in h
    assert 'href="http://127.0.0.1:8000/app/#/"' in h and "Biblioteca de máquinas" in h
    assert 'rel="noopener noreferrer"' in h


def test_cabecera_escapa_la_url_del_entorno() -> None:
    h = est.cabecera_html('http://x/"><script>alert(1)</script>')
    assert "<script" not in h


def test_grafica_usa_una_sola_escala_con_el_color_de_los_tokens() -> None:
    tokens = est.leer_tokens()
    spec = est.grafica_barras({"a": 3, "b": 1}, tokens).to_dict()
    texto = str(spec)
    assert tokens["dato"] in texto
    colores = set(re.findall(r"#[0-9a-fA-F]{6}", texto))
    assert colores <= set(tokens.values()), colores - set(tokens.values())
