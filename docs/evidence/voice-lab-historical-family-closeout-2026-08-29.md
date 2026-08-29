# Voice Lab historical family closeout — 2026-08-29

Status: **DURABLE LAB EVIDENCE / BRANCH DELETION AUTHORITY**

Production status: **EDGE ACTIVE / UNAFFECTED**

Baseline before this consolidation: `main@4d61b1cfaa9af1f79264cfb7be858b68f42d0e9a`.

## Purpose

Consolidate the historical Voice Lab branch forest by scientific family so Git branches stop acting as the archive.

This receipt preserves the branch/HEAD/PR chain, the final family conclusion and the reopening condition. Individual closed PRs, runs and artifacts remain traceability anchors; branch refs are not required once this receipt is on `main`.

This document does **not** reopen, rerun or reinterpret any scientific cell.

## First mechanical prune completed

One-shot cleanup run `33224258807` deleted exactly the 23 refs previously classified `EVIDENCE_DURABLE_CAN_DELETE`.

Every target was guarded by its exact HEAD SHA before deletion. The cleanup workflow then deleted its own ephemeral branch. Production code and `main` were untouched.

## Family conclusions

| Family | Final state | Durable conclusion | Reopen condition |
| --- | --- | --- | --- |
| Qwen3 / Qwen | **SCIENTIFIC REJECT — CLOSED** | Multiple distinct speaker-conditioning topologies preserved identity/French but failed independent high-arousal panic; earlier composition/style lanes also failed identity/acting. #159 and #167 are decisive current one-cell emotion rejects. | Only a material upstream capability change matching the frozen reopening rules; never seed/CFG/tuning or additional NUC compute. |
| FACodec | **SCIENTIFIC REJECT — EMOTION** | FACodec reached target identity and French evidence, but source-valid SUPERB arbitration rejected emotion preservation on 3/4 cells (#114). | A materially different architecture/checkpoint, not verifier shopping or parameter tuning. |
| WORLD prosody | **SCIENTIFIC / TECHNICAL REJECT** | Four-cell WORLD path failed speaker identity (#123/#124); later one-cell source-filter transplant failed frozen pre-write clipping gate (#168). | A materially new prosody architecture; no F0/energy/blend/gain rescue loop. |
| Chatterbox Multilingual | **SCIENTIFIC REJECT — ACTING / EMOTION** | V2 #149 passed machine, identity and French but failed human panic acting; V3 #151/#152 failed frozen emotion gate. | Material multilingual/native emotion capability change such as a genuinely new Turbo/open release; no scalar-exaggeration tuning. |
| ChatterboxVC | **SCIENTIFIC REJECT — FRENCH / EMOTION** | One-cell #144 passed, but bounded confirmation #145 exposed French failures and #147 bounded selection produced no eligible candidate. | Material VC architecture change with robust French and independent emotion; no seed/reference-pool tuning. |
| MeanVC | **SCIENTIFIC REJECT — FRENCH** | Native-runtime #118/#119 reproduced technical, identity and emotion passes but French/content regression on all four cells. | Material model/tokenizer architecture change with demonstrated French preservation. |
| Zonos v0.1 | **SCIENTIFIC REJECT — EMOTION** | Resource path passed; immutable scientific render/recovery #154/#156 passed technical/identity/French and failed emotion. | Material new conditioning/model capability; no threshold/seed rescue. |
| ZONOS2 | **SCIENTIFIC REJECT — EMOTION** | #169 resource PASS; #170 technical/identity/French PASS and emotion REJECT with high-arousal axes still acoustically sadness-like. | Material new affect control, not different valence/arousal weights. |
| RVC | **OPERATIONAL / ARCHITECTURE REJECT** | CPU learned-character path was operationally rejected (#125); dataset pilots do not constitute qualification. | Materially different supported execution/training path plus admissible scientific architecture. |
| CosyVoice2-EU | **SCIENTIFIC REJECT — EMOTION** | #163 resource PASS; #164/#165 identity and French PASS, emotion REJECT. | New checkpoint/path with genuinely independent panic control. |
| CosyVoice3 | **TECHNICAL REJECT — RETIRED** | #138 resource PASS; #140 exact one-cell run 32987499790 produced duration ratio 1.546875 > frozen 1.5 limit; no rescue authorized. | Material new upstream/open release; capability-gap specifically watches CosyVoice v3.5 open weights with French zero-shot + independent emotion. |
| kNN-VC | **NOT QUALIFIED — FRENCH/CONTENT** | #107–#109: identity locking useful, but persistent Lucie contained-sadness French/content weakness; one bounded richer-reference repair failed its identity preflight. | Material architecture/reference mechanism change; no further pool, ASR, parameter or threshold tuning. |
| OpenVoice V2 | **SCIENTIFIC REJECT / RETIRED** | Human tone-color lane failed identity; broader closeout records useful French/identity properties but insufficient panic qualification. | Materially new OpenVoice capability, not tone-color tuning. |
| Seed-VC | **NON-ADMISSIBLE / RETIRED** | Post-hoc VC path and licensing/trajectory mismatch; no autonomous qualification. | Material license and architecture change. |
| VoxCPM2 | **SCIENTIFIC REJECT — IDENTITY** | #141 resource PASS; #142 independent identity REJECT. Earlier age-lineage reference was additionally contaminated by Multilingual-French integrity findings. | Material identity+emotion architecture change; do not resume age-lineage while core identity/emotion/French gate is unresolved. |
| Wren | **TECHNICAL REJECT + LICENSE** | #161 resource PASS; #162 failed the frozen technical reference-conditioning gate; current closeout also records CC-BY-NC. | Material technical and licensing change. |
| DSP identity signature | **HUMAN IDENTITY FAIL** | Fixed EQ signature moved the identity error: 2/3 human identity despite 6/6 acting and French preserved (#98). | No EQ parameter tuning; only materially different architecture. |
| FreeVC | **SMOKE REJECT** | Post-expression identity-lock path rejected at the preregistered smoke gate (#106). | Materially different identity-lock architecture. |
| Fish S2 Pro | **RESOURCE NOT PROVEN + LICENSE** | #160 did not prove reliable standard-CPU execution and carries research/non-commercial licensing constraints. | Material supported runtime/hardware or official smaller/quantized checkpoint plus admissible licensing. |
| Marco-Voice | **RESOURCE FAIL — WATCH** | #171 reached synthesis path but hit upstream source defects including unconditional fp16 emotion embedding under fp16=False; NUC reassessment found upstream unchanged. | Only when upstream fixes both recorded source defects and provides a runnable environment. |
| X-VC | **SCIENTIFIC REJECT — FRENCH** | #120 failed first scientific French lexical-content gate; later gates correctly skipped. | Material model/tokenizer change with French evidence. |
| French panic erratum | **SUPERSEDED ON MAIN** | #39 evidence was materialized on main; canonical panic text is now `Vite ! Ils arrivent ! Fermez la porte !`. | No reopening; this is an evidence correction. |
| Capability closeout | **MATERIALIZED ON MAIN** | #172's capability-gap evidence and reopening rules are already present on main. | Update only when a documented reopening trigger actually occurs. |

## French integrity finding retained from the UNKNOWN audit

Issue #56 is the durable human verdict for the targeted Edge French-pronunciation sentinel:

- dedicated `fr-FR` controls Denise + Henri: **6/6 good**, zero foreign-pronunciation defects;
- Multilingual controls Vivienne + Remy: **2/6 good**, **4/6 foreign-pronunciation defects**;
- probes covered `Approchez`, `Courez`, `Regardez`, `Écoutez`;
- French production/reference anchors must use dedicated `fr-FR` voices by default;
- Edge Multilingual voices remain Lab-only for French identity anchors;
- do not hide the defect by removing sentinel words.

This preserves the unique value of `feature/french-language-integrity`; its old rendering/player workflow does not need a permanent branch.

## Closed-unmerged branches reclassified

The following **76** branches were previously held only because a family-level durable receipt did not yet exist.

| Branch | Exact HEAD | PR evidence | Family | New retention class |
| --- | --- | --- | --- | --- |
| `feature/dsp-identity-signature-killer` | `2a4dd24c00ff495950730a1e8fe7dec552c48d06` | #98 closed | DSP identity signature | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-four-clip-matrix` | `8cbee330bea58ee0be107658f5d5b270a940cb62` | #111 closed | FACodec | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-french-emotion-diagnostics` | `47ad53b4d0c0e00836108635e88215d5b4dd8ddd` | #113 closed | FACodec | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-lucie-sadness-killer` | `e1357693119fbc9f94bf83e3534ba0f674e2508c` | #110 closed | FACodec | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-wespeaker-arbitration` | `1a656091502b0e17db164fbc4ed0d297d129c3eb` | #112 closed | FACodec | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-world-emotion-evidence` | `6ac8ec7a63a9e30ee208201a39322606e69a99db` | #122 closed | WORLD prosody | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-world-four-cell-matrix` | `f25f513c470a3e504814beb57963af01e0e5bb47` | #123 closed | WORLD prosody | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-world-prosody-restore-continuation` | `cc2ec46ed4b23d84ff079cc4ce7b2ac0e165e903` | #127 closed | WORLD prosody | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-world-prosody-restore-smoke` | `715337894c3d92a22909888032527027ad805594` | #121 closed | WORLD prosody | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-world-smoke-gate-continuation` | `daff05ba4d540796a696a7226caa70e787465eaf` | #128 closed | WORLD prosody | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/facodec-world-suprasegmental-smoke` | `eed2290e8ae708496875eac7e33d7723f60e2a8b` | #124 closed | WORLD prosody | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/freevc-identity-lock-killer` | `874aa13cfc512690453b1272a1ca70eda0f9515d` | #106 closed | FreeVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/knnvc-identity-lock-killer` | `37c3c1f61ec003f3595b2a92d25390e579da6ed0` | #107 closed | kNN-VC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/knnvc-lucie-reference-pack-killer` | `83cb00945a80d0d547f7e5178b47db393f3f1c9c` | #109 closed | kNN-VC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/knnvc-machine-qa` | `6480d71a70a6273046ebb257139f08148136f6b9` | #108 closed | kNN-VC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/meanvc-identity-emotion-killer` | `96b9d6a7ccf83824ade8ce065dda41a71ebf6a4e` | #115 closed | MeanVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/meanvc-identity-emotion-killer-native-xtrans` | `b621c797ba2cbdaa82d338ec7cbe4919b18f9a9f` | #118 closed, #119 closed | MeanVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/meanvc-identity-emotion-killer-rerun` | `ca619be60f9178938f107b1f3280587c26917a42` | #116 closed | MeanVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/meanvc-identity-emotion-killer-rope-compat` | `ca619be60f9178938f107b1f3280587c26917a42` | #117 closed | MeanVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/openvoice-v2-tone-killer` | `de55b08673c96c14bb1500ffeef536e2de1fa8da` | #76 closed | OpenVoice V2 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-character-composition` | `999154c9d963f658e965511880052e34d2acdc0d` | #67 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-contrast-emotion-claire-recovery` | `2fa3121ce9e39e31832b88c8e88aa907b52b75e4` | #88 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-contrast-emotion-killer` | `ab0863ea9ba9194938f5f93a5d83beccc4f6cd0d` | #86 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-customvoice-identity-emotion-killer` | `2f94db606664a8b4b505f12947de8dc7a07d34c5` | #105 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-extreme-cast-claire-recovery` | `021dc936774145b917fd5f68042ccee2e25e806f` | #104 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-extreme-cast-panic` | `b1b48c9b9f598c6f79523645a239f26ad53bba38` | #103 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-panic-robust-casting` | `65de0a21ac4fa0d4dbc2784eb86af291d483daf5` | #97 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-style-transplant-killer` | `37f1eb20432422a8733ea2213f05db3ffa856e96` | #70 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/rvc-gpu-training-package` | `d88b32321db3af45a2c9c341b09e0716eb45040e` | #129 closed | RVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/rvc-learned-character-feasibility` | `bfc8411ac36033d14cb364e6881361fd2d4c2067` | #125 closed | RVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/rvc-lucie-dataset-zero-render-aggregate` | `055aa45217c8bd70d40c3d4e233df67e8f593cd7` | #131 closed | RVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/rvc-lucie-neutral-dataset-expansion` | `bbf7aa214ddf3f25297dc15fff58e7e5dc4c220d` | #130 closed | RVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/rvc-lucie-neutral-dataset-pilot` | `5fb54c5876915be1d73cda5cd102e6944674e608` | #126 closed | RVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/superb-source-emotion-preflight` | `c33f9568735b8e1281c72303115e8f54a5b36156` | #114 closed | FACodec | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/xvc-french-content-smoke` | `5cdd5db29812e66c6b88e76ad8541a13cf1d8176` | #120 closed | X-VC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `fix/voice-lab-panic-pronunciation-erratum` | `f5dcd764dad6b6fe7d4dba4a26b5198592fd1d69` | #39 closed | French panic erratum | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-multilingual-claire-panic-one-cell` | `06a66fe29bdb9e478345727efccbe0ef76d4a52d` | #149 closed | Chatterbox Multilingual | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-multilingual-cpu-resource-preflight` | `feab40fccd4b573570083202fcb73fdf08f4c2a4` | #148 closed | Chatterbox Multilingual | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-multilingual-v3-claire-panic-one-cell` | `76e0dbc0750f274950345ceda151c0cd88983912` | #151 closed, #152 closed | Chatterbox Multilingual | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-multilingual-v3-cpu-resource-preflight` | `2519ee1fb4bff7aabdb20c0c54f3236adf725bc0` | #150 closed | Chatterbox Multilingual | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-vc-2x3-confirmation` | `a70bd1c2787104fa84a067c7daf9c6635ab3d652` | #145 closed | ChatterboxVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-vc-bounded-claire-panic` | `a5cd402d37a60c2b7e3a1239a8b449296722e888` | #147 closed | ChatterboxVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-vc-claire-panic-one-cell` | `5ef9a366679fffb2a3dcdf23277a21e0f6b3a45a` | #144 closed | ChatterboxVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-vc-cpu-resource-preflight` | `20b38f6d165a761cee70faf989d47b39a07df53b` | #143 closed | ChatterboxVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/chatterbox-vc-seed-control-preflight` | `9eb7a4952f122fa3f53b235e9f716ed701b1a4be` | #146 closed | ChatterboxVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/cosyvoice2-eu-claire-panic-one-cell` | `891e27f6465e7e12033900c24c962cac046dbdd9` | #164 closed | CosyVoice2-EU | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/cosyvoice2-eu-claire-panic-validation` | `6cc3d92d312d5607c889ce3e9745ad6edb228f11` | #165 closed | CosyVoice2-EU | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/cosyvoice2-eu-cpu-resource-preflight` | `fd414556b083b10843544cd46354b8b5a9e2f974` | #163 closed | CosyVoice2-EU | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/cosyvoice3-claire-panic-one-cell` | `f05efcce8530c7bc41c2be9c664a3f30818d6d53` | #140 closed | CosyVoice3 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/cosyvoice3-cpu-resource-preflight` | `00d8471efbdf27e56de482aa33aaf0b9dbb92a0d` | #138 closed | CosyVoice3 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/fish-s2-pro-cpu-resource-preflight` | `f75b97f3ee5c5ad519784a8bc03fd393df406469` | #160 closed | Fish S2 Pro | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/marco-voice-cpu-fearful-resource-preflight` | `dc4ec08f05e89f08ad1b85c3d4c78fb0ae33a177` | #171 closed | Marco-Voice | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/meanvc2-cpu-one-cell` | `32eb0acd33cc4ea412a01fd5de23d86a6cdbf60e` | #133 closed | MeanVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/meanvc2-cpu-one-cell-science` | `e1eb04a7f0f59c3a4e29dc341b002d8b504fd75c` | #134 closed | MeanVC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/openvoice-v2-cpu-feasibility` | `8298fff4463b0a6b8f01233e6ba386cfb4bd20d4` | #132 closed | OpenVoice V2 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/qwen-c-emotion-stack-claire-panic-one-cell` | `1b9d57eb327e8279fdb7cffcb25e45160062923e` | #159 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/qwen-c-emotion-stack-cpu-preflight` | `eb20028f8b8a773b07a10bd33877cef51e7559c3` | #158 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/qwen-c-graft-claire-panic-one-cell` | `8a5b6fbb9db89628dbb058b421468c537863ab58` | #167 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/qwen-c-graft-cpu-preflight` | `7f3fd865713f85eebf16f0f5e533ddfc0b0e2fe1` | #166 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/qwen3-bounded-native-selection` | `f5208ca5339b63fb83105f50dd645e61ef5b6f18` | #135 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/qwen3-bounded-selection-zero-render-validation` | `9c48925d2007c44dae6d73edcc89ab493aaa2e8f` | #136 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/qwen3-c-xvector-emotion-cpu-resource-preflight` | `64f4a57ca8c126270ef876fad1e7e52256d4f56b` | #157 closed | Qwen3 / Qwen | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/seed-vc-cpu-one-cell-science` | `2090bf36d81c166e50a4299a5b15ce25c38c72fa` | #139 closed | Seed-VC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/seed-vc-cpu-resource-preflight` | `a84b09fc6d97e99be2f09dbf7857d306339499b0` | #137 closed | Seed-VC | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/voice-casting-capability-gap-2026-08-28` | `ce5adee3df4978e2cf45bd0f3a2a281a1e94beed` | #172 closed | Capability closeout | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/voxcpm2-claire-panic-one-cell` | `e2a415b12e7c164d783981016298aa5c0e4de719` | #142 closed | VoxCPM2 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/voxcpm2-cpu-resource-preflight` | `3a52a147b65d442d7a10b59a8d330722896054f1` | #141 closed | VoxCPM2 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/world-prosody-claire-panic-one-cell` | `eb969e074fff7807d4d6bbe354bc7638ca627d86` | #168 closed | WORLD prosody | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/wren-05b-expressive-claire-panic-one-cell` | `938df8505bde0910356e2b8713bd3641f0d5496e` | #162 closed | Wren | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/wren-05b-expressive-cpu-resource-preflight` | `6473d3e65599c552c28b70bcb2664497cbd1be34` | #161 closed | Wren | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/zonos-v01-claire-panic-one-cell` | `f4487e6b4b7c5bb16a856424a2972451fe50a998` | #154 closed | Zonos v0.1 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/zonos-v01-claire-panic-validate-recovery` | `090b4d8003d1860369953ce1d5512c3996242188` | #155 closed | Zonos v0.1 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/zonos-v01-claire-panic-validation-recovery` | `293a4f96bb3c6a3f33692be368c71fae7761b194` | #156 closed | Zonos v0.1 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/zonos-v01-cpu-resource-preflight` | `af6973e4b2f5e85f84ba61e0db1a080e4bdd4150` | #153 closed | Zonos v0.1 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/zonos2-claire-panic-one-cell` | `5581226498a4b2916da4ad1381532a33f3e9b4ab` | #170 closed | ZONOS2 | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/zonos2-cpu-emotion-preflight` | `e9be14db5da78abc0771bf62415f7d8e83b3bdce` | #169 closed | ZONOS2 | `EVIDENCE_DURABLE_CAN_DELETE` |

All rows above become `EVIDENCE_DURABLE_CAN_DELETE` **only after this document is merged to main**.

A resource-preflight PASS in an intermediate PR is not erased: its exact PR and run history remain accessible. The deletion decision reflects that a later family verdict determines current scientific status.

## UNKNOWN branches audited and reclassified

The following **18** branches had no associated PR in the original inventory. Each was compared to current `main` and inspected for unique evidence.

| Branch | Exact HEAD | Family | Audit conclusion | New retention class |
| --- | --- | --- | --- | --- |
| `chore/voice-lab-progress-logs` | `ad914f7de5119f4c4dda5bed076bbaad5d94bad3` | Other | Historical progress/scaffolding chain; final CosyVoice3/VoxCPM2 outcomes are preserved by #140/#142 and this family receipt. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `docs/qwen3-style-transplant-verdict` | `e2d7aa2bcdf566f6e160e5c967af73f56d80d721` | Qwen3 / Qwen | 0 commits unique versus current main at audit time; no unique retained content. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/cosyvoice3-killer` | `81c03facfd0860ba26c35256d145cbda6942cf8b` | CosyVoice3 | Historical CosyVoice3 harness superseded by formal resource/science PRs #138/#140. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/french-language-integrity` | `f350b1d3e6babefcf345b7f7bfe8d9422c451627` | Other | Human conclusion is durable in issue #56: dedicated fr-FR 6/6 good; Multilingual 2/6 good with 4 foreign-pronunciation defects. Protocol/result summarized below. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/knn-mkl-k2-preflight` | `2237039ee0bc26c29c12c80d26aa5077937f7d62` | kNN-VC | Dependency-freeze-only workflow; full kNN-VC chain #107–#109 is final and retired. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-progress-telemetry` | `cd01bfad10fbb553c91d3e838d2ed1f86017c9a9` | Qwen3 / Qwen | Historical Qwen scaffolding/telemetry; final Qwen family conclusions preserved on main and in #159/#167. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-style-transplant-lucie-recovery` | `83c2b369ba84bf8460fcf4369c9e1d32b060eccd` | Qwen3 / Qwen | Historical recovery scaffolding; style-transplant final identity failure is preserved by #70 and family closeout. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-voicedesign-killer` | `cd01bfad10fbb553c91d3e838d2ed1f86017c9a9` | Qwen3 / Qwen | Historical Qwen VoiceDesign scaffolding; later direct/conditioned Qwen outcomes supersede it. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-xvector-identity-confirm` | `5dce91a12b65054d6587c62711c40e49f89f6ce7` | Qwen3 / Qwen | Identity qualification is scientifically absorbed by later Qwen evidence: strong x-vector identity/French but emotion reject (#159/#167). | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/qwen3-xvector-killer` | `4133309eb29804d8471e8bce02ce029efea60a7f` | Qwen3 / Qwen | Historical x-vector harness superseded by later Qwen one-cell evidence. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/rvc-gpu-package-audit` | `f039f497d5a7f4ff64c9f159c613c32db40d8a6a` | RVC | 0 commits unique versus current main at audit time; no unique retained content. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/voxcpm2-age-lineage` | `0966ab6db40975b2e200ddd10f7a82e52a372ed0` | VoxCPM2 | Historical age-lineage scaffolding; core VoxCPM2 identity rejected by #142 and age-lineage is explicitly frozen. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/voxcpm2-fr-clean-confirmation` | `6a957f932a21b40523c2a6e8221cdbf4156eed26` | VoxCPM2 | Historical VoxCPM2 French follow-up; issue #56 records contaminated Multilingual anchor and #142 records final identity reject. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/voxcpm2-killer` | `2cce03631a2bdb3e19b64a31c8822fe4c395452e` | VoxCPM2 | Historical VoxCPM2 harness superseded by formal #141/#142 evidence. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/voxcpm2-progress-telemetry` | `87d549b701fd75f9df57ae47bc5a65b6795e8a41` | VoxCPM2 | Historical telemetry only; superseded by #141/#142. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `feature/voxcpm2-stage2` | `1e5aef389b66d74425ebd9eb9c9a26253fd35ee9` | VoxCPM2 | Historical stage-2 scaffolding; superseded by final identity reject #142. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/cosyvoice3-claire-panic-one-cell-run` | `78b9b36c9b11e635096ac9b6903035644abf8e62` | CosyVoice3 | Exact execution lane for #140; authoritative run 32987499790 and technical duration reject are preserved in #140. | `EVIDENCE_DURABLE_CAN_DELETE` |
| `lab/qwen-base-icl-cpu-resource-preflight` | `f039f497d5a7f4ff64c9f159c613c32db40d8a6a` | Qwen3 / Qwen | 0 commits unique versus current main at audit time; no unique retained content. | `EVIDENCE_DURABLE_CAN_DELETE` |

All 18 UNKNOWN refs are therefore safe to delete after this receipt merges.

## Additional merged scaffolding

`chore/voice-lab-evidence-consolidation@b3dda95a2c665e3044e8f350a2857531aacb8f76` is the already-merged branch behind PR #176. It was intentionally excluded from the 2026-08-28 inventory and is now `EVIDENCE_DURABLE_CAN_DELETE`.

The branch used to merge this receipt, `chore/consolidate-voice-lab-family-evidence`, also becomes deletable immediately after its PR merges.

## Deletion authorization

After this receipt is on `main`, repository cleanup is authorized to delete:

- all 76 reclassified closed-unmerged refs above;
- all 18 audited UNKNOWN refs above;
- `chore/voice-lab-evidence-consolidation`;
- the merged branch carrying this receipt.

Deletion must still verify each ref's exact expected SHA before removing it. Any ref drift is an automatic STOP for that ref.

## Scientific state after branch deletion

Branch deletion changes no science.

```text
VOICE_LAB_STATUS=CAPABILITY_GAP_WATCH
PRODUCTION_PROVIDER=EDGE
NEW_SCIENTIFIC_CELL=NOT_AUTHORIZED
GENERIC_NUC_BENCHMARKING=CLOSED
PRIVATE_NUC_CONTROL_PLANE=NOT_NEEDED
SCIENTIFIC_REJECTS=REMAIN_CLOSED
```

The next repository task after branch cleanup is a separate audit of historical Lab code still present on `main`. That task must preserve generic reusable Lab primitives and remove only model/experiment-specific dead scaffolding. It must not alter the Production rendering contract.
