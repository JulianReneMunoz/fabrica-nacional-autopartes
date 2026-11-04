"""Detección de desafíos antibots (el rastreador no intenta superarlos)."""

from __future__ import annotations

from fabrica_autopartes.scraping.cliente_http import RespuestaHTTP, detectar_proteccion


def test_sg_captcha_de_siteground() -> None:
    # Encabezados observados en https://autopartesfanalca.com.co/ el 4 de noviembre de 2026
    r = RespuestaHTTP(
        url="https://autopartesfanalca.com.co/",
        url_final="https://autopartesfanalca.com.co/",
        estado=202,
        tipo_contenido="text/html",
        contenido=b"<html>" + b" " * 150 + b"</html>",
        encabezados={"Server": "nginx", "SG-Captcha": "challenge", "X-Robots-Tag": "noindex"},
    )
    assert r.proteccion_antibots == "SiteGround Security (SG-Captcha): challenge"


def test_desafio_por_contenido_y_respuesta_normal() -> None:
    assert detectar_proteccion(503, {}, b"<script src='/cdn-cgi/challenge-platform/x.js'></script>")
    assert detectar_proteccion(200, {"Content-Type": "text/html"}, b"<html>captcha</html>") is None
    assert detectar_proteccion(404, {}, b"<html>No encontrado</html>") is None
