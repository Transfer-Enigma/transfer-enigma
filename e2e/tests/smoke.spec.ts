import { expect, test } from '@playwright/test';
import type { Locator, Page } from '@playwright/test';

import { loginAsAdmin } from './auth';

// All selectors prefer data-testid, gracefully falling back to visible text.
// The frontends currently have no data-testid attributes, so the text
// fallback is what actually matches today; testids win once they are added.
function byTestIdOrText(page: Page, testId: string, fallback: Locator): Locator {
  return page.getByTestId(testId).or(fallback);
}

async function shot(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
}

test('home: calculator page opens', async ({ page }) => {
  // Anonymous visitors are bounced to /login, so authenticate first.
  await loginAsAdmin(page);
  await page.goto('/');
  const heading = byTestIdOrText(
    page,
    'calculator-title',
    page.getByRole('heading', { name: /калькулятор маршрутов/i }),
  );
  await expect(heading.first()).toBeVisible();
  await shot(page, 'smoke-home');
});

test('demo: broken UID shows 404', async ({ page }) => {
  await page.goto('/demo/e2e-broken-uid-0000');
  const notFound = byTestIdOrText(
    page,
    'not-found-page',
    page.getByRole('heading', { name: /^404$/ }),
  );
  await expect(notFound.first()).toBeVisible();
  await expect(page.getByText(/страница не найдена/i).first()).toBeVisible();
  await shot(page, 'smoke-404');
});

test('admin: login page opens', async ({ page }) => {
  await page.goto('/admin/login');
  const loginForm = byTestIdOrText(
    page,
    'login-form',
    page.locator('input[type="password"]').or(page.getByRole('button', { name: /войти/i })),
  );
  await expect(loginForm.first()).toBeVisible();
  await shot(page, 'smoke-admin-login');
});
