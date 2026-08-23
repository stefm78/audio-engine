# Effects and narrative sound direction

Audio Engine publishes a bounded **capability catalog** so applications can ask the installed engine what it can actually render before authoring sound direction.

```bash
audio-engine capabilities
audio-engine capabilities --category acoustic_spaces
```

The returned JSON is the source of truth for application affordances. Do not hard-code a larger palette than the installed engine advertises.

## Acoustic spaces

The public set remains intentionally small:

| id | Intended perception |
| --- | --- |
| `dry` | close, neutral narration |
| `outdoor-open` | open exterior with no room tail |
| `small-stone-room` | chapel or small masonry volume |
| `large-stone-interior` | nave or large masonry hall |
| `confined-stone` | crypt, cellar or confined masonry volume |

These presets are restrained synthetic early-reflection treatments. They are **not** authentic impulse responses and must not be described as reproducing the acoustics of a named place.

Resolution order is segment → actor → program → `dry`. The TTS cache is always dry; changing acoustic treatment remixes locally without a new TTS call.

### Acoustic accent

An acoustic accent is a **sound-design usage pattern**, not a new DSP slicing primitive. The author deliberately creates a short segment and applies an acoustic space only to that segment. The capability catalog advertises a recommended rendered duration of at most 2500 ms.

This is deliberate: applying reverb to an arbitrary range of milliseconds inside a spoken phrase would push the public contract toward DAW-style automation. If the intended phrase is too long, split the narration semantically.

## Sound roles

The engine exposes four narrative roles:

- `texture` — continuous bed/layer under speech;
- `punctuation` — punctual event that underlines an idea;
- `scene` — event given a narration-free window, then stopped before speech resumes;
- `bridge` — event that owns a real foreground interval, then **continues under the next spoken segment** while ducking and fading out.

### Scene — foreground only

```json
{
  "sound": "historic-horse-hooves",
  "role": "scene",
  "after_segment": 3,
  "space_ms": 3200
}
```

V4 scene semantics remain unchanged for compatibility: `space_ms` is the total narration-free window, including small engine-owned margins.

### Bridge — foreground then carry

Schema v5 adds the transition that scene intentionally did not provide:

```json
{
  "sound": "historic-horse-hooves",
  "role": "bridge",
  "after_segment": 3,
  "foreground_ms": 3500,
  "carry_under_speech_ms": 2500,
  "gain_db": -23,
  "placement": "left"
}
```

`foreground_ms` means the **actual interval between the start of the sound and the restart of narration**. The engine inserts a short pre-roll before the sound begins, then preserves the full declared foreground interval. When speech resumes, the same sound continues for `carry_under_speech_ms`; normal speech ducking lowers it automatically and the bridge receives a longer default fade-out.

A bridge requires a following segment because its purpose is to hand attention back to speech. It is bounded and deterministic; it does not create an arbitrary timeline.

## Fades

Hard cuts are never the default for new narrative roles.

- continuous texture: 1000 ms fade-in, 1500 ms fade-out;
- punctuation: 0 ms fade-in, 250 ms fade-out;
- scene: 180 ms fade-in, 500 ms fade-out;
- bridge: 500 ms fade-in, 1200 ms fade-out.

The engine clamps fades for short assets. A zero fade is accepted only when explicitly authored.

Bridge manifests also report requested versus rendered duration and whether the event was clipped by the source asset or by the master duration. This makes an undersized source visible to QA rather than hiding it.

## Compatibility

V1–v3 behavior is preserved. V4 scene semantics are preserved. `bridge`, `foreground_ms`, and `carry_under_speech_ms` require schema v5 so Audio Engine 0.7 cannot silently accept and ignore the new intention.

## Why the catalog is separate from the sound library

The sound library answers **which validated audio resources are available**. The capability catalog answers **which rendering operations and narrative semantics this engine can perform**. Applications generally need both.

## Explicit non-goals

The catalog still does not expose arbitrary reverb parameters, named-room authenticity claims, HRTF/binaural 3D, front/rear/height positioning, arbitrary plugin chains, random scheduling, or unlimited tracks.

A new public effect belongs here only when the renderer, manifest and tests support it end-to-end.
