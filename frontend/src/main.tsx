import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/schibsted-grotesk/400.css";
import "@fontsource/schibsted-grotesk/500.css";
import "@fontsource/schibsted-grotesk/600.css";
import "@fontsource/schibsted-grotesk/700.css";
import App from "./App";
import "./index.css";

const racine = document.getElementById("root");
if (!racine) throw new Error("Élément #root introuvable");
createRoot(racine).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
