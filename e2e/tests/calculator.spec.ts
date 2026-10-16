import { expect, test } from '@playwright/test';
import type { Locator, Page } from '@playwright/test';

import { loginAsAdmin } from './auth';

// End-to-end route calculation on synthetic seed data (see e2e/seed.sql):
//   E2E Alpha -> E2E Gamma, direct RAIL segment, container size 20.
// Flow: log in via UI (page + page.request share the browser context, so the
// JWT cookies apply to API calls too), then departures/destinations/calculate
// via API, then the same selection via UI query params (the calculator
// auto-calculates when all params are present) and assert that the routes
// list renders.

interface GroupedPoint {
  ids: number[];
  external_ids: string[];
  translates: Record<string, { name: string; country: string } | null>;
}

function byTestIdOrText(page: Page, testId: string, fallback: Locator): Locator {
  return page.getByTestId(testId).or(fallback);
}

async function shot(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: `screenshots/${name}.png`, fullPage: true });
}

function findPointId(points: GroupedPoint[], needle: string): number | undefined {
  for (const p of points) {
    const names = Object.values(p.translates ?? {})
      .map((t) => t?.name ?? '')
      .join(' ');
    if (names.toLowerCase().includes(needle.toLowerCase()) && (p.ids?.length ?? 0) > 0)
      return p.ids[0];
  }
  return undefined;
}

const dispatchDate = new Date().toISOString().slice(0, 10);

test('calculator: API selection + route calculation + UI render', async ({ page }) => {
  await loginAsAdmin(page);
  // Shares cookies with the page, unlike the standalone `request` fixture.
  const api = page.request;

  // 1. Departure points via API.
  const depRes = await api.get(`/api/v2/points/departures?date=${dispatchDate}`);
  expect(depRes.ok()).toBeTruthy();
  const depBody = await depRes.json();
  const departures: GroupedPoint[] = depBody.data ?? [];
  expect(departures.length).toBeGreaterThan(0);

  const fromId = findPointId(departures, 'Alpha') ?? departures[0]?.ids?.[0];
  expect(fromId).toBeDefined();

  // 2. Destination points via API for the chosen departure.
  const destRes = await api.get(
    `/api/v2/points/destinations?date=${dispatchDate}&departure_point_ids=I${fromId}`,
  );
  expect(destRes.ok()).toBeTruthy();
  const destBody = await destRes.json();
  const destinations: GroupedPoint[] = destBody.data ?? [];
  expect(destinations.length).toBeGreaterThan(0);

  const toId = findPointId(destinations, 'Gamma') ?? destinations.find((d) => d.ids?.[0] !== fromId)?.ids?.[0];
  expect(toId).toBeDefined();

  // 3. Route calculation via API.
  const calcRes = await api.post('/api/v2/routes/calculate', {
    data: {
      dispatchDate,
      departureInternalIds: [fromId],
      destinationInternalIds: [toId],
      departureExternalIds: [],
      destinationExternalIds: [],
      cargoWeight: 10000,
      containerType: 20,
      headTruck: false,
      tailTruck: false,
    },
  });
  expect(calcRes.ok()).toBeTruthy();
  const calcBody = await calcRes.json();
  expect(Array.isArray(calcBody.routes)).toBeTruthy();
  expect(calcBody.routes.length).toBeGreaterThan(0);

  // 4. Same selection through the UI: query params trigger auto-calculation.
  await page.goto(
    `/?date=${dispatchDate}&departureIds=I${fromId}&destinationIds=I${toId}&type=20&weight=10000&currency=RUB`,
  );
  const heading = byTestIdOrText(
    page,
    'calculator-title',
    page.getByRole('heading', { name: /калькулятор маршрутов/i }),
  );
  await expect(heading.first()).toBeVisible();
  await shot(page, 'calculator-form');

  // 5. Routes list renders: the results block appears only when routes exist
  // (v-if on routes.length), and it must contain our synthetic seed data.
  // A generic class-only selector would be vacuous here, so assert content.
  const routesBlock = page.locator('#results-direct');
  await expect(routesBlock.first()).toBeVisible({ timeout: 120 * 1000 });
  // Scope to the results block: the same company name also occurs in the
  // (hidden) point-autocomplete dropdown above the form.
  await expect(routesBlock.getByText(/E2E Rail Line/).first()).toBeVisible();
  await shot(page, 'calculator-routes');
});
