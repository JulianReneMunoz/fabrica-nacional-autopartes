"""Ficha corporativa de Fanalca (``data/catalogo/ficha_fanalca.json``): datos de la empresa construidos a
mano a partir del corpus, cada uno con su fragmento, su URL y una evidencia literal. La herramienta
estructurada la usa con ``tipo_consulta="ficha_empresa"`` y la responde en oraciones, sin JSON; las fuentes
viajan como citas."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from fabrica_autopartes.core.config import RAIZ_PROYECTO
from fabrica_autopartes.pipelines.texto import sin_tildes

RUTA_FICHA = RAIZ_PROYECTO / "data" / "catalogo" / "ficha_fanalca.json"
ARCHIVO_FICHA = "data/catalogo/ficha_fanalca.json"
# Separador de los tramos literales de una evidencia («En 1959, … fundaron Super Bus Medellín»).
SEPARADOR_EVIDENCIA = " … "

SeccionFicha = Literal[
    "presentacion",
    "proposito",
    "mision",
    "valores",
    "negocios",
    "plantas",
    "contacto",
    "historia",
    "no_publicado",
]

TEXTO_NO_PUBLICADO = (
    "No tengo esa información: Fanalca no la publica en su sitio y no hago cotizaciones. Si quieres, te "
    "comparto los canales oficiales de contacto para consultarla."
)


class FuenteDato(BaseModel):
    fragmento_id: str
    url: str
    titulo: str
    origen: Literal["scraping", "lectura_web", "semilla"]
    evidencia: str

    def tramos(self) -> list[str]:
        """Tramos literales de la evidencia: cada uno debe aparecer en el texto del fragmento."""
        return [t.strip() for t in self.evidencia.split(SEPARADOR_EVIDENCIA) if t.strip()]


class TextoConFuentes(BaseModel):
    texto: str
    fuentes: list[FuenteDato]


class ListaDeElementos(BaseModel):
    elementos: list[str]
    fuentes: list[FuenteDato]


class Hito(BaseModel):
    texto: str
    fuente: FuenteDato
    # El hito se cuenta en la misma oración de la constitución («…, y empezaron con 12 colaboradores»).
    con_la_fundacion: bool = False


class Historia(BaseModel):
    fundacion: str
    fundadores: str
    nombre_original: str
    hitos: list[Hito]
    fuentes: list[FuenteDato]


class Planta(BaseModel):
    lugar: str
    departamento: str


class Negocio(BaseModel):
    id: str
    nombre: str
    descripcion: str
    plantas: list[Planta]
    fuentes: list[FuenteDato]


class Canal(BaseModel):
    canal: str
    valor: str
    fuente: FuenteDato


class Contacto(BaseModel):
    direccion: str
    canales: list[Canal]
    fuentes: list[FuenteDato]


class FichaFanalca(BaseModel):
    version_esquema: int
    nota: str
    presentacion: TextoConFuentes
    proposito: TextoConFuentes
    pilares: ListaDeElementos
    valores: ListaDeElementos
    historia: Historia
    negocios: list[Negocio]
    contacto: Contacto
    no_publicado: list[str]

    def todas_las_fuentes(self) -> list[FuenteDato]:
        fuentes = [
            *self.presentacion.fuentes,
            *self.proposito.fuentes,
            *self.pilares.fuentes,
            *self.valores.fuentes,
            *self.historia.fuentes,
            *(h.fuente for h in self.historia.hitos),
        ]
        for negocio in self.negocios:
            fuentes.extend(negocio.fuentes)
        fuentes.extend(c.fuente for c in self.contacto.canales)
        fuentes.extend(self.contacto.fuentes)
        return fuentes


@lru_cache(maxsize=2)
def cargar_ficha(ruta: Path = RUTA_FICHA) -> FichaFanalca:
    return FichaFanalca.model_validate_json(ruta.read_text(encoding="utf-8"))


# --- Qué sección pide la pregunta ------------------------------------------------------------------------
_PATRONES_SECCION: list[tuple[SeccionFicha, re.Pattern[str]]] = [
    (
        "no_publicado",
        re.compile(
            r"\b(nit|horarios?|hora de atencion|abren|cierran|precios?|cuanto (cuesta|cuestan|vale|valen)"
            r"|cotiza\w*|cotizacion(es)?|inventario|repuestos disponibles|disponibilidad)\b"
        ),
    ),
    ("mision", re.compile(r"\b(mision|vision|filosofia)\b")),
    ("valores", re.compile(r"\b(valores|pilares)\b")),
    ("proposito", re.compile(r"\bproposito\b")),
    # «¿Qué hace Fanalca?» es una presentación solo si es toda la pregunta: «¿Qué hace Fanalca en
    # sostenibilidad?» y «Hola, soy Ana…, ¿qué hace Fanalca?» van al buscador.
    (
        "presentacion",
        re.compile(
            r"\b(que es fanalca|a que se dedica(n)?|quienes son)\b"
            r"|^[\s¿¡]*que hace fanalca(\s+(hoy|ahora))?[\s?.!]*$"
        ),
    ),
    (
        "contacto",
        re.compile(r"\b(contacto|contactar|comunicarme|telefonos?|direccion|correo|canales|linea de)\b"),
    ),
    (
        "plantas",
        re.compile(
            r"\b(plantas?|fabricas?|sedes|ubicad[oa]s?|ubicacion|donde (estan|queda|quedan|esta|tienen))\b"
        ),
    ),
    ("negocios", re.compile(r"\b(negocios?|unidades de negocio|lineas de negocio|empresas del grupo)\b")),
    (
        "historia",
        re.compile(r"\b(historia|fundad[oa]|fundo|fundacion de fanalca|cuando (nacio|empezo|se creo))\b"),
    ),
]
# Con estas palabras la pregunta es sobre los documentos (ruta documental), no sobre la ficha.
_PIDE_DOCUMENTOS = re.compile(r"\b(documentos?|corpus|informe|segun|noticias?|articulo)\b")


def seccion_ficha(mensaje: str, permitir_documentos: bool = False) -> SeccionFicha | None:
    """Sección de la ficha que responde la pregunta, o ``None``. Una pregunta sobre «el documento» va a la
    ruta documental salvo que ``permitir_documentos`` (ruta mixta). Lo no publicado (precios, NIT, horarios)
    se reconoce siempre."""
    texto = sin_tildes(mensaje)
    no_publicado = _PATRONES_SECCION[0][1]
    if no_publicado.search(texto):
        return "no_publicado"
    if not permitir_documentos and _PIDE_DOCUMENTOS.search(texto):
        return None
    if re.search(r"\bfundacion fanalca\b", texto):
        return None  # la Fundación Fanalca es una entidad, no la fecha de fundación
    for seccion, patron in _PATRONES_SECCION[1:]:
        if patron.search(texto):
            return seccion
    return None


# --- Redacción en oraciones ------------------------------------------------------------------------------
def _enumerar(elementos: list[str]) -> str:
    if len(elementos) <= 1:
        return "".join(elementos)
    return f"{', '.join(elementos[:-1])} y {elementos[-1]}"


def _minuscula_inicial(texto: str) -> str:
    return texto[0].lower() + texto[1:] if texto else texto


def _mayuscula_inicial(texto: str) -> str:
    return texto[0].upper() + texto[1:] if texto else texto


_CLAVES_NEGOCIO = {
    "honda_motocicletas": r"\b(honda )?(motos|motocicletas)\b",
    "honda_autos": r"\b(honda )?(autos|automoviles|carros)\b",
    "tubos_perfiles": r"\b(tubos|perfiles|acero)\b",
    "autopartes": r"\bautopartes\b",
    "ambiental": r"\b(ambiental|compactadoras|residuos)\b",
    "fanalvias": r"\bfanalvias\b",
}


def _negocio_mencionado(ficha: FichaFanalca, mensaje: str) -> Negocio | None:
    texto = sin_tildes(mensaje)
    for negocio in ficha.negocios:
        patron = _CLAVES_NEGOCIO.get(negocio.id)
        if patron and re.search(patron, texto):
            return negocio
    return None


def plantas_por_lugar(ficha: FichaFanalca) -> list[tuple[str, list[str]]]:
    """«Acopi, Yumbo (Valle del Cauca)» → negocios que tienen planta allí, en el orden de la ficha."""
    lugares: dict[str, list[str]] = {}
    for negocio in ficha.negocios:
        for planta in negocio.plantas:
            lugares.setdefault(f"{planta.lugar} ({planta.departamento})", []).append(negocio.nombre)
    return list(lugares.items())


def _pilares(ficha: FichaFanalca) -> str:
    return _enumerar([_minuscula_inicial(p) for p in ficha.pilares.elementos])


def _redactar_historia(h: Historia) -> str:
    """Todos los hitos, en orden, en 2 o 3 oraciones: la constitución (con los hitos marcados
    ``con_la_fundacion``) y el resto repartido en una o dos oraciones."""
    con_fundacion = [_minuscula_inicial(x.texto) for x in h.hitos if x.con_la_fundacion]
    resto = [_minuscula_inicial(x.texto) for x in h.hitos if not x.con_la_fundacion]
    primera = f"Fanalca se constituyó el {h.fundacion}, entre {h.fundadores}, como {h.nombre_original}"
    if con_fundacion:
        primera += f", y {_enumerar(con_fundacion)}"
    oraciones = [f"{primera}."]
    if resto:
        mitad = (len(resto) + 1) // 2 if len(resto) > 2 else len(resto)
        for grupo in (resto[:mitad], resto[mitad:]):
            if grupo:
                cuerpo = "; ".join(grupo[:-1]) + f"; y {grupo[-1]}" if len(grupo) > 2 else _enumerar(grupo)
                oraciones.append(f"{_mayuscula_inicial(cuerpo)}.")
    return " ".join(oraciones)


def redactar_ficha(
    mensaje: str, seccion: SeccionFicha, ficha: FichaFanalca | None = None
) -> tuple[str, list[FuenteDato]]:
    """Respuesta en 1 a 3 oraciones con los datos exactos de la ficha y las fuentes de esos datos."""
    ficha = ficha or cargar_ficha()
    if seccion == "no_publicado":
        return TEXTO_NO_PUBLICADO, []

    if seccion == "mision":
        texto = (
            "En la información de Fanalca que tengo no aparecen una misión y una visión como tal; lo que sí "
            f"publica es su propósito superior: «{ficha.proposito.texto}». Sus pilares estratégicos son "
            f"{_pilares(ficha)}."
        )
        return texto, [*ficha.proposito.fuentes, *ficha.pilares.fuentes]

    if seccion == "proposito":
        texto = f"El propósito superior de Fanalca es: «{ficha.proposito.texto}»."
        return texto, list(ficha.proposito.fuentes)

    if seccion == "valores":
        valores = _enumerar([f"«{v}»" for v in ficha.valores.elementos])
        texto = (
            f"Los valores corporativos de Fanalca son: {valores}. Y sus pilares estratégicos son "
            f"{_pilares(ficha)}."
        )
        return texto, [*ficha.valores.fuentes, *ficha.pilares.fuentes]

    h = ficha.historia
    nombres = [n.nombre for n in ficha.negocios]
    fuentes_negocios = [n.fuentes[0] for n in ficha.negocios]

    if seccion == "presentacion":
        texto = (
            f"Fanalca es {ficha.presentacion.texto}. Se constituyó el {h.fundacion} como {h.nombre_original} "
            f"y hoy tiene {len(nombres)} negocios: {_enumerar(nombres)}."
        )
        return texto, [*ficha.presentacion.fuentes, *h.fuentes, *fuentes_negocios]

    if seccion == "historia":
        return _redactar_historia(h), [*h.fuentes, *(hito.fuente for hito in h.hitos)]

    if seccion == "contacto":
        c = ficha.contacto
        # Punto y coma entre canales: las comas solas se confunden con las cifras de los teléfonos.
        canales = [f"{canal.canal}, {canal.valor}" for canal in c.canales]
        lista = f"{'; '.join(canales[:-1])}; y {canales[-1]}" if len(canales) > 1 else "".join(canales)
        texto = f"La dirección publicada de Fanalca es {c.direccion}. Sus canales oficiales son {lista}."
        return texto, [*c.fuentes, *(canal.fuente for canal in c.canales)]

    negocio = _negocio_mencionado(ficha, mensaje)
    if seccion == "plantas":
        if negocio is not None and negocio.plantas:
            lugares = _enumerar([f"{p.lugar} ({p.departamento})" for p in negocio.plantas])
            return f"{negocio.nombre} tiene plantas en {lugares}.", list(negocio.fuentes)
        partes = [f"en {lugar}, de {_enumerar(negocios)}" for lugar, negocios in plantas_por_lugar(ficha)]
        texto = f"Fanalca tiene plantas {'; '.join(partes[:-1])}; y {partes[-1]}."
        return texto, [n.fuentes[0] for n in ficha.negocios if n.plantas]

    # negocios
    if negocio is not None:
        return f"{negocio.nombre}: {negocio.descripcion}", list(negocio.fuentes)
    return f"Fanalca tiene {len(nombres)} negocios: {_enumerar(nombres)}.", fuentes_negocios
