# Agent guidance

## Purpose

Audio Engine converts a declared structured audio program into audio assets and a machine-readable manifest. It also publishes validated voice and sound catalogs.

Internally it has four responsibilities with one public product boundary:

- `voice` — text and resolved voice settings → cached mono voice clips;
- `ambience` — legacy schema-v2 single-bed preparation and pre-production candidate tooling;
- `sound` — validated sound meta-index + one deterministic environment track from bed/layers/events;
- `mix` — speech + optional prepared environment → final mono/stereo master.

Consumers call **Audio Engine**, not separate services.

## Non-goals

Do not add:
- audioguide-specific or Learn-it-specific behavior;
- content authoring or permanent media storage;
- arbitrary Web downloads during rendering;
- web UI, backend, database, accounts, queues, or job dashboards;
- HRTF/binaural 3D, room simulation, reverb design, plugin chains, or general-purpose DAW behavior without new evidence;
- unbounded tracks or events;
- nondeterministic/random event scheduling in the public contract.

## Stable boundary

- Schema v1: stable narration contract.
- Schema v2: stable stereo placement + one optional legacy ambience bed.
- Schema v3: bounded deterministic soundscape. Old engines must reject it rather than silently lose sound design.
- Assembly remains schema v1.

Core commands include `voices`, `recommend`, `sounds`, `ambiences`, `ambience discover/qualify`, `render`, `batch`, `assemble`, and `validate`.

## Voice governance

- Linguistic quality precedes role fit.
- French pronunciation is eliminatory in the tested palette.
- Casting scores are advisory rankings, not fabricated historical quality scores.
- Keep voice synthesis cache independent from placement and all environment mixing.

## Sound catalog governance

The public `sounds` meta-index means **validated and usable**, not merely discovered.

Every public entry must have:
- stable unique id;
- intrinsic type `ambience` or `event`;
- status `validated`;
- exact SHA-256 content hash;
- verified per-asset licence and attribution obligations;
- a locked asset reference;
- useful semantic tags.

`layer` is a mix role, not a resource type. An ambience can serve as a bed or layer.

A catalog id may render only from materialized local content whose SHA-256 exactly matches the validated entry. `asset.location` may document a licensed asset that is not redistributable, but location-only entries are not directly renderable until materialized in an authorized local workspace.

Web search is discovery, never render-time resolution.

## Soundscape governance

Schema v3 is deliberately bounded:
- at most one bed;
- at most two continuous layers;
- at most sixteen punctual events;
- events use explicit `at_ms` timing;
- event placement is semantic `left`, `center`, or `right`;
- environment ducking is one global `speech` or `off` choice.

Do not add random recurrence, arbitrary automation, unlimited timelines, or per-plugin processing without separate evidence.

The `sound` module should produce **one deterministic environment WAV**. The mixer then remains a simple two-input responsibility: speech + environment. This boundary is intentional.

## Mix governance

- Mono remains default for ordinary narration.
- Stereo is activated only when scene placement, legacy ambience, or soundscape requires it.
- Public spatial vocabulary remains strictly `left`, `center`, `right`; numeric pan is internal.
- Use constant-power panning and avoid hard panning ordinary dialogue.
- Voice intelligibility takes priority over realism.
- Ducking must remain subtle.
- Normalize only the final master.

## Asset governance

- Render inputs are local/snapshotted and workspace-bounded.
- Reject HTTP(S), absolute paths, and workspace escapes.
- Production assets require provenance, licence and content hash.
- Raw redistribution depends on the exact asset licence; commercial royalty-free files must not be republished standalone when forbidden.
- Do not create a separate asset service without evidence.

## Engineering rules

- Keep dependencies minimal.
- Product-specific exceptions are architecture defects.
- Batch failures must not destroy successful outputs.
- Expensive TTS cache must survive changes to event time, ambience gain, fades, or placement.
- Environment preparation and final mix are local deterministic stages with content-addressed caches.
- Cache fingerprints must include source hashes, declared settings, target duration/format and relevant processing code.
- Default spoken-word output is MP3 mono 24 kHz 80 kbit/s; stereo speech uses at least 96 kbit/s.
- Manifest must record engine version, provider, profile, hashes, cache information, output properties and environment component provenance.
- Run offline smoke tests before merging rendering changes. Provider smoke is useful evidence but should not make ordinary CI brittle.

## Privacy

The current Edge provider is remote. Never imply that input text stays local.
