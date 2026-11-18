# DJConnect Design Principles

These principles describe how DJConnect should feel to users across clients, docs, setup, and product surfaces.

## 1. Music first

DJConnect should never make the user feel like they are operating an AI system.

The music is primary. DJConnect enriches the listening experience around it.

## 2. One DJ, many devices

A user should feel that the same DJ follows them across their linked personal devices.

Starting a conversation on an iPhone, continuing on Apple Watch, and later opening a Mac or Windows client should feel like one continuous profile, not separate device personalities.

## 3. Shared devices behave like shared spaces

A living-room display, kitchen voice satellite, Pi wall screen, or guest-facing VibeCast surface should default to a household, room, kids, or guest profile.

Personal chat history and personal Music DNA should not appear on shared devices unless the device is explicitly linked to a personal profile.

## 4. Setup should be the shortest path to music

Initial setup should ask only what is needed to make DJConnect work:

1. choose a music backend;
2. create one initial profile;
3. link one music account/backend binding;
4. link one device;
5. choose simple fallback behavior.

Household modeling, multiple profiles, rooms, satellites, privacy controls, export/import, and extra accounts belong in options or management flows.

## 5. The user should not configure intelligence modules

Users should not need to understand Track Intelligence, Lyrics Intelligence, Artist Intelligence, Album Intelligence, Music DNA, Mood Engine, and Recommendation Engine as separate systems.

They should experience one coherent DJConnect Intelligence layer through different surfaces.

## 6. Insights are one ecosystem

Track Insight, Lyrics Explain, Artist Insight, Album Insight, recommendations, Discover, and VibeCast layers are all expressions of the same Insight ecosystem.

Renderers decide how much of that ecosystem to show.

## 7. VibeCast is a presentation experience, not a control surface

VibeCast should make music beautiful and alive on a larger screen.

It may include artwork, lyrics, track insight, artist context, album context, mood layers, guest companion features, and live visual reactions.

Any future reactions follow the deferred [Audience Experience Architecture](docs/product/AUDIENCE_EXPERIENCE_ARCHITECTURE.md): they are transient, privacy-filtered Audience Events presented through an independent layer, never social-feed content or direct intelligence authority.

It should avoid becoming a complex controller.

## 8. Ask DJ should feel conversational, not transactional

Ask DJ should answer music questions, explain recommendations, continue context, and reflect the profile's response style.

It should know when to be brief, when to go deeper, and when to stay out of the way.

## 9. Community should be generous

Community users should feel they have a real product, not a demo.

Personal and future Cloud should add personalization, continuity, premium voices, cloud sync, and advanced profile capabilities rather than artificially removing core usefulness from Community.

## 10. Privacy must be understandable

Users should understand where personal memory lives.

Profile-level controls should exist for:

- private session behavior;
- clearing Ask DJ history;
- resetting Music DNA;
- exporting a profile;
- importing a profile;
- avoiding personal state on shared devices.

## 11. Guest experiences must be safe by default

Guest-facing flows should be read-only unless explicitly designed otherwise.

Guest surfaces should not expose personal Music DNA, private history, OAuth tokens, credentials, or Home Assistant administration.

## 12. Platform capabilities should adapt to the client

A watch, Pi display, Windows desktop, Apple app, ESP32 remote, and VibeCast renderer should expose the same platform capability model according to their constraints.

Do not duplicate product concepts per platform.

## 13. Silence is a feature

DJConnect should not constantly interrupt the music.

Proactive intelligence should be timely, useful, and optional. The best DJ sometimes says nothing.

## 14. Every advanced feature needs a simple default

If a feature requires advanced configuration, it must also have a safe default or graceful disabled state.

## 15. User-facing names should be human

Use names that explain the experience:

- Music DNA;
- Ask DJ;
- VibeCast;
- Discover;
- Insights;
- Household DJ;
- Personal DJ.

Avoid exposing internal names unless the user is in developer documentation.
