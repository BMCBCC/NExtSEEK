import { defineConfig, devices } from "@playwright/test";

const useRealBackend = !!process.env.USE_REAL_BACKEND;

const frontendServer = {
  command: "npm run dev",
  url: "http://localhost:5173",
  reuseExistingServer: !process.env.CI,
};

// The standalone shell keeps its chat input disabled until VITE_API_BASE_URL,
// VITE_API_USER and VITE_API_PASS are all set (src/hooks/useAuth.ts). The mock
// project answers every request itself (e2e/fixtures/ws-mock.ts), so it starts
// the dev server with placeholders: nothing real is needed, a real .env is
// overridden for the run (Vite lets the process environment win over .env), and
// a request the mocks miss fails to resolve mock.invalid instead of leaving the
// machine. A dev server already listening on 5173 is reused as it was started.
const mockServer = {
  ...frontendServer,
  env: {
    VITE_API_BASE_URL: "http://mock.invalid",
    VITE_API_USER: "mock",
    VITE_API_PASS: "mock",
  },
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "mock",
      use: { ...devices["Desktop Chrome"] },
      testIgnore: "**/real-backend/**",
    },
    ...(useRealBackend
      ? [
          {
            name: "real-standalone",
            testDir: "./e2e/real-backend",
            testMatch: "test-case-1-standalone.spec.ts",
            use: {
              ...devices["Desktop Chrome"],
              baseURL: "http://localhost:5173",
            },
            timeout: 120_000,
          },
          {
            name: "real-embedded",
            testDir: "./e2e/real-backend",
            testMatch: /.*-embedded\.spec\.ts/,
            use: {
              ...devices["Desktop Chrome"],
              baseURL: "https://nextseek-dev.mit.edu",
              ignoreHTTPSErrors: true,
            },
            timeout: 120_000,
          },
        ]
      : []),
  ],
  webServer: useRealBackend ? frontendServer : mockServer,
});
