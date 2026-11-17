import { describe, expect, it } from "vitest";
import { bajarNivel, CONFIG_CALIDAD, nivelDesdeUrl, nivelInicial, subirNivel } from "../ignisCalidad";

describe("niveles de calidad de la escena IGNIS", () => {
  it("baja y sube un nivel sin salirse de los extremos", () => {
    expect(bajarNivel("alto")).toBe("medio");
    expect(bajarNivel("medio")).toBe("bajo");
    expect(bajarNivel("bajo")).toBe("bajo");
    expect(subirNivel("bajo")).toBe("medio");
    expect(subirNivel("alto")).toBe("alto");
  });

  it("lee ?calidad= de la búsqueda o del hash e ignora valores desconocidos", () => {
    expect(nivelDesdeUrl("?calidad=bajo")).toBe("bajo");
    expect(nivelDesdeUrl("", "#/atencion?calidad=medio")).toBe("medio");
    expect(nivelDesdeUrl("?calidad=ultra")).toBeNull();
    expect(nivelInicial("", "#/atencion")).toBe("alto");
  });

  it("el nivel bajo no usa reflejos ni posprocesado y cada nivel es más liviano que el anterior", () => {
    expect(CONFIG_CALIDAD.bajo.reflector).toBe(0);
    expect(CONFIG_CALIDAD.bajo.posprocesado).toBe(false);
    expect(CONFIG_CALIDAD.alto.reflector).toBeGreaterThan(CONFIG_CALIDAD.medio.reflector);
    expect(CONFIG_CALIDAD.alto.dpr[1]).toBeGreaterThan(CONFIG_CALIDAD.medio.dpr[1]);
    expect(CONFIG_CALIDAD.medio.oclusion).toBe(false);
  });
});
