# Open/local expressive TTS challengers

Status: Voice Casting Lab research only. Production remains on the validated Edge path.

## Current arbitration — 2026-08-24

The project optimizes for a **character**, not an isolated impressive line. Qualification order is therefore:

1. correct, natural French;
2. stable character identity across lines and emotions;
3. convincing acting;
4. operational simplicity and reproducibility;
5. age/lineage only after identity and emotion are independently qualified.

A model that clearly fails an identity or French gate is not rescued through broad parameter tuning. At most one narrow confirmation is allowed for a predeclared borderline result.

For French reference anchors, dedicated `fr-FR` Edge voices are the safe baseline. A targeted sentinel campaign found the dedicated French voices clean while the tested `Multilingual` Edge voices intermittently switched to foreign pronunciation. Multilingual voices therefore remain laboratory candidates only and must not seed a French character identity anchor.

## Challenger status

### Chatterbox Multilingual V3 — eliminated

Chatterbox demonstrated strong acting on the initial hard probes but did not preserve character identity reliably when the emotional range was extended.

Decision: **eliminated for stable-character rendering**. Do not restart tuning.

### CosyVoice 3 — eliminated

CosyVoice 3 won the two initial acting comparisons but failed both identity checks against the reference character.

Decision: **eliminated for stable-character rendering**. Do not restart tuning.

### VoxCPM2 — eliminated

VoxCPM2 initially looked unusually promising: it beat Edge on acting while preserving identity in the first killer, then passed a broader two-character Stage 2. A later French-integrity investigation showed that the original multilingual Edge anchors were contaminated, so a clean confirmation was run with dedicated French anchors (Denise + Henri).

Clean-anchor human result:

- acting: VoxCPM2 `1/4`, Edge `1/4`, neither convincing `2/4`;
- French: one eliminatory VoxCPM2 defect;
- identity: `2/2` correct.

Decision: **eliminated**. Identity preservation is interesting research evidence, but French robustness and acting generalization are insufficient. Do not reopen a tuning loop.

The separate VoxCPM2 age-lineage experiment also failed its age-control gate (`1/6` requested ages perceived correctly) despite strong identity recognition. Age transformation by that method is not qualified.

### Qwen3-TTS VoiceDesign 1.7B — excellent acting, identity strategy eliminated

Pinned research source: `QwenLM/Qwen3-TTS` at `022e286b98fbec7e1e916cb940cdf532cd9f488e`.

VoiceDesign human result on two deliberately similar French female characters:

- acting: Qwen3 `4/4` vs dedicated-fr Edge controls;
- French: `4/4` at least equivalent, zero invalid-French veto;
- identity ABX: `2/4` correct.

Decision: the **identity-by-description + fixed seed strategy is eliminated**. The result nevertheless establishes that Qwen3 has a very strong French expressive signal worth preserving through a more explicit speaker-identity mechanism.

### Qwen3-TTS Base 1.7B — x-vector stable-identity experiment, borderline

The Base model exposes `x_vector_only_mode=True`, where only the frozen speaker embedding is used; reference speech codes and reference text are not carried as ICL style conditioning. This directly tests the desired separation between **who is speaking** and **how the line is performed**.

The experiment reused byte-for-byte the two VoiceDesign reference anchors; characters were not redesigned.

First human result:

- acting: Qwen3 x-vector `4/4` vs dedicated-fr Edge controls;
- French: `4/4` equivalent, zero invalid-French veto;
- identity ABX: `3/4` correct.

This is **BORDERLINE, not PASS**. The single miss was Claire under panic. Per the predeclared rule, exactly one narrow high-arousal identity confirmation was generated with the same frozen anchors and no tuning.

Canonical confirmation run: `32772435007`  
Artifact: `voice-casting-qwen3-xvector-identity-confirm`  
Output: two new high-arousal clips + the two frozen references.  
Human decision still required: `2/2` identity plus no French defect to qualify this architecture in the Lab.

No production promotion is implied by a confirmation pass.

## Next decision tree

If the narrow Qwen3 x-vector confirmation passes, the next work is a **minimal Lab-only character contract**: frozen character anchor / speaker prompt + generated line, followed by a small composition test across a broader emotional set. Production Edge remains unchanged until an explicit later promotion gate.

If the confirmation fails, the x-vector stable-character strategy is eliminated without tuning. A distinct architecture may then be evaluated, but only after verifying French support, licensing, identity mechanism and operational cost. Do not resurrect Chatterbox, CosyVoice or VoxCPM2 tuning.

## Governance

No open model is promoted by benchmark generation alone. Promotion requires human listening evidence for:

1. French pronunciation;
2. naturalness;
3. identity continuity;
4. acting fit on difficult intentions;
5. long-form fatigue;
6. operational simplicity/reliability;
7. reproducible provenance and graceful fallback.

Heavy ML dependencies stay outside the production Audio Engine dependency graph unless a later promotion decision explicitly changes that boundary.
