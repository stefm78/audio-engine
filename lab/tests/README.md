# Voice Lab tests

These tests exercise reusable Voice Lab primitives only.

They are intentionally outside `tests/` so Production CI does not depend on
Lab code. The manual `Voice Casting Lab` workflow runs this suite before a Lab
campaign.

Production rendering must remain valid if this entire Lab surface is unavailable.
