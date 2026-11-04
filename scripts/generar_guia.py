"""Genera la guía cronológica de agentes (Markdown y LaTeX) desde ``fases_agentes.yaml``."""

from __future__ import annotations

from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "docs" / "manuales" / "fases_agentes.yaml"
HERRAMIENTAS = RAIZ / "docs" / "manuales" / "herramientas_windows.yaml"

_TEX = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("_", r"\_"),
    ("#", r"\#"),
    ("$", r"\$"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\^{}"),
    ("≥", r"$\geq$"),
    ("→", r"$\rightarrow$"),
    ("<", r"\textless{}"),
    (">", r"\textgreater{}"),
    ('"', "''"),
]


def tex(texto: str) -> str:
    salida = ""
    for c in str(texto):
        for a, b in _TEX:
            if c == a:
                salida += b
                break
        else:
            salida += c
    return salida


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


def latex(fases: list[dict]) -> str:
    partes = []
    for f in fases:
        partes.append(f"\\subsection{{{tex(f['id'])} · {tex(f['etapa'])}}}\\label{{fase:{f['id']}}}")
        partes.append("\\begin{description}[leftmargin=3.2cm,style=nextline]")
        partes.append(f"\\item[1. Herramienta] {tex(f['herramienta'])}")
        partes.append(f"\\item[2. Terminal] {tex(f['terminal'])}")
        partes.append("\\item[3. Comandos] \\leavevmode")
        partes.append("\\begin{lstlisting}[style=ps]\n" + "\n".join(f["comandos"]) + "\n\\end{lstlisting}")
        partes.append(f"\\item[4. Explicación] {tex(f['explicacion'])}")
        partes.append(f"\\item[5. Agente] {tex(f['agente'])}. Contexto: {tex(f['contexto'])}")
        if f.get("prompt"):
            partes.append("\\begin{promptbox}" + tex(f["prompt"].strip()) + "\\end{promptbox}")
        partes.append(f"\\item[6. Archivos] {tex(', '.join(f['archivos']) or '—')}")
        partes.append(f"\\item[7. Pruebas] {tex('; '.join(f['pruebas']))}")
        partes.append(f"\\item[8. Resultado] {tex(f['resultado'])}")
        errores = "; ".join(f"{tex(e['error'])} $\\rightarrow$ {tex(e['correccion'])}" for e in f["errores"])
        partes.append(f"\\item[9. Errores] {errores if errores else '—'}")
        partes.append(f"\\item[10. Condición] \\textbf{{{tex(f['condicion'])}}}")
        partes.append("\\end{description}\n")
    return "\n".join(partes)


def _urls(texto: str) -> str:
    return " · ".join(f"\\url{{{u.strip()}}}" for u in texto.split("·"))


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


def herramientas_tex(items: list[dict]) -> str:
    partes = []
    for h in items:
        filas = [
            ("Función", tex(h["funcion"])),
            ("Página oficial", _urls(h["url"])),
            ("Versión", tex(h["version"])),
            ("Requisitos", tex(h["requisitos"])),
            ("Instalación gráfica", tex(h["grafica"])),
            ("Configuración", tex(h["configuracion"])),
            ("Variables", tex(h["variables"])),
            ("Verificación", ", ".join(f"\\texttt{{{tex(v)}}}" for v in h["verificacion"])),
            ("Errores frecuentes", tex(h["errores"])),
            ("Actualización", f"\\texttt{{{tex(h['actualizacion'])}}}"),
            ("Seguridad", tex(h["seguridad"])),
        ]
        partes.append(f"\\section{{{tex(h['nombre'])}}}")
        partes.append("{\\small\\begin{tabularx}{\\linewidth}{@{}>{\\bfseries}p{2.9cm}X@{}}\\toprule")
        partes += [f"{a} & {b}\\\\" for a, b in filas]
        partes.append("\\bottomrule\\end{tabularx}}")
        partes.append("\\begin{lstlisting}[style=ps]\n" + "\n".join(h["comandos"]) + "\n\\end{lstlisting}\n")
    return "\n".join(partes)


def main() -> None:
    items = yaml.safe_load(HERRAMIENTAS.read_text(encoding="utf-8"))["herramientas"]
    (RAIZ / "docs" / "manuales" / "instalacion_windows.md").write_text(
        herramientas_md(items), encoding="utf-8"
    )
    (RAIZ / "docs" / "latex" / "generado" / "herramientas.tex").write_text(
        herramientas_tex(items), encoding="utf-8"
    )
    fases = yaml.safe_load(FUENTE.read_text(encoding="utf-8"))["fases"]
    (RAIZ / "docs" / "manuales" / "guia_operativa_agentes.md").write_text(markdown(fases), encoding="utf-8")
    destino = RAIZ / "docs" / "latex" / "generado" / "guia_fases.tex"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(latex(fases), encoding="utf-8")
    print(f"{len(fases)} fases → guia_operativa_agentes.md y {destino.name}")


if __name__ == "__main__":
    main()
