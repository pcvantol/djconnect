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

  test("places the active prompt category first", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await expect(
      page.locator("#engineering-dashboard-content").evaluate(
        (dashboard) => dashboard.firstElementChild?.id,
      ),
    ).resolves.toBe("currentRun");
  });

  test("uses prompt history rather than a hidden last-executed prompt card", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    for (const selector of [
      "#promptRuns",
      "#lastExecutionGroup",
      "#lastExecution",
      "#report",
      "#reportAnalysis",
    ])
      await expect(page.locator(selector)).toHaveCount(0);
    await expect(page.locator("#promptHistoryDetailModal")).toHaveCount(1);
  });

  test("shows the refresh timestamp in the bottom status bar", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await expect(page.locator("#currentTime")).toHaveCount(0);
    await expect(page.locator(".footer #lastRefresh")).toContainText(
      "Laatst bijgewerkt:",
    );
    await expect(page.locator(".footer #updateMode")).toContainText(
      "Serverpush:",
    );
  });

  test("uses the selected locale service for copy and date formatting", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#dashboardLocale").selectOption("de");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    await expect(page.locator(".footer #lastRefresh")).toContainText("Zuletzt aktualisiert:");
    await expect(page.locator("#dashboardLocale option:checked")).toHaveText("Deutsch");
  });

  test("changes visible interface copy for each supported language", async ({ page }) => {
    const expectations = [
      ["en", "Language", "Refresh automatically", "AI analysis", "Passed", "Execution"],
      ["nl", "Taal", "Automatisch vernieuwen", "AI-analyse", "Geslaagd", "Uitvoering"],
      ["de", "Sprache", "Automatisch aktualisieren", "KI-Analyse", "Erfolgreich", "Ausführung"],
      ["fr", "Langue", "Actualiser automatiquement", "Analyse IA", "Réussi", "Exécution"],
      ["es", "Idioma", "Actualizar automáticamente", "Análisis de IA", "Superado", "Ejecución"],
    ];

    for (const [language, localeLabel, refreshLabel, analysisLabel, passLabel, detailTitle] of expectations) {
      await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
      await page.locator("#dashboardLocale").selectOption(language);
      await expect(page.locator("html")).toHaveAttribute("lang", language);
      await expect(page.locator(".dashboard-locale span")).toHaveText(localeLabel);
      await expect(page.locator(".auto-refresh-toggle span")).toHaveText(refreshLabel);
      await expect(page.locator("#promptHistoryAnalysisHeader")).toHaveText(analysisLabel);
      expect(await page.evaluate(() => enumLabel("PASS"))).toBe(passLabel);
      await page.evaluate(() => renderPromptHistoryDetail({
        history: { run_id: "inbox-localization", status: "COMPLETE", title: "Prompt", executed_at: "2026-08-03T20:53:29Z" },
      }));
      await expect(page.locator("#promptHistoryDetailContent h3").first()).toHaveText(detailTitle);
    }
  });

  test("formats preflight timestamps through the selected dashboard locale", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    expect(await page.evaluate(() => [
      formatTimestamp("2026-08-03T20:53:29.203403+00:00"),
      formatTimestamp("2026-08-03T20:53:29.354948+00:00"),
    ])).toEqual([
      "maandag 3 augustus 2026 om 22:53:29",
      "maandag 3 augustus 2026 om 22:53:29",
    ]);
  });

  test("localizes capability preflight recommendations", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    expect(await page.evaluate(() => capabilityRecommendation("Capability admission passed."))).toBe(
      "Capabilitytoelating geslaagd.",
    );
    expect(await page.evaluate(() => capabilityRecommendation(
      "Repair or upgrade the Execution Host before resubmitting.",
    ))).toBe("Herstel of upgrade de Execution Host voordat je opnieuw indient.");
  });

  test("renders preflight enums as localized labels", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    expect(await page.evaluate(() => [
      enumLabel("PASS"),
      enumLabel("RETRYABLE"),
      enumLabel("RETRYABLE_AFTER_HOST_REPAIR"),
      enumLabel("CAPABILITY"),
    ])).toEqual([
      "Geslaagd",
      "Opnieuw proberen mogelijk",
      "Opnieuw proberen na herstel van de Execution Host",
      "Capability",
    ]);
  });

  test("keeps the status bar at the bottom while dashboard content scrolls", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#engineering-dashboard-content").evaluate((content) => {
      content.style.minHeight = "2000px";
    });
    const layout = await page.evaluate(() => {
      const region = document.querySelector(".dashboard-scroll-region");
      const footer = document.querySelector(".footer");
      region.scrollTop = 160;
      return {
        bodyOverflow: getComputedStyle(document.body).overflowY,
        regionOverflow: getComputedStyle(region).overflowY,
        regionScrolled: region.scrollTop > 0,
        footerBottom: Math.round(footer.getBoundingClientRect().bottom),
        viewportBottom: window.innerHeight,
      };
    });
    expect(layout.bodyOverflow).toBe("hidden");
    expect(layout.regionOverflow).toBe("auto");
    expect(layout.regionScrolled).toBe(true);
    expect(layout.footerBottom).toBeLessThanOrEqual(layout.viewportBottom);
  });

  test("labels the splash screen as loading data", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await expect(page.locator(".dashboard-splash__loading")).toHaveText("Gegevens laden…");
    await expect(page.locator(".dashboard-splash__version")).toHaveCSS("color", "rgb(240, 182, 106)");
    await expect(page.locator(".dashboard-splash__spinner")).toHaveCSS("border-top-color", "rgb(240, 182, 106)");
  });

  test("loads the initial status before serverpush connects", async ({ page }) => {
    await page.route("**/api/events", (route) => route.abort());
    await page.route("**/api/dashboard-snapshot", (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        status: {
          watcher_state: "WATCHER_IDLE",
          platform_version: "1.5.0",
          queue_depth: 0,
          queue_items: [],
        },
        rate_limits: {
          provider: "Codex CLI",
          provider_version: "0.146.0",
          windows: [],
          reset_credits: 0,
        },
        component_versions: {},
      }),
    }));
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });

    await expect(page.locator("#platformVersion")).toHaveText("1.5.0");
    await expect(page.locator("#queueSummary")).not.toHaveText("Wachtrij laden…");
    await expect(page.locator("#queueSummary")).toHaveText("0 prompts in de wachtrij.");
    await expect(page.locator("#rateLimits")).toBeVisible();
    await expect(page.locator("#rateLimitProvider")).toHaveText("Codex CLI · 0.146.0");
    await expect(page.locator("#rateLimitDetails")).toHaveCSS("font-size", "14px");
  });

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
      }),
    }));
    expect(health.components.dashboard.version).toMatch(/^\d+\.\d+\.\d+$/);
    expect(health.components.inbox_watcher.version).toMatch(/^\d+\.\d+\.\d+$/);
    expect(health.components.dashboard.uptime_seconds).toEqual(expect.any(Number));
    expect(health.components.inbox_watcher).toHaveProperty("uptime_seconds");
    expect(health.components.dashboard_relay).toHaveProperty("uptime_seconds");
    expect(health.components).not.toHaveProperty("private_remote_access");

    const favicon = await request.get(`${dashboardUrl}/assets/engineering-status-icon.svg`);
    expect(favicon.status()).toBe(200);
    expect(favicon.headers()["content-type"]).toContain("image/svg+xml");
    const homescreenIcon = await request.get(`${dashboardUrl}/assets/engineering-status-icon-180.png`);
    expect(homescreenIcon.status()).toBe(200);
    expect(homescreenIcon.headers()["content-type"]).toContain("image/png");
    const stylesheet = await request.get(`${dashboardUrl}/assets/dashboard.css`);
    expect(stylesheet.status()).toBe(200);
    expect(stylesheet.headers()["content-type"]).toContain("text/css");
    const script = await request.get(`${dashboardUrl}/assets/dashboard.js`);
    expect(script.status()).toBe(200);
    expect(script.headers()["content-type"]).toContain("text/javascript");
    const locales = await request.get(`${dashboardUrl}/assets/dashboard_locales.mjs`);
    expect(locales.status()).toBe(200);
    expect(locales.headers()["content-type"]).toContain("text/javascript");
    const statusStore = await request.get(`${dashboardUrl}/assets/dashboard_status_store.mjs`);
    expect(statusStore.status()).toBe(200);
    expect(statusStore.headers()["content-type"]).toContain("text/javascript");
  });

  test("shows uptime only for locally owned processes", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    await page.evaluate(() => renderPlatformHealth({ components: {
      dashboard: { healthy: true, detail: "HTTP-dashboard reageert", version: "1.2.82", uptime_seconds: 3725 },
      inbox_watcher: { healthy: true, detail: "LaunchAgent is geladen", version: "1.1.4", uptime_seconds: 75 },
    }}));

    const componentText = await page.locator("#platformHealthComponents").textContent();
    expect(componentText).toContain("Uptime 1u 2m");
    expect(componentText).toContain("Uptime 1m");
    expect(componentText).not.toContain("Statusopslag");
  });

  test("centres component information actions and balances component-card text padding", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#platformHealth").evaluate((element) => { element.open = true; });
    await page.evaluate(() => renderPlatformHealth({ components: {
      dashboard: { healthy: true, detail: "HTTP-dashboard reageert", version: "1.2.87", uptime_seconds: 1440 },
    }}));

    const alignment = await page.locator(".platform-health__component").evaluate((card) => {
      const box = card.getBoundingClientRect();
      const name = card.querySelector(".platform-health__component-name").getBoundingClientRect();
      const detail = card.querySelector(".platform-health__component-detail").getBoundingClientRect();
      const info = card.querySelector(".component-info").getBoundingClientRect();
      return {
        infoCentreOffset: Math.abs((info.top + info.height / 2) - (box.top + box.height / 2)),
        paddingDifference: Math.abs((name.top - box.top) - (box.bottom - detail.bottom)),
      };
    });

    expect(alignment.infoCentreOffset).toBeLessThan(1);
    expect(alignment.paddingDifference).toBeLessThan(1);
    await expect(page.locator(".platform-health__component").first()).toHaveAttribute("role", "button");
    await expect(page.locator(".platform-health__component").first()).toHaveAttribute("tabindex", "0");
  });

  test("uses a green hover fill for component information actions", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#dashboardSplash").evaluate((element) => { element.hidden = true; });
    await page.locator("#platformHealth").evaluate((element) => { element.open = true; });
    await page.evaluate(() => renderPlatformHealth({ components: {
      dashboard: { healthy: true, detail: "HTTP-dashboard reageert", version: "1.2.87" },
    }}));
    const info = page.locator(".platform-health .component-info").first();

    await expect(info).toHaveCSS("min-height", "32px");
    await expect(info).toHaveCSS("min-width", "32px");
    await info.hover();
    await expect(info).toHaveCSS("background-color", "rgb(163, 230, 53)");
    await expect(info).toHaveCSS("color", "rgb(24, 35, 15)");
  });

  test("uses the execution host title for the core local component", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => showComponentModal({
      component: "inbox_watcher",
      healthy: true,
      detail: "connected",
      git_commit: "host-only-commit",
      processes: [{ pid: 123, memory_kib: 1024 }],
      launchd: {},
    }));

    const modal = page.locator("#componentModal");
    await expect(modal).toContainText("Engineering Execution Host");
  });

  test("renders the safe current Codex activity from the live status projection", async ({ page }) => {
    await page.route("**/api/events", (route) => route.abort());
    await page.route("**/api/dashboard-snapshot", (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ status: { watcher_state: "WATCHER_IDLE" } }),
    }));
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await expect(page.locator("#platformVersion")).toHaveText("Niet beschikbaar");
    // Keep the fixture authoritative: a delayed initial SSE snapshot must not
    // overwrite this intentionally projected active run.
    await page.locator("#autoRefresh").uncheck();
    await page.evaluate(() => r({
      watcher_state: "ENGINEERING_RUN_ACTIVE",
      current_phase: "EXECUTE_AGENT",
      current_action: "Codex bewerkt bestanden",
      run_id: "activity-run",
      prompt_title: "Veilige voortgang",
      submitted_filename: "activity.md",
    }, {}));

    await expect(page.locator("#currentRun")).toBeVisible();
    await expect(page.locator("#action")).toHaveText("Codex bewerkt bestanden");
  });

  test("refines the active duration indication with comparable runtime history", async ({ page }) => {
    await page.route("**/api/events", (route) => route.abort());
    await page.route("**/api/dashboard-snapshot", (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ status: { watcher_state: "WATCHER_IDLE" } }),
    }));
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    await page.evaluate(() => r({
      watcher_state: "ENGINEERING_RUN_ACTIVE",
      current_phase: "EXECUTE_AGENT",
      run_id: "duration-run",
      prompt_characters: 1000,
    }, {
      duration_estimate: {
        sample_count: 3,
        lower_seconds: 1800,
        upper_seconds: 2400,
      },
    }));

    await expect(page.locator("#executionEstimate")).toHaveText("Indicatieve totale duur: 22–30 minuten");
    await expect(page.locator("#executionEstimateMeta")).toContainText(
      "3 vergelijkbare voltooide uitvoeringen",
    );
  });

  test("keeps the active prompt category visible for a blocked predecessor", async ({ page }) => {
    await page.route("**/api/events", (route) => route.abort());
    await page.route("**/api/dashboard-snapshot", (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ status: { watcher_state: "WATCHER_IDLE" } }),
    }));
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await expect(page.locator("#platformVersion")).toHaveText("Niet beschikbaar");
    await page.locator("#autoRefresh").uncheck();
    await page.evaluate(() => r({
      watcher_state: "WATCHER_IDLE",
      current_phase: "BLOCKED",
      current_action: "Wacht op een herstelde voorganger.",
      prompt_title: "Geblokkeerde voorganger",
      submitted_filename: "blocked.md",
      blocking_predecessor_run: "blocked-run",
      blocking_predecessor_title: "Geblokkeerde voorganger",
      blocking_predecessor_phase: "BLOCKED",
      predecessor_recovery_action: "Dien de herstelde prompt opnieuw in.",
    }, {}));

    await expect(page.locator("#currentRun")).toBeVisible();
    await expect(page.locator("#currentRun")).toHaveAttribute("open", "");
    await expect(page.locator("#predecessorGate")).toBeVisible();
    await expect(page.locator("#predecessorRun")).toHaveText("blocked-run");
  });

  test("keeps the active prompt category visible for a terminal blocked run", async ({ page }) => {
    await page.route("**/api/events", (route) => route.abort());
    await page.route("**/api/dashboard-snapshot", (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ status: { watcher_state: "WATCHER_IDLE" } }),
    }));
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await expect(page.locator("#platformVersion")).toHaveText("Niet beschikbaar");
    await page.evaluate(() => r({
      watcher_state: "WATCHER_IDLE",
      prompt_title: "Geblokkeerde prompt",
      submitted_filename: "blocked.md",
      last_executed_run: "blocked-run",
      last_executed_title: "Geblokkeerde prompt",
      last_executed_filename: "blocked.md",
      last_executed_phase: "BLOCKED",
    }, {}));

    await expect(page.locator("#currentRun")).toBeVisible();
    await expect(page.locator("#currentRun")).toHaveAttribute("open", "");
    await expect(page.locator("#phase")).toHaveText("Geblokkeerd");
    await expect(page.locator("#runId")).toHaveText("blocked-run");
    await expect(page.locator("#predecessorGate")).toBeHidden();
  });

  test("allows the AI question field to grow only vertically", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#codexChat").evaluate((element) => { element.open = true; });
    await expect(page.locator("#chatInput")).toHaveCSS("resize", "vertical");
  });

  test("bounds and sanitizes free-form dashboard input client-side", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await expect(page.locator("#chatInput")).toHaveAttribute("maxlength", "2000");
    await expect(page.locator("#promptHistoryFilter")).toHaveAttribute("maxlength", "160");
    await expect(page.locator("#logFilter")).toHaveAttribute("maxlength", "160");

    const values = await page.locator("#chatInput, #promptHistoryFilter").evaluateAll((inputs) => Object.fromEntries(inputs.map((input) => {
      input.value = input.id === "chatInput"
        ? `eerste\r\ntweede\u202E${"x".repeat(2100)}`
        : `zoek\u0000term\n${"x".repeat(200)}`;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      return [input.id, input.value];
    })));

    expect(values.chatInput).toHaveLength(2000);
    expect(values.chatInput).toContain("eerste\ntweede");
    expect(values.chatInput).not.toContain("\u202E");
    expect(values.promptHistoryFilter).toHaveLength(160);
    expect(values.promptHistoryFilter).toContain("zoekterm");
    expect(values.promptHistoryFilter).not.toContain("\u0000");
    expect(values.promptHistoryFilter).not.toContain("\n");
  });

  test("keeps platform health status text readable in light mode", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.getByTestId("theme-toggle").click();
    await page.evaluate(() => renderPlatformHealth({ components: {
      dashboard: { healthy: true, detail: "HTTP-dashboard reageert", version: "1.2.87" },
    }}));

    await expect(page.locator(".platform-health__component-detail")).toHaveCSS("color", "rgb(24, 34, 48)");
  });

  test("renders component details in the light modal theme", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.getByTestId("theme-toggle").click();
    await page.locator("#platformHealth").evaluate((element) => { element.open = true; });
    await expect(page.locator(".component-info").first()).toHaveCSS("color", "rgb(60, 116, 17)");
    await page.locator(".platform-health__component").first().click();

    await expect(page.locator("#componentModal")).toHaveAttribute("open", "");
    await expect(page.locator("#componentModal")).toBeFocused();
    await expect(page.locator(".component-modal__panel")).toHaveCSS("background-color", "rgb(255, 255, 255)");
    await expect(page.locator(".component-modal__panel")).toHaveCSS("color", "rgb(24, 34, 48)");
    await expect(page.locator("#componentModalTitle")).toHaveCSS("border-bottom-color", "rgb(163, 230, 53)");
    await expect(page.locator("#componentModalClose")).toHaveCSS("font-size", "18px");
    await expect(page.locator("#componentModalClose")).toHaveCSS("min-height", "32px");
    await expect(page.locator("#componentModalClose")).toHaveCSS("min-width", "32px");
  });

  test("uses a green hover fill for the component-detail close action", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => showComponentModal({
      component: "inbox_watcher",
      healthy: true,
      detail: "connected",
      launchd: {},
    }));
    const close = page.locator("#componentModalClose");

    await close.hover();
    await expect(close).toHaveCSS("background-color", "rgb(163, 230, 53)");
  });

  test("uses a green hover fill for the component restart action", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => showComponentModal({
      component: "dashboard",
      healthy: true,
      detail: "running",
      launchd: {},
      restart_supported: true,
    }));
    const restart = page.locator("#componentModalRestart");

    await restart.hover();
    await expect(restart).toHaveCSS("background-color", "rgb(163, 230, 53)");
    await expect(restart).toHaveCSS("color", "rgb(24, 35, 15)");
  });

  test("renders action-coloured confirmation dialogs as light surfaces in light mode", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.getByTestId("theme-toggle").click();
    await page.evaluate(() => showComponentModal({
      component: "dashboard",
      healthy: true,
      detail: "running",
      launchd: {},
      restart_supported: true,
    }));
    await page.locator("#componentModalRestart").click();

    await expect(page.locator("#confirmationModal")).toHaveAttribute("data-theme-mode", "light");
    await expect(page.locator(".confirmation-modal__panel")).toHaveCSS("background-color", "rgb(247, 251, 255)");
    await expect(page.locator(".confirmation-modal__panel")).toHaveCSS("color", "rgb(24, 34, 48)");
    await expect(page.locator("#confirmationModalText")).toHaveCSS("color", "rgb(24, 34, 48)");
    await expect(page.locator(".confirmation-modal__panel")).toHaveCSS("border-top-color", "rgb(163, 230, 53)");
    expect(await page.locator("#confirmationModalConfirm").evaluate((element) => getComputedStyle(element).backgroundColor)).not.toBe("rgb(163, 230, 53)");
    await expect(page.locator("#confirmationModalConfirm")).toHaveCSS("border-top-color", "rgb(163, 230, 53)");
    await page.locator("#confirmationModalCancel").hover();
    await expect(page.locator("#confirmationModalCancel")).toHaveCSS("background-color", "rgb(163, 230, 53)");
    await expect(page.locator("#confirmationModalCancel")).toHaveCSS("border-top-color", "rgb(163, 230, 53)");
    await page.locator("#confirmationModalConfirm").hover();
    await expect(page.locator("#confirmationModalConfirm")).toHaveCSS("background-color", "rgb(163, 230, 53)");
  });

  test("shows the splash screen before reloading the dashboard", async ({ page }) => {
    await page.route("**/api/components/dashboard/restart", (route) =>
      route.fulfill({ status: 202, json: { restarting: "dashboard" } }),
    );
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => showComponentModal({
      component: "dashboard",
      healthy: true,
      detail: "running",
      launchd: {},
      restart_supported: true,
    }));
    await page.locator("#componentModalRestart").click();
    await page.locator("#confirmationModalConfirm").click();

    await expect(page.getByTestId("dashboard-splash")).toBeVisible();
    await expect(page.locator("body")).not.toHaveClass(/dashboard-ready/);
  });

  test("refreshes uptime and memory while component details remain open", async ({ page }) => {
    let detailsRequest = 0;
    await page.route("**/api/components/dashboard/details", (route) => {
      detailsRequest += 1;
      return route.fulfill({ json: {
        component: "dashboard",
        healthy: true,
        detail: "HTTP-dashboard reageert",
        version: "1.2.87",
        uptime_seconds: detailsRequest === 1 ? 10 : 20,
        processes: [{ pid: 42, memory_kib: detailsRequest === 1 ? 1024 : 2048 }],
        launchd: {},
        restart_supported: true,
      } });
    });
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#platformHealth").evaluate((element) => { element.open = true; });
    await page.locator(".component-info").first().click();

    await expect(page.locator("#componentModalContent")).toContainText("Uptime10s");
    await expect(page.locator("#componentModalContent")).toContainText("PID 42: 1.0 MiB");
    await page.evaluate(() => refreshOpenComponentDetails());
    await expect(page.locator("#componentModalContent")).toContainText("Uptime20s");
    await expect(page.locator("#componentModalContent")).toContainText("PID 42: 2.0 MiB");

    await page.locator("#componentModalClose").click();
    await expect.poll(() => page.evaluate(() => componentDetailsRefreshTimer)).toBeNull();
  });

  test("renders prompt-history report actions as light surfaces in light mode", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#themeToggle").click();
    await page.evaluate(() => {
      document.querySelector("#promptHistoryReportModal").showModal();
      document.querySelector("#promptHistoryReportContent").textContent = "# Rapport\n\nInhoud";
      document.querySelector("#promptHistoryReportCopy").hidden = false;
      document.querySelector("#promptHistoryReportDownload").hidden = false;
    });
    for (const selector of ["#promptHistoryReportContent", "#promptHistoryReportCopy", "#promptHistoryReportDownload"]) {
      expect(await page.locator(selector).evaluate((element) => getComputedStyle(element).backgroundColor)).not.toBe("rgb(24, 24, 31)");
    }
    await expect(page.locator("#promptHistoryReportDownload")).toHaveText("⇩");
    expect(await page.locator("#promptHistoryReportDownload").evaluate((element) => getComputedStyle(element, "::before").content)).toContain("↓");
  });

  test("keeps report-modal actions and markdown code light in light mode", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#themeToggle").click();
    await page.evaluate(() => {
      document.querySelector("#promptHistoryReportModal").showModal();
      document.querySelector("#promptHistoryReportDownload").hidden = false;
      document.querySelector("#promptHistoryReportCopy").hidden = false;
      document.querySelector("#promptHistoryReportContent").innerHTML =
        "<p><code>inline code</code></p><pre>code block</pre>";
    });

    for (const selector of ["#promptHistoryReportDownload", "#promptHistoryReportCopy"]) {
      await expect(page.locator(selector)).toHaveCSS("background-color", "rgb(247, 251, 255)");
      await expect(page.locator(selector)).toHaveCSS("color", "rgb(28, 78, 104)");
    }
    for (const selector of ["#promptHistoryReportContent code", "#promptHistoryReportContent pre"])
      await expect(page.locator(selector)).toHaveCSS("background-color", "rgb(238, 244, 251)");
  });

  test("uses light glyphs for dark prompt-history report actions", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      document.querySelector("#promptHistoryReportModal").showModal();
      document.querySelector("#promptHistoryReportCopy").hidden = false;
      document.querySelector("#promptHistoryReportDownload").hidden = false;
    });
    const download = page.locator("#promptHistoryReportDownload");

    for (const action of [download, page.locator("#promptHistoryReportCopy")])
      await expect(action).toHaveCSS("color", "rgb(247, 243, 238)");
  });

  test("renders log actions in the light category style", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.getByTestId("theme-toggle").click();
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    await page.evaluate(() => renderLogPagination("inbox", 1, 1));

    await expect(page.getByTestId("clear-inbox-log")).toHaveText("⌫");
    await expect(page.getByTestId("clear-inbox-log")).toHaveCSS("background-color", "rgb(255, 248, 239)");
    await expect(page.getByTestId("download-inbox-log")).toHaveCSS("background-color", "rgb(255, 250, 244)");
    await expect(page.locator("#inboxLogPagination button").first()).toHaveCSS("background-color", "rgb(255, 243, 226)");
  });

  test("fills component-log actions orange on hover", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#dashboardSplash").evaluate((element) => { element.hidden = true; });
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    await page.evaluate(() => renderLogPagination("inbox", 1, 1));

    for (const action of [
      page.getByTestId("download-inbox-log"),
      page.getByTestId("download-dashboard-log"),
      page.getByTestId("clear-inbox-log"),
      page.getByTestId("clear-dashboard-log"),
    ]) {
      await action.hover();
      await expect(action).toHaveCSS("background-color", "rgb(240, 182, 106)");
      await expect(action).toHaveCSS("color", "rgb(32, 24, 18)");
    }
  });

  test("fills the historical report action red on hover", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#dashboardSplash").evaluate((element) => { element.hidden = true; });
    await page.locator("#promptHistory").evaluate((element) => { element.open = true; });
    await page.evaluate(() => {
      promptHistoryEntries = [{
        run_id: "report-hover",
        status: "COMPLETE",
        title: "Rapport hover",
        executed_at: "2026-08-02T10:00:00+00:00",
        git_commit: "abc1234",
        report_available: true,
      }];
      promptHistoryPage = 1;
      renderPromptHistory();
    });
    const report = page.locator('[title="Bekijk engineeringrapport voor Rapport hover"]');

    await report.hover();
    await expect(report).toHaveCSS("background-color", "rgb(255, 113, 143)");
    await expect(report).toHaveCSS("color", "rgb(39, 25, 35)");
  });

  test("downloads each redacted component log", async ({ page }) => {
    await page.route("**/api/logs/**", (route) => route.fulfill({ contentType: "application/x-ndjson", body: '{"level":"INFO","event":"test"}\n' }));
    await page.route("**/api/audit/user-action", (route) => route.fulfill({ contentType: "application/json", body: '{"logged":true}' }));
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#dashboardSplash").evaluate((element) => { element.hidden = true; });
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });

    await page.evaluate(() => {
      URL.createObjectURL = () => "blob:component-log";
      HTMLAnchorElement.prototype.click = function click() { window.__componentLogDownload = this.download; };
    });
    for (const [testId, filename] of [["download-inbox-log", "inbox-watcher-log-"], ["download-dashboard-log", "statusdashboard-log-"]]) {
      await page.getByTestId(testId).click();
      await expect.poll(() => page.evaluate(() => window.__componentLogDownload)).toMatch(new RegExp(`^${filename}.*\\.ndjson$`));
    }
  });

  test("uses the shared single-line circular border for download glyphs", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });

    for (const button of [
      page.locator("#downloadChat"),
      page.getByTestId("download-inbox-log"),
      page.getByTestId("download-dashboard-log"),
    ]) {
      await expect(button).toHaveCSS("border-top-width", "1px");
      await expect(button).toHaveCSS("border-top-style", "solid");
      await expect(button).toHaveCSS("border-top-left-radius", "50%");
    }
  });

  test("fills the chat download glyph with its purple category on hover", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#dashboardSplash").evaluate((element) => { element.hidden = true; });
    await page.locator("#codexChat").evaluate((element) => { element.open = true; });
    const download = page.locator("#downloadChat");
    await page.addStyleTag({ content: "#downloadChat[hidden]{display:flex!important}" });

    await download.hover();
    await expect(download).toHaveCSS("background-color", "rgb(208, 164, 255)");
    await expect(download).toHaveCSS("color", "rgb(23, 21, 26)");
  });

  test("fills the AI question send action with its purple category on hover", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#dashboardSplash").evaluate((element) => { element.hidden = true; });
    await page.locator("#codexChat").evaluate((element) => { element.open = true; });
    const send = page.locator("#chatSend");

    await send.hover();
    await expect(send).toHaveCSS("background-color", "rgb(208, 164, 255)");
    await expect(send).toHaveCSS("color", "rgb(23, 21, 26)");
    await send.evaluate((button) => { button.disabled = true; });
    await send.hover();
    await expect(send).toHaveCSS("background-color", "rgb(208, 164, 255)");
    await expect(send).toHaveCSS("color", "rgb(23, 21, 26)");
  });

  test("uses a light resting surface for the chat clear glyph in light mode", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.getByTestId("theme-toggle").click();
    await page.evaluate(() => {
      document.querySelector("#codexChat").open = true;
      document.querySelector("#clearChat").hidden = false;
    });
    const clear = page.locator("#clearChat");

    await expect(clear).toBeVisible();
    await expect(clear).toHaveCSS("background-color", "rgb(255, 247, 255)");
    await expect(clear).toHaveCSS("color", "rgb(104, 73, 138)");
    await page.evaluate(() => {
      chatMessage("user", "Eigen bericht");
      chatMessage("assistant", "AI-antwoord");
    });
    await expect(page.locator(".chat-message--user .chat-message__copy")).toHaveCSS("color", "rgb(28, 78, 104)");
    await expect(page.locator(".chat-message--assistant .chat-message__copy")).toHaveCSS("color", "rgb(104, 73, 138)");
  });

  test("uses matching orange iOS-style toggles in the title bar", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const theme = page.getByTestId("theme-toggle");
    const allSections = page.getByTestId("toggle-all-sections");
    const autoRefresh = page.locator("#autoRefresh");

    await expect(autoRefresh).toHaveAttribute("role", "switch");
    await expect(autoRefresh).toHaveCSS("background-color", "rgb(240, 182, 106)");
    await theme.click();
    await allSections.click();
    await page.waitForTimeout(250);
    for (const toggle of [theme, allSections]) {
      await expect(toggle).toHaveAttribute("aria-checked", "true");
      expect(await toggle.evaluate((element) => getComputedStyle(element, "::before").backgroundColor)).toBe("rgb(240, 182, 106)");
    }
  });

  test("keeps the platform version labels orange in both themes", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const platformLabel = page.locator(".footer .label").first();
    await expect(platformLabel).toHaveCSS("color", "rgb(240, 182, 106)");
    await page.getByTestId("theme-toggle").click();
    await expect(platformLabel).toHaveCSS("color", "rgb(240, 182, 106)");
  });

  test("uses the centralized house style for toast and shared controls", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const houseStyle = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--house-style").trim());
    expect(houseStyle).toBe("#f0b66a");

    await page.evaluate(() => showCopyToast());
    await expect(page.getByTestId("copy-toast")).toHaveCSS("border-color", "rgb(240, 182, 106)");
    await expect(page.locator("#autoRefresh")).toHaveCSS("background-color", "rgb(240, 182, 106)");
    await expect(page.locator(".rate-limit-reset")).toHaveCSS("border-color", "rgb(81, 216, 138)");
  });

  test("keeps the copy toast above an open report modal", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      document.querySelector("#promptHistoryReportModal").showModal();
      showCopyToast();
    });
    await expect(page.getByTestId("copy-toast")).toHaveClass(/copy-toast--visible/);
    await expect(page.getByTestId("copy-toast")).toBeVisible();
    expect(await page.getByTestId("copy-toast").evaluate(
      (toast) => toast.matches(":popover-open"),
    )).toBeTruthy();
  });

  test("pads title bar content evenly from both horizontal edges", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const padding = await page.locator(".dashboard-titlebar").evaluate((element) => {
      const style = getComputedStyle(element);
      return [style.paddingLeft, style.paddingRight, style.borderTopLeftRadius];
    });
    expect(padding).toEqual(["16px", "16px", "18px"]);
  });

  test("never renders a white focus ring on visible interactive elements", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      document.querySelectorAll("details").forEach((element) => { element.open = true; });
    });

    const violations = await page.evaluate(() => {
      const selector = [
        "button:not([disabled])",
        "input:not([disabled])",
        "select:not([disabled])",
        "textarea:not([disabled])",
        "summary",
        '[role="button"]:not([aria-disabled="true"])',
        "[tabindex]:not([tabindex='-1'])",
      ].join(",");
      const isVisible = (element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
      };
      const hasWhite = (value) => /rgb\(\s*(?:2[4-5]\d|255)\s*,\s*(?:2[4-5]\d|255)\s*,\s*(?:2[4-5]\d|255)\s*\)/.test(value);

      return ["dark", "light"].flatMap((theme) => {
        document.documentElement.dataset.theme = theme;
        return [...document.querySelectorAll(selector)].filter(isVisible).flatMap((element) => {
          element.focus({ preventScroll: true });
          const style = getComputedStyle(element);
          const focusStyles = `${style.outlineColor} ${style.boxShadow}`;
          return hasWhite(focusStyles) ? [{
            theme,
            element: element.id || element.getAttribute("data-testid") || element.tagName,
            focusStyles,
          }] : [];
        });
      });
    });

    expect(violations).toEqual([]);
  });

  test("keeps the skip-link dashboard target focusable without outlining all categories", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const content = page.locator("#engineering-dashboard-content");

    await content.focus();
    await expect(content).toBeFocused();
    await expect(content).toHaveCSS("outline-style", "none");
    await expect(content).toHaveCSS("box-shadow", "none");
  });

  test("keeps report-modal shell focusable without a visible selection ring", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const modal = page.locator("#promptHistoryReportModal");

    await modal.evaluate((element) => { element.showModal(); element.focus(); });
    await expect(modal).toBeFocused();
    await expect(modal).toHaveCSS("outline-style", "none");
    await expect(modal).toHaveCSS("box-shadow", "none");
  });

  test("keeps prompt-detail shell focusable without a visible selection ring", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const modal = page.locator("#promptHistoryDetailModal");

    await modal.evaluate((element) => { element.showModal(); element.focus(); });
    await expect(modal).toBeFocused();
    await expect(modal).toHaveCSS("outline-style", "none");
    await expect(modal).toHaveCSS("box-shadow", "none");
  });

  test("keeps prompt-chat shell focusable without a visible selection ring", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const modal = page.locator("#promptHistoryChatModal");

    await modal.evaluate((element) => { element.showModal(); element.focus(); });
    await expect(modal).toBeFocused();
    await expect(modal).toHaveCSS("outline-style", "none");
    await expect(modal).toHaveCSS("box-shadow", "none");
  });

  test("keeps the prompt-detail close action at the top right while scrolling", async ({ page }) => {
    await page.setViewportSize({ width: 720, height: 360 });
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const modal = page.locator("#promptHistoryDetailModal"),
      panel = modal.locator(".prompt-detail-modal__panel"),
      content = page.locator("#promptHistoryDetailContent"),
      header = modal.locator(".prompt-detail-modal__header"),
      close = page.locator("#promptHistoryDetailClose");

    await modal.evaluate((element) => {
      document.querySelector("#promptHistoryDetailContent").innerHTML =
        "<p>Detailregel</p>".repeat(120);
      element.showModal();
    });
    const before = {
      close: await close.boundingBox(),
      header: await header.boundingBox(),
    };
    await content.evaluate((element) => { element.scrollTop = 180; });
    const after = {
      close: await close.boundingBox(),
      header: await header.boundingBox(),
    }, panelBox = await panel.boundingBox();

    await expect.poll(() => content.evaluate((element) => element.scrollTop)).toBe(180);
    expect(after.close.y).toBe(before.close.y);
    expect(after.header.y).toBe(before.header.y);
    expect(after.close.x + after.close.width).toBeGreaterThan(panelBox.x + panelBox.width - 48);
  });

  test("uses light glyphs for all dark report-modal actions", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      document.querySelector("#promptHistoryReportModal").showModal();
      document.querySelector("#promptHistoryReportDownload").hidden = false;
      document.querySelector("#promptHistoryReportCopy").hidden = false;
    });
    const download = page.locator("#promptHistoryReportDownload");

    await download.hover();
    for (const action of [
      download,
      page.locator("#promptHistoryReportCopy"),
      page.locator("#promptHistoryReportClose"),
    ]) await expect(action).toHaveCSS("color", "rgb(247, 243, 238)");
    await expect(page.locator(".report-view-modal__header")).toHaveCSS("border-bottom-color", "rgb(141, 199, 255)");
    await expect(page.locator("#promptHistoryReportClose")).toHaveCSS("font-size", "18px");
  });

  test("keeps a long report modal inside a short viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 300 });
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const modal = page.locator("#promptHistoryReportModal");

    await modal.evaluate((element) => {
      document.querySelector("#promptHistoryReportContent").textContent = "Rapportregel\n".repeat(80);
      element.showModal();
    });
    const box = await modal.boundingBox();
    const panelBox = await modal.locator(".report-view-modal__panel").boundingBox();
    const actions = modal.locator(".report-view-modal__actions");
    const actionBoxBeforeScroll = await actions.boundingBox();
    const header = modal.locator(".report-view-modal__header");
    const content = modal.locator("#promptHistoryReportContent");
    const headerBox = await header.boundingBox();
    const contentBox = await content.boundingBox();
    await content.evaluate((element) => { element.scrollTop = 160; });
    const actionBoxAfterScroll = await actions.boundingBox();

    expect(box.y).toBeGreaterThanOrEqual(18);
    expect(box.y + box.height).toBeLessThanOrEqual(282);
    expect(panelBox.y).toBeGreaterThanOrEqual(18);
    expect(panelBox.y + panelBox.height).toBeLessThanOrEqual(282);
    expect(actionBoxBeforeScroll.x + actionBoxBeforeScroll.width).toBeGreaterThan(panelBox.x + panelBox.width - 44);
    expect(contentBox.y).toBeGreaterThanOrEqual(headerBox.y + headerBox.height);
    await expect.poll(() => content.evaluate((element) => element.scrollTop)).toBe(160);
    expect(actionBoxAfterScroll.y).toBe(actionBoxBeforeScroll.y);
  });

  test("marks every dashboard element with the active light or dark theme", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });

    for (const theme of ["dark", "light"]) {
      await page.evaluate((activeTheme) => applyDashboardTheme(activeTheme), theme);
      const violations = await page.evaluate((activeTheme) => [...document.querySelectorAll("body, body *")]
        .filter((element) => !["SCRIPT", "STYLE"].includes(element.tagName))
        .filter((element) => element.dataset.themeMode !== activeTheme)
        .map((element) => ({
          element: element.id || element.getAttribute("data-testid") || element.tagName,
          themeMode: element.dataset.themeMode || null,
        })), theme);
      expect(violations).toEqual([]);
    }
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
    expect(await page.getByTestId("engineering-workspace").evaluate((element) => element.parentElement.id)).toBe("engineering-dashboard-content");
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
      "platformHealth", "codexChat", "technicalDetails", "componentLogs",
    ].map((id) => document.getElementById(id).getBoundingClientRect().height));
    expect(Math.max(...collapsedCategoryHeights) - Math.min(...collapsedCategoryHeights)).toBeLessThan(1);
    await page.locator("#platformHealth").evaluate((element) => { element.open = true; });
    await expect(page.locator(".component-info").first()).toBeVisible();
    await page.locator(".component-info").first().click();
    await expect(page.locator("#componentModal")).toHaveAttribute("open", "");
    await expect(page.locator("#componentModalTitle")).not.toHaveText("Componentinformatie");
    await page.locator("#componentModalClose").click();
    await expect(page.locator("#componentModal")).not.toHaveAttribute("open", "");
    await page.evaluate(() => executionTelemetry([{ date: "2026-08-01", prompt_count: 1, average_execution_seconds: 10, average_total_execution_seconds: 12, average_queue_wait_seconds: 2, input_tokens: 100, output_tokens: 20, total_tokens: 120, complete_count: 1, blocked_count: 0, failed_count: 0 }]));
    await expect(page.locator("#executionTelemetryRows tr td").first()).toHaveText("01-08-2026");
    expect(await page.evaluate(() => [
      document.getElementById("technicalDetails").nextElementSibling.id,
      document.getElementById("workspaceCard").nextElementSibling.id,
      document.getElementById("executionTelemetry").nextElementSibling.id,
      document.getElementById("platformHealth").nextElementSibling.id,
    ])).toEqual(["workspaceCard", "executionTelemetry", "platformHealth", "componentLogs"]);
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
    const sendButton = page.locator("#chatSend");
    await expect(sendButton).toHaveCSS("background-color", "rgb(52, 40, 63)");
    await expect(sendButton).toHaveCSS("border-bottom-left-radius", "8px");
    expect(await sendButton.evaluate((button) => {
      const style = getComputedStyle(button);
      return { bottom: style.bottom, right: style.right };
    })).toEqual({ bottom: "10px", right: "10px" });
    await expect(page.locator("#downloadChat")).toHaveAttribute("hidden", "");
    await expect(page.locator("#codexChat > .category-description")).toHaveText("Stel korte, alleen-lezen vragen over de laatst uitgevoerde prompt en het bijbehorende rapport. Dit start geen engineering of wijzigingen.");
    await expect(page.locator("#codexChat .estimate-meta")).toHaveCount(0);
    await page.evaluate(() => {
      chatHistory = [{ role: "user", text: "Wat zijn de volgende stappen?" }];
      renderChatHistory();
    });
    await expect(page.locator("#downloadChat")).not.toHaveAttribute("hidden", "");
    await expect(page.locator("#downloadChat")).toHaveText("⇩");
    expect(await page.locator("#downloadChat").evaluate((element) => getComputedStyle(element).borderRadius)).toBe("50%");
    expect(await page.locator("#downloadChat").evaluate((element) => getComputedStyle(element, "::before").content)).toContain("↓");
    await page.evaluate(() => chatMessage("assistant", "Een antwoord."));
    expect(await page.locator(".chat-message--user .chat-message__body").evaluate((element) => getComputedStyle(element).fontFamily)).toBe(
      await page.locator(".chat-message--assistant .chat-message__body").evaluate((element) => getComputedStyle(element).fontFamily),
    );
    expect(await page.locator("#chatInput").evaluate((element) => getComputedStyle(element).fontFamily)).toBe(
      await page.locator(".chat-message--assistant .chat-message__body").evaluate((element) => getComputedStyle(element).fontFamily),
    );
    await expect(page.locator('label[for="chatInput"]')).toHaveCSS("margin-bottom", "10px");
    await expect(page.locator(".chat-message__copy")).toHaveCount(2);
    await expect(page.locator(".chat-message--assistant .chat-message__copy")).toHaveAttribute("aria-label", "Kopieer bericht");
    await page.locator("#codexChat").evaluate((element) => { element.open = true; });
    await page.locator(".chat-message--user .chat-message__copy").hover();
    await expect(page.locator(".chat-message--user .chat-message__copy")).toHaveCSS("background-color", "rgb(141, 199, 255)");
    await expect(page.locator(".chat-message--user .chat-message__copy")).toHaveCSS("color", "rgb(23, 21, 26)");
    await page.locator(".chat-message--assistant .chat-message__copy").hover();
    await expect(page.locator(".chat-message--assistant .chat-message__copy")).toHaveCSS("background-color", "rgb(208, 164, 255)");
    await expect(page.locator(".chat-message--assistant .chat-message__copy")).toHaveCSS("color", "rgb(23, 21, 26)");
    await page.evaluate(() => Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: () => Promise.resolve() },
    }));
    await page.locator(".chat-message--assistant .chat-message__copy").click();
    await expect(page.getByTestId("copy-toast")).toHaveText("Gekopieerd naar klembord");
    await expect(page.getByTestId("copy-toast")).toHaveClass(/copy-toast--visible/);
    expect(await page.evaluate(() => chatHistoryMarkdown())).toContain("## Jij\n\nWat zijn de volgende stappen?");
  });

  test("sorts the two component-log tables independently", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    const tables = page.locator("#componentLogs .log-table");
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

  test("paginates the two component-log tables independently", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    await page.locator("#autoRefresh").uncheck();
    await page.waitForFunction(() => componentLogsLoaded);
    await page.waitForTimeout(350);
    await page.evaluate(() => {
      refreshComponentLogs = async () => {};
      componentLogEntries.inbox = Array.from({ length: 51 }, (_, index) => ({
        line: index + 1,
        timestamp: `2026-08-02T00:${String(index).padStart(2, "0")}:00Z`,
        level: "INFO",
        event: `inbox_${index}`,
        runId: "—",
        details: "test",
      }));
      componentLogEntries.dashboard = Array.from({ length: 2 }, (_, index) => ({
        line: index + 1,
        timestamp: `2026-08-02T01:0${index}:00Z`,
        level: "INFO",
        event: `dashboard_${index}`,
        runId: "—",
        details: "test",
      }));
      independentLogPageStates.inbox = 1;
      independentLogPageStates.dashboard = 1;
      componentLogsLoaded = true;
      renderComponentLogs();
    });

    await expect(page.locator("#inboxComponentLog tr")).toHaveCount(50);
    await expect(page.locator("#inboxLogPagination")).toContainText("Pagina 1 van 2 · 51 regels");
    await expect(page.locator("#dashboardLogPagination")).toContainText("Pagina 1 van 1 · 2 regels");
    const previousInboxLogPage = page.locator("#inboxLogPagination").getByRole("button", { name: "Vorige" });
    await previousInboxLogPage.hover();
    await expect(previousInboxLogPage).toHaveCSS("background-color", "rgb(240, 182, 106)");
    await expect(previousInboxLogPage).toHaveCSS("color", "rgb(16, 21, 29)");
    const nextInboxLogPage = page.locator("#inboxLogPagination").getByRole("button", { name: "Volgende" });
    await nextInboxLogPage.hover();
    await expect(nextInboxLogPage).toHaveCSS("background-color", "rgb(240, 182, 106)");
    await expect(nextInboxLogPage).toHaveCSS("color", "rgb(32, 24, 18)");
    await nextInboxLogPage.click();
    await expect(page.locator("#inboxComponentLog tr")).toHaveCount(1);
    await expect(page.locator("#inboxLogPagination")).toContainText("Pagina 2 van 2 · 51 regels");
    await expect(page.locator("#dashboardComponentLog tr")).toHaveCount(2);
  });

  test("shows a searchable, sortable and paginated prompt history", async ({ page }) => {
    await page.route("**/api/prompt-history", async (route) => {
      await route.fulfill({ json: { runs: [] } });
    });
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    await page.locator("#promptHistory").evaluate((element) => { element.open = true; });
    await page.evaluate(() => {
      document.querySelector("#promptHistory").open = true;
      promptHistoryEntries = Array.from({ length: 26 }, (_, index) => ({
        run_id: `inbox-history-${index}`,
        status: index % 2 ? "COMPLETE" : "FAILED",
        title: `Geschiedenis prompt ${String(index).padStart(2, "0")}`,
        executed_at: `2026-08-02T12:${String(index).padStart(2, "0")}:00Z`,
        git_commit: index % 2 ? "abcdef1" : null,
        report_available: index % 2 === 1,
        analysis_available: index % 2 === 1,
      }));
      renderPromptHistory();
    });

    await expect(page.locator("#promptHistoryRows tr")).toHaveCount(25);
    await expect(page.locator("#promptHistoryPagination")).toContainText("Pagina 1 van 2 · 26 prompts");
    const nextPromptHistoryPage = page.locator("#promptHistoryPagination").getByRole("button", { name: "Volgende" });
    await nextPromptHistoryPage.hover();
    await expect(nextPromptHistoryPage).toHaveCSS("background-color", "rgb(255, 113, 143)");
    await expect(nextPromptHistoryPage).toHaveCSS("color", "rgb(39, 25, 35)");
    await page.locator('#promptHistory th[data-history-sort-key="title"]').click();
    await expect(page.locator('#promptHistory th[data-history-sort-key="title"]')).toHaveAttribute("aria-sort", "ascending");
    await page.locator("#promptHistoryFilter").fill("prompt 25");
    await expect(page.locator("#promptHistoryRows tr")).toHaveCount(1);
    const reportView = page.locator("#promptHistoryRows .prompt-history-report");
    await expect(reportView).toHaveCount(1);
    await expect(reportView).toHaveText("▤");
    await page.route("**/api/prompt-history/**/report", (route) => route.fulfill({
      contentType: "text/markdown",
      body: "# Historisch rapport\n\nDit rapport wordt in een dialoog getoond.",
    }));
    await reportView.click();
    await expect(page.locator("#promptHistoryReportModal")).toBeVisible();
    await expect(page.locator("#promptHistoryReportModal")).toBeFocused();
    await expect(page.locator("#promptHistoryReportContent")).toContainText("Historisch rapport");
    await expect(page.locator("#promptHistoryReportDownload")).toBeVisible();
    await expect(page.locator("#promptHistoryReportCopy")).toBeVisible();
    await page.locator("#promptHistoryReportClose").click();
    await expect(page.locator("#promptHistoryReportModal")).not.toBeVisible();
    await page.route("**/api/prompt-history/**/details", (route) => route.fulfill({
      json: {
        history: { run_id: "inbox-history-25", status: "COMPLETE", title: "Geschiedenis prompt 25", executed_at: "2026-08-02T12:25:00Z", execution_mode: "GENESIS", repository: "pcvantol/djconnect" },
        execution: { seconds: 42, total_seconds: 61 },
        runtime: { runtime_provider: "codex_cli", codex_cli_version: "0.146.0" },
        usage: { input_tokens: 120, output_tokens: 45 },
        commits: { "Genesis-commit": "abcdef1" },
        evidence: ["Execution Host: Engineering Platform"],
        reviewers: [],
      },
    }));
    await page.locator("#promptHistoryRows tr td").nth(1).click();
    await expect(page.locator("#promptHistoryDetailModal")).toBeVisible();
    await expect(page.locator("#promptHistoryDetailModal")).toBeFocused();
    await expect(page.locator("#promptHistoryDetailContent")).toContainText("Engineering Platform");
    await expect(page.locator("#promptHistoryDetailContent")).toContainText("0.146.0");
    await expect(page.locator("#promptHistoryDetailContent")).not.toContainText("Historisch rapport");
    await expect(page.locator("#promptHistoryDetailContent")).not.toContainText("Historische AI-analyse");
    await expect(page.locator("#promptHistoryReportModal")).not.toBeVisible();
    await page.locator("#promptHistoryDetailClose").click();
    await expect(page.locator("#promptHistoryDetailModal")).not.toBeVisible();
    const analysisView = page.locator("#promptHistoryRows .prompt-history-analysis").first();
    await expect(page.locator("#promptHistoryRows .prompt-history-analysis")).toHaveCount(1);
    await expect(page.locator("#promptHistoryRows a.prompt-history-analysis")).toHaveCount(0);
    await page.route("**/api/prompt-history/**/analysis", (route) => route.fulfill({
      contentType: "text/markdown",
      body: "# Historische AI-analyse\n\nDit advies hoort bij precies deze uitvoering.",
    }));
    await analysisView.click();
    await expect(page.locator("#promptHistoryReportModal")).toBeVisible();
    await expect(page.locator("#promptHistoryReportContent")).toContainText("Historische AI-analyse");
    await expect(page.locator("#promptHistoryReportDownload")).toBeVisible();
    await page.locator("#promptHistoryReportClose").click();
    const chat = page.locator("#promptHistoryRows .prompt-history-chat");
    await expect(chat).toHaveCount(1);
    await chat.click();
    await expect(page.locator("#promptHistoryChatModal")).toBeVisible();
    await expect(page.locator("#promptHistoryChatModal")).toBeFocused();
    let submittedRun;
    await page.route("**/api/codex-chat", async (route) => {
      submittedRun = route.request().postDataJSON().run_id;
      await route.fulfill({ json: { answer: "Dit advies hoort bij de geselecteerde prompt.", model: "Codex CLI" } });
    });
    await page.locator("#chatInput").fill("Wat is de volgende stap?");
    await page.locator("#chatSend").click();
    await expect(page.locator("#chatMessages")).toContainText("geselecteerde prompt");
    expect(submittedRun).toBe("inbox-history-25");
    await page.locator("#promptHistoryChatClose").click();
    await expect(page.locator("#promptHistoryChatModal")).not.toBeVisible();
    await expect(page.getByTestId("download-inbox-log")).toHaveCount(1);
  });

  test("scrolls only chat bubbles inside a prompt-history conversation", async ({ page }) => {
    await page.setViewportSize({ width: 720, height: 520 });
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const modal = page.locator("#promptHistoryChatModal"),
      messages = page.locator("#chatMessages"),
      header = modal.locator(".prompt-chat-modal__header"),
      input = page.locator("#chatInput");

    await modal.evaluate((element) => {
      document.querySelector("#chatMessages").innerHTML =
        '<article class="chat-message">Bericht</article>'.repeat(100);
      element.showModal();
    });
    const before = {
      header: await header.boundingBox(),
      input: await input.boundingBox(),
    };
    await messages.evaluate((element) => { element.scrollTop = 160; });
    const after = {
      header: await header.boundingBox(),
      input: await input.boundingBox(),
    };

    await expect.poll(() => messages.evaluate((element) => element.scrollTop)).toBe(160);
    expect(after.header.y).toBe(before.header.y);
    expect(after.input.y).toBe(before.input.y);
  });

  test("uses a distinct purple surface for AI answers in a prompt-history conversation", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const modal = page.locator("#promptHistoryChatModal"),
      panel = modal.locator(".prompt-chat-modal__panel");
    await modal.evaluate((element) => {
      document.querySelector("#chatMessages").innerHTML =
        '<article class="chat-message chat-message--assistant">Antwoord</article>';
      element.showModal();
    });
    const answer = page.locator("#chatMessages .chat-message--assistant");

    await expect(answer).toHaveCSS("background-color", "rgb(60, 42, 77)");
    expect(await answer.evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    )).not.toBe(await panel.evaluate(
      (element) => getComputedStyle(element).backgroundColor,
    ));
  });

  test("retains terminal status colours in the light prompt-history table", async ({ page }) => {
    await page.route("**/api/prompt-history", (route) => route.fulfill({ json: { runs: [] } }));
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#themeToggle").click();
    await page.evaluate(() => {
      promptHistoryEntries = [
        { run_id: "inbox-complete", status: "COMPLETE", title: "Complete", executed_at: "2026-08-03T12:00:00Z" },
        { run_id: "inbox-blocked", status: "BLOCKED", title: "Blocked", executed_at: "2026-08-03T11:00:00Z" },
        { run_id: "inbox-failed", status: "FAILED", title: "Failed", executed_at: "2026-08-03T10:00:00Z" },
      ];
      renderPromptHistory();
    });
    await expect(page.locator(".prompt-history-status--complete")).toHaveCSS("color", "rgb(20, 134, 91)");
    await expect(page.locator(".prompt-history-status--blocked")).toHaveCSS("color", "rgb(166, 90, 0)");
    await expect(page.locator(".prompt-history-status--failed")).toHaveCSS("color", "rgb(180, 35, 64)");
  });

  test("uses a light inline-code surface in AI answers when light mode is enabled", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#themeToggle").click();
    await page.evaluate(() => {
      const message = document.createElement("article");
      message.className = "chat-message chat-message--assistant";
      message.innerHTML = '<div class="chat-message__body"><p><code>git diff --check</code></p></div>';
      document.querySelector("#chatMessages").append(message);
    });
    await expect(page.locator(".chat-message--assistant code")).toHaveCSS("background-color", "rgb(233, 238, 246)");
    await expect(page.locator(".chat-message--assistant code")).toHaveCSS("color", "rgb(24, 34, 48)");
  });

  test("opens and closes all visible dashboard categories with the title-bar switch", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    const toggle = page.getByTestId("toggle-all-sections");
    await expect(toggle).toHaveAttribute("role", "switch");
    await expect(toggle).toHaveAttribute("aria-checked", "false");
    await expect(toggle).toHaveAttribute("aria-label", "Alle secties openen");

    await toggle.evaluate((button) => button.click());
    await expect(toggle).toHaveAttribute("aria-checked", "true");
    await expect(toggle).toHaveAttribute("aria-label", "Alle secties sluiten");
    for (const id of ["workspaceCard", "promptHistory", "platformHealth", "codexChat", "technicalDetails", "componentLogs"]) {
      await expect(page.locator(`#${id}`)).toHaveAttribute("open", "");
    }

    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(toggle).toHaveAttribute("aria-checked", "true");
    await expect(page.locator("#workspaceCard")).toHaveAttribute("open", "");

    await toggle.evaluate((button) => button.click());
    await expect(toggle).toHaveAttribute("aria-checked", "false");
    for (const id of ["workspaceCard", "platformHealth", "codexChat", "technicalDetails", "componentLogs"]) {
      await expect(page.locator(`#${id}`)).not.toHaveAttribute("open", "");
    }
  });

  test("switches between persisted dark and light dashboard themes", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    const toggle = page.getByTestId("theme-toggle");
    await expect(toggle).toHaveAttribute("role", "switch");
    await expect(toggle).toHaveAttribute("aria-checked", "false");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-checked", "true");
    await expect(toggle).toHaveAttribute("aria-label", "Donkere modus inschakelen");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await expect(page.locator("body")).toHaveCSS("background-color", "rgb(232, 237, 244)");
    await page.evaluate(() => rateLimits({ provider: "Codex CLI", provider_version: "0.146.0", windows: [], reset_credits: 1 }));
    await expect(page.locator("#rateLimitReset")).toHaveCSS("background-color", "rgb(232, 255, 245)");
    await expect(page.locator("#rateLimitReset")).toHaveCSS("color", "rgb(20, 90, 66)");
    await expect(page.locator("#technicalDetails .technical-grid > .card").first()).toHaveCSS("background-color", "rgb(255, 255, 255)");
    await page.evaluate(() => {
      document.querySelector("#promptHistory").open = true;
      promptHistoryEntries = Array.from({ length: 26 }, (_, index) => ({
        run_id: `light-theme-${index}`,
        status: "COMPLETE",
        title: `Lichte modus prompt ${index}`,
        executed_at: "2026-08-02T10:00:00+00:00",
        git_commit: null,
        report_available: false,
      }));
      promptHistoryPage = 1;
      renderPromptHistory();
    });
    const historyPagination = page.locator("#promptHistoryPagination");
    await expect(historyPagination.getByRole("button", { name: "Volgende" })).toHaveCSS("background-color", "rgb(255, 255, 255)");
    await expect(historyPagination.getByRole("button", { name: "Vorige" })).not.toHaveCSS("background-color", "rgb(68, 43, 55)");

    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await page.locator("#dashboardSplash").evaluate((element) => { element.hidden = true; });
    await toggle.click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("fills the reset action with a brighter green on hover", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#dashboardSplash").evaluate((element) => { element.hidden = true; });
    await page.locator("#rateLimits").evaluate((element) => { element.open = true; });
    await page.evaluate(() => rateLimits({ provider: "Codex CLI", provider_version: "0.146.0", windows: [], reset_credits: 1 }));
    const reset = page.locator("#rateLimitReset");

    await reset.hover();
    await expect(reset).toHaveCSS("background-color", "rgb(81, 216, 138)");
    await expect(reset).toHaveCSS("color", "rgb(17, 42, 32)");
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

  test("formats displayed log timestamps as dd-MM-yyyy HH:mm:ss", async ({ page }) => {
    await page.route("**/api/logs/**", (route) =>
      route.fulfill({ contentType: "application/x-ndjson", body: "" }),
    );
    const logsLoaded = Promise.all([
      page.waitForResponse((response) => response.url().endsWith("/api/logs/inbox")),
      page.waitForResponse((response) => response.url().endsWith("/api/logs/dashboard")),
    ]);
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await logsLoaded;
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    await page.evaluate(() => {
      componentLogEntries.inbox = structuredLogEntries(
        '{"timestamp":"2026-08-02T19:26:10.878167+00:00","level":"INFO","event":"formatted"}\n'
        + '{"timestamp":"onbekend-tijdstip","level":"WARNING","event":"fallback"}',
      );
      componentLogEntries.dashboard = [];
      renderComponentLogs();
    });

    await expect(page.locator("#inboxComponentLog tr td").nth(1)).toContainText("02-08-2026");
    await expect(page.locator("#inboxComponentLog tr td").nth(1)).toContainText("21:26:10");
    await expect(page.locator("#inboxComponentLog tr").nth(1).locator("td").nth(1)).toHaveText("onbekend-tijdstip");
  });

  test("treats an absent component log as an empty state, not malformed JSON", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    await page.evaluate(() => {
      componentLogEntries.inbox = structuredLogEntries("Nog geen applicatielog beschikbaar.");
      componentLogEntries.dashboard = [];
      renderComponentLogs();
    });

    const inboxText = await page.locator("#inboxComponentLog").textContent();
    expect(inboxText).toContain("Nog geen applicatielog beschikbaar.");
    expect(inboxText).not.toContain("ONGELDIGE JSON");
    expect(inboxText).not.toContain("onleesbare logregel");
  });

  test("keeps the Inbox queue visible when empty and numbers the oldest prompt first", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    const queue = page.getByTestId("engineering-inbox-queue");
    await page.evaluate(() => queueItems([], 0));
    await expect(queue).toBeVisible();
    await expect(queue).not.toHaveAttribute("open", "");
    await expect(queue.locator("summary")).toContainText("Inbox-wachtrij");
    await expect(queue.locator(".category-description")).toHaveText("Prompts worden uitgevoerd op volgorde van aanmaakdatum.");
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
    await expect(page.locator("#queueSummary")).toHaveText("2 prompts in de wachtrij.");
  });

  test("renders provider limit rows on separate lines", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#autoRefresh").uncheck();
    await page.evaluate(() => rateLimits({
      provider: "Codex CLI",
      provider_version: "0.146.0",
      windows: [{ label: "Weekvenster", used_percent: 24, resets_at: 0 }],
      reset_credits: 2,
    }));
    await expect(page.locator("#rateLimitProvider")).toHaveText("Codex CLI · 0.146.0");
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

  test("uses an in-app confirmation modal before clearing each component log", async ({ page }) => {
    let postCount = 0;
    await page.route("**/api/logs/inbox", async (route) => {
      if (route.request().method() === "POST") {
        postCount += 1;
        await route.fulfill({ contentType: "application/json", body: '{"cleared":"inbox"}' });
        return;
      }
      await route.fulfill({ contentType: "text/plain", body: "" });
    });
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#componentLogs").evaluate((element) => { element.open = true; });
    const nativeDialogs = [];
    page.on("dialog", async (dialog) => {
      nativeDialogs.push(dialog.type());
      await dialog.dismiss();
    });
    await page.getByTestId("clear-inbox-log").click();
    const modal = page.locator("#confirmationModal");
    await expect(modal).toBeVisible();
    await expect(modal).toBeFocused();
    await expect(modal.locator(".confirmation-modal__panel")).toHaveCSS("border-top-color", "rgb(240, 182, 106)");
    await expect(page.locator("#confirmationModalTitle")).toHaveCSS("border-bottom-color", "rgb(240, 182, 106)");
    expect(await page.locator("#confirmationModalConfirm").evaluate((element) => getComputedStyle(element).backgroundColor)).not.toBe("rgb(240, 182, 106)");
    for (const action of [page.locator("#confirmationModalCancel"), page.locator("#confirmationModalConfirm")]) {
      await action.hover();
      await expect(action).toHaveCSS("background-color", "rgb(240, 182, 106)");
      await expect(action).toHaveCSS("border-top-color", "rgb(240, 182, 106)");
    }
    await expect(page.locator("#confirmationModalConfirm")).toHaveCSS("font-size", "13px");
    await expect(page.locator("#confirmationModalConfirm")).toHaveCSS("font-family", await page.locator("#rateLimitReset").evaluate((button) => getComputedStyle(button).fontFamily));
    await expect(modal).toContainText("Wis de applicatielogs van Engineering Execution Host?");
    await page.keyboard.press("Escape");
    await expect(modal).not.toBeVisible();
    expect(postCount).toBe(0);

    await page.getByTestId("clear-inbox-log").click();
    await page.locator("#confirmationModalConfirm").click();
    await expect(page.getByTestId("clear-dashboard-log")).toBeVisible();
    await expect.poll(() => postCount).toBe(1);
    expect(nativeDialogs).toEqual([]);
  });

  test("clears only the browser-local AI conversation through the in-app modal", async ({ page }) => {
    await page.route("**/api/codex-chat", async (route) => {
      await route.fulfill({ contentType: "application/json", body: '{"answer":"De uitvoering is gereed.","model":"Codex CLI"}' });
    });
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#codexChat").evaluate((element) => { element.open = true; });
    await page.locator("#chatInput").fill("Wat is de status?");
    await page.locator("#chatSend").click();

    await expect(page.locator("#clearChat")).toBeVisible();
    await page.locator("#clearChat").click();
    const modal = page.locator("#confirmationModal");
    await expect(modal).toContainText("Dit wist alleen de lokale chatweergave.");
    await page.locator("#confirmationModalCancel").click();
    await expect(page.locator("#chatMessages")).toContainText("Wat is de status?");

    await page.locator("#clearChat").click();
    await page.locator("#confirmationModalConfirm").click();
    await expect(page.locator("#chatMessages")).toBeEmpty();
    await expect(page.locator("#clearChat")).toBeHidden();
    await expect(page.locator("#downloadChat")).toBeHidden();
    await expect.poll(() => page.evaluate(() => sessionStorage.getItem("djconnect-engineering-chat-history"))).toBeNull();
  });

  test("shows the iPhone pull-to-refresh threshold", async ({ page }) => {
    await page.goto(dashboardUrl, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => updatePullRefresh(72));
    await expect(page.getByTestId("pull-refresh")).toHaveText("Laat los om te vernieuwen");
    await expect(page.getByTestId("pull-refresh")).toHaveClass(/pull-refresh--visible/);
  });
});
