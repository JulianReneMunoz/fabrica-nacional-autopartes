"""Validaciones de calidad del corpus Gold (usadas por CLI, pruebas y servidor MCP)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from fabrica_autopartes.domain.modelos import Fragmento
from fabrica_autopartes.pipelines.texto import contiene_datos_personales

_RESTOS_HTML = ("<div", "<script", "</p>", "&nbsp;", "{{", "cookie")


@dataclass
class Hallazgo:
    regla: str
    severidad: str  # "error" | "advertencia"
    fragmento_id: str
    detalle: str


@dataclass
class InformeCalidad:
    total_fragmentos: int
    errores: int
    advertencias: int
    hallazgos: list[Hallazgo] = field(default_factory=list)

    @property
    def aprobado(self) -> bool:
        return self.errores == 0 and self.total_fragmentos > 0

    def a_dict(self) -> dict:
        d = asdict(self)
        d["aprobado"] = self.aprobado
        return d


def validar_fragmentos(fragmentos: list[Fragmento], max_tokens: int = 600) -> InformeCalidad:
    hallazgos: list[Hallazgo] = []
    ids: set[str] = set()
    for f in fragmentos:
        if f.id in ids:
            hallazgos.append(Hallazgo("id_unico", "error", f.id, "Identificador duplicado"))
        ids.add(f.id)
        if not f.url.startswith(("http://", "https://")):
            hallazgos.append(Hallazgo("procedencia", "error", f.id, "Fragmento sin URL de origen"))
        bajo = f.texto.lower()
        for resto in _RESTOS_HTML:
            if resto in bajo:
                hallazgos.append(Hallazgo("html_residual", "advertencia", f.id, f"Contiene '{resto}'"))
        if f.tokens_aprox > max_tokens:
            hallazgos.append(
                Hallazgo("tamano", "advertencia", f.id, f"{f.tokens_aprox} tokens > {max_tokens}")
            )
        if contiene_datos_personales(f.texto.replace("[correo omitido]", "")):
            hallazgos.append(
                Hallazgo("datos_personales", "advertencia", f.id, "Contiene un correo electrónico")
            )
    errores = sum(1 for h in hallazgos if h.severidad == "error")
    return InformeCalidad(
        total_fragmentos=len(fragmentos),
        errores=errores,
        advertencias=len(hallazgos) - errores,
        hallazgos=hallazgos,
    )
