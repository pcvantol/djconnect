import { defineConfig } from "@playwright/test";

export default defineConfig({
  fullyParallel: true,
  workers: process.env.CI ? 8 : undefined,
  snapshotPathTemplate: "{testDir}/{testFilePath}-snapshots/{arg}-{platform}{ext}",
});
