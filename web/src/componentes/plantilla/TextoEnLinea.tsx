import { Fragment, type ReactNode } from "react";

/**
 * Markdown en línea mínimo y seguro: **negrita** y *cursiva* se convierten en elementos React (sin HTML crudo)
 * y los asteriscos o acentos graves sobrantes se eliminan.
 */
export function TextoEnLinea({ texto }: { texto: string }) {
  const partes: ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*|\*([^*\s][^*]*)\*/g;
  let ultimo = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  const limpio = (s: string) => s.replace(/[*`]/g, "");
  while ((m = re.exec(texto))) {
    if (m.index > ultimo) partes.push(limpio(texto.slice(ultimo, m.index)));
    partes.push(m[1] !== undefined ? <strong key={i++}>{limpio(m[1])}</strong> : <em key={i++}>{limpio(m[2])}</em>);
    ultimo = m.index + m[0].length;
  }
  if (ultimo < texto.length) partes.push(limpio(texto.slice(ultimo)));
  return (
    <>
      {partes.map((p, k) => (
        <Fragment key={k}>{p}</Fragment>
      ))}
    </>
  );
}
