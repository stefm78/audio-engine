# Azure expressive duel (Voice Casting Lab only)

Status: experimental / pre-production only.

## Why this exists

Human listening evidence showed that Edge remains useful for narration and stable character identity, but rate/pitch/volume changes did not reliably create convincing acting on hard intentions. Azure Speech is therefore evaluated only inside the Voice Casting Lab before any production promotion.

The experiment answers two separate questions:

1. **Controlled same-base-voice test** — `fr-FR-DeniseNeural` and `fr-FR-HenriNeural` are compared between the current Edge path and Azure Speech native styles. This reduces the risk of confusing a better voice identity with a better expressive control.
2. **MAI ceiling test** — French `fr-FR-Soleil:MAI-Voice-2` and `fr-FR-Marc:MAI-Voice-2` are tested on hard intentions using native styles such as `fearful`, `whispering`, `determined`, `surprised`, `shouting`, `softvoice`, and `angry`.

The experiment renders 48 clips for 12 blind decisions. No result automatically changes the production provider or voice catalog.

## Credentials

The workflow `.github/workflows/voice-casting-azure-duel.yml` reads only these repository Actions secrets:

- `AZURE_SPEECH_KEY`
- `AZURE_SPEECH_REGION`

No production workflow depends on them.

A Speech resource must be created in an Azure region supporting MAI voices. `francecentral` and `westeurope` are currently suitable European choices according to Azure Speech region documentation. Keep the region secret equal to the exact region identifier of the resource because Azure Speech keys are region-scoped.

## Cost discipline

Use an Azure Speech Free (F0) resource when available for the experiment. The current Azure Speech price page lists 0.5 million Neural text-to-speech characters per month in the F0 tier. The experiment is intentionally tiny relative to that allowance.

MAI-Voice-2 is currently an Azure public-preview capability. Preview status is acceptable for lab evidence but is an explicit reason not to make it a production dependency without a separate promotion decision.

## Promotion gate

Azure may become a production-capable provider only if blind listening evidence demonstrates a material improvement and the operational/cost/reliability trade-off remains acceptable.

Required gates remain:

- French pronunciation first;
- acting-fit improvement on hard intentions;
- character identity continuity;
- long-form stability and fatigue;
- deterministic manifest/provenance;
- graceful fallback when the remote provider is unavailable;
- no silent recasting of an established character.

Until those gates pass, Edge remains the production provider and Azure Speech stays a lab-only dependency.
