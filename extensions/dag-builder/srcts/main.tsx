import { createRoot } from "react-dom/client";
import DAGBuilder from "./DAGBuilder";
import "./styles.css";

const container = document.getElementById("root");
if (container) {
  const root = createRoot(container);
  root.render(<DAGBuilder />);
} else {
  console.error("Could not find root element to mount React component.");
}
