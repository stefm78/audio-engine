# Voice Lab reference pack v1 — durable archive receipt

Date: 2026-08-28

Status: **DURABLE LAB EVIDENCE — PRODUCTION UNAFFECTED**

## Purpose

This receipt records the durable archive created from the four immutable Voice Casting Lab WAV references before expiry of the source GitHub Actions artifact.

The archive is Lab evidence only. It does not promote any voice or provider to Production.

## Source

- repository: `stefm78/audio-engine`
- source run: `32823632721`
- source artifact id: `9554047730`
- source artifact name: `voice-casting-qwen3-contrast-emotion-killer-recovery`
- source artifact digest recorded by the archive workflow: `sha256:1d913dd1070c3c0d2cc6ba0f2c4b748eed6bcf48a0a9a3a30b5cd4d7f72c3fe0`
- original artifact expiry: 2026-09-08

## Archive production

- archive branch head: `fe090fc968684aab2d29f30a26d38cf3ddf54d36`
- archive workflow: `.github/workflows/archive-voice-lab-reference-pack.yml`
- successful archive run: `33165305338`
- target Production/Lab source SHA: `159fbebc34fd3797595eb1425fbf81c4f4801352`

The archive workflow downloaded the exact source artifact, required the four expected WAV paths, verified all four SHA-256 values, copied only those reference WAVs plus source metadata into the pack, and published a GitHub prerelease.

## Durable release

- release tag: `voice-lab-reference-pack-v1`
- release id: `378425754`
- release target: `159fbebc34fd3797595eb1425fbf81c4f4801352`
- release type: prerelease
- archive asset id: `533667623`
- archive asset: `voice-lab-reference-pack-v1.tar.xz`
- archive asset size: `627464` bytes
- archive asset digest: `sha256:688eaa76d700f6ce5b5410e5fe37fa17877c7673737c31d7a50442304d6a4759`
- checksum asset id: `533667622`
- checksum asset: `voice-lab-reference-pack-v1.tar.xz.sha256`
- checksum asset digest: `sha256:7d55dc294614d6afe3a4f4a86e757d22243bf4b3820e7b5812b20a1cc7b6671c`

GitHub currently reports the release as `immutable: false`. Governance therefore treats the tag, release and assets as read-mostly durable evidence: do not overwrite or delete them without an explicit evidence migration.

## Independent post-publication verification

A separate verification branch downloaded the already-published release assets rather than reading the source Actions artifact.

- verification branch HEAD: `9e54ab2dc09b34da07752b42e4ce617d52617bdd`
- verification workflow: `.github/workflows/verify-voice-lab-reference-pack.yml`
- successful verification run: `33173561027`
- verified archive digest: `sha256:688eaa76d700f6ce5b5410e5fe37fa17877c7673737c31d7a50442304d6a4759`
- post-extraction verdict: `PASS_DURABLE_RELEASE_EXACT_BYTES`

The verification run extracted the durable release archive and independently re-ran SHA-256 checks against all four WAV files. This closes the distinction between "the source bytes were correct before packaging" and "the durable published asset still contains those exact bytes".

## Immutable WAV hashes

```text
reference-claire.wav
3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe

reference-lucie.wav
9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822

clips/claire--panic.wav
ac92fd1f8346b981ac7518e1e698cf8b1c31a96dff069ad60a2d017a17ff9d7f

clips/claire--sadness-contained.wav
d2091868592c3c8691c2c0c6a39adaa3613d4941d087c36e4be69e5395a19c84
```

Frozen panic text:

`Vite ! Ils arrivent ! Fermez la porte !`

Frozen panic source duration: `2.56 s`.

## Copies and authority

- GitHub Release pack: durable independent archive of the temporary Actions artifact.
- NUC reference store: persistent read-mostly safety/cache copy, SHA-256 verified.
- original temporary Actions artifact: no longer required for retention after this receipt and release have been verified.
- Production runtime: no dependency on any of the above.

## Decision

```text
REFERENCE_HASHES_VERIFIED: PASS
NUC_REFERENCE_COPY: PASS
DURABLE_RELEASE_ARCHIVE: PASS
POST_PUBLICATION_EXACT_BYTES: PASS
SOURCE_ARTIFACT_EXPIRY_RISK: CLOSED
PRODUCTION_PROMOTION: NO
PRODUCTION_DEPENDENCY: NONE
```
