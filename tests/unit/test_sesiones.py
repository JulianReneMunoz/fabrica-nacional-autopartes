"""Sesiones por usuario seudónimo (ADR-033): alias, HMAC, HKDF, cookie Fernet y propiedad de los hilos."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.core.excepciones import (
    ErrorAliasInvalido,
    ErrorHiloAjeno,
    ErrorSesionesNoConfiguradas,
    ErrorSinSesion,
)
from fabrica_autopartes.repositories.auditoria import RepositorioMemoriaIgnis
from fabrica_autopartes.repositories.sesiones import RepositorioSesiones
from fabrica_autopartes.services.sesiones import (
    ServicioSesiones,
    SesionUsuario,
    sesiones_configuradas,
    titulo_de,
    validar_alias,
)

# model_copy no valida: el secreto alternativo se pasa ya como SecretStr.
OTRO_SECRETO = SecretStr("otro-secreto-de-prueba-distinto-al-del-fixture-98765")


def _servicio(config: Configuracion, tmp_path: Path, reloj: list[float] | None = None) -> ServicioSesiones:
    hora = reloj if reloj is not None else [1_800_000_000.0]
    return ServicioSesiones(
        config,
        RepositorioSesiones(tmp_path / "sesiones.sqlite"),
        RepositorioMemoriaIgnis(tmp_path / "memoria.sqlite"),
        reloj=lambda: hora[0],
    )


# ------------------------------------------------------------------ alias
@pytest.mark.parametrize(
    ("alias", "normalizado"), [("compras-01", "compras-01"), ("Ñandú3", "ñandú3"), ("ABC12", "abc12")]
)
def test_alias_validos(alias: str, normalizado: str) -> None:
    assert validar_alias(alias) == normalizado


@pytest.mark.parametrize(
    "alias",
    [
        "ana@gmail.com",  # correo
        "3001234567",  # teléfono
        "+573001234567",  # teléfono con prefijo
        "user-123456",  # seis dígitos seguidos
        "Ana Gómez",  # nombre completo con espacio
        "ana-gomez",  # forma nombre-apellido
        "rojo-veloz",  # misma forma: falso positivo aceptado
        "ab",  # corto
        "x" * 33,  # largo
        "12345",  # solo números
        "",
    ],
)
def test_alias_invalidos(alias: str) -> None:
    with pytest.raises(ErrorAliasInvalido) as error:
        validar_alias(alias)
    if alias:
        assert alias not in str(error.value)  # el mensaje es genérico


# ------------------------------------------------------------------ identidad y claves
def test_user_id_determinista_y_dependiente_del_secreto(config: Configuracion, tmp_path: Path) -> None:
    servicio = _servicio(config, tmp_path)
    uid = servicio.user_id_de("compras-01")
    assert uid == servicio.user_id_de("compras-01")
    assert len(uid) == 32 and all(c in "0123456789abcdef" for c in uid)
    assert uid != servicio.user_id_de("compras-02")

    otro = _servicio(config.model_copy(update={"secreto_sesion": OTRO_SECRETO}), tmp_path / "otro")
    assert otro.user_id_de("compras-01") != uid


def test_las_claves_hkdf_del_hmac_y_de_fernet_son_distintas(config: Configuracion, tmp_path: Path) -> None:
    servicio = _servicio(config, tmp_path)
    # Fernet guarda sus claves crudas: 16 bytes de firma + 16 de cifrado = la clave derivada para la cookie.
    clave_fernet = servicio._fernet._signing_key + servicio._fernet._encryption_key
    assert clave_fernet == servicio._clave_cookie
    assert len(servicio._clave_hmac) == len(clave_fernet) == 32
    assert servicio._clave_hmac != clave_fernet


def test_sin_secreto_o_con_secreto_corto_falla_con_mensaje_claro(
    config: Configuracion, tmp_path: Path
) -> None:
    for secreto in (None, SecretStr("corto")):
        cfg = config.model_copy(update={"secreto_sesion": secreto})
        assert not sesiones_configuradas(cfg)
        servicio = _servicio(cfg, tmp_path)
        with pytest.raises(ErrorSesionesNoConfiguradas, match="IGNIS_SECRETO_SESION"):
            servicio.crear_sesion("compras-01")
        with pytest.raises(ErrorSesionesNoConfiguradas):
            servicio.leer_token("cualquier")


# ------------------------------------------------------------------ cookie
def test_la_cookie_cifrada_vuelve_a_la_misma_sesion(config: Configuracion, tmp_path: Path) -> None:
    servicio = _servicio(config, tmp_path)
    sesion, token = servicio.crear_sesion("Compras-01")
    assert sesion.alias == "compras-01"
    assert "compras" not in token  # cifrada, no solo firmada
    assert servicio.leer_token(token) == sesion
    assert "compras" not in repr(sesion)  # el alias no se filtra en repr


def test_cookie_manipulada_vencida_o_de_otro_secreto_da_sin_sesion(
    config: Configuracion, tmp_path: Path
) -> None:
    hora = [1_800_000_000.0]
    servicio = _servicio(config, tmp_path, hora)
    _, token = servicio.crear_sesion("compras-01")

    manipulado = token[:-6] + ("A" if token[-6] != "A" else "B") + token[-5:]
    for malo in (manipulado, "", None, "no-es-un-token"):
        with pytest.raises(ErrorSinSesion):
            servicio.leer_token(malo)

    otro = _servicio(config.model_copy(update={"secreto_sesion": OTRO_SECRETO}), tmp_path / "otro", hora)
    with pytest.raises(ErrorSinSesion):
        otro.leer_token(token)

    hora[0] += servicio.ttl_s - 1
    assert servicio.leer_token(token).alias == "compras-01"
    hora[0] += 2
    with pytest.raises(ErrorSinSesion):
        servicio.leer_token(token)


def test_la_renovacion_extiende_el_vencimiento(config: Configuracion, tmp_path: Path) -> None:
    hora = [1_800_000_000.0]
    servicio = _servicio(config, tmp_path, hora)
    _, token = servicio.crear_sesion("compras-01")
    hora[0] += servicio.ttl_s - 10
    _, renovado = servicio.sesion_activa(token)
    hora[0] += 20  # el token original ya venció; el renovado no
    with pytest.raises(ErrorSinSesion):
        servicio.leer_token(token)
    assert servicio.leer_token(renovado).alias == "compras-01"


# ------------------------------------------------------------------ hilos
def test_propiedad_de_los_hilos(config: Configuracion, tmp_path: Path) -> None:
    servicio = _servicio(config, tmp_path)
    ana = servicio.user_id_de("compras-01")
    beto = servicio.user_id_de("ventas-02")

    servicio.reclamar_hilo("hilo-nuevo", ana)  # nuevo y sin historial: se asigna
    servicio.reclamar_hilo("hilo-nuevo", ana)  # propio: permitido
    with pytest.raises(ErrorHiloAjeno):
        servicio.reclamar_hilo("hilo-nuevo", beto)

    # Hilo sin dueño que ya tiene historial (por ejemplo, del usuario «demo» anterior a las sesiones): 403.
    servicio.memoria_ignis.guardar_turno("hilo-viejo", "user", "consulta anterior")
    with pytest.raises(ErrorHiloAjeno):
        servicio.reclamar_hilo("hilo-viejo", ana)
    assert servicio.repo.dueno_de("hilo-viejo") is None


def test_titulo_anonimizado_y_recortado() -> None:
    assert "ana@gmail.com" not in titulo_de("Escribir a ana@gmail.com sobre la sede")
    assert "Ana" not in titulo_de("Me llamo Ana, ¿dónde queda la sede?")
    assert len(titulo_de("x " * 100)) == 60


def test_sesion_usuario_corto() -> None:
    assert SesionUsuario("0123456789abcdef0123456789abcdef", "a").user_id_corto == "01234567"
