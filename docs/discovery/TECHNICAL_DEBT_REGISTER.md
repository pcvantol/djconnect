# Technical Debt Register

Epic 2 discovery-only register. Do not implement directly from this file without a focused follow-up issue or PR.

| Priority | Area | Repositories | Debt | Recommended owner |
| --- | --- | --- | --- | --- |
| P0 | Profile Architecture | `djconnect`, all clients | Runtime identity is not yet a first-class DJConnect Profile resolver/storage model. | Epic 3 |
| P1 | Insight Feed | `djconnect`, `djconnect-app`, `djconnect-windows`, `djconnect-pi`, `djconnect-website` | Track Insight, Discover, VibeCast and future Lyrics work are feature-specific instead of one shared feed model. | Epic 4 |
| P1 | Contract compatibility | `djconnect`, `djconnect-app`, `djconnect-windows`, `djconnect-pi` | Contract fixtures exist but are not yet promoted to formal cross-client compatibility governance. | Epic 2B |
| P1 | Foundation sync | all sibling repos | AGENTS/foundation pointers are uneven; some repos have local sync prompt copies. | Epic 2A |
| P1 | Release repo validation | release repos | Release-only repos lack AGENTS and repo-local manifest/checksum validation. | Epic 6 |
| P1 | Product-language validation | `djconnect-website`, release repos | Public docs can drift into old Spotify/client language without automated guardrails. | Epic 8 |
| P2 | Duplicate client parsing | Apple, Windows, Pi | Native clients duplicate parsing and presentation mapping. This is acceptable only if fixture conformance remains strong. | Epic 2B |
| P2 | Central API expansion guard | `djconnect-api`, `djconnect-website` | Central API can drift into cloud/product ownership without ADR-0007. | ADR-0007 |
| P2 | Dirty/generated workspace hygiene | Apple, release repos | Local derived data and dirty worktrees complicate audits. | Developer tooling |
| P2 | Firmware source/release boundary | `djconnect-esp32`, `djconnect-firmware` | Source repo also describes itself as release repo; public release repo is artifact-only. | Epic 6 |
