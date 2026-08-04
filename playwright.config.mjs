import { defineConfig } from "@playwright/test";

export default defineConfig({
  snapshotPathTemplate: "{testDir}/{testFilePath}-snapshots/{arg}{ext}",
});
