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
