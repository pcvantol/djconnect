# Epic 2 Innovation Lab Recommendations

Epic 2 did not implement new ideas. These are candidates to add to or refine in `INNOVATION_LAB.md`.

## Ambient Client capability budget

**Domain:** Client capability classes / Pi / shared devices  
**Status recommendation:** Exploration

Define how rich an Ambient Client should become before it stops being ambient. The Pi currently renders Track Insight, Music DNA and Music Discovery, which can fit a room display if profile/privacy rules are strong. The platform needs a named capability budget for shared screens.

Open questions:

- Which Music DNA blocks are safe on shared displays?
- Should Pi support profile switching or only room/household profiles?
- Which controls should require an explicitly linked personal profile?

## Contract Fixture Compatibility Dashboard

**Domain:** Developer experience / platform quality  
**Status recommendation:** Exploration

The HA repo already exports fixtures and Apple/Pi/Windows consume them. A simple compatibility dashboard could show which clients pass which fixture families.

Open questions:

- Should fixture conformance be published in release notes?
- Should release repositories include fixture manifest versions?
- Can CI collect client conformance without cross-repo coupling?

## Foundation language lint

**Domain:** Product language / website / release repos  
**Status recommendation:** Exploration

Add lightweight checks for avoid terms such as `Spotify profile`, `trial`, `lite`, stale `Client API URL`, or client-owned intelligence language in public docs.

Open questions:

- Which terms are hard failures and which are warnings?
- How should historical changelog entries be handled?

## Shared device privacy preview

**Domain:** Privacy / profiles / shared devices  
**Status recommendation:** Exploration

Before full Profile Architecture ships, create product mockups or contract examples showing how household, room, guest and personal profiles behave on Pi/VibeCast.

Open questions:

- What should the default shared profile reveal?
- How does a user temporarily personalize a shared device?
- How does private mode interact with VibeCast and guest companion?
