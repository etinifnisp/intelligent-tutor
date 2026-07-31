import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173',
    headless: true,
    trace: 'on-first-retry',
  },
  webServer: process.env.E2E_SKIP_SERVER
    ? undefined
    : [
        {
          command: 'cd ../backend ; python app.py',
          url: 'http://127.0.0.1:8000/health/live',
          reuseExistingServer: true,
          timeout: 120_000,
        },
        {
          command: 'npm run dev',
          url: 'http://127.0.0.1:5173',
          reuseExistingServer: true,
          timeout: 60_000,
        },
      ],
});
