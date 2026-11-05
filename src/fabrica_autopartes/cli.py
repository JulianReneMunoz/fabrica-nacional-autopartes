"""Interfaz de línea de comandos: ``uv run fabrica <comando>``.

Comandos:
  scrape     Rastrea el sitio oficial y guarda las capturas en Bronze (requiere red).
  build      Reconstruye Silver y Gold desde Bronze o desde la semilla (sin red).
  validate   Valida la calidad del corpus Gold.
  graficas   Genera las gráficas de cada etapa del proceso de datos.
  pipeline   Proceso completo: scrape → build → validate → graficas.
  ask        Responde una pregunta (Q&A).
  faq        Genera preguntas frecuentes.
  summary    Genera el resumen ejecutivo.
  evaluate   Ejecuta el banco de 24 preguntas y guarda métricas.
  stats      Muestra estadísticas de la base de conocimiento.
  simulador  Genera o valida el ensamblaje 3D de demostración (v2.0).
  openapi    Exporta el contrato OpenAPI de la API.
"""

from __future__ import annotations

import argparse
import json
import sys

from fabrica_autopartes.core.registro import configurar_registro


def _opciones_llm(p: argparse.ArgumentParser) -> None:
    p.add_argument("--proveedor", choices=["ollama", "openai", "anthropic", "claude_code", "extractivo"])
    p.add_argument("--modelo")
    p.add_argument("--version-prompt", choices=["v1", "v2", "v3"])
    p.add_argument("--modo-contexto", choices=["auto", "completo", "seleccion"])


def _op(a: argparse.Namespace) -> dict[str, str | None]:
    return {
        "proveedor": a.proveedor,
        "modelo": a.modelo,
        "version_prompt": a.version_prompt,
        "modo_contexto": getattr(a, "modo_contexto", None),
    }


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fabrica", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--nivel-log", default="INFO")
    sub = parser.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("scrape", help="Rastrear el sitio oficial (Bronze)")
    s.add_argument("--url", action="append", help="URL semilla adicional (repetible)")
    s.add_argument("--sin-sitemap", action="store_true")
    s.add_argument("--max-paginas", type=int)

    b = sub.add_parser("build", help="Construir Silver y Gold")
    b.add_argument("--fuente", choices=["auto", "scraping", "semilla", "ambas", "mixta"], default="auto")

    sub.add_parser("validate", help="Validar calidad del corpus Gold")

    g = sub.add_parser("graficas", help="Generar las gráficas de cada etapa del proceso de datos")
    g.add_argument("--salida", default="docs/graficas")

    pl = sub.add_parser("pipeline", help="Proceso completo: scrape → build → validate → graficas")
    pl.add_argument("--max-paginas", type=int)
    pl.add_argument("--sin-sitemap", action="store_true")
    pl.add_argument(
        "--desde-cero",
        action="store_true",
        help="Eliminar data/bronze antes de rastrear (resumen y gráficas de una sola ejecución completa)",
    )
    pl.add_argument(
        "--sin-complemento",
        action="store_true",
        help="No complementar con lectura web los dominios que no pudieron rastrearse",
    )
    sub.add_parser("stats", help="Estadísticas de la base")

    a = sub.add_parser("ask", help="Pregunta al sistema Q&A")
    a.add_argument("pregunta")
    _opciones_llm(a)

    f = sub.add_parser("faq", help="Generar FAQ")
    f.add_argument("-n", type=int, default=8)
    _opciones_llm(f)

    r = sub.add_parser("summary", help="Generar resumen")
    r.add_argument("--enfoque")
    _opciones_llm(r)

    e = sub.add_parser("evaluate", help="Evaluar con el banco de preguntas")
    _opciones_llm(e)

    sim = sub.add_parser("simulador", help="Simulador 3D v2.0: generar GLB y manifiesto")
    sim.add_argument("accion", choices=["generar", "validar"])
    sim.add_argument("--salida", default="web/public/modelos")
    sim.add_argument(
        "--ensamblaje",
        choices=["freno_disco", "moto_honda"],
        default="freno_disco",
        help="Ensamblaje a generar o validar (por defecto freno_disco)",
    )
    sim.add_argument("--diametro-disco", type=float)
    sim.add_argument("--diametro-piston", type=float)

    o = sub.add_parser("openapi", help="Exportar OpenAPI a JSON")
    o.add_argument("--salida", default="docs/api/openapi.json")
    return parser


def _main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    configurar_registro(args.nivel_log)

    if args.comando == "openapi":
        from pathlib import Path

        from fabrica_autopartes.api.main import crear_app

        ruta = Path(args.salida)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            json.dumps(crear_app().openapi(), ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
        print(f"OpenAPI exportado en {ruta}")
        return 0

    if args.comando == "simulador":
        from pathlib import Path

        from pydantic import ValidationError

        from fabrica_autopartes.simulador.catalogo_freno import ParametrosFreno
        from fabrica_autopartes.simulador.cinematica import validar_ensamblaje
        from fabrica_autopartes.simulador.generacion import construir_ensamblaje, generar

        sobrescritos = {
            k: v
            for k, v in {
                "diametro_disco": args.diametro_disco,
                "diametro_piston": args.diametro_piston,
            }.items()
            if v is not None
        }
        if args.ensamblaje != "freno_disco" and sobrescritos:
            print("Los parámetros --diametro-* solo aplican a freno_disco")
            return 2
        try:
            parametros = ParametrosFreno(**sobrescritos)
        except ValidationError as exc:
            print(f"Parámetros inválidos: {exc}")
            return 2
        parametros_freno = parametros if args.ensamblaje == "freno_disco" else None
        if args.accion == "validar":
            errores = validar_ensamblaje(construir_ensamblaje(args.ensamblaje, parametros_freno))
            print("Ensamblaje íntegro" if not errores else "\n".join(errores))
            return 0 if not errores else 1
        manifiesto = generar(Path(args.salida), parametros_freno, args.ensamblaje)
        print(
            f"GLB: {Path(args.salida) / Path(manifiesto['archivo']).name} ({manifiesto['bytes']} bytes, "
            f"{len(manifiesto['piezas'])} piezas, sha256 {manifiesto['sha256'][:16]}…)"
        )
        return 0

    from fabrica_autopartes.services.asistente import ServicioAsistente

    servicio = ServicioAsistente()

    if args.comando == "scrape":
        if args.max_paginas:
            servicio.config.max_paginas = args.max_paginas
        rastreo = servicio.rastrear(args.url, usar_sitemap=not args.sin_sitemap)
        print(
            f"Capturadas: {len(rastreo.capturadas)} | Omitidas por robots: {len(rastreo.omitidas_robots)} | "
            f"Errores: {len(rastreo.errores)} | Duplicadas: {rastreo.duplicadas}"
        )
        return 0 if rastreo.capturadas else 2

    if args.comando == "graficas":
        from pathlib import Path

        from fabrica_autopartes.pipelines.graficas import generar_graficas

        rutas = generar_graficas(servicio.config.dir_gold / "metricas_etapas.json", Path(args.salida))
        for ruta_grafica in rutas:
            print(f"Gráfica: {ruta_grafica}")
        return 0

    if args.comando == "pipeline":
        from pathlib import Path

        from fabrica_autopartes.pipelines.calidad import validar_fragmentos
        from fabrica_autopartes.pipelines.graficas import generar_graficas

        if args.max_paginas:
            servicio.config.max_paginas = args.max_paginas
        if args.desde_cero and servicio.config.dir_bronze.exists():
            import shutil

            shutil.rmtree(servicio.config.dir_bronze)
            print(f"      {servicio.config.dir_bronze} eliminado: rastreo completo desde cero")
        print("[1/4] Rastreo responsable de los sitios oficiales (Bronze)")
        rastreo = servicio.rastrear(None, usar_sitemap=not args.sin_sitemap)
        print(
            f"      capturadas={len(rastreo.capturadas)} omitidas_robots={len(rastreo.omitidas_robots)} "
            f"errores={len(rastreo.errores)} duplicadas={rastreo.duplicadas} "
            f"omitidas_proteccion={len(rastreo.omitidas_proteccion)}"
        )
        for host, proteccion in rastreo.hosts_protegidos.items():
            print(f"      {host}: protección antibots ({proteccion}); no se elude")
        from fabrica_autopartes.pipelines.bronze import AlmacenBronze

        if AlmacenBronze(servicio.config.dir_bronze).vacio():
            print("No se capturó ninguna página: revisar red, robots.txt y data/bronze/errores.jsonl")
            return 2
        if not rastreo.capturadas:
            print("      sin páginas nuevas: se reutilizan las capturas existentes en Bronze")
        fuente = "scraping" if args.sin_complemento else "mixta"
        print(f"[2/4] Construcción Silver y Gold desde Bronze (fuente: {fuente})")
        construccion = servicio.construir(fuente)
        for advertencia in construccion.advertencias:
            print(f"      {advertencia}")
        print(
            f"      documentos={construccion.documentos_silver} "
            f"fragmentos={construccion.estadisticas.fragmentos} "
            f"tokens≈{construccion.estadisticas.tokens_aprox}"
        )
        print("[3/4] Validación de calidad")
        calidad = validar_fragmentos(servicio.base.fragmentos)
        print(
            f"      aprobado={calidad.aprobado} errores={calidad.errores} advertencias={calidad.advertencias}"
        )
        print("[4/4] Gráficas de cada etapa → docs/graficas/")
        destino = Path("docs/graficas")
        for ruta_grafica in generar_graficas(servicio.config.dir_gold / "metricas_etapas.json", destino):
            print(f"      {ruta_grafica}")
        return 0 if calidad.aprobado else 1

    if args.comando == "build":
        construccion = servicio.construir(args.fuente)
        for adv in construccion.advertencias:
            print(f"ADVERTENCIA: {adv}")
        print(json.dumps(construccion.estadisticas.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.comando == "validate":
        from fabrica_autopartes.pipelines.calidad import validar_fragmentos

        calidad = validar_fragmentos(servicio.base.fragmentos)
        print(json.dumps(calidad.a_dict(), ensure_ascii=False, indent=2))
        return 0 if calidad.aprobado else 1

    if args.comando == "stats":
        print(json.dumps(servicio.base.estadisticas().model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.comando == "ask":
        r = servicio.responder(args.pregunta, canal="cli", **_op(args))
        print(r.respuesta)
        for f in r.fuentes:
            print(f"  - [{f.fragmento_id}] {f.url}")
        print(
            f"(fundamentada={r.fundamentada}, confianza={r.confianza}, modo={r.modo_contexto}, "
            f"{r.latencia_ms} ms)"
        )
        return 0

    if args.comando == "faq":
        faq = servicio.generar_faq(args.n, canal="cli", **_op(args))
        for i, it in enumerate(faq.items, 1):
            print(f"{i}. {it.pregunta}\n   {it.respuesta} {it.fuentes}")
        for adv in faq.advertencias:
            print(f"ADVERTENCIA: {adv}")
        return 0

    if args.comando == "summary":
        print(servicio.resumir(args.enfoque, canal="cli", **_op(args)).resumen)
        return 0

    if args.comando == "evaluate":
        from fabrica_autopartes.services.evaluacion import evaluar

        informe = evaluar(servicio, _op(args))
        print(json.dumps(informe["metricas"], ensure_ascii=False, indent=2))
        print(f"Informe: {informe.get('archivo')}")
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada: los errores del dominio se muestran como un mensaje claro, sin traza."""
    from fabrica_autopartes.core.excepciones import ErrorFNA

    try:
        return _main(argv)
    except ErrorFNA as exc:
        print(f"Error ({exc.codigo}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
