# Automatic listening previews

`audio-engine ambience qualify` always keeps the downloaded source file as the canonical production candidate and automatically creates a universal MP3 derivative for human listening.

The preview is deliberately non-canonical:

- source SHA-256 remains the production identity;
- preview SHA-256 is recorded only as preview evidence;
- the preview is encoded as MP3 at 160 kb/s and 44.1 kHz for broad player compatibility;
- no listening reviewer should have to transcode OGG, WAV, FLAC or other source formats manually;
- `--preview-dir` can redirect previews to an artifact/listening directory without changing the canonical source.

This automation belongs to qualification, never to render-time asset resolution.
