import { describe, expect, it } from 'vitest';
import { crearEstado, nucleo, pasoEscaner, posicionBarrido, nivelesSinMovimiento } from './escanerIgnis';

function correr(modo: Parameters<typeof pasoEscaner>[2], segundos: number, amplitud = 0) {
  let e = crearEstado();
  const dt = 1 / 60;
  for (let t = 0; t < segundos; t += dt) e = pasoEscaner(e, dt, modo, amplitud);
  return e;
}

describe('posicionBarrido', () => {
  it('va de izquierda a derecha y vuelve', () => {
    expect(posicionBarrido(0)).toBeCloseTo(0);
    expect(posicionBarrido(0.5)).toBeCloseTo(1);
    expect(posicionBarrido(1)).toBeCloseTo(0);
    expect(posicionBarrido(0.25)).toBeCloseTo(0.5);
  });
});

describe('nucleo', () => {
  it('es máximo en el segmento del núcleo y 0 lejos', () => {
    expect(nucleo(0, 0, 12, 1)).toBe(1);
    expect(nucleo(5, 0, 12, 1)).toBe(0);
  });
});

describe('pasoEscaner', () => {
  it('no muta el estado anterior', () => {
    const e0 = crearEstado();
    const copia = JSON.stringify(e0);
    pasoEscaner(e0, 0.1, 'hablando', 0.8);
    expect(JSON.stringify(e0)).toBe(copia);
  });

  it('al hablar el segmento más brillante recorre toda la barra', () => {
    let e = crearEstado();
    const visitados = new Set<number>();
    for (let k = 0; k < 120; k++) {
      e = pasoEscaner(e, 1 / 60, 'hablando', 0.6);
      visitados.add(e.niveles.indexOf(Math.max(...e.niveles)));
    }
    expect(visitados.has(0)).toBe(true);
    expect(visitados.has(11)).toBe(true);
  });

  it('deja estela: varios segmentos encendidos a la vez', () => {
    const e = correr('hablando', 0.7, 0.7);
    expect(e.niveles.filter((v) => v > 0.05).length).toBeGreaterThan(2);
  });

  it('más amplitud da más brillo al hablar', () => {
    const bajo = Math.max(...correr('hablando', 1, 0).niveles);
    const alto = Math.max(...correr('hablando', 1, 1).niveles);
    expect(alto).toBeGreaterThan(bajo);
  });

  it('en reposo queda tenue y centrado', () => {
    const e = correr('reposo', 3);
    expect(Math.max(...e.niveles)).toBeLessThan(0.35);
    expect(e.niveles[0]).toBeLessThan(e.niveles[5]);
  });

  it('al escuchar se abre desde el centro con el volumen', () => {
    const poco = correr('escuchando', 0.5, 0.1).niveles.filter((v) => v > 0.3).length;
    const mucho = correr('escuchando', 0.5, 1).niveles.filter((v) => v > 0.3).length;
    expect(mucho).toBeGreaterThan(poco);
  });

  it('los niveles siempre están entre 0 y 1', () => {
    const e = correr('hablando', 2, 5);
    e.niveles.forEach((v) => {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    });
  });
});

describe('nivelesSinMovimiento', () => {
  it('es simétrico', () => {
    const n = nivelesSinMovimiento('hablando');
    expect(n[0]).toBeCloseTo(n[11]);
  });
});

import { amplitudPorEventos, modoDesdeConversacion } from './escanerIgnis';

describe('modoDesdeConversacion', () => {
  it('teclear o hablar al micrófono → escuchando', () => {
    expect(modoDesdeConversacion('escribiendo')).toBe('escuchando');
    expect(modoDesdeConversacion('escuchando')).toBe('escuchando');
  });
  it('respuesta por texto o por voz → hablando', () => {
    expect(modoDesdeConversacion('respondiendo')).toBe('hablando');
    expect(modoDesdeConversacion('hablando')).toBe('hablando');
  });
  it('reposo o estados desconocidos → reposo', () => {
    ['auto', 'desconocido', ''].forEach((e) =>
      expect(modoDesdeConversacion(e)).toBe('reposo'),
    );
  });
});

describe('amplitudPorEventos', () => {
  it('sube con cada evento y se apaga sin eventos', () => {
    const a = amplitudPorEventos(0, 1 / 60, 2);
    expect(a).toBeGreaterThan(0.5);
    let b = a;
    for (let i = 0; i < 60; i++) b = amplitudPorEventos(b, 1 / 60, 0);
    expect(b).toBeLessThan(0.01);
  });
  it('nunca pasa de 1', () => {
    expect(amplitudPorEventos(0.9, 0.01, 10)).toBe(1);
  });
});
