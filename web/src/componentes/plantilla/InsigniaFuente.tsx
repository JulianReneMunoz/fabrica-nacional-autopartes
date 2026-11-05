/**
 * Insignia de procedencia: siempre en UNA línea (`white-space: nowrap`) y con color + texto, para que la
 * procedencia nunca dependa solo del color. Texto visible en mayúsculas por CSS; el DOM conserva minúsculas.
 */
export type Fuente = "scraping" | "lectura_web" | "semilla" | "base_conocimiento" | "ficha" | "supuesto" | "no_publicado";

export const TEXTO_FUENTE: Record<Fuente, string> = {
  scraping: "scraping",
  lectura_web: "lectura web",
  semilla: "semilla",
  base_conocimiento: "base de conocimiento",
  ficha: "ficha",
  supuesto: "supuesto didáctico",
  no_publicado: "no publicado",
};

const ALIAS: Record<string, Fuente> = { demostrativo: "supuesto", publicado: "ficha" };

export function normalizarFuente(tipo: string): Fuente | null {
  const t = ALIAS[tipo] ?? tipo;
  return t in TEXTO_FUENTE ? (t as Fuente) : null;
}

export function InsigniaFuente({ fuente, texto }: { fuente: string; texto?: string }) {
  const f = normalizarFuente(fuente);
  return <span className={`insignia fuente-${f ?? "otra"}`}>{texto ?? (f ? TEXTO_FUENTE[f] : fuente)}</span>;
}
