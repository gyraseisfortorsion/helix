import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  workers: 1,
  reporter: "list",
  webServer: [
    {
      command:
        ".venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8001",
      cwd: "..",
      url: "http://127.0.0.1:8001/api/health",
      env: {
        ANTHROPIC_API_KEY: "",
        ALPHAGENOME_API_KEY: "",
        EVO2_BASE_URL: "",
        EVO2_FORWARD_URL: "",
        DNA_ACCESS_KEY: "",
        DNA_ALLOW_LOCAL_WORKSPACES: "true",
        DNA_DATA_DIR: "data/e2e",
        PYDANTIC_AI_NO_BANNER: "1",
      },
    },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      env: { VITE_API_PROXY_TARGET: "http://127.0.0.1:8001" },
    },
  ],
});
