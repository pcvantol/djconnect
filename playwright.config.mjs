import { defineConfig } from "@playwright/test";

export default defineConfig({
  fullyParallel: true,
  workers: process.env.CI ? 10 : undefined,
  snapshotPathTemplate: "{testDir}/{testFilePath}-snapshots/{arg}-{platform}{ext}",
});
