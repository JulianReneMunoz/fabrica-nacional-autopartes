import { describe, expect, it } from "vitest";
import referencia from "./referencia_freno.json";
import refMoto from "./referencia_moto.json";
import * as moto from "../modelos/moto";
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

describe("moto: réplica TypeScript de fisica_moto (Python)", () => {
  const TOL = 1e-6;
  const cerca = (obtenido: number, esperado: number, tol = TOL) => expect(Math.abs(obtenido - esperado)).toBeLessThan(tol);
  const SUP = moto.SUPUESTOS;
  const carrera = (SUP.carrera_mm.valor as number) / 1000;
  const biela = (SUP.longitud_biela_mm.valor as number) / 1000;

  it("los supuestos coinciden con SUPUESTOS_REFERENCIA y llevan la etiqueta «supuesto didáctico»", () => {
    expect(Object.keys(SUP).sort()).toEqual(Object.keys(refMoto.supuestos).sort());
    for (const [clave, valor] of Object.entries(refMoto.supuestos)) expect(SUP[clave].valor).toEqual(valor);
    for (const x of Object.values(SUP)) expect(x.etiqueta).toBe("supuesto didáctico");
    cerca(moto.RADIO_PINON_M, refMoto.geometria_cadena.radio_pinon_m);
    cerca(moto.RADIO_CORONA_M, refMoto.geometria_cadena.radio_corona_m);
  });

  it.each(refMoto.llantas.map((c) => [c.medida, c] as const))("radio de llanta %s", (_, c) => {
    cerca(moto.diametroLlantaMm(c.medida), c.diametro_mm);
    cerca(moto.radioLlantaM(c.medida), c.radio_m);
  });
  it("el radio de 140/70-17 es 0,3139 m (±0,001)", () => {
    expect(Math.abs(moto.radioLlantaM("140/70-17") - 0.3139)).toBeLessThan(0.001);
    expect(() => moto.radioLlantaM("140-70/17")).toThrow();
  });

  it("velocidad por rpm y marcha coincide con Python", () => {
    expect(refMoto.velocidades.length).toBeGreaterThan(20);
    for (const c of refMoto.velocidades) {
      const g = (SUP.relaciones_marcha.valor as number[])[c.marcha - 1];
      const prim = SUP.relacion_primaria.valor as number;
      const fin = SUP.relacion_final.valor as number;
      cerca(moto.relacionTotal(prim, g, fin), c.relacion_total);
      cerca(moto.velocidadKmh(c.rpm, moto.radioLlantaM(c.medida), prim, g, fin), c.velocidad_kmh);
    }
  });
  it("la velocidad crece linealmente con las rpm y decrece con la relación", () => {
    const R = moto.radioLlantaM("140/70-17");
    const v1 = moto.velocidadKmh(3000, R, 3.35, 1.4, 3);
    expect(moto.velocidadKmh(6000, R, 3.35, 1.4, 3)).toBeCloseTo(2 * v1, 9);
    expect(moto.velocidadKmh(6000, R, 3.35, 1.1, 3)).toBeGreaterThan(moto.velocidadKmh(6000, R, 3.35, 1.4, 3));
  });

  it.each(refMoto.cilindradas.map((c) => [`${c.diametro_mm}x${c.carrera_mm}`, c] as const))("cilindrada %s", (_, c) => {
    cerca(moto.cilindradaCm3(c.diametro_mm, c.carrera_mm), c.cilindrada_cm3);
  });
  it("la cilindrada calculada coincide con la nominal dentro de ±1 %", () => {
    const r = moto.calcularMoto(moto.ENTRADA_MOTO_DEFECTO);
    expect(Math.abs(r.diferencia_cilindrada_pct)).toBeLessThan(1);
  });

  it("posición del pistón y ángulo de biela por ángulo de cigüeñal coinciden con Python", () => {
    for (const c of refMoto.pistones) {
      const t = (c.theta_grados * Math.PI) / 180;
      cerca(moto.posicionPistonM(t, c.carrera_m, c.biela_m), c.posicion_m);
      cerca(moto.anguloBielaRad(t, c.carrera_m, c.biela_m), c.angulo_biela_rad);
      expect(moto.faseCiclo(c.theta_grados)).toBe(c.fase);
    }
  });
  it("el pistón queda en [PMI, PMS], la carrera vale 2r y la biela no supera asin(r/L)", () => {
    const xs: number[] = [];
    let phiMax = 0;
    for (let g = 0; g <= 720; g += 2) {
      const t = (g * Math.PI) / 180;
      xs.push(moto.posicionPistonM(t, carrera, biela));
      phiMax = Math.max(phiMax, Math.abs(moto.anguloBielaRad(t, carrera, biela)));
    }
    const pms = biela + carrera / 2;
    const pmi = biela - carrera / 2;
    for (const x of xs) {
      expect(x).toBeLessThanOrEqual(pms + 1e-12);
      expect(x).toBeGreaterThanOrEqual(pmi - 1e-12);
    }
    cerca(Math.max(...xs) - Math.min(...xs), carrera, 1e-9);
    expect(phiMax).toBeLessThanOrEqual(Math.asin(carrera / 2 / biela) + 1e-12);
    const t = (70 * Math.PI) / 180; // φ cumple L·sin φ = r·sin θ
    cerca(biela * Math.sin(moto.anguloBielaRad(t, carrera, biela)), (carrera / 2) * Math.sin(t), 1e-12);
  });

  it("el ciclo dura 720° y recorre admisión, compresión, expansión y escape", () => {
    expect([0, 179, 180, 360, 540, 719].map(moto.faseCiclo)).toEqual(["admision", "admision", "compresion", "expansion", "escape", "escape"]);
    expect(moto.faseCiclo(720)).toBe(moto.faseCiclo(0));
    expect(moto.faseCiclo(-90)).toBe("escape");
  });
  it("las válvulas abren solo en su fase y la chispa salta en la expansión", () => {
    expect(moto.levanteAdmision(90)).toBeCloseTo(0.005, 9);
    expect(moto.levanteAdmision(270)).toBe(0);
    expect(moto.levanteEscape(630)).toBeCloseTo(0.005, 9);
    expect(moto.levanteEscape(90)).toBe(0);
    expect(moto.intensidadChispa(361)).toBeGreaterThan(0.9);
    expect(moto.intensidadChispa(300)).toBe(0);
    expect(moto.intensidadChispa(400)).toBe(0);
    expect(moto.faseCiclo(361)).toBe("expansion");
  });

  it("cadena: ω y velocidad lineal del piñón y de la corona coinciden con Python y entre sí", () => {
    for (const c of refMoto.cadena) {
      const g = (SUP.relaciones_marcha.valor as number[])[c.marcha - 1];
      const prim = SUP.relacion_primaria.valor as number;
      const fin = SUP.relacion_final.valor as number;
      cerca(moto.velocidadAngularPinonRadS(c.rpm, prim, g), c.omega_pinon_rad_s);
      cerca(moto.velocidadAngularCoronaRadS(c.rpm, prim, g, fin), c.omega_corona_rad_s);
      cerca(moto.velocidadCadenaMS(c.rpm, prim, g), c.v_cadena_m_s);
      cerca(moto.velocidadCadenaDesdeCoronaMS(c.rpm, prim, g, fin), c.v_cadena_desde_corona_m_s);
      cerca(moto.velocidadCadenaMS(c.rpm, prim, g), moto.velocidadCadenaDesdeCoronaMS(c.rpm, prim, g, fin), 1e-12);
    }
  });
  it("cadena: la corona gira con la rueda (ω_corona·R = v de la moto)", () => {
    const R = moto.radioLlantaM("140/70-17");
    const v = moto.velocidadKmh(6000, R, 3.35, 1.4, 3) / 3.6;
    cerca(moto.velocidadAngularCoronaRadS(6000, 3.35, 1.4, 3) * R, v, 1e-9);
  });
  it("cadena: el lazo es continuo, cerrado y la abscisa es longitud de arco", () => {
    const t = moto.trazadoCadena();
    const a = t.punto(0);
    const b = t.punto(t.longitud);
    cerca(a.x, b.x, 1e-9);
    cerca(a.y, b.y, 1e-9);
    const paso = 1e-4;
    for (let s = 0; s < t.longitud; s += t.longitud / 200) {
      const p = t.punto(s);
      const q = t.punto(s + paso);
      cerca(Math.hypot(q.x - p.x, q.y - p.y), paso, 1e-6);
    }
    const ys = Array.from({ length: 400 }, (_, i) => t.punto((i * t.longitud) / 400).y);
    expect(Math.max(...ys)).toBeGreaterThan(moto.EJE_CORONA[1] + moto.RADIO_CORONA_M - 0.003);
    expect(Math.min(...ys)).toBeLessThan(moto.EJE_CORONA[1] - moto.RADIO_CORONA_M + 0.003);
  });

  it("reparto CBS: coincide con Python y conserva la suma de presiones y de fuerzas", () => {
    for (const c of refMoto.reparto_cbs) {
      const e = c.entrada as moto.EntradaMoto;
      const [pd, pt] = moto.repartirPresion(e, c.presion_total_bar);
      cerca(pd, c.presion_delantera_bar);
      cerca(pt, c.presion_trasera_bar);
      cerca(pd + pt, c.presion_total_bar, 1e-12);
    }
    const base = { ...moto.ENTRADA_MOTO_DEFECTO, palanca: "trasera" as const, fuerza_palanca_n: 100, velocidad_inicial_kmh: 60 };
    const sin = moto.calcularMoto({ ...base, cbs: false });
    const con = moto.calcularMoto({ ...base, cbs: true });
    cerca(con.fuerza_pistones_total_n, sin.fuerza_pistones_total_n, 0.01);
    expect(con.freno_delantero && con.freno_trasero).toBeTruthy();
    expect(sin.freno_delantero).toBeNull();
  });

  it("cálculo completo: coincide con calcular_moto de Python (rpm, marcha, estado, frenos)", () => {
    expect(refMoto.calculos.length).toBeGreaterThan(20);
    for (const c of refMoto.calculos) {
      const r = moto.calcularMoto(c.entrada as moto.EntradaMoto, c.medida) as unknown as Record<string, unknown>;
      const esperado = c.salida as Record<string, unknown>;
      for (const clave of [
        "radio_llanta_m",
        "medida_llanta",
        "relacion_total",
        "rpm_efectivas",
        "estado_motor",
        "velocidad_kmh",
        "cilindrada_calculada_cm3",
        "cilindrada_referencia_cm3",
        "diferencia_cilindrada_pct",
        "fuerza_pistones_total_n",
        "rueda_delantera_bloqueada",
        "rueda_trasera_bloqueada",
      ]) {
        if (typeof esperado[clave] === "number") cerca(r[clave] as number, esperado[clave] as number);
        else expect(r[clave]).toEqual(esperado[clave]);
      }
      for (const lado of ["freno_delantero", "freno_trasero"]) {
        const esp = esperado[lado] as Record<string, unknown> | null;
        const obt = r[lado] as Record<string, unknown> | null;
        if (esp === null) {
          expect(obt).toBeNull();
          continue;
        }
        for (const [k, v] of Object.entries(esp)) {
          if (k === "procedencia") continue;
          if (typeof v === "number") cerca(obt?.[k] as number, v);
          else expect(obt?.[k]).toEqual(v);
        }
      }
    }
  });

  it("estados: limitador por encima del corte, ahogo con marcha por debajo del ralentí, neutro sin velocidad", () => {
    const lim = moto.calcularMoto({ ...moto.ENTRADA_MOTO_DEFECTO, rpm: 12000, marcha: 2 });
    expect(lim.estado_motor).toBe("limitador");
    expect(lim.rpm_efectivas).toBe(9500);
    const ahogo = moto.calcularMoto({ ...moto.ENTRADA_MOTO_DEFECTO, rpm: 900, marcha: 3 });
    expect(ahogo.estado_motor).toBe("ahogado");
    expect(ahogo.velocidad_kmh).toBe(0);
    expect(ahogo.relacion_total).toBeNull();
    const neutro = moto.calcularMoto({ ...moto.ENTRADA_MOTO_DEFECTO, rpm: 5000, marcha: 0 });
    expect(neutro.estado_motor).toBe("neutro");
    expect(neutro.velocidad_kmh).toBe(0);
  });
  it("el saneamiento acota lo inválido y ningún valor es NaN", () => {
    const sucio = { version: "XX", rpm: Number.NaN, marcha: 99, palanca: "z", fuerza_palanca_n: -5, cbs: true, velocidad_inicial_kmh: Infinity } as unknown as moto.EntradaMoto;
    const e = moto.sanearEntrada(sucio);
    expect(e.marcha).toBe(5);
    expect(e.fuerza_palanca_n).toBe(0);
    expect(e.cbs).toBe(true); // versión por defecto DLX
    expect(moto.sanearEntrada({ ...moto.ENTRADA_MOTO_DEFECTO, version: "STD", cbs: true }).cbs).toBe(false);
    const recorrer = (o: unknown): void => {
      if (typeof o === "number") expect(Number.isNaN(o)).toBe(false);
      else if (o && typeof o === "object") Object.values(o).forEach(recorrer);
    };
    for (let rpm = 0; rpm <= 12000; rpm += 1000)
      for (let marcha = 0; marcha <= 5; marcha++)
        for (const palanca of ["delantera", "trasera"] as const)
          recorrer(moto.calcularMoto({ ...moto.ENTRADA_MOTO_DEFECTO, rpm, marcha, palanca, fuerza_palanca_n: rpm / 40, cbs: true }));
    recorrer(moto.calcularMoto(sucio));
    recorrer(moto.trazadoCadena().punto(1.234));
  });
  it("«Ver con ficha de…» aplica solo campos publicados y conserva el resto como supuesto", () => {
    const campo = (valor: unknown, estado: "publicado" | "no_publicado"): moto.CampoFichaApi => ({ valor: valor as never, unidad: null, fuente: "f", fecha_consulta: "2026-11-04", estado });
    const grupos = { llantas: { trasera: campo("140/70-17", "publicado") }, motor: { cilindrada: campo(null, "no_publicado") } };
    const porVersion = { STD: { cbs: campo(false, "publicado") }, DLX: { cbs: campo(true, "publicado") } };
    const dlx = moto.ajusteDesdeFicha(grupos, porVersion, "DLX");
    expect(dlx.medidaLlanta).toBe("140/70-17");
    expect(dlx.cbsDisponible).toBe(true);
    expect(dlx.conservados).toContain("motor.cilindrada");
    expect(moto.ajusteDesdeFicha(grupos, porVersion, "STD").cbsDisponible).toBe(false);
    const vacio = moto.ajusteDesdeFicha(undefined, undefined, "DLX");
    expect(vacio.medidaLlanta).toBeNull();
    expect(vacio.cbsDisponible).toBeNull();
    const base = { ...moto.ENTRADA_MOTO_DEFECTO, rpm: 6000, marcha: 3 };
    expect(moto.calcularMoto(base, "140/70-17").velocidad_kmh).toBeGreaterThan(moto.calcularMoto(base).velocidad_kmh);
  });
  it("textoMarcha explica el cambio", () => {
    expect(moto.textoMarcha(3, 4.6)).toContain("1/4,60");
    expect(moto.textoMarcha(0, null)).toContain("Neutro");
  });

  it("A7: el disco delantero usa el radio de la llanta delantera y el trasero el de la trasera", () => {
    const e = { ...moto.ENTRADA_MOTO_DEFECTO, palanca: "trasera" as const, cbs: true, fuerza_palanca_n: 100, velocidad_inicial_kmh: 60 };
    const fs = moto.frenosMoto(e, null, 60);
    cerca(fs.delantero!.entrada.radio_neumatico_m, moto.radioLlantaM(moto.MEDIDA_DELANTERA_DEMO));
    cerca(fs.trasero!.entrada.radio_neumatico_m, moto.radioLlantaM("130/70-17"));
    expect(fs.delantero!.entrada.radio_neumatico_m).not.toBeCloseTo(fs.trasero!.entrada.radio_neumatico_m, 3);
  });
  it("A5: sin movimiento no se informa bloqueo", () => {
    const parado = moto.calcularMoto({ ...moto.ENTRADA_MOTO_DEFECTO, marcha: 0, palanca: "delantera", fuerza_palanca_n: 600 });
    expect(parado.freno_delantero).not.toBeNull();
    expect(parado.rueda_delantera_bloqueada).toBe(false);
    expect(moto.calcularMoto({ ...moto.ENTRADA_MOTO_DEFECTO, rpm: 5000, marcha: 3, fuerza_palanca_n: 600 }).rueda_delantera_bloqueada).toBe(true);
  });
  it("A18: marcha alta con rpm bajas ahoga; en marchas bajas el embrague patina", () => {
    expect(moto.calcularMoto({ ...moto.ENTRADA_MOTO_DEFECTO, rpm: 600, marcha: 5 }).estado_motor).toBe("ahogado");
    expect(moto.calcularMoto({ ...moto.ENTRADA_MOTO_DEFECTO, rpm: 600, marcha: 1 }).estado_motor).toBe("patinaje");
  });
  it("A6: con la STD el freno trasero no publicado se conserva como supuesto", () => {
    const campo = (valor: unknown, estado: "publicado" | "no_publicado"): moto.CampoFichaApi => ({ valor: valor as never, unidad: null, fuente: "f", fecha_consulta: "2026-11-04", estado });
    const pv = { STD: { trasero: campo(null, "no_publicado"), cbs: campo(false, "publicado") }, DLX: { trasero: campo("Disco", "publicado"), cbs: campo(true, "publicado") } };
    expect(moto.ajusteDesdeFicha({}, pv, "STD").conservados).toContain("frenos.STD.trasero");
    expect(moto.ajusteDesdeFicha({}, pv, "STD").traseroPublicado).toBeNull();
    expect(moto.ajusteDesdeFicha({}, pv, "DLX").conservados).not.toContain("frenos.DLX.trasero");
    expect(moto.ajusteDesdeFicha({}, pv, "DLX").traseroPublicado).toBe(true);
  });
  it("A8: con el limitador la chispa se suprime en ciclos alternos", () => {
    expect(moto.intensidadChispaMotor(361, 0, "normal")).toBeGreaterThan(0.9);
    expect(moto.intensidadChispaMotor(361, 1, "normal")).toBeGreaterThan(0.9);
    expect(moto.intensidadChispaMotor(361, 0, "limitador")).toBeGreaterThan(0.9);
    expect(moto.intensidadChispaMotor(361, 1, "limitador")).toBe(0);
    expect(moto.intensidadChispaMotor(361, 0, "ahogado")).toBe(0);
  });
});

describe("moto: dinámica con la velocidad como variable de estado continua", () => {
  const SUP = moto.SUPUESTOS;
  const num = (c: string) => SUP[c].valor as number;
  const marchas = SUP.relaciones_marcha.valor as number[];
  const prim = num("relacion_primaria");
  const fin = num("relacion_final");
  const corte = num("corte_encendido_rpm");
  const cotaA = (v: number) => Math.max(num("aceleracion_max_m_s2"), 9.80665 * num("adherencia_neumatico")) + num("rozamiento_m_s2") + num("arrastre_aero_1_m") * v * v;

  it.each(refMoto.dinamica.map((d, i) => [d.medida ?? "genérica", i] as const))("el escenario exportado por Python coincide paso a paso (%s) con tolerancia 1e-6", (_, i) => {
    const din = refMoto.dinamica[i];
    const radio = moto.radioLlantaM(din.medida ?? String(SUP.medida_llanta_trasera.valor));
    let est = din.estado_inicial as moto.EstadoDinamico;
    let previo = est;
    const modos = new Set<string>();
    expect(din.pasos.length).toBeGreaterThan(500);
    for (const p of din.pasos) {
      est = moto.pasoMoto(est, p.mando as moto.MandoMoto, p.dt, din.medida);
      const esp = p.estado;
      expect(Math.abs(est.v_ms - esp.v_ms)).toBeLessThan(1e-6);
      expect(Math.abs(est.rpm_motor - esp.rpm_motor)).toBeLessThan(1e-6);
      expect(est.modo).toBe(esp.modo);
      expect(est.v_ms).toBeGreaterThanOrEqual(0);
      expect(Number.isNaN(est.rpm_motor)).toBe(false);
      modos.add(est.modo);
      if (p.dt === 0) expect(est.v_ms).toBe(previo.v_ms); // Δv = 0 exacto en el cambio de mandos
      else expect(Math.abs(est.v_ms - previo.v_ms)).toBeLessThanOrEqual(cotaA(previo.v_ms) * p.dt + 1e-12);
      if (p.mando.marcha >= 1 && !p.mando.freno && (est.modo === "normal" || est.modo === "limitador")) {
        const deriv = moto.rpmDerivadas(est.v_ms, radio, prim, marchas[p.mando.marcha - 1], fin);
        expect(Math.abs(est.rpm_motor - Math.min(deriv, corte))).toBeLessThan(1e-6);
      }
      previo = est;
    }
    for (const m of ["neutro", "normal", "patinaje", "limitador", "embrague", "ahogado"]) expect(modos.has(m)).toBe(true);
  });

  it("el cambio de marcha salta las rpm y no la velocidad; el neutro decae sin detenerse en seco", () => {
    let est: moto.EstadoDinamico = { v_ms: 12, rpm_motor: 5000, modo: "normal", t_freno_s: 0, a_ms2: 0 };
    const m1 = { ...moto.MANDO_DEFECTO, marcha: 2, acelerador: 0.5 };
    const cambio = moto.pasoMoto(est, { ...m1, marcha: 4 }, 0);
    expect(cambio.v_ms).toBe(est.v_ms);
    expect(cambio.rpm_motor).not.toBeCloseTo(moto.pasoMoto(est, m1, 0).rpm_motor, 0);
    for (let i = 0; i < 60; i++) est = moto.pasoMoto(est, { ...moto.MANDO_DEFECTO, marcha: 0 }, 0.05);
    expect(est.v_ms).toBeGreaterThan(8);
    expect(est.v_ms).toBeLessThan(12);
  });
  it("frenar hasta detenerse: v monótona decreciente, sin v negativa; soltar continúa desde la v actual", () => {
    let est: moto.EstadoDinamico = { v_ms: 15, rpm_motor: 1400, modo: "embrague", t_freno_s: 0, a_ms2: 0 };
    const frena = { ...moto.MANDO_DEFECTO, marcha: 2, palanca: "trasera" as const, cbs: true, fuerza_palanca_n: 180, freno: true };
    let prev = est.v_ms;
    for (let i = 0; i < 200; i++) {
      est = moto.pasoMoto(est, frena, 0.05);
      expect(est.v_ms).toBeLessThanOrEqual(prev);
      expect(est.v_ms).toBeGreaterThanOrEqual(0);
      prev = est.v_ms;
    }
    expect(est.v_ms).toBe(0);
    expect(moto.pasoMoto(est, { ...frena, freno: false }, 0.05).v_ms).toBe(0);
    for (let i = 0; i < 60; i++) est = moto.pasoMoto(est, { ...moto.MANDO_DEFECTO, marcha: 1, acelerador: 1 }, 0.05);
    expect(est.v_ms).toBeGreaterThan(3);
  });
  it("calcularMotoDesdeEstado toma v y rpm del estado, y marca el bloqueo solo con movimiento", () => {
    const mando = { ...moto.MANDO_DEFECTO, marcha: 3, fuerza_palanca_n: 600, freno: true };
    const enMarcha = moto.calcularMotoDesdeEstado({ v_ms: 10, rpm_motor: 3000, modo: "embrague", t_freno_s: 0, a_ms2: 0 }, mando);
    expect(enMarcha.velocidad_kmh).toBeCloseTo(36, 6);
    expect(enMarcha.rueda_delantera_bloqueada).toBe(true);
    const parada = moto.calcularMotoDesdeEstado({ v_ms: 0, rpm_motor: 1400, modo: "embrague", t_freno_s: 0, a_ms2: 0 }, mando);
    expect(parada.rueda_delantera_bloqueada).toBe(false);
  });
});
