import type { DefinicionMaquina } from "./tipos";

export const PRENSA: DefinicionMaquina = {
  id: "prensa",
  ruta: "#/maquina/prensa",
  navegacion: "Prensa",
  pregunta: "¿Cómo convierte una prensa una lámina de acero en un panel estampado?",
  formula: "F = L · t · τ",
  contexto: "L: perímetro de corte, t: espesor de la lámina y τ: resistencia al corte; la prensa debe entregar al menos F.",
  idea: "La fuerza para cortar crece con el perímetro, el espesor y la resistencia del acero.",
  pasos: [
    "El volante y la manivela giran y almacenan energía",
    "La biela convierte el giro en carrera vertical del carro",
    "El punzón toca la lámina sobre la matriz",
    "Corte: la prensa debe entregar F = L · t · τ",
    "El carro sube y la pieza estampada queda libre",
  ],
  experimentos: [
    {
      pregunta: "Si el espesor de la lámina pasa de 2 a 4 mm, ¿qué ocurre con la fuerza de corte?",
      opciones: [
        { texto: "Se duplica", correcta: true },
        { texto: "Se cuadruplica", correcta: false },
        { texto: "Se reduce porque la lámina es más rígida", correcta: false },
      ],
    },
    {
      pregunta: "Con acero HSLA 420 de 4 mm y 1.200 mm de perímetro, ¿completa la prensa de 200 t el corte?",
      opciones: [
        { texto: "Sí, con margen", correcta: false },
        { texto: "No: la fuerza supera la capacidad", correcta: true },
      ],
    },
    {
      pregunta: "¿En qué punto de la carrera es mínima la velocidad del carro?",
      opciones: [
        { texto: "A mitad de carrera", correcta: false },
        { texto: "En los puntos muertos superior e inferior", correcta: true },
        { texto: "Es constante", correcta: false },
      ],
    },
  ],
  controles: [
    { id: "espesor", etiqueta: "Espesor de lámina", min: 0.5, max: 6, paso: 0.1, unidad: "mm", decimales: 1 },
    { id: "perimetro", etiqueta: "Perímetro de corte", min: 200, max: 3000, paso: 50, unidad: "mm" },
  ],
  pestanas: ["componentes", "empresa", "faq"],
  componentes: [
    { nombre: "Bastidor", funcion: "Estructura rígida que soporta la reacción del corte." },
    { nombre: "Volante y manivela", funcion: "Almacenan energía y generan el giro que mueve la biela." },
    { nombre: "Biela", funcion: "Convierte el giro de la manivela en carrera vertical del carro." },
    { nombre: "Carro y punzón", funcion: "Bajan hasta la lámina y la cortan contra la matriz." },
    { nombre: "Matriz", funcion: "Define el contorno del corte y recibe la pieza estampada." },
    { nombre: "Lámina de acero", funcion: "Material que se corta; su espesor y su τ fijan la fuerza." },
  ],
  duracionRecorrido: 28,
  lamina: "prensa",
  revisionExtra: ["τ por material declarado como rango típico publicado (demostrativo)"],
};
