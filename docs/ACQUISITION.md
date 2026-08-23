# Zero-touch sound acquisition

Audio Engine can resolve a semantic sound request without a human selection step.

```text
semantic request
      ↓
validated sound meta-index
      ├── hit → exact id/hash
      ↓ miss
multi-source discovery
      ↓
upstream metadata verification
      ↓
download + technical qualification
      ↓
deterministic gates + scoring
      ↓
selected candidate above threshold?
      ├── no → continue discovery / degrade gracefully
      ↓ yes
locked local asset + runtime catalog
      ↓
durable consumer Release
      ↓
render from local hash-verified content
```

The rendering command itself remains offline with respect to sound discovery. Network access occurs only in the acquisition/provisioning stage.

## Product-level command

```bash
audio-engine sound ensure "quiet cathedral room tone" \
  --type ambience \
  --id cathedral-calm \
  --prefer-tag cathedral \
  --prefer-tag reverberant
```

`ensure` first checks the validated catalog. A catalog hit performs no network requests. A miss triggers autonomous acquisition.

The stable semantic id is supplied by the consumer or defaults to a slug of the request. Once selected, the id and content hash are frozen; later catalog changes do not silently change an existing declared soundscape.

## Provider policy

Broad discovery and automatic promotion are deliberately different concepts.

- **Wikimedia Commons** is the first fully autonomous provider because Audio Engine can query the upstream MediaWiki API for the original file URL and machine-readable licence metadata.
- **Openverse** is used as a discovery amplifier. Openverse explicitly recommends verification at the original source, so Openverse metadata alone is never final promotion evidence. Openverse results are currently auto-eligible only when they resolve back to a supported Commons source that can be re-queried upstream.
- The broader source registry remains available for discovery. Additional providers become autonomous only when an adapter can obtain enough upstream evidence to enforce the same gates without human review.

A provider failure is isolated. Discovery continues with the remaining providers.

## Automatic gates

A downloaded candidate is rejected automatically when any hard gate fails, including:

- incomplete source provenance;
- licence not verified from a supported upstream API;
- licence outside the automatic allow-list;
- unsupported channel layout;
- sample rate below policy;
- duration outside the policy for `ambience` or `event`;
- required semantic tags missing;
- technical probe failure.

Survivors are scored deterministically using duration suitability, stereo, sample rate, licence friction, discovery rank and preferred semantic tags.

If no candidate reaches the selection threshold, the result is `no-selection` with action `continue-discovery`. A human is not requested to break the tie.

## Audit preview

Qualification still creates a universal MP3 derivative. It exists only for optional debugging/audit:

```text
canonical source → SHA-256 production identity
       └────────→ MP3 audit preview (non-canonical)
```

The preview never participates in promotion or render identity.

## Reusable workflow and durable storage

`.github/workflows/acquire-sound.yml` packages the same policy for GitHub Actions. It can:

1. resolve or acquire a semantic sound;
2. upload acquisition evidence as a CI artifact;
3. publish a selected source file, its mini-catalog and selection proof to a `sound-library` GitHub Release in the caller repository.

This keeps ownership clear:

- Audio Engine owns acquisition, validation and selection semantics;
- the consumer owns its durable binary assets;
- `render` consumes only local, hash-verified files.

## Complexity boundary

Audio Engine does not become a general crawler. Each autonomous provider is a small explicit adapter with bounded result counts, HTTPS-only downloads, a size cap and provider-specific evidence rules.

The governing rule is:

> Search broadly, verify upstream, select automatically, freeze exact content, render offline.
