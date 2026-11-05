// Validación de la paleta: contraste WCAG AA y simulación de daltonismo (Machado et al. 2009, severidad 1,0).
// Uso: node scripts/validar_paleta.mjs   (sale con código 1 si algún requisito falla)
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../src/tema/tokens.css", import.meta.url), "utf8");
const v = Object.fromEntries([...css.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map((m) => [m[1], m[2]]));
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const lum = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
const contraste = (a, b) => {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};
const MATRICES = {
  protanopia: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deuteranopia: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.01182, 0.04294, 0.968881]],
  tritanopia: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.3039]],
};
const aplicar = (m, c) => {
  const l = c.map(lin);
  return m.map((f) => Math.min(Math.max(f[0] * l[0] + f[1] * l[1] + f[2] * l[2], 0), 1)).map((x) => (x <= 0.0031308 ? 12.92 * x : 1.055 * x ** (1 / 2.4) - 0.055));
};
const lab = (c) => {
  const l = c.map(lin);
  const X = (0.4124 * l[0] + 0.3576 * l[1] + 0.1805 * l[2]) / 0.95047;
  const Y = 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2];
  const Z = (0.0193 * l[0] + 0.1192 * l[1] + 0.9505 * l[2]) / 1.08883;
  const f = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
};
const dE = (a, b) => Math.hypot(...lab(a).map((x, i) => x - lab(b)[i]));

let falla = false;
const informe = (t) => console.log(t);
informe("== Contraste (WCAG 2.1) ==");
const texto = [["tinta", "papel"], ["tinta-2", "papel"], ["tinta-3", "papel"], ["tinta-3", "papel-2"], ["acento-texto", "papel"], ["acento-texto", "acento-suave"],
  ["dato-texto", "papel"], ["dato-texto", "dato-fondo"], ["ok-texto", "papel"], ["ok-texto", "ok-fondo"], ["alerta-texto", "papel"], ["alerta-texto", "alerta-fondo"], ["papel", "tinta"], ["foco-inverso", "tinta"], ["acento", "tinta"]];
for (const [a, b] of texto) {
  const r = contraste(rgb(v[a]), rgb(v[b]));
  const ok = r >= 4.5;
  falla ||= !ok;
  informe(`${ok ? "OK " : "FALLA"} texto ${a} sobre ${b}: ${r.toFixed(2)}:1 (mínimo 4,5)`);
}
const grafico = [["acento", "papel"], ["dato", "papel"], ["ok", "papel"], ["alerta", "papel"], ["foco", "papel"], ["tinta-3", "papel"]];
// Las fases del ciclo (Okabe-Ito, definidas en modelos/moto.ts) son sectores grandes con etiqueta de texto; se informan sin bloquear.
const informativos = [["fase-admision", "papel"], ["fase-compresion", "papel"], ["fase-expansion", "papel"], ["fase-escape", "papel"]];
for (const [a, b] of informativos) informe(`INFO gráfico ${a} sobre ${b}: ${contraste(rgb(v[a]), rgb(v[b])).toFixed(2)}:1 (sector con etiqueta de texto)`);
for (const [a, b] of grafico) {
  const r = contraste(rgb(v[a]), rgb(v[b]));
  const ok = r >= 3;
  falla ||= !ok;
  informe(`${ok ? "OK " : "FALLA"} gráfico ${a} sobre ${b}: ${r.toFixed(2)}:1 (mínimo 3)`);
}
informe("\n== Distancia perceptual entre categorías (CIE76 ΔE; ≥ 20 = distinguibles sin color puro) ==");
for (const grupo of [["acento", "dato", "ok", "alerta"], ["fase-admision", "fase-compresion", "fase-expansion", "fase-escape"]]) {
  for (const [nombre, m] of [["normal", null], ...Object.entries(MATRICES)]) {
    let min = 1e9, par = "";
    for (let i = 0; i < grupo.length; i++)
      for (let j = i + 1; j < grupo.length; j++) {
        const a = m ? aplicar(m, rgb(v[grupo[i]])) : rgb(v[grupo[i]]);
        const b = m ? aplicar(m, rgb(v[grupo[j]])) : rgb(v[grupo[j]]);
        const d = dE(a, b);
        if (d < min) [min, par] = [d, `${grupo[i]}/${grupo[j]}`];
      }
    informe(`${min >= 20 ? "OK " : "AVISO"} ${grupo[0]}… ${nombre}: par más cercano ${par} ΔE=${min.toFixed(1)}`);
  }
}
informe("\nNota: los estados nunca dependen solo del color (ícono + texto en ChipDato; texto en InsigniaFuente).");
process.exit(falla ? 1 : 0);
