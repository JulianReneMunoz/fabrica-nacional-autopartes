# Fase 7a · Fidelidad 3D de la moto

Agregar al plan una fase 7a «Fidelidad 3D de la moto», después de la fase 7 y antes de la 7b, sin cambiar
cálculos ni los ids de piezas/articulaciones que usa la animación (solo se añaden o reubican piezas).

0. **Diagnóstico de la captura actual (corregir todo):**
   - El motor (pistón y biela) flota, sin cárter ni soporte.
   - Hay una caja oscura y una barra diagonal sueltas.
   - El tanque y el sillín no tienen apoyo.
   - El chasis es un solo tubo.
   - El motor es demasiado pequeño respecto a las ruedas.
   - El resaltado pinta toda la llanta trasera de naranja: usar un contorno, sin recolorear la pieza.
   - Las etiquetas quedan lejos de su pieza («Tras.: sin accionar») y no tienen línea guía.
   - La etiqueta «ficha 150» es incorrecta, porque la cilindrada no está publicada. Debe decir
     «150 cm³ nominal — supuesto didáctico».

1. **Skills:** escanear con skillspector (`--no-llm`, puntuación < 51) e instalar, desde la carpeta temporal de
   CloudAI-X/threejs-skills, las de lighting, materials, postprocessing y performance. Registrar el
   resultado en la bitácora (S-02).

2. **Puntos duros primero:** definir en un solo módulo las coordenadas de:
   - eje delantero y eje trasero;
   - pipa de dirección (lanzamiento ~26°);
   - pivote del basculante;
   - anclajes del amortiguador;
   - soportes del motor.

   Las proporciones son las de una naked de ~150 cc, como supuesto didáctico: entre ejes ~1,30 m y altura de
   sillín ~0,79 m. Todas las piezas se posicionan a partir de esos puntos.

3. **Geometría con formas reales:**
   - Lathe: tanque, escape, barras de horquilla, faro, perfil del neumático y cubos.
   - Tube sobre curvas: chasis de doble cuna que abraza el motor, manubrio, codo del escape desde la culata,
     cables y mangueras.
   - Extrude: guardabarros, cubiertas laterales, basculante, sillín y colín.
   - Motor a escala real: cárter, cilindro inclinado con aletas, culata y tapas laterales. El corte muestra el
     pistón y la biela dentro del cilindro.
   - Detalle mecánico: dientes en piñón y corona, eslabones de cadena con InstancedMesh, discos perforados y
     rines de 5–6 rayos.

4. **Piezas nuevas** (~70 en total), cada una en su subconjunto y con despiece:
   - Dirección: tijas, manubrio, manijas, puños y espejos.
   - Carrocería: guardabarros, cubiertas laterales, colín, tapa del tanque y porta placa.
   - Motor: culata, tapas del motor, filtro de aire y cuerpo de aceleración.
   - Transmisión: pedal de cambios, tensores y cubrecadena.
   - Frenos: bomba y manguera de freno, y pedal de freno.
   - Chasis: estribos y caballete lateral.
   - Eléctrico: direccionales y batería.

   La moto es genérica, sin logotipos ni réplica de un modelo comercial.

5. **Materiales e iluminación:**
   - Materiales PBR por tipo: metal pulido, caucho mate, pintura semibrillante y aluminio.
   - Iluminación de estudio con Lightformers locales, sin descargar HDR.
   - Sombras de contacto, SSAO y tone mapping ACES.
   - Selección con contorno.
   - Etiquetas pegadas a su pieza, con línea guía.
   - Rendimiento ≥ 50 fps en un portátil.

6. **Verificación:**
   - Los hashes del freno no cambian.
   - Pasan pytest, Vitest, Playwright y `simulador validar --ensamblaje moto_honda`.
   - Capturas de antes y después desde tres ángulos: lateral, 3/4 y despiece.
   - Volver a grabar el video del recorrido (< 30 s).
   - El script de cierre se detiene antes del commit si alguna prueba falla.

7. **Prueba de conectividad nueva en `simulador validar`:** en la posición armada, cada pieza (salvo la raíz)
   debe tocar o solaparse con la pieza a la que se monta, con una tolerancia de 2 mm. Ninguna pieza puede
   quedar flotando. Añadir la prueba a pytest.

**Orden final:** 7 → 7a → 7b → 8 → 9, con un commit local al cerrar cada fase.
- Detenerse al terminar la 7a para mostrar las capturas, y otra vez tras la 7b.
- En el commit de la fase 8, incluir el reporte de evaluación sin seguimiento (`…v3_completo.md`) de
  `evaluacion/resultados/`.
