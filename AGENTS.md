# Agent guidance

## Purpose

Audio Engine converts a declared structured audio program into audio assets and a machine-readable manifest. It also publishes validated voice, sound and engine-capability catalogs.

Internally it has five responsibilities with one public product boundary:

- `voice` — text and resolved voice settings → cached dry mono voice clips;
- `ambience` — legacy schema-v2 single-bed preparation and pre-production candidate tooling;
- `sound` — validated sound meta-index + one deterministic environment track from bed/layers/events;
- `effects` — bounded semantic acoustic-space presets and public capability metadata;
- `mix` — dry speech clips + optional acoustic-space treatment + optional prepared environment → final mono/stereo master.

Consumers call **Audio Engine**, not separate services.

## Non-goals

Do not add:
- audioguide-specific, audiobook-specific or Learn-it-specific behavior;
- any Production dependency on Voice Lab runners, experimental model caches or private Lab infrastructure;
- content authoring or permanent media storage;
- arbitrary Web downloads during rendering;
- web UI, backend, database, accounts, queues, or job dashboards;
- HRTF/binaural 3D, front/rear/height positioning, user-defined reverb design, plugin chains, or general-purpose DAW behavior;
- claims that a synthetic acoustic preset reproduces the authentic acoustics of a named place;
- unbounded tracks or events;
- nondeterministic/random event scheduling in the public contract.

## Stable boundary

- Schema v1: stable narration contract.
- Schema v2: stable stereo placement + one optional legacy ambience bed.
- Schema v3: bounded deterministic soundscape with explicit timestamps. Old engines must reject it rather than silently lose sound design.
- Schema v4: bounded narrative sound direction: semantic acoustic spaces, safe event fades and explicit `scene` events that reserve narration-free space after a segment. Older schemas must not accept v4-only fields.
- Schema v5: bounded `bridge` intent with explicit foreground time and fixed carry under following speech.
- Schema v6: measured relative bridge carry based on actual rendered spoken-segment duration; fixed v5 carry remains available.
- Assembly remains schema v1.

Core commands include `capabilities`, `voices`, `recommend`, `sounds`, `ambiences`, `ambience discover/qualify`, `render`, `batch`, `assemble`, and `validate`.

## Production / Lab isolation

Production and research share one repository but not one runtime dependency graph.

- `main` is the Production authority for the reusable renderer.
- Current Production TTS remains Edge unless an explicit promotion decision changes it.
- Voice Lab experiments may use GitHub-hosted CPU or external/private execution resources, but Production must remain fully functional when those resources are unavailable.
- Experimental ML dependencies, model weights and persistent Lab caches must not become required dependencies of `audio-engine render`.
- Lab experiments are evidence-producing research lanes; scientific PASS is necessary but never sufficient for Production promotion.
- Durable Lab evidence must be preserved before deleting historical branches or workflows.
- For a public repository, do not attach a persistent self-hosted Lab machine directly as a default execution target. Any future NUC integration requires an explicitly governed secure control-plane or local/manual execution model.

## Voice governance

- Linguistic quality precedes role fit.
- French pronunciation is eliminatory in the tested palette.
- Casting scores are advisory rankings, not fabricated historical quality scores.
- Keep voice synthesis cache independent from placement, acoustic-space processing and all environment mixing.
- Cached TTS clips remain dry. Acoustic-space processing happens locally after the voice cache.
- Narration intelligibility takes priority over acoustic realism.

## Capability catalog governance

`audio-engine capabilities` is the machine-readable source of truth for what applications may offer.

- Publish only effects and semantics that the current engine actually renders.
- Keep public vocabulary semantic (`large-stone-interior`), not plugin-oriented (`reverb=0.72`).
- Acoustic spaces are restrained synthetic evocations unless an explicitly governed authentic impulse response is introduced later.
- The initial public acoustic-space set is intentionally small: `dry`, `outdoor-open`, `small-stone-room`, `large-stone-interior`, `confined-stone`.
- A new public effect requires contract semantics, deterministic rendering, manifest evidence and tests. Do not add decorative catalog entries without implementation.

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

Schema v3/v4 remains deliberately bounded:
- at most one bed;
- at most two continuous layers;
- at most sixteen punctual events;
- v3 events use explicit `at_ms` timing;
- v4 punctuation events retain explicit `at_ms` timing;
- v4 `scene` events use one `after_segment` anchor and a bounded `space_ms` narration-free window;
- event placement is semantic `left`, `center`, or `right`;
- environment ducking is one global `speech` or `off` choice.

Continuous bed/layers are narrative `texture`. Event roles are `punctuation` or `scene`. `scene` means the sound is intentionally allowed to carry information or emotion without speech for a short declared window.

V4 event fades are safe defaults. A hard cut is allowed only when the author explicitly sets the corresponding fade duration to zero.

Do not add random recurrence, arbitrary automation, unlimited timelines, or per-plugin processing without separate evidence.

The `sound` module should produce **one deterministic environment WAV**. The mixer then remains a simple speech/environment responsibility. This boundary is intentional.

## Mix governance

- Mono remains default for ordinary narration.
- Stereo is activated only when scene placement, legacy ambience, or soundscape requires it.
- Public spatial vocabulary remains strictly `left`, `center`, `right`; numeric pan is internal.
- Use constant-power panning and avoid hard panning ordinary dialogue.
- Voice intelligibility takes priority over realism.
- Ducking must remain subtle.
- Acoustic-space presets must remain restrained enough for spoken-word playback on phone, car speaker and headphones.
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
- Expensive TTS cache must survive changes to event time, ambience gain, fades, placement, acoustic-space preset or scene spacing.
- Environment preparation and final mix are local deterministic stages with content-addressed caches.
- Cache fingerprints must include source hashes, declared settings, resolved scene timing, target duration/format and relevant processing code.
- Default spoken-word output is MP3 mono 24 kHz 80 kbit/s; stereo speech uses at least 96 kbit/s.
- Manifest must record engine version, provider, profile, hashes, cache information, output properties, resolved acoustic spaces and environment component provenance.
- Run offline smoke tests before merging rendering changes. Provider smoke is useful evidence but should not make ordinary CI brittle.

## Privacy

The current Edge provider is remote. Never imply that input text stays local.
