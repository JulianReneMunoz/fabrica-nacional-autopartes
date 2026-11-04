"""Puertos (interfaces) del dominio: desacoplan el rastreador del almacenamiento Bronze.

Detectado con ``scripts/verificar_capas.py``: el rastreador (capa 1) importaba
``pipelines.bronze`` (capa 2). Con este protocolo la dependencia se invierte.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from fabrica_autopartes.domain.modelos import RegistroCaptura


class AlmacenCapturas(Protocol):
    def guardar(
        self,
        *,
        url: str,
        url_final: str,
        estado: int,
        tipo_contenido: str,
        contenido: bytes,
        agente_usuario: str,
    ) -> RegistroCaptura: ...

    def registrar_error(self, url: str, motivo: str) -> None: ...

    def registros(self) -> Iterator[RegistroCaptura]: ...

    def urls_capturadas(self) -> set[str]: ...
