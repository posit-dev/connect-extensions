import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "dist",
    rollupOptions: {
      input: {
        index: "index.html",
        sandbox: "sandbox.html",
      },
    },
  },
});
