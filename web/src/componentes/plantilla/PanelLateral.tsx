/** Panel lateral con pestañas estándar (WAI-ARIA tabs, con flechas de teclado). */
import { useId, useState, type KeyboardEvent, type ReactNode } from "react";
import type { IdPestana } from "../../maquinas/tipos";

export const TITULO_PESTANA: Record<IdPestana, string> = {
  componentes: "Componentes",
  empresa: "Datos de la empresa",
  ficha: "Ficha técnica",
  faq: "FAQ",
};

export interface PestanaPanel {
  id: IdPestana;
  contenido: ReactNode;
}

export function PanelLateral({ pestanas, inicial }: { pestanas: PestanaPanel[]; inicial?: IdPestana }) {
  const base = useId();
  const [activa, setActiva] = useState<IdPestana>(inicial ?? pestanas[0].id);
  const actual = pestanas.find((p) => p.id === activa) ?? pestanas[0];
  const mover = (e: KeyboardEvent, i: number) => {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!d) return;
    e.preventDefault();
    const n = pestanas[(i + d + pestanas.length) % pestanas.length].id;
    setActiva(n);
    document.getElementById(`${base}-${n}`)?.focus();
  };
  return (
    <section className="pestanas" aria-label="Panel lateral">
      <div role="tablist" className="pestanas-lista" aria-label="Secciones del panel lateral">
        {pestanas.map((p, i) => (
          <button
            key={p.id}
            role="tab"
            id={`${base}-${p.id}`}
            aria-selected={actual.id === p.id}
            aria-controls={`${base}-panel`}
            tabIndex={actual.id === p.id ? 0 : -1}
            className={actual.id === p.id ? "activa" : ""}
            onClick={() => setActiva(p.id)}
            onKeyDown={(e) => mover(e, i)}
          >
            {TITULO_PESTANA[p.id]}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-${actual.id}`} className="pestanas-panel">
        {actual.contenido}
      </div>
    </section>
  );
}
