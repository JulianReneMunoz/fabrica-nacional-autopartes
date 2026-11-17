import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

const contenedor = document.getElementById("raiz");
if (contenedor) {
  createRoot(contenedor).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
