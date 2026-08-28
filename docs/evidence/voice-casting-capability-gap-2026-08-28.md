# Voice Casting Lab — capability gap and reopening rules — 2026-08-28

Status: **LAB EVIDENCE ONLY — CAPABILITY GAP / WATCH**

Production Edge remains unchanged.

Baseline: `main@f039f497d5a7f4ff64c9f159c613c32db40d8a6a`.

## Objective

The unresolved target is deliberately strict:

1. French must remain intelligible and natural.
2. The character must remain immediately recognizable.
3. High-arousal panic/fear must be convincingly expressed.
4. Speaker identity and emotion must be independently controllable.
5. The path must be reproducible and usable with permissive/open licensing.
6. The research path must be executable on the available standard CPU environment unless a future resource decision explicitly changes that constraint.

Priority remains:

**character identity > expressivity > compute**

The Lab does not accept best-of-N selection, seed search, broad parameter sweeps, post-result threshold changes or DSP/VC rescue loops as evidence of a qualified architecture.

## Frozen scientific protocol

For a new one-cell candidate:

1. preregister exact model/code/weights, reference, text, seed and emotion settings;
2. create exactly one scientific render;
3. technical gate;
4. independent WeSpeaker gate: Claire similarity > Lucie similarity;
5. Whisper Small French WER <= 0.5;
6. frozen SUPERB source-relative gate: candidate closer to immutable panic than immutable contained sadness;
7. blind human identity + acting + French only after machine 4/4 PASS.

No retry, replacement seed or tuning is authorized after a scientific render.

Immutable current references:

- Claire neutral: `3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe`
- Lucie neutral: `9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822`
- Claire panic: `ac92fd1f8346b981ac7518e1e698cf8b1c31a96dff069ad60a2d017a17ff9d7f`
- Claire contained sadness: `d2091868592c3c8691c2c0c6a39adaa3613d4941d087c36e4be69e5395a19c84`
- frozen text: `Vite ! Ils arrivent ! Fermez la porte !`

## Current evidence

### Chatterbox Multilingual V2 — closest end-to-end result, human acting fail

PR/run evidence: #149 / run `33051484957`.

Machine:

- technical PASS;
- identity PASS: Claire `0.7764995` vs Lucie `0.5258361`, margin `+0.2506634`;
- French PASS, WER 0;
- source-relative emotion PASS: panic `0.9790397` vs sadness `0.9454065`, margin `+0.0336332`.

Human blind:

- identity PASS;
- French PASS;
- **acting FAIL**.

Decision: do not tune exaggeration/seed. Later scalar-exaggeration variants did not establish a stable panic degree of freedom.

### Qwen3-TTS Pure-C x-vector — identity/French strong, emotion reject

PR/run evidence: #159.

- identity PASS, margin `+0.2356448955`;
- French WER 0;
- emotion REJECT: panic `0.6316704041` vs sadness `0.9387430170`, margin `-0.3070726129`.

Decision: x-vector identity reinforcement does not solve high-arousal panic.

### Qwen3-TTS Pure-C qvoice graft — identity/French strong, emotion worse

PR/run evidence: #166 resource PASS, #167 scientific cell / run `33120631545`.

Candidate SHA:
`f642524ca9de2a1e1e5a8189602fca2097541bdece8696e980a23d3f727c24e1`

- technical PASS;
- identity PASS: Claire `0.7412390501373979`, Lucie `0.515245039252663`, margin `+0.22599401088473492`;
- French WER 0;
- emotion REJECT: panic `0.47667729672827563`, sadness `0.8582708508437057`, margin `-0.38159355411543006`.

Decision: stronger speaker/timbre conditioning reinforces identity but not panic.

### WORLD/PyWORLD prosody transplant — technical reject

PR #168.

Exactly one WORLD source-filter resynthesis used:

- Chatterbox #149 as timbre carrier;
- immutable panic source as F0/duration/relative-energy donor;
- carrier spectral envelope + aperiodicity retained.

Pre-write result:

- duration `2.565 s` vs donor `2.56 s`;
- RMS `0.10266987005156715`;
- finite;
- absolute pre-write peak `1.2629717409181032`.

The preregistered contract forbade normalization/gain rescue.

Decision: **TECHNICAL REJECT — PRE-WRITE CLIPPING**. No second resynthesis.

### ZONOS2 — new affect-axis architecture, emotion reject

PR #169 resource PASS.

PR #170 scientific cell / run `33147461857`.

Frozen affect hypothesis used only shipped axes:

- valence `-1.0`;
- arousal `+1.0`;
- strength `1.0`;
- emotion CFG `1.5`;
- expressive mode;
- seed 1;
- Q4_K CPU pipeline.

Candidate SHA:
`37b5dd6a2be7a952f009a8352b54b93cfc07ae4350fcefcdeb93be5f07f83113`

Machine:

- technical PASS;
- identity PASS: Claire `0.14835496996476455`, Lucie `0.12443191195025949`, margin `+0.02392305801450506`;
- French PASS: transcript `BIT ! Ils arrivent ! Fermez la porte !`, WER `0.16666666666666666`;
- emotion REJECT: panic `0.6172165586842894`, sadness `0.9319082135806375`, margin `-0.3146916548963481`.

Decision: negative-valence/high-arousal affect axes still produced a sadness-like acoustic profile.

### Marco-Voice — architecture attractive, public CPU release not executable without patch cascade

PR #171.

Why it mattered:

- arbitrary speaker reference;
- separate emotion embedding in the same synthesis path;
- upstream publishes a native `Fearful` embedding;
- Apache-2.0;
- multilingual/cross-lingual claims.

Frozen resources:

- code `ATH-MaaS/Marco-Voice@669d5afca063875a365522e87134a8c06cdd1e8e`;
- model `ATH-MaaS/Marco-Voice@813ab3b80d52d9e94e7a9e86ea2fe4df161052a4`, `marco_voice_enhenced`;
- official emotion asset `emotion_info.pt` SHA `8d66ae02c5d65c7690416776c08bf6d9b8c835b6bdb1adc30c3a35b20800c0d9`;
- exact key `female003/Fearful`;
- `fp16=False`, CPU.

One deterministic source repair was preregistered because upstream `encoder.py` used `nn.Linear` without importing `nn`.

After dependency completion and that single repair, the actual LLM synthesis path was reached.

Second distinct upstream source defect:

`cosyvoice_rodis/llm/llm.py` unconditionally converts the emotion embedding to `torch.float16` even under documented `fp16=False`.

CPU LLM weights remain Float32, causing:

`RuntimeError: mat1 and mat2 must have the same dtype, but got Half and Float`

The source-repair budget was exactly 1. No second source patch was authorized.

Authoritative final run:
`33157052517`

Evidence artifact:
`9680189307`

Digest:
`sha256:b8730a5da619cd6148c5c29450aba797d05eb57d61059438627739967b41373f`

Decision: **RESOURCE FAIL**. No Claire/Lucie scientific render.

## Other families already retired / non-admissible

Do not reopen unless the external capability itself materially changes.

- OpenVoice V2: identity/french useful, panic expression failure.
- Chatterbox V3 scalar exaggeration: emotion reject.
- ChatterboxVC/S3Gen: post-hoc VC and French/repro issues.
- Seed-VC: post-hoc VC/licensing mismatch.
- MeanVC2: French reject.
- CosyVoice3 prior killer: technical duration reject.
- VoxCPM2: identity reject.
- Zonos v0.1: emotion reject.
- Fish S2 Pro: non-commercial license and CPU preflight failures.
- Wren 0.5B: technical reject and CC-BY-NC.
- FireRedTTS3: clone and voice-design/emotion paths are not a single arbitrary-reference + emotion path.
- IndexTTS-2.5: independent `afraid` control and cloning are architecturally attractive, but current official language coverage does not include French.
- TED-TTS: ideal emotion-vector + speaker prompt topology, but IndexTTS backbone language coverage does not establish French.
- dots.tts.edit: emotion editing is public, but current edit checkpoint supports English/Mandarin rather than French.
- Step-Audio-EditX: emotion editing attractive, but current French support is not established and available compute path is GPU-heavy.
- MOSS-TTS v1.5 / Local: French cloning is strong but no independent fear condition.
- MOSS-VoiceGenerator: emotion/style control but no arbitrary speaker reference; released model is Chinese/English.
- OmniVoice: multilingual cloning but no emotion vocabulary.
- Audio8: French cloning but no independent emotion channel.
- KugelAudio open: current release removed raw arbitrary voice cloning.
- XTTS-v2: French and internally separated identity/style signals, but CPML non-commercial weights and no viable commercial licensing path.
- F5-TTS Emotional CFG: no Fear class and French weights are not permissive for the intended trajectory.
- GPT-SoVITS mainstream path: style/emotion remains driven by the reference prompt; no qualified French arbitrary-speaker + independent fear control.
- GSV-TTS-Lite: timbre/style dual-reference is attractive, but current release supports Chinese/Japanese/English only.
- NVIDIA Magpie: Multilingual model has French emotional built-in voices but no zero-shot cloning; Zeroshot model clones arbitrary voices but does not expose the same independent emotional style control for that arbitrary clone.
- Aurora-1.6B community model: published demo path uses predefined x-vectors rather than demonstrated arbitrary reference cloning and does not expose a validated independent emotion path.
- Luna-TTS current release: no French in published language set.
- Higgs Audio 2.5 1B: public executable weights required for this use case are not currently available.
- FlexiVoice / ReStyle-TTS / FC-TTS / SwanTale: concepts are scientifically aligned, but no public executable French-capable checkpoint currently satisfies the Lab gate.

## Current diagnosis

The repeated pattern is now strong evidence, not anecdote:

- speaker identity can be preserved;
- French can be preserved;
- low/moderate expressivity can be produced;
- **high-arousal panic remains the missing independent degree of freedom**.

Reinforcing speaker conditioning does not solve the problem and often worsens the panic-vs-sadness margin.

A model must expose a genuinely independent high-arousal control that survives French generation without changing the speaker.

## Capability gap decision

Status after #171:

**NO CURRENT PUBLIC/PERMISSIVE/CPU-EXECUTABLE MODEL IS AUTHORIZED FOR ANOTHER SCIENTIFIC CELL.**

Do not spend compute on another variant of a retired family.

Do not weaken the frozen machine gates to manufacture a PASS.

Do not start age/lineage, long-form catalog expansion or Production promotion while this identity + emotion + French problem remains unresolved.

## Reopening triggers

A new scientific lane may be opened only if at least one of the following materially occurs.

### Tier 1 — immediate high-value trigger

1. **IndexTTS-2.5 or successor officially adds French** while retaining:
   - arbitrary speaker reference;
   - independent 8D emotion vector including `afraid`;
   - executable public weights.

2. **MOSS-TTS 2.0** is released with:
   - French;
   - arbitrary voice cloning;
   - a separate fear/emotion/style condition not encoded in the speaker reference;
   - permissive public weights.

3. **dots.tts.edit** adds validated French editing for its `emo` operation while preserving source speaker identity.

4. **Marco-Voice upstream fixes** both:
   - the missing `nn` import;
   - unconditional fp16 emotion embedding under `fp16=False`;
   and provides a runnable inference environment without a local patch cascade.

5. **CosyVoice v3.5 open weights** become public with:
   - French zero-shot cloning;
   - same-call independent emotion instruction;
   - local/permissive execution.
   The current Alibaba Cloud capability alone is not an open-model trigger.

### Tier 2 — research release trigger

6. FlexiVoice, ReStyle-TTS, FC-TTS or SwanTale releases official code + checkpoint with French evidence and arbitrary speaker + independent emotion conditioning.

7. Higgs Audio 2.5 1B public weights are released with French evidence and arbitrary reference + scene/emotion instruction in one path.

8. Chatterbox Turbo becomes genuinely multilingual/French while retaining native paralinguistic/emotion tags and arbitrary reference cloning.

9. OmniVoice adds a native emotion vocabulary including fear while preserving its multilingual reference-cloning path.

10. NVIDIA releases a zero-shot Magpie path where an arbitrary audio-prompt clone can simultaneously select an independent emotional style, with locally usable licensing/access.

## What not to treat as a reopening trigger

The following are insufficient on their own:

- a new UI around an old model;
- a ComfyUI node that merely combines already-rejected backends;
- a new seed or CFG recommendation;
- a benchmark improvement without French evidence;
- a fixed built-in emotional voice without arbitrary speaker cloning;
- an arbitrary clone where emotion still comes only from the speaker reference;
- a community model card claim without executable code and exact weights;
- GPU-only availability when the available execution environment has not changed;
- a non-commercial checkpoint for a product trajectory.

## Next action

The Lab should remain **CAPABILITY GAP / WATCH** until a reopening trigger occurs.

When a trigger occurs, restart with a cheap resource/API gate first. Only then authorize one frozen Claire-panic scientific render.

Production remains unchanged.
