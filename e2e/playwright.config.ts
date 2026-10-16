import { defineConfig, devices } from '@playwright/test';

// Base URL of the stack under test (nginx reverse proxy).
// In CI it is injected via the E2E_BASE_URL env var, locally defaults to :80.
const baseURL = process.env.E2E_BASE_URL?.trim() || 'http://localhost:80';

export default defineConfig({
  testDir: './tests',
  timeout: 180 * 1000,
  expect: {
    timeout: 60 * 1000,
  },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  outputDir: 'test-results',
  use: {
    baseURL,
    headless: true,
    // Every test produces screenshots: explicit page.screenshot() calls
    // store into screenshots/, this flag additionally captures failures.
    screenshot: 'on',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
