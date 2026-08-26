# Voice Lab resource admissibility

Effective 2026-08-26 after the RVC GPU handover boundary was reached.

## Hard rule

Before a new scientific architecture receives expensive corpus, tuning, or training work, its next decisive experiment MUST be executable on resources already available to this project, or have a pre-proven zero-cost external execution path requiring no user-provided hardware.

A design that reaches an unavailable hardware boundary after substantial preparatory work is an architecture/governance defect, even when its science remains valid.

## Current admissible execution classes

1. GitHub-hosted CPU Actions / ordinary CPU-compatible inference: admissible.
2. Reuse of immutable existing Lab artifacts: preferred.
3. Free ephemeral notebook GPU may be retained as a fallback, but MUST NOT become the sole active path until complete end-to-end execution and return-of-evidence are proven.
4. User-provided or self-hosted CUDA: unavailable; MUST NOT be assumed.
5. Paid GPU services: not assumed.

## Scientific consequence

The qualified Lucie RVC corpus and frozen RVC package remain valid evidence, but RVC is parked at `dataset-pass` / GPU-handover while its required execution resource is unavailable.

The active successor search must prioritize zero-training or CPU-feasible identity architectures and apply the same ordering:

`identity > expressivity > compute`, with French/content as a hard killer gate.

No threshold relaxation, opportunistic tuning, retry/substitution, Production/Edge/Pages change, or resurrection of scientifically retired architecture families is authorized by this resource amendment.
