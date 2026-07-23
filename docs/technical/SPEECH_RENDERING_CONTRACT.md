# Speech Rendering Contract

## Status

Canonical renderer-neutral architecture. This contract introduces no Renderer
Host, TTS provider, voice configuration, audio asset, client UI, transport or
Runtime implementation.

## Purpose

Speech Presentation is the immutable, renderer-safe expression of an approved
DJMoment. It is produced server-side by Presentation Composer and is consumed
only after Broadcast by Renderer Hosts.

```text
Session Intelligence
  -> DJMoment
  -> Presentation Composer
  -> immutable Presentation
  -> Broadcast
  -> Speech Presentation
  -> Renderer Host
  -> renderer-specific rendering
```

The Presentation remains identical across Renderer Hosts. A host may choose a
local interpretation, but never generates, edits, reorders or otherwise
changes Presentation content.

## Renderer-safe input

The canonical Presentation Projection provides a Renderer Host with:

- Presentation identity;
- source DJMoment identity and type;
- renderer-safe visibility;
- optional Speech Presentation mode; and
- ordered immutable Speech Segments containing ordinal, semantic Speaker Role
  and text.

It never provides Planner state, Knowledge internals, prompts, provider
identifiers or payloads, renderer instructions, TTS provider selection, voice
identifiers, Session Runtime context, Session identity or Profile-private data.
Speech Presentation is text-only; Broadcast carries no audio, speech asset,
locale, room-routing instruction or renderer configuration.

## Segment and role contract

Renderer Hosts process segments sequentially in supplied ordinal order and
preserve both order and semantic Speaker Role. A Renderer Host must not merge,
split, reorder, rewrite or infer segments. Where future renderer-safe timing
hints are supplied, a host preserves them as hints; no timing master or
cross-renderer synchronization authority is introduced.

```text
Segment 1: DJ
        ->
Segment 2: Sidekick
```

`DJ` and `Sidekick` are semantic roles, never voices, TTS engines, renderer
identities or provider identifiers.

## Renderer-local role mapping

An Audio Renderer Host may own a local Role Mapping:

```text
Speaker Role -> configured local voice -> configured local TTS provider
```

This mapping is entirely renderer-local. Presentation Composer, Session
Runtime, Broadcast and Room Presentation Routing neither receive nor select a
voice, a provider or a device. Room Presentation Routing selects only eligible
Renderer Hosts; it never changes a Presentation or maps a role to a voice.

## Renderer capabilities and fallback

Renderer capability is local and optional. A host may support any bounded
combination of Speech Audio, Speech Text, Speech Highlighting, Speech
Synchronization and Voice Mapping. Lack of one capability never invalidates
the Presentation.

| Available capability | Renderer behavior |
| --- | --- |
| Speech Audio | May render each supplied segment with local speech capability. |
| Speech Text | May display supplied segments as role-labelled text. |
| Speech Highlighting | Deferred local enhancement; never changes segment order or text. |
| Speech Synchronization | Deferred local enhancement using future safe hints only. |
| Voice Mapping | May map a semantic role to a local configured voice and provider. |

When Speech Audio is unavailable, a host may render Speech Text. When Speech
Text is unavailable too, the Presentation remains valid and the host continues
its existing renderer behavior. No fallback may cause server-side regeneration,
another Broadcast projection or a Session Flow change.

## Text and audio interpretations

A Visual Renderer Host may interpret Speech Text as ordered, role-labelled
dialogue bubbles associated with the one existing Session Flow item for the
source DJMoment. This is not chat, messaging, a new timeline or a new Session
Flow entry.

An Audio Renderer Host may interpret the same segments through renderer-local
speech synthesis, including future Home Assistant configured TTS, Apple local
speech synthesis or another renderer-specific provider. These are possible
local implementations, not server contracts.

## Renderer relationships

The future Universal Receiver Speech Presentation Component may render ordered
dialogue bubbles, preserve speaker roles, remain subordinate to the existing
Session Flow item and later use safe synchronization hints with Audio Renderer
Hosts. It does not redesign the Receiver or authorize browser TTS.

VibeCast consumes the same Presentation Projection and may later choose Text
Rendering, Audio Rendering or both. Apple and Home Assistant may later act as
Audio Renderer Hosts. No such renderer implementation changes Presentation
Composer or introduces a second presentation pipeline.

## Deferred work

- Home Assistant renderer implementation;
- Apple renderer implementation;
- Google TV and VibeCast renderer implementation;
- Voice configuration UI;
- synchronized speech highlighting;
- Presentation Memory and Presentation Cast;
- multi-audio-renderer policy;
- speech asset generation; and
- cloud speech.

## References

- [Presentation Composer Architecture](../product/PRESENTATION_COMPOSER_ARCHITECTURE.md)
- [Broadcast Transport](BROADCAST_TRANSPORT.md)
- [Universal Receiver Architecture](UNIVERSAL_RECEIVER_ARCHITECTURE.md)
- [Audio Renderer Host Architecture](AUDIO_RENDERER_HOST_ARCHITECTURE.md)
- [Room Presentation Routing Architecture](ROOM_PRESENTATION_ROUTING_ARCHITECTURE.md)
- [VibeCast Architecture](../product/VIBECAST_ARCHITECTURE.md)
