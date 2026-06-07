import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function getVendorChunkName(id: string) {
  if (!id.includes("node_modules")) {
    return;
  }

  const marker = "node_modules/";
  const modulePath = id.slice(id.lastIndexOf(marker) + marker.length);
  const parts = modulePath.split("/");
  const packageName = parts[0].startsWith("@") ? `${parts[0]}/${parts[1]}` : parts[0];

  if (
    packageName === "react" ||
    packageName === "react-dom" ||
    packageName === "react-router" ||
    packageName === "react-router-dom" ||
    packageName === "@remix-run/router" ||
    packageName === "scheduler"
  ) {
    return "react-vendor";
  }
  if (packageName === "dayjs") {
    return "dayjs-vendor";
  }
  if (packageName === "json2mq" || packageName === "string-convert") {
    return;
  }
  return `vendor-${packageName.replace("@", "").replace("/", "-")}`;
}

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          return getVendorChunkName(id);
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 4173,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
});
