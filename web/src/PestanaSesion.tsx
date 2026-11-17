/**
 * «Mi sesión» (ADR-033): alias y `user_id` seudónimo recortado, hilos del usuario con «Reabrir», «Nuevo hilo» y
 * «Cerrar sesión». Los datos salen de la API; sin hilos se muestra el estado vacío.
 */
import { useCallback, useEffect, useState } from "react";
import { etiquetaRuta } from "./ignisCliente";
import { useIgnis } from "./ignisContexto";
import { Icono } from "./IgnisIconos";
import { hashDe } from "./ignisRutas";
import { ErrorSesion, listarHilos, type HiloDTO } from "./ignisSesion";

type Estado = { tipo: "cargando" } | { tipo: "error"; mensaje: string } | { tipo: "listo"; hilos: HiloDTO[] };

function fecha(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("es-CO", { dateStyle: "short", timeStyle: "short" });
}

export default function PestanaSesion() {
  const { sesion, hilo, abrirHilo, nuevoHilo, cerrarSesion, sesionVencida } = useIgnis();
  const [estado, setEstado] = useState<Estado>({ tipo: "cargando" });
  const [aviso, setAviso] = useState("");

  const manejarError = useCallback(
    (e: unknown) => {
      if (e instanceof ErrorSesion && e.estado === 401) sesionVencida();
      return e instanceof Error ? e.message : String(e);
    },
    [sesionVencida],
  );

  const cargar = useCallback(() => {
    setEstado({ tipo: "cargando" });
    listarHilos()
      .then((hilos) => setEstado({ tipo: "listo", hilos }))
      .catch((e: unknown) => setEstado({ tipo: "error", mensaje: manejarError(e) }));
  }, [manejarError]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const irAAtencion = () => {
    window.location.hash = hashDe("atencion");
  };

  const reabrir = (threadId: string) => {
    abrirHilo(threadId);
    irAAtencion();
  };

  const crear = async () => {
    try {
      await nuevoHilo();
      irAAtencion();
    } catch (e) {
      setAviso(manejarError(e));
    }
  };

  const usuario = sesion.estado === "activa" ? sesion : null;
  return (
    <section className="ig-pestana" aria-labelledby="titulo-sesion">
      <header className="ig-pestana-cab">
        <span className="ig-pestana-icono" aria-hidden="true">
          <Icono nombre="usuario" tamano={22} />
        </span>
        <h1 id="titulo-sesion">Mi sesión</h1>
      </header>

      <div className="ig-sesion-datos">
        <div>
          <span className="ig-sesion-etiqueta">Alias</span>
          <strong>{usuario?.alias ?? "—"}</strong>
        </div>
        <div>
          <span className="ig-sesion-etiqueta">Usuario seudónimo</span>
          <code title="Primeros 8 caracteres del user_id (HMAC del alias)">{usuario?.userIdCorto ?? "—"}</code>
        </div>
        <div className="ig-sesion-acciones">
          <button className="ignis-btn primario" onClick={() => void crear()}>
            <Icono nombre="mas" tamano={16} /> Nuevo hilo
          </button>
          <button className="ignis-btn" onClick={() => void cerrarSesion()}>
            <Icono nombre="salir" tamano={16} /> Cerrar sesión
          </button>
        </div>
      </div>
      <p className="ig-vacio-motivo">
        El alias no se guarda en el servidor: solo viaja en la cookie cifrada de este navegador. Cerrar sesión la
        borra de aquí.
      </p>
      {aviso ? (
        <p className="ignis-aviso" role="alert">
          {aviso}
        </p>
      ) : null}

      <h2 className="ig-sesion-subtitulo">Mis hilos</h2>
      {estado.tipo === "cargando" ? (
        <div className="ig-esqueleto" aria-busy="true" aria-label="Cargando los hilos">
          <span className="ig-esqueleto-linea ancha" />
          <span className="ig-esqueleto-linea" />
        </div>
      ) : estado.tipo === "error" ? (
        <div className="ig-vacio-tarjeta" role="alert">
          <strong>No se pudieron cargar los hilos</strong>
          <p>{estado.mensaje}</p>
          <button className="ignis-btn" onClick={cargar}>
            Reintentar
          </button>
        </div>
      ) : estado.hilos.length === 0 ? (
        <div className="ig-vacio-tarjeta" role="status">
          <strong>Todavía no hay hilos</strong>
          <p>Escribe a IGNIS en Atención o crea un hilo nuevo.</p>
        </div>
      ) : (
        <div className="ig-tabla-contenedor">
          <table className="ig-tabla">
            <caption className="sr">Hilos de la sesión, del más reciente al más antiguo</caption>
            <thead>
              <tr>
                <th scope="col">Título</th>
                <th scope="col">Turnos</th>
                <th scope="col">Última ruta</th>
                <th scope="col">Actualizado</th>
                <th scope="col">
                  <span className="sr">Acción</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {estado.hilos.map((h) => (
                <tr key={h.thread_id} aria-current={h.thread_id === hilo ? "true" : undefined}>
                  <td>
                    <span className="ig-hilo-titulo">{h.titulo || "(sin mensajes)"}</span>
                    <code className="ig-hilo-id">{h.thread_id}</code>
                  </td>
                  <td className="numero">{h.turnos}</td>
                  <td>{h.ultima_ruta ? etiquetaRuta(h.ultima_ruta) : "—"}</td>
                  <td>{fecha(h.actualizado)}</td>
                  <td>
                    <button className="ignis-btn" onClick={() => reabrir(h.thread_id)} aria-label={`Reabrir el hilo ${h.titulo || h.thread_id}`}>
                      <Icono nombre="historial" tamano={16} /> Reabrir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
