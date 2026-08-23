# Agent guidance

## Purpose

Audio Engine converts a declared structured audio program into audio assets and a machine-readable manifest. It also publishes the validated voice palette and recommends suitable presets from declared vocal traits.

## Non-goals

Do not add:
- audioguide-specific behavior;
- Learn-it-specific behavior;
- content authoring or generation;
- permanent audio storage or GitHub Release publishing;
- web UI, backend, database, accounts, queues, or job dashboards.

Consumers own their content, publication, storage, and playback experience.

## Stable boundary

Schema v1 is a public contract. Preserve backward compatibility unless a new schema version is explicitly introduced.

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

## Engineering rules

- Keep dependencies minimal.
- Product-specific exceptions are architecture defects; do not add them here.
- A batch failure must not destroy successful outputs.
- Intermediate TTS clips are temporary.
- Final spoken-word output defaults to `speech`: MP3, mono, 24 kHz, 80 kbit/s.
- Normalize only the final assembled output.
- Keep provider code behind the provider boundary.
- Record engine version, provider, profile, source hash, and output properties in `manifest.json`.
- Run offline smoke tests before merging rendering changes.
- Network/provider smoke is useful evidence but must not make ordinary CI brittle.

## Privacy

The current Edge provider is remote. Never imply that input text stays local.
