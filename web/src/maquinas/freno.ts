import type { DefinicionMaquina } from "./tipos";

export const FRENO: DefinicionMaquina = {
  id: "freno",
  ruta: "#/maquina/freno",
  navegacion: "Freno",
  pregunta: "¿Cómo convierte un freno de disco la presión hidráulica en fuerza de frenado?",
  formula: "T = 2 · μ · p · A · r",
  contexto: "p: presión hidráulica, A: área del pistón, μ: fricción pastilla-disco y r: radio efectivo del disco.",
  idea: "La presión empuja un solo pistón; la pinza flotante reacciona y aprieta el disco por ambas caras, así el par crece con la presión, el área del pistón, μ y el radio.",
  pasos: [
    "La presión hidráulica llega a la pinza",
    "El pistón empuja la pastilla interna: F = p · A",
    "La pinza flotante se desliza y aprieta la pastilla externa",
    "La fricción en ambas caras produce el par: T = 2 · μ · F · r",
    "El par decelera la rueda hasta detenerla",
  ],
  experimentos: [
    {
      pregunta: "Si la presión pasa de 25 a 50 bar, ¿qué le ocurre al par de frenado?",
      opciones: [
        { texto: "Se duplica", correcta: true },
        { texto: "Se cuadruplica", correcta: false },
        { texto: "No cambia: depende solo de μ", correcta: false },
      ],
    },
    {
      pregunta: "Si μ entre pastilla y disco baja de 0,40 a 0,30, ¿qué ocurre con la distancia de detención a 25 bar?",
      opciones: [
        { texto: "Disminuye", correcta: false },
        { texto: "Aumenta alrededor de un tercio", correcta: true },
        { texto: "No cambia", correcta: false },
      ],
    },
    {
      pregunta: "Con la misma presión, si la velocidad pasa de 60 a 120 km/h, ¿cuánto cambia la distancia?",
      opciones: [
        { texto: "Se duplica", correcta: false },
        { texto: "Se cuadruplica", correcta: true },
        { texto: "Se mantiene", correcta: false },
      ],
    },
  ],
  controles: [
    { id: "presion", etiqueta: "Presión hidráulica", min: 0, max: 80, paso: 1, unidad: "bar" },
    { id: "mu", etiqueta: "μ pastilla-disco", min: 0.2, max: 0.6, paso: 0.01, unidad: "", decimales: 2 },
    { id: "velocidad", etiqueta: "Velocidad inicial", min: 10, max: 140, paso: 5, unidad: "km/h" },
    { id: "despiece", etiqueta: "Despiece manual", min: 0, max: 1, paso: 0.01, unidad: "", decimales: 2 },
  ],
  pestanas: ["componentes", "empresa", "faq"],
  duracionRecorrido: 29,
  lamina: "freno",
  revisionExtra: ["Despiece reversible y orden de desmontaje validado por la API", "Holguras ampliadas declaradas en la escena"],
};
