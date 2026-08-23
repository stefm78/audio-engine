# Ambience discovery and qualification

Audio Engine separates **broad discovery** from **validated production sounds**. It is not a crawler and rendering never downloads from the Web.

## Commands

Candidate discovery and intake:

```bash
audio-engine ambience discover "quiet cathedral room tone"
audio-engine ambience discover "forest at dawn" --source freesound --source pixabay

audio-engine ambience qualify assets/cathedral.wav \
  --id cathedral-calm-candidate \
  --source-provider "Provider name" \
  --source-page "https://provider.example/asset/123" \
  --source-identifier "123" \
  --license "CC0-1.0" \
  --raw-redistribution allowed \
  --tag interior --tag calm
```

Validated production collection:

```bash
audio-engine sounds
audio-engine sounds --type ambience --tag interior
audio-engine sounds --type event --tag bell
```

The legacy `audio-engine ambiences` command remains available for schema-v2 compatibility. New reusable production resources should converge on the generic `sounds` meta-index described in [`SOUNDS.md`](SOUNDS.md).

## Candidate workflow

```text
many Web/catalog sources
        ↓
ambience discover
        ↓
human/agent download outside render
        ↓
ambience qualify
        ↓
licence + listening + suitability review
        ↓
validated sounds meta-index
        ↓
schema-v3 soundscape
```

`ambience discover` performs **zero network requests** itself. It turns a semantic query into a machine-readable plan across known sources.

`ambience qualify` operates only on an already-downloaded local file and records technical evidence such as SHA-256, duration, codec/sample-rate/channel information, declared provenance, licence and redistribution posture.

A successful probe **never means approved**. Candidate output remains ineligible until rights, listening, speech-masking, context, loopability where relevant, and durable asset strategy are reviewed.

## Broad discovery surface

The current source registry covers Openverse, Wikimedia Commons, Freesound, Pixabay Sound Effects, ZapSplat, Mixkit, Sonniss GameAudioGDC, Free To Use Sounds, Soundly, BOOM Library, Pro Sound Effects and Pond5.

This is a discovery surface, not an allow-list. Provider reputation never replaces checking the exact asset licence.

The sourcing rule is:

> Search widely. Qualify strictly. Produce from exact locked content.

## Promotion into `sounds`

A reusable ambience/event is promoted only after:

1. provenance identified;
2. exact per-asset licence verified;
3. SHA-256 captured;
4. listening quality reviewed;
5. suitability behind spoken audio reviewed;
6. contextual/historical fit reviewed where applicable;
7. loopability/speech masking recorded where relevant;
8. durable, licence-compliant asset materialization established.

The public `sounds` catalog then enforces `status: validated`, verified licence metadata, exact content hash and locked asset information. At render time, a catalog id is accepted only if its materialized local file matches the recorded SHA-256.

## Snapshot and redistribution

Two cases must remain distinct:

1. **Redistributable originals** — suitable CC0/open assets may be snapshotted in shared durable storage when permitted.
2. **Production-only licensed originals** — many commercial royalty-free libraries allow embedding in a finished mix but forbid raw redistribution. Their source files must stay in authorized storage and must not be republished standalone.

`asset.location` can document a validated asset that is not currently materialized. Rendering by catalog id requires a local `asset.file` available in the authorized workspace.

## Legacy schema-v2 ambience

Schema v2 still accepts one local relative `ambience.file` with gain, loop, fades and speech ducking. It is preserved for backward compatibility.

Schema v3 `soundscape` is the forward path for richer environments: validated or explicit local ambience resources can act as bed/layers and punctual `event` resources can be placed at explicit timestamps.
