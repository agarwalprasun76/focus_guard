import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig(({ command }) => ({
    plugins: [react()],
    // In packaged/runtime mode the admin SPA is mounted at /admin.
    // Keep dev server root path unchanged for local frontend development.
    base: command === "build" ? "/admin/" : "/",
    server: {
        host: "127.0.0.1",
        port: 5173,
    },
    test: {
        environment: "jsdom",
        setupFiles: ["./src/test/setup.ts"],
        globals: true,
        css: true,
        exclude: [
            "**/node_modules/**",
            "**/dist/**",
            "**/e2e/**",
            "**/*.spec.ts",
        ],
    },
}));
