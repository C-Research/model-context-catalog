import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base must match the path mcc/routes.py mounts the built assets under.
export default defineConfig({
  base: "/ui/",
  plugins: [react()],
  build: {
    outDir: "dist",
  },
});
