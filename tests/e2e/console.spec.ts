import { expect, test } from '../../apps/web/node_modules/@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

function password() {
  if (process.env.ROADEYE_DEMO_PASSWORD) return process.env.ROADEYE_DEMO_PASSWORD;
  const env = fs.readFileSync(path.resolve('../../.env'), 'utf8');
  return env.match(/^ROADEYE_DEMO_PASSWORD=(.+)$/m)![1];
}

test('console drives actual backend through normal journey and evidence', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await page.getByLabel('Local password').fill(password());
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('button', { name: 'Scenario runner', exact: true }).click();
  await page.getByLabel('Scenario', { exact: true }).selectOption('normal_journey');
  await page.getByRole('button', { name: 'Create run', exact: true }).click();
  await expect(page.getByLabel('Selected run')).not.toHaveValue('');
  await page.getByRole('button', { name: 'play', exact: true }).click();
  await expect(page.getByRole('cell', { name: 'delivered', exact: true })).toBeVisible({ timeout: 30000 });
  await expect(page.getByRole('cell', { name: '{"done":18}', exact: true })).toBeVisible({ timeout: 30000 });
  await page.getByRole('button', { name: 'Observation inspector', exact: true }).click();
  await expect(page.getByRole('cell', { name: 'ZZ01AA0001', exact: true })).toHaveCount(3);
  await page.getByLabel('Inspect observation').selectOption({ index: 1 });
  await expect(page.getByRole('heading', { name: 'Machine decision: accepted' })).toBeVisible();
  const evidence = page.getByRole('link', { name: 'Open supporting synthetic evidence' });
  const content = await page.request.get((await evidence.getAttribute('href'))!);
  expect(content.status()).toBe(200);
  expect(await content.text()).toContain('SYNTHETIC EVIDENCE');
  await page.getByRole('button', { name: 'Trajectory explorer', exact: true }).click();
  await page.getByRole('button', { name: 'Reconstruct journey' }).click();
  await expect(page.getByRole('heading', { name: 'Observed camera sightings' })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'plausible', exact: true })).toHaveCount(2);
  await page.getByRole('button', { name: 'Analytics', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Travel time and congestion proxy' })).toBeVisible();
  await page.screenshot({ path: '/tmp/roadeye-console.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('viewer sees server permission denial and empty scope', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Local actor').selectOption('viewer');
  await page.getByLabel('Local password').fill(password());
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('button', { name: 'Observation inspector', exact: true }).click();
  await expect(page.getByText('No run selected. Create one in Scenario runner.')).toBeVisible();
  await page.getByLabel('Selected run').selectOption({ index: 1 });
  await expect(page.getByRole('alert').filter({ hasText: 'Permission denied' })).toBeVisible();
});
