"""Utilidades de normalización de texto y estimación de tokens."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

_ESPACIOS = re.compile(r"[ \t ​]+")
_SALTOS = re.compile(r"\n{3,}")
_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    lineas = [_ESPACIOS.sub(" ", linea).strip() for linea in texto.split("\n")]
    texto = "\n".join(lineas)
    return _SALTOS.sub("\n\n", texto).strip()


def hash_texto(texto: str) -> str:
    return hashlib.sha256(normalizar(texto).lower().encode("utf-8")).hexdigest()


def tokens_aprox(texto: str) -> int:
    """Estimación conservadora (≈4 caracteres por token). No reemplaza al tokenizador
    real del modelo; se usa para presupuestar el contexto."""
    return math.ceil(len(texto) / 4)


def tejas(texto: str, n: int = 5) -> set[str]:
    palabras = re.findall(r"\w+", texto.lower())
    if len(palabras) < n:
        return {" ".join(palabras)}
    return {" ".join(palabras[i : i + n]) for i in range(len(palabras) - n + 1)}


def similitud_jaccard(a: str, b: str) -> float:
    ta, tb = tejas(a), tejas(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


DOMINIOS_CORPORATIVOS = (
    "fanalca.com",
    "fanalca.com.co",
    "autopartesfanalca.com.co",
    "autopartesfanalca.com",
)


def es_correo_corporativo(correo: str, dominios: tuple[str, ...] = DOMINIOS_CORPORATIVOS) -> bool:
    dominio = correo.lower().rsplit("@", 1)[-1].rstrip(".")
    return any(dominio == d or dominio.endswith("." + d) for d in dominios)


def contiene_datos_personales(texto: str) -> bool:
    """Detecta correos no corporativos (posibles datos personales, Ley 1581 de 2012)."""
    return any(not es_correo_corporativo(m.group(0)) for m in _CORREO.finditer(texto))


def anonimizar_correos(texto: str, dominios: tuple[str, ...] = DOMINIOS_CORPORATIVOS) -> str:
    """Conserva buzones corporativos publicados y oculta cualquier otro correo."""

    def _reemplazo(m: re.Match[str]) -> str:
        correo = m.group(0)
        return correo if es_correo_corporativo(correo, dominios) else "[correo omitido]"

    return _CORREO.sub(_reemplazo, texto)


# Teléfonos colombianos de 10 dígitos (celular 3xx o fijo 60x), con +57 opcional y separadores.
_TELEFONO = re.compile(r"(?<![\w+])(?:\+?57[\s.-]?)?\(?[36]\d{2}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?![\w])")
# Documento precedido de su tipo (cédula, CC, NIT, TI, CE, pasaporte, documento) o cifra suelta de 6 a 10
# dígitos con o sin puntos de miles; el dígito de verificación del NIT («-7») queda incluido.
_TIPO_DOCUMENTO = (
    r"(?:c[ée]dula(?:\s+de\s+(?:ciudadan[íi]a|extranjer[íi]a))?|c\.?\s?c\.?|nit|t\.?\s?i\.?|c\.?\s?e\.?"
    r"|pasaporte|documento(?:\s+de\s+identidad)?|identificaci[óo]n)"
)
_DOCUMENTO_CON_TIPO = re.compile(
    rf"(?i)(?<!\w)({_TIPO_DOCUMENTO})(\s*(?:n[°ºo.]?|no\.|n[úu]mero)?\s*[:#]?\s*)[A-Z]{{0,2}}\d[\d.\s-]{{4,16}}\d"
)
# Los montos de dinero no son documentos: se excluyen las cifras precedidas de «$» o seguidas de COP/pesos.
_DOCUMENTO_SUELTO = re.compile(
    r"(?<![\w.,])(?<!\$)(?<!\$\s)(?:\d{1,3}(?:\.\d{3}){2,3}|\d{6,10})(?:-\d)?(?![\w.,]?\d)"
    r"(?!\s*(?:COP|pesos)\b)",
    re.IGNORECASE,
)


MARCA_PERFIL = "[dato de perfil omitido (Ley 1581)]"
# Cola de una autopresentación: hasta un signo de puntuación, un salto de línea o « y » (siguiente cláusula).
_COLA_PERFIL = r"[^,.;:!?¿¡\n]*?(?=\s+y\s|[,.;:!?¿¡\n]|$)"
_AUTOPRESENTACION = re.compile(
    rf"(?i:\bme\s+llamo|\bmi\s+nombre\s+es|\btrabajo\s+en|\bmi\s+empresa\s+es)\b{_COLA_PERFIL}"
    # «soy» solo cuenta si lo sigue un nombre propio (mayúscula): «soy cliente» no es una autopresentación.
    rf"|(?i:\bsoy)\s+(?=[A-ZÁÉÍÓÚÑ]){_COLA_PERFIL}"
)


def omitir_autopresentaciones(texto: str) -> str:
    """Reemplaza «me llamo …», «mi nombre es …», «soy Nombre …», «trabajo en …» y «mi empresa es …» por
    ``MARCA_PERFIL`` (Ley 1581 de 2012): nombres y empleadores no se persisten."""
    return _AUTOPRESENTACION.sub(MARCA_PERFIL, texto)


def anonimizar_datos_personales(texto: str, dominios: tuple[str, ...] = DOMINIOS_CORPORATIVOS) -> str:
    """Oculta correos no corporativos, teléfonos y números de documento antes de persistir texto libre.

    Ley 1581 de 2012. Se aplica a mensajes de usuarios, no al corpus: una cifra suelta de 6 a 10 dígitos
    se trata como posible documento aunque sea otra cosa (falso positivo aceptado a favor de la privacidad).
    """
    resultado = anonimizar_correos(texto, dominios)
    resultado = _TELEFONO.sub("[teléfono omitido]", resultado)
    resultado = _DOCUMENTO_CON_TIPO.sub(lambda m: f"{m.group(1)}{m.group(2)}[documento omitido]", resultado)
    return _DOCUMENTO_SUELTO.sub("[documento omitido]", resultado)


# --- Respuestas para el cliente: texto limpio, completo y apto para leerse en voz alta ---------------------
def sin_tildes(texto: str) -> str:
    """Minúsculas y sin tildes ni diéresis (la «ñ» queda como «n»): base de las comparaciones por palabras."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


_FIN_ORACION = re.compile(r"(?<=[.!?…])\s+")


def partir_oraciones(texto: str) -> list[str]:
    """Oraciones de un texto: corta tras «.», «!», «?» o «…» seguidos de espacio, y en los saltos de línea."""
    oraciones: list[str] = []
    for linea in texto.split("\n"):
        oraciones.extend(o.strip() for o in _FIN_ORACION.split(linea) if o.strip())
    return oraciones


# Jerga interna que no llega al cliente (lista cerrada). «RAG» se busca solo en mayúsculas.
_JERGA = re.compile(
    r"\b(?:pydantic|bm25|router|enrutamiento|corpus|fragmentos?|thread|deterministas?|json)\b", re.IGNORECASE
)
_JERGA_RAG = re.compile(r"\bRAG\b")
_URL_EN_PARENTESIS = re.compile(r"\(\s*(?:https?://|www\.)[^)]*\)", re.IGNORECASE)
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_MARCADOR_ID = re.compile(r"\[[\w#.:/-]{1,80}\]")
_MARCA_BLINDAJE = re.compile(r"\[[^\]\n]*NEUTRALIZAD[^\]\n]*\]")
_ETIQUETA = re.compile(r"<\s*/?\s*[a-z_]+[^<>\n]*>", re.IGNORECASE)
_ARCHIVO = re.compile(r"(?<![\w@])[\w./\\-]*\.(?:jsonl?|csv|ya?ml|pdf|glb|md|txt|py)\b", re.IGNORECASE)
_BLOQUE_LLAVES = re.compile(r"\{[^{}]*\}")
_BLOQUE_CORCHETES_JSON = re.compile(r"\[[^\[\]]*\"[^\[\]]*\]")
_ENCABEZADO = re.compile(r"(?m)^\s*#{1,6}\s+")
_ALMOHADILLAS = re.compile(r"#{2,}")
_CITA_MD = re.compile(r"(?m)^\s*>\s*")
_VINETA = re.compile(r"(?m)^\s*(?:[-*•]|\d{1,2}[.)])\s+")
_ENUMERACION = re.compile(r"(?<![\w.])\d{1,2}\)\s+")
_ENFASIS = re.compile(r"\*\*|__|`")
_SEPARADOR = re.compile(r"\s*[|→]\s*")


def _ajustar_puntuacion(texto: str) -> str:
    t = re.sub(r"\(\s*\)", " ", texto)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s+([,.;:?!…])", r"\1", t)
    t = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", t)
    t = re.sub(r"[,;:]\s*([.?!])", r"\1", t)
    t = re.sub(r"\.{2,}(?!\.)", ".", t)
    return t.strip(" ,;:")


def _con_signos_de_apertura(oracion: str) -> str:
    """«Qué tal?» → «¿Qué tal?»; «Listo!» → «¡Listo!» (la voz entona mejor con los dos signos)."""
    if oracion.endswith("?") and "¿" not in oracion:
        return f"¿{oracion}"
    if oracion.endswith("!") and "¡" not in oracion:
        return f"¡{oracion}"
    return oracion


def pulir_respuesta(texto: str, respaldo: str = "", max_caracteres: int = 600) -> str:
    """Filtro de salida común (motor de reglas y futuro LLM) antes del chat, los subtítulos y la voz.

    Quita marcadores ``[id]``, URL, acentos graves, nombres de archivo, bloques con aspecto de JSON,
    etiquetas y marcas del blindaje, markdown, separadores «|» y «→» y la jerga interna; agrega «¿» y «¡»
    cuando faltan y recorta en límite de oración (nunca a media palabra). Si no queda nada, devuelve
    ``respaldo`` (el agente pasa la frase de rechazo fija). Es idempotente: un texto ya limpio no cambia.
    """
    t = _URL_EN_PARENTESIS.sub(" ", texto)
    t = _URL.sub(" ", t)
    t = _MARCA_BLINDAJE.sub(" ", t)
    t = _ETIQUETA.sub(" ", t)
    for _ in range(3):  # bloques anidados
        t = _BLOQUE_LLAVES.sub(" ", t)
        t = _BLOQUE_CORCHETES_JSON.sub(" ", t)
    t = _MARCADOR_ID.sub(" ", t)
    t = _ARCHIVO.sub(" ", t)
    t = _ENCABEZADO.sub("", t)
    t = _ALMOHADILLAS.sub(" ", t)
    t = _CITA_MD.sub("", t)
    t = _VINETA.sub("", t)
    t = _ENUMERACION.sub("", t)
    t = _ENFASIS.sub("", t)
    t = _SEPARADOR.sub(", ", t)
    t = _JERGA.sub(" ", t)
    t = _JERGA_RAG.sub(" ", t)
    oraciones = []
    for oracion in partir_oraciones(t):
        o = _ajustar_puntuacion(oracion)
        if re.search(r"[^\W\d_]", o):
            oraciones.append(_con_signos_de_apertura(o[0].upper() + o[1:]))
    resultado = ""
    for o in oraciones:
        candidato = f"{resultado} {o}".strip()
        if resultado and len(candidato) > max_caracteres:
            break
        resultado = candidato
    return resultado or respaldo


# --- Texto del scraping: solo oraciones completas y útiles -----------------------------------------------
_NAVEGACION = {
    "leer mas", "ver mas", "inicio", "contacto", "menu", "ir al contenido", "compartir", "siguiente",
    "anterior", "volver", "buscar", "read more", "home",
}  # fmt: skip
_COOKIES = re.compile(
    r"cookies|politica de privacidad|aviso de privacidad|acepto los terminos|acepta(?:r)? todo"
)
_METADATOS_BLOG = re.compile(r"(autor|publicacion|categoria) de la entrada")
_SEPARADORES_MENU = re.compile(r"[|>•]")
_CON_DATO_DE_CONTACTO = re.compile(rf"{_CORREO.pattern}|{_TELEFONO.pattern}")


def _linea_util(linea: str) -> bool:
    base = sin_tildes(linea).strip(" .:-*#")
    if not base or base in _NAVEGACION:
        return False
    if len(_SEPARADORES_MENU.findall(linea)) >= 3 or _COOKIES.search(base) or _METADATOS_BLOG.search(base):
        return False
    palabras = re.findall(r"[^\W\d_]+", linea)
    return not (len(palabras) > 4 and all(p.isupper() for p in palabras))


def limpiar_texto_scrapeado(texto: str, min_caracteres: int = 25, max_caracteres: int = 320) -> list[str]:
    """Oraciones completas de un texto del scraping, en su orden.

    Descarta menús, avisos de cookies y privacidad, rótulos de navegación, metadatos de entradas del blog
    (llevan nombres de personas: Ley 1581), líneas en mayúsculas de más de 4 palabras, encabezados cortos y
    oraciones de menos de ``min_caracteres`` o más de ``max_caracteres``. También descarta las oraciones con
    correos o teléfonos: los canales corporativos salen de la ficha estructurada, no del texto libre.
    """
    oraciones: list[str] = []
    for linea in texto.split("\n"):
        if not _linea_util(linea):
            continue
        if linea.lstrip().startswith("#"):
            # Un encabezado corto es un rótulo («## Sostenibilidad»); uno largo trae contenido
            # («#### Contamos con plantas de producción en …»).
            linea = _ENCABEZADO.sub("", linea)
            if len(linea.split()) < 6:
                continue
        limpia = _VINETA.sub("", _ENFASIS.sub("", linea)).strip()
        for oracion in partir_oraciones(limpia):
            o = _ajustar_puntuacion(oracion)
            if o and o[-1].isalnum():
                o += "."
            if min_caracteres <= len(o) <= max_caracteres and not _CON_DATO_DE_CONTACTO.search(o):
                oraciones.append(o)
    return oraciones


_TEXTO_PALABRAS_VACIAS = (
    "a al algo algun alguna ante asi cada como con cual cuales cuando de del desde donde dos el ella ellos "
    "en entre era es esa ese eso esta este esto estos fue ha hace hay la las le les lo los mas me mi muy no "
    "nos o para pero por que quien se segun ser si sin sobre son su sus tambien te tiene tienen tu un una "
    "uno unos y ya yo dice dicen decir cuenta cuentame quiero saber puedes podrias informacion fanalca "
    "documento documentos corpus empresa datos dato favor gustaria conocer explica explicame "
    # Palabras de la ruta mixta que piden la cifra, no el tema: solo cuenta el tema («sostenibilidad»).
    "compara comparar cifras cifra estructurados estructurada estructurado estadisticas estadistica"
)
_PALABRAS_VACIAS = frozenset(_TEXTO_PALABRAS_VACIAS.split())


def terminos_de(texto: str) -> set[str]:
    """Raíces (6 letras) de las palabras con contenido: «sostenibilidad» y «sostenible» comparten «sosten»."""
    return {
        p[:6]
        for p in re.findall(r"[a-z0-9ñ]+", sin_tildes(texto))
        if len(p) >= 3 and p not in _PALABRAS_VACIAS
    }


def _jaccard_palabras(a: str, b: str) -> float:
    pa, pb = set(re.findall(r"\w+", sin_tildes(a))), set(re.findall(r"\w+", sin_tildes(b)))
    return len(pa & pb) / len(pa | pb) if pa and pb else 0.0


def seleccionar_oraciones(
    pregunta: str, textos: list[list[str]], max_oraciones: int = 3, max_palabras: int = 90
) -> list[tuple[int, str]]:
    """Oraciones más pertinentes para la pregunta, en su orden de aparición: ``(índice del texto, oración)``.

    ``textos`` trae las oraciones ya limpias de cada fragmento. Puntúa por términos de la pregunta (sin tildes
    ni palabras vacías), descarta casi duplicadas (Jaccard ≥ 0,6) y respeta ``max_palabras``. Si la pregunta
    tiene términos y ninguna oración comparte alguno, devuelve una lista vacía (sin evidencia).
    """
    terminos = terminos_de(pregunta)
    candidatas: list[tuple[int, int, int, str]] = []  # (puntaje, índice del texto, posición, oración)
    for i, oraciones in enumerate(textos):
        for j, oracion in enumerate(oraciones):
            puntaje = len(terminos & terminos_de(oracion))
            if puntaje or not terminos:
                candidatas.append((puntaje, i, j, oracion))
    candidatas.sort(key=lambda c: (-c[0], c[1], c[2]))
    elegidas: list[tuple[int, int, int, str]] = []
    palabras = 0
    for c in candidatas:
        if len(elegidas) == max_oraciones:
            break
        if any(_jaccard_palabras(c[3], e[3]) >= 0.6 for e in elegidas):
            continue
        n = len(c[3].split())
        if elegidas and palabras + n > max_palabras:
            continue
        elegidas.append(c)
        palabras += n
    return [(i, o) for _, i, _, o in sorted(elegidas, key=lambda c: (c[1], c[2]))]
