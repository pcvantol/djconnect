import { defineConfig } from "@playwright/test";

export default defineConfig({
  fullyParallel: true,
  // Ten workers keep the full browser suite fast in CI. A failed browser
  // interaction gets one clean retry because each worker owns an isolated
  // dashboard process and an occasional concurrent reload must not turn into
  // a persistent PR failure.
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 10 : undefined,
  snapshotPathTemplate: "{testDir}/{testFilePath}-snapshots/{arg}-{platform}{ext}",
});
