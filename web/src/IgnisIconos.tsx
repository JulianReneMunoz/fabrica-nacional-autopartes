/** Íconos de línea de la aplicación IGNIS (SVG propios de trazo, sin dependencias ni emojis). */
const TRAZOS = {
  menu: "M4 6h16M4 12h16M4 18h16",
  inicio: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z",
  cubo: "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3zM4 7.5l8 4.5 8-4.5M12 12v9",
  escaner: "M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3M4 12h16",
  grafica: "M4 20h16M7 16v-5M12 16V7M17 16v-8",
  arquitectura: "M9 3h6v5H9zM12 8v4M6 15v-3h12v3M4 15h4v5H4zM10 15h4v5h-4zM16 15h4v5h-4z",
  ajustes: "M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1",
  ayuda: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.5V14M12 17.5v.01",
  salir: "M9 21H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h4M16 17l5-5-5-5M21 12H9",
  mic: "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3M8 21h8",
  micApagado: "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3M8 21h8M3 3l18 18",
  volumen: "M4 9h4l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6M18.5 6.5a8 8 0 0 1 0 11",
  detener: "M7 7h10v10H7z",
  subtitulos: "M3 5h18v14H3zM10 10.5a2 2 0 1 0 0 3M17 10.5a2 2 0 1 0 0 3",
  girar: "M21 12a9 9 0 1 1-3-6.7M21 4v5h-5",
  acercar: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-5-5M8 11h6M11 8v6",
  alejar: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM21 21l-5-5M8 11h6",
  ampliar: "M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5",
  restablecer: "M3 12a9 9 0 1 0 3-6.7M3 4v5h5",
  descargar: "M12 4v11M7 10l5 5 5-5M5 20h14",
  archivo: "M6 3h8l4 4v14H6zM14 3v4h4M9 13h6M9 17h6",
  plano: "M4 4h16v16H4zM4 9h16M9 9v11M13 13h4v4h-4z",
  auto: "M3 15v-3l2.5-4.5A2 2 0 0 1 7.2 6.5h9.6a2 2 0 0 1 1.7 1L21 12v3a1 1 0 0 1-1 1h-1M3 15a1 1 0 0 0 1 1h1M9 16h6M7 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM17 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM4 12h16",
  faq: "M5 4h14a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-6l-4 3v-3H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zM10 8.5a2 2 0 1 1 2.8 1.8c-.5.2-.8.7-.8 1.2M12 14v.01",
  datos: "M12 3c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3zM4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6",
  corpus: "M4 5a1 1 0 0 1 1-1h5l2 2h7a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1zM8 11h8M8 15h5",
  base: "M5 6a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM19 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM6 20a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM18 19a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM6 5.5l5.2 5.8M18 7.6l-5.3 3.8M11.3 12.8l-4.6 5.4M12.8 12.6l4.4 4.8",
  memoria: "M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 0V5a1 1 0 0 0-1-1zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 0",
  herramienta: "M14.5 5.5a4 4 0 0 0-5 5L4 16l4 4 5.5-5.5a4 4 0 0 0 5-5l-2.5 2.5-2.5-.5-.5-2.5z",
  prompt: "M4 5h16v14H4zM8 10l2.5 2L8 14M13 14h3",
  deslizadores: "M4 7h10M18 7h2M4 17h4M12 17h8M16 5v4M10 15v4",
  lista: "M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01",
  objetivo: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 12h.01",
  matraz: "M9 3h6M10 3v6L5 18a2 2 0 0 0 1.8 3h10.4A2 2 0 0 0 19 18l-5-9V3M7.5 14h9",
  kanban: "M4 4h16v16H4zM9.3 4v16M14.7 4v16M6 7h1.5M11.3 7h1.5M16.7 7h1.5M6 10h1.5M16.7 10h1.5",
  usuario: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0",
  expandir: "M9 6l6 6-6 6",
  contraer: "M15 6l-6 6 6 6",
  mas: "M12 5v14M5 12h14",
  cerrar: "M6 6l12 12M18 6L6 18",
  enviar: "M4 12l16-8-6 16-2-7z",
  lapiz: "M15 4l5 5L9 20H4v-5z",
  historial: "M12 7v5l3 2M3 12a9 9 0 1 0 2.6-6.4M3 4v4h4",
  ruta: "M6 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM18 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM8 17h7a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7",
  escudo: "M12 3l7 3v6c0 4-3 7.5-7 9-4-1.5-7-5-7-9V6z",
  chat: "M4 5h16v11H9l-5 4z",
} as const;

export type NombreIcono = keyof typeof TRAZOS;

export function Icono({ nombre, tamano = 20 }: { nombre: NombreIcono; tamano?: number }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={tamano}
      height={tamano}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={TRAZOS[nombre]} />
    </svg>
  );
}
