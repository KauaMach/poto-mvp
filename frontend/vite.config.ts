import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],

  // A aplicação é servida na RAIZ pelo FastAPI (http://RaspPoto.local:8000/).
  //
  // "/" e não "./": com base relativa, a rota /painel/ (com barra final)
  // resolveria os assets para /painel/assets/… e quebraria. Como servimos
  // sempre da raiz, o caminho absoluto funciona em qualquer rota.
  base: "/",

  server: {
    port: 5173,
    proxy: {
      // Em desenvolvimento o front roda na 5173 e o backend na 8000.
      // Em produção não há proxy: o próprio backend serve os dois.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: true, // /api/v1/ws — o painel em tempo real
      },
    },
  },

  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
