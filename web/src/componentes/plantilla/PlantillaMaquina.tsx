/**
 * Plantilla común de todas las máquinas (mismo orden en freno, prensa, línea y moto):
 *  1. migas y título con la pregunta   2. franja de la fórmula   3. lienzo (8/12) con barra estándar
 *  4. columna lateral (4/12): «Controles» siempre visible + pestañas estándar   5. chips de números
 *  6. idea principal (una frase)       7. «Mecanismo paso a paso» y «Modo experimento»   8. nota al pie
 * Por debajo de 1100 px la columna lateral pasa debajo del lienzo; por debajo de 700 px es un cajón.
 */
import { useState, type ReactNode } from "react";
import type { Maquina } from "../../api";
import type { DefinicionMaquina, IdPestana } from "../../maquinas/tipos";
import { BandaTour } from "../anatomia";
import { BarraLienzo, type PropsBarraLienzo } from "./BarraLienzo";
import { Reproduccion, type PropsReproduccion } from "./controles";
import { ModoExperimento, type Experimento } from "./ModoExperimento";
import { PanelEmpresa } from "./PanelEmpresa";
import { FaqFanalcaAuto } from "./PanelFaq";
import { PanelLateral, type PestanaPanel } from "./PanelLateral";
import { PasoAPaso } from "./PasoAPaso";

export const NOTA_PIE = "Cifras demostrativas; los datos de la empresa provienen de fuentes oficiales citadas por URL.";

const CHECKLIST = [
  "Responde una sola pregunta con una relación medible",
  "Entre 2 y 4 controles; correr, pausar, reiniciar y cámara lenta",
  "Cifras junto a las piezas que las producen",
  "Idea principal en una frase",
  "Datos de empresa con URL; parámetros demostrativos marcados",
  "Sin procedimientos de reparación ni de seguridad",
];

export interface PropsPlantilla {
  def: DefinicionMaquina;
  maquina: Maquina | null;
  errorApi: string | null;
  barra: PropsBarraLienzo;
  /** Contenido del lienzo (Canvas 3D o SVG 2D). */
  lienzo: ReactNode;
  /** Capas sobre el lienzo (etiquetas de cifras, cuadro de cámara lenta). */
  capas?: ReactNode;
  leyenda: string;
  banda: { texto: string | null; transcurrido: number; duracion: number; bloqueadoPorMovimiento?: boolean };
  escenarioProps?: Record<string, string | number | undefined>;
  alturaLienzo?: string;
  /** Deslizadores y mandos propios (bajo el título «Controles»). */
  controles: ReactNode;
  reproduccion?: PropsReproduccion;
  controlesExtra?: ReactNode;
  contenidoPestanas: Partial<Record<IdPestana, ReactNode>>;
  pestanaInicial?: IdPestana;
  chips: ReactNode;
  /** Bloque opcional bajo los chips (lecturas detalladas en vivo). */
  detalle?: ReactNode;
  pasoActual: number;
  experimentos: Experimento[];
  /** Atributos de la raíz (p. ej. data-testid). */
  raizProps?: Record<string, string | number | undefined>;
  avisos?: ReactNode;
}

export function PlantillaMaquina(p: PropsPlantilla) {
  const [cajon, setCajon] = useState(false);
  const { def } = p;
  const pestanas: PestanaPanel[] = def.pestanas.map((id) => ({
    id,
    contenido:
      p.contenidoPestanas[id] ??
      (id === "empresa" ? <PanelEmpresa maquina={p.maquina} error={p.errorApi} /> : id === "faq" ? <FaqFanalcaAuto /> : null),
  }));
  return (
    <div className="plantilla" data-maquina-id={def.id} {...p.raizProps}>
      <nav className="migas" aria-label="Migas">
        <a href="#/">← Biblioteca</a>
      </nav>
      <h1 className="titular">{def.pregunta}</h1>
      <div className="franja-formula">
        <span className="relacion" data-testid="formula">{def.formula}</span>
        <span className="contexto">{def.contexto}</span>
      </div>
      {p.avisos}

      <div className="rejilla-maquina">
        <section className="lienzo-col" aria-label="Lienzo">
          <BarraLienzo {...p.barra} />
          <div className="escenario" style={p.alturaLienzo ? { height: p.alturaLienzo } : undefined} {...p.escenarioProps}>
            {p.lienzo}
            {p.capas}
            <span className="leyenda-escena">{p.leyenda}</span>
            <BandaTour {...p.banda} />
          </div>
          <button className="boton boton-cajon" aria-expanded={cajon} onClick={() => setCajon(!cajon)}>
            ☰ Controles y datos
          </button>
        </section>
        <aside className={`lateral-col${cajon ? " cajon-abierto" : ""}`} aria-label="Controles y datos">
          <button className="boton secundario cerrar-cajon" onClick={() => setCajon(false)}>✕ Cerrar</button>
          <section className="panel" aria-label="Controles">
            <h3>Controles</h3>
            {p.controles}
            {p.reproduccion && <Reproduccion {...p.reproduccion} />}
            {p.controlesExtra}
          </section>
          <PanelLateral pestanas={pestanas} inicial={p.pestanaInicial} />
        </aside>
      </div>
      {cajon && <button className="velo-cajon" aria-label="Cerrar cajón" onClick={() => setCajon(false)} />}

      <div className="lecturas" aria-label="Lecturas">{p.chips}</div>
      {p.detalle}
      <p className="idea" data-testid="idea-principal">
        <span className="rotulo-idea">Idea principal</span> {def.idea}
      </p>
      <div className="dos-tarjetas">
        <PasoAPaso pasos={def.pasos} actual={p.pasoActual} />
        <ModoExperimento experimentos={p.experimentos} />
      </div>
      <details className="panel revision">
        <summary>Revisión crítica</summary>
        <ul className="critica">
          {[...CHECKLIST, ...def.revisionExtra].map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </details>
      <p className="pie-nota">{NOTA_PIE}</p>
    </div>
  );
}
