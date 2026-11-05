export function PasoAPaso({ pasos, actual }: { pasos: string[]; actual: number }) {
  return (
    <section className="panel" aria-label="Mecanismo paso a paso">
      <h3>Mecanismo paso a paso</h3>
      <ol className="pasos" aria-label="Secuencia del mecanismo">
        {pasos.map((p, i) => (
          <li key={p} className={i === actual ? "actual" : undefined} aria-current={i === actual ? "step" : undefined}>
            {p}
          </li>
        ))}
      </ol>
    </section>
  );
}
