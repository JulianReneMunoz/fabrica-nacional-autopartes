/**
 * Colocación de etiquetas 3D proyectadas (puro, sin React ni three): cada etiqueta parte de un punto de anclaje
 * en pantalla (sobre su pieza), se desplaza a una posición preferida, se mantiene dentro del escenario, no se
 * solapa con otras etiquetas ni con zonas reservadas (barra de herramientas, leyenda, banda del recorrido) y
 * queda unida a su pieza por una línea guía hasta el borde más cercano de la caja.
 */
export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface CajaEtiqueta {
  clave: string;
  /** Punto de anclaje en la pieza (px, relativo al escenario). */
  px: number;
  py: number;
  /** Desplazamiento preferido del centro de la caja respecto al anclaje (px). */
  pref: [number, number];
  w: number;
  h: number;
  /** Centro resultante (px). */
  cx: number;
  cy: number;
}

const MARGEN = 6;
const BORDE = 4;

const solapa = (a: Rect, b: Rect, margen = MARGEN) =>
  a.x < b.x + b.w + margen && a.x + a.w + margen > b.x && a.y < b.y + b.h + margen && a.y + a.h + margen > b.y;

export const rectDe = (c: CajaEtiqueta): Rect => ({ x: c.cx - c.w / 2, y: c.cy - c.h / 2, w: c.w, h: c.h });

/** Coloca las cajas; devuelve las mismas con `cx`/`cy` definitivos. Determinista y sin estado entre fotogramas. */
export function colocarEtiquetas(
  entradas: Omit<CajaEtiqueta, "cx" | "cy">[],
  ancho: number,
  alto: number,
  reservadas: Rect[] = [],
  margenInferior = 0,
): CajaEtiqueta[] {
  const cajas: CajaEtiqueta[] = entradas.map((e) => ({ ...e, cx: e.px + e.pref[0], cy: e.py + e.pref[1] }));
  const limitar = (c: CajaEtiqueta) => {
    c.cx = Math.min(Math.max(c.cx, c.w / 2 + BORDE), Math.max(ancho - c.w / 2 - BORDE, c.w / 2 + BORDE));
    c.cy = Math.min(Math.max(c.cy, c.h / 2 + BORDE), Math.max(alto - margenInferior - c.h / 2 - BORDE, c.h / 2 + BORDE));
  };
  cajas.forEach(limitar);
  for (let iter = 0; iter < 24; iter++) {
    let movido = false;
    for (const c of cajas) {
      for (const o of reservadas) {
        const r = rectDe(c);
        if (!solapa(r, o)) continue;
        // Candidatos: a la izquierda, derecha, arriba o abajo de la zona reservada; se elige el más cercano que cabe.
        const candidatos: [number, number][] = [
          [o.x - MARGEN - c.w / 2, c.cy],
          [o.x + o.w + MARGEN + c.w / 2, c.cy],
          [c.cx, o.y - MARGEN - c.h / 2],
          [c.cx, o.y + o.h + MARGEN + c.h / 2],
        ];
        const cabe = ([x, y]: [number, number]) =>
          x - c.w / 2 >= BORDE - 1e-9 && x + c.w / 2 <= ancho - BORDE + 1e-9 && y - c.h / 2 >= BORDE - 1e-9 && y + c.h / 2 <= alto - margenInferior - BORDE + 1e-9;
        const ordenados = candidatos.sort((p, q) => Math.hypot(p[0] - c.cx, p[1] - c.cy) - Math.hypot(q[0] - c.cx, q[1] - c.cy));
        const [nx, ny] = ordenados.find(cabe) ?? ordenados[0];
        c.cx = nx;
        c.cy = ny;
        limitar(c);
        movido = true;
      }
    }
    for (let i = 0; i < cajas.length; i++) {
      for (let j = i + 1; j < cajas.length; j++) {
        const a = cajas[i];
        const b = cajas[j];
        if (!solapa(rectDe(a), rectDe(b))) continue;
        const ox = (a.w + b.w) / 2 + MARGEN - Math.abs(a.cx - b.cx);
        const oy = (a.h + b.h) / 2 + MARGEN - Math.abs(a.cy - b.cy);
        if (oy <= ox) {
          const s = a.cy <= b.cy ? 1 : -1;
          a.cy -= (s * oy) / 2;
          b.cy += (s * oy) / 2;
        } else {
          const s = a.cx <= b.cx ? 1 : -1;
          a.cx -= (s * ox) / 2;
          b.cx += (s * ox) / 2;
        }
        limitar(a);
        limitar(b);
        movido = true;
      }
    }
    if (!movido) break;
  }
  return cajas;
}

/** Punto del borde de la caja más cercano al anclaje (extremo de la línea guía junto a la etiqueta). */
export function puntoBorde(c: CajaEtiqueta): [number, number] {
  const r = rectDe(c);
  return [Math.min(Math.max(c.px, r.x), r.x + r.w), Math.min(Math.max(c.py, r.y), r.y + r.h)];
}

/** `true` si alguna pareja de cajas se solapa (sin margen). */
export function hayCajasSolapadas(rects: Rect[]): boolean {
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) if (solapa(rects[i], rects[j], 0)) return true;
  return false;
}
