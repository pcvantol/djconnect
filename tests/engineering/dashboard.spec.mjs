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
    expect(health.components.dashboard.version).toMatch(/^\d+\.\d+\.\d+$/);
    expect(health.components.inbox_watcher.version).toMatch(/^\d+\.\d+\.\d+$/);

    const favicon = await request.get(`${dashboardUrl}/assets/engineering-status-icon.svg`);
    expect(favicon.status()).toBe(200);
    expect(favicon.headers()["content-type"]).toContain("image/svg+xml");
    const homescreenIcon = await request.get(`${dashboardUrl}/assets/engineering-status-icon-180.png`);
    expect(homescreenIcon.status()).toBe(200);
    expect(homescreenIcon.headers()["content-type"]).toContain("image/png");
  });

  test("shows the private dashboard and keeps completed work collapsed by default", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    // This test intentionally mutates projected state below.  Freeze the
    // client-side projection first so a legitimate SSE update cannot replace
    // that deterministic fixture midway through the assertions.
    await page.locator("#autoRefresh").uncheck();
    await expect(page.getByTestId("engineering-dashboard-title")).toHaveText("Engineering Status");
    await expect(page.getByTestId("dashboard-splash")).toBeHidden();
    await expect(page.locator("#dashboardFavicon")).toHaveAttribute("href", "/assets/engineering-status-icon.svg");
    await expect(page.locator('link[rel="apple-touch-icon"]')).toHaveAttribute("href", "/assets/engineering-status-icon-180.png");
    await expect(page.getByTestId("dashboard-app-icon")).toHaveAttribute("src", "/assets/engineering-status-icon.svg");
    await expect(page.getByTestId("engineering-workspace")).not.toHaveAttribute("open", "");
    await expect(page.getByTestId("engineering-inbox-queue")).not.toHaveAttribute("open", "");
    await expect(page.getByTestId("platform-health")).not.toHaveAttribute("open", "");
    await expect(page.locator("#queueItems > summary .category-icon")).toHaveText("☷");
    await expect(page.locator("#workspaceCard > summary .category-icon")).toHaveText("⌂");
    await expect(page.locator("#rateLimits > summary .category-icon")).toHaveText("◔");
    await expect(page.locator("#componentLogs > summary .category-icon")).toHaveText("≡");
    await expect(page.locator("#codexChat > summary .category-icon")).toHaveText("✦");
    for (const selector of ["#workspaceCard > summary", "#queueItems > summary", "#rateLimits > summary", "#componentLogs > summary", "#codexChat > summary"]) {
      expect(await page.locator(selector).evaluate((summary) => getComputedStyle(summary, "::before").right)).toBe("0px");
    }
    await expect(page.locator(".current-run__category-description")).toHaveText("De actieve engineeringprompt, met actuele voortgang, uitvoeringstijd en uitvoeringscontext.");
    expect(await page.locator("#indicator").evaluate((element) => element.parentElement.className)).toBe("current-run__prompt-heading");
    await expect(page.locator("#loadComponentLogs")).toHaveCount(0);
    await expect(page.getByTestId("pull-refresh")).toHaveText("Trek omlaag om te vernieuwen");
    await page.evaluate(() => showCopyToast());
    await expect(page.getByTestId("copy-toast")).toHaveText("Gekopieerd naar klembord");
    await expect(page.getByTestId("copy-toast")).toHaveClass(/copy-toast--visible/);
    const collapsedCategoryHeights = await page.evaluate(() => [
      "workspaceCard", "platformHealth", "codexChat", "technicalDetails", "componentLogs",
    ].map((id) => document.getElementById(id).getBoundingClientRect().height));
    expect(Math.max(...collapsedCategoryHeights) - Math.min(...collapsedCategoryHeights)).toBeLessThan(1);
    await page.evaluate(() => executionTelemetry([{ date: "2026-08-01", prompt_count: 1, average_execution_seconds: 10, average_total_execution_seconds: 12, average_queue_wait_seconds: 2, input_tokens: 100, output_tokens: 20, total_tokens: 120, complete_count: 1, blocked_count: 0, failed_count: 0 }]));
    expect(await page.evaluate(() => [
      document.getElementById("technicalDetails").nextElementSibling.id,
      document.getElementById("executionTelemetry").nextElementSibling.id,
      document.getElementById("platformHealth").nextElementSibling.id,
    ])).toEqual(["executionTelemetry", "platformHealth", "componentLogs"]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
    expect(await page.evaluate(() => {
      const mainCategory = document.getElementById("componentLogs");
      const nestedCard = mainCategory.querySelector(".card");
      const widths = (element) => {
        const style = getComputedStyle(element);
        return [style.borderTopWidth, style.borderRightWidth, style.borderBottomWidth, style.borderLeftWidth];
      };
      return { main: widths(mainCategory), nested: widths(nestedCard) };
    })).toEqual({
      main: ["2px", "2px", "2px", "2px"],
      nested: ["1px", "1px", "1px", "1px"],
    });
    await expect(page.locator("#componentLogControls")).not.toHaveAttribute("hidden", "");
    expect(await page.locator("#reportContent").evaluate((element) => element.parentElement.className)).toBe("markdown-copy-wrap");
    expect(await page.locator("#reportAnalysisContent").evaluate((element) => element.parentElement.className)).toBe("markdown-copy-wrap");
    await expect(page.locator("#copyReport")).toHaveClass(/copy--glyph/);
    await expect(page.locator("#copyReport")).toHaveText("⧉");
    await expect(page.locator("#copyReport")).toHaveAttribute("hidden", "");
    await expect(page.locator("#copyReportAnalysis")).toHaveAttribute("hidden", "");
    expect(await page.locator("#lastFinalStatus").evaluate((element) => element.previousElementSibling.id)).toBe("lastIndicator");
    await page.evaluate(() => lastExecutionTime({ seconds: 75, total_seconds: 125, finished_at: "2026-08-01T10:01:30Z" }));
    await expect(page.locator("#lastExecutionFinishedAtValue")).toHaveText("zaterdag 1 augustus 2026 om 12:01:30");
    await expect(page.locator("#lastExecutionTimeValue")).toHaveText("1 min 15 sec");
    await expect(page.locator("#lastTotalExecutionTimeValue")).toHaveText("2 min 5 sec");
    await page.evaluate(() => lastRuntimeMetadata({
      runtime_provider: "codex_cli",
      model: "gpt-5.6-terra",
      reasoning_profile: "medium",
      configuration_profile: "sandbox: workspace-write",
      codex_cli_version: "0.146.0",
    }));
    await expect(page.locator("#lastRuntimeProviderValue")).toHaveText("codex_cli");
    await expect(page.locator("#lastModelValue")).toHaveText("gpt-5.6-terra");
    await expect(page.locator("#lastReasoningProfileValue")).toHaveText("medium");
    await expect(page.locator("#lastConfigurationProfileValue")).toHaveText("sandbox: workspace-write");
    await expect(page.locator("#lastCodexCliVersionValue")).toHaveText("0.146.0");
    await page.evaluate(() => lastRuntimeMetadata({ runtime_provider: "codex_cli" }));
    await expect(page.locator("#lastModel")).toHaveAttribute("hidden", "");
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
      document.getElementById("promptRuns").hidden = false;
      document.getElementById("lastExecutionGroup").hidden = false;
      document.querySelector('[data-testid="last-executed-prompt-category"]').hidden = false;
    });
    const categorySummary = lastExecution.locator(":scope > summary");
    await expect(categorySummary).toContainText("Laatst uitgevoerde prompt");
    await expect(lastExecution).not.toHaveAttribute("open", "");
    await expect(lastExecution).toHaveCSS("row-gap", "0px");
    await lastExecution.evaluate((element) => { element.open = true; });
    await expect(lastExecution).toHaveAttribute("open", "");

    const sendButton = page.locator("#chatSend");
    await expect(sendButton).toHaveCSS("background-color", "rgb(52, 40, 63)");
    await expect(sendButton).toHaveCSS("border-bottom-left-radius", "8px");
    expect(await sendButton.evaluate((button) => {
      const style = getComputedStyle(button);
      return { bottom: style.bottom, right: style.right };
    })).toEqual({ bottom: "10px", right: "10px" });
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

  test("opens and closes all visible dashboard categories with the title-bar switch", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    const toggle = page.getByTestId("toggle-all-sections");
    await expect(toggle).toHaveAttribute("role", "switch");
    await expect(toggle).toHaveAttribute("aria-checked", "false");
    await expect(toggle).toHaveAttribute("aria-label", "Alle secties openen");

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-checked", "true");
    await expect(toggle).toHaveAttribute("aria-label", "Alle secties sluiten");
    for (const id of ["workspaceCard", "platformHealth", "codexChat", "technicalDetails", "componentLogs"]) {
      await expect(page.locator(`#${id}`)).toHaveAttribute("open", "");
    }

    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(toggle).toHaveAttribute("aria-checked", "true");
    await expect(page.locator("#workspaceCard")).toHaveAttribute("open", "");

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-checked", "false");
    for (const id of ["workspaceCard", "platformHealth", "codexChat", "technicalDetails", "componentLogs"]) {
      await expect(page.locator(`#${id}`)).not.toHaveAttribute("open", "");
    }
  });

  test("parses each newline-delimited JSON log entry separately", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const entries = await page.evaluate(() => structuredLogEntries(
      '{"timestamp":"2026-08-01T10:00:00+00:00","level":"INFO","event":"first"}\n'
      + '{"timestamp":"2026-08-01T10:01:00+00:00","level":"WARNING","event":"second"}',
    ));
    expect(entries).toHaveLength(2);
    expect(entries.map((entry) => entry.event)).toEqual(["first", "second"]);
    expect(entries.map((entry) => entry.level)).toEqual(["INFO", "WARNING"]);
  });

  test("keeps the Inbox queue visible when empty and numbers the oldest prompt first", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    const queue = page.getByTestId("engineering-inbox-queue");
    await page.evaluate(() => queueItems([], 0));
    await expect(queue).toBeVisible();
    await expect(queue).not.toHaveAttribute("open", "");
    await expect(queue.locator("summary")).toContainText("Inbox-wachtrij");
    await expect(queue.locator(".category-description")).toHaveText("Prompts in uitvoervolgorde: oudste eerst. Ook een lege wachtrij blijft zichtbaar.");
    await queue.locator("summary").click();
    await expect(page.locator("#queueSummary")).toHaveText("0 prompts in de wachtrij.");
    await expect(page.locator("#queueList")).toContainText("Geen Inbox-prompts wachten op uitvoering.");

    await page.evaluate(() => queueItems([
      { filename: "later.md", title: "Later uitvoeren", modified_at: "2026-08-02T10:02:00Z" },
      { filename: "earlier.md", title: "Eerst uitvoeren", modified_at: "2026-08-02T10:01:00Z" },
    ], 2));
    const entries = page.locator("#queueList .queue-item");
    await expect(entries).toHaveCount(2);
    await expect(entries.nth(0)).toContainText("1");
    await expect(entries.nth(0)).toContainText("Eerst uitvoeren");
    await expect(entries.nth(0)).toContainText("Bestandsnaam: earlier.md");
    await expect(entries.nth(0)).toHaveAttribute("aria-label", "Positie 1: Eerst uitvoeren");
    await expect(entries.nth(1)).toContainText("Later uitvoeren");
    await expect(page.locator("#queueSummary")).toHaveText("2 prompts in uitvoervolgorde: oudste eerst.");
  });

  test("renders provider limit rows on separate lines", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    await page.evaluate(() => rateLimits({
      windows: [{ label: "Weekvenster", used_percent: 24, resets_at: 0 }],
      reset_credits: 2,
    }));
    await expect(page.locator("#rateLimitDetails")).toHaveText(/Weekvenster: 76% beschikbaar.*Beschikbare resets: 2/s);
    expect(await page.locator("#rateLimitDetails").evaluate((element) => element.textContent)).toContain("\n");
  });

  test("keeps dashboard view preferences in the browser", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const autoRefresh = page.locator("#autoRefresh");
    await expect(autoRefresh).toBeChecked();
    await page.locator("#technicalDetails > summary").click();
    await page.locator("#autoRefresh").uncheck();
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(autoRefresh).not.toBeChecked();
    await expect(page.locator("#technicalDetails")).toHaveAttribute("open", "");
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
