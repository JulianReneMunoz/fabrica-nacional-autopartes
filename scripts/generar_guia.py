"""Genera la guía cronológica de agentes y la guía de instalación (Markdown) desde los YAML fuente."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "docs" / "manuales" / "fases_agentes.yaml"
HERRAMIENTAS = RAIZ / "docs" / "manuales" / "herramientas_windows.yaml"


def markdown(fases: list[dict]) -> str:
    md = [
        "# Guía operativa de desarrollo con agentes (OpenCode y Claude Code)",
        "",
        "Generada desde `fases_agentes.yaml`. No avanzar de fase sin cumplir la condición indicada.",
        "",
    ]
    for f in fases:
        md += [
            f"## {f['id']} · {f['etapa']}",
            "",
            f"1. **Herramienta:** {f['herramienta']}",
            f"2. **Terminal:** {f['terminal']}",
            "3. **Comandos:**",
            "",
            "```powershell",
            *f["comandos"],
            "```",
            "",
            f"4. **Explicación:** {f['explicacion']}",
            f"5. **Agente y prompt:** {f['agente']}",
            "",
        ]
        if f.get("prompt"):
            md += ["```text", f["prompt"].strip(), "```", ""]
        md += [
            f"6. **Archivos:** {', '.join(f['archivos']) or '—'}",
            f"7. **Pruebas:** {'; '.join(f['pruebas'])}",
            f"8. **Resultado esperado:** {f['resultado']}",
            "9. **Errores frecuentes:** "
            + ("; ".join(f"{e['error']} → {e['correccion']}" for e in f["errores"]) or "—"),
            f"10. **Condición para continuar:** {f['condicion']}",
            "",
        ]
    return "\n".join(md) + "\n"


def herramientas_md(items: list[dict]) -> str:
    md = [
        "# Instalación desde cero en Windows 11",
        "",
        "Generada desde `herramientas_windows.yaml`. Terminal: PowerShell, salvo indicación.",
        "",
    ]
    for i, h in enumerate(items, 1):
        md += [
            f"## {i}. {h['nombre']}",
            "",
            f"- **Función:** {h['funcion']}",
            f"- **Página oficial:** {h['url']}",
            f"- **Versión recomendada:** {h['version']}",
            f"- **Requisitos previos:** {h['requisitos']}",
            f"- **Instalación gráfica:** {h['grafica']}",
            "- **Instalación por PowerShell:**",
            "",
            "```powershell",
            *h["comandos"],
            "```",
            "",
            f"- **Configuración inicial:** {h['configuracion']}",
            f"- **Variables de entorno:** {h['variables']}",
            "- **Verificación:** " + "; ".join(f"`{v}`" for v in h["verificacion"]),
            f"- **Errores frecuentes:** {h['errores']}",
            f"- **Actualización:** `{h['actualizacion']}`",
            f"- **Seguridad:** {h['seguridad']}",
            "",
        ]
    return "\n".join(md) + "\n"


def main() -> None:
    items = yaml.safe_load(HERRAMIENTAS.read_text(encoding="utf-8"))["herramientas"]
    (RAIZ / "docs" / "manuales" / "instalacion_windows.md").write_text(
        herramientas_md(items), encoding="utf-8"
    )
    fases = yaml.safe_load(FUENTE.read_text(encoding="utf-8"))["fases"]
    (RAIZ / "docs" / "manuales" / "guia_operativa_agentes.md").write_text(markdown(fases), encoding="utf-8")
    print(f"{len(fases)} fases → guia_operativa_agentes.md e instalacion_windows.md")


if __name__ == "__main__":
    main()
