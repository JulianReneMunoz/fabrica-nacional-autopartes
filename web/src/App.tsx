import { lazy, Suspense, useEffect, useState } from "react";
import { MAQUINAS } from "./maquinas";
import Biblioteca from "./paginas/Biblioteca";
import MaquinaLinea from "./paginas/MaquinaLinea";
import MaquinaPrensa from "./paginas/MaquinaPrensa";

// El simulador 3D carga three.js; se separa en su propio fragmento para que la biblioteca abra rápido.
const MaquinaFreno = lazy(() => import("./paginas/MaquinaFreno"));
const MaquinaMoto = lazy(() => import("./paginas/MaquinaMoto"));
const ExploradorMoto = lazy(() => import("./paginas/ExploradorMoto"));

/** Enrutador por hash (#/, #/maquina/freno?tour=1): funciona servido como estático desde FastAPI. */
export function leerRuta(hash: string) {
  const limpio = hash.replace(/^#/, "") || "/";
  const [ruta, consulta = ""] = limpio.split("?");
  return { ruta, parametros: new URLSearchParams(consulta) };
}

/** Id de la máquina de una ruta. Alias: #/moto → moto_honda; #/explorador → explorador de la moto. */
export function idDeRuta(ruta: string): string | null {
  if (ruta === "/moto") return "moto_honda";
  if (ruta === "/explorador" || ruta === "/maquina/moto_honda/explorador") return "moto_explorador";
  return ruta.startsWith("/maquina/") ? ruta.slice("/maquina/".length) : null;
}

export default function App() {
  const [hash, setHash] = useState(window.location.hash);
  const [menu, setMenu] = useState(false);
  useEffect(() => {
    const alCambiar = () => {
      setHash(window.location.hash);
      setMenu(false);
    };
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);
  const { ruta, parametros } = leerRuta(hash);
  const tour = parametros.get("tour") === "1";
  const id = idDeRuta(ruta);

  let pagina;
  if (id === "freno") pagina = <MaquinaFreno tour={tour} />;
  else if (id === "prensa") pagina = <MaquinaPrensa tour={tour} />;
  else if (id === "linea") pagina = <MaquinaLinea tour={tour} />;
  else if (id === "moto_honda") pagina = <MaquinaMoto tour={tour} />;
  else if (id === "moto_explorador") pagina = <ExploradorMoto />;
  else pagina = <Biblioteca />;

  return (
    <>
      <header className="cabecera">
        <span className="marca">
          <b>FNA</b> · Anatomía<span className="larga"> de máquinas · v2.0</span>
        </span>
        <button className="boton-menu" aria-expanded={menu} aria-controls="navegacion-principal" onClick={() => setMenu(!menu)}>
          {menu ? "✕ Cerrar" : "☰ Menú"}
        </button>
        <nav id="navegacion-principal" className={menu ? "abierto" : undefined} aria-label="Principal">
          <a href="#/" aria-current={id ? undefined : "page"}>Biblioteca</a>
          {MAQUINAS.map((m) => (
            <a key={m.id} href={m.ruta} aria-current={id === m.id ? "page" : undefined}>{m.navegacion}</a>
          ))}
          <a href="/docs" target="_blank" rel="noreferrer">API</a>
        </nav>
      </header>
      <main className={tour ? "contenedor tour" : "contenedor"}>
        <Suspense fallback={<p className="aviso">Cargando simulador 3D…</p>}>{pagina}</Suspense>
      </main>
    </>
  );
}
