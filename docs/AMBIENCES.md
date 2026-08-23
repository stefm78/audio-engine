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

A small empty catalog is preferable to an impressive but unreliable sound library.

## Web discovery versus production

The policy is:

> Discover on the Web. Qualify once. Produce from a locked asset.

Web services such as Wikimedia Commons or Openverse can help find candidates, but Web search/download is intentionally outside the `render` contract.

A production program uses a local relative `ambience.file`. The file may be:

- a product-specific recording owned by the consumer;
- a snapshot of a qualified Web asset;
- later, a materialized member of a shared curated ambience pack.

Playback never depends on the third-party source: the ambience is mixed into the final master.

## Licence policy

Initial automated policy is deliberately conservative:

- CC0 / public-domain equivalent: suitable after provenance and quality checks;
- CC BY: suitable after attribution requirements are captured;
- CC BY-SA: manual review;
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
    "provider": "Wikimedia Commons",
    "identifier": "File:Example.flac",
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
