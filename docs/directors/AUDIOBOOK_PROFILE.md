# Audiobook Production Director profile

This profile extends the common [Production Plan v1](PRODUCTION_PLAN_V1.md) with Audiobook-only consumer context.

## Required product context

| Field | Purpose |
| --- | --- |
| `book_id` | stable work id |
| `part_id` | part/section identity |
| `chapter_id` | chapter identity |
| `scene_id` | current scene identity |
| `arc_position` | semantic position in the local narrative arc |
| `continuity_scope` | scope in which casting/performance continuity must hold |
| `sound_density` | sparse/moderate/rich authoring policy |
| `narrator_pace_policy` | long-form pacing policy retained by the director |
| `chapter_assembly_id` | consumer assembly identity |

These fields stay outside Audio Engine.

## Director rules

- Preserve narrator and character continuity across chapters.
- Avoid accumulating effects simply because the engine can render them.
- Long-form fatigue matters more than local spectacle.
- Prefer sparse sound design unless a scene earns a stronger treatment.
- Performance intent belongs to the director; Audio Engine executes the resolved Program.
- Chapter hierarchy and assembly metadata remain consumer concerns.
- Use measured rendered duration and levels for final continuity checks.

The fixture in `examples/directors/audiobook-scene.*` uses a single short `acoustic-accent` and therefore compiles to the lowest sufficient schema, v4.

Status:

```text
AUDIOBOOK_PROFILE_DEFINED
```
