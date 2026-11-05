# Prompt · Máquina 3D «Motocicleta Honda» con ficha técnica y preguntas frecuentes

> Uso: abrir Claude Code en `C:\fabrica-nacional-autopartes`, adjuntar las dos imágenes de referencia
> (lámina CB-160 STD/DLX y tablero de referencia de estilo) y escribir:
> `Lee docs/prompts/prompt_moto_honda_3d.md y ejecútalo en modo plan; espera mi aprobación antes de escribir código.`

---

Utiliza las skills `fna-maquinas-anatomia` y `fna-simulador-3d` (método Anatomy) para crear una nueva máquina
interactiva en el visor web (`web/`) sobre esta pregunta:

**¿Cómo convierte una motocicleta Honda el giro del motor en velocidad de la rueda, y la palanca en fuerza de
frenado?**

## 0. Reglas que no cambian

- **Conservar lo existente.** La máquina del freno (`#/freno`), la prensa, la línea y la biblioteca siguen
  funcionando igual. La motocicleta es una opción nueva en el frontend (`#/moto`) y una tarjeta nueva en la
  biblioteca. El modelo de freno (`web/src/modelos/freno.ts`) se reutiliza, no se duplica.
- **Stack fijo.** Windows 11, uv, FastAPI, PostgreSQL/SQLite, MCP, Vite + React + three + @react-three/fiber +
  drei. Sin notebooks, sin JupyterLab, sin Anaconda.
- **Estilo impersonal** en código, comentarios, documentación (sin primera ni tercera persona).
- **Datos verificables.** Ningún valor técnico se inventa. Cada dato de la ficha lleva fuente (URL o documento) y
  fecha de consulta. Un dato no encontrado se muestra como «No publicado», nunca se estima en silencio.
- **Scraping responsable.** Respetar `robots.txt`. Prohibido eludir CAPTCHAs, autenticación o bloqueos
  anti-bots: un host protegido se marca y se omite, igual que en el pipeline actual.
- **Propiedad intelectual.** El modelo 3D es **procedimental y esquemático**: una motocicleta *naked* genérica
  de baja cilindrada. No incluye logotipos, emblemas, el ala de Honda ni una réplica del diseño de carrocería
  de un modelo comercial. El nombre del modelo aparece solo como texto en la ficha. La lámina comercial no se
  muestra dentro de la aplicación: solo es fuente de datos.
- **Alcance didáctico.** La geometría no es diseño industrial certificado y la animación no valida la mecánica.
  No se generan procedimientos de reparación, mantenimiento ni instrucciones de seguridad vial.
- **El backend valida** todo valor que envíe el cliente (Pydantic, rangos, 422 ante entradas inválidas).

## 1. Asignación de modelos por especialidad (subagentes de `.claude/agents/`)

| Fase | Subagente | Modelo |
|---|---|---|
| Mecanismo, relaciones físicas y supuestos | `arquitecto-mecanico-3d` | opus |
| Esquema de datos, API y ADR | `arquitecto-sistema` | opus |
| Fichas técnicas (investigación y YAML) | `ingeniero-datos` | sonnet |
| Preguntas frecuentes y respuestas con citas | `ingeniero-llm` | sonnet |
| Escena 3D, paneles y controles | `ingeniero-3d-frontend` | sonnet |
| Revisión crítica final | `revisor-calidad` | opus |
| Lint, tipos y pruebas rápidas | `verificador-rapido` | haiku |
| README, matriz y bitácora | `documentador` | sonnet |

`CLAUDE_CODE_SUBAGENT_MODEL` debe permanecer sin definir para que cada subagente use su modelo.

## 2. Investigar antes de diseñar

1. **Portafolio.** Revisar la base de conocimiento (`data/gold/docs/negocios-honda-motocicletas.md`: Fanalca
   ensambla en Acopi, Yumbo, motocicletas Honda de 100 a 250 cc) y el sitio oficial de Honda Motos Colombia.
   Seleccionar **entre 3 y 5 modelos vigentes**, incluida la **CB 160F STD/DLX**.
2. **Ficha técnica por modelo.** Para cada uno: tipo de motor, cilindrada, diámetro × carrera, potencia y
   régimen, torque y régimen, relación de compresión, transmisión (número de marchas, relación primaria,
   relaciones de cada marcha, transmisión final piñón/corona), frenos delantero y trasero, CBS, suspensiones,
   medidas de llanta, capacidad del tanque, peso, arranque, iluminación e instrumentos.
3. **Datos de la lámina CB-160 (STD/DLX) aportada por el usuario**, para contrastar con la fuente oficial:
   - Motor Honda 4T; «Pot: 15,04 / 8.000 RPM». La unidad no aparece en la lámina y debe confirmarse con la
     fuente oficial antes de mostrarse.
   - Llanta trasera ancha 140/70-17.
   - Freno de disco delantero. Freno de disco trasero y sistema de frenos combinado CBS solo en la versión DLX.
   - Monosuspensión trasera (la lámina dice «Pro Arm»: verificar la denominación oficial).
   - Arranque eléctrico y de pedal, velocímetro digital, farola multifocal, stop LED en forma de X, sillín de
     doble nivel, tanque robusto.

   En el YAML, la fuente de estos valores es `lamina-cb160-std-dlx (aportada por el usuario)`. Si la fuente
   oficial publica un valor distinto, prevalece la oficial y la diferencia se registra en la bitácora.
4. **Relaciones que la máquina debe preservar** (todas en un único modelo TypeScript, `web/src/modelos/moto.ts`):
   - **Radio de la llanta desde su medida:** para `ancho/perfil-rin`,
     `D = rin·25,4 + 2·ancho·perfil/100` (mm). Para 140/70-17: D = 627,8 mm y R ≈ 0,314 m.
   - **Velocidad desde el régimen:**
     `v [km/h] = rpm · 2π·R · 60 / (1000 · i_primaria · i_marcha · i_final)`. Si una relación no está
     publicada, se usa un valor de ejemplo marcado visiblemente como «supuesto didáctico».
   - **Cilindrada desde diámetro y carrera:** `V = π/4 · D² · carrera`. Debe coincidir con la cilindrada de la
     ficha con un margen de ±1 %. Si no coincide, se señala en la revisión crítica.
   - **Biela-manivela:** `x(θ) = r·cos θ + √(L² − r²·sin² θ)`, con `r = carrera/2`. El ciclo de 4 tiempos ocupa
     720° de cigüeñal (admisión, compresión, expansión, escape), y las válvulas y la chispa se sincronizan con θ.
   - **Frenado:** reutilizar `calcularFreno` y `estadoRueda` (bloqueo). Con CBS, la palanca trasera reparte
     fuerza entre ambos discos con una proporción marcada como «supuesto didáctico» si no está publicada.

## 3. Datos y backend

- **Fichas curadas:** `data/catalogo/motos_honda.yaml`. Cada campo tiene la forma
  `{valor, unidad, fuente, fecha_consulta, estado: publicado|no_publicado|supuesto}`.
- **Esquemas Pydantic** en `api/esquemas.py`. Rutas nuevas en `api/routes/motos.py`:
  - `GET /api/motos`: lista resumida.
  - `GET /api/motos/{id}`: ficha completa con fuentes.
  - `GET /api/motos/{id}/faq`: preguntas de modelo respondidas desde la ficha, de forma determinista, con el
    campo y la fuente que sustentan cada respuesta.
  - `POST /api/motos/{id}/calculo`: velocidad, cilindrada y frenado. Valida rpm, marcha y fuerza de palanca.
- **Ensamblaje del simulador:** registrar la motocicleta como `moto-honda` en el modelo de ensamblajes
  existente (piezas, jerarquía, despiece, secuencia, articulaciones), para que el visor y el servidor MCP la
  expongan igual que el freno.
- **Preguntas frecuentes sobre Fanalca:** tomar las preguntas respondibles de `evaluacion/preguntas.yaml` (sede,
  contacto, planta, red de distribución, portafolio…). Las respuestas se generan con `POST /api/qa` (proveedor
  `claude_code`, modelo `sonnet`, prompt `v3`) y se guardan con sus citas en `data/gold/faq_visor.json` mediante
  un comando nuevo `uv run fabrica faq-visor`, para que la demostración no dependa de la latencia. El botón
  «Preguntar en vivo» usa `POST /api/qa` directamente. Una pregunta sin respuesta en la base muestra la frase de
  rechazo; no se completa con conocimiento general.
- ADR-017 registra las decisiones: fichas curadas frente a scraping, respuestas deterministas para modelos y
  respuestas precalculadas con LLM para Fanalca.

## 4. La máquina (`web/src/paginas/MaquinaMoto.tsx` + `EscenaMoto.tsx`)

### El objeto
Motocicleta reconocible a primera vista. Está construida con piezas agrupadas en **ensamblajes**: motor
(cilindro, pistón, biela, cigüeñal, válvulas, bujía), transmisión (caja, piñón, cadena, corona), chasis y
tanque, suspensión delantera (horquilla telescópica), suspensión trasera (monoamortiguador y basculante),
frenos (disco delantero, disco o tambor trasero, cálipers, CBS), ruedas y llantas (dimensionadas con la medida
real de la ficha), sistema eléctrico (farola, stop, velocímetro) y escape.

### La vista interior
- **Corte del motor:** el pistón sube y baja según la biela-manivela, las válvulas abren en su fase y la chispa
  aparece en la expansión.
- **Despiece:** separación animada por ensamblaje.
- **Transmisión expuesta:** el piñón y la corona giran con la relación real; la rueda gira a la velocidad que
  calcula el modelo.

### Los controles (de 2 a 4, junto a la parte que afectan)
1. **Acelerador (rpm):** de ralentí hasta el corte de encendido de la ficha.
2. **Marcha:** N, 1.ª a 5.ª (o las que tenga el modelo).
3. **Palanca de freno:** delantera o trasera, y CBS activado o desactivado si la versión lo incluye.
4. **Selector de modelo:** cambia la ficha y redimensiona la llanta y el motor.

Además: ejecutar, pausar, reiniciar y **cámara lenta obligatoria para el motor**. A 8.000 rpm el cigüeñal da
133 vueltas por segundo, así que la escala de tiempo se muestra siempre (p. ej., «animación a 1/200 de la
velocidad real»).

### Los números (salen del mismo modelo, junto a la pieza)
- rpm y ángulo del cigüeñal junto al motor, con la fase del ciclo 4T.
- Relación total y velocidad junto a la rueda trasera.
- Cilindrada calculada frente a la cilindrada de la ficha.
- Fuerza, torque de frenado y estado de bloqueo junto a cada disco.

### La retroalimentación y la idea principal
Etiquetas cortas que explican qué cambió («marcha 3.ª: la rueda gira 1/x del motor»). Debajo de la máquina, una
sola frase: **«La velocidad es el giro del motor dividido por las relaciones de transmisión y multiplicado por
la circunferencia de la llanta; el freno invierte el camino y convierte la fuerza de la mano en torque sobre la
rueda.»**

### Modo experimento (romper la regla)
- rpm por encima del corte: el limitador corta la chispa.
- Marcha alta con rpm bajas: el motor se ahoga por debajo del ralentí.
- Fuerza de palanca excesiva sin CBS: la rueda se bloquea (modelo de freno existente).

Cada caso muestra qué deja de funcionar y por qué.

## 5. Distribución de pantalla

Tablero de laboratorio claro, con la imagen de referencia de estilo adjunta como guía de **composición**, no de
marca:

- **Fondo y tipografía:** fondo claro, un solo color de acento (naranja), etiquetas en mayúsculas monoespaciadas
  y números grandes.
- **Cabecera:** nombre del modelo, versión (STD/DLX), estado («EN MARCHA», «FRENANDO», «DESPIECE»), rpm, marcha y
  velocidad.
- **Columna izquierda** (pestañas plegables):
  - «Datos en vivo»: motor con el diagrama del ciclo 4T, transmisión y frenos.
  - «FAQ Fanalca»: lista de preguntas. Al pulsar una se despliega la respuesta con citas y el enlace a la fuente.
- **Centro:** la motocicleta ocupa la mayor parte del espacio, con rotación orbital y giro automático opcional.
- **Columna derecha** (pestañas plegables):
  - «Ficha técnica»: tabla agrupada por sistema, con fuente y estado de cada valor. Al pulsar un dato, se resalta
    la pieza correspondiente en 3D.
  - «FAQ modelos»: preguntas sobre el modelo seleccionado, como «¿qué potencia tiene?», «¿qué diferencia hay
    entre STD y DLX?», «¿qué es el CBS?» o «¿qué medida tiene la llanta trasera?».
  - «Ensamblajes»: chips para aislar motor, transmisión, chasis, suspensión, frenos, ruedas o eléctrico.
  - «Vista»: etiquetas, despiece, corte del motor y giro.
- **Franja inferior:** línea de tiempo de la secuencia (arranque → acelerar → cambiar marcha → frenar con CBS →
  despiece) con reproducir, pausar y pasos.
- **Paleta y accesibilidad:** colores validados para daltonismo con la skill `dataviz`. Las etiquetas 3D son
  superposiciones DOM proyectadas, igual que en `EscenaFreno`. El diseño es responsivo: en pantallas estrechas,
  las columnas pasan a cajones.

## 6. Pruebas y evidencias

- **Vitest** (`modelos.test.ts`):
  - El radio de 140/70-17 es 0,3139 m (±0,001).
  - La cilindrada calculada coincide con la ficha.
  - La velocidad crece de forma lineal con rpm y decrece con la relación.
  - La posición del pistón está en [PMI, PMS] y la carrera vale 2r.
  - El ciclo dura 720°.
  - Con CBS, la suma de fuerzas se conserva.
  - Ningún valor es `NaN`.
- **Vitest de interfaz:** los controles actualizan los números, las FAQ se despliegan y la ficha muestra
  «No publicado» cuando corresponde.
- **pytest:**
  - Esquema del YAML: todo valor tiene fuente y fecha, o estado `no_publicado`.
  - Rutas `/api/motos*`, con 422 ante rpm negativas o marcha inexistente.
  - `faq-visor` con un proveedor simulado.
- **Playwright** (`e2e/moto.spec.ts`): carga, controles, ficha, FAQ y modo experimento.
- **Capturas:** guardar en `docs/capturas/`.
- **Recorrido automático de menos de 30 s:** acelerar, cambiar a 3.ª, frenar con CBS, despiece y corte del
  motor. Se graba en `docs/videos/recorrido_moto.mp4` con CDP screencast + ffmpeg, igual que el del freno, con
  la máquina centrada y sin cursor.

## 7. Revisión crítica (`revisor-calidad`, opus)

Revisar la máquina como un crítico severo:

1. Probar todos los controles y estados.
2. Buscar piezas que se mueven mal, números que no coinciden (velocidad, cilindrada, giro de rueda frente a
   giro de corona), datos sin fuente, etiquetas ilegibles, estados imposibles (marcha engranada con rueda
   detenida y motor en marcha sin embrague) y cualquier cosa que enseñe una idea equivocada.
3. Corregir y volver a comprobar.

La máquina termina cuando el modelo, los números y la imagen cuentan la misma historia.

## 8. Documentación y cierre

- **Documentación técnica:** ecuaciones, supuestos, capturas y tabla de fuentes de las fichas en el ADR-017 y
  en `docs/`.
- **Trazabilidad:** ADR-017, matriz (`V2-16` en adelante; sin «;» dentro de los campos), fase nueva en
  `fases_agentes.yaml` y entrada en la bitácora.
- **README:** ruta `#/moto` y comando `faq-visor`.
- **Streamlit:** la pestaña «Simulador 3D» enlaza la nueva máquina.
- **Verificación local:** ejecutar `.\scripts\verificar_calidad.ps1` (Ruff, mypy, capas, pytest, Vitest,
  build). Todo debe pasar antes del commit.
- **Commit sugerido:** `feat: máquina 3D de motocicleta Honda con ficha técnica y preguntas frecuentes`.
  El push solo se hace tras la aprobación del usuario.

**Criterio de terminado:** en cinco segundos se entiende qué es el objeto, dónde empieza el proceso y qué se
puede tocar; cada número tiene su fuente o su marca de supuesto; el CI sigue en verde.
