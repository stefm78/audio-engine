# Ambience catalog

Audio Engine separates **broad discovery** from the small **curated ambience catalog** used in production. It is not a crawler and not a repository of arbitrary audio files.

## Commands

Curated production catalog:

```bash
audio-engine ambiences
audio-engine ambiences --tag interior
audio-engine ambiences --tag interior --tag calm
audio-engine ambiences --id cathedral-calm
```

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

All command output is JSON so humans, agents, Audioguide, Learn-it, or other clients can use the same evidence.

`ambience discover` performs **zero network requests**. It turns one semantic query into a machine-readable plan across the known sourcing surface, including direct search URLs where a stable provider search URL is known. Humans or agents perform the actual Web search outside the rendering process.

`ambience qualify` operates only on a file that has already been downloaded under the applicable terms. It probes the local asset and records:

- SHA-256 and byte size;
- codec;
- sample rate;
- channel count when identifiable;
- duration;
- declared source/provider metadata;
- declared licence and redistribution mode;
- pending listening, loopability, speech-masking, licence-verification and snapshot gates.

A successful technical probe **never means the asset is approved**. Qualified output deliberately remains `status: candidate` and `promotion.eligible: false` until the human/editorial and rights gates are completed.

## Broad discovery, narrow promotion

The sourcing rule is:

> Search widely. Qualify strictly. Produce from a locked asset.

Discovery should not be limited to one or two websites. The machine-readable source registry currently covers:

- Openverse;
- Wikimedia Commons;
- Freesound;
- Pixabay Sound Effects;
- ZapSplat;
- Mixkit;
- Sonniss GameAudioGDC;
- Free To Use Sounds;
- Soundly;
- BOOM Library;
- Pro Sound Effects;
- Pond5.

The registry is a discovery surface, not an allow-list. A provider name never substitutes for checking the licence of the exact asset.

## Promotion gates

An ambience enters the curated catalog only after all production gates are satisfied:

1. provenance identified;
2. licence verified;
3. content hash captured;
4. listening quality reviewed;
5. suitability as a background bed reviewed;
6. loopability recorded when relevant;
7. speech masking checked;
8. durable production snapshot strategy established.

A small curated catalog is preferable to an impressive but unreliable sound library. Discovery, however, should remain broad.

## Web discovery versus production

Web search/download is intentionally outside the `render` contract.

A production program uses a local relative `ambience.file`. The file may be:

- a product-specific recording owned by the consumer;
- a snapshot of a qualified Web asset;
- later, a materialized member of a shared curated ambience pack.

Playback never depends on the third-party source: the ambience is mixed into the final master.

## Snapshot and redistribution rule

Two asset classes must be treated differently:

1. **Redistributable source assets** — for example CC0 or suitable CC BY material. The original may be snapshotted in a durable shared location when the licence permits it and attribution obligations are preserved.
2. **Production-only licensed assets** — many royalty-free commercial libraries permit use inside a finished production but forbid redistribution of the raw sound. These originals must not be committed to a public repository or public Release as standalone files. Keep the licensed source in an appropriate private/local asset location and publish only the resulting mixed production plus provenance metadata permitted by the licence.

The engine does not need to know which storage product is used. It only receives the qualified local file at render time.

## Licence policy

Initial automated policy is deliberately conservative:

- CC0 / public-domain equivalent: suitable after provenance and quality checks;
- CC BY: suitable after attribution requirements are captured;
- CC BY-SA: manual review;
- provider-specific royalty-free licences: manual review of the exact asset and raw-redistribution rules;
- NC or ND restrictions: rejected by default for the shared generic catalog.

The catalog policy is machine-readable in `ambiences.json`; it is guidance, not legal advice.

## Entry shape

A promoted entry should look broadly like:

```json
{
  "id": "cathedral-calm",
  "label": "Cathedral — calm room tone",
  "tags": ["interior", "calm", "stereo", "loopable"],
  "source": {
    "provider": "qualified provider",
    "identifier": "provider asset id",
    "page": "canonical source page"
  },
  "license": {
    "id": "CC0-1.0",
    "verified": true,
    "attribution": null
  },
  "content_sha256": "...",
  "audio": {
    "channels": 2,
    "loopable": true
  },
  "defaults": {
    "gain_db": -22,
    "ducking": "speech"
  },
  "snapshot": {
    "status": "locked",
    "location": "consumer/shared durable asset location"
  }
}
```

Adding such an entry must not require changing the mixer or consumer application code.

## Client responsibility

Clients should expose semantic choices, for example:

```text
Ambience: None / Cathedral / Forest / Street / Classroom
Level: Subtle / Normal / Present
```

They should not expose provenance URLs, codecs, channel gains, or FFmpeg settings to ordinary users.
