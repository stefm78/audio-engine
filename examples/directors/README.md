# Production Director fixtures

These fixtures prove the boundary described by PROD-WP-003.

For each product there are three files:

- `*.plan.json` — consumer-side Production Plan v1;
- `*.program.json` — exact hand-compiled Audio Engine Program;
- `*.disposition.json` — explicit disposition of every Production Plan leaf field.

The repository test `tests/test_production_director_profiles.py` verifies:

- common/profile plan shape;
- exact no-silent-field-loss coverage;
- speaker -> preset resolution;
- text mapping;
- recipe-specific Program shape;
- lowest sufficient Program schema for these examples;
- Audio Engine contract validation;
- offline preflight with zero TTS/network access.

These are interface fixtures, not final product content.

## Binding-mode fixture

`audiobook-scene-ref.plan.json` binds to the existing `audiobook-scene.program.json` by exact Git blob SHA. It intentionally contains no spoken text. This demonstrates the preferred migration/long-form `program-ref` mode without creating a second content authority.
