/** FAQ de Fanalca: respuestas precalculadas con citas (faq_visor.json) y pregunta en vivo. Autónoma: carga sus datos. */
import { useEffect, useState } from "react";
import { apiMoto, type FaqVisor, type RespuestaQa } from "../../api";
import { FaqFanalca } from "../panelesMoto";

export function FaqFanalcaAuto() {
  const [datos, setDatos] = useState<FaqVisor | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [falta, setFalta] = useState(false);
  const [enVivo, setEnVivo] = useState<{ respuesta: RespuestaQa | null; error: string | null; consultando: boolean }>({ respuesta: null, error: null, consultando: false });
  useEffect(() => {
    apiMoto.faqVisor().then(setDatos, (e: Error) => {
      if (e.message.startsWith("HTTP 404")) setFalta(true);
      else setError(e.message);
    });
  }, []);
  const preguntar = (pregunta: string) => {
    setEnVivo({ respuesta: null, error: null, consultando: true });
    apiMoto.qa(pregunta).then(
      (r) => setEnVivo({ respuesta: r, error: null, consultando: false }),
      (e: Error) => setEnVivo({ respuesta: null, error: e.message, consultando: false }),
    );
  };
  return <FaqFanalca datos={datos} error={error} faltaArchivo={falta} enVivo={enVivo} alPreguntar={preguntar} />;
}
