"""Sesiones por usuario seudónimo (ADR-033).

- **Identidad:** ``user_id`` = HMAC-SHA256 del alias normalizado. La clave del HMAC y la de la cookie se
  derivan con HKDF de ``IGNIS_SECRETO_SESION`` con etiquetas distintas, así que una no revela la otra. Sin
  el secreto (o con menos de 32 caracteres) las sesiones fallan con ``ErrorSesionesNoConfiguradas``: no hay
  secreto por defecto.
- **Cookie:** ``{u: user_id, a: alias}`` cifrado y autenticado con Fernet, con vencimiento (8 h
  deslizantes). El alias solo viaja en esa cookie: no se guarda en la base, los logs, la auditoría ni el
  Store.
- **Limitación:** la cookie no se puede revocar desde el servidor. Cerrar sesión la borra del navegador,
  pero una copia robada vale hasta su vencimiento.
- **Hilos:** cada ``thread_id`` tiene un dueño. Un hilo nuevo y sin historial se asigna al primer usuario
  que lo usa; un hilo de otro usuario, o uno sin dueño que ya tiene historial (por ejemplo, anterior a las
  sesiones), responde 403.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.excepciones import (
    ErrorAliasInvalido,
    ErrorHiloAjeno,
    ErrorRecursoNoEncontrado,
    ErrorSesionesNoConfiguradas,
    ErrorSinSesion,
)
from fabrica_autopartes.pipelines.texto import anonimizar_datos_personales, omitir_autopresentaciones
from fabrica_autopartes.repositories.auditoria import RepositorioMemoriaIgnis
from fabrica_autopartes.repositories.sesiones import Hilo, RepositorioSesiones

LONGITUD_MINIMA_SECRETO = 32
_SAL_HKDF = b"fna-ignis-sesiones-v1"
_INFO_USER_ID = b"ignis/user_id"
_INFO_COOKIE = b"ignis/cookie"

_ALIAS = re.compile(r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ-]{3,32}")
# Dos o más palabras de solo letras separadas por guion («ana-gomez»): forma de nombre y apellido. También
# rechaza alias inventados como «rojo-veloz»; se prefiere ese falso positivo a guardar un nombre.
_NOMBRE_APELLIDO = re.compile(r"[^\W\d_]{2,}(?:-[^\W\d_]{2,})+")
_DIGITOS_SEGUIDOS = re.compile(r"\d{6,}")
_USER_ID = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True)
class SesionUsuario:
    """Sesión descifrada de la cookie. ``alias`` no aparece en ``repr`` para no filtrarlo a un log por
    error."""

    user_id: str
    alias: str = field(repr=False)

    @property
    def user_id_corto(self) -> str:
        return self.user_id[:8]


def normalizar_alias(alias: str) -> str:
    return unicodedata.normalize("NFC", alias.strip()).lower()


def validar_alias(alias: str) -> str:
    """Devuelve el alias normalizado o lanza ``ErrorAliasInvalido`` (mensaje genérico, sin el alias).

    Acepta de 3 a 32 letras (con tildes y ñ), números y guiones. Rechaza correos, teléfonos y documentos (lo
    que ``anonimizar_datos_personales`` modificaría, 6 dígitos seguidos o solo números) y la forma
    nombre-apellido.
    Los espacios y la «@» quedan fuera por el juego de caracteres.
    """
    limpio = unicodedata.normalize("NFC", alias.strip())
    if (
        not _ALIAS.fullmatch(limpio)
        or limpio.isdigit()
        or _DIGITOS_SEGUIDOS.search(limpio)
        or anonimizar_datos_personales(limpio) != limpio
        or _NOMBRE_APELLIDO.fullmatch(limpio)
    ):
        raise ErrorAliasInvalido()
    return limpio.lower()


def titulo_de(mensaje: str, largo: int = 60) -> str:
    """Título del hilo: primera pregunta sin autopresentaciones ni datos de contacto, recortada."""
    texto = " ".join(anonimizar_datos_personales(omitir_autopresentaciones(mensaje)).split())
    return texto if len(texto) <= largo else texto[: largo - 1].rstrip() + "…"


def nuevo_thread_id() -> str:
    return f"hilo-{secrets.token_hex(8)}"


def sesiones_configuradas(config: Configuracion) -> bool:
    """Verdadero si ``IGNIS_SECRETO_SESION`` existe y tiene al menos 32 caracteres (sin secreto por
    defecto)."""
    secreto = config.secreto_sesion.get_secret_value() if config.secreto_sesion else ""
    return len(secreto) >= LONGITUD_MINIMA_SECRETO


def _derivar(secreto: bytes, info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=_SAL_HKDF, info=info).derive(secreto)


class ServicioSesiones:
    """Lógica de sesiones e hilos. ``reloj`` permite fijar la hora en las pruebas de vencimiento."""

    def __init__(
        self,
        config: Configuracion,
        repo: RepositorioSesiones,
        memoria_ignis: RepositorioMemoriaIgnis,
        reloj: Callable[[], float] = time.time,
    ) -> None:
        self.repo = repo
        self.memoria_ignis = memoria_ignis
        self.ttl_s = config.minutos_sesion * 60
        self._reloj = reloj
        self.configuradas = sesiones_configuradas(config)
        if self.configuradas and config.secreto_sesion is not None:
            semilla = config.secreto_sesion.get_secret_value().encode("utf-8")
            # Dos claves de 32 bytes derivadas con etiquetas distintas: una no revela la otra.
            self._clave_hmac = _derivar(semilla, _INFO_USER_ID)
            self._clave_cookie = _derivar(semilla, _INFO_COOKIE)
            self._fernet = Fernet(base64.urlsafe_b64encode(self._clave_cookie))

    def _exigir_configuracion(self) -> None:
        if not self.configuradas:
            raise ErrorSesionesNoConfiguradas()

    # ------------------------------------------------------------ identidad y cookie
    def user_id_de(self, alias_normalizado: str) -> str:
        self._exigir_configuracion()
        return hmac.new(self._clave_hmac, alias_normalizado.encode("utf-8"), hashlib.sha256).hexdigest()[:32]

    def emitir_token(self, sesion: SesionUsuario) -> str:
        self._exigir_configuracion()
        datos = json.dumps({"u": sesion.user_id, "a": sesion.alias}, ensure_ascii=False).encode("utf-8")
        return self._fernet.encrypt_at_time(datos, int(self._reloj())).decode("ascii")

    def leer_token(self, token: str | None) -> SesionUsuario:
        """Descifra y valida la cookie; ``ErrorSinSesion`` si falta, está manipulada, vencida o es de otro
        secreto."""
        self._exigir_configuracion()
        if not token:
            raise ErrorSinSesion()
        try:
            datos: Any = json.loads(
                self._fernet.decrypt_at_time(token.encode("ascii"), self.ttl_s, int(self._reloj()))
            )
            user_id, alias = str(datos["u"]), str(datos["a"])
        except (InvalidToken, UnicodeError, ValueError, KeyError, TypeError) as exc:
            raise ErrorSinSesion() from exc
        # La cookie es autenticada; además, el user_id debe corresponder al alias con la clave actual.
        if not _USER_ID.fullmatch(user_id) or not hmac.compare_digest(user_id, self.user_id_de(alias)):
            raise ErrorSinSesion()
        return SesionUsuario(user_id, alias)

    # ------------------------------------------------------------ sesiones
    def crear_sesion(self, alias: str) -> tuple[SesionUsuario, str]:
        self._exigir_configuracion()
        normalizado = validar_alias(alias)
        sesion = SesionUsuario(self.user_id_de(normalizado), normalizado)
        self.repo.registrar_acceso(sesion.user_id)
        return sesion, self.emitir_token(sesion)

    def sesion_activa(self, token: str | None) -> tuple[SesionUsuario, str]:
        """Valida la cookie y devuelve la sesión con un token renovado (vencimiento deslizante)."""
        sesion = self.leer_token(token)
        self.repo.registrar_acceso(sesion.user_id)
        return sesion, self.emitir_token(sesion)

    # ------------------------------------------------------------ hilos
    def reclamar_hilo(self, thread_id: str, user_id: str) -> None:
        """Permite usar el hilo o lanza ``ErrorHiloAjeno``.

        Solo se asignan hilos nuevos y sin historial. Un hilo sin dueño con turnos guardados (anterior a las
        sesiones) no se entrega al primero que lo pida.
        """
        dueno = self.repo.dueno_de(thread_id)
        if dueno == user_id:
            return
        if dueno is not None or self.memoria_ignis.tiene_historial(thread_id):
            raise ErrorHiloAjeno()
        if not self.repo.crear_hilo(thread_id, user_id) and self.repo.dueno_de(thread_id) != user_id:
            raise ErrorHiloAjeno()  # otro usuario lo reclamó entre la consulta y la inserción

    def nuevo_hilo(self, user_id: str) -> str:
        while True:
            thread_id = nuevo_thread_id()
            if self.repo.crear_hilo(thread_id, user_id):
                return thread_id

    def hilos(self, user_id: str) -> list[Hilo]:
        return self.repo.listar_hilos(user_id)

    def mensajes(self, thread_id: str, user_id: str) -> list[dict[str, Any]]:
        dueno = self.repo.dueno_de(thread_id)
        if dueno is None:
            raise ErrorRecursoNoEncontrado("Hilo no encontrado.")
        if dueno != user_id:
            raise ErrorHiloAjeno()
        return self.memoria_ignis.obtener_historial(thread_id)

    def registrar_turno(self, thread_id: str, user_id: str, mensaje: str, ruta: str) -> None:
        self.repo.registrar_turno(thread_id, user_id, titulo_de(mensaje), ruta)
