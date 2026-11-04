import { describe, expect, it } from "vitest";
import referencia from "./referencia_freno.json";
import { calcularFreno, ENTRADA_FRENO_DEFECTO, estadoRueda, type EntradaFreno } from "../modelos/freno";
import { carrera, ENTRADA_PRENSA_DEFECTO, fuerzaCorte, ventanaCorte } from "../modelos/prensa";
import { calcularLinea, colaAcumulada, ENTRADA_LINEA_DEFECTO } from "../modelos/linea";

describe("freno: réplica TypeScript de fisica_freno.calcular (Python)", () => {
  it.each(referencia.casos.map((c, i) => [i, c] as const))("caso %i coincide con Python", (_, caso) => {
    const r = calcularFreno(caso.entrada as EntradaFreno);
    for (const [clave, esperado] of Object.entries(caso.salida)) {
      if (clave === "procedencia") continue;
      const obtenido = (r as unknown as Record<string, unknown>)[clave];
      if (typeof esperado === "number") expect(obtenido as number).toBeCloseTo(esperado, 3);
      else expect(obtenido).toEqual(esperado);
    }
  });

  it("los valores por defecto coinciden con EntradaFreno de Python", () => {
    expect(ENTRADA_FRENO_DEFECTO).toEqual(referencia.casos[0].entrada);
  });

  it("el par es lineal en la presión", () => {
    const a = calcularFreno({ ...ENTRADA_FRENO_DEFECTO, presion_bar: 20 }).par_frenado_nm;
    const b = calcularFreno({ ...ENTRADA_FRENO_DEFECTO, presion_bar: 40 }).par_frenado_nm;
    expect(b / a).toBeCloseTo(2, 4); // redondeo a 3 decimales, igual que Python
  });

  it("40 bar bloquean la rueda y 25 bar no", () => {
    expect(calcularFreno({ ...ENTRADA_FRENO_DEFECTO, presion_bar: 40 }).rueda_bloqueada).toBe(true);
    expect(calcularFreno(ENTRADA_FRENO_DEFECTO).rueda_bloqueada).toBe(false);
  });

  it("estadoRueda: se detiene en t_detencion y recorre d_detencion", () => {
    const r = calcularFreno(ENTRADA_FRENO_DEFECTO);
    const fin = estadoRueda(ENTRADA_FRENO_DEFECTO, r, (r.tiempo_detencion_s ?? 0) + 1);
    expect(fin.detenido).toBe(true);
    expect(fin.velocidad_kmh).toBe(0);
    expect(fin.recorrido_m).toBeCloseTo(r.distancia_detencion_m ?? 0, 2);
    const inicio = estadoRueda(ENTRADA_FRENO_DEFECTO, r, 0);
    expect(inicio.velocidad_kmh).toBeCloseTo(60, 6);
  });

  it("estadoRueda con bloqueo: la rueda se detiene antes que el vehículo", () => {
    const e = { ...ENTRADA_FRENO_DEFECTO, presion_bar: 60 };
    const r = calcularFreno(e);
    const s = estadoRueda(e, r, 0.3);
    expect(s.rueda_detenida).toBe(true);
    expect(s.detenido).toBe(false);
  });

  it("la secuencia de desmontaje exportada inicia con los pasadores y termina en el cubo", () => {
    expect(referencia.secuencia_desmontaje[0]).toBe("pasador_guia_1");
    expect(referencia.secuencia_desmontaje.at(-1)).toBe("cubo");
    expect(new Set(referencia.secuencia_desmontaje).size).toBe(15);
  });
});

describe("prensa: F = L·t·τ y biela-manivela", () => {
  it("fuerza de corte por defecto", () => {
    const f = fuerzaCorte(ENTRADA_PRENSA_DEFECTO);
    expect(f.fuerza_kn).toBeCloseTo((1200 * 2 * 280) / 1000, 9);
    expect(f.excede).toBe(false);
  });
  it("HSLA 4 mm excede 200 t", () => {
    const f = fuerzaCorte({ ...ENTRADA_PRENSA_DEFECTO, espesor_mm: 4, tau_mpa: 450 });
    expect(f.toneladas).toBeGreaterThan(200);
    expect(f.excede).toBe(true);
  });
  it("carrera: 0 en el punto muerto superior y 2r en el inferior", () => {
    expect(carrera(ENTRADA_PRENSA_DEFECTO, 0)).toBeCloseTo(0, 9);
    expect(carrera(ENTRADA_PRENSA_DEFECTO, Math.PI)).toBeCloseTo(2 * ENTRADA_PRENSA_DEFECTO.radio_manivela_mm, 9);
  });
  it("la ventana de corte está antes del punto muerto inferior", () => {
    const v = ventanaCorte(ENTRADA_PRENSA_DEFECTO);
    expect(v.inicio).toBeLessThan(v.fin);
    expect(v.fin).toBeLessThan(Math.PI);
    expect(carrera(ENTRADA_PRENSA_DEFECTO, v.fin) - carrera(ENTRADA_PRENSA_DEFECTO, v.inicio)).toBeCloseTo(2, 3);
  });
});

describe("línea: takt", () => {
  it("valores por defecto cumplen la demanda de 24.000 chasises/año", () => {
    const r = calcularLinea(ENTRADA_LINEA_DEFECTO);
    expect(r.takt_min).toBeCloseTo((288 * 2 * 8 * 60) / 24000, 9);
    expect(r.estaciones_min).toBe(21);
    expect(r.cumple).toBe(true);
    expect(colaAcumulada(ENTRADA_LINEA_DEFECTO, 10000)).toBe(0);
  });
  it("30.000 chasises/año con 22 estaciones no cumplen y la cola crece", () => {
    const e = { ...ENTRADA_LINEA_DEFECTO, demanda_anual: 30000 };
    const r = calcularLinea(e);
    expect(r.cumple).toBe(false);
    expect(r.estaciones_min).toBe(27);
    expect(r.deficit_anual).toBeGreaterThan(0);
    expect(colaAcumulada(e, 2000)).toBeGreaterThan(colaAcumulada(e, 500));
  });
  it("estaciones mínimas exactas cuando el contenido es múltiplo del takt", () => {
    const e = { ...ENTRADA_LINEA_DEFECTO, demanda_anual: 27648, contenido_min: 200 }; // takt = 10 min
    expect(calcularLinea(e).estaciones_min).toBe(20);
  });
});
