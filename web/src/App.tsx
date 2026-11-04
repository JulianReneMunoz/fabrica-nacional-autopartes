import { lazy, Suspense, useEffect, useState } from "react";
import Biblioteca from "./paginas/Biblioteca";
import MaquinaPrensa from "./paginas/MaquinaPrensa";
import MaquinaLinea from "./paginas/MaquinaLinea";

// El simulador 3D carga three.js; se separa en su propio fragmento para que la biblioteca abra rápido.
const MaquinaFreno = lazy(() => import("./paginas/MaquinaFreno"));

/** Enrutador por hash (#/, #/maquina/freno?tour=1): funciona servido como estático desde FastAPI. */
export function leerRuta(hash: string) {
  const limpio = hash.replace(/^#/, "") || "/";
  const [ruta, consulta = ""] = limpio.split("?");
  return { ruta, parametros: new URLSearchParams(consulta) };
}

export default function App() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const alCambiar = () => setHash(window.location.hash);
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);
  const { ruta, parametros } = leerRuta(hash);
  const tour = parametros.get("tour") === "1";
  const id = ruta.startsWith("/maquina/") ? ruta.slice("/maquina/".length) : null;

  let pagina;
  if (id === "freno") pagina = <MaquinaFreno tour={tour} />;
  else if (id === "prensa") pagina = <MaquinaPrensa tour={tour} />;
  else if (id === "linea") pagina = <MaquinaLinea tour={tour} />;
  else pagina = <Biblioteca />;

  return (
    <>
      <header className="cabecera">
        <span className="marca">
          <b>FNA</b> · Anatomía de máquinas · v2.0
        </span>
        <nav aria-label="Principal">
          <a href="#/" aria-current={id ? undefined : "page"}>Biblioteca</a>
          <a href="#/maquina/freno" aria-current={id === "freno" ? "page" : undefined}>Freno 3D</a>
          <a href="#/maquina/prensa" aria-current={id === "prensa" ? "page" : undefined}>Prensa</a>
          <a href="#/maquina/linea" aria-current={id === "linea" ? "page" : undefined}>Línea</a>
          <a href="/docs" target="_blank" rel="noreferrer">API</a>
        </nav>
      </header>
      <main className={tour ? "contenedor tour" : "contenedor"}>
        <Suspense fallback={<p className="aviso">Cargando simulador 3D…</p>}>{pagina}</Suspense>
      </main>
    </>
  );
}
