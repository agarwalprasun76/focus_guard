import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

/** Dashboard hero heading (Phase A5 date presets; not a literal "Dashboard" `<h1>`). */
export async function expectDashboardHeroVisible(page: Page) {
  await expect(
    page.getByRole("heading", {
      name: /Today's Focus|Yesterday's Focus|Focus Summary/,
    })
  ).toBeVisible();
}
