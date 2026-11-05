import type { ReactNode } from "react";
import { InsigniaFuente } from "./InsigniaFuente";

/**
 * Chip de un número o estado. Variantes: «neutro», «dato» (azul), «supuesto» (borde punteado + insignia) y
 * «estado» (verde o rojo, con ícono y texto: nunca solo color).
 */
export type VarianteChip = "neutro" | "dato" | "supuesto" | "estado";

export function ChipDato(props: { etiqueta: string; valor: ReactNode; variante?: VarianteChip; ok?: boolean }) {
  const variante = props.variante ?? "neutro";
  const estado = variante === "estado" ? (props.ok === false ? "alerta" : "ok") : null;
  return (
    <span className={`chip chip-${variante}${estado ? ` chip-${estado}` : ""}`} data-variante={variante}>
      {estado && (
        <span className="chip-icono" aria-hidden="true">
          {estado === "ok" ? "✓" : "✕"}
        </span>
      )}
      <span className="chip-etiqueta">{props.etiqueta}</span> <b>{props.valor}</b>
      {variante === "supuesto" && <InsigniaFuente fuente="supuesto" />}
    </span>
  );
}
