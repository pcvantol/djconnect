# DJConnect Platform Discovery Report

Epic 2: Platform Discovery & Repository Audit  
Date: 2026-07-09  
Scope: all current DJConnect repositories  
Mode: discovery-only; no runtime implementation changes

## Executive summary

DJConnect is healthier than a typical early multi-repository platform. The strongest signal is that the core architecture is already visible in code: Home Assistant owns intelligence, clients consume backend contracts, ESP32 avoids provider credentials, the central API is scoped to trust/relay, and release repositories are mostly artifact-only.

The biggest platform risk is not one broken repository. It is timing: the foundation now describes a Profile-centered, backend-agnostic, Insight Feed-oriented platform, while runtime implementation is still partly device/user-keyed, feature-specific and Apple-led. That is normal after Epic 1, but Epic 3 should happen before large new feature work.

The most important recommendation is to keep Epic 2 discovery-only and move next into Profile Architecture, then Insight Feed, then feature flags/capability governance and distribution cleanup.

## Platform health

Overall platform health: **7.3 / 10**

The platform has strong direction, strong local core quality and unusually good contract testing. It is held back by incomplete Profile Architecture, uneven foundation sync across sibling repos, release-repo drift and missing formal parity rules between Apple, Windows, Pi and ESP32.

## Repository scores

| Repository | Product | Architecture | Docs | Testing | CI/CD | Security | Privacy | Release | DX | Overall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `djconnect` | 8 | 8 | 9 | 9 | 9 | 9 | 8 | 9 | 8 | 8.6 |
| `djconnect-app` | 9 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 7 | 8.0 |
| `djconnect-windows` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 7 | 7 | 7.8 |
| `djconnect-pi` | 7 | 8 | 8 | 8 | 8 | 8 | 7 | 8 | 8 | 7.8 |
| `djconnect-esp32` | 8 | 8 | 8 | 7 | 8 | 9 | 9 | 8 | 7 | 8.0 |
| `djconnect-api` | 7 | 8 | 8 | 8 | 9 | 9 | 8 | 8 | 8 | 8.1 |
| `djconnect-website` | 7 | 7 | 8 | 8 | 8 | 7 | 7 | 8 | 7 | 7.4 |
| `djconnect-firmware` | 6 | 8 | 6 | 2 | 1 | 6 | 7 | 7 | 5 | 5.3 |
| `djconnect-app-releases` | 5 | 7 | 5 | 1 | 1 | 5 | 5 | 6 | 4 | 4.3 |
| `djconnect-pi-releases` | 6 | 8 | 6 | 1 | 1 | 6 | 6 | 7 | 5 | 5.1 |

## Architecture maturity

Score: **7 / 10**

Strengths:

- Repository ownership is mostly respected.
- Backend-owned intelligence is a real implementation pattern.
- Music Backend adapter work has begun in the HA repo.
- Clients consume contract fixtures rather than inventing all contracts locally.
- Central API remains relay/trust-oriented and has not become the product brain.
- ESP32 is correctly scoped as Voice/Control Client.

Gaps:

- DJConnect Profile is not yet implemented as the primary runtime identity.
- Insight Feed is not yet the unifying backend-owned intelligence contract.
- Feature flags and capability maturity are documented but not platform-wide runtime mechanisms.
- Apple is the richest client and risks becoming de facto product authority.
- Pi is richer than the current Ambient Client wording suggests.

## Product maturity

Score: **7 / 10**

Strengths:

- Product identity is now clear: AI music platform centered on an AI DJ experience.
- Community is positioned as complete/local-first.
- Personal is correctly profile-centric in foundation docs.
- Clients increasingly present backend-owned Ask DJ, Music DNA, Discover and Track Insight.

Gaps:

- Public website and release repos still contain older implementation-first or Spotify-specific wording.
- Community/Personal is not yet enforced by runtime architecture.
- "DJConnect Profile" is not yet a concrete user-facing identity across clients.
- Release repos lag behind source repos and may mislead users.

## Consistency score

Score: **6.5 / 10**

The core repos are aligned, but consistency drops in public release repos and website copy. AGENTS coverage is uneven:

- Strong: `djconnect`, `djconnect-pi`, `djconnect-esp32`.
- Partial: `djconnect-app`, `djconnect-windows`, `djconnect-api`.
- Missing: `djconnect-website`, `djconnect-firmware`, `djconnect-app-releases`, `djconnect-pi-releases`.

## Technical debt

Top technical debt:

1. Missing Profile resolver/storage and profile-scoped API semantics.
2. Missing Insight Feed abstraction.
3. Duplicated client parsing/rendering logic across Apple, Windows and Pi.
4. Repo-local `SYNC_PROMPTS.md` files in app/Windows despite canonical HA source-of-truth rules.
5. Release repositories lack CI validation and AGENTS guidance.
6. Website/release docs lack automated product-language drift checks.
7. Local dirty worktrees in sibling repos reduce discovery reproducibility.

## Product debt

Top product debt:

1. Product language drift in website/release repos.
2. Apple/Windows/Pi parity not formally defined.
3. Pi Ambient Client has grown toward Intelligence Client behavior without a formal capability budget.
4. TestFlight/App Store/Microsoft Store distribution strategy is not platform-final.
5. Community/Personal tier boundary is documented but not runtime-enforced.
6. "Your AI DJ" story is stronger in foundation docs than in some public entrypoints.

## Top opportunities

1. Make Profile Architecture the next implementation epic.
2. Turn Track Insight, Lyrics Explain, Discover and VibeCast into one Insight Feed architecture.
3. Use contract fixtures as a formal cross-client compatibility suite.
4. Add foundation-aware AGENTS to every repo.
5. Add product-language tests for website and release repos.
6. Promote central API trust boundary ADR before cloud/profile expansion.
7. Create a client parity matrix with required/optional/forbidden capabilities by client class.

## Top risks

1. Feature work before Profile Architecture will harden the wrong identity model.
2. Apple-first UX may accidentally redefine platform behavior.
3. Central API could drift from relay/trust into cloud-owned intelligence without ADR.
4. Shared Pi displays could leak personal context until Profile Architecture and privacy modes exist.
5. Release repo stale docs can create incorrect install/security expectations.
6. Spotify-specific public wording can undermine Music Backend agnosticism.

## Top inconsistencies

- `Client API URL` vs `Client adres` in release docs.
- Spotify Premium listed as a general requirement in release repos despite Music Assistant support.
- Keychain wording in app release repo conflicts with current Apple source README.
- Foundation docs say full canonical set; sibling AGENTS often mention only older docs.
- Pi is documented as Ambient, but exposes more personal management surfaces than "light" suggests.
- Website mentions "Spotify profile" in historical/current docs, conflicting with "DJConnect Profile".

## Top duplicate logic

- Contract parsing in Apple, Windows and Pi.
- Music DNA/Discovery presentation mapping across Apple, Windows and Pi.
- Release-note publishing flows across app, Windows, Pi and website.
- Local diagnostic redaction implementations across clients.
- HTTP/WebSocket fallback logic across Apple, Windows and Pi.

Duplication is not inherently wrong for native clients, but shared fixture coverage should be treated as the compatibility contract.

## Recommended Epic ordering

1. Epic 3: Profile Architecture.
2. Epic 4: Intelligence Engine / Insight Feed.
3. Epic 5: Feature Flags, Capability Maturity and Client Parity.
4. Epic 6: Distribution and Release Strategy.
5. Epic 7: Platform Quality Standard rollout.
6. Epic 8: Website and Product Story.
7. Future Cloud and Personal only after Profile Architecture and central trust ADR are accepted.

## Repository reports

- `docs/discovery/djconnect.md`
- `docs/discovery/djconnect-app.md`
- `docs/discovery/djconnect-windows.md`
- `docs/discovery/djconnect-pi.md`
- `docs/discovery/djconnect-esp32.md`
- `docs/discovery/djconnect-api.md`
- `docs/discovery/djconnect-website.md`
- `docs/discovery/djconnect-firmware.md`
- `docs/discovery/djconnect-app-releases.md`
- `docs/discovery/djconnect-pi-releases.md`

## Supporting registers

- `docs/discovery/TECHNICAL_DEBT_REGISTER.md`
- `docs/discovery/PRODUCT_DEBT_REGISTER.md`
- `docs/discovery/CI_CD_REVIEW.md`
- `docs/discovery/SECURITY_PRIVACY_REVIEW.md`
- `docs/discovery/RELEASE_PROCESS_REVIEW.md`
- `docs/discovery/BACKLOG_RECOMMENDATIONS.md`
- `docs/discovery/INNOVATION_RECOMMENDATIONS.md`

## Discovery constraints

- No runtime code was changed.
- Sibling repositories were read-only during this audit.
- Existing dirty worktrees in sibling repos were not modified.
- Some audited branches were not `main`; findings should be validated during repo-specific follow-up PRs.
