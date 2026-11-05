import { calcularLinea, ENTRADA_LINEA_DEFECTO } from "../modelos/linea";
import type { DefinicionMaquina } from "./tipos";

const R30 = calcularLinea({ ...ENTRADA_LINEA_DEFECTO, demanda_anual: 30000, contenido_min: 240, estaciones: 22, turnos_dia: 2 });

export const LINEA: DefinicionMaquina = {
  id: "linea",
  ruta: "#/maquina/linea",
  navegacion: "Línea",
  pregunta: "¿Cada cuánto debe salir un chasis de la línea de ensamble?",
  formula: "takt = tiempo disponible / demanda",
  contexto: "El tiempo disponible al año dividido por la demanda anual fija el ritmo de salida de cada chasis.",
  idea: "La demanda fija el ritmo: si una estación tarda más que el takt, la cola crece.",
  pasos: [
    "La demanda anual y el tiempo disponible fijan el takt",
    "El contenido de trabajo se reparte entre las estaciones",
    "Cada estación trabaja un ciclo c = contenido / estaciones",
    "Si c ≤ takt sale un chasis a tiempo; si no, la cola crece",
  ],
  experimentos: [
    {
      pregunta: "Si la demanda sube a 30.000 chasises/año con 22 estaciones y 240 min de contenido, ¿se cumple el takt?",
      opciones: [
        { texto: "Sí, sobra capacidad", correcta: false },
        { texto: "No: el ciclo supera el takt y la cola crece", correcta: true },
      ],
    },
    {
      pregunta: "¿Cuántas estaciones como mínimo se necesitan para 30.000 chasises/año?",
      opciones: [
        { texto: "22", correcta: false },
        { texto: String(R30.estaciones_min), correcta: true },
        { texto: "35", correcta: false },
      ],
    },
    {
      pregunta: "Con 30.000 chasises/año, si se pasa de 2 a 3 turnos, ¿qué ocurre con el takt?",
      opciones: [
        { texto: "Disminuye", correcta: false },
        { texto: "Aumenta un 50 %", correcta: true },
        { texto: "No cambia", correcta: false },
      ],
    },
  ],
  controles: [
    { id: "demanda", etiqueta: "Demanda anual", min: 6000, max: 40000, paso: 500, unidad: "chasises" },
    { id: "contenido", etiqueta: "Contenido de trabajo", min: 60, max: 480, paso: 10, unidad: "min/chasis" },
    { id: "estaciones", etiqueta: "Estaciones", min: 4, max: 40, paso: 1, unidad: "" },
    { id: "turnos", etiqueta: "Turnos por día", min: 1, max: 3, paso: 1, unidad: "" },
  ],
  pestanas: ["componentes", "empresa", "faq"],
  componentes: [
    { nombre: "Cola de entrada", funcion: "Chasises esperando: crece cuando el ciclo supera al takt." },
    { nombre: "Transportador", funcion: "Mueve cada chasis de una estación a la siguiente." },
    { nombre: "Estaciones de trabajo", funcion: "Reparten el contenido de trabajo: c = contenido / estaciones." },
    { nombre: "Salida", funcion: "Cuenta los chasises terminados frente a los demandados." },
  ],
  duracionRecorrido: 26,
  lamina: "linea",
  revisionExtra: ["Demanda inicial tomada de la base de conocimiento con su URL"],
};
