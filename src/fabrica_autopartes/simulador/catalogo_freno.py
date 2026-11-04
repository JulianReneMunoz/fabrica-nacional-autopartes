"""Caso principal de demostración: freno de disco delantero con pinza flotante de un pistón.

Selección justificada (Parte VIII, §34): conjunto técnicamente manejable, relacionado con la
fabricación de partes metálicas para chasis de Autopartes Fanalca y con física simple y
verificable (presión hidráulica → fuerza de sujeción → par de frenado).

Todas las dimensiones son paramétricas y DEMOSTRATIVAS: corresponden a un orden de magnitud
plausible para un automóvil pequeño, no a un plano de fabricante. La geometría es
procedural y simplificada; no constituye un diseño industrial certificado.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, model_validator

from fabrica_autopartes.simulador.modelos import (
    Articulacion,
    Ensamblaje,
    Geometria,
    LimitesMovimiento,
    Pieza,
    Subconjunto,
    TipoArticulacion,
    Transformacion,
)

ADVERTENCIA = (
    "Modelo de demostración con geometría procedural simplificada y dimensiones demostrativas. "
    "No es un diseño industrial certificado ni sustituye documentación técnica del fabricante."
)
REF_DEMO = "Modelo de demostración del proyecto (sin documentación de fabricante)"


class ParametrosFreno(BaseModel):
    """Parámetros del ensamblaje (m). Se validan antes de construir geometría."""

    diametro_disco: float = Field(0.280, ge=0.18, le=0.45)
    espesor_disco: float = Field(0.022, ge=0.008, le=0.040)
    radio_interior_disco: float = Field(0.090, ge=0.05, le=0.15)
    diametro_piston: float = Field(0.054, ge=0.030, le=0.075)
    radio_efectivo: float = Field(0.115, ge=0.07, le=0.20)
    holgura_pastilla: float = Field(0.0005, ge=0.0001, le=0.002)
    n_esparragos: int = Field(4, ge=3, le=6)

    @model_validator(mode="after")
    def _coherencia(self) -> ParametrosFreno:
        r_ext = self.diametro_disco / 2
        if self.radio_interior_disco >= r_ext - 0.03:
            raise ValueError("El anillo de fricción debe medir al menos 30 mm de ancho radial")
        if not (self.radio_interior_disco + 0.02 <= self.radio_efectivo <= r_ext - 0.02):
            raise ValueError("El radio efectivo debe quedar dentro del anillo de fricción")
        return self


def _pieza(**kw: object) -> Pieza:
    kw.setdefault("referencia_documental", REF_DEMO)
    return Pieza.model_validate(kw)


def construir_freno(p: ParametrosFreno | None = None) -> Ensamblaje:
    p = p or ParametrosFreno.model_validate({})
    r_ext = p.diametro_disco / 2
    e = p.espesor_disco
    re_ = p.radio_efectivo
    alto_pastilla = min(0.050, r_ext - p.radio_interior_disco - 0.004)
    esp_pastilla = 0.012
    z_past = e / 2 + p.holgura_pastilla + esp_pastilla / 2
    largo_piston = 0.040
    z_piston = -(e / 2 + p.holgura_pastilla + esp_pastilla + largo_piston / 2)
    y_pinza = re_ + 0.008
    ranura = e + 2 * (p.holgura_pastilla + esp_pastilla)
    largo_interior = largo_piston + 0.010

    piezas: list[Pieza] = [
        _pieza(
            id="cubo",
            nombre="Cubo de rueda",
            tipo="cubo",
            subconjunto="rotacion",
            descripcion="Cuerpo giratorio que soporta el disco y la rueda sobre los rodamientos.",
            funcion="Transmite el giro de la rueda al disco y centra el conjunto.",
            material="Acero forjado (demostrativo)",
            dimensiones_m={"radio": 0.065, "largo": 0.05},
            geometria=Geometria(
                primitiva="cubo",
                parametros={"radio": 0.065, "largo": 0.05, "radio_brida": 0.075, "espesor_brida": 0.008},
                nodo_glb="cubo",
            ),
            transformacion=Transformacion(posicion=(0.0, 0.0, -(e / 2) - 0.025)),
            ancla=(0.0, 0.0, -(e / 2)),
            relacionadas=["disco"] + [f"esparrago_{i}" for i in range(1, p.n_esparragos + 1)],
            articulaciones=["j_rueda"],
            direccion_despiece=(0.0, 0.0, -1.0),
            distancia_despiece_m=0.10,
            retirar_antes=["disco"] + [f"esparrago_{i}" for i in range(1, p.n_esparragos + 1)],
        ),
        _pieza(
            id="disco",
            nombre="Disco de freno ventilado",
            tipo="disco",
            subconjunto="rotacion",
            descripcion="Anillo de fricción solidario al cubo, con agujeros de ventilación.",
            funcion="Superficie sobre la que las pastillas generan la fricción que frena la rueda.",
            material="Fundición gris (demostrativo)",
            dimensiones_m={
                "diametro": p.diametro_disco,
                "espesor": e,
                "radio_interior": p.radio_interior_disco,
            },
            geometria=Geometria(
                primitiva="disco_ventilado",
                parametros={
                    "radio_exterior": r_ext,
                    "radio_interior": 0.045,
                    "espesor": e,
                    "radio_agujeros": 0.004,
                    "n_agujeros": 12,
                    "radio_circulo_agujeros": (p.radio_interior_disco + r_ext) / 2,
                },
                nodo_glb="disco",
            ),
            transformacion=Transformacion(posicion=(0.0, 0.0, 0.0)),
            ancla=(0.0, 0.0, 0.0),
            relacionadas=["cubo", "pastilla_interna", "pastilla_externa"],
            articulaciones=["j_disco_cubo"],
            direccion_despiece=(0.0, 0.0, 1.0),
            distancia_despiece_m=0.14,
            retirar_antes=["soporte_pinza"],
        ),
    ]
    for i in range(1, p.n_esparragos + 1):
        ang = 2 * math.pi * (i - 1) / p.n_esparragos + math.pi / 4
        x, y = 0.05 * math.cos(ang), 0.05 * math.sin(ang)
        piezas.append(
            _pieza(
                id=f"esparrago_{i}",
                nombre=f"Espárrago de rueda {i}",
                tipo="esparrago",
                subconjunto="rotacion",
                descripcion="Perno roscado prensado en el cubo que sujeta la rueda.",
                funcion="Fija la rueda al cubo; atraviesa el sombrero del disco.",
                material="Acero aleado (demostrativo)",
                dimensiones_m={"radio": 0.006, "largo": 0.05},
                geometria=Geometria(
                    primitiva="cilindro",
                    parametros={"radio": 0.006, "largo": 0.05},
                    nodo_glb=f"esparrago_{i}",
                ),
                transformacion=Transformacion(posicion=(round(x, 6), round(y, 6), 0.02)),
                ancla=(round(x, 6), round(y, 6), -e / 2),
                relacionadas=["cubo"],
                articulaciones=[f"j_esparrago_{i}"],
                direccion_despiece=(0.0, 0.0, 1.0),
                distancia_despiece_m=0.22,
                retirar_antes=["disco"],
            )
        )
    piezas += [
        _pieza(
            id="soporte_pinza",
            nombre="Soporte de pinza",
            tipo="soporte",
            subconjunto="pinza",
            descripcion="Pieza fija atornillada a la mangueta que aloja los pasadores guía.",
            funcion="Reacciona el par de frenado hacia la mangueta y guía el deslizamiento de la pinza.",
            material="Acero (demostrativo)",
            dimensiones_m={"ancho": 0.17, "alto": 0.025, "largo": 0.020},
            geometria=Geometria(
                primitiva="caja",
                parametros={"ancho": 0.17, "alto": 0.025, "largo": 0.020},
                nodo_glb="soporte_pinza",
            ),
            transformacion=Transformacion(posicion=(0.0, round(re_ - 0.045, 6), round(-(e / 2) - 0.035, 6))),
            ancla=(0.0, round(re_ - 0.045, 6), -0.06),
            relacionadas=[
                "cuerpo_pinza",
                "pasador_guia_1",
                "pasador_guia_2",
                "tornillo_soporte_1",
                "tornillo_soporte_2",
            ],
            articulaciones=["j_soporte"],
            direccion_despiece=(0.0, 0.35, -1.0),
            distancia_despiece_m=0.17,
            retirar_antes=[
                "tornillo_soporte_1",
                "tornillo_soporte_2",
                "pastilla_interna",
                "pastilla_externa",
            ],
        ),
        _pieza(
            id="cuerpo_pinza",
            nombre="Cuerpo de pinza flotante",
            tipo="pinza",
            subconjunto="pinza",
            descripcion="Carcasa en C que abraza el disco y contiene el cilindro del pistón.",
            funcion=(
                "Convierte la presión hidráulica en fuerza sobre ambas pastillas al deslizar "
                "sobre los pasadores."
            ),
            material="Fundición nodular (demostrativo)",
            dimensiones_m={"ancho": 0.13, "alto": 0.08, "largo": round(ranura + largo_interior + 0.012, 4)},
            geometria=Geometria(
                primitiva="pinza",
                parametros={
                    "ancho": 0.13,
                    "alto": 0.08,
                    "ranura_largo": round(ranura, 5),
                    "ranura_alto": 0.06,
                    "largo_interior": round(largo_interior, 4),
                    "largo_exterior": 0.012,
                    "radio_cilindro": round(p.diametro_piston / 2 + 0.001, 5),
                },
                nodo_glb="cuerpo_pinza",
            ),
            transformacion=Transformacion(posicion=(0.0, round(y_pinza, 6), 0.0)),
            ancla=(0.0, round(y_pinza, 6), 0.0),
            relacionadas=["piston", "pastilla_externa", "pasador_guia_1", "pasador_guia_2", "soporte_pinza"],
            articulaciones=["j_pinza_flotante"],
            direccion_despiece=(0.0, 1.0, 0.0),
            distancia_despiece_m=0.13,
            retirar_antes=["pasador_guia_1", "pasador_guia_2"],
        ),
        _pieza(
            id="piston",
            nombre="Pistón de pinza",
            tipo="piston",
            subconjunto="pinza",
            descripcion="Émbolo cilíndrico desplazado por el líquido de frenos.",
            funcion="Empuja la pastilla interna contra el disco con fuerza F = p·A.",
            material="Acero cromado (demostrativo)",
            dimensiones_m={"diametro": p.diametro_piston, "largo": largo_piston},
            geometria=Geometria(
                primitiva="cilindro",
                parametros={"radio": p.diametro_piston / 2, "largo": largo_piston},
                nodo_glb="piston",
            ),
            transformacion=Transformacion(posicion=(0.0, round(re_, 6), round(z_piston, 6))),
            ancla=(0.0, round(re_, 6), round(z_piston, 6)),
            relacionadas=["cuerpo_pinza", "pastilla_interna"],
            articulaciones=["j_piston"],
            direccion_despiece=(0.0, 0.7, -0.7),
            distancia_despiece_m=0.16,
            retirar_antes=["cuerpo_pinza"],
        ),
        _pieza(
            id="pastilla_interna",
            nombre="Pastilla interna",
            tipo="pastilla",
            subconjunto="pinza",
            descripcion="Placa de respaldo con material de fricción del lado del pistón.",
            funcion="Genera fricción sobre la cara interna del disco.",
            material="Material de fricción sobre placa de acero (demostrativo)",
            dimensiones_m={"ancho": 0.10, "alto": round(alto_pastilla, 4), "espesor": esp_pastilla},
            geometria=Geometria(
                primitiva="caja",
                parametros={"ancho": 0.10, "alto": round(alto_pastilla, 4), "largo": esp_pastilla},
                nodo_glb="pastilla_interna",
            ),
            transformacion=Transformacion(posicion=(0.0, round(re_, 6), round(-z_past, 6))),
            ancla=(0.0, round(re_, 6), round(-z_past, 6)),
            relacionadas=["piston", "disco"],
            articulaciones=["j_pastilla_interna"],
            direccion_despiece=(0.0, 1.0, -0.4),
            distancia_despiece_m=0.09,
            retirar_antes=["cuerpo_pinza"],
        ),
        _pieza(
            id="pastilla_externa",
            nombre="Pastilla externa",
            tipo="pastilla",
            subconjunto="pinza",
            descripcion="Pastilla apoyada en los dedos del cuerpo de la pinza.",
            funcion="Genera fricción sobre la cara externa del disco por reacción de la pinza flotante.",
            material="Material de fricción sobre placa de acero (demostrativo)",
            dimensiones_m={"ancho": 0.10, "alto": round(alto_pastilla, 4), "espesor": esp_pastilla},
            geometria=Geometria(
                primitiva="caja",
                parametros={"ancho": 0.10, "alto": round(alto_pastilla, 4), "largo": esp_pastilla},
                nodo_glb="pastilla_externa",
            ),
            transformacion=Transformacion(posicion=(0.0, round(re_, 6), round(z_past, 6))),
            ancla=(0.0, round(re_, 6), round(z_past, 6)),
            relacionadas=["cuerpo_pinza", "disco"],
            articulaciones=["j_pastilla_externa"],
            direccion_despiece=(0.0, 1.0, 0.4),
            distancia_despiece_m=0.09,
            retirar_antes=["cuerpo_pinza"],
        ),
    ]
    for i, x in ((1, -0.07), (2, 0.07)):
        piezas.append(
            _pieza(
                id=f"pasador_guia_{i}",
                nombre=f"Pasador guía {i}",
                tipo="pasador",
                subconjunto="pinza",
                descripcion="Perno lubricado sobre el que desliza la pinza flotante.",
                funcion="Permite el desplazamiento axial de la pinza y alinea las pastillas.",
                material="Acero (demostrativo)",
                dimensiones_m={"radio": 0.005, "largo": 0.08},
                geometria=Geometria(
                    primitiva="cilindro",
                    parametros={"radio": 0.005, "largo": 0.08},
                    nodo_glb=f"pasador_guia_{i}",
                ),
                transformacion=Transformacion(posicion=(x, round(y_pinza, 6), -0.03)),
                ancla=(x, round(y_pinza, 6), -0.03),
                relacionadas=["cuerpo_pinza", "soporte_pinza"],
                articulaciones=[f"j_pasador_{i}"],
                direccion_despiece=(0.0, 0.0, -1.0),
                distancia_despiece_m=0.12,
            )
        )
        piezas.append(
            _pieza(
                id=f"tornillo_soporte_{i}",
                nombre=f"Tornillo de soporte {i}",
                tipo="tornillo",
                subconjunto="fijacion",
                descripcion="Tornillo que fija el soporte de la pinza a la mangueta.",
                funcion="Mantiene el soporte en posición y transmite el par de reacción.",
                material="Acero clase 10.9 (demostrativo)",
                dimensiones_m={"radio": 0.006, "largo": 0.03},
                geometria=Geometria(
                    primitiva="tornillo",
                    parametros={"radio": 0.006, "largo": 0.03, "radio_cabeza": 0.0095, "alto_cabeza": 0.008},
                    nodo_glb=f"tornillo_soporte_{i}",
                ),
                transformacion=Transformacion(posicion=(round(x * 1.07, 6), round(re_ - 0.045, 6), -0.07)),
                ancla=(round(x * 1.07, 6), round(re_ - 0.045, 6), -0.055),
                relacionadas=["soporte_pinza"],
                articulaciones=[f"j_tornillo_{i}"],
                direccion_despiece=(0.0, 0.0, -1.0),
                distancia_despiece_m=0.15,
            )
        )

    articulaciones = [
        Articulacion(
            id="j_rueda",
            nombre="Giro de la rueda",
            tipo=TipoArticulacion.ROTACIONAL,
            padre=None,
            hijo="cubo",
            eje=(0.0, 0.0, 1.0),
            unidad="grados",
            continua=True,
            descripcion="El cubo gira libremente sobre los rodamientos de la mangueta.",
        ),
        Articulacion(
            id="j_disco_cubo",
            nombre="Disco fijo al cubo",
            tipo=TipoArticulacion.FIJA,
            padre="cubo",
            hijo="disco",
        ),
        Articulacion(
            id="j_soporte",
            nombre="Soporte fijo a la mangueta",
            tipo=TipoArticulacion.FIJA,
            padre=None,
            hijo="soporte_pinza",
        ),
        Articulacion(
            id="j_pinza_flotante",
            nombre="Deslizamiento de la pinza flotante",
            tipo=TipoArticulacion.PRISMATICA,
            padre="soporte_pinza",
            hijo="cuerpo_pinza",
            eje=(0.0, 0.0, -1.0),
            unidad="m",
            limites=LimitesMovimiento(minimo=0.0, maximo=0.003),
            descripcion="La reacción del pistón desplaza la pinza hacia el interior del vehículo.",
        ),
        Articulacion(
            id="j_piston",
            nombre="Carrera del pistón",
            tipo=TipoArticulacion.PRISMATICA,
            padre="cuerpo_pinza",
            hijo="piston",
            eje=(0.0, 0.0, 1.0),
            unidad="m",
            limites=LimitesMovimiento(minimo=0.0, maximo=0.003),
            descripcion="La presión hidráulica empuja el pistón hacia el disco.",
        ),
        Articulacion(
            id="j_pastilla_interna",
            nombre="Pastilla interna arrastrada por el pistón",
            tipo=TipoArticulacion.COMPUESTA,
            padre="cuerpo_pinza",
            hijo="pastilla_interna",
            eje=(0.0, 0.0, 1.0),
            unidad="m",
            maestra="j_piston",
            relacion=1.0,
        ),
        Articulacion(
            id="j_pastilla_externa",
            nombre="Pastilla externa arrastrada por la pinza",
            tipo=TipoArticulacion.COMPUESTA,
            padre="soporte_pinza",
            hijo="pastilla_externa",
            eje=(0.0, 0.0, -1.0),
            unidad="m",
            maestra="j_pinza_flotante",
            relacion=1.0,
        ),
    ]
    for i in range(1, p.n_esparragos + 1):
        articulaciones.append(
            Articulacion(
                id=f"j_esparrago_{i}",
                nombre=f"Espárrago {i} prensado",
                tipo=TipoArticulacion.FIJA,
                padre="cubo",
                hijo=f"esparrago_{i}",
            )
        )
    for i in (1, 2):
        articulaciones.append(
            Articulacion(
                id=f"j_pasador_{i}",
                nombre=f"Pasador {i} en soporte",
                tipo=TipoArticulacion.FIJA,
                padre="soporte_pinza",
                hijo=f"pasador_guia_{i}",
            )
        )
        articulaciones.append(
            Articulacion(
                id=f"j_tornillo_{i}",
                nombre=f"Tornillo {i} a mangueta",
                tipo=TipoArticulacion.FIJA,
                padre=None,
                hijo=f"tornillo_soporte_{i}",
            )
        )

    return Ensamblaje(
        id="freno_disco",
        nombre="Freno de disco delantero (pinza flotante)",
        descripcion="Conjunto de demostración: cubo, disco ventilado, pinza flotante de un pistón, "
        "pastillas, pasadores guía y tornillería.",
        version="2.0.0",
        advertencia=ADVERTENCIA,
        subconjuntos=[
            Subconjunto(
                id="rotacion",
                nombre="Conjunto giratorio",
                padre=None,
                descripcion="Cubo, espárragos y disco: giran con la rueda.",
            ),
            Subconjunto(
                id="pinza",
                nombre="Conjunto de pinza",
                padre=None,
                descripcion="Soporte, cuerpo flotante, pistón, pastillas y pasadores.",
            ),
            Subconjunto(
                id="fijacion",
                nombre="Fijación a la mangueta",
                padre=None,
                descripcion="Tornillos del soporte.",
            ),
        ],
        piezas=piezas,
        articulaciones=articulaciones,
        archivo_glb="freno_disco.glb",
        parametros={k: float(v) for k, v in p.model_dump().items()},
        procedencia_parametros={k: "demostrativo" for k in p.model_dump()},
    )
