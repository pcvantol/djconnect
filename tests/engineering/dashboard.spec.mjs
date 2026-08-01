import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { test, expect } from "@playwright/test";

const repository = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const dashboardUrl = "http://127.0.0.1:8876";
let dashboard;

async function waitForDashboard() {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      if ((await fetch(`${dashboardUrl}/api/health`)).ok) return;
    } catch {
      // The local dashboard process is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Engineering Status did not become healthy in time.");
}

test.beforeAll(async () => {
  dashboard = spawn(
    "python3",
    [
      "-c",
      'from pathlib import Path; from tools.engineering.dashboard import DashboardHTTPServer, handler; DashboardHTTPServer(("127.0.0.1", 8876), handler(Path(".").resolve())).serve_forever()',
    ],
    { cwd: repository, stdio: "ignore" },
  );
  await waitForDashboard();
});

test.afterAll(() => {
  dashboard?.kill("SIGTERM");
});

test.describe("Engineering Status browser smoke", () => {
  test.use({ viewport: { width: 390, height: 844 }, colorScheme: "dark", locale: "nl-NL", reducedMotion: "reduce" });

  test("exposes the structured Engineering Platform health projection", async ({ request }) => {
    const response = await request.get(`${dashboardUrl}/health`);
    expect([200, 503]).toContain(response.status());

    const health = await response.json();
    expect(health).toEqual(expect.objectContaining({
      health: health.healthy ? "ok" : "degraded",
      healthy: expect.any(Boolean),
      components: expect.objectContaining({
        dashboard: expect.objectContaining({ healthy: true, state: "running" }),
        inbox_watcher: expect.objectContaining({ healthy: expect.any(Boolean) }),
        dashboard_relay: expect.objectContaining({ healthy: expect.any(Boolean) }),
        status_storage: expect.objectContaining({ healthy: expect.any(Boolean) }),
        private_remote_access: expect.objectContaining({ healthy: expect.any(Boolean) }),
      }),
    }));
  });

  test("shows the private dashboard and keeps completed work collapsed by default", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await expect(page.getByTestId("engineering-dashboard-title")).toHaveText("Engineering Status");
    await expect(page.getByTestId("dashboard-splash")).toBeHidden();
    await expect(page.locator("#dashboardFavicon")).toHaveAttribute("href", /^data:image\/svg\+xml,/);
    await expect(page.getByTestId("engineering-workspace")).not.toHaveAttribute("open", "");
    await expect(page.locator(".current-run__category-description")).toHaveText("De actieve engineeringprompt, met actuele voortgang, uitvoeringstijd en uitvoeringscontext.");
    expect(await page.locator("#indicator").evaluate((element) => element.parentElement.className)).toBe("current-run__prompt-heading");
    await expect(page.locator("#loadComponentLogs")).toHaveCount(0);
    await expect(page.getByTestId("pull-refresh")).toHaveText("Trek omlaag om te vernieuwen");
    await page.evaluate(() => executionTelemetry([{ date: "2026-08-01", prompt_count: 1, average_execution_seconds: 10, average_total_execution_seconds: 12, average_queue_wait_seconds: 2, input_tokens: 100, output_tokens: 20, total_tokens: 120, complete_count: 1, blocked_count: 0, failed_count: 0 }]));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
    await expect(page.locator("#componentLogControls")).not.toHaveAttribute("hidden", "");
    expect(await page.locator("#reportContent").evaluate((element) => element.parentElement.className)).toBe("markdown-copy-wrap");
    expect(await page.locator("#reportAnalysisContent").evaluate((element) => element.parentElement.className)).toBe("markdown-copy-wrap");
    await expect(page.locator("#copyReport")).toHaveClass(/copy--glyph/);
    await expect(page.locator("#copyReport")).toHaveText("⧉");
    expect(await page.locator("#lastFinalStatus").evaluate((element) => element.previousElementSibling.id)).toBe("lastIndicator");
    await page.evaluate(() => lastExecutionTime({ seconds: 75, total_seconds: 125 }));
    await expect(page.locator("#lastExecutionTimeValue")).toHaveText("1 min 15 sec");
    await expect(page.locator("#lastTotalExecutionTimeValue")).toHaveText("2 min 5 sec");
    await page.evaluate(() => {
      const target = document.getElementById("reportContent");
      target.replaceChildren();
      renderMarkdownAnswer(target, "# Rapporttitel\n\n- eerste bevinding\n- **belangrijk bewijs**");
    });
    await expect(page.locator("#reportContent h3")).toHaveText("Rapporttitel");
    await expect(page.locator("#reportContent li")).toHaveCount(2);
    await expect(page.locator("#reportContent strong")).toHaveText("belangrijk bewijs");

    const lastExecution = page.getByTestId("last-executed-prompt-category");
    await page.evaluate(() => {
      document.getElementById("lastExecutionGroup").hidden = false;
      document.querySelector('[data-testid="last-executed-prompt-category"]').hidden = false;
    });
    const categorySummary = lastExecution.locator(":scope > summary");
    await expect(categorySummary).toContainText("Laatst uitgevoerde prompt");
    await expect(lastExecution).not.toHaveAttribute("open", "");
    await expect(lastExecution).toHaveCSS("row-gap", "0px");
    await categorySummary.click();
    await expect(lastExecution).toHaveAttribute("open", "");
  });

  test("sorts the two component-log tables independently", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    const tables = page.locator(".log-table");
    await expect(tables).toHaveCount(2);

    const inboxLevel = tables.nth(0).locator('th[data-sort-key="level"]');
    const dashboardLevel = tables.nth(1).locator('th[data-sort-key="level"]');
    const dashboardTimestamp = tables.nth(1).locator('th[data-sort-key="timestamp"]');

    await inboxLevel.click();
    await expect(inboxLevel).toHaveAttribute("aria-sort", "ascending");
    await expect(dashboardLevel).toHaveAttribute("aria-sort", "none");
    await expect(dashboardTimestamp).toHaveAttribute("aria-sort", "descending");

    await dashboardLevel.click();
    await expect(dashboardLevel).toHaveAttribute("aria-sort", "ascending");
    await expect(inboxLevel).toHaveAttribute("aria-sort", "ascending");
  });

  test("asks for confirmation before clearing each component log", async ({ page }) => {
    await page.route("**/api/logs/inbox", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({ contentType: "application/json", body: '{"cleared":"inbox"}' });
        return;
      }
      await route.fulfill({ contentType: "text/plain", body: "" });
    });
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    page.once("dialog", async (dialog) => {
      expect(dialog.type()).toBe("confirm");
      await dialog.accept();
    });
    await page.getByTestId("clear-inbox-log").click();
    await expect(page.getByTestId("clear-dashboard-log")).toBeVisible();
  });

  test("shows the iPhone pull-to-refresh threshold", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => updatePullRefresh(72));
    await expect(page.getByTestId("pull-refresh")).toHaveText("Laat los om te vernieuwen");
    await expect(page.getByTestId("pull-refresh")).toHaveClass(/pull-refresh--visible/);
  });
});
