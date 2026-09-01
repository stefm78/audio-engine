# Production Manifest v1

Production Manifest v1 is the executor-neutral boundary between a consumer repository and Audio Engine.

It is deliberately product-agnostic. A consumer may call its units scenes, chapters, lessons, or anything else; the engine sees only independently renderable `units`, ordered `assemblies`, and one ordered `master`.

## Invariants

- `engine_ref` is an exact 40-character Git commit SHA.
- Every unit declares a provider. There is no implicit provider fallback.
- A `ready` unit pins a workspace-relative Program and voice pack by SHA-256.
- A `hold` unit carries an explicit reason and may remain incomplete without blocking unrelated units.
- Every unit belongs to exactly one assembly.
- The master includes every assembly exactly once.
- `production plan` is offline and verifies hashes before expensive rendering.
- Cache state is not part of the manifest and never changes correctness.

Example:

```json
{
  "schema_version": 1,
  "id": "story-v1",
  "engine_ref": "1111111111111111111111111111111111111111",
  "units": [
    {
      "id": "scene-01",
      "state": "ready",
      "provider": "edge",
      "program": "programs/scene-01.json",
      "program_sha256": "<sha256>",
      "voice_pack": "voices/production.json",
      "voice_pack_sha256": "<sha256>"
    },
    {
      "id": "scene-02",
      "state": "hold",
      "provider": "local-expressive-v1",
      "hold_reason": "voice package not promoted"
    }
  ],
  "assemblies": [
    {"id": "block-a", "units": ["scene-01", "scene-02"]}
  ],
  "master": {"assemblies": ["block-a"]}
}
```

Commands:

```bash
audio-engine production validate path/to/production.json
audio-engine production validate path/to/production.json --verify-files --workspace-root .
audio-engine production plan path/to/production.json --workspace-root .
```

The plan output is designed to feed the same shard executor contract on GitHub-hosted runners or a future persistent worker. Executor selection is operational policy, not manifest semantics.
