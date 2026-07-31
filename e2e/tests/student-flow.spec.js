import { test, expect } from '@playwright/test';

test.describe('Student learning flow', () => {
  test('loads Today page and navigates to Practice', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Today' })).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: 'Start Practice Session' }).click();
    await expect(page.getByRole('heading', { name: 'Practice' })).toBeVisible();
  });

  test('Practice page shows question workspace', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Practice' }).click();
    await expect(page.getByRole('heading', { name: 'Practice' })).toBeVisible();
    await expect(page.getByText('How confident are you?')).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('button', { name: 'Hint 1' })).toBeVisible();
  });

  test('Ask Tutor page loads chat interface', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Ask Tutor' }).click();
    await expect(page.getByText('Ask Tutor')).toBeVisible();
    await expect(page.getByPlaceholder(/Ask any JEE question/)).toBeVisible();
  });

  test('Progress page loads stats', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Progress' }).click();
    await expect(page.getByRole('heading', { name: 'Progress' })).toBeVisible();
    await expect(page.getByText('Total attempts')).toBeVisible({ timeout: 15_000 });
  });
});
