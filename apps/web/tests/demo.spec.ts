import { test, expect, type Page } from "@playwright/test";
import { mkdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const demoPath = resolve(process.cwd(), "../../demo/solutions");
const screenshots = resolve(process.cwd(), "../../output/playwright");

async function startAnalysis(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Load demo example" }).click();
  await expect(page.getByLabel("Resume text", { exact: true })).toHaveValue(/Maya Chen/);
  await page.getByRole("button", { name: "Analyze evidence" }).click();
  await expect(page).toHaveURL(/\/readiness$/);
}

async function enterQuery(page: Page, filename: string) {
  const editor = page.getByRole("textbox", { name: /^SQL editor for/ });
  await page.evaluate((sql) => navigator.clipboard.writeText(sql), readFileSync(resolve(demoPath, filename), "utf8"));
  await editor.focus();
  await editor.press("ControlOrMeta+A");
  await editor.press("ControlOrMeta+V");
}

async function submit(page: Page, points: string) {
  await page.getByRole("button", { name: "Submit for evaluation" }).click();
  await expect(page.locator(".submission-section h3")).toHaveText(points);
  await expect(page.getByRole("button", { name: "Submit for evaluation" })).toBeEnabled();
}

test("real SQL demo works without external network and updates evidence after retries", async ({ page, context }) => {
  const external: string[] = [];
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (["http:", "https:"].includes(url.protocol) && url.origin !== "http://127.0.0.1:3100") {
      external.push(url.href);
      return route.abort();
    }
    return route.continue();
  });
  mkdirSync(screenshots, { recursive: true });
  await startAnalysis(page);
  const sqlRow = page.locator(".requirement-row").filter({ has: page.getByRole("heading", { name: "SQL relational querying", exact: true }) });
  await expect(sqlRow).toContainText("Not yet verified");
  await expect(page.locator(".mode-chip")).toHaveText("Demo analysis · real SQL");
  await page.screenshot({ path: resolve(screenshots, "evidence-before.png"), fullPage: true, animations: "disabled" });
  await page.getByRole("button", { name: "Start graded assessment" }).click();
  await enterQuery(page, "t1.sql");
  await page.getByRole("button", { name: "Run preview" }).click();
  await expect(page.locator(".data-table tbody tr")).not.toHaveCount(0);
  await submit(page, "35 / 35 points");
  await page.getByRole("button", { name: "Next task" }).click();
  await enterQuery(page, "t2.sql");
  await submit(page, "25 / 25 points");
  await page.getByRole("link", { name: "View results", exact: true }).click();
  const aggregation = page.locator(".competency-row").filter({ hasText: "Aggregation" });
  await expect(aggregation).toContainText("15 / 25");
  await expect(aggregation).toContainText("Partially demonstrated");
  await page.getByRole("link", { name: "Project workspace", exact: true }).click();
  await page.getByRole("button", { name: /Correct net revenue after refunds/ }).click();
  await enterQuery(page, "t3-naive.sql");
  await page.getByRole("button", { name: "Submit for evaluation" }).click();
  await expect(page.locator(".submission-section .feedback-mark.failed")).not.toHaveCount(0);
  await expect(page.locator(".submission-section h3")).not.toHaveText("40 / 40 points");
  await expect(page.getByRole("button", { name: "Submit for evaluation" })).toBeEnabled();
  await page.screenshot({ path: resolve(screenshots, "assessment-failed.png"), fullPage: true, animations: "disabled" });
  await enterQuery(page, "t3.sql");
  await submit(page, "40 / 40 points");
  await page.getByRole("link", { name: "View results", exact: true }).click();
  await expect(page.locator(".score-plate strong")).toHaveText("100 / 100");
  await expect(aggregation).toContainText("25 / 25");
  await expect(page.locator(".competency-row").filter({ hasText: "Refund edge cases" })).toContainText("30 / 30");
  await expect(page.locator(".trail-row").filter({ hasText: "SQL relational querying" })).toContainText("Demonstrated on project");
  await page.screenshot({ path: resolve(screenshots, "evidence-after.png"), fullPage: true, animations: "disabled" });
  await page.locator(".evidence-trail").screenshot({ path: resolve(screenshots, "evidence-trail.png"), animations: "disabled" });

  // A later failed attempt must replace the passing result and downgrade evidence.
  await page.getByRole("link", { name: "Project workspace", exact: true }).click();
  await page.getByRole("button", { name: /Correct net revenue after refunds/ }).click();
  await enterQuery(page, "t3-naive.sql");
  await page.getByRole("button", { name: "Submit for evaluation" }).click();
  await expect(page.locator(".submission-section h3")).not.toHaveText("40 / 40 points");
  await expect(page.getByRole("button", { name: "Submit for evaluation" })).toBeEnabled();
  await page.getByRole("link", { name: "View results", exact: true }).click();
  await expect(page.locator(".score-plate strong")).not.toHaveText("100 / 100");
  await expect(aggregation).toContainText("Partially demonstrated");

  await page.getByRole("link", { name: "Full evidence map", exact: true }).click();
  await expect(sqlRow).toContainText("Partially demonstrated");
  await page.getByRole("link", { name: "Reset session", exact: true }).click();
  await expect(page.getByLabel("Resume text", { exact: true })).toHaveValue("");
  await page.reload();
  await expect(page.getByLabel("Resume text", { exact: true })).toHaveValue("");
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
});

test("an unavailable backend explains how to recover, then demo loading can retry", async ({ page }) => {
  await page.goto("/");
  await page.route("**/api/demo/fixture", (route) => route.fulfill({ status: 500, body: "Internal Server Error" }));
  await page.getByRole("button", { name: "Load demo example" }).click();
  await expect(page.locator('.form-error[role="alert"]')).toContainText("Start both servers with npm run demo");
  await page.unroute("**/api/demo/fixture");
  await page.getByRole("button", { name: "Load demo example" }).click();
  await expect(page.getByLabel("Resume text", { exact: true })).toHaveValue(/Maya Chen/);
});
