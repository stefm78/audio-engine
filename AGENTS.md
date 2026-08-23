# Agent guidance

## Purpose

Audio Engine converts a declared structured audio program into audio assets and a machine-readable manifest. It also publishes the validated voice palette and recommends suitable presets from declared vocal traits.

Internally it has three responsibilities with one public product boundary:

- `voice` — text and resolved voice settings → cached mono voice clips;
- `ambience` — one declared background asset → prepared background bed;
- `mix` — voice clips + optional ambience → final mono/stereo master.

Consumers call **Audio Engine**, not three separate services.

## Non-goals

Do not add:
- audioguide-specific behavior;
- Learn-it-specific behavior;
- content authoring or generation;
- permanent audio storage or GitHub Release publishing;
- arbitrary Web downloads during rendering;
- web UI, backend, database, accounts, queues, or job dashboards;
- HRTF/binaural 3D, room simulation, reverb design, or general-purpose DAW behavior without new evidence.

Consumers own their content, asset qualification, publication, storage, and playback experience.

## Stable boundary

Schema v1 is a public narration contract and remains backward compatible.
Schema v2 adds stereo placement and one optional ambience bed. Do not silently accept v2-only behavior in a v1 program.

Core commands:
- `voices`: publish the tested voice palette, quality gate and casting rules;
- `recommend`: rank presets for a requested vocal target without synthesis;
- `render`: one program → one audio asset;
- `batch`: many programs → independent best-effort renders;
- `assemble`: existing audio assets → one longer asset;
- `validate`: contract validation without synthesis.

## Voice governance

- Linguistic quality precedes role fit.
- French pronunciation is an eliminatory quality criterion inherited from the initial blind benchmark.
- Casting scores are advisory rankings, not historical quality scores.
- Do not invent benchmark scores that were not measured.
- A consumer may override a recommendation with an explicit validated preset or provider voice.
- Keep the recommendation rules visible and machine-readable.

## Mix governance

- Mono remains the default for ordinary narration.
- Stereo is activated only when a declared scene or ambience needs it.
- Simple client vocabulary is `left`, `center`, `right`; numeric pan is an advanced override.
- Use constant-power panning; do not hard-pan ordinary dialogue by default.
- Spatial placement represents a stable scene, not decorative movement.
- One background ambience bed is enough for the current contract.
- Voice intelligibility takes priority over ambience realism.
- `ducking: speech` may lower ambience during speech; it must remain subtle.
- Normalize only the final master.

## Asset governance

- `ambience.file` is a local/snapshotted production input relative to the program file.
- Do not accept arbitrary HTTP(S) URLs in the render contract.
- Web search is discovery, not rendering.
- Production ambience must have known provenance, licence, and content hash before durable publication.
- Curated reusable ambience packs may be added as data later; do not create a separate asset service without evidence.

## Engineering rules

- Keep dependencies minimal.
- Product-specific exceptions are architecture defects; do not add them here.
- A batch failure must not destroy successful outputs.
- Voice synthesis is the expensive remote stage; keep its cache independent from placement and mixing.
- Ambience preparation and final mix are local deterministic stages.
- Final spoken-word output defaults to `speech`: MP3, mono, 24 kHz, 80 kbit/s.
- Stereo `speech` uses at least 96 kbit/s automatically.
- Keep provider code behind the provider boundary.
- Record engine version, provider, profile, source hashes, stage-cache information, and output properties in `manifest.json`.
- Run offline smoke tests before merging rendering changes.
- Network/provider smoke is useful evidence but must not make ordinary CI brittle.

## Privacy

The current Edge provider is remote. Never imply that input text stays local.
