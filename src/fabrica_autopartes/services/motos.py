"""Servicio de fichas técnicas de motocicletas Honda (catálogo curado) y cálculo didáctico.

La motocicleta 3D es una referencia genérica (``moto_honda``); el selector «Ver con ficha de…»
aplica únicamente los campos con estado ``publicado``. Lo no publicado conserva el valor típico
de la categoría, declarado como «supuesto didáctico». Las respuestas de modelo (FAQ) son
deterministas: salen de la ficha y citan el campo y la fuente que las sustentan.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.core.excepciones import ErrorRecursoNoEncontrado
from fabrica_autopartes.simulador.fisica_moto import (
    SUPUESTOS_REFERENCIA,
    EntradaMoto,
    ResultadoMoto,
    SupuestoDidactico,
    calcular_moto,
)

RUTA_CATALOGO = RAIZ_PROYECTO / "data" / "catalogo" / "motos_honda.yaml"
Estado = Literal["publicado", "no_publicado", "supuesto"]
ID_ENSAMBLAJE = "moto_honda"
TITULO_BIBLIOTECA = "Motocicleta (referencia genérica) con fichas Honda"

# Campos que «Ver con ficha de…» puede reemplazar: (grupo, campo) → clave del supuesto genérico.
CAMPOS_APLICABLES: dict[tuple[str, str], str] = {
    ("llantas", "trasera"): "medida_llanta_trasera",
    ("motor", "cilindrada"): "cilindrada_nominal_cm3",
    ("motor", "diametro_x_carrera"): "diametro_x_carrera",
    ("motor", "potencia"): "potencia",
    ("transmision", "marchas"): "n_marchas",
}


class CampoFicha(BaseModel):
    valor: str | int | float | bool | list[Any] | None = None
    unidad: str | None = None
    fuente: str | None = None
    fecha_consulta: str | None = None
    estado: Estado
    observacion: str | None = None


class FuenteFicha(BaseModel):
    id: str
    descripcion: str
    url: str | None = None
    fecha_consulta: str | None = None
    estado_acceso: str | None = None


class ResumenMoto(BaseModel):
    id: str
    nombre: str
    categoria: str
    versiones: list[str]
    campos_publicados: int
    campos_no_publicados: int


class FichaMoto(BaseModel):
    id: str
    nombre: str
    categoria: str
    versiones: list[str]
    grupos: dict[str, dict[str, CampoFicha]]
    por_version: dict[str, dict[str, CampoFicha]]
    pendientes_de_confirmar: list[dict[str, str]]
    fuentes: list[FuenteFicha]
    supuestos: list[SupuestoDidactico]
    ensamblaje_id: str = ID_ENSAMBLAJE
    titulo_biblioteca: str = TITULO_BIBLIOTECA


class RespuestaModelo(BaseModel):
    id: str
    pregunta: str
    respuesta: str
    campos: list[str] = Field(description="Rutas grupo.campo que sustentan la respuesta")
    fuentes: list[str]
    estado: Estado


class FichaAplicada(BaseModel):
    modelo: str
    version: str
    aplicados: dict[str, str] = Field(description="Campo publicado aplicado → valor")
    conservados_genericos: list[str] = Field(description="Campos no publicados: supuesto didáctico")


class CalculoMoto(BaseModel):
    resultado: ResultadoMoto
    ficha_aplicada: FichaAplicada | None


def validar_catalogo(datos: dict[str, Any]) -> list[str]:
    """Reglas del catálogo: todo valor lleva fuente y fecha, o su estado es ``no_publicado``."""
    errores: list[str] = []
    for modelo in datos.get("modelos", []):
        for ruta, campo in _recorrer(modelo):
            try:
                c = CampoFicha.model_validate(campo)
            except ValueError as exc:
                errores.append(f"{modelo.get('id')}.{ruta}: {exc}")
                continue
            if c.estado != "no_publicado" and c.valor is not None and not (c.fuente and c.fecha_consulta):
                errores.append(f"{modelo.get('id')}.{ruta}: valor sin fuente o sin fecha_consulta")
            if c.estado == "no_publicado" and c.valor is not None:
                errores.append(f"{modelo.get('id')}.{ruta}: no_publicado no debe llevar valor")
    return errores


def _recorrer(nodo: Any, prefijo: str = "") -> list[tuple[str, dict[str, Any]]]:
    campos: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(nodo, dict):
        return campos
    for clave, valor in nodo.items():
        if isinstance(valor, dict) and "estado" in valor:
            campos.append((f"{prefijo}{clave}", valor))
        elif isinstance(valor, dict):
            campos.extend(_recorrer(valor, f"{prefijo}{clave}."))
    return campos


@lru_cache(maxsize=1)
def _cargar(ruta: Path = RUTA_CATALOGO) -> dict[str, Any]:
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    errores = validar_catalogo(datos)
    if errores:
        raise ValueError("Catálogo de motos inválido: " + "; ".join(errores))
    return dict(datos)


def _modelo(modelo_id: str) -> dict[str, Any]:
    for m in _cargar()["modelos"]:
        if m["id"] == modelo_id:
            return dict(m)
    raise ErrorRecursoNoEncontrado(f"No existe la ficha de moto '{modelo_id}'")


_GRUPOS_FICHA = ("motor", "transmision", "suspension", "llantas", "capacidades", "electrico", "chasis")


def _campo(modelo: dict[str, Any], ruta: str, version: str | None = None) -> CampoFicha | None:
    nodo: Any = modelo
    if version is not None:
        nodo = modelo.get("frenos_por_version", {}).get(version, {})
    for parte in ruta.split("."):
        if not isinstance(nodo, dict) or parte not in nodo:
            return None
        nodo = nodo[parte]
    return CampoFicha.model_validate(nodo) if isinstance(nodo, dict) and "estado" in nodo else None


def listar_motos() -> list[ResumenMoto]:
    resumenes = []
    for m in _cargar()["modelos"]:
        estados = [CampoFicha.model_validate(c).estado for _, c in _recorrer(m)]
        resumenes.append(
            ResumenMoto(
                id=m["id"],
                nombre=m["nombre"],
                categoria=m["categoria"],
                versiones=list(m["versiones"]),
                campos_publicados=estados.count("publicado"),
                campos_no_publicados=estados.count("no_publicado"),
            )
        )
    return resumenes


def obtener_ficha(modelo_id: str) -> FichaMoto:
    m = _modelo(modelo_id)
    grupos = {g: {k: CampoFicha.model_validate(v) for k, v in m[g].items()} for g in _GRUPOS_FICHA if g in m}
    por_version = {
        ver: {k: CampoFicha.model_validate(v) for k, v in campos.items()}
        for ver, campos in m.get("frenos_por_version", {}).items()
    }
    fuentes = [
        FuenteFicha(id=k, **{c: v.get(c) for c in ("descripcion", "url", "fecha_consulta", "estado_acceso")})
        for k, v in _cargar().get("fuentes", {}).items()
    ]
    return FichaMoto(
        id=m["id"],
        nombre=m["nombre"],
        categoria=m["categoria"],
        versiones=list(m["versiones"]),
        grupos=grupos,
        por_version=por_version,
        pendientes_de_confirmar=[
            {k: str(v) for k, v in p.items()} for p in m.get("pendiente_de_confirmar", [])
        ],
        fuentes=fuentes,
        supuestos=list(SUPUESTOS_REFERENCIA.values()),
    )


def aplicar_ficha(modelo_id: str, version: str) -> FichaAplicada:
    """Campos publicados que reemplazan al valor genérico; el resto conserva su supuesto."""
    m = _modelo(modelo_id)
    aplicados: dict[str, str] = {}
    genericos: list[str] = []
    for (grupo, campo), clave in CAMPOS_APLICABLES.items():
        c = _campo(m, f"{grupo}.{campo}")
        if c is not None and c.estado == "publicado" and c.valor is not None:
            aplicados[f"{grupo}.{campo}"] = str(c.valor)
        else:
            genericos.append(f"{grupo}.{campo} ({clave})")
    for campo in ("trasero", "cbs"):
        c = _campo(m, f"{campo}", version)
        ruta = f"frenos.{version}.{campo}"
        if c is not None and c.estado == "publicado" and c.valor is not None:
            aplicados[ruta] = str(c.valor)
        else:
            genericos.append(ruta)
    return FichaAplicada(
        modelo=modelo_id, version=version, aplicados=aplicados, conservados_genericos=genericos
    )


def calcular(modelo_id: str | None, entrada: EntradaMoto) -> CalculoMoto:
    """Cálculo didáctico. Con ``modelo_id`` aplica los campos publicados de esa ficha."""
    if modelo_id is None:
        return CalculoMoto(resultado=calcular_moto(entrada), ficha_aplicada=None)
    ficha = aplicar_ficha(modelo_id, entrada.version)
    cbs_ficha = ficha.aplicados.get(f"frenos.{entrada.version}.cbs")
    if entrada.cbs and cbs_ficha == "False":
        raise ValueError(f"La ficha '{modelo_id}' versión {entrada.version} no incluye CBS")
    medida = ficha.aplicados.get("llantas.trasera")
    return CalculoMoto(resultado=calcular_moto(entrada, medida), ficha_aplicada=ficha)


def _fuente(c: CampoFicha | None) -> list[str]:
    return [c.fuente] if c is not None and c.fuente else []


def preguntas_modelo(modelo_id: str) -> list[RespuestaModelo]:
    """Preguntas frecuentes del modelo, respondidas de forma determinista desde la ficha."""
    m = _modelo(modelo_id)

    def valor_o_no_publicado(ruta: str, version: str | None = None) -> tuple[str, CampoFicha | None]:
        c = _campo(m, ruta, version)
        if c is None or c.estado == "no_publicado" or c.valor is None:
            return "No publicado", c
        unidad = f" {c.unidad}" if c.unidad and c.unidad not in {"ancho/perfil-rin"} else ""
        return f"{c.valor}{unidad}", c

    respuestas: list[RespuestaModelo] = []

    def agregar(
        id_: str, pregunta: str, texto: str, rutas: list[str], campos: list[CampoFicha | None]
    ) -> None:
        estados = [c.estado for c in campos if c is not None]
        estado: Estado = "publicado" if estados and all(e == "publicado" for e in estados) else "no_publicado"
        fuentes = sorted({f for c in campos for f in _fuente(c)})
        respuestas.append(
            RespuestaModelo(
                id=id_, pregunta=pregunta, respuesta=texto, campos=rutas, fuentes=fuentes, estado=estado
            )
        )

    pot, c_pot = valor_o_no_publicado("motor.potencia")
    reg, c_reg = valor_o_no_publicado("motor.regimen_potencia")
    obs = c_pot.observacion if c_pot is not None else ""
    agregar(
        "potencia",
        "¿Qué potencia tiene?",
        f"Potencia: {pot}. Régimen de potencia: {reg}. {obs}".strip(),
        ["motor.potencia", "motor.regimen_potencia"],
        [c_pot, c_reg],
    )
    tipo, c_tipo = valor_o_no_publicado("motor.tipo")
    agregar("motor", "¿Qué tipo de motor tiene?", f"Motor: {tipo}.", ["motor.tipo"], [c_tipo])
    llanta, c_llanta = valor_o_no_publicado("llantas.trasera")
    agregar(
        "llanta_trasera",
        "¿Qué medida tiene la llanta trasera?",
        f"Llanta trasera: {llanta}.",
        ["llantas.trasera"],
        [c_llanta],
    )
    susp, c_susp = valor_o_no_publicado("suspension.trasera")
    agregar(
        "suspension_trasera", "¿Cómo es la suspensión trasera?", f"{susp}.", ["suspension.trasera"], [c_susp]
    )
    arr, c_arr = valor_o_no_publicado("electrico.arranque")
    agregar("arranque", "¿Cómo arranca?", f"Arranque: {arr}.", ["electrico.arranque"], [c_arr])
    ins, c_ins = valor_o_no_publicado("electrico.instrumentos")
    agregar("instrumentos", "¿Qué instrumentos tiene?", f"{ins}.", ["electrico.instrumentos"], [c_ins])

    std_t, c_st = valor_o_no_publicado("trasero", "STD")
    dlx_t, c_dt = valor_o_no_publicado("trasero", "DLX")
    std_c = _campo(m, "cbs", "STD")
    dlx_c = _campo(m, "cbs", "DLX")
    agregar(
        "std_vs_dlx",
        "¿Qué diferencia hay entre STD y DLX?",
        f"Freno trasero: STD {std_t}; DLX {dlx_t}. CBS: STD "
        f"{'sí' if std_c and std_c.valor else 'no'}; DLX {'sí' if dlx_c and dlx_c.valor else 'no'}. "
        "La lámina asigna CBS y disco trasero solo a la DLX.",
        ["frenos.STD.trasero", "frenos.DLX.trasero", "frenos.STD.cbs", "frenos.DLX.cbs"],
        [c_st, c_dt, std_c, dlx_c],
    )
    agregar(
        "cbs",
        "¿Qué es el CBS?",
        "CBS es el sistema de frenos combinado: según la lámina solo está en la versión DLX. En el "
        "simulador, la palanca trasera con CBS reparte la presión entre ambos discos con una "
        "proporción de supuesto didáctico, porque el reparto real no está publicado.",
        ["frenos.DLX.cbs", "frenos.DLX.reparto_cbs"],
        [dlx_c, _campo(m, "reparto_cbs", "DLX")],
    )
    cil, c_cil = valor_o_no_publicado("motor.cilindrada")
    agregar("cilindrada", "¿Qué cilindrada tiene?", f"Cilindrada: {cil}.", ["motor.cilindrada"], [c_cil])
    return respuestas
