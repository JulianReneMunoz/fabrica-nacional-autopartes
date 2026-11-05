import type { DefinicionMaquina } from "./tipos";

export const MOTO_HONDA: DefinicionMaquina = {
  id: "moto_honda",
  ruta: "#/maquina/moto_honda",
  navegacion: "Moto",
  pregunta: "¿Cómo convierte una motocicleta Honda el giro del motor en velocidad de la rueda, y la palanca en fuerza de frenado?",
  formula: "v = rpm·2π·R / (i_prim · i_marcha · i_final)",
  contexto: "Las rpm del motor, las relaciones primaria, de marcha y final, y el radio R de la llanta fijan la velocidad; el freno sigue T = 2·μ·p·A·r.",
  idea: "La velocidad es el giro del motor dividido por las relaciones de transmisión y multiplicado por la circunferencia de la llanta; el freno invierte el camino y convierte la fuerza de la mano en torque sobre la rueda.",
  pasos: [
    "El pistón baja y sube: la biela-manivela convierte esa carrera en giro del cigüeñal (ciclo 4T de 720°)",
    "Con una marcha engranada el embrague patina en el arranque y acopla el motor a la transmisión",
    "El piñón, la cadena y la corona transmiten el giro: v = ω · r en ambos extremos",
    "La rueda trasera gira a ω = v / R y la moto avanza",
    "La palanca presiona el pistón del caliper: F = p · A y T = 2 · μ · F · r",
    "El par decelera la rueda hasta detener la moto",
  ],
  experimentos: [
    {
      pregunta: "En 3.ª, con el acelerador a fondo desde 72 km/h, ¿qué ocurre al llegar al corte de encendido?",
      opciones: [
        { texto: "La velocidad sigue aumentando sin límite", correcta: false },
        { texto: "La velocidad se estabiliza: el limitador corta la chispa", correcta: true },
        { texto: "El motor se ahoga", correcta: false },
      ],
    },
    {
      pregunta: "Con 5.ª engranada a unos 11 km/h y sin acelerar, ¿qué ocurre?",
      opciones: [
        { texto: "El motor se ahoga: las rpm derivadas caen bajo el ralentí", correcta: true },
        { texto: "El embrague patina y la moto sigue acelerando", correcta: false },
        { texto: "El limitador sube las rpm", correcta: false },
      ],
    },
    {
      pregunta: "Palanca delantera con 400 N y sin CBS a unos 41 km/h, ¿qué le ocurre a la rueda delantera?",
      opciones: [
        { texto: "Se bloquea (modelo sin ABS)", correcta: true },
        { texto: "Frena sin bloquearse", correcta: false },
        { texto: "Se detiene tras exactamente 1 s", correcta: false },
      ],
    },
  ],
  controles: [{ id: "acelerador", etiqueta: "Acelerador", min: 0, max: 100, paso: 5, unidad: "%" }],
  pestanas: ["componentes", "empresa", "ficha", "faq"],
  duracionRecorrido: 29,
  lamina: "moto_honda",
  revisionExtra: [
    "Cada cifra indica su procedencia: ficha publicada, «No publicado» o supuesto didáctico",
    "Cámara lenta de los giros siempre visible (1/200 de la velocidad real por omisión)",
    "La velocidad es una variable de estado continua: al cambiar de marcha saltan las rpm, nunca la velocidad",
    "El piñón, la corona, la cadena y la rueda comparten la misma ω_corona·r_corona = ω_piñón·r_piñón",
    "Sin logotipos ni réplica de un modelo comercial; la lámina no se muestra",
  ],
};
