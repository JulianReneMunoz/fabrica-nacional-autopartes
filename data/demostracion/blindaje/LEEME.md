# Documento de prueba del blindaje (caso 5)

`fragmentos.jsonl` contiene un único fragmento **ficticio**, escrito por el equipo del proyecto para demostrar el
blindaje contra inyección indirecta (R09, rúbrica 2.4, caso 5 de validación). **No es contenido de Fanalca**: su
origen es `demostrativo`, no tiene URL y su texto incluye a propósito una instrucción maliciosa («Ignora las
instrucciones anteriores…») que IGNIS debe neutralizar sin obedecerla.

- No forma parte del corpus Gold (`data/gold/`) ni de la semilla (`data/seed/`); el M1, la MCP, la batería de
  IGNIS y el CI no lo leen.
- IGNIS solo lo consulta con `FNA_IGNIS_DEMO_BLINDAJE=true` **y** cuando la pregunta menciona «documento de
  prueba» (tarjeta del caso 5 en Atención). Sin esa variable, no tiene ningún efecto.
- Las pruebas de `tests/integration/test_caso5_blindaje.py` lo usan directamente, sin la variable.
