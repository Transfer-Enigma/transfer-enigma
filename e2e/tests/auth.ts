import { expect } from '@playwright/test';
import type { Page } from '@playwright/test';

// Credentials mirror the CI fallbacks in project-e2e.yml
// (ADMIN_LOGIN/ADMIN_PASSWORD or e2e_admin/e2e_admin_pass).
export function adminCreds(): { login: string; password: string } {
  return {
    login: process.env.E2E_ADMIN_LOGIN?.trim() || 'e2e_admin',
    password: process.env.E2E_ADMIN_PASSWORD?.trim() || 'e2e_admin_pass',
  };
}

// The calculator (both `/` UI and `/api/v2/*`) requires auth: anonymous
// visitors are bounced to the login page. Log in via the UI form so the
// browser context (page + page.request) carries the JWT cookies.
export async function loginAsAdmin(page: Page): Promise<void> {
  const { login, password } = adminCreds();
  await page.goto('/login');
  await page.locator('input[name="login"]').fill(login);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole('button', { name: /войти/i }).click();
  await expect(page.getByRole('heading', { name: /калькулятор маршрутов/i }).first()).toBeVisible({
    timeout: 60 * 1000,
  });
}
