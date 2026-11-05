# ADR-017 · Motocicleta de referencia genérica con fichas Honda curadas

- **Estado:** aceptada
- **Contexto:** la biblioteca de máquinas necesita explicar cómo una motocicleta convierte el giro del motor en
  velocidad de rueda y la fuerza de la palanca en frenado. El sitio oficial de Honda Motos Colombia
  (`motos.honda.com.co`) permite el acceso según `robots.txt` (`Allow: /`), pero sus páginas de producto
  respondieron HTTP 307 sin cuerpo a la lectura automatizada y la CB 160F carece de página de producto en el
  sitemap. Las fichas disponibles son la lámina CB-160 (STD/DLX) aportada por el usuario y las fichas que este
  pegue después. La geometría de una moto comercial no debe replicarse (propiedad intelectual).
- **Decisión:**
  1. **Un solo ensamblaje 3D genérico.** `moto_honda` (identificador único en backend, API, visor y GLB) es una
     motocicleta *naked* esquemática de unos 150 cc, sin logotipos ni réplica de un modelo comercial. Sus parámetros
     de cálculo son «valores típicos de la categoría — supuesto didáctico», declarados en
     `simulador/fisica_moto.py` (`SUPUESTOS_REFERENCIA`) y en `web/src/modelos/moto.ts`, y visibles en la interfaz.
  2. **Fichas curadas, no scraping.** `data/catalogo/motos_honda.yaml` guarda cada campo como
     `{valor, unidad, fuente, fecha_consulta, estado}` con `estado ∈ {publicado, no_publicado, supuesto}`. Un valor
     sin fuente y fecha, o un `no_publicado` con valor, invalida el catálogo (`services.motos.validar_catalogo`).
     Las fichas posteriores solo amplían el YAML.
  3. **«Ver con ficha de…».** El selector de modelo aplica únicamente los campos `publicado` (medida de llanta,
     freno trasero, CBS, cilindrada, diámetro × carrera, potencia, marchas). Lo no publicado conserva el valor
     genérico con su marca de supuesto. La respuesta de cálculo informa qué se aplicó y qué se conservó.
  4. **FAQ de modelo deterministas.** `GET /api/v1/motos/{id}/faq` responde desde la ficha, con el campo y la
     fuente que sustentan cada respuesta; un dato ausente se muestra como «No publicado».
  5. **FAQ de Fanalca precalculadas.** El comando `fabrica faq-visor` genera respuestas con el proveedor
     `claude_code` (modelo `sonnet`, prompt `v3`) mediante `POST /api/v1/tareas/qa` y las guarda con sus citas en
     `data/gold/faq_visor.json`; la demostración no depende de la latencia del modelo. «Preguntar en vivo» usa el
     mismo endpoint. Sin respuesta en la base se muestra la frase de rechazo fija.
  6. **Física separada de la escena.** `simulador/fisica_moto.py` reutiliza `fisica_freno.calcular` por disco;
     el CBS reparte la presión entre ambos discos y conserva la suma. La animación no valida propiedades mecánicas.
  7. **Contratos.** Rutas `GET /api/v1/motos`, `/motos/{id}`, `/motos/{id}/faq` y `POST /motos/{id}/calculo` con
     validación Pydantic (rpm, marcha, fuerza de palanca, versión; 422 ante entradas inválidas). Los modelos de
     respuesta residen en `services/motos.py` y se reexportan en `api/esquemas.py` para respetar la regla de
     dependencias entre capas.
  8. **Ruta del visor.** `#/maquina/moto_honda` conserva la convención de la biblioteca; `#/moto` actúa como alias.
     Tarjeta de la biblioteca: «Motocicleta (referencia genérica) con fichas Honda».
- **Alternativas:** una geometría por modelo comercial (descartada: propiedad intelectual y datos insuficientes);
  scraping automatizado de las fichas (descartado: respuesta 307 y fichas sin publicar); respuestas de modelo
  generadas con un LLM (descartadas: se exige trazabilidad campo → fuente).
- **Consecuencias:** varias cifras de la simulación (relaciones de caja, cilindrada, diámetro × carrera, corte de
  encendido) se muestran como supuesto didáctico hasta que existan fichas que las publiquen. El diseño de ensamblaje
  genérico permite ampliar modelos sin tocar la geometría. Los cambios en `Geometria`, `generacion`,
  `parametros_animacion` y la herramienta MCP `consultar_pieza` son retrocompatibles (el ensamblaje por defecto
  sigue siendo `freno_disco`).
