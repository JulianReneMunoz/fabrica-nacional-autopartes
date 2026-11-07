"""Capa Bronze: HTML tal como respondió el sitio + manifiesto JSONL de capturas.

Regla: la capa Bronze nunca se edita a mano; es el respaldo histórico que permite
reprocesar Silver y Gold sin volver a consultar el sitio.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

from fabrica_autopartes.domain.modelos import RegistroCaptura, ahora_utc


class AlmacenBronze:
    def __init__(self, directorio: Path) -> None:
        self.directorio = directorio
        self.dir_html = directorio / "html"
        self.manifiesto = directorio / "manifiesto.jsonl"
        self.errores = directorio / "errores.jsonl"
        self.dir_html.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def hash_contenido(contenido: bytes) -> str:
        return hashlib.sha256(contenido).hexdigest()

    def guardar(
        self,
        *,
        url: str,
        url_final: str,
        estado: int,
        tipo_contenido: str,
        contenido: bytes,
        agente_usuario: str,
    ) -> RegistroCaptura:
        sha = self.hash_contenido(contenido)
        ruta = self.dir_html / f"{sha}.html"
        if not ruta.exists():
            ruta.write_bytes(contenido)
        registro = RegistroCaptura(
            url=url,
            url_final=url_final,
            estado_http=estado,
            tipo_contenido=tipo_contenido,
            sha256=sha,
            archivo_html=ruta.relative_to(self.directorio).as_posix(),
            bytes=len(contenido),
            agente_usuario=agente_usuario,
        )
        with self.manifiesto.open("a", encoding="utf-8", newline="\n") as f:
            f.write(registro.model_dump_json() + "\n")
        return registro

    def registrar_error(self, url: str, motivo: str) -> None:
        with self.errores.open("a", encoding="utf-8", newline="\n") as f:
            f.write(
                json.dumps(
                    {"url": url, "motivo": motivo, "fecha": ahora_utc().isoformat()},
                    ensure_ascii=False,
                )
                + "\n"
            )

    def registros(self) -> Iterator[RegistroCaptura]:
        if not self.manifiesto.exists():
            return
        with self.manifiesto.open(encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    yield RegistroCaptura.model_validate_json(linea)

    def ultimos_por_url(self) -> dict[str, RegistroCaptura]:
        """Última captura exitosa por URL final (la más reciente gana)."""
        ultimos: dict[str, RegistroCaptura] = {}
        for r in self.registros():
            if 200 <= r.estado_http < 300:
                ultimos[r.url_final] = r
        return ultimos

    def urls_capturadas(self) -> set[str]:
        return {r.url for r in self.registros()} | {r.url_final for r in self.registros()}

    def leer_html(self, registro: RegistroCaptura) -> str:
        return (self.directorio / registro.archivo_html).read_text(encoding="utf-8", errors="replace")

    def guardar_resumen(self, resumen: dict) -> None:
        """Resumen de la última ejecución del rastreador (insumo de las gráficas)."""
        datos = {"fecha": ahora_utc().isoformat(), **resumen}
        (self.directorio / "resumen_rastreo.json").write_text(
            json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )

    def leer_resumen(self) -> dict | None:
        ruta = self.directorio / "resumen_rastreo.json"
        return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None

    def vacio(self) -> bool:
        return not self.manifiesto.exists() or self.manifiesto.stat().st_size == 0

    def html_disponible(self) -> bool:
        """Algún HTML del manifiesto existe en disco (el HTML crudo no se versiona: bitácora R-02)."""
        return any((self.directorio / r.archivo_html).exists() for r in self.registros())
