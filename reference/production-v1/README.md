# Production Reference v1

This directory is the first production-director reference package for Audio Engine.

It is a deliberately compact fictional scene, not product content and not a claim about a real historical location. Its purpose is to exercise the reusable Production boundary with one reproducible hard case.

## Files

- `program.json` — full schema-v6 reference Program.
- `probe.json` — smaller representative Program used before committing to the full render.
- `sound-requirements.json` — semantic requirements for the exact sound assets used by both Programs.

## Why there are two Programs

`audio-engine preview` extracts windows from a full render; it is not a cheap pre-render gate.

The director therefore supplies a separate, intentionally small `probe.json` that retains the riskiest interaction: three distinct actors plus an ambience bed and a horse-hooves bridge that starts alone and carries through two measured spoken segments.

The gate sequence is:

```text
full program preflight
        |
probe program preflight
        |
probe render
        |
===== commit =====
        |
full render
        |
automatic structural QA
        |
listening artifacts
        |
human evaluation
```

## Asset policy

The repository does not pretend these sound ids exist in the built-in empty catalog.

The workflow hydrates `sound-requirements.json` from the durable `production-reference-sounds-v1` Release first, then uses the existing autonomous acquisition/qualification path if a resource is missing.

Every selected resource must be:
- technically readable;
- within Audio Engine duration/channel/rate policy;
- machine-verified for licence/provenance;
- content-hash locked;
- materialized locally before preflight/render.

Rendering itself performs no Web asset resolution.

## Reference dimensions exercised

The full Program exercises:
- validated French voice presets;
- stable actor placement;
- continuous texture bed;
- speech ducking;
- punctuation event;
- measured v6 bridge carry;
- scene event with narration-free space;
- safe fades owned by the engine;
- semantic acoustic-space changes;
- measured spoken timing as bridge authority.

The reference deliberately does not claim support for a separate music track because music is not currently a first-class Audio Engine resource type.
