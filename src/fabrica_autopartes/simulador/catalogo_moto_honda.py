"""Motocicleta de referencia genérica (naked de ~150 cc) para el simulador 3D.

Ensamblaje ``moto_honda`` (ADR-017). La geometría es procedural, esquemática y DEMOSTRATIVA:
no incorpora logotipos, emblemas ni réplica de un modelo comercial, y no constituye un diseño
industrial certificado. Las medidas de motor, transmisión y llantas se toman de
``fisica_moto.SUPUESTOS_REFERENCIA`` (todas con procedencia ``demostrativo``); el resto de
dimensiones son valores elegidos para que el conjunto sea legible.

Todas las piezas se posicionan a partir de ``puntos_duros_moto`` (ejes, pipa de dirección, pivote
del basculante, anclajes del amortiguador y soportes del motor). Cada pieza (salvo el chasis, que
es la raíz) declara la pieza en la que se monta (``metadatos["montada_en"]``): la prueba de
conectividad exige que en la posición armada ambas se toquen o se solapen (tolerancia de 2 mm).
El orden de desmontaje se deriva de esos montajes (lo montado sobre una pieza se retira antes).

Sistema de referencia: X hacia delante, Y hacia arriba (suelo en Y = 0), Z hacia el lado derecho
del conductor. Los ejes de las ruedas, del cigüeñal y del basculante son paralelos a Z.

Coherencia con la física (``fisica_moto``): la carrera del pistón fija el recorrido de
``j_piston`` (de PMS a PMI, valores en [-carrera, 0] respecto al PMS, a lo largo del eje inclinado
del cilindro), la longitud de biela acota el giro de ``j_biela`` (±asin(r/L)) y la relación final
(14/42) fija la compuesta del piñón. La animación no valida propiedades mecánicas.
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, field_validator

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
    Sistema,
    Subconjunto,
    TipoArticulacion,
    Transformacion,
    Vector3,
)
from fabrica_autopartes.simulador.primitivas_moto import codificar_puntos, perfil_neumatico
from fabrica_autopartes.simulador.puntos_duros_moto import (
    ALTURA_SILLIN_M,
    DIENTES_CORONA,
    DIENTES_PINON,
    ENTRE_EJES_M,
    INCLINACION_CILINDRO_GRADOS,
    LANZAMIENTO_GRADOS,
    MEDIDA_DELANTERA_DEMO,
    PUNTOS,
    RADIO_PASO_CORONA_M,
    RADIO_PASO_PINON_M,
    Z_BRAZOS_M,
    Z_CADENA_M,
    Z_HORQUILLA_M,
    tabla_puntos_duros,
)

ID_ENSAMBLAJE = "moto_honda"
ADVERTENCIA = (
    "Referencia genérica esquemática de una motocicleta naked de ~150 cc, con geometría procedural "
    "y dimensiones demostrativas. No es un diseño industrial ni una réplica de un modelo comercial, "
    "no incluye logotipos ni emblemas y la animación no valida propiedades mecánicas."
)
REF_DEMO = "Modelo de demostración del proyecto (sin documentación de fabricante)"
TOLERANCIA_CONECTIVIDAD_M = 0.002


class ParametrosMoto(BaseModel):
    """Medidas de llanta (``ancho/perfil-rin``) que condicionan la geometría de las ruedas."""

    medida_llanta_trasera: str = str(SUPUESTOS_REFERENCIA["medida_llanta_trasera"].valor)
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


def _rot_hacia(dx: float, dy: float) -> Vector3:
    """Euler XYZ (grados) que orienta el eje local Z de una primitiva según (dx, dy) en el plano XY."""
    return (90.0, 0.0, _r(math.degrees(math.atan2(dx, -dy))))


def _unitario(dx: float, dy: float) -> Vector3:
    n = math.hypot(dx, dy)
    return (_r(dx / n), _r(dy / n), 0.0)


def _largo(pts: np.ndarray) -> float:
    return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))


class _Constructor:
    """Acumula piezas y articulaciones y deriva relaciones y orden de desmontaje."""

    def __init__(self) -> None:
        self.piezas: list[Pieza] = []
        self.arts: list[Articulacion] = []
        self._manuales: dict[str, list[str]] = {}

    # ------------------------------------------------------------------ primitivo
    def pieza(
        self,
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
        montada: str | None,
        rot: Vector3 = (0.0, 0.0, 0.0),
        art: str | None = None,
        padre_cin: str | None = None,
        retirar_extra: list[str] | None = None,
        relacionadas: list[str] | None = None,
    ) -> None:
        pos = (_r(pos[0]), _r(pos[1]), _r(pos[2]))
        art_id = art or f"j_{id_}"
        self.piezas.append(
            Pieza.model_validate(
                dict(
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
                        parametros={k: (v if k.startswith("n_") else _r(v)) for k, v in params.items()},
                        nodo_glb=id_,
                    ),
                    transformacion=Transformacion(posicion=pos, rotacion_grados=rot),
                    ancla=pos,
                    relacionadas=list(relacionadas or []),
                    articulaciones=[art_id],
                    direccion_despiece=despiece[0],
                    distancia_despiece_m=despiece[1],
                    retirar_antes=[],
                    metadatos={"montada_en": montada} if montada else {},
                    referencia_documental=REF_DEMO,
                )
            )
        )
        if retirar_extra:
            self._manuales[id_] = retirar_extra
        if art is None:  # pieza rígida respecto a su pieza de montaje (o a la indicada)
            padre = padre_cin or montada
            self.arts.append(
                Articulacion(
                    id=art_id,
                    nombre=f"{nombre} fija",
                    tipo=TipoArticulacion.FIJA,
                    padre=padre,
                    hijo=id_,
                )
            )

    # -------------------------------------------------------------- derivadas
    def tubo(
        self,
        id_: str,
        nombre: str,
        tipo: str,
        sub: str,
        descripcion: str,
        funcion: str,
        material: str,
        puntos: list[Vector3],
        radio: float,
        despiece: tuple[Vector3, float],
        montada: str | None,
        suavizado: int = 2,
        secciones: int = 12,
        **kw: object,
    ) -> None:
        pts = np.asarray(puntos, dtype=float)
        centro = (pts.min(axis=0) + pts.max(axis=0)) / 2
        params = {"radio": radio, "n_secciones": float(secciones), "n_suavizado": float(suavizado)}
        params.update(codificar_puntos(pts - centro, ("x", "y", "z")))
        self.pieza(
            id_,
            nombre,
            tipo,
            sub,
            descripcion,
            funcion,
            material,
            {"radio": radio, "largo_trayectoria": _largo(pts)},
            "tubo",
            params,
            (float(centro[0]), float(centro[1]), float(centro[2])),
            despiece,
            montada,
            **kw,  # type: ignore[arg-type]
        )

    def extrusion(
        self,
        id_: str,
        nombre: str,
        tipo: str,
        sub: str,
        descripcion: str,
        funcion: str,
        material: str,
        poligono: list[tuple[float, float]],
        espesor: float,
        z: float,
        despiece: tuple[Vector3, float],
        montada: str | None,
        **kw: object,
    ) -> None:
        pts = np.asarray(poligono, dtype=float)
        centro = (pts.min(axis=0) + pts.max(axis=0)) / 2
        params = {"espesor": espesor, **codificar_puntos(pts - centro, ("x", "y"))}
        ext = pts.max(axis=0) - pts.min(axis=0)
        self.pieza(
            id_,
            nombre,
            tipo,
            sub,
            descripcion,
            funcion,
            material,
            {"largo": float(ext[0]), "alto": float(ext[1]), "espesor": espesor},
            "extrusion",
            params,
            (float(centro[0]), float(centro[1]), z),
            despiece,
            montada,
            **kw,  # type: ignore[arg-type]
        )

    def revolucion(
        self,
        id_: str,
        nombre: str,
        tipo: str,
        sub: str,
        descripcion: str,
        funcion: str,
        material: str,
        perfil: list[tuple[float, float]],
        pos: Vector3,
        despiece: tuple[Vector3, float],
        montada: str | None,
        rot: Vector3 = (0.0, 0.0, 0.0),
        secciones: int = 40,
        cerrado: bool = False,
        **kw: object,
    ) -> None:
        arr = np.asarray(perfil, dtype=float)
        params = {"n_secciones": float(secciones), "n_cerrado": 1.0 if cerrado else 0.0}
        params.update(codificar_puntos(arr, ("r", "z")))
        self.pieza(
            id_,
            nombre,
            tipo,
            sub,
            descripcion,
            funcion,
            material,
            {"radio_maximo": float(arr[:, 0].max()), "largo_axial": float(np.ptp(arr[:, 1]))},
            "revolucion",
            params,
            pos,
            despiece,
            montada,
            rot=rot,
            **kw,  # type: ignore[arg-type]
        )

    def fija(self, id_: str, nombre: str, padre: str | None, hijo: str) -> None:
        self.arts.append(
            Articulacion(id=id_, nombre=nombre, tipo=TipoArticulacion.FIJA, padre=padre, hijo=hijo)
        )

    # -------------------------------------------------------------- cierre
    def cerrar(self) -> None:
        """Deriva ``retirar_antes`` y ``relacionadas`` del árbol de montaje."""
        por_id = {p.id: p for p in self.piezas}
        for p in self.piezas:
            padre = p.metadatos.get("montada_en")
            if padre is None:
                continue
            if padre not in por_id:
                raise ValueError(f"{p.id}: montada en pieza inexistente '{padre}'")
            if p.id not in por_id[padre].retirar_antes:
                por_id[padre].retirar_antes.append(p.id)
            if padre not in p.relacionadas:
                p.relacionadas.append(padre)
            if p.id not in por_id[padre].relacionadas:
                por_id[padre].relacionadas.append(p.id)
        for pid, extra in self._manuales.items():
            for e in extra:
                if e not in por_id[pid].retirar_antes:
                    por_id[pid].retirar_antes.append(e)


# Centro de la moto para el despiece radial (X, Y en metros; el plano medio es Z = 0).
CENTRO_DESPIECE_M = (0.0, 0.40)
_FACTOR_DISTANCIA_RADIAL = 1.35
_RADIO_MINIMO_DESPIECE_M = 0.30


def _despiece_radial(piezas: list[Pieza]) -> None:
    """Reorienta el despiece de cada pieza hacia afuera desde el centro de la moto (solo presentación).

    La componente en el plano XY es la dirección radial desde ``CENTRO_DESPIECE_M`` hasta la pieza
    (con un radio mínimo para las piezas centrales, que así se separan sobre todo a los lados); la
    componente Z conserva el signo y la proporción originales, de modo que las piezas que comparten
    posición (cubo, rin, llanta, disco) se escalonan en el eje de la rueda y las de un mismo
    subconjunto siguen una dirección coherente con su posición. El orden de desmontaje, la
    conectividad en posición armada y los movimientos del mecanismo no cambian.
    """
    cx, cy = CENTRO_DESPIECE_M
    for p in piezas:
        px, py, _pz = p.transformacion.posicion
        dx0, dy0, dz0 = p.direccion_despiece
        rx, ry = px - cx, py - cy
        norma = max(math.hypot(rx, ry), _RADIO_MINIMO_DESPIECE_M)
        ux, uy = rx / norma, ry / norma
        if uy < 0:  # hacia abajo se atenúa: las piezas no deben atravesar el piso de la escena
            uy *= 0.45
        # Parte axial original (z) normalizada con el máximo de las componentes originales.
        mx = max(abs(dx0), abs(dy0), abs(dz0)) or 1.0
        uz = dz0 / mx
        vx, vy, vz = ux, uy, uz * 0.9
        n = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
        p.direccion_despiece = (_r(vx / n), _r(vy / n), _r(vz / n))
        p.distancia_despiece_m = _r(min(p.distancia_despiece_m * _FACTOR_DISTANCIA_RADIAL, 1.0))


def sistemas_moto() -> list[Sistema]:
    """Sistemas funcionales de la vista «explorador» (fase 14): cada pieza pertenece a uno solo.

    Texto técnico genérico de la función de cada sistema; sin cifras, referencias de repuesto ni precios.
    """
    return [
        Sistema(
            id="motor",
            nombre="Motor",
            funcion=(
                "Convierte la energía del combustible en giro del cigüeñal mediante el ciclo de cuatro "
                "tiempos: admisión, compresión, expansión y escape."
            ),
            piezas=[
                "carter",
                "cilindro",
                "culata",
                "piston",
                "biela",
                "ciguenal",
                "valvula_admision",
                "valvula_escape",
                "bujia",
                "tapa_motor_izquierda",
                "tapa_motor_derecha",
                "cuerpo_aceleracion",
                "filtro_aire",
            ],
        ),
        Sistema(
            id="transmision",
            nombre="Transmisión",
            funcion=(
                "Adapta el régimen del motor a la velocidad de la rueda: la caja de cambios selecciona la "
                "relación y el piñón, la cadena y la corona llevan el giro a la rueda trasera."
            ),
            piezas=[
                "caja_cambios",
                "pinon",
                "cadena",
                "corona",
                "cubrecadena",
                "pedal_cambios",
                "tensor_izquierdo",
                "tensor_derecho",
            ],
        ),
        Sistema(
            id="frenos",
            nombre="Frenos",
            funcion=(
                "Convierten la fuerza de la manija o del pedal en presión hidráulica y, en los cálipers, en "
                "fricción de las pastillas contra los discos, que decelera las ruedas."
            ),
            piezas=[
                "manija_freno",
                "bomba_freno",
                "manguera_freno",
                "caliper_delantero",
                "disco_delantero",
                "pedal_freno",
                "caliper_trasero",
                "disco_trasero",
                "unidad_cbs",
            ],
        ),
        Sistema(
            id="suspension",
            nombre="Suspensión",
            funcion=(
                "Mantiene las ruedas en contacto con el suelo y absorbe las irregularidades: la horquilla "
                "telescópica guía la rueda delantera y el basculante con el monoamortiguador, la trasera."
            ),
            piezas=[
                "puente_horquilla",
                "tubo_izquierdo",
                "botella_izquierda",
                "tubo_derecho",
                "botella_derecha",
                "monoamortiguador",
                "basculante",
                "basculante_brazo_izquierdo",
                "basculante_travesano",
            ],
        ),
        Sistema(
            id="iluminacion",
            nombre="Iluminación",
            funcion=(
                "Hace visible el vehículo y su intención: la farola ilumina el camino, la luz trasera señala "
                "el frenado y las direccionales indican el giro."
            ),
            piezas=[
                "farola",
                "stop",
                "direccional_delantera_izquierda",
                "direccional_delantera_derecha",
                "direccional_trasera_izquierda",
                "direccional_trasera_derecha",
            ],
        ),
        Sistema(
            id="electrico",
            nombre="Sistema eléctrico",
            funcion=(
                "Almacena y distribuye la energía eléctrica que usan el encendido, las luces y los "
                "instrumentos del tablero."
            ),
            piezas=["bateria", "velocimetro"],
        ),
        Sistema(
            id="carroceria",
            nombre="Chasis y carrocería",
            funcion=(
                "El chasis es la estructura que une motor, suspensiones y dirección; la carrocería cubre los "
                "componentes, contiene el combustible y sostiene al conductor."
            ),
            piezas=[
                "chasis",
                "pipa_direccion",
                "cuna_chasis",
                "cuna_chasis_derecha",
                "subchasis",
                "tanque",
                "tapa_tanque",
                "sillin",
                "colin",
                "porta_placa",
                "cubierta_izquierda",
                "cubierta_derecha",
                "guardabarros_delantero",
                "guardabarros_trasero",
                "estribo_izquierdo",
                "estribo_derecho",
                "caballete_lateral",
            ],
        ),
        Sistema(
            id="ruedas",
            nombre="Ruedas",
            funcion=(
                "Transmiten al suelo las fuerzas de tracción, frenado y apoyo: la llanta hace el contacto, "
                "el rin la soporta y el cubo gira sobre el eje."
            ),
            piezas=[
                "cubo_delantero",
                "rin_delantero",
                "llanta_delantera",
                "cubo_trasero",
                "rin_trasero",
                "llanta_trasera",
            ],
        ),
        Sistema(
            id="escape",
            nombre="Escape",
            funcion="Conduce los gases quemados fuera del cilindro y atenúa su ruido antes de expulsarlos.",
            piezas=["tubo_escape", "silenciador"],
        ),
        Sistema(
            id="direccion",
            nombre="Dirección",
            funcion=(
                "Permite orientar la rueda delantera y reúne los mandos del conductor: manubrio, puños, "
                "manija de embrague y espejos."
            ),
            piezas=[
                "tija_superior",
                "manubrio",
                "puno_izquierdo",
                "puno_derecho",
                "manija_embrague",
                "espejo_izquierdo",
                "espejo_derecho",
            ],
        ),
    ]


def construir_moto(parametros: ParametrosMoto | None = None) -> Ensamblaje:
    """Construye el ensamblaje ``moto_honda`` a partir de los puntos duros."""
    pr = parametros or ParametrosMoto()
    P = PUNTOS
    b = _Constructor()

    # ------------------------------------------------------------------ magnitudes base
    carrera = _sup("carrera_mm") / 1000
    diametro = _sup("diametro_mm") / 1000
    biela_l = _sup("longitud_biela_mm") / 1000
    r_man = carrera / 2
    rel_final = _sup("relacion_final")
    rel_primaria = _sup("relacion_primaria")
    cilindrada = _sup("cilindrada_nominal_cm3")
    assert math.isclose(DIENTES_CORONA / DIENTES_PINON, rel_final)
    assert math.isclose(RADIO_PASO_CORONA_M / RADIO_PASO_PINON_M, rel_final)

    ancho_t, perfil_t, rin_pulg = parsear_medida_llanta(pr.medida_llanta_trasera)
    ancho_d, perfil_d, rin_d_pulg = parsear_medida_llanta(pr.medida_llanta_delantera)
    r_t = radio_llanta_m(pr.medida_llanta_trasera)
    r_d = radio_llanta_m(pr.medida_llanta_delantera)
    seccion_t = ancho_t * perfil_t / 100 / 1000
    seccion_d = ancho_d * perfil_d / 100 / 1000
    r_rin_t = rin_pulg * 25.4 / 2000
    r_rin_d = rin_d_pulg * 25.4 / 2000
    # Los puntos duros usan el radio de la medida predeterminada; con otra medida se reescala el eje
    eje_t = (P.eje_trasero[0], r_t)
    eje_d = (P.eje_delantero[0], r_d)

    pivote = P.pivote_basculante
    cig = P.ciguenal
    inc = INCLINACION_CILINDRO_GRADOS
    ax, ay = P.eje_cilindro
    ux, uy = P.eje_horquilla
    lanz = LANZAMIENTO_GRADOS
    rot_horq = _rot_hacia(ux, uy)
    rot_cil = _rot_hacia(ax, ay)  # eje local Z hacia arriba, a lo largo del cilindro
    rot_cil_inv = _rot_hacia(-ax, -ay)  # eje local Z hacia el cigüeñal
    rot_caja_cil = (0.0, 0.0, _r(-inc))  # eje local Y a lo largo del cilindro
    recorrido_horq = 0.12
    recorrido_amort = 0.05
    levante_valvula = 0.005
    osc_basculante = 8.0
    giro_biela = math.degrees(math.asin(r_man / biela_l))
    pin_pms = r_man + biela_l  # distancia cigüeñal-bulón en el PMS
    zf = Z_HORQUILLA_M
    zb = Z_BRAZOS_M
    zc = Z_CADENA_M
    x_pinon = cig[0] - 0.25
    pinon = (x_pinon, eje_t[1])
    d_cadena = pinon[0] - eje_t[0]

    def m(t: float, lateral: float = 0.0, z: float = 0.0) -> Vector3:
        x, y = P.en_motor(t, lateral)
        return (x, y, z)

    def fork(s: float, z: float = 0.0) -> Vector3:
        x, y = P.sobre_horquilla(s)
        return (x, y, z)

    def sc(dx: float, dy: float) -> tuple[float, float]:
        return (cig[0] + dx, cig[1] + dy)

    # ============================================================ CHASIS Y CARROCERÍA ESTRUCTURAL
    sub = "chasis_tanque"
    pipa_a = fork(-0.03)
    espina = [pipa_a, (0.30, 0.755, 0.0), (0.15, 0.745, 0.0), (-0.02, 0.725, 0.0), (-0.20, 0.690, 0.0)]
    b.tubo(
        "chasis",
        "Chasis (columna principal)",
        "estructura",
        sub,
        "Columna tubular que parte de la pipa de dirección y pasa sobre el motor hasta el subchasis.",
        "Soporta tanque, subchasis y suspensión trasera; es la referencia fija del vehículo.",
        "Tubo de acero (demostrativo)",
        espina,
        0.014,
        ((0.0, 1.0, 0.0), 0.50),
        None,
        art="j_chasis",
    )
    b.fija("j_chasis", "Chasis como referencia fija del vehículo", None, "chasis")
    b.pieza(
        "pipa_direccion",
        "Pipa de dirección",
        "estructura",
        sub,
        f"Tubo corto inclinado según el lanzamiento ({lanz:.0f}°, demostrativo).",
        "Aloja el eje de dirección y define la inclinación de la horquilla.",
        "Acero (demostrativo)",
        {"radio": 0.03, "largo": 0.13, "lanzamiento_grados": lanz},
        "cilindro",
        {"radio": 0.03, "largo": 0.13},
        (P.pipa[0], P.pipa[1], 0.0),
        ((0.0, 1.0, 0.0), 0.40),
        "chasis",
        rot=rot_horq,
        art="j_pipa",
    )
    b.fija("j_pipa", "Pipa soldada al chasis", "chasis", "pipa_direccion")
    soporte_d = P.soporte_motor_delantero
    soporte_i = P.soporte_motor_inferior
    soporte_t = P.soporte_motor_trasero

    def cuna(signo: float) -> list[Vector3]:
        z = 0.085 * signo
        return [
            fork(0.05),
            (0.43, 0.60, 0.05 * signo),
            (0.36, 0.46, z),
            (soporte_d[0], soporte_d[1], z),
            (soporte_i[0], soporte_i[1], z),
            (0.02, 0.19, z),
            (-0.10, 0.215, z),
            (soporte_t[0], soporte_t[1], z),
            (pivote[0], pivote[1], z),
        ]

    b.tubo(
        "cuna_chasis",
        "Cuna izquierda del chasis",
        "estructura",
        sub,
        "Tubo izquierdo de la doble cuna: baja de la pipa por delante del motor, lo abraza por debajo "
        "y sube hasta el pivote del basculante.",
        "Soporta el motor por sus puntos de anclaje y rigidiza el chasis.",
        "Tubo de acero (demostrativo)",
        cuna(-1.0),
        0.012,
        ((-0.3, -0.2, -1.0), 0.30),
        "pipa_direccion",
        suavizado=2,
    )
    b.tubo(
        "cuna_chasis_derecha",
        "Cuna derecha del chasis",
        "estructura",
        sub,
        "Tubo derecho de la doble cuna (simétrico del izquierdo).",
        "Soporta el motor por su lado derecho y rigidiza el chasis.",
        "Tubo de acero (demostrativo)",
        cuna(1.0),
        0.012,
        ((-0.3, -0.2, 1.0), 0.30),
        "pipa_direccion",
        suavizado=2,
    )
    rail_z = 0.10
    rails = [
        (-0.50, 0.700, rail_z),
        (-0.12, 0.700, rail_z),
        (-0.20, 0.690, 0.0),
        (-0.12, 0.700, -rail_z),
        (-0.50, 0.700, -rail_z),
        (-0.50, 0.700, rail_z),
    ]
    b.tubo(
        "subchasis",
        "Subchasis trasero",
        "estructura",
        sub,
        "Lazo tubular que sale del extremo de la columna y sostiene el sillín y el colín.",
        "Soporta sillín, carrocería trasera y batería.",
        "Tubo de acero (demostrativo)",
        rails,
        0.011,
        ((-1.0, 0.3, 0.0), 0.40),
        "chasis",
        suavizado=1,
    )
    # tanque: revolución alrededor de X (perfil radio–z con z hacia delante)
    perfil_tanque = [
        (0.0, -0.19),
        (0.05, -0.185),
        (0.085, -0.14),
        (0.098, -0.06),
        (0.100, 0.02),
        (0.092, 0.10),
        (0.07, 0.15),
        (0.05, 0.175),
        (0.03, 0.19),
        (0.0, 0.195),
    ]
    tank_c = (0.17, 0.80, 0.0)
    b.revolucion(
        "tanque",
        "Tanque de combustible",
        "tanque",
        sub,
        "Volumen de revolución con vientre y estrechamiento posterior, sin marcas ni emblemas.",
        "Almacena el combustible; en el modelo solo ocupa volumen.",
        "Chapa de acero pintada (demostrativo)",
        perfil_tanque,
        tank_c,
        ((0.0, 1.0, 0.0), 0.30),
        "chasis",
        rot=(0.0, 90.0, 0.0),
        secciones=48,
    )
    seat_top = ALTURA_SILLIN_M
    b.extrusion(
        "sillin",
        "Sillín",
        "sillin",
        sub,
        f"Asiento de perfil extruido; su cara superior está a {seat_top:.2f} m del suelo.",
        "Apoya al conductor.",
        "Espuma y vinilo (demostrativo)",
        [
            (0.06, 0.745),
            (0.04, 0.775),
            (0.0, seat_top - 0.002),
            (-0.20, seat_top),
            (-0.40, seat_top - 0.005),
            (-0.52, 0.775),
            (-0.52, 0.708),
            (0.06, 0.708),
        ],
        0.30,
        0.0,
        ((-0.3, 1.0, 0.0), 0.34),
        "subchasis",
    )
    for lado, s_ in (("izquierdo", -1.0), ("derecho", 1.0)):
        b.pieza(
            f"estribo_{lado}",
            f"Estribo {lado}",
            "estructura",
            sub,
            f"Apoyapiés {lado} (varilla) unido a la cuna del chasis.",
            "Sirve de apoyo al pie del conductor; en el modelo solo ocupa volumen.",
            "Acero (demostrativo)",
            {"radio": 0.009, "largo": 0.08},
            "cilindro",
            {"radio": 0.009, "largo": 0.08},
            (-0.10, 0.215, 0.125 * s_),
            ((0.0, -0.2, s_), 0.25),
            "cuna_chasis" if s_ < 0 else "cuna_chasis_derecha",
        )
    b.tubo(
        "caballete_lateral",
        "Caballete lateral",
        "estructura",
        sub,
        "Varilla articulada (representada fija, plegada) que baja desde la cuna izquierda.",
        "Sostiene la moto parada; en el modelo solo ocupa volumen.",
        "Acero (demostrativo)",
        [(-0.15, 0.245, -0.09), (-0.17, 0.15, -0.13), (-0.14, 0.03, -0.17)],
        0.008,
        ((0.0, -0.3, -1.0), 0.30),
        "cuna_chasis",
        suavizado=1,
        secciones=10,
    )

    # ============================================================ CARROCERÍA
    sub = "carroceria"
    b.extrusion(
        "colin",
        "Colín trasero",
        "carroceria",
        sub,
        "Cubierta trasera del asiento (perfil extruido).",
        "Cierra la línea posterior; en el modelo solo ocupa volumen.",
        "Plástico pintado (demostrativo)",
        [(-0.46, 0.708), (-0.62, 0.735), (-0.63, 0.775), (-0.46, 0.785)],
        0.14,
        0.0,
        ((-1.0, 0.3, 0.0), 0.35),
        "sillin",
    )
    b.pieza(
        "porta_placa",
        "Porta placa",
        "carroceria",
        sub,
        "Soporte plano de la placa (sin placa ni texto).",
        "Sujeta la placa de matrícula.",
        "Plástico (demostrativo)",
        {"ancho": 0.006, "alto": 0.12, "largo": 0.20},
        "caja",
        {"ancho": 0.006, "alto": 0.12, "largo": 0.20},
        (-0.625, 0.69, 0.0),
        ((-1.0, -0.2, 0.0), 0.30),
        "colin",
    )
    for lado, s_ in (("izquierda", -1.0), ("derecha", 1.0)):
        b.extrusion(
            f"cubierta_{lado}",
            f"Cubierta lateral {lado}",
            "carroceria",
            sub,
            f"Panel lateral {lado} bajo el sillín (perfil extruido).",
            "Cubre la zona de la batería y el subchasis.",
            "Plástico pintado (demostrativo)",
            [(-0.10, 0.60), (-0.45, 0.62), (-0.50, 0.715), (-0.10, 0.715)],
            0.012,
            0.116 * s_,
            ((0.0, 0.1, s_), 0.35),
            "subchasis",
        )
    b.pieza(
        "tapa_tanque",
        "Tapa del tanque",
        "tanque",
        sub,
        "Tapón circular liso sobre el tanque.",
        "Cierra la boca de llenado.",
        "Aluminio (demostrativo)",
        {"radio": 0.032, "largo": 0.012},
        "cilindro",
        {"radio": 0.032, "largo": 0.012},
        (0.20, tank_c[1] + 0.098 + 0.005, 0.0),
        ((0.0, 1.0, 0.0), 0.25),
        "tanque",
        rot=(90.0, 0.0, 0.0),
    )
    ang_g = np.radians(np.arange(50, 151, 10))
    ro_g, ri_g = r_d + 0.040, r_d + 0.030
    arco_f = [(eje_d[0] + ro_g * math.cos(a), eje_d[1] + ro_g * math.sin(a)) for a in ang_g]
    arco_f += [(eje_d[0] + ri_g * math.cos(a), eje_d[1] + ri_g * math.sin(a)) for a in ang_g[::-1]]
    b.extrusion(
        "guardabarros_delantero",
        "Guardabarros delantero",
        "carroceria",
        sub,
        "Arco extruido sobre la rueda delantera, fijado a los tubos de la horquilla (no se comprime "
        "con ella).",
        "Protege de proyecciones; en el modelo solo ocupa volumen.",
        "Plástico (demostrativo)",
        arco_f,
        0.19,
        0.0,
        ((0.0, 1.0, 0.0), 0.30),
        "tubo_derecho",
    )
    ro_t, ri_t = r_t + 0.035, r_t + 0.025

    def pol(a_deg: float, r_: float) -> tuple[float, float]:
        a_ = math.radians(a_deg)
        return (eje_t[0] + r_ * math.cos(a_), eje_t[1] + r_ * math.sin(a_))

    x80, x88 = pol(80, ro_t)[0], pol(88, ro_t)[0]
    arco_t = [pol(a_, ro_t) for a_ in (62, 68, 74)]
    arco_t += [pol(80, ro_t), (x80, 0.74), (x88, 0.74), pol(88, ro_t)]
    arco_t += [pol(a_, ro_t) for a_ in (96, 104, 112, 120, 128, 135)]
    arco_t += [pol(a_, ri_t) for a_ in (135, 128, 120, 112, 104, 96, 88, 80, 74, 68, 62)]
    b.extrusion(
        "guardabarros_trasero",
        "Guardabarros trasero",
        "carroceria",
        sub,
        "Arco extruido sobre la rueda trasera con una ménsula que sube hasta el colín.",
        "Protege de proyecciones; en el modelo solo ocupa volumen.",
        "Plástico (demostrativo)",
        arco_t,
        0.15,
        0.0,
        ((-1.0, 0.5, 0.0), 0.30),
        "colin",
    )

    # ============================================================ MOTOR EN CORTE
    sub = "motor"
    # Cárter: perfil extruido (mitad izquierda, z < -0.02); la mitad derecha queda abierta (corte)
    perfil_carter = [
        (0.115, -0.03),
        (0.12, 0.03),
        (0.10, 0.09),
        (0.05, 0.125),
        (-0.02, 0.135),
        (-0.09, 0.115),
        (-0.12, 0.085),
        (-0.24, 0.085),
        (-0.29, 0.05),
        (-0.30, -0.07),
        (-0.26, -0.115),
        (-0.12, -0.125),
        (-0.07, -0.145),
        (0.0, -0.15),
        (0.07, -0.135),
        (0.105, -0.09),
    ]
    b.extrusion(
        "carter",
        "Cárter del motor (en corte)",
        "carcasa",
        sub,
        "Semicárter izquierdo extruido; el lado derecho se omite para mostrar cigüeñal, biela y pistón.",
        "Aloja el cigüeñal y soporta el cilindro; se apoya en la cuna del chasis por los soportes del motor.",
        "Aleación de aluminio (demostrativo)",
        [sc(x, y) for x, y in perfil_carter],
        0.055,
        -0.0475,
        ((0.0, 0.0, -1.0), 0.30),
        "cuna_chasis",
    )
    t_cil = 0.1125
    b.pieza(
        "cilindro",
        "Cilindro (en corte)",
        "cilindro_motor",
        sub,
        "Camisa del cilindro con aletas, inclinada hacia delante y representada en corte (mitad +Z retirada) "
        "para ver el pistón y la biela en su interior.",
        "Guía al pistón y contiene la cámara de combustión.",
        "Aleación de aluminio con camisa (demostrativo)",
        {"diametro": diametro, "largo": 0.125, "inclinacion_grados": inc},
        "cilindro_corte",
        {
            "radio_interior": diametro / 2,
            "radio_exterior": diametro / 2 + 0.012,
            "largo": 0.125,
            "n_aletas": 7,
            "alto_aleta": 0.004,
            "radio_aleta": diametro / 2 + 0.025,
        },
        m(t_cil),
        ((0.3, 1.0, 0.0), 0.30),
        "carter",
        rot=rot_cil,
        art="j_cilindro",
    )
    b.fija("j_cilindro", "Cilindro fijo al cárter", "carter", "cilindro")
    b.pieza(
        "culata",
        "Culata (en corte)",
        "cilindro_motor",
        sub,
        "Culata con aletas y techo cerrado, en corte; aloja las válvulas y la bujía.",
        "Cierra la cámara de combustión y guía válvulas y bujía.",
        "Aleación de aluminio (demostrativo)",
        {"radio": diametro / 2 + 0.021, "largo": 0.072},
        "cilindro_corte",
        {
            "radio_interior": 0.034,
            "radio_exterior": 0.050,
            "largo": 0.072,
            "tapa": 0.016,
            "n_aletas": 4,
            "alto_aleta": 0.004,
            "radio_aleta": 0.058,
        },
        m(0.210),
        ((0.3, 1.0, 0.0), 0.45),
        "cilindro",
        rot=rot_cil,
    )
    b.pieza(
        "piston",
        "Pistón",
        "piston",
        sub,
        "Émbolo cilíndrico que sube y baja dentro del cilindro inclinado (carrera tomada de fisica_moto).",
        "Transmite la presión de los gases a la biela y comprime la mezcla.",
        "Aleación de aluminio (demostrativo)",
        {"diametro": diametro - 0.001, "largo": 0.05, "carrera": carrera},
        "cilindro",
        {"radio": (diametro - 0.001) / 2, "largo": 0.05},
        m(pin_pms + 0.006),
        ((0.3, 1.0, 0.0), 0.16),
        "biela",
        rot=rot_cil,
        art="j_piston",
        retirar_extra=["cilindro"],
    )
    b.pieza(
        "biela",
        "Biela",
        "biela",
        sub,
        "Barra que une el bulón del pistón con la muñequilla del cigüeñal (longitud entre centros de "
        "fisica_moto).",
        "Convierte el movimiento lineal del pistón en giro del cigüeñal.",
        "Acero forjado (demostrativo)",
        {"longitud_entre_centros": biela_l, "ancho": 0.016},
        "caja",
        {"ancho": 0.016, "alto": biela_l + 0.016, "largo": 0.008},
        m(r_man + biela_l / 2),
        ((0.0, 0.0, 1.0), 0.14),
        "ciguenal",
        rot=rot_caja_cil,
        art="j_biela",
    )
    b.pieza(
        "ciguenal",
        "Cigüeñal",
        "ciguenal",
        sub,
        "Eje acodado con dos brazos y una muñequilla excéntrica; en el PMS la muñequilla queda sobre "
        "el eje del cilindro.",
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
        (cig[0], cig[1], 0.0),
        ((0.0, 0.0, 1.0), 0.28),
        "carter",
        rot=rot_caja_cil,
        art="j_ciguenal",
    )
    for nombre_v, lat, id_v, desc_v, fun_v in (
        (
            "admisión",
            -0.0185,
            "valvula_admision",
            "abre el conducto de admisión",
            "Deja entrar la mezcla fresca durante la fase de admisión.",
        ),
        (
            "escape",
            0.0185,
            "valvula_escape",
            "abre el conducto de escape",
            "Evacúa los gases quemados durante la fase de escape.",
        ),
    ):
        b.pieza(
            id_v,
            f"Válvula de {nombre_v}",
            "valvula",
            sub,
            f"Válvula de vástago y cabeza circular que {desc_v}; se desplaza a lo largo del eje del "
            f"cilindro.",
            fun_v,
            "Acero (demostrativo)",
            {"radio_vastago": 0.0035, "largo": 0.07, "radio_cabeza": 0.0095, "levante": levante_valvula},
            "cubo",
            {"radio": 0.0035, "largo": 0.07, "radio_brida": 0.0095, "espesor_brida": 0.002},
            m(0.2105, lat),
            ((0.5 * (1 if lat > 0 else -1), 1.0, 0.0), 0.20),
            "culata",
            rot=rot_cil_inv,
            art=f"j_{id_v}",
        )
    b.pieza(
        "bujia",
        "Bujía",
        "bujia",
        sub,
        "Elemento roscado con cabeza hexagonal que penetra en la cámara de combustión por el techo "
        "de la culata.",
        "Provee la chispa que inicia la combustión al final de la compresión.",
        "Acero con aislante cerámico (demostrativo)",
        {"radio": 0.004, "largo": 0.045},
        "tornillo",
        {"radio": 0.004, "largo": 0.045, "radio_cabeza": 0.0075, "alto_cabeza": 0.012},
        m(0.2225),
        ((0.0, 1.0, 0.0), 0.14),
        "culata",
        rot=rot_cil_inv,
        art="j_bujia",
    )
    b.fija("j_bujia", "Bujía roscada a la culata", "culata", "bujia")
    b.pieza(
        "tapa_motor_izquierda",
        "Tapa izquierda del motor",
        "carcasa",
        sub,
        "Tapa circular del lado izquierdo (generador), con perfil de revolución.",
        "Cubre el extremo del cigüeñal.",
        "Aleación de aluminio (demostrativo)",
        {"radio": 0.065, "espesor": 0.015},
        "revolucion",
        {
            "n_secciones": 40.0,
            "n_cerrado": 0.0,
            **codificar_puntos(
                [(0.0, -0.0075), (0.06, -0.0075), (0.065, -0.003), (0.065, 0.0075), (0.0, 0.0075)], ("r", "z")
            ),
        },
        (cig[0], cig[1], -0.0815),
        ((0.0, 0.0, -1.0), 0.40),
        "carter",
    )
    b.pieza(
        "tapa_motor_derecha",
        "Tapa derecha del motor (embrague)",
        "carcasa",
        sub,
        "Tapa circular del embrague sobre la caja de cambios, a la derecha.",
        "Cubre el embrague (no modelado).",
        "Aleación de aluminio (demostrativo)",
        {"radio": 0.045, "espesor": 0.016},
        "cilindro",
        {"radio": 0.045, "largo": 0.016},
        (cig[0] - 0.145, cig[1] - 0.02, 0.082),
        ((0.0, 0.0, 1.0), 0.35),
        "caja_cambios",
    )
    b.tubo(
        "cuerpo_aceleracion",
        "Cuerpo de aceleración",
        "carcasa",
        sub,
        "Conducto de admisión que sale de la culata hacia atrás.",
        "Dosifica el aire de admisión.",
        "Aluminio (demostrativo)",
        [m(0.205, -0.04), m(0.205, -0.125)],
        0.017,
        ((-1.0, 0.3, 0.0), 0.25),
        "culata",
        suavizado=0,
    )
    fa = m(0.205, -0.19)
    b.pieza(
        "filtro_aire",
        "Caja del filtro de aire",
        "carcasa",
        sub,
        "Caja prismática bajo el tanque, detrás del cilindro.",
        "Filtra el aire antes del cuerpo de aceleración.",
        "Plástico (demostrativo)",
        {"ancho": 0.14, "alto": 0.12, "largo": 0.14},
        "caja",
        {"ancho": 0.14, "alto": 0.12, "largo": 0.14},
        fa,
        ((-1.0, 0.2, 0.0), 0.30),
        "cuerpo_aceleracion",
    )

    # ============================================================ TRANSMISIÓN
    sub = "transmision"
    perfil_caja = [
        (-0.11, -0.12),
        (-0.26, -0.115),
        (-0.30, -0.07),
        (-0.29, 0.05),
        (-0.24, 0.085),
        (-0.11, 0.085),
    ]
    b.extrusion(
        "caja_cambios",
        "Caja de cambios (carcasa)",
        "carcasa",
        sub,
        "Carcasa de la caja de cinco marchas (semicárter derecho trasero), unida al semicárter izquierdo.",
        "Aloja los ejes y engranajes que adaptan el régimen del motor a la rueda.",
        "Aleación de aluminio (demostrativo)",
        [sc(x, y) for x, y in perfil_caja],
        0.10,
        0.025,
        ((0.0, 0.0, 1.0), 0.22),
        "carter",
        art="j_caja_cambios",
    )
    b.fija("j_caja_cambios", "Caja de cambios atornillada al cárter", "carter", "caja_cambios")
    b.pieza(
        "pinon",
        "Piñón de salida (14 dientes)",
        "engranaje",
        sub,
        f"Piñón de cadena de {DIENTES_PINON} dientes (radio de paso {RADIO_PASO_PINON_M} m) en el eje "
        f"de salida.",
        "Mueve la cadena de transmisión final.",
        "Acero (demostrativo)",
        {
            "radio": RADIO_PASO_PINON_M,
            "radio_paso": RADIO_PASO_PINON_M,
            "espesor": 0.006,
            "dientes": float(DIENTES_PINON),
        },
        "engranaje",
        {
            "n_dientes": float(DIENTES_PINON),
            "radio_punta": RADIO_PASO_PINON_M + 0.003,
            "radio_raiz": RADIO_PASO_PINON_M - 0.003,
            "espesor": 0.006,
            "radio_agujero": 0.008,
        },
        (pinon[0], pinon[1], zc),
        ((0.0, 0.0, 1.0), 0.22),
        "caja_cambios",
        art="j_pinon",
    )
    b.pieza(
        "cadena",
        "Cadena de transmisión",
        "cadena",
        sub,
        "Lazo cerrado que rodea piñón y corona (sin eslabones: el visor los instancia sobre esta "
        "trayectoria).",
        "Transmite el giro del piñón a la corona de la rueda trasera.",
        "Acero (demostrativo)",
        {"distancia_entre_centros": d_cadena, "ancho": 0.012},
        "cadena",
        {
            "distancia": d_cadena,
            "radio_pinon": RADIO_PASO_PINON_M + 0.004,
            "radio_corona": RADIO_PASO_CORONA_M + 0.004,
            "grosor": 0.008,
            "ancho": 0.012,
        },
        ((pinon[0] + eje_t[0]) / 2, eje_t[1], zc),
        ((0.0, 0.0, 1.0), 0.30),
        "corona",
        art="j_cadena",
    )
    b.fija("j_cadena", "Lazo de cadena (esquemático, sin movimiento propio)", "chasis", "cadena")
    b.pieza(
        "corona",
        "Corona trasera (42 dientes)",
        "engranaje",
        sub,
        f"Corona de {DIENTES_CORONA} dientes (radio de paso {RADIO_PASO_CORONA_M} m) solidaria a la "
        f"rueda trasera.",
        "Recibe la cadena; una vuelta de rueda equivale a la relación final de vueltas del piñón.",
        "Acero (demostrativo)",
        {
            "radio": RADIO_PASO_CORONA_M,
            "radio_paso": RADIO_PASO_CORONA_M,
            "espesor": 0.006,
            "relacion_final": rel_final,
            "dientes": float(DIENTES_CORONA),
        },
        "engranaje",
        {
            "n_dientes": float(DIENTES_CORONA),
            "radio_punta": RADIO_PASO_CORONA_M + 0.003,
            "radio_raiz": RADIO_PASO_CORONA_M - 0.003,
            "espesor": 0.006,
            "radio_agujero": 0.03,
            "n_aligeramientos": 5.0,
            "radio_aligeramiento": 0.014,
            "radio_circulo_aligeramiento": 0.068,
        },
        (eje_t[0], eje_t[1], zc),
        ((0.0, 0.0, 1.0), 0.36),
        "cubo_trasero",
        art="j_corona",
    )
    top_a = (pinon[0] - 0.02, pinon[1] + 0.036)
    top_b = (eje_t[0] + 0.04, eje_t[1] + RADIO_PASO_CORONA_M + 0.004)
    b.extrusion(
        "cubrecadena",
        "Cubrecadena",
        "carroceria",
        sub,
        "Protector plano sobre el ramal superior de la cadena, fijado al brazo derecho del basculante.",
        "Evita el contacto con la cadena; en el modelo solo ocupa volumen.",
        "Plástico (demostrativo)",
        [
            (top_a[0], top_a[1] + 0.012),
            (top_b[0], top_b[1] + 0.012),
            (top_b[0], top_b[1] - 0.010),
            (top_a[0], top_a[1] - 0.010),
        ],
        0.004,
        0.0875,
        ((0.0, 1.0, 1.0), 0.20),
        "basculante",
        padre_cin="basculante",
    )
    b.tubo(
        "pedal_cambios",
        "Pedal de cambios",
        "estructura",
        sub,
        "Palanca izquierda del selector de marchas, unida al semicárter.",
        "Selecciona la marcha (no modelada).",
        "Acero (demostrativo)",
        [
            (pinon[0], pinon[1] - 0.025, -0.07),
            (pinon[0], 0.26, -0.14),
            (-0.05, 0.235, -0.145),
            (0.0, 0.232, -0.145),
        ],
        0.007,
        ((0.0, -0.2, -1.0), 0.30),
        "carter",
        suavizado=1,
        secciones=10,
    )
    for lado, s_ in (("izquierdo", -1.0), ("derecho", 1.0)):
        b.pieza(
            f"tensor_{lado}",
            f"Tensor {lado} de cadena",
            "estructura",
            sub,
            f"Regulador {lado} del eje trasero (pieza rectangular) sobre el brazo del basculante.",
            "Permite tensar la cadena; en el modelo solo ocupa volumen.",
            "Acero (demostrativo)",
            {"ancho": 0.05, "alto": 0.03, "largo": 0.014},
            "caja",
            {"ancho": 0.05, "alto": 0.03, "largo": 0.014},
            (eje_t[0] - 0.02, eje_t[1], (zb + 0.0) * s_),
            ((-0.5, 0.0, s_), 0.22),
            "basculante" if s_ > 0 else "basculante_brazo_izquierdo",
            padre_cin="basculante",
        )

    # ============================================================ SUSPENSIÓN DELANTERA Y DIRECCIÓN
    sub = "suspension_delantera"
    largo_tubo = 0.42
    largo_botella = 0.32
    s0 = -0.09
    s_bot0 = 0.29
    yoke = (0.0, 0.0, lanz)
    b.pieza(
        "puente_horquilla",
        "Puente inferior de la horquilla",
        "estructura",
        sub,
        "Tija inferior: travesaño que une ambos tubos fijos con la pipa de dirección.",
        "Mantiene paralelos los tubos de la horquilla y transmite la dirección.",
        "Aleación de aluminio (demostrativo)",
        {"ancho": 0.04, "alto": 0.035, "largo": 0.22},
        "caja",
        {"ancho": 0.04, "alto": 0.035, "largo": 0.22},
        fork(0.075),
        ((0.0, 1.0, 0.0), 0.45),
        "pipa_direccion",
        rot=yoke,
        art="j_puente",
    )
    b.fija("j_puente", "Puente fijo a la pipa", "pipa_direccion", "puente_horquilla")
    perfil_tubo = [
        (0.0, -largo_tubo / 2),
        (0.011, -largo_tubo / 2),
        (0.0125, -largo_tubo / 2 + 0.004),
        (0.0125, largo_tubo / 2 - 0.004),
        (0.011, largo_tubo / 2),
        (0.0, largo_tubo / 2),
    ]
    perfil_bot = [
        (0.0, -largo_botella / 2),
        (0.0145, -largo_botella / 2),
        (0.0165, -largo_botella / 2 + 0.01),
        (0.0165, largo_botella / 2 - 0.006),
        (0.0145, largo_botella / 2),
        (0.0, largo_botella / 2),
    ]
    for lado, lado_b, z, sig in (("izquierdo", "izquierda", -zf, -1.0), ("derecho", "derecha", zf, 1.0)):
        b.revolucion(
            f"tubo_{lado}",
            f"Barra fija {lado} de la horquilla",
            "tubo_suspension",
            sub,
            f"Barra superior {lado} de la horquilla telescópica (perfil de revolución), fija al puente.",
            "Guía el deslizamiento de la botella y aloja resorte y aceite (no modelados).",
            "Acero cromado (demostrativo)",
            perfil_tubo,
            fork(s0 + largo_tubo / 2, z),
            ((0.0, 1.0, 0.3 * sig), 0.40),
            "puente_horquilla",
            rot=rot_horq,
            secciones=24,
            art=f"j_tubo_{lado}",
        )
        b.fija(f"j_tubo_{lado}", f"Tubo {lado} sujeto al puente", "puente_horquilla", f"tubo_{lado}")
        b.revolucion(
            f"botella_{lado_b}",
            f"Botella {lado_b} de la horquilla",
            "botella",
            sub,
            f"Cuerpo inferior {lado_b} que desliza sobre la barra fija y sostiene el eje de la rueda.",
            "Absorbe irregularidades al comprimirse (recorrido demostrativo).",
            "Aleación de aluminio (demostrativo)",
            perfil_bot,
            fork(s0 + s_bot0 + largo_botella / 2, z),
            ((0.4, -0.8, 0.5 * sig), 0.30),
            f"tubo_{lado}",
            rot=rot_horq,
            secciones=24,
            art=f"j_botella_{lado_b}",
        )
    b.pieza(
        "tija_superior",
        "Tija superior",
        "estructura",
        "direccion",
        "Travesaño superior que une los tubos fijos y sujeta el manubrio.",
        "Mantiene paralelos los tubos y soporta el manubrio.",
        "Aleación de aluminio (demostrativo)",
        {"ancho": 0.04, "alto": 0.03, "largo": 0.20},
        "caja",
        {"ancho": 0.04, "alto": 0.03, "largo": 0.20},
        fork(-0.075),
        ((0.0, 1.0, 0.0), 0.55),
        "pipa_direccion",
        rot=yoke,
    )
    sub = "direccion"
    barra = [
        (0.35, 0.855, -0.36),
        (0.37, 0.842, -0.28),
        (0.385, 0.834, -0.20),
        (0.39, 0.830, -0.08),
        (0.39, 0.830, 0.08),
        (0.385, 0.834, 0.20),
        (0.37, 0.842, 0.28),
        (0.35, 0.855, 0.36),
    ]
    b.tubo(
        "manubrio",
        "Manubrio",
        "estructura",
        sub,
        "Tubo curvado con ligero retroceso en los extremos, apoyado sobre la tija superior.",
        "Permite dirigir la moto y aloja manijas y puños.",
        "Aluminio (demostrativo)",
        barra,
        0.011,
        ((0.0, 1.0, 0.0), 0.60),
        "tija_superior",
        suavizado=1,
    )
    perfil_puno = [(0.0, -0.05), (0.016, -0.05), (0.018, -0.045), (0.018, 0.05), (0.0, 0.05)]
    for lado, s_, desc in (
        ("izquierdo", -1.0, "Puño fijo izquierdo"),
        ("derecho", 1.0, "Puño derecho (acelerador)"),
    ):
        b.revolucion(
            f"puno_{lado}",
            desc,
            "agarre",
            sub,
            f"{desc} de caucho, torneado.",
            "Agarre de la mano del conductor.",
            "Caucho (demostrativo)",
            perfil_puno,
            (0.36, 0.848, 0.31 * s_),
            ((0.0, 0.3, s_), 0.40),
            "manubrio",
            secciones=24,
        )
    for nombre_m, s_ in (("freno", 1.0), ("embrague", -1.0)):
        b.tubo(
            f"manija_{nombre_m}",
            f"Manija de {nombre_m}",
            "estructura",
            sub,
            f"Palanca de {nombre_m} articulada en el manubrio (representada fija).",
            f"Acciona el {nombre_m} (no modelado en detalle).",
            "Aluminio (demostrativo)",
            [(0.385, 0.834, 0.20 * s_), (0.415, 0.845, 0.30 * s_), (0.43, 0.85, 0.36 * s_)],
            0.006,
            ((0.5, 0.2, s_), 0.35),
            "manubrio",
            suavizado=1,
            secciones=10,
        )
    for lado, s_ in (("izquierdo", -1.0), ("derecho", 1.0)):
        pts = [
            (0.0, 0.0),
            (0.012 * s_, 0.0),
            (0.020 * s_, 0.085),
            (0.088 * s_, 0.112),
            (0.095 * s_, 0.150),
            (0.050 * s_, 0.180),
            (0.0, 0.170),
            (-0.012 * s_, 0.090),
        ]  # (dz, dy)
        pol_e = [(-dz, dy) for dz, dy in pts]  # x local = -dz (Ry 90°: x -> -z)
        b.extrusion(
            f"espejo_{lado}",
            f"Espejo {lado}",
            "estructura",
            sub,
            f"Espejo retrovisor {lado} (silueta con vástago, sin marcas).",
            "Da visibilidad trasera al conductor.",
            "Plástico y aluminio (demostrativo)",
            pol_e,
            0.014,
            0.0,
            ((0.0, 1.0, s_), 0.35),
            "manubrio",
        )
        e = b.piezas[-1]
        ctr = np.asarray(pol_e, dtype=float)
        c0 = (ctr.min(axis=0) + ctr.max(axis=0)) / 2
        # posición: el origen de la silueta (0,0) = punto de montaje (0.385, 0.834, 0.20·s)
        px = 0.385
        py = 0.834 + float(c0[1])
        pz = 0.20 * s_ - float(c0[0])
        e.transformacion = Transformacion(posicion=(px, py, pz), rotacion_grados=(0.0, 90.0, 0.0))
        e.ancla = (_r(px), _r(py), _r(pz))
    b.revolucion(
        "velocimetro",
        "Velocímetro",
        "instrumento",
        sub,
        "Instrumento circular con bisel, sobre la tija superior.",
        "Muestra la velocidad y el régimen (en el visor, calculados con fisica_moto).",
        "Plástico (demostrativo)",
        [(0.0, -0.015), (0.036, -0.015), (0.040, -0.010), (0.040, 0.015), (0.0, 0.015)],
        (0.425, 0.842, 0.0),
        ((0.0, 1.0, 0.0), 0.25),
        "tija_superior",
        rot=(0.0, 90.0, 0.0),
        secciones=32,
        art="j_velocimetro",
    )
    b.fija("j_velocimetro", "Velocímetro sujeto a la tija superior", "tija_superior", "velocimetro")

    # ============================================================ SUSPENSIÓN TRASERA
    sub = "suspension_trasera"
    sup, inf = P.amortiguador_superior, P.amortiguador_inferior
    largo_amort = math.hypot(sup[0] - inf[0], sup[1] - inf[1])
    perfil_brazo = [
        (-0.235, 0.300),
        (-0.235, 0.392),
        (-0.45, 0.375),
        (-0.60, 0.350),
        (-0.655, eje_t[1] + 0.03),
        (-0.67, eje_t[1]),
        (-0.655, eje_t[1] - 0.03),
        (-0.60, 0.272),
        (-0.45, 0.292),
    ]
    b.pieza(
        "monoamortiguador",
        "Monoamortiguador",
        "amortiguador",
        sub,
        "Conjunto cilíndrico único (resorte y amortiguador) entre el subchasis y el travesaño del "
        "basculante.",
        "Absorbe las irregularidades que recibe la rueda trasera (recorrido demostrativo).",
        "Acero y aluminio (demostrativo)",
        {"radio": 0.022, "largo": largo_amort, "recorrido": recorrido_amort},
        "cilindro",
        {"radio": 0.022, "largo": largo_amort},
        ((sup[0] + inf[0]) / 2, (sup[1] + inf[1]) / 2, 0.0),
        ((0.0, 0.5, -1.0), 0.30),
        "basculante_travesano",
        rot=_rot_hacia(sup[0] - inf[0], sup[1] - inf[1]),
        art="j_monoamortiguador",
    )
    b.extrusion(
        "basculante",
        "Basculante (brazo derecho)",
        "basculante",
        sub,
        "Brazo derecho del basculante (perfil extruido) que une el pivote del chasis con el eje trasero.",
        "Mantiene la rueda trasera y permite su recorrido vertical alrededor del pivote.",
        "Aleación de aluminio (demostrativo)",
        perfil_brazo,
        0.03,
        zb,
        ((0.0, 0.0, 1.0), 0.45),
        "cuna_chasis_derecha",
        art="j_basculante",
    )
    b.extrusion(
        "basculante_brazo_izquierdo",
        "Basculante (brazo izquierdo)",
        "basculante",
        sub,
        "Brazo izquierdo del basculante, rígido con el derecho.",
        "Completa la horquilla trasera.",
        "Aleación de aluminio (demostrativo)",
        perfil_brazo,
        0.03,
        -zb,
        ((0.0, 0.0, -1.0), 0.45),
        "basculante_travesano",
        padre_cin="basculante",
    )
    b.tubo(
        "basculante_travesano",
        "Travesaño del basculante",
        "basculante",
        sub,
        "Tubo transversal que une ambos brazos y recibe el anclaje inferior del amortiguador.",
        "Rigidiza el basculante y soporta el monoamortiguador.",
        "Acero (demostrativo)",
        [(inf[0], inf[1], -zb), (inf[0], inf[1], zb)],
        0.014,
        ((-0.3, -0.4, 0.0), 0.30),
        "basculante",
        padre_cin="basculante",
        suavizado=0,
    )

    # ============================================================ RUEDAS Y LLANTAS
    sub = "ruedas"
    ruedas = (
        (
            "delantero",
            "delantera",
            eje_d,
            r_d,
            seccion_d,
            r_rin_d,
            ancho_d / 1000,
            pr.medida_llanta_delantera,
            "botella_izquierda",
            0.045,
            0.055,
        ),
        (
            "trasero",
            "trasera",
            eje_t,
            r_t,
            seccion_t,
            r_rin_t,
            ancho_t / 1000,
            pr.medida_llanta_trasera,
            "basculante",
            0.060,
            0.070,
        ),
    )
    for tag, tag_f, centro, r_ll, seccion, r_rin, ancho, medida, padre, semi, ancho_aro in ruedas:
        es_del = tag == "delantero"
        sgn = 1.0 if es_del else -1.0
        ox, oy = _r(centro[0]), _r(centro[1])
        if es_del:
            perfil_cubo = [
                (0.0, -0.095),
                (0.012, -0.095),
                (0.012, -0.030),
                (0.032, -0.030),
                (0.032, 0.044),
                (0.058, 0.044),
                (0.058, 0.056),
                (0.012, 0.056),
                (0.012, 0.095),
                (0.0, 0.095),
            ]
        else:
            perfil_cubo = [
                (0.0, -0.11),
                (0.012, -0.11),
                (0.012, -0.056),
                (0.048, -0.056),
                (0.048, -0.044),
                (0.034, -0.044),
                (0.034, 0.062),
                (0.050, 0.062),
                (0.050, 0.082),
                (0.012, 0.082),
                (0.012, 0.11),
                (0.0, 0.11),
            ]
        b.revolucion(
            f"cubo_{tag}",
            f"Cubo {tag}",
            "cubo",
            sub,
            f"Cubo torneado de la rueda {tag_f} con eje, brida para el disco de freno"
            + (" y brida para la corona" if not es_del else "")
            + "; une rin, disco y eje, de modo que el disco no queda flotando.",
            "Transmite el giro entre el eje, el rin y el disco; el eje apoya en la horquilla o el "
            "basculante.",
            "Aleación de aluminio (demostrativo)",
            perfil_cubo,
            (centro[0], centro[1], 0.0),
            ((0.0, 0.0, sgn), 0.20),
            "botella_izquierda" if es_del else "basculante",
            secciones=40,
            art=f"j_cubo_{tag}",
        )
        b.pieza(
            f"rin_{tag}",
            f"Rin {tag}",
            "rin",
            sub,
            f"Rin de 5 rayos de la rueda {tag_f} (aro, cubo y rayos).",
            "Soporta la llanta y gira con la rueda.",
            "Aleación de aluminio (demostrativo)",
            {"radio": r_rin, "ancho": ancho_aro},
            "rin_rayos",
            {
                "radio_exterior": r_rin + 0.003,
                "ancho": ancho_aro,
                "n_rayos": 5.0,
                "radio_cubo": 0.040,
                "ancho_rayo": 0.022,
                "espesor_rayo": 0.015,
                "radio_agujero": 0.026,
            },
            (centro[0], centro[1], 0.0),
            ((0.0, 0.0, sgn), 0.40 if es_del else 0.55),
            f"cubo_{tag}",
            art=f"j_rueda_{tag_f}",
        )
        pl = perfil_neumatico(r_ll, r_rin, semi)
        b.pieza(
            f"llanta_{tag_f}",
            f"Llanta {tag_f} ({medida})",
            "llanta",
            sub,
            f"Neumático {tag_f} de medida {medida} (radio exterior {r_ll:.4f} m desde fisica_moto); "
            "sección en superelipse, sin dibujo ni marcas; el ancho del perfil es menor que el nominal."
            + (
                f" Medida genérica ({medida}, supuesto didáctico); con «Ver con ficha de…» CB 160F "
                f"la medida pasa a 140/70-17 y la rueda se reescala en el visor."
                if tag_f == "trasera"
                else " Medida delantera supuesta (demostrativo): no consta en la ficha."
            ),
            "Transmite al suelo las fuerzas de tracción y frenado.",
            "Caucho (demostrativo)",
            {"radio_exterior": r_ll, "altura_flanco": seccion, "ancho_nominal": ancho},
            "revolucion",
            {"n_secciones": 72.0, "n_cerrado": 1.0, **codificar_puntos(pl, ("r", "z"))},
            (centro[0], centro[1], 0.0),
            ((0.0, 0.0, -sgn), 0.50),
            f"rin_{tag}",
            art=f"j_llanta_{tag_f}",
        )
        b.arts.append(
            Articulacion(
                id=f"j_rueda_{tag_f}",
                nombre=f"Giro de la rueda {tag}",
                tipo=TipoArticulacion.ROTACIONAL,
                padre=padre,
                hijo=f"rin_{tag}",
                eje=(0.0, 0.0, 1.0),
                origen=(ox, oy, 0.0),
                unidad="grados",
                continua=True,
                descripcion="Rotación continua alrededor del eje de la rueda.",
            )
        )
        for hijo_, nom_ in ((f"llanta_{tag_f}", "Llanta"), (f"cubo_{tag}", "Cubo")):
            b.arts.append(
                Articulacion(
                    id=f"j_{hijo_.split('_')[0]}_{tag_f}" if hijo_.startswith("llanta") else f"j_cubo_{tag}",
                    nombre=f"{nom_} {tag} solidario al rin",
                    tipo=TipoArticulacion.COMPUESTA,
                    padre=padre,
                    hijo=hijo_,
                    eje=(0.0, 0.0, 1.0),
                    origen=(ox, oy, 0.0),
                    unidad="grados",
                    maestra=f"j_rueda_{tag_f}",
                    relacion=1.0,
                    descripcion="Mismo ángulo que el rin.",
                )
            )

    # ============================================================ FRENOS
    sub = "frenos"
    espesor_disco = 0.004
    pinza_params = {
        "ancho": 0.07,
        "alto": 0.06,
        "ranura_largo": 0.024,
        "ranura_alto": 0.04,
        "largo_interior": 0.024,
        "largo_exterior": 0.0235,
        "radio_cilindro": 0.0165,
    }
    dir_brazo = _unitario(pivote[0] - eje_t[0], pivote[1] - eje_t[1])
    for tag, centro, r_dis, z_dis, kind in (
        ("delantero", eje_d, 0.14, 0.05, "del"),
        ("trasero", eje_t, 0.11, -0.05, "tra"),
    ):
        es_del = kind == "del"
        b.pieza(
            f"disco_{tag}",
            f"Disco de freno {tag}",
            "disco",
            sub,
            f"Disco {tag} de {r_dis * 2 * 1000:.0f} mm de diámetro, perforado, atornillado a la brida "
            f"del cubo.",
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
            f"cubo_{tag}",
            art=f"j_disco_{tag}",
        )
        y_p = r_dis - 0.0075
        if es_del:
            pos_c = (centro[0] - ux * y_p, centro[1] - uy * y_p, z_dis)
            rot_c = (0.0, 0.0, lanz)
            padre_c, mont_c = "botella_derecha", "botella_derecha"
        else:
            pos_c = (centro[0] + dir_brazo[0] * y_p, centro[1] + dir_brazo[1] * y_p, z_dis)
            rot_c = (0.0, 180.0, _r(-(90.0 - math.degrees(math.atan2(dir_brazo[1], dir_brazo[0])))))
            padre_c, mont_c = "basculante", "basculante_brazo_izquierdo"
        b.pieza(
            f"caliper_{tag}",
            f"Cáliper {tag}",
            "pinza",
            sub,
            f"Pinza de un pistón (Ø{_sup('diametro_piston_m') * 1000:.0f} mm de fisica_moto, "
            f"representado como "
            "cavidad) que abraza el disco y se apoya en la horquilla o el brazo.",
            "Convierte la presión hidráulica en fuerza de sujeción sobre las pastillas.",
            "Aleación de aluminio (demostrativo)",
            {"ancho": 0.07, "alto": 0.06, "diametro_piston": _sup("diametro_piston_m")},
            "pinza",
            pinza_params,
            pos_c,
            ((0.0, 1.0, 0.6 if es_del else -0.6), 0.25),
            mont_c,
            rot=rot_c,
            art=f"j_caliper_{tag}",
        )
        b.fija(f"j_caliper_{tag}", f"Cáliper sujeto a {mont_c}", padre_c, f"caliper_{tag}")
    b.pieza(
        "unidad_cbs",
        "Unidad CBS (esquemática)",
        "unidad_hidraulica",
        sub,
        "Bloque hidráulico esquemático del frenado combinado (CBS) colgado de la columna del chasis; "
        "sin válvulas.",
        "Representa el reparto de presión entre ambos discos (supuesto didáctico en fisica_moto).",
        "Aleación de aluminio (demostrativo)",
        {"ancho": 0.07, "alto": 0.05, "largo": 0.05},
        "caja",
        {"ancho": 0.07, "alto": 0.05, "largo": 0.05},
        (0.18, 0.708, 0.0),
        ((0.0, 0.5, 1.0), 0.25),
        "chasis",
        art="j_unidad_cbs",
    )
    b.fija("j_unidad_cbs", "Unidad CBS sujeta al chasis", "chasis", "unidad_cbs")
    b.pieza(
        "bomba_freno",
        "Bomba de freno delantera",
        "unidad_hidraulica",
        sub,
        "Cilindro maestro con el depósito integrado, abrazado al manubrio derecho.",
        "Genera la presión hidráulica del freno delantero a partir de la fuerza en la manija.",
        "Aluminio (demostrativo)",
        {"radio": 0.013, "largo": 0.07},
        "cilindro",
        {"radio": 0.013, "largo": 0.07},
        (0.40, 0.842, 0.20),
        ((0.3, 1.0, 0.5), 0.25),
        "manubrio",
    )
    ax_ = (eje_d[0], eje_d[1])
    p_c1 = (ax_[0] - ux * 0.17, ax_[1] - uy * 0.17, 0.095)
    p_c2 = (ax_[0] - ux * 0.155, ax_[1] - uy * 0.155, 0.075)
    b.tubo(
        "manguera_freno",
        "Manguera de freno delantera",
        "manguera",
        sub,
        "Manguera flexible desde la bomba hasta el cáliper, pegada a la botella derecha.",
        "Conduce la presión hidráulica al cáliper delantero.",
        "Caucho reforzado (demostrativo)",
        [(0.40, 0.835, 0.17), fork(-0.02, 0.13), fork(0.10, 0.118), fork(0.25, 0.118), p_c1, p_c2],
        0.005,
        ((0.3, 0.0, 1.0), 0.30),
        "bomba_freno",
        suavizado=1,
        secciones=8,
    )
    b.tubo(
        "pedal_freno",
        "Pedal de freno trasero",
        "estructura",
        sub,
        "Palanca derecha del freno trasero, unida al estribo.",
        "Acciona el freno trasero (no modelado en detalle).",
        "Acero (demostrativo)",
        [(-0.10, 0.215, 0.12), (-0.18, 0.225, 0.118), (-0.26, 0.225, 0.118)],
        0.007,
        ((-0.5, -0.2, 1.0), 0.28),
        "estribo_derecho",
        suavizado=1,
        secciones=10,
    )

    # ============================================================ ELÉCTRICO
    sub = "electrico"
    perfil_faro = [
        (0.0, 0.0),
        (0.088, 0.0),
        (0.090, 0.02),
        (0.082, 0.07),
        (0.060, 0.12),
        (0.030, 0.15),
        (0.0, 0.158),
    ]
    b.revolucion(
        "farola",
        "Farola",
        "luz",
        sub,
        "Faro delantero de revolución (sin marcas ni emblemas), sujeto a las barras de la horquilla.",
        "Ilumina el camino; en el modelo solo ocupa volumen.",
        "Policarbonato (demostrativo)",
        perfil_faro,
        (0.452, 0.725, 0.0),
        ((1.0, 0.0, 0.0), 0.25),
        "tubo_derecho",
        rot=(0.0, 90.0, 0.0),
        secciones=40,
        art="j_farola",
    )
    b.fija("j_farola", "Farola sujeta a las barras de la horquilla", "tubo_derecho", "farola")
    b.pieza(
        "stop",
        "Luz trasera (stop)",
        "luz",
        sub,
        "Piloto trasero elipsoidal sobre el colín.",
        "Señala el frenado y la presencia del vehículo.",
        "Policarbonato (demostrativo)",
        {"radio_x": 0.012, "radio_y": 0.02, "radio_z": 0.05},
        "elipsoide",
        {"radio_x": 0.012, "radio_y": 0.02, "radio_z": 0.05},
        (-0.628, 0.765, 0.0),
        ((-1.0, 0.0, 0.0), 0.25),
        "colin",
        art="j_stop",
    )
    b.fija("j_stop", "Luz trasera sujeta al colín", "chasis", "stop")
    for pos_d, mont, x_d, y_d, z_d, rz in (
        ("delantera", "farola", 0.522, 0.725, 0.092, 0.016),
        ("trasera", "colin", -0.62, 0.76, 0.078, 0.014),
    ):
        for lado, s_ in (("izquierda", -1.0), ("derecha", 1.0)):
            b.pieza(
                f"direccional_{pos_d}_{lado}",
                f"Direccional {pos_d} {lado}",
                "luz",
                sub,
                f"Luz intermitente {pos_d} {lado} (elipsoide pegado a {mont}).",
                "Indica el giro del vehículo.",
                "Policarbonato (demostrativo)",
                {"radio_x": 0.02, "radio_y": 0.014, "radio_z": rz},
                "elipsoide",
                {"radio_x": 0.02, "radio_y": 0.014, "radio_z": rz},
                (x_d, y_d, z_d * s_),
                ((0.2, 0.0, s_), 0.25),
                mont,
            )
    b.pieza(
        "bateria",
        "Batería",
        "electrico",
        sub,
        "Bloque prismático colgado del extremo de la columna.",
        "Alimenta el sistema eléctrico (no modelado).",
        "Plástico (demostrativo)",
        {"ancho": 0.09, "alto": 0.10, "largo": 0.07},
        "caja",
        {"ancho": 0.09, "alto": 0.10, "largo": 0.07},
        (-0.14, 0.64, 0.0),
        ((0.0, -1.0, 0.0), 0.30),
        "chasis",
    )

    # ============================================================ ESCAPE
    sub = "escape"
    codo = [
        m(0.205, 0.040),
        (0.245, 0.505, 0.0),
        (0.265, 0.42, 0.0),
        (0.268, 0.30, 0.012),
        (0.24, 0.19, 0.04),
        (0.16, 0.12, 0.09),
        (0.0, 0.115, 0.13),
        (-0.12, 0.135, 0.14),
        (-0.20, 0.15, 0.14),
    ]
    b.tubo(
        "tubo_escape",
        "Tubo de escape (colector)",
        "escape",
        sub,
        "Codo que sale de la culata por delante del cilindro, rodea el motor por debajo y llega al "
        "silenciador.",
        "Conduce los gases quemados fuera del cilindro.",
        "Acero inoxidable (demostrativo)",
        codo,
        0.016,
        ((0.3, -0.3, 1.0), 0.25),
        "culata",
        suavizado=2,
        art="j_tubo_escape",
    )
    b.fija("j_tubo_escape", "Colector sujeto a la culata", "culata", "tubo_escape")
    perfil_sil = [
        (0.0, -0.21),
        (0.020, -0.21),
        (0.040, -0.19),
        (0.047, -0.15),
        (0.047, 0.17),
        (0.040, 0.195),
        (0.022, 0.21),
        (0.0, 0.21),
    ]
    b.revolucion(
        "silenciador",
        "Silenciador",
        "escape",
        sub,
        "Cuerpo de revolución horizontal junto a la rueda trasera.",
        "Atenúa el ruido de los gases de escape.",
        "Acero inoxidable (demostrativo)",
        perfil_sil,
        (-0.41, 0.15, 0.14),
        ((-0.5, 0.0, 1.0), 0.30),
        "tubo_escape",
        rot=(0.0, 90.0, 0.0),
        secciones=32,
        art="j_silenciador",
    )
    b.fija("j_silenciador", "Silenciador sujeto al colector", "tubo_escape", "silenciador")

    # ============================================================ ARTICULACIONES DE LAS PIEZAS ORIGINALES
    arts = b.arts
    arts += [
        Articulacion(
            id="j_piston",
            nombre="Carrera del pistón (PMS a PMI)",
            tipo=TipoArticulacion.PRISMATICA,
            padre="cilindro",
            hijo="piston",
            eje=(_r(ax), _r(ay), 0.0),
            unidad="m",
            limites=LimitesMovimiento(minimo=-_r(carrera), maximo=0.0),
            descripcion=(
                "Valor 0 en el PMS y -carrera en el PMI (recorrido = carrera de fisica_moto), a lo largo "
                "del eje del cilindro."
            ),
        ),
        Articulacion(
            id="j_biela",
            nombre="Oscilación de la biela sobre el bulón",
            tipo=TipoArticulacion.ROTACIONAL,
            padre="piston",
            hijo="biela",
            eje=(0.0, 0.0, 1.0),
            origen=(_r(m(pin_pms)[0]), _r(m(pin_pms)[1]), 0.0),
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
            origen=(_r(cig[0]), _r(cig[1]), 0.0),
            unidad="grados",
            continua=True,
            descripcion="Rotación continua alrededor del eje Z; θ = 0 con el pistón en el PMS.",
        ),
        Articulacion(
            id="j_valvula_admision",
            nombre="Apertura de la válvula de admisión",
            tipo=TipoArticulacion.PRISMATICA,
            padre="culata",
            hijo="valvula_admision",
            eje=(_r(-ax), _r(-ay), 0.0),
            unidad="m",
            limites=LimitesMovimiento(minimo=0.0, maximo=levante_valvula),
            descripcion=(
                "Desplazamiento hacia la cámara a lo largo del eje del cilindro; el levante es demostrativo."
            ),
        ),
        Articulacion(
            id="j_valvula_escape",
            nombre="Apertura de la válvula de escape",
            tipo=TipoArticulacion.PRISMATICA,
            padre="culata",
            hijo="valvula_escape",
            eje=(_r(-ax), _r(-ay), 0.0),
            unidad="m",
            limites=LimitesMovimiento(minimo=0.0, maximo=levante_valvula),
            descripcion=(
                "Desplazamiento hacia la cámara a lo largo del eje del cilindro; el levante es demostrativo."
            ),
        ),
        Articulacion(
            id="j_pinon",
            nombre="Giro del piñón (relación final respecto a la rueda)",
            tipo=TipoArticulacion.COMPUESTA,
            padre="chasis",
            hijo="pinon",
            eje=(0.0, 0.0, 1.0),
            origen=(_r(pinon[0]), _r(pinon[1]), 0.0),
            unidad="grados",
            maestra="j_rueda_trasera",
            relacion=rel_final,
            descripcion="Gira relacion_final veces el ángulo de la rueda trasera (42/14).",
        ),
        Articulacion(
            id="j_corona",
            nombre="Corona solidaria a la rueda trasera",
            tipo=TipoArticulacion.COMPUESTA,
            padre="basculante",
            hijo="corona",
            eje=(0.0, 0.0, 1.0),
            origen=(_r(eje_t[0]), _r(eje_t[1]), 0.0),
            unidad="grados",
            maestra="j_rueda_trasera",
            relacion=1.0,
            descripcion="Mismo ángulo que la rueda trasera.",
        ),
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
            origen=(_r(pivote[0]), _r(pivote[1]), 0.0),
            unidad="grados",
            limites=LimitesMovimiento(minimo=-osc_basculante, maximo=osc_basculante),
            descripcion="Giro alrededor del pivote; límites demostrativos.",
        ),
    ]
    for tag, centro in (("delantero", eje_d), ("trasero", eje_t)):
        arts.append(
            Articulacion(
                id=f"j_disco_{tag}",
                nombre=f"Disco {tag} solidario a la rueda",
                tipo=TipoArticulacion.COMPUESTA,
                padre="botella_izquierda" if tag == "delantero" else "basculante",
                hijo=f"disco_{tag}",
                eje=(0.0, 0.0, 1.0),
                origen=(_r(centro[0]), _r(centro[1]), 0.0),
                unidad="grados",
                maestra=f"j_rueda_{'delantera' if tag == 'delantero' else 'trasera'}",
                relacion=1.0,
                descripcion="Mismo ángulo que la rueda.",
            )
        )

    b.cerrar()
    _despiece_radial(b.piezas)
    # orden de desmontaje: las articulaciones hijas de otro hijo no deben introducir ciclos cinemáticos
    parametros_ens = {
        "carrera_m": _r(carrera),
        "diametro_cilindro_m": _r(diametro),
        "longitud_biela_m": _r(biela_l),
        "cilindrada_nominal_cm3": cilindrada,
        "relacion_primaria": rel_primaria,
        "relacion_final": rel_final,
        "radio_llanta_trasera_m": _r(r_t),
        "radio_llanta_delantera_m": _r(r_d),
        "distancia_entre_ejes_m": _r(eje_d[0] - eje_t[0]),
        "altura_sillin_m": ALTURA_SILLIN_M,
        "angulo_lanzamiento_grados": lanz,
        "inclinacion_cilindro_grados": inc,
        "recorrido_horquilla_m": recorrido_horq,
        "recorrido_monoamortiguador_m": recorrido_amort,
        "oscilacion_basculante_grados": osc_basculante,
        "levante_valvula_m": levante_valvula,
        # trayectoria de la cadena (el visor instancia los eslabones sobre ella)
        "cadena_radio_paso_pinon_m": RADIO_PASO_PINON_M,
        "cadena_radio_paso_corona_m": RADIO_PASO_CORONA_M,
        "cadena_entre_centros_m": _r(d_cadena),
        "cadena_z_m": Z_CADENA_M,
        "cadena_dientes_pinon": float(DIENTES_PINON),
        "cadena_dientes_corona": float(DIENTES_CORONA),
        "cadena_pinon_x_m": _r(pinon[0]),
        "cadena_pinon_y_m": _r(pinon[1]),
        "cadena_corona_x_m": _r(eje_t[0]),
        "cadena_corona_y_m": _r(eje_t[1]),
        "tolerancia_conectividad_m": TOLERANCIA_CONECTIVIDAD_M,
        "entre_ejes_nominal_m": ENTRE_EJES_M,
    }
    for nombre_p, x_p, y_p in tabla_puntos_duros():
        parametros_ens[f"punto_{nombre_p}_x_m"] = _r(x_p)
        parametros_ens[f"punto_{nombre_p}_y_m"] = _r(y_p)
    return Ensamblaje(
        id=ID_ENSAMBLAJE,
        nombre="Motocicleta (referencia genérica)",
        descripcion=(
            "Motocicleta naked de ~150 cc de referencia genérica: motor en corte a escala, "
            "transmisión, doble "
            "cuna tubular, suspensiones, dirección, frenos, ruedas, carrocería, sistema eléctrico y escape. "
            "Esquemática y demostrativa."
        ),
        version="2.0.0",
        advertencia=ADVERTENCIA,
        subconjuntos=[
            Subconjunto(
                id="motor",
                nombre="Motor en corte",
                padre=None,
                descripcion=(
                    "Cárter, cilindro con aletas, culata, pistón, biela, cigüeñal, válvulas, bujía y "
                    "admisión."
                ),
            ),
            Subconjunto(
                id="transmision",
                nombre="Transmisión",
                padre=None,
                descripcion=(
                    "Caja de cambios, piñón, cadena, corona, cubrecadena, pedal de cambios y tensores."
                ),
            ),
            Subconjunto(
                id="chasis_tanque",
                nombre="Chasis y tanque",
                padre=None,
                descripcion=(
                    "Columna, doble cuna, subchasis, pipa de dirección, tanque, sillín, estribos y caballete."
                ),
            ),
            Subconjunto(
                id="suspension_delantera",
                nombre="Suspensión delantera",
                padre=None,
                descripcion="Horquilla telescópica: tijas, barras fijas y botellas.",
            ),
            Subconjunto(
                id="suspension_trasera",
                nombre="Suspensión trasera",
                padre=None,
                descripcion="Monoamortiguador y basculante (dos brazos y travesaño).",
            ),
            Subconjunto(
                id="frenos",
                nombre="Frenos",
                padre=None,
                descripcion="Discos, cálipers, unidad CBS, bomba, manguera y pedal de freno.",
            ),
            Subconjunto(
                id="ruedas",
                nombre="Ruedas y llantas",
                padre=None,
                descripcion="Cubo, rin de 5 rayos y llanta delanteros y traseros.",
            ),
            Subconjunto(
                id="electrico",
                nombre="Sistema eléctrico",
                padre=None,
                descripcion="Farola, luz trasera, direccionales y batería.",
            ),
            Subconjunto(id="escape", nombre="Escape", padre=None, descripcion="Colector y silenciador."),
            Subconjunto(
                id="direccion",
                nombre="Dirección y mandos",
                padre=None,
                descripcion="Manubrio, manijas, puños, espejos y velocímetro.",
            ),
            Subconjunto(
                id="carroceria",
                nombre="Carrocería",
                padre=None,
                descripcion="Guardabarros, cubiertas laterales, colín, porta placa y tapa del tanque.",
            ),
        ],
        piezas=b.piezas,
        sistemas=sistemas_moto(),
        articulaciones=arts,
        archivo_glb="modelos/moto_honda.glb",
        parametros=parametros_ens,
        procedencia_parametros={k: "demostrativo" for k in parametros_ens},
    )
