import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
// English-only content — the latin subset covers it, so we skip the
// cyrillic/greek/vietnamese/latin-ext subsets fontsource ships by default.
import "@fontsource/ibm-plex-mono/latin-500.css";
import "@fontsource/ibm-plex-mono/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-700.css";
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "./styles/orange.css";
import "./styles/app.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
