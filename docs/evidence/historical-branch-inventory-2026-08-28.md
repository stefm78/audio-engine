# Historical branch inventory — 2026-08-28

Status: **READ-ONLY AUDIT SNAPSHOT**

Repository: `stefm78/audio-engine`

Snapshot baseline: `main@37c13257bd3a15d4ca388265ec15ddf86122c329`

The consolidation branch that creates this snapshot is intentionally excluded from the inventory.

## Purpose

This file is the first durable branch-retention inventory for the Production / Voice Lab rationalization.

It is intentionally conservative. It does **not** authorize automatic deletion of every closed-unmerged experiment branch.

Deletion policy remains:

1. preserve verdict;
2. preserve PR and exact HEAD;
3. preserve run/artifact identifiers and digests when relevant;
4. preserve immutable reference hashes;
5. preserve reopen condition;
6. only then delete obsolete branch scaffolding.

## Snapshot summary

Branches outside `main`, excluding this consolidation branch: **117**

- `KEEP_TEMP_ACTIVE`: **0**
- `EVIDENCE_DURABLE_CAN_DELETE`: **23**
- `EVIDENCE_NOT_DURABLE_HOLD`: **76**
- `UNKNOWN_REVIEW_REQUIRED`: **18**

Classification rule used for this first pass:

- open associated PR -> `KEEP_TEMP_ACTIVE`;
- associated merged PR -> `EVIDENCE_DURABLE_CAN_DELETE`;
- closed-unmerged PR -> `EVIDENCE_NOT_DURABLE_HOLD` until its exact scientific evidence is checked against durable records;
- no associated PR -> `UNKNOWN_REVIEW_REQUIRED`;
- `lab/archive-reference-pack-v1` -> `EVIDENCE_DURABLE_CAN_DELETE` because release `voice-lab-reference-pack-v1` is published;
- `lab/verify-reference-pack-v1` -> `EVIDENCE_DURABLE_CAN_DELETE` because run `33173561027` re-downloaded the published release, verified its archive digest, extracted it and passed all four immutable WAV hashes.

At snapshot time no historical branch has an open PR. The NUC capability closeout PR #175 has merged and its branch is therefore classed as deletable evidence scaffolding.

## Important limits

This inventory classifies **branch retention**, not scientific validity.

A branch marked `EVIDENCE_DURABLE_CAN_DELETE` may be deleted only in a separate cleanup action after reviewing this inventory. No branch deletion is part of the evidence-consolidation PR that introduced this file.

A branch marked `EVIDENCE_NOT_DURABLE_HOLD` is not scientifically reopened. It is held only because branch deletion has not yet been proven safe from an evidence-retention standpoint.

## Inventory

| Branch | HEAD | PR | Class | Initial rationale |
| --- | --- | --- | --- | --- |
| `chore/rationalize-production-lab-boundary` | `e9e0fe71a145916a6664cab491141f1206e4a4e9` | #173 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `chore/voice-lab-progress-logs` | `ad914f7de5119f4c4dda5bed076bbaad5d94bad3` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `docs/qwen3-style-transplant-verdict` | `e2d7aa2bcdf566f6e160e5c967af73f56d80d721` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/chatterbox-v3-stage2` | `b1b7bcf616d023411e198d6ec6eee12f4a1cc205` | #44 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/cosyvoice3-killer` | `81c03facfd0860ba26c35256d145cbda6942cf8b` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/dsp-identity-signature-killer` | `2a4dd24c00ff495950730a1e8fe7dec552c48d06` | #98 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-four-clip-matrix` | `8cbee330bea58ee0be107658f5d5b270a940cb62` | #111 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-french-emotion-diagnostics` | `47ad53b4d0c0e00836108635e88215d5b4dd8ddd` | #113 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-lucie-sadness-killer` | `e1357693119fbc9f94bf83e3534ba0f674e2508c` | #110 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-wespeaker-arbitration` | `1a656091502b0e17db164fbc4ed0d297d129c3eb` | #112 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-world-emotion-evidence` | `6ac8ec7a63a9e30ee208201a39322606e69a99db` | #122 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-world-four-cell-matrix` | `f25f513c470a3e504814beb57963af01e0e5bb47` | #123 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-world-prosody-restore-continuation` | `cc2ec46ed4b23d84ff079cc4ce7b2ac0e165e903` | #127 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-world-prosody-restore-smoke` | `715337894c3d92a22909888032527027ad805594` | #121 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-world-smoke-gate-continuation` | `daff05ba4d540796a696a7226caa70e787465eaf` | #128 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/facodec-world-suprasegmental-smoke` | `eed2290e8ae708496875eac7e33d7723f60e2a8b` | #124 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/freevc-identity-lock-killer` | `874aa13cfc512690453b1272a1ca70eda0f9515d` | #106 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/french-language-integrity` | `f350b1d3e6babefcf345b7f7bfe8d9422c451627` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/knn-mkl-k2-preflight` | `2237039ee0bc26c29c12c80d26aa5077937f7d62` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/knnvc-identity-lock-killer` | `37c3c1f61ec003f3595b2a92d25390e579da6ed0` | #107 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/knnvc-lucie-reference-pack-killer` | `83cb00945a80d0d547f7e5178b47db393f3f1c9c` | #109 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/knnvc-machine-qa` | `6480d71a70a6273046ebb257139f08148136f6b9` | #108 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/meanvc-identity-emotion-killer` | `96b9d6a7ccf83824ade8ce065dda41a71ebf6a4e` | #115 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/meanvc-identity-emotion-killer-native-xtrans` | `b621c797ba2cbdaa82d338ec7cbe4919b18f9a9f` | #118 closed, #119 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/meanvc-identity-emotion-killer-rerun` | `ca619be60f9178938f107b1f3280587c26917a42` | #116 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/meanvc-identity-emotion-killer-rope-compat` | `ca619be60f9178938f107b1f3280587c26917a42` | #117 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/openvoice-v2-tone-killer` | `de55b08673c96c14bb1500ffeef536e2de1fa8da` | #76 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-character-composition` | `999154c9d963f658e965511880052e34d2acdc0d` | #67 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-character-lab` | `143e35c10b51181bc75820f406870ec22dad71f3` | #66 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/qwen3-contrast-casting` | `6951b83afc96bee232e25f92c03bc77a3a6386b5` | #82 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/qwen3-contrast-emotion-claire-recovery` | `2fa3121ce9e39e31832b88c8e88aa907b52b75e4` | #88 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-contrast-emotion-killer` | `ab0863ea9ba9194938f5f93a5d83beccc4f6cd0d` | #86 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-customvoice-identity-emotion-killer` | `2f94db606664a8b4b505f12947de8dc7a07d34c5` | #105 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-extreme-cast-claire-recovery` | `021dc936774145b917fd5f68042ccee2e25e806f` | #104 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-extreme-cast-panic` | `b1b48c9b9f598c6f79523645a239f26ad53bba38` | #103 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-panic-robust-casting` | `65de0a21ac4fa0d4dbc2784eb86af291d483daf5` | #97 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-progress-telemetry` | `cd01bfad10fbb553c91d3e838d2ed1f86017c9a9` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/qwen3-style-transplant-killer` | `37f1eb20432422a8733ea2213f05db3ffa856e96` | #70 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/qwen3-style-transplant-lucie-recovery` | `83c2b369ba84bf8460fcf4369c9e1d32b060eccd` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/qwen3-voicedesign-killer` | `cd01bfad10fbb553c91d3e838d2ed1f86017c9a9` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/qwen3-xvector-identity-confirm` | `5dce91a12b65054d6587c62711c40e49f89f6ce7` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/qwen3-xvector-killer` | `4133309eb29804d8471e8bce02ce029efea60a7f` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/rvc-gpu-package-audit` | `f039f497d5a7f4ff64c9f159c613c32db40d8a6a` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/rvc-gpu-training-package` | `d88b32321db3af45a2c9c341b09e0716eb45040e` | #129 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/rvc-learned-character-feasibility` | `bfc8411ac36033d14cb364e6881361fd2d4c2067` | #125 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/rvc-lucie-dataset-zero-render-aggregate` | `055aa45217c8bd70d40c3d4e233df67e8f593cd7` | #131 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/rvc-lucie-neutral-dataset-expansion` | `bbf7aa214ddf3f25297dc15fff58e7e5dc4c220d` | #130 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/rvc-lucie-neutral-dataset-pilot` | `5fb54c5876915be1d73cda5cd102e6944674e608` | #126 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/superb-source-emotion-preflight` | `c33f9568735b8e1281c72303115e8f54a5b36156` | #114 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `feature/voice-casting-distance-gate` | `aedf91b435de51c73a4277ffa359f5fc1eda4af0` | #81 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/voice-casting-lab` | `3610bb34d296fa95cc9701cd0ed1f43538b68fe5` | #24 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/voice-lab-acting-evidence` | `4d74ec3b48c28f64a4bf017a83f9fac853c3143f` | #35 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/voice-lab-adaptive-candidates` | `a26bed3a0a2b1f5c241ed725e3d636edbdc271be` | #31 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/voice-lab-chatterbox-killer-test` | `c0d46192fcc14f51448f16853a09002a073dd81e` | #41 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/voice-lab-human-evidence` | `d2b3a6e1f805679362bcade923edf74a90b5c65e` | #34 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/voice-lab-multilingual-eval` | `2d3e2d4a8299ac1bfb2b831ace55b5d87bd3654d` | #29 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/voice-lab-pages` | `81e8c846cbfc2f54f490854fce64de185fa9c47e` | #69 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `feature/voxcpm2-age-lineage` | `0966ab6db40975b2e200ddd10f7a82e52a372ed0` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/voxcpm2-fr-clean-confirmation` | `6a957f932a21b40523c2a6e8221cdbf4156eed26` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/voxcpm2-killer` | `2cce03631a2bdb3e19b64a31c8822fe4c395452e` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/voxcpm2-progress-telemetry` | `87d549b701fd75f9df57ae47bc5a65b6795e8a41` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/voxcpm2-stage2` | `1e5aef389b66d74425ebd9eb9c9a26253fd35ee9` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `feature/xvc-french-content-smoke` | `5cdd5db29812e66c6b88e76ad8541a13cf1d8176` | #120 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `fix/voice-lab-panic-pronunciation-erratum` | `f5dcd764dad6b6fe7d4dba4a26b5198592fd1d69` | #39 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `infra/publish-dsp-identity-signature` | `0843a4a9867c5eb85945ceaeb8730ff69fac615c` | #100 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `infra/publish-openvoice-v2-tone-killer` | `b71b0bac4fb05200b682235024a76b79009c8d53` | #79 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `infra/publish-qwen3-contrast-casting` | `6111bc8a2fe1e7ffa34da13591a9b459fd7f1ed8` | #84 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `infra/publish-qwen3-contrast-emotion` | `6fde430613a7ed7d482b53b0909aa01846485fe9` | #91 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `infra/publish-radio-only-contrast-emotion` | `80db8f44487e9179967805be091e43d561a7e97a` | #94 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `infra/trigger-voice-lab-pages-publish` | `b78d4af3952b24aa2307834380934a4df55cdc27` | #74 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `infra/voice-lab-radio-only` | `8269ce6774297498a7817f9890cdc0744e6a4792` | #93 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `lab/archive-reference-pack-v1` | `fe090fc968684aab2d29f30a26d38cf3ddf54d36` | — | `EVIDENCE_DURABLE_CAN_DELETE` | Durable release exists; branch only created the archive workflow |
| `lab/chatterbox-multilingual-claire-panic-one-cell` | `06a66fe29bdb9e478345727efccbe0ef76d4a52d` | #149 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/chatterbox-multilingual-cpu-resource-preflight` | `feab40fccd4b573570083202fcb73fdf08f4c2a4` | #148 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/chatterbox-multilingual-v3-claire-panic-one-cell` | `76e0dbc0750f274950345ceda151c0cd88983912` | #151 closed, #152 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/chatterbox-multilingual-v3-cpu-resource-preflight` | `2519ee1fb4bff7aabdb20c0c54f3236adf725bc0` | #150 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/chatterbox-vc-2x3-confirmation` | `a70bd1c2787104fa84a067c7daf9c6635ab3d652` | #145 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/chatterbox-vc-bounded-claire-panic` | `a5cd402d37a60c2b7e3a1239a8b449296722e888` | #147 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/chatterbox-vc-claire-panic-one-cell` | `5ef9a366679fffb2a3dcdf23277a21e0f6b3a45a` | #144 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/chatterbox-vc-cpu-resource-preflight` | `20b38f6d165a761cee70faf989d47b39a07df53b` | #143 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/chatterbox-vc-seed-control-preflight` | `9eb7a4952f122fa3f53b235e9f716ed701b1a4be` | #146 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/cosyvoice2-eu-claire-panic-one-cell` | `891e27f6465e7e12033900c24c962cac046dbdd9` | #164 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/cosyvoice2-eu-claire-panic-validation` | `6cc3d92d312d5607c889ce3e9745ad6edb228f11` | #165 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/cosyvoice2-eu-cpu-resource-preflight` | `fd414556b083b10843544cd46354b8b5a9e2f974` | #163 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/cosyvoice3-claire-panic-one-cell` | `f05efcce8530c7bc41c2be9c664a3f30818d6d53` | #140 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/cosyvoice3-claire-panic-one-cell-run` | `78b9b36c9b11e635096ac9b6903035644abf8e62` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `lab/cosyvoice3-cpu-resource-preflight` | `00d8471efbdf27e56de482aa33aaf0b9dbb92a0d` | #138 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/fish-s2-pro-cpu-resource-preflight` | `f75b97f3ee5c5ad519784a8bc03fd393df406469` | #160 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/marco-voice-cpu-fearful-resource-preflight` | `dc4ec08f05e89f08ad1b85c3d4c78fb0ae33a177` | #171 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/meanvc2-cpu-one-cell` | `32eb0acd33cc4ea412a01fd5de23d86a6cdbf60e` | #133 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/meanvc2-cpu-one-cell-science` | `e1eb04a7f0f59c3a4e29dc341b002d8b504fd75c` | #134 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/nuc-capability-closeout` | `acfdaca554852f8c792c5b8d4d613dab79c901cf` | #175 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |
| `lab/openvoice-v2-cpu-feasibility` | `8298fff4463b0a6b8f01233e6ba386cfb4bd20d4` | #132 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/qwen-base-icl-cpu-resource-preflight` | `f039f497d5a7f4ff64c9f159c613c32db40d8a6a` | — | `UNKNOWN_REVIEW_REQUIRED` | No associated PR found in repository PR history |
| `lab/qwen-c-emotion-stack-claire-panic-one-cell` | `1b9d57eb327e8279fdb7cffcb25e45160062923e` | #159 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/qwen-c-emotion-stack-cpu-preflight` | `eb20028f8b8a773b07a10bd33877cef51e7559c3` | #158 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/qwen-c-graft-claire-panic-one-cell` | `8a5b6fbb9db89628dbb058b421468c537863ab58` | #167 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/qwen-c-graft-cpu-preflight` | `7f3fd865713f85eebf16f0f5e533ddfc0b0e2fe1` | #166 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/qwen3-bounded-native-selection` | `f5208ca5339b63fb83105f50dd645e61ef5b6f18` | #135 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/qwen3-bounded-selection-zero-render-validation` | `9c48925d2007c44dae6d73edcc89ab493aaa2e8f` | #136 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/qwen3-c-xvector-emotion-cpu-resource-preflight` | `64f4a57ca8c126270ef876fad1e7e52256d4f56b` | #157 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/seed-vc-cpu-one-cell-science` | `2090bf36d81c166e50a4299a5b15ce25c38c72fa` | #139 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/seed-vc-cpu-resource-preflight` | `a84b09fc6d97e99be2f09dbf7857d306339499b0` | #137 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/verify-reference-pack-v1` | `9e54ab2dc09b34da07752b42e4ce617d52617bdd` | — | `EVIDENCE_DURABLE_CAN_DELETE` | Verification run 33173561027 passed against published release; branch is verification scaffolding only |
| `lab/voice-casting-capability-gap-2026-08-28` | `ce5adee3df4978e2cf45bd0f3a2a281a1e94beed` | #172 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/voxcpm2-claire-panic-one-cell` | `e2a415b12e7c164d783981016298aa5c0e4de719` | #142 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/voxcpm2-cpu-resource-preflight` | `3a52a147b65d442d7a10b59a8d330722896054f1` | #141 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/world-prosody-claire-panic-one-cell` | `eb969e074fff7807d4d6bbe354bc7638ca627d86` | #168 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/wren-05b-expressive-claire-panic-one-cell` | `938df8505bde0910356e2b8713bd3641f0d5496e` | #162 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/wren-05b-expressive-cpu-resource-preflight` | `6473d3e65599c552c28b70bcb2664497cbd1be34` | #161 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/zonos-v01-claire-panic-one-cell` | `f4487e6b4b7c5bb16a856424a2972451fe50a998` | #154 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/zonos-v01-claire-panic-validate-recovery` | `090b4d8003d1860369953ce1d5512c3996242188` | #155 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/zonos-v01-claire-panic-validation-recovery` | `293a4f96bb3c6a3f33692be368c71fae7761b194` | #156 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/zonos-v01-cpu-resource-preflight` | `af6973e4b2f5e85f84ba61e0db1a080e4bdd4150` | #153 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/zonos2-claire-panic-one-cell` | `5581226498a4b2916da4ad1381532a33f3e9b4ab` | #170 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `lab/zonos2-cpu-emotion-preflight` | `e9be14db5da78abc0771bf62415f7d8e83b3bdce` | #169 closed | `EVIDENCE_NOT_DURABLE_HOLD` | Closed-unmerged PR evidence exists; per-branch durable receipt not yet confirmed |
| `voice-edge-normalization` | `278e35da627572c47b18a65fa2dab5ee2ebff9ec` | #23 merged | `EVIDENCE_DURABLE_CAN_DELETE` | At least one associated PR merged |

## Next branch-cleanup pass

The next safe pass should:

1. delete the `EVIDENCE_DURABLE_CAN_DELETE` refs in a separate cleanup action after a final spot check;
2. audit closed-unmerged branches in scientific families, grouping related recovery/preflight branches under durable evidence receipts;
3. inspect the remaining no-PR refs individually;
4. never treat additional compute or the NUC as a reason to reopen a `SCIENTIFIC REJECT`.
