"""Bronze con manifiesto pero sin HTML en disco (el HTML crudo no se versiona, bitácora R-02).

Se usa HTML sintético propio de las pruebas (``tests/fixtures/sitio``), sin contenido de terceros.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.excepciones import ErrorConfiguracion
from fabrica_autopartes.pipelines.bronze import AlmacenBronze
from fabrica_autopartes.pipelines.orquestador import construir_base

SITIO = Path(__file__).resolve().parents[1] / "fixtures" / "sitio"


def _bronze_con_paginas(config: Configuracion) -> AlmacenBronze:
    almacen = AlmacenBronze(config.dir_bronze)
    for nombre in ("inicio.html", "quienes-somos.html", "contacto.html"):
        url = f"https://ejemplo-fna.test/{nombre.removesuffix('.html')}/"
        almacen.guardar(
            url=url,
            url_final=url,
            estado=200,
            tipo_contenido="text/html",
            contenido=(SITIO / nombre).read_bytes(),
            agente_usuario="FNA-KB/prueba",
        )
    return almacen


def test_con_html_en_disco_auto_usa_scraping(config: Configuracion) -> None:
    almacen = _bronze_con_paginas(config)
    assert almacen.html_disponible()
    resultado = construir_base(config)
    assert resultado.fuente_usada == "scraping"
    assert resultado.documentos_silver > 0


def test_manifiesto_sin_html_da_error_claro_y_no_toca_gold(config: Configuracion) -> None:
    almacen = _bronze_con_paginas(config)
    for html in (config.dir_bronze / "html").glob("*.html"):
        html.unlink()  # simula un clon nuevo: el manifiesto está versionado y el HTML no
    assert not almacen.vacio() and not almacen.html_disponible()
    with pytest.raises(ErrorConfiguracion, match="fabrica pipeline"):
        construir_base(config)
    assert not (config.dir_gold / "fragmentos.jsonl").exists()  # la base Gold no se reemplaza


def test_la_semilla_sigue_disponible_sin_html(config: Configuracion) -> None:
    _bronze_con_paginas(config)
    for html in (config.dir_bronze / "html").glob("*.html"):
        html.unlink()
    assert construir_base(config, "semilla").fuente_usada == "semilla"
