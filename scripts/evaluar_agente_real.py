"""Banco de 24 preguntas contra el agente con el modelo real configurado (A-08).

Consume la API: se ejecuta solo con ``FNA_PRUEBAS_AGENTE_REAL=1``. Usa la configuración y la base del entorno
del usuario, una pregunta por ``thread_id``, y se detiene si el costo acumulado supera ``--tope-usd``.
El informe (sin la clave) queda en ``evaluacion/resultados/<fecha>_agente_<modelo>_banco-<banco>.json``.

Uso: ``uv run --no-sync python scripts/evaluar_agente_real.py [--banco v2] [--tope-usd 0.50]``
"""

from __future__ import annotations

import argparse
import os
import sys

from fabrica_autopartes.core.config import Configuracion
from fabrica_autopartes.repositories.auditoria import RepositorioAuditoria
from fabrica_autopartes.services.asistente import ServicioAsistente
from fabrica_autopartes.services.evaluacion import BANCO_POR_DEFECTO, BANCOS
from fabrica_autopartes.services.evaluacion_agente import TOPE_USD_POR_DEFECTO, evaluar_agente

PROVEEDOR_ESPERADO = "anthropic"
MODELO_ESPERADO = "claude-haiku-5-5"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tope-usd", type=float, default=TOPE_USD_POR_DEFECTO)
    parser.add_argument(
        "--banco",
        choices=sorted(BANCOS),
        default=BANCO_POR_DEFECTO,
        help=f"Versión del banco (por defecto {BANCO_POR_DEFECTO}; v1 reproduce A-08)",
    )
    args = parser.parse_args(argv)
    if os.environ.get("FNA_PRUEBAS_AGENTE_REAL") != "1":
        print("Ejecución con modelo real desactivada: definir FNA_PRUEBAS_AGENTE_REAL=1.", file=sys.stderr)
        return 2
    if not 0 < args.tope_usd <= 5:
        print("--tope-usd debe estar entre 0 y 5.", file=sys.stderr)
        return 2
    config = Configuracion()
    # El costo y la tarifa del informe son los de Claude Haiku 5.5 en la API: otro proveedor o modelo se
    # rechaza antes de construir el servicio y sin ninguna llamada.
    if config.proveedor_agente != PROVEEDOR_ESPERADO or config.modelo_anthropic != MODELO_ESPERADO:
        print(
            f"El banco se valida con {PROVEEDOR_ESPERADO} / {MODELO_ESPERADO}; la configuración actual es "
            f"{config.proveedor_agente} / {config.modelo_anthropic}. Ajustar FNA_PROVEEDOR_AGENTE y "
            "FNA_MODELO_ANTHROPIC.",
            file=sys.stderr,
        )
        return 4
    servicio = ServicioAsistente(config, RepositorioAuditoria(config.url_base_datos))
    estado = servicio.verificar_agente(consultar=True)  # models.retrieve: no consume tokens
    if not estado.disponible:
        print(f"Proveedor del agente no disponible: {estado.mensaje}", file=sys.stderr)
        return 3
    # Recuperador de buscar_fragmentos (ADR-031): sin el semántico, la herramienta vuelve a bm25.
    disponible, motivo = servicio.base.disponibilidad_semantica()
    semantico = "disponible" if disponible else f"no disponible ({motivo}): se usará bm25"
    print(f"Recuperador del agente: {config.agente_recuperador} · semántico {semantico}")
    informe = evaluar_agente(servicio, tope_usd=args.tope_usd, banco=args.banco)
    m, c = informe["metricas"], informe["consumo"]
    print(f"Agente {informe['proveedor']} / {informe['modelo']} · banco {informe['banco']}")
    print(f"Preguntas ejecutadas: {m['preguntas_ejecutadas']}/{m['total_preguntas']}", end="")
    print(" (interrumpido por el tope de costo)" if informe["interrumpido_por_tope"] else "")
    for clave in ("exactitud_respondibles", "rechazo_correcto", "tasa_fundamentada", "exactitud_global"):
        print(f"  {clave}: {m[clave]}")
    print(f"  con URL inválidas: {m['con_urls_invalidas']} · errores: {m['errores']}")
    print(f"  latencia media: {m['latencia_media_ms']} ms")
    print(
        f"Consumo: {c['llamadas_modelo']} llamadas · {c['tokens_entrada']} tokens de entrada · "
        f"{c['tokens_salida']} de salida · USD {c['costo_usd']:.4f} · "
        f"tarifa alta: {c['llamadas_tarifa_alta']}"
    )
    if informe["interrumpido_por_error"]:
        print("Banco interrumpido por un error del proveedor (ver el detalle).")
    for d in informe["detalle"]:
        estado_p = "ok " if d["acierto"] else "MAL"
        uso = d["consumo"]
        error = f" · error: {d['error'][:80]}" if d["error"] else ""
        print(
            f"  {estado_p} {d['id']} {d['tipo']:<13} herr={d['llamadas_herramienta']} "
            f"in={uso['tokens_entrada']} out={uso['tokens_salida']} USD {uso['costo_usd']:.5f}{error}"
        )
    print(f"Informe: {informe['archivo']}")
    return 1 if m["errores"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
