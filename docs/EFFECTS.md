# Effects and narrative sound direction

Audio Engine 0.7 adds a bounded **capability catalog** and schema-v4 narrative sound direction.

The design goal is not to expose studio parameters. Applications ask what the engine can do, then author semantic intent.

```bash
audio-engine capabilities
audio-engine capabilities --category acoustic_spaces
```

The returned JSON is the source of truth for application affordances. Do not hard-code a larger UI palette than the installed engine advertises.

## Acoustic spaces

The initial set is intentionally small:

| id | Intended perception |
| --- | --- |
| `dry` | close, neutral narration |
| `outdoor-open` | open exterior with no room tail |
| `small-stone-room` | chapel or small masonry volume |
| `large-stone-interior` | nave or large masonry hall |
| `confined-stone` | crypt, cellar or confined masonry volume |

These presets are restrained synthetic early-reflection treatments. They are **not** authentic impulse responses and must not be described as reproducing the acoustics of a named place.

Resolution order is:

1. segment `acoustic_space`;
2. actor `acoustic_space`;
3. program `acoustic_space`;
4. `dry`.

The TTS cache is always dry. Changing an acoustic-space preset must remix locally without a new TTS call.

## Sound roles

There are only three narrative roles:

- `texture` — continuous bed/layer under speech;
- `punctuation` — punctual event that underlines an idea;
- `scene` — punctual event intentionally given narration-free time because the sound itself carries information or emotion.

A v4 `scene` is anchored to a segment rather than an absolute timestamp:

```json
{
  "sound": "historic-horse-hooves",
  "role": "scene",
  "after_segment": 3,
  "space_ms": 3200,
  "gain_db": -18,
  "placement": "left"
}
```

Audio Engine reserves at least `space_ms` after the referenced segment. The scene starts after a short internal pre-roll and ends before a short post-roll. If the source is longer than the available window it is trimmed with a safe fade-out.

## Fades

Hard cuts are not the default in v4.

- continuous texture: 1000 ms fade-in, 1500 ms fade-out by default;
- punctuation: 0 ms fade-in, 250 ms fade-out by default;
- scene: 180 ms fade-in, 500 ms fade-out by default.

The engine clamps fades when an asset is shorter than the requested transition. An author may explicitly set a fade duration to `0` when a hard edge is narratively intentional.

V1–v3 behavior is preserved. V4-only event fields are rejected by lower schema versions so an older engine cannot silently ignore sound direction.

## Why the catalog is separate from the sound library

The sound library answers:

> Which validated audio resources do I have?

The capability catalog answers:

> Which rendering operations and narrative semantics can this engine perform?

Applications generally need both.

## Explicit non-goals

The current catalog does not expose:

- arbitrary reverb parameters;
- named-room authenticity claims;
- HRTF or binaural 3D;
- front/rear/height positioning;
- arbitrary plugin chains;
- random scheduling;
- unlimited tracks.

A new public effect should be added only when the renderer, manifest and tests support it end-to-end.
