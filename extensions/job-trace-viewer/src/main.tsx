import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./components/agent-prism/theme/theme.css";
import "./index.css";
import App from "./App";

const rootEl = document.getElementById("root");
if (!rootEl) throw new Error("No #root element found");

createRoot(rootEl).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
