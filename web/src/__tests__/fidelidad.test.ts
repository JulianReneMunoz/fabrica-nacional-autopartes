import { describe, expect, it } from "vitest";
import { colocarEtiquetas, hayCajasSolapadas, puntoBorde, rectDe } from "../modelos/etiquetas";
import { mecanismoMotor } from "../modelos/mecanismo";
import { GEOMETRIA_MOTOR } from "../modelos/moto";
import { GEOMETRIA_MOVIL_DEFECTO, geometriaMovil } from "../paginas/EscenaMoto";

describe("mecanismo sobre el eje inclinado del cilindro (15°)", () => {
  const u = GEOMETRIA_MOVIL_DEFECTO.ejeCilindro;
  const c = GEOMETRIA_MOVIL_DEFECTO.centroCiguenal;
  const carrera = GEOMETRIA_MOTOR.carreraM;
  const biela = GEOMETRIA_MOTOR.bielaM;
  const distanciaAlEje = (p: { x: number; y: number }) => Math.abs((p.x - c[0]) * u[1] - (p.y - c[1]) * u[0]); // producto vectorial con u

  it("el eje es unitario e inclinado 15° respecto a la vertical", () => {
    expect(Math.hypot(u[0], u[1])).toBeCloseTo(1, 12);
    expect((Math.atan2(u[0], u[1]) * 180) / Math.PI).toBeCloseTo(15, 9);
  });
  it("el bulón del pistón queda sobre el eje del cilindro: distancia al eje ≈ 0 para varios θ", () => {
    for (let g = 0; g <= 720; g += 30) {
      const m = mecanismoMotor((g * Math.PI) / 180, u, c, carrera, biela);
      expect(distanciaAlEje(m.bulon)).toBeLessThan(1e-12);
    }
  });
  it("el pistón recorre exactamente la carrera 2r a lo largo del eje y nunca sube del PMS", () => {
    const d = Array.from({ length: 73 }, (_, i) => mecanismoMotor((i * 10 * Math.PI) / 180, u, c, carrera, biela).desplazamiento);
    expect(Math.max(...d)).toBeCloseTo(0, 12);
    expect(Math.min(...d)).toBeCloseTo(-carrera, 9);
  });
  it("la biela mantiene su longitud entre muñequilla y bulón y φ cumple L·sin φ = r·sin θ", () => {
    for (let g = 0; g < 360; g += 25) {
      const t = (g * Math.PI) / 180;
      const m = mecanismoMotor(t, u, c, carrera, biela);
      expect(Math.hypot(m.bulon.x - m.muneca.x, m.bulon.y - m.muneca.y)).toBeCloseTo(biela, 9);
      expect(biela * Math.sin(m.phi)).toBeCloseTo((carrera / 2) * Math.sin(t), 12);
    }
  });
  it("θ = 0 es el PMS: muñequilla y bulón alineados con el eje (biela en su pose base)", () => {
    const m = mecanismoMotor(0, u, c, carrera, biela);
    expect(distanciaAlEje(m.muneca)).toBeLessThan(1e-12);
    expect(m.phi).toBe(0);
  });
});

describe("geometriaMovil: ejes y orígenes desde las articulaciones", () => {
  it("lee el eje del pistón, el centro del cigüeñal, la horquilla y la cadena de la API", () => {
    const arts = [
      { id: "j_piston", tipo: "prismatica", padre: null, hijo: "piston", eje: [0.5, 0.8660254, 0], origen: [0, 0, 0], maestra: null, relacion: null },
      { id: "j_ciguenal", tipo: "rotacional", padre: null, hijo: "ciguenal", eje: [0, 0, 1], origen: [0.2, 0.4, 0], maestra: null, relacion: null },
      { id: "j_botella_izquierda", tipo: "prismatica", padre: null, hijo: "botella_izquierda", eje: [-0.4, 0.9165, 0], origen: [0, 0, 0], maestra: null, relacion: null },
    ];
    const g = geometriaMovil(arts, { cadena_pinon_x_m: -0.1, cadena_corona_y_m: 0.31, cadena_z_m: 0.08 });
    expect((Math.atan2(g.ejeCilindro[0], g.ejeCilindro[1]) * 180) / Math.PI).toBeCloseTo(30, 6);
    expect(g.centroCiguenal).toEqual([0.2, 0.4]);
    expect(Math.hypot(...g.ejeHorquilla)).toBeCloseTo(1, 9);
    expect(g.cadena.pinon[0]).toBe(-0.1);
    expect(g.cadena.corona[1]).toBe(0.31);
    expect(g.cadena.z).toBe(0.08);
  });
  it("sin datos de la API usa los valores por omisión (cilindro a 15°, horquilla a 26°)", () => {
    const g = geometriaMovil(null, null);
    expect((Math.atan2(g.ejeCilindro[0], g.ejeCilindro[1]) * 180) / Math.PI).toBeCloseTo(15, 9);
    expect((Math.atan2(-g.ejeHorquilla[0], g.ejeHorquilla[1]) * 180) / Math.PI).toBeCloseTo(26, 9);
  });
});

describe("colocarEtiquetas: sin solapes, dentro del escenario y con línea guía", () => {
  const base = (clave: string, px: number, py: number, pref: [number, number], w = 150, h = 34) => ({ clave, px, py, pref, w, h });
  const reservadas = [
    { x: 12, y: 12, w: 330, h: 44 },
    { x: 560, y: 12, w: 300, h: 90 },
  ];

  it.each([
    [1440, 900, 685, 520],
    [1280, 800, 640, 464],
  ])("con anclajes agrupados (ventana %i×%i, escenario %i×%i) ninguna caja se solapa ni sale", (_a, _b, W, H) => {
    const entradas = [
      base("motor", 330, 230, [-110, -105], 170, 36),
      base("cilindrada", 345, 225, [120, -100], 210, 36),
      base("transmision", 220, 330, [-20, 95], 190, 36),
      base("rueda", 150, 345, [-95, 55], 200, 36),
      base("disco_del", 520, 330, [95, -85], 190, 36),
      base("disco_tras", 160, 340, [-125, -95], 200, 52),
    ];
    const cajas = colocarEtiquetas(entradas, W, H, reservadas, 40);
    const rects = cajas.map(rectDe);
    expect(hayCajasSolapadas(rects)).toBe(false);
    for (const r of rects) {
      expect(r.x).toBeGreaterThanOrEqual(0);
      expect(r.y).toBeGreaterThanOrEqual(0);
      expect(r.x + r.w).toBeLessThanOrEqual(W);
      expect(r.y + r.h).toBeLessThanOrEqual(H - 40);
      for (const o of reservadas) expect(r.x < o.x + o.w && r.x + r.w > o.x && r.y < o.y + o.h && r.y + r.h > o.y).toBe(false);
    }
  });
  it("sin conflictos respeta la posición preferida y la línea guía parte del borde más cercano", () => {
    const [c] = colocarEtiquetas([base("a", 300, 300, [80, -60])], 800, 600);
    expect(c.cx).toBeCloseTo(380, 6);
    expect(c.cy).toBeCloseTo(240, 6);
    const [bx, by] = puntoBorde(c);
    const r = rectDe(c);
    expect(bx).toBeGreaterThanOrEqual(r.x);
    expect(bx).toBeLessThanOrEqual(r.x + r.w);
    expect(by).toBeCloseTo(r.y + r.h, 6); // el anclaje queda debajo de la caja
  });
  it("una etiqueta cuya posición preferida cae sobre una zona reservada se desplaza fuera de ella y dentro del escenario", () => {
    const zona = { x: 380, y: 12, w: 300, h: 90 }; // cuadro «cámara lenta» arriba a la derecha
    const [c] = colocarEtiquetas([base("cilindrada", 500, 150, [120, -100], 240, 36)], 685, 520, [zona], 40);
    const r = rectDe(c);
    expect(r.x < zona.x + zona.w && r.x + r.w > zona.x && r.y < zona.y + zona.h && r.y + r.h > zona.y).toBe(false);
    expect(r.x).toBeGreaterThanOrEqual(0);
    expect(r.x + r.w).toBeLessThanOrEqual(685);
    expect(r.y).toBeGreaterThanOrEqual(0);
  });
  it("es determinista", () => {
    const e = [base("a", 100, 100, [0, 0]), base("b", 110, 105, [0, 0]), base("c", 120, 110, [0, 0])];
    expect(colocarEtiquetas(e, 700, 500)).toEqual(colocarEtiquetas(e, 700, 500));
  });
});
