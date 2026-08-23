# Ambience catalog

Audio Engine exposes a small **curated ambience catalog**, not a Web search engine and not a repository of arbitrary audio files.

## Commands

```bash
audio-engine ambiences
audio-engine ambiences --tag interior
audio-engine ambiences --tag interior --tag calm
audio-engine ambiences --id cathedral-calm
```

The output is JSON so humans, agents, Audioguide, Learn-it, or other clients can consume the same collection metadata.

## Current state

The catalog may legitimately contain zero entries. An ambience is added only after all production gates are satisfied:

1. provenance identified;
2. licence verified;
3. content hash captured;
4. listening quality reviewed;
5. suitability as a background bed reviewed;
6. loopability recorded when relevant;
7. durable production snapshot strategy established.

A small curated catalog is preferable to an impressive but unreliable sound library. Discovery, however, must be broad.

## Broad discovery, narrow promotion

The sourcing rule is:

> Search widely. Qualify strictly. Produce from a locked asset.

Discovery should not be limited to one or two websites. Useful source families include:

### Open / broadly redistributable discovery

- Openverse — cross-provider discovery of openly licensed audio; verify the upstream licence before promotion;
- Wikimedia Commons — strong provenance and open licences, but uneven ambience coverage;
- Freesound — very broad field-recording community with CC0 / CC BY / CC BY-NC assets; filter licence deliberately;
- Internet Archive and other open archives may be searched when a specific recording is relevant, with per-item licence verification.

### Free / royalty-free production libraries

- Pixabay — large royalty-free sound-effects catalogue; raw standalone redistribution restrictions must be respected;
- Mixkit — free commercial-use sound effects, useful for common ambience categories;
- ZapSplat — large catalogue, including some CC0 material plus provider-specific licensed sounds;
- Sonniss #GameAudioGDC — professional royalty-free giveaway archives; raw standalone redistribution is not allowed.

### Professional field-recording and SFX libraries

- Free To Use Sounds — high-resolution real-world and immersive field recordings;
- Soundly — large searchable cloud library and add-on ecosystem;
- BOOM Library — studio-grade professional SFX and ambience libraries;
- Pro Sound Effects — professional commercial SFX catalogue;
- Pond5 and similar stock-audio marketplaces — useful fallback when a precise ambience cannot be sourced elsewhere.

This list is a discovery surface, not an allow-list. A provider name never substitutes for checking the licence of the exact asset.

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

A future qualified entry should look broadly like:

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
