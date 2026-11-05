# Motocicleta de referencia con fichas Honda: modelo, supuestos y fuentes

Documento técnico de la máquina `moto_honda` (ver también [ADR-017](adr/ADR-017-motocicleta-referencia-fichas-honda.md)).
La motocicleta es una **referencia genérica y esquemática** (*naked* de unos 150 cc), sin logotipos ni réplica
de un modelo comercial. La geometría no es diseño industrial certificado y la animación no valida propiedades
mecánicas. Las fichas técnicas son datos curados con fuente, fecha y estado.

## 1. Relaciones del modelo

La física vive en `src/fabrica_autopartes/simulador/fisica_moto.py` y se replica en `web/src/modelos/moto.ts`.
La paridad Python y TypeScript se comprueba con `web/src/__tests__/referencia_moto.json` (tolerancia 1e-6).

| Relación | Expresión |
|---|---|
| Diámetro de llanta `ancho/perfil-rin` | `D = rin·25,4 + 2·ancho·perfil/100` (mm) |
| Velocidad | `v [km/h] = rpm · 2π·R · 60 / (1000 · i_primaria · i_marcha · i_final)` |
| RPM con marcha engranada | `rpm = v · i_total / (2π·R) · 60` |
| Cilindrada | `V = π/4 · D² · carrera` |
| Biela-manivela (θ = 0 en el PMS) | `x(θ) = r·cos θ + √(L² − r²·sin² θ)`, con `r = carrera/2` |
| Ángulo de la biela | `φ = asin(r·sin θ / L)` |
| Ciclo de 4 tiempos | 720° de cigüeñal: admisión, compresión, expansión, escape |
| Cadena | `v = ω_piñón · r_piñón = ω_corona · r_corona` |
| Frenado | `fisica_freno.calcular` por disco; el CBS reparte la presión y conserva la suma |

Para 140/70-17 resulta `D = 627,8 mm` y `R = 0,3139 m`; para 130/70-17, `R = 0,3069 m`; para 90/80-17,
`R = 0,2879 m`.

### Dinámica continua

La velocidad es una variable de estado continua (`paso_moto`, con paso `dt`). Con marcha engranada las rpm se
derivan de la velocidad: al cambiar de marcha saltan las rpm, no la velocidad. El acelerador produce una
aceleración simple, el freno una desaceleración tomada del cálculo de frenado, y en neutro la velocidad decae
por rozamiento sin detenerse en seco. Al soltar el freno la moto continúa desde su velocidad actual. La relación
de la velocidad con las rpm se cumple siempre que haya marcha engranada, salvo el tramo explícito de patinaje de
embrague en el arranque.

## 2. Supuestos didácticos

Todo valor necesario para la simulación que **no está publicado** se declara como «supuesto didáctico» en
`SUPUESTOS_REFERENCIA` (Python) y en `moto.ts`, y se muestra con esa marca en la interfaz.

| Clave | Valor | Unidad |
|---|---|---|
| `cilindrada_nominal_cm3` | 150 | cm³ |
| `diametro_mm` / `carrera_mm` | 57,0 / 58,7 | mm |
| `longitud_biela_mm` | 105 | mm |
| `medida_llanta_trasera` / `medida_llanta_delantera` | 130/70-17 / 90/80-17 | — |
| `ralenti_rpm` / `corte_encendido_rpm` | 1.400 / 9.500 | rpm |
| `n_marchas` | 5 | — |
| `relacion_primaria` | 3,35 | — |
| `relaciones_marcha` | 2,80 · 1,90 · 1,40 · 1,10 · 0,95 | — |
| `relacion_final` | 3,0 (corona 42 / piñón 14) | — |
| `presion_bar_por_newton` | 0,30 | bar/N |
| `reparto_cbs_delantero` | 0,40 | — |
| `coeficiente_friccion` / `adherencia_neumatico` | 0,40 / 0,90 | — |
| `diametro_piston_m` / `radio_efectivo_m` | 0,030 / 0,10 | m |
| `masa_por_rueda_kg` / `inercia_rueda_kg_m2` | 120 / 0,9 | kg · kg·m² |
| `aceleracion_max_m_s2` | 3,0 | m/s² |
| `rozamiento_m_s2` / `arrastre_aero_1_m` | 0,5 / 0,0023 | m/s² · 1/m |
| `tau_rpm_libre_s` / `rpm_tope_libre` | 0,25 / 11.000 | s · rpm |
| `banda_limitador_rpm` | 100 | rpm |
| `acelerador_minimo_sin_ahogo` / `marcha_minima_ahogo` | 0,20 / 3 | — |

Radios de paso de la cadena: piñón 0,03 m y corona 0,09 m (relación 3,0).

## 3. Fichas técnicas y fuentes

Las fichas viven en `data/catalogo/motos_honda.yaml`. Cada campo lleva `{valor, unidad, fuente, fecha_consulta,
estado}` con `estado ∈ {publicado, no_publicado, supuesto}`. Un valor sin fuente y fecha, o un `no_publicado` con
valor, invalida el catálogo (`services.motos.validar_catalogo`).

| Fuente | Tipo | Observación |
|---|---|---|
| `lamina-cb160-std-dlx (aportada por el usuario)` | documento aportado | Única fuente de datos de la CB 160F STD/DLX; consulta 2026-11-04. La lámina no se muestra en la aplicación. |
| `motos.honda.com.co` | sitio oficial | `robots.txt` permite el acceso; las páginas de producto respondieron HTTP 307 sin cuerpo a la lectura automatizada (no legible automáticamente). No hay página de producto de la CB 160F en el sitemap. |

Campos de la CB 160F con estado `publicado`: tipo de motor (Honda 4T), régimen de potencia (8.000 rpm), suspensión
trasera (monosuspensión), llanta trasera (140/70-17), arranque (eléctrico y de pedal), iluminación, instrumentos,
sillín y tanque (descripción), freno delantero de disco (STD y DLX), freno trasero de disco y CBS solo en la DLX.
El resto queda `no_publicado`: cilindrada, diámetro por carrera, potencia (la unidad de la lámina no está
confirmada), torque, relación de compresión, relaciones de transmisión, suspensión delantera, llanta delantera,
tanque en litros, peso y reparto del CBS.

El selector **«Ver con ficha de…»** aplica solo los campos `publicado`; lo no publicado conserva el valor genérico con
su marca de supuesto. Con la ficha CB 160F la llanta trasera pasa de 130/70-17 a 140/70-17 y la rueda 3D cambia de
tamaño junto con la velocidad calculada.

## 4. Geometría y ensamblaje

El ensamblaje `moto_honda` (`simulador/catalogo_moto_honda.py`) tiene 79 piezas, 79 articulaciones y 11
subconjuntos. Todas las piezas se posicionan desde un módulo único de puntos duros
(`simulador/puntos_duros_moto.py`): entre ejes de 1,30 m, altura de sillín de 0,79 m, lanzamiento de 26° e
inclinación del cilindro de 15°. La posición armada se valida con una prueba de conectividad: cada pieza (salvo la
raíz) debe tocar o solaparse con la pieza a la que se monta, con tolerancia de 2 mm. El despiece es radial por
subconjunto. Los neumáticos se modelan con sección circular y ancho menor que el nominal; el radio exterior
coincide con el de la medida declarada.

## 5. API y datos servidos

| Ruta | Descripción |
|---|---|
| `GET /api/v1/motos` | lista resumida de fichas |
| `GET /api/v1/motos/{id}` | ficha completa con fuentes y supuestos |
| `GET /api/v1/motos/{id}/faq` | preguntas del modelo, respondidas de forma determinista desde la ficha |
| `POST /api/v1/motos/{id}/calculo` | cálculo didáctico; valida rpm, marcha, fuerza de palanca y versión (422 ante entradas inválidas) |
| `GET /api/v1/faq-visor` | respuestas precalculadas de las preguntas frecuentes de Fanalca |

Las respuestas de Fanalca se generan con `uv run fabrica faq-visor` (proveedor `claude_code`, modelo `sonnet`, prompt
`v3`) y se guardan con sus citas en `data/gold/faq_visor.json`.

## 6. Limitaciones

- Sin cilindrada, diámetro por carrera, relaciones de transmisión ni potencia publicadas, la comprobación de
  cilindrada y la velocidad por marcha usan valores típicos marcados como supuesto.
- El embrague no se modela: al frenar el motor vuelve a ralentí y la transmisión sigue a la rueda.
- La chispa salta en el punto muerto superior, sin avance de encendido.
- Los discos usan un radio efectivo supuesto, aunque la escena dibuja discos de 280 y 220 mm.
- El rendimiento se midió con renderizado por software (SwiftShader), no con una GPU real.
