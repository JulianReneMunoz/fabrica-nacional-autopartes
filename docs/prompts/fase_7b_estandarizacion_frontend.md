# Fase 7b · Estandarización y estructura del frontend

Ampliar la fase 7b del plan con este alcance. Va después de la 7a y no cambia ningún cálculo, mecanismo, id de
pieza ni ruta. Se conservan las skills de la 7b (frontend-design, anatomy, data-visualization, con escaneo
registrado como S-03).

## 1. Referencia visual (el estilo actual pasa a ser el estándar)

El estilo de las páginas actuales de **freno** y **línea** y de la **biblioteca** se mantiene y se aplica igual a
todas las páginas, incluida la moto:
- fondo claro cuadriculado;
- barra superior negra;
- un solo acento naranja;
- texto en sans-serif, y etiquetas y números en monoespaciada;
- paneles con borde fino, sin sombras pesadas.

Hoy la moto usa otra distribución, con todo encima del lienzo. Debe pasar a la misma plantilla que las demás.

## 2. Defectos observados en las capturas (corregir)

1. **Biblioteca:** en las tarjetas aparecen asteriscos de Markdown sin procesar («\*\*Yumbo\*\* y
   \*\*Bogotá\*\*»). Hay que renderizar el Markdown en línea o limpiarlo.
2. **Biblioteca:** el contenido ocupa una franja angosta en pantallas anchas (1920 px) y la cuarta tarjeta (moto)
   queda abajo. La cuadrícula debe usar el ancho disponible: 4 columnas en ≥ 1600 px, 3 en ≥ 1200 px, 2 en
   ≥ 800 px y 1 en móvil.
3. **Cabecera:** en ventanas medianas la navegación se corta («Bibli…»). Debe ser responsiva, con menú plegable
   por debajo de 900 px.
4. **Navegación con etiquetas inconsistentes** («Freno 3D», «Prensa», «Línea», «Moto»). Unificarlas: Biblioteca ·
   Freno · Prensa · Línea · Moto · API, con estado activo visible.
5. **Panel lateral distinto en cada máquina:** el freno muestra «Árbol de componentes», la línea «Datos de la
   empresa» y la moto paneles flotantes. Debe ser un solo panel con pestañas estándar (sección 3).
6. **Lienzo 3D del freno:** el modelo ocupa una parte pequeña del área. Encuadrar la cámara automáticamente al
   tamaño del ensamblaje (fit to bounds), con margen.
7. **Idea principal:** según el método Anatomy, es una sola frase y va **debajo** de la máquina, igual en todas
   las páginas.

## 3. Plantilla común `PlantillaMaquina` (mismo orden en todas las máquinas)

1. Migas («← Biblioteca») y título con la pregunta.
2. Franja de la fórmula: insignia con la fórmula + una línea de contexto.
3. **Lienzo** (8 de 12 columnas) con una barra de herramientas estándar:
   - Las máquinas 3D (freno, moto) usan: Ensamblado · Despiece · Sección · Cámara · PNG · Guardar vista ·
     Recorrido 30 s.
   - Las máquinas 2D (prensa, línea) usan solo los botones que les aplican, en el mismo orden.
4. **Columna lateral** (4 de 12 columnas):
   - «Controles» siempre visible arriba: deslizadores, Correr/Reiniciar y velocidad.
   - Debajo, pestañas estándar: **Componentes** · **Datos de la empresa** · **Ficha técnica** (solo moto) ·
     **FAQ** (Fanalca y modelo).
5. Fila de **chips de números**, que salen del mismo modelo que la animación.
6. **Idea principal** (una frase).
7. Dos tarjetas lado a lado: «Mecanismo paso a paso» y «Modo experimento».
8. Nota al pie: «Cifras demostrativas; los datos de la empresa provienen de fuentes oficiales citadas por URL».

**Diseño responsivo:**
- Por debajo de 1100 px, la columna lateral pasa debajo del lienzo.
- Por debajo de 700 px, los paneles se convierten en cajones.
- En el tamaño del recorrido (1280×800), el lienzo no puede quedar estrecho ni las etiquetas solapadas.

## 4. Componentes únicos (una sola implementación reutilizada)

- **`InsigniaFuente`**: SCRAPING · LECTURA WEB · BASE DE CONOCIMIENTO · FICHA · SUPUESTO DIDÁCTICO ·
  NO PUBLICADO. Siempre en una sola línea (`white-space: nowrap`), cada una con su color y su texto, para que
  nunca dependan solo del color.
- **`ChipDato`** con cuatro variantes:
  - neutro;
  - dato (azul);
  - supuesto (borde punteado + insignia);
  - estado (verde o rojo, con ícono y texto).
- **`BarraLienzo`**, **`PanelLateral`** (con pestañas), **`TarjetaMaquina`** (biblioteca), **`PasoAPaso`**,
  **`ModoExperimento`** y **`EtiquetaPieza`** (pegada a la pieza, con línea guía).

## 5. Sistema de diseño (tokens)

- Crear `web/src/tema/tokens.css` con variables CSS para colores, tipografías, escala de espaciado (4/8 px),
  radios, bordes y estados.
- Validar la paleta con `/dataviz` para daltonismo y contraste AA.
- Ningún color ni tamaño fijo dentro de los componentes: todo sale de los tokens.

## 6. Estructura del código

```
web/src/
  tema/tokens.css
  componentes/plantilla/   PlantillaMaquina, BarraLienzo, PanelLateral, ChipDato, InsigniaFuente,
                           EtiquetaPieza, PasoAPaso, ModoExperimento, TarjetaMaquina
  maquinas/<id>.ts         definición declarativa de cada máquina: pregunta, fórmula, idea principal,
                           pasos, experimentos, controles, pestañas disponibles
  paginas/                 cada página solo aporta su escena y su configuración
```

- Eliminar el código duplicado entre MaquinaFreno, MaquinaPrensa, MaquinaLinea y MaquinaMoto.
- La biblioteca se construye a partir de `maquinas/*.ts`.

## 7. Accesibilidad

- Foco visible en todos los controles.
- Deslizadores operables con teclado y con `aria-label`.
- Contraste AA.
- Respeto a `prefers-reduced-motion`: en ese caso, el recorrido automático no se inicia solo.

## 8. Verificación y cierre

- Pasan Vitest (incluidos los nuevos componentes de la plantilla), Playwright de las cuatro máquinas y la
  biblioteca, y pytest.
- Los hashes del freno no cambian.
- Capturas de antes y después de la biblioteca y de las cuatro máquinas a 1280×800 y 1920×1080, guardadas en
  `docs/capturas/v2/` solo cuando hay un cambio real. Playwright no debe sobrescribir los PNG versionados: sus
  capturas de prueba van a `test-results/`.
- Volver a grabar el video del recorrido de la moto (< 30 s).
- Commit local al cerrar la fase.
- Detenerse para mostrar las capturas de antes y después.
