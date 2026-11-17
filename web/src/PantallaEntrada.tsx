/**
 * Pantalla de entrada con alias (ADR-033). Demo académica sin contraseña: el alias se convierte en el servidor en
 * un `user_id` seudónimo y solo viaja en la cookie cifrada del propio usuario.
 */
import { useState, type FormEvent } from "react";
import { useIgnis } from "./ignisContexto";
import { Icono } from "./IgnisIconos";
import { validarAlias } from "./ignisSesion";

export default function PantallaEntrada({ aviso }: { aviso?: string }) {
  const { entrar } = useIgnis();
  const [alias, setAlias] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    const problema = validarAlias(alias);
    if (problema) {
      setError(problema);
      return;
    }
    setEnviando(true);
    setError("");
    try {
      await entrar(alias.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setEnviando(false);
    }
  };

  const mensaje = error || aviso || "";
  return (
    <div className="ig-entrada">
      <form className="ig-entrada-tarjeta" onSubmit={enviar} noValidate aria-labelledby="ig-entrada-titulo">
        <span className="ig-entrada-icono" aria-hidden="true">
          <Icono nombre="auto" tamano={28} />
        </span>
        <h1 id="ig-entrada-titulo">Entrar a IGNIS</h1>
        <p className="ig-entrada-texto">
          Elige un alias para guardar tus hilos y preferencias. Es una demo académica sin contraseña.
        </p>
        <label htmlFor="ig-alias">Alias</label>
        <input
          id="ig-alias"
          className="ignis-input"
          value={alias}
          onChange={(e) => setAlias(e.target.value)}
          maxLength={32}
          autoComplete="off"
          spellCheck={false}
          placeholder="por ejemplo: compras-01"
          aria-describedby="ig-alias-ayuda ig-alias-error"
          aria-invalid={error ? true : undefined}
        />
        <small id="ig-alias-ayuda">
          De 3 a 32 letras, números o guiones. No uses tu nombre, correo ni teléfono (Ley 1581 de 2012).
        </small>
        <p id="ig-alias-error" className="ig-entrada-error" role="alert">
          {mensaje}
        </p>
        <button type="submit" className="ignis-btn primario" disabled={enviando || !alias.trim()}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
