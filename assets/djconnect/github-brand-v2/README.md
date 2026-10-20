# GitHub Brand V2 preview

Use `social-preview-v2.png` unchanged for DJConnect repository social previews.
The 1280 × 640 opaque PNG is 379,111 bytes. Keep the entire canvas: the approved
wordmark, glass mark and fixed brand tagline must remain visible. Do not crop to
the icon, stretch the wordmark, or add another button frame around the glass.

The embedded wordmark is the exact approved Brand V2 asset from protected Core
commit `7e14e5970b3f68d33d243ae6bab2b281fad59bb2`. The adjacent manifest records
its SHA-256, source manifest, composition, rendering version and output hashes.
The original approved asset and its manifest are unchanged. The SVG is the
self-contained composition source; upload the PNG to GitHub.

Reproduce in a fresh output directory with the installed Playwright dependency:

```sh
node scripts/export_github_social_preview.mjs --output /private/tmp/djc-preview-new \
  --browser-executable '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
```

The exporter uses only pinned Git blobs and embedded image data, blocks HTTP(S)
requests, and never changes GitHub settings. Two isolated exports with Chromium
155.0.8059.85 produced byte-identical PNG, SVG and manifest files. Independent
visual review approved the complete wordmark and tagline placement. Different
browser versions require a fresh byte and visual review.

[GitHub's social-preview guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)
recommends 1280 × 640 pixels and requires a file smaller than 1 MB. Upload through
repository **Settings → Social preview → Edit**. This source export is separate
from protected delivery, actual settings readback and consumer adoption; its
presence does not prove those steps have happened.

Copyright (c) 2026 Peter van Tol. DJConnect assets retain their repository license.
