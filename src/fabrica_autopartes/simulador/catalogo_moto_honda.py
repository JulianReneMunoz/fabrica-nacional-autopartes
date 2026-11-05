"""Motocicleta de referencia genérica (naked de ~150 cc) para el simulador 3D.

Ensamblaje ``moto_honda`` (ADR-017). La geometría es procedural, esquemática y DEMOSTRATIVA:
no incorpora logotipos, emblemas ni réplica de un modelo comercial, y no constituye un diseño
industrial certificado. Las medidas de motor, transmisión y llantas se toman de
``fisica_moto.SUPUESTOS_REFERENCIA`` (todas con procedencia ``demostrativo``); el resto de
dimensiones son valores elegidos para que el conjunto sea legible.

Sistema de referencia: X hacia delante, Y hacia arriba (suelo en Y = 0), Z hacia el lado derecho
del conductor. Los ejes de las ruedas, del cigüeñal y del basculante son paralelos a Z.

Coherencia con la física (``fisica_moto``): la carrera del pistón (``carrera_mm``) fija el
recorrido de ``j_piston`` (de PMS a PMI, valores en [-carrera, 0] respecto al PMS), la longitud de
biela acota el giro de ``j_biela`` (±asin(r/L)) y la relación final fija la compuesta del piñón.
La animación no valida propiedades mecánicas.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, field_validator

from fabrica_autopartes.simulador.fisica_moto import (
    SUPUESTOS_REFERENCIA,
    parsear_medida_llanta,
    radio_llanta_m,
)
from fabrica_autopartes.simulador.modelos import (
    Articulacion,
    Ensamblaje,
    Geometria,
    LimitesMovimiento,
    Pieza,
    Subconjunto,
    TipoArticulacion,
    Transformacion,
    Vector3,
)

ID_ENSAMBLAJE = "moto_honda"
ADVERTENCIA = (
    "Referencia genérica esquemática de una motocicleta naked de ~150 cc, con geometría procedural "
    "y dimensiones demostrativas. No es un diseño industrial ni una réplica de un modelo comercial, "
    "no incluye logotipos ni emblemas y la animación no valida propiedades mecánicas."
)
REF_DEMO = "Modelo de demostración del proyecto (sin documentación de fabricante)"
MEDIDA_DELANTERA_DEMO = "90/80-17"


class ParametrosMoto(BaseModel):
    """Medidas de llanta (``ancho/perfil-rin``) que condicionan la geometría de las ruedas."""

    medida_llanta_trasera: str = Field(
        default_factory=lambda: str(SUPUESTOS_REFERENCIA["medida_llanta_trasera"].valor)
    )
    medida_llanta_delantera: str = MEDIDA_DELANTERA_DEMO

    @field_validator("medida_llanta_trasera", "medida_llanta_delantera")
    @classmethod
    def _medida_valida(cls, v: str) -> str:
        parsear_medida_llanta(v)
        return v


def _sup(clave: str) -> float:
    valor = SUPUESTOS_REFERENCIA[clave].valor
    assert isinstance(valor, float)
    return valor


def _r(v: float) -> float:
    return round(v, 6)


def _pieza(**kw: object) -> Pieza:
    kw.setdefault("referencia_documental", REF_DEMO)
    return Pieza.model_validate(kw)


def _rot_hacia(dx: float, dy: float) -> Vector3:
    """Euler XYZ (grados) que orienta el eje local Z de una primitiva según (dx, dy) en el plano XY."""
    return (90.0, 0.0, _r(math.degrees(math.atan2(dx, -dy))))


def _unitario(dx: float, dy: float) -> Vector3:
    n = math.hypot(dx, dy)
    return (_r(dx / n), _r(dy / n), 0.0)


def _p(
    id_: str,
    nombre: str,
    tipo: str,
    sub: str,
    descripcion: str,
    funcion: str,
    material: str,
    dims: dict[str, float],
    primitiva: str,
    params: dict[str, float],
    pos: Vector3,
    despiece: tuple[Vector3, float],
    art: str,
    rot: Vector3 = (0.0, 0.0, 0.0),
    relacionadas: list[str] | None = None,
    retirar: list[str] | None = None,
) -> Pieza:
    pos = (_r(pos[0]), _r(pos[1]), _r(pos[2]))
    return _pieza(
        id=id_,
        nombre=nombre,
        tipo=tipo,
        subconjunto=sub,
        descripcion=descripcion,
        funcion=funcion,
        material=material,
        dimensiones_m={k: _r(v) for k, v in dims.items()},
        geometria=Geometria(
            primitiva=primitiva,  # type: ignore[arg-type]
            parametros={k: _r(v) if not k.startswith("n_") else v for k, v in params.items()},
            nodo_glb=id_,
        ),
        transformacion=Transformacion(posicion=pos, rotacion_grados=rot),
        ancla=pos,
        relacionadas=relacionadas or [],
        articulaciones=[art],
        direccion_despiece=despiece[0],
        distancia_despiece_m=despiece[1],
        retirar_antes=retirar or [],
    )


def _fija(id_: str, nombre: str, padre: str | None, hijo: str) -> Articulacion:
    return Articulacion(id=id_, nombre=nombre, tipo=TipoArticulacion.FIJA, padre=padre, hijo=hijo)


def construir_moto(p: ParametrosMoto | None = None) -> Ensamblaje:
    """Construye el ensamblaje ``moto_honda`` (36+ piezas agrupadas en subconjuntos)."""
    p = p or ParametrosMoto()
    # ------------------------------------------------------------------ magnitudes base
    carrera = _sup("carrera_mm") / 1000
    diametro = _sup("diametro_mm") / 1000
    biela_l = _sup("longitud_biela_mm") / 1000
    r_man = carrera / 2
    rel_final = _sup("relacion_final")
    rel_primaria = _sup("relacion_primaria")
    cilindrada = _sup("cilindrada_nominal_cm3")

    ancho_t, perfil_t, rin_pulg = parsear_medida_llanta(p.medida_llanta_trasera)
    ancho_d, perfil_d, rin_d_pulg = parsear_medida_llanta(p.medida_llanta_delantera)
    r_t = radio_llanta_m(p.medida_llanta_trasera)
    r_d = radio_llanta_m(p.medida_llanta_delantera)
    seccion_t = ancho_t * perfil_t / 100 / 1000  # altura del flanco (m)
    seccion_d = ancho_d * perfil_d / 100 / 1000
    r_rin_t = rin_pulg * 25.4 / 2000
    r_rin_d = rin_d_pulg * 25.4 / 2000

    # Ejes y puntos de referencia (m)
    eje_trasero = (-0.63, r_t, 0.0)
    pivote = (-0.27, 0.34, 0.0)  # pivote del basculante
    cigue = (0.0, 0.33, 0.0)  # centro del cigüeñal
    pipa = (0.50, 0.70)  # centro de la pipa de dirección
    lanz = 27.0  # ángulo de lanzamiento de la dirección (grados)
    ux, uy = math.sin(math.radians(lanz)), -math.cos(math.radians(lanz))  # eje de horquilla, hacia abajo
    s_eje = (pipa[1] - r_d) / -uy
    eje_delantero = (pipa[0] + ux * s_eje, r_d, 0.0)
    distancia_ejes = eje_delantero[0] - eje_trasero[0]
    z_horq = 0.09
    s0 = -0.08  # inicio de los tubos fijos a lo largo del eje de horquilla (desde la pipa)

    def sobre_horquilla(s: float) -> tuple[float, float]:
        return (pipa[0] + ux * s, pipa[1] + uy * s)

    rot_horq = _rot_hacia(ux, uy)
    recorrido_horq = 0.12
    recorrido_amort = 0.05
    levante_valvula = 0.005
    osc_basculante = 8.0
    giro_biela = math.degrees(math.asin(r_man / biela_l))

    # Motor
    pin_pms = cigue[1] + r_man + biela_l  # altura del bulón en el PMS
    x_pinon = -0.20
    r_pinon = 0.03
    r_corona = r_pinon * rel_final
    z_cadena = 0.065

    piezas: list[Pieza] = []
    arts: list[Articulacion] = []

    # ================================================================== MOTOR EN CORTE
    piezas += [
        _p(
            "cilindro",
            "Cilindro (en corte)",
            "cilindro_motor",
            "motor",
            "Camisa del cilindro representada en corte (mitad del lado +Z retirada) para ver el interior.",
            "Guía al pistón y contiene la cámara de combustión.",
            "Aleación de aluminio con camisa (demostrativo)",
            {"diametro": diametro, "largo": 0.12},
            "cilindro_corte",
            {"radio_interior": diametro / 2, "radio_exterior": diametro / 2 + 0.012, "largo": 0.12},
            (cigue[0], 0.44, 0.0),
            ((0.0, 1.0, 0.0), 0.30),
            "j_cilindro",
            rot=(90.0, 0.0, 0.0),
            relacionadas=["piston", "bujia", "valvula_admision", "valvula_escape"],
            retirar=["bujia", "valvula_admision", "valvula_escape", "tubo_escape"],
        ),
        _p(
            "piston",
            "Pistón",
            "piston",
            "motor",
            "Émbolo cilíndrico que sube y baja dentro del cilindro (carrera tomada de fisica_moto).",
            "Transmite la presión de los gases a la biela y comprime la mezcla.",
            "Aleación de aluminio (demostrativo)",
            {"diametro": diametro - 0.001, "largo": 0.05, "carrera": carrera},
            "cilindro",
            {"radio": (diametro - 0.001) / 2, "largo": 0.05},
            (cigue[0], pin_pms + 0.006, 0.0),
            ((0.0, 1.0, 0.0), 0.14),
            "j_piston",
            rot=(90.0, 0.0, 0.0),
            relacionadas=["cilindro", "biela"],
            retirar=["cilindro"],
        ),
        _p(
            "biela",
            "Biela",
            "biela",
            "motor",
            "Barra que une el bulón del pistón con la muñequilla del cigüeñal "
            "(longitud entre centros de fisica_moto).",
            "Convierte el movimiento lineal del pistón en giro del cigüeñal.",
            "Acero forjado (demostrativo)",
            {"longitud_entre_centros": biela_l, "ancho": 0.016},
            "caja",
            {"ancho": 0.016, "alto": biela_l + 0.016, "largo": 0.008},
            (cigue[0], cigue[1] + r_man + biela_l / 2, 0.0),
            ((0.0, -1.0, 0.0), 0.12),
            "j_biela",
            relacionadas=["piston", "ciguenal"],
            retirar=["piston"],
        ),
        _p(
            "ciguenal",
            "Cigüeñal",
            "ciguenal",
            "motor",
            "Eje acodado con dos brazos y una muñequilla excéntrica; en el PMS la muñequilla queda arriba.",
            "Transforma el movimiento alternativo en rotación y entrega el par al tren de transmisión.",
            "Acero forjado (demostrativo)",
            {"excentricidad": r_man, "largo_eje": 0.09, "radio_brazo": 0.04},
            "manivela",
            {
                "radio_eje": 0.012,
                "largo_eje": 0.09,
                "radio_brazo": 0.04,
                "espesor_brazo": 0.010,
                "radio_muneca": 0.010,
                "largo_muneca": 0.016,
                "excentricidad": r_man,
            },
            cigue,
            ((0.0, 0.0, -1.0), 0.28),
            "j_ciguenal",
            relacionadas=["biela", "caja_cambios"],
            retirar=["biela"],
        ),
        _p(
            "valvula_admision",
            "Válvula de admisión",
            "valvula",
            "motor",
            "Válvula de vástago y cabeza circular que abre el conducto de admisión.",
            "Deja entrar la mezcla fresca durante la fase de admisión.",
            "Acero (demostrativo)",
            {"radio_vastago": 0.0035, "largo": 0.07, "radio_cabeza": 0.0095, "levante": levante_valvula},
            "cubo",
            {"radio": 0.0035, "largo": 0.07, "radio_brida": 0.0095, "espesor_brida": 0.002},
            (-0.0185, 0.535, 0.0),
            ((-0.5, 1.0, 0.0), 0.20),
            "j_valvula_admision",
            rot=(90.0, 0.0, 0.0),
            relacionadas=["cilindro", "bujia"],
        ),
        _p(
            "valvula_escape",
            "Válvula de escape",
            "valvula",
            "motor",
            "Válvula de vástago y cabeza circular que abre el conducto de escape.",
            "Evacúa los gases quemados durante la fase de escape.",
            "Acero resistente al calor (demostrativo)",
            {"radio_vastago": 0.0035, "largo": 0.07, "radio_cabeza": 0.0095, "levante": levante_valvula},
            "cubo",
            {"radio": 0.0035, "largo": 0.07, "radio_brida": 0.0095, "espesor_brida": 0.002},
            (0.0185, 0.535, 0.0),
            ((0.5, 1.0, 0.0), 0.20),
            "j_valvula_escape",
            rot=(90.0, 0.0, 0.0),
            relacionadas=["cilindro", "tubo_escape"],
        ),
        _p(
            "bujia",
            "Bujía",
            "bujia",
            "motor",
            "Elemento roscado con cabeza hexagonal que penetra en la cámara de combustión.",
            "Provee la chispa que inicia la combustión al final de la compresión.",
            "Acero con aislante cerámico (demostrativo)",
            {"radio": 0.004, "largo": 0.04},
            "tornillo",
            {"radio": 0.004, "largo": 0.04, "radio_cabeza": 0.0075, "alto_cabeza": 0.010},
            (0.0, 0.52, 0.0),
            ((0.0, 1.0, 0.0), 0.12),
            "j_bujia",
            rot=(90.0, 0.0, 0.0),
            relacionadas=["cilindro"],
        ),
    ]
    arts += [
        _fija("j_cilindro", "Cilindro fijo al chasis", "chasis", "cilindro"),
        Articulacion(
            id="j_piston",
            nombre="Carrera del pistón (PMS a PMI)",
            tipo=TipoArticulacion.PRISMATICA,
            padre="cilindro",
            hijo="piston",
            eje=(0.0, 1.0, 0.0),
            unidad="m",
            limites=LimitesMovimiento(minimo=-_r(carrera), maximo=0.0),
            descripcion="Valor 0 en el PMS y -carrera en el PMI (recorrido = carrera de fisica_moto).",
        ),
        Articulacion(
            id="j_biela",
            nombre="Oscilación de la biela sobre el bulón",
            tipo=TipoArticulacion.ROTACIONAL,
            padre="piston",
            hijo="biela",
            eje=(0.0, 0.0, 1.0),
            origen=(cigue[0], _r(pin_pms), 0.0),
            unidad="grados",
            limites=LimitesMovimiento(minimo=-_r(giro_biela), maximo=_r(giro_biela)),
            descripcion="Giro alrededor del bulón; límite asin(r/L), r = carrera/2, L = longitud de biela.",
        ),
        Articulacion(
            id="j_ciguenal",
            nombre="Giro del cigüeñal",
            tipo=TipoArticulacion.ROTACIONAL,
            padre=None,
            hijo="ciguenal",
            eje=(0.0, 0.0, 1.0),
            origen=cigue,
            unidad="grados",
            continua=True,
            descripcion="Rotación continua alrededor del eje Z; θ = 0 con el pistón en el PMS.",
        ),
        Articulacion(
            id="j_valvula_admision",
            nombre="Apertura de la válvula de admisión",
            tipo=TipoArticulacion.PRISMATICA,
            padre="cilindro",
            hijo="valvula_admision",
            eje=(0.0, -1.0, 0.0),
            unidad="m",
            limites=LimitesMovimiento(minimo=0.0, maximo=levante_valvula),
            descripcion="Desplazamiento hacia la cámara; el levante es demostrativo.",
        ),
        Articulacion(
            id="j_valvula_escape",
            nombre="Apertura de la válvula de escape",
            tipo=TipoArticulacion.PRISMATICA,
            padre="cilindro",
            hijo="valvula_escape",
            eje=(0.0, -1.0, 0.0),
            unidad="m",
            limites=LimitesMovimiento(minimo=0.0, maximo=levante_valvula),
            descripcion="Desplazamiento hacia la cámara; el levante es demostrativo.",
        ),
        _fija("j_bujia", "Bujía roscada al cilindro", "cilindro", "bujia"),
    ]

    # ================================================================== TRANSMISIÓN
    piezas += [
        _p(
            "caja_cambios",
            "Caja de cambios (carcasa)",
            "carcasa",
            "transmision",
            "Carcasa esquemática de la caja de cinco marchas, detrás del cigüeñal.",
            "Aloja los ejes y engranajes que adaptan el régimen del motor a la rueda.",
            "Aleación de aluminio (demostrativo)",
            {"ancho": 0.12, "alto": 0.12, "largo": 0.09},
            "caja",
            {"ancho": 0.12, "alto": 0.12, "largo": 0.09},
            (-0.13, 0.30, 0.0),
            ((-1.0, 0.0, -0.3), 0.20),
            "j_caja_cambios",
            relacionadas=["ciguenal", "pinon"],
            retirar=["pinon"],
        ),
        _p(
            "pinon",
            "Piñón de salida",
            "engranaje",
            "transmision",
            "Piñón de cadena de 14 dientes (representado como disco liso) en el eje de salida.",
            "Mueve la cadena de transmisión final.",
            "Acero (demostrativo)",
            {"radio": r_pinon, "espesor": 0.010, "dientes_demostrativos": 14.0},
            "cilindro",
            {"radio": r_pinon, "largo": 0.010},
            (x_pinon, r_t, z_cadena),
            ((0.0, 0.0, 1.0), 0.20),
            "j_pinon",
            relacionadas=["cadena", "caja_cambios"],
            retirar=["cadena"],
        ),
        _p(
            "cadena",
            "Cadena de transmisión",
            "cadena",
            "transmision",
            "Lazo cerrado esquemático que rodea piñón y corona (sin eslabones individuales).",
            "Transmite el giro del piñón a la corona de la rueda trasera.",
            "Acero (demostrativo)",
            {"distancia_entre_centros": x_pinon - eje_trasero[0], "ancho": 0.012},
            "cadena",
            {
                "distancia": x_pinon - eje_trasero[0],
                "radio_pinon": r_pinon + 0.004,
                "radio_corona": r_corona + 0.004,
                "grosor": 0.008,
                "ancho": 0.012,
            },
            ((x_pinon + eje_trasero[0]) / 2, r_t, z_cadena),
            ((0.0, 0.0, 1.0), 0.28),
            "j_cadena",
            relacionadas=["pinon", "corona"],
        ),
        _p(
            "corona",
            "Corona trasera",
            "engranaje",
            "transmision",
            "Corona de 42 dientes (representada como disco aligerado) solidaria a la rueda trasera.",
            "Recibe la cadena; una vuelta de rueda equivale a la relación final de vueltas del piñón.",
            "Acero (demostrativo)",
            {"radio": r_corona, "espesor": 0.006, "relacion_final": rel_final},
            "disco_ventilado",
            {
                "radio_exterior": r_corona,
                "radio_interior": 0.03,
                "espesor": 0.006,
                "radio_agujeros": 0.013,
                "n_agujeros": 5,
                "radio_circulo_agujeros": 0.06,
            },
            (eje_trasero[0], eje_trasero[1], z_cadena),
            ((0.0, 0.0, 1.0), 0.34),
            "j_corona",
            relacionadas=["cadena", "rin_trasero"],
            retirar=["cadena"],
        ),
    ]
    arts += [
        _fija("j_caja_cambios", "Caja de cambios atornillada al chasis", "chasis", "caja_cambios"),
        Articulacion(
            id="j_pinon",
            nombre="Giro del piñón (relación final respecto a la rueda)",
            tipo=TipoArticulacion.COMPUESTA,
            padre="chasis",
            hijo="pinon",
            eje=(0.0, 0.0, 1.0),
            origen=(x_pinon, _r(r_t), 0.0),
            unidad="grados",
            maestra="j_rueda_trasera",
            relacion=rel_final,
            descripcion="Gira relacion_final veces el ángulo de la rueda trasera (42/14).",
        ),
        _fija("j_cadena", "Lazo de cadena (esquemático, sin movimiento propio)", "chasis", "cadena"),
        Articulacion(
            id="j_corona",
            nombre="Corona solidaria a la rueda trasera",
            tipo=TipoArticulacion.COMPUESTA,
            padre="basculante",
            hijo="corona",
            eje=(0.0, 0.0, 1.0),
            origen=(eje_trasero[0], _r(eje_trasero[1]), 0.0),
            unidad="grados",
            maestra="j_rueda_trasera",
            relacion=1.0,
            descripcion="Mismo ángulo que la rueda trasera.",
        ),
    ]

    # ================================================================== CHASIS Y TANQUE
    cabeza = (0.48, 0.74)
    cola = (-0.32, 0.64)
    cuna_a = (0.46, 0.66)
    cuna_b = (0.10, 0.24)
    piezas += [
        _p(
            "chasis",
            "Chasis (columna principal)",
            "estructura",
            "chasis_tanque",
            "Tubo principal que une la pipa de dirección con la zona del asiento (esquemático).",
            "Soporta motor, tanque, asiento y suspensiones.",
            "Tubo de acero (demostrativo)",
            {"radio": 0.022, "largo": math.hypot(cabeza[0] - cola[0], cabeza[1] - cola[1])},
            "cilindro",
            {"radio": 0.022, "largo": math.hypot(cabeza[0] - cola[0], cabeza[1] - cola[1])},
            ((cabeza[0] + cola[0]) / 2, (cabeza[1] + cola[1]) / 2, 0.0),
            ((0.0, 1.0, 0.0), 0.50),
            "j_chasis",
            rot=_rot_hacia(cabeza[0] - cola[0], cabeza[1] - cola[1]),
            relacionadas=["pipa_direccion", "cuna_chasis", "tanque", "sillin"],
            retirar=[
                "tanque",
                "sillin",
                "cilindro",
                "ciguenal",
                "caja_cambios",
                "pipa_direccion",
                "cuna_chasis",
                "monoamortiguador",
                "basculante",
                "pinon",
                "cadena",
                "farola",
                "stop",
                "velocimetro",
                "unidad_cbs",
            ],
        ),
        _p(
            "cuna_chasis",
            "Cuna delantera del chasis",
            "estructura",
            "chasis_tanque",
            "Tubo inclinado que baja de la pipa de dirección por delante del motor.",
            "Rigidiza el chasis y apoya el motor por delante.",
            "Tubo de acero (demostrativo)",
            {"radio": 0.018, "largo": math.hypot(cuna_a[0] - cuna_b[0], cuna_a[1] - cuna_b[1])},
            "cilindro",
            {"radio": 0.018, "largo": math.hypot(cuna_a[0] - cuna_b[0], cuna_a[1] - cuna_b[1])},
            ((cuna_a[0] + cuna_b[0]) / 2, (cuna_a[1] + cuna_b[1]) / 2, 0.0),
            ((1.0, -0.3, 0.0), 0.30),
            "j_cuna_chasis",
            rot=_rot_hacia(cuna_a[0] - cuna_b[0], cuna_a[1] - cuna_b[1]),
            relacionadas=["chasis"],
        ),
        _p(
            "pipa_direccion",
            "Pipa de dirección",
            "estructura",
            "chasis_tanque",
            "Tubo corto inclinado según el ángulo de lanzamiento (27°, demostrativo).",
            "Aloja el eje de dirección y define la inclinación de la horquilla.",
            "Acero (demostrativo)",
            {"radio": 0.03, "largo": 0.14, "lanzamiento_grados": lanz},
            "cilindro",
            {"radio": 0.03, "largo": 0.14},
            (pipa[0], pipa[1], 0.0),
            ((0.0, 1.0, 0.0), 0.40),
            "j_pipa",
            rot=rot_horq,
            relacionadas=["chasis", "puente_horquilla"],
            retirar=["puente_horquilla"],
        ),
        _p(
            "tanque",
            "Tanque de combustible",
            "tanque",
            "chasis_tanque",
            "Volumen elipsoidal esquemático sobre la columna del chasis (sin marcas).",
            "Almacena el combustible; en el modelo solo ocupa volumen.",
            "Chapa de acero pintada (demostrativo)",
            {"largo": 0.40, "alto": 0.18, "ancho": 0.24},
            "elipsoide",
            {"radio_x": 0.20, "radio_y": 0.09, "radio_z": 0.12},
            (0.20, 0.80, 0.0),
            ((0.0, 1.0, 0.0), 0.30),
            "j_tanque",
            relacionadas=["chasis", "sillin"],
        ),
        _p(
            "sillin",
            "Sillín",
            "sillin",
            "chasis_tanque",
            "Asiento esquemático de una pieza.",
            "Apoya al conductor.",
            "Espuma y vinilo (demostrativo)",
            {"largo": 0.45, "alto": 0.07, "ancho": 0.26},
            "caja",
            {"ancho": 0.45, "alto": 0.07, "largo": 0.26},
            (-0.30, 0.70, 0.0),
            ((-0.3, 1.0, 0.0), 0.34),
            "j_sillin",
            relacionadas=["chasis", "tanque"],
        ),
    ]
    arts += [
        _fija("j_chasis", "Chasis como referencia fija del vehículo", None, "chasis"),
        _fija("j_cuna_chasis", "Cuna soldada al chasis", "chasis", "cuna_chasis"),
        _fija("j_pipa", "Pipa soldada al chasis", "chasis", "pipa_direccion"),
        _fija("j_tanque", "Tanque sujeto al chasis", "chasis", "tanque"),
        _fija("j_sillin", "Sillín sujeto al chasis", "chasis", "sillin"),
    ]

    # ================================================================== SUSPENSIÓN DELANTERA
    largo_tubo = 0.42
    largo_botella = 0.30
    c_tubo = sobre_horquilla(s0 + largo_tubo / 2)
    c_bot = sobre_horquilla(s0 + 0.26 + largo_botella / 2)
    c_puente = sobre_horquilla(-0.06)
    piezas.append(
        _p(
            "puente_horquilla",
            "Puente de la horquilla",
            "estructura",
            "suspension_delantera",
            "Travesaño que une ambos tubos fijos con la pipa de dirección.",
            "Mantiene paralelos los tubos de la horquilla y transmite la dirección.",
            "Aleación de aluminio (demostrativo)",
            {"ancho": 0.05, "alto": 0.035, "largo": 0.22},
            "caja",
            {"ancho": 0.05, "alto": 0.035, "largo": 0.22},
            (c_puente[0], c_puente[1], 0.0),
            ((0.0, 1.0, 0.0), 0.45),
            "j_puente",
            rot=(0.0, 0.0, lanz),
            relacionadas=["pipa_direccion", "tubo_izquierdo", "tubo_derecho"],
            retirar=["tubo_izquierdo", "tubo_derecho"],
        )
    )
    lados = (("izquierdo", "izquierda", -z_horq, -1.0), ("derecho", "derecha", z_horq, 1.0))
    for lado, lado_b, z, sig in lados:
        piezas.append(
            _p(
                f"tubo_{lado}",
                f"Tubo fijo {lado} de la horquilla",
                "tubo_suspension",
                "suspension_delantera",
                f"Tubo superior {lado} de la horquilla telescópica, fijo al puente.",
                "Guía el deslizamiento de la botella y aloja resorte y aceite (no modelados).",
                "Acero cromado (demostrativo)",
                {"radio": 0.0125, "largo": largo_tubo},
                "cilindro",
                {"radio": 0.0125, "largo": largo_tubo},
                (c_tubo[0], c_tubo[1], z),
                ((0.0, 1.0, 0.3 * sig), 0.40),
                f"j_tubo_{lado}",
                rot=rot_horq,
                relacionadas=["puente_horquilla", f"botella_{lado_b}"],
                retirar=[f"botella_{lado_b}"],
            )
        )
        piezas.append(
            _p(
                f"botella_{lado_b}",
                f"Botella {lado_b} de la horquilla",
                "botella",
                "suspension_delantera",
                f"Cuerpo inferior {lado} que desliza sobre el tubo fijo y sostiene el eje de la rueda.",
                "Absorbe irregularidades al comprimirse (recorrido demostrativo).",
                "Aleación de aluminio (demostrativo)",
                {"radio": 0.0165, "largo": largo_botella, "recorrido": recorrido_horq},
                "cilindro",
                {"radio": 0.0165, "largo": largo_botella},
                (c_bot[0], c_bot[1], z),
                ((0.4, -0.8, 0.5 * sig), 0.30),
                f"j_botella_{lado_b}",
                rot=rot_horq,
                relacionadas=[f"tubo_{lado}", "rin_delantero"],
                retirar=(
                    ["rin_delantero", "caliper_delantero"] if lado == "izquierdo" else ["rin_delantero"]
                ),
            )
        )
    arts += [
        _fija("j_puente", "Puente fijo a la pipa", "pipa_direccion", "puente_horquilla"),
        _fija("j_tubo_izquierdo", "Tubo izquierdo sujeto al puente", "puente_horquilla", "tubo_izquierdo"),
        _fija("j_tubo_derecho", "Tubo derecho sujeto al puente", "puente_horquilla", "tubo_derecho"),
        Articulacion(
            id="j_botella_izquierda",
            nombre="Compresión de la horquilla (botella izquierda)",
            tipo=TipoArticulacion.PRISMATICA,
            padre="tubo_izquierdo",
            hijo="botella_izquierda",
            eje=_unitario(-ux, -uy),
            unidad="m",
            limites=LimitesMovimiento(minimo=0.0, maximo=recorrido_horq),
            descripcion="La botella sube a lo largo del eje de la horquilla al comprimirse.",
        ),
        Articulacion(
            id="j_botella_derecha",
            nombre="Compresión de la horquilla (botella derecha)",
            tipo=TipoArticulacion.COMPUESTA,
            padre="tubo_derecho",
            hijo="botella_derecha",
            eje=_unitario(-ux, -uy),
            unidad="m",
            maestra="j_botella_izquierda",
            relacion=1.0,
            descripcion="Se comprime igual que la botella izquierda.",
        ),
    ]

    # ================================================================== SUSPENSIÓN TRASERA
    sup = (-0.17, 0.63)
    inf = (-0.42, 0.33)
    largo_amort = math.hypot(sup[0] - inf[0], sup[1] - inf[1])
    brazo_dx = eje_trasero[0] - pivote[0]
    brazo_dy = eje_trasero[1] - pivote[1]
    largo_brazo = math.hypot(brazo_dx, brazo_dy) + 0.04
    piezas += [
        _p(
            "monoamortiguador",
            "Monoamortiguador",
            "amortiguador",
            "suspension_trasera",
            "Conjunto cilíndrico único (resorte y amortiguador) entre el chasis y el basculante.",
            "Absorbe las irregularidades que recibe la rueda trasera (recorrido demostrativo).",
            "Acero y aluminio (demostrativo)",
            {"radio": 0.022, "largo": largo_amort, "recorrido": recorrido_amort},
            "cilindro",
            {"radio": 0.022, "largo": largo_amort},
            ((sup[0] + inf[0]) / 2, (sup[1] + inf[1]) / 2, 0.0),
            ((0.0, 0.5, -1.0), 0.30),
            "j_monoamortiguador",
            rot=_rot_hacia(sup[0] - inf[0], sup[1] - inf[1]),
            relacionadas=["chasis", "basculante"],
        ),
        _p(
            "basculante",
            "Basculante (monobrazo esquemático)",
            "basculante",
            "suspension_trasera",
            "Brazo oscilante de un solo lado que une el pivote del chasis con el eje trasero.",
            "Mantiene la rueda trasera y permite su recorrido vertical alrededor del pivote.",
            "Aleación de aluminio (demostrativo)",
            {"largo": largo_brazo, "alto": 0.04, "ancho": 0.03, "oscilacion_grados": osc_basculante},
            "caja",
            {"ancho": largo_brazo, "alto": 0.04, "largo": 0.03},
            ((pivote[0] + eje_trasero[0]) / 2, (pivote[1] + eje_trasero[1]) / 2, 0.10),
            ((0.0, 0.0, 1.0), 0.45),
            "j_basculante",
            rot=(0.0, 0.0, _r(math.degrees(math.atan2(brazo_dy, brazo_dx)) + 180.0)),
            relacionadas=["chasis", "monoamortiguador", "rin_trasero"],
            retirar=["rin_trasero", "monoamortiguador", "caliper_trasero", "disco_trasero", "corona"],
        ),
    ]
    arts += [
        Articulacion(
            id="j_monoamortiguador",
            nombre="Recorrido del monoamortiguador",
            tipo=TipoArticulacion.PRISMATICA,
            padre="chasis",
            hijo="monoamortiguador",
            eje=_unitario(sup[0] - inf[0], sup[1] - inf[1]),
            unidad="m",
            limites=LimitesMovimiento(minimo=0.0, maximo=recorrido_amort),
            descripcion="Compresión esquemática del conjunto (recorrido demostrativo).",
        ),
        Articulacion(
            id="j_basculante",
            nombre="Oscilación del basculante",
            tipo=TipoArticulacion.ROTACIONAL,
            padre="chasis",
            hijo="basculante",
            eje=(0.0, 0.0, 1.0),
            origen=pivote,
            unidad="grados",
            limites=LimitesMovimiento(minimo=-osc_basculante, maximo=osc_basculante),
            descripcion="Giro alrededor del pivote; límites demostrativos.",
        ),
    ]

    # ================================================================== RUEDAS Y LLANTAS
    for tag, nom, centro, r_ll, seccion, r_rin, ancho, medida, padre in (
        (
            "delantero",
            "delantero",
            eje_delantero,
            r_d,
            seccion_d,
            r_rin_d,
            ancho_d / 1000,
            p.medida_llanta_delantera,
            "botella_izquierda",
        ),
        (
            "trasero",
            "trasero",
            eje_trasero,
            r_t,
            seccion_t,
            r_rin_t,
            ancho_t / 1000,
            p.medida_llanta_trasera,
            "basculante",
        ),
    ):
        es_del = tag == "delantero"
        tag_f = "delantera" if es_del else "trasera"
        piezas.append(
            _p(
                f"rin_{tag}",
                f"Rin {nom}",
                "rin",
                "ruedas",
                f"Rin esquemático (disco aligerado con 6 ventanas) de la rueda {nom}.",
                "Soporta la llanta y gira sobre el eje de la rueda.",
                "Aleación de aluminio (demostrativo)",
                {"radio": r_rin, "espesor": 0.024},
                "disco_ventilado",
                {
                    "radio_exterior": r_rin + 0.003,
                    "radio_interior": 0.03,
                    "espesor": 0.024,
                    "radio_agujeros": 0.05,
                    "n_agujeros": 6,
                    "radio_circulo_agujeros": 0.125,
                },
                centro,
                ((0.0, 0.0, 1.0), 0.40 if es_del else 0.55),
                f"j_rueda_{tag_f}",
                relacionadas=[
                    f"llanta_{tag_f}",
                    f"disco_{tag}",
                    "botella_izquierda" if es_del else "basculante",
                ],
                retirar=(
                    ["llanta_delantera", "disco_delantero"]
                    if es_del
                    else ["llanta_trasera", "disco_trasero", "corona"]
                ),
            )
        )
        piezas.append(
            _p(
                f"llanta_{tag_f}",
                f"Llanta {nom} ({medida})",
                "llanta",
                "ruedas",
                f"Neumático {nom} de medida {medida} (radio exterior {r_ll:.4f} m desde fisica_moto); "
                "perfil circular esquemático, sin dibujo ni marcas.",
                "Transmite al suelo las fuerzas de tracción y frenado.",
                "Caucho (demostrativo)",
                {"radio_exterior": r_ll, "altura_flanco": seccion, "ancho_nominal": ancho},
                "toro",
                {"radio_mayor": r_ll - seccion / 2, "radio_menor": seccion / 2},
                centro,
                ((0.0, 0.0, -1.0), 0.50),
                f"j_llanta_{tag_f}",
                relacionadas=[f"rin_{tag}"],
            )
        )
        arts.append(
            Articulacion(
                id=f"j_rueda_{tag_f}",
                nombre=f"Giro de la rueda {nom}",
                tipo=TipoArticulacion.ROTACIONAL,
                padre=padre,
                hijo=f"rin_{tag}",
                eje=(0.0, 0.0, 1.0),
                origen=(_r(centro[0]), _r(centro[1]), 0.0),
                unidad="grados",
                continua=True,
                descripcion="Rotación continua alrededor del eje de la rueda.",
            )
        )
        arts.append(
            Articulacion(
                id=f"j_llanta_{tag_f}",
                nombre=f"Llanta {nom} solidaria al rin",
                tipo=TipoArticulacion.COMPUESTA,
                padre=padre,
                hijo=f"llanta_{tag_f}",
                eje=(0.0, 0.0, 1.0),
                origen=(_r(centro[0]), _r(centro[1]), 0.0),
                unidad="grados",
                maestra=f"j_rueda_{tag_f}",
                relacion=1.0,
                descripcion="Mismo ángulo que el rin.",
            )
        )

    # ================================================================== FRENOS
    z_disc_del, z_disc_tra = 0.05, -0.05
    r_disc_del, r_disc_tra = 0.14, 0.11
    espesor_disco = 0.004
    pinza_params = {
        "ancho": 0.07,
        "alto": 0.06,
        "ranura_largo": 0.024,
        "ranura_alto": 0.04,
        "largo_interior": 0.024,
        "largo_exterior": 0.010,
        "radio_cilindro": 0.0165,
    }
    for tag, centro, r_dis, z_dis, rot_y, _padre in (
        ("delantero", eje_delantero, r_disc_del, z_disc_del, 0.0, "botella_izquierda"),
        ("trasero", eje_trasero, r_disc_tra, z_disc_tra, 180.0, "basculante"),
    ):
        es_del = tag == "delantero"
        piezas.append(
            _p(
                f"disco_{tag}",
                f"Disco de freno {tag}",
                "disco",
                "frenos",
                f"Disco {tag} de {r_dis * 2 * 1000:.0f} mm de diámetro, con orificios, solidario a la rueda.",
                "Superficie sobre la que las pastillas generan la fricción que frena la rueda.",
                "Acero inoxidable (demostrativo)",
                {"diametro": 2 * r_dis, "espesor": espesor_disco},
                "disco_ventilado",
                {
                    "radio_exterior": r_dis,
                    "radio_interior": 0.05 if es_del else 0.04,
                    "espesor": espesor_disco,
                    "radio_agujeros": 0.006 if es_del else 0.005,
                    "n_agujeros": 8 if es_del else 6,
                    "radio_circulo_agujeros": 0.105 if es_del else 0.085,
                },
                (centro[0], centro[1], z_dis),
                ((0.0, 0.0, 1.0 if es_del else -1.0), 0.30),
                f"j_disco_{tag}",
                relacionadas=[f"caliper_{tag}", f"rin_{tag}"],
                retirar=[f"caliper_{tag}"],
            )
        )
        y_p = r_dis + 0.0025 + 0.03 - 0.04
        piezas.append(
            _p(
                f"caliper_{tag}",
                f"Cáliper {tag}",
                "pinza",
                "frenos",
                f"Pinza de un pistón (Ø{_sup('diametro_piston_m') * 1000:.0f} mm de fisica_moto, "
                "representado como cavidad) que abraza el disco.",
                "Convierte la presión hidráulica en fuerza de sujeción sobre las pastillas.",
                "Aleación de aluminio (demostrativo)",
                {"ancho": 0.07, "alto": 0.06, "diametro_piston": _sup("diametro_piston_m")},
                "pinza",
                pinza_params,
                (centro[0], centro[1] + y_p, z_dis),
                ((0.0, 1.0, 0.6 if es_del else -0.6), 0.25),
                f"j_caliper_{tag}",
                rot=(0.0, rot_y, 0.0),
                relacionadas=[f"disco_{tag}", "unidad_cbs"],
            )
        )
    piezas.append(
        _p(
            "unidad_cbs",
            "Unidad CBS (esquemática)",
            "unidad_hidraulica",
            "frenos",
            "Bloque hidráulico esquemático del frenado combinado (CBS); no modela válvulas ni circuitos.",
            "Representa el reparto de presión entre ambos discos (supuesto didáctico en fisica_moto).",
            "Aleación de aluminio (demostrativo)",
            {"ancho": 0.07, "alto": 0.05, "largo": 0.05},
            "caja",
            {"ancho": 0.07, "alto": 0.05, "largo": 0.05},
            (0.15, 0.60, 0.0),
            ((0.0, 1.0, 0.5), 0.25),
            "j_unidad_cbs",
            relacionadas=["caliper_delantero", "caliper_trasero"],
        )
    )
    arts += [
        Articulacion(
            id="j_disco_delantero",
            nombre="Disco delantero solidario a la rueda",
            tipo=TipoArticulacion.COMPUESTA,
            padre="botella_izquierda",
            hijo="disco_delantero",
            eje=(0.0, 0.0, 1.0),
            origen=(_r(eje_delantero[0]), _r(eje_delantero[1]), 0.0),
            unidad="grados",
            maestra="j_rueda_delantera",
            relacion=1.0,
            descripcion="Mismo ángulo que la rueda delantera.",
        ),
        Articulacion(
            id="j_disco_trasero",
            nombre="Disco trasero solidario a la rueda",
            tipo=TipoArticulacion.COMPUESTA,
            padre="basculante",
            hijo="disco_trasero",
            eje=(0.0, 0.0, 1.0),
            origen=(_r(eje_trasero[0]), _r(eje_trasero[1]), 0.0),
            unidad="grados",
            maestra="j_rueda_trasera",
            relacion=1.0,
            descripcion="Mismo ángulo que la rueda trasera.",
        ),
        _fija("j_caliper_delantero", "Cáliper sujeto a la botella", "botella_izquierda", "caliper_delantero"),
        _fija("j_caliper_trasero", "Cáliper sujeto al basculante", "basculante", "caliper_trasero"),
        _fija("j_unidad_cbs", "Unidad CBS sujeta al chasis", "chasis", "unidad_cbs"),
    ]

    # ================================================================== ELÉCTRICO
    piezas += [
        _p(
            "farola",
            "Farola",
            "luz",
            "electrico",
            "Faro delantero esquemático (volumen elipsoidal liso, sin marcas).",
            "Ilumina el camino; en el modelo solo ocupa volumen.",
            "Policarbonato (demostrativo)",
            {"radio_x": 0.05, "radio_y": 0.08, "radio_z": 0.08},
            "elipsoide",
            {"radio_x": 0.05, "radio_y": 0.08, "radio_z": 0.08},
            (0.60, 0.72, 0.0),
            ((1.0, 0.0, 0.0), 0.25),
            "j_farola",
            relacionadas=["pipa_direccion"],
        ),
        _p(
            "stop",
            "Luz trasera (stop)",
            "luz",
            "electrico",
            "Bloque trasero esquemático.",
            "Señala el frenado y la presencia del vehículo.",
            "Policarbonato (demostrativo)",
            {"ancho": 0.03, "alto": 0.03, "largo": 0.12},
            "caja",
            {"ancho": 0.03, "alto": 0.03, "largo": 0.12},
            (-0.54, 0.72, 0.0),
            ((-1.0, 0.0, 0.0), 0.25),
            "j_stop",
            relacionadas=["sillin"],
        ),
        _p(
            "velocimetro",
            "Velocímetro",
            "instrumento",
            "electrico",
            "Instrumento circular esquemático (disco liso) sobre la pipa de dirección.",
            "Muestra la velocidad y el régimen (en el visor, calculados con fisica_moto).",
            "Plástico (demostrativo)",
            {"radio": 0.04, "largo": 0.03},
            "cilindro",
            {"radio": 0.04, "largo": 0.03},
            (0.47, 0.84, 0.0),
            ((0.0, 1.0, 0.0), 0.25),
            "j_velocimetro",
            rot=(0.0, 90.0, 0.0),
            relacionadas=["pipa_direccion"],
        ),
    ]
    arts += [
        _fija("j_farola", "Farola sujeta a la pipa", "chasis", "farola"),
        _fija("j_stop", "Luz trasera sujeta al chasis", "chasis", "stop"),
        _fija("j_velocimetro", "Velocímetro sujeto al chasis", "chasis", "velocimetro"),
    ]

    # ================================================================== ESCAPE
    a, b = (0.05, 0.46), (-0.10, 0.19)
    largo_tubo_esc = math.hypot(a[0] - b[0], a[1] - b[1])
    piezas += [
        _p(
            "tubo_escape",
            "Tubo de escape (colector)",
            "escape",
            "escape",
            "Tubo inclinado que baja desde el motor hacia el silenciador (esquemático, a un costado).",
            "Conduce los gases quemados fuera del cilindro.",
            "Acero inoxidable (demostrativo)",
            {"radio": 0.014, "largo": largo_tubo_esc},
            "cilindro",
            {"radio": 0.014, "largo": largo_tubo_esc},
            ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.12),
            ((0.0, -0.3, 1.0), 0.25),
            "j_tubo_escape",
            rot=_rot_hacia(a[0] - b[0], a[1] - b[1]),
            relacionadas=["silenciador", "valvula_escape"],
            retirar=["silenciador"],
        ),
        _p(
            "silenciador",
            "Silenciador",
            "escape",
            "escape",
            "Cilindro horizontal esquemático junto a la rueda trasera.",
            "Atenúa el ruido de los gases de escape.",
            "Acero inoxidable (demostrativo)",
            {"radio": 0.035, "largo": 0.40},
            "cilindro",
            {"radio": 0.035, "largo": 0.40},
            (-0.32, 0.19, 0.14),
            ((-0.5, 0.0, 1.0), 0.30),
            "j_silenciador",
            rot=(0.0, 90.0, 0.0),
            relacionadas=["tubo_escape"],
        ),
    ]
    arts += [
        _fija("j_tubo_escape", "Colector sujeto al motor", "cilindro", "tubo_escape"),
        _fija("j_silenciador", "Silenciador sujeto al chasis", "chasis", "silenciador"),
    ]

    subconjuntos = [
        Subconjunto(
            id="motor",
            nombre="Motor en corte",
            padre=None,
            descripcion="Cilindro, pistón, biela, cigüeñal, válvulas y bujía (ciclo de cuatro tiempos).",
        ),
        Subconjunto(
            id="transmision",
            nombre="Transmisión",
            padre=None,
            descripcion="Caja de cambios, piñón, cadena y corona.",
        ),
        Subconjunto(
            id="chasis_tanque",
            nombre="Chasis y tanque",
            padre=None,
            descripcion="Estructura, pipa de dirección, tanque y sillín.",
        ),
        Subconjunto(
            id="suspension_delantera",
            nombre="Suspensión delantera",
            padre=None,
            descripcion="Horquilla telescópica: puente, tubos fijos y botellas.",
        ),
        Subconjunto(
            id="suspension_trasera",
            nombre="Suspensión trasera",
            padre=None,
            descripcion="Monoamortiguador y basculante.",
        ),
        Subconjunto(
            id="frenos",
            nombre="Frenos",
            padre=None,
            descripcion="Discos, cálipers y unidad CBS esquemática.",
        ),
        Subconjunto(
            id="ruedas",
            nombre="Ruedas y llantas",
            padre=None,
            descripcion="Rin y llanta delanteros y traseros (medidas desde fisica_moto).",
        ),
        Subconjunto(
            id="electrico",
            nombre="Sistema eléctrico",
            padre=None,
            descripcion="Farola, luz trasera y velocímetro.",
        ),
        Subconjunto(
            id="escape",
            nombre="Escape",
            padre=None,
            descripcion="Colector y silenciador.",
        ),
    ]

    parametros = {
        "carrera_m": _r(carrera),
        "diametro_cilindro_m": _r(diametro),
        "longitud_biela_m": _r(biela_l),
        "cilindrada_nominal_cm3": cilindrada,
        "relacion_primaria": rel_primaria,
        "relacion_final": rel_final,
        "radio_llanta_trasera_m": _r(r_t),
        "radio_llanta_delantera_m": _r(r_d),
        "distancia_entre_ejes_m": _r(distancia_ejes),
        "angulo_lanzamiento_grados": lanz,
        "recorrido_horquilla_m": recorrido_horq,
        "recorrido_monoamortiguador_m": recorrido_amort,
        "oscilacion_basculante_grados": osc_basculante,
        "levante_valvula_m": levante_valvula,
    }
    return Ensamblaje(
        id=ID_ENSAMBLAJE,
        nombre="Motocicleta (referencia genérica)",
        descripcion=(
            "Motocicleta naked de ~150 cc de referencia genérica: motor en corte, transmisión, chasis, "
            "suspensiones, frenos, ruedas, sistema eléctrico y escape. Esquemática y demostrativa."
        ),
        version="1.0.0",
        advertencia=ADVERTENCIA,
        subconjuntos=subconjuntos,
        piezas=piezas,
        articulaciones=arts,
        archivo_glb="modelos/moto_honda.glb",
        parametros=parametros,
        procedencia_parametros={k: "demostrativo" for k in parametros},
    )
