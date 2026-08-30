# Audioguide Production Director profile

This profile extends the common [Production Plan v1](PRODUCTION_PLAN_V1.md) with Audioguide-only consumer context.

## Required product context

| Field | Purpose |
| --- | --- |
| `station_id` | stable stop/station id |
| `location_label` | human-facing place label |
| `visual_cue` | what the listener should look at |
| `target_duration_s` | desired listening duration |
| `max_duration_s` | hard editorial ceiling |
| `resume_after_beats` | safe restart points after interruption |
| `listening_environment` | e.g. `outdoor-noisy`, used by the director to favor intelligibility |
| `next_step` | route/navigation metadata |
| `optional_content_policy` | what to drop under time pressure |

These fields stay outside Audio Engine.

## Director rules

- Speech intelligibility wins over decorative sound design.
- A visual instruction must occur while it is still useful at the physical station.
- Prefer short, restart-friendly beats.
- Treat the real-world environment as part of the listening context.
- Target duration is editorial guidance; measured rendered duration is the final audio authority.
- Route metadata never enters the renderer.
- If optional content threatens the station maximum, omit it before increasing speech speed beyond the intended character/narrator style.

The fixture in `examples/directors/audioguide-station.*` intentionally compiles to Program schema v1 because no higher Audio Engine capability is needed.

Status:

```text
AUDIOGUIDE_PROFILE_DEFINED
```
