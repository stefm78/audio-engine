from pathlib import Path

from .contract import ContractError, load_json, validate_program
from .providers.factory import build_promoted_providers
from .voice.render import provider_cache_identity, render_voice_clip
from .voices import load_voice_config, resolve_segments


def prewarm_promoted_provider_cache(
    program_path,
    voices_path,
    provider_package_path,
    cache_root,
    workspace_root=".",
    model_cache_root=".provider-models",
):
    program_path = Path(program_path)
    program = validate_program(load_json(program_path))
    voice_config, _ = load_voice_config(voices_path)
    resolved = resolve_segments(program, voice_config)

    providers = build_promoted_providers(
        [provider_package_path],
        workspace_root=workspace_root,
        model_cache_root=model_cache_root,
    )
    if len(providers) != 1:
        raise ContractError("provider cache prewarm requires exactly one promoted provider package")
    provider = next(iter(providers.values()))

    selected = [segment for segment in resolved if segment["provider"] == provider.name]
    if not selected:
        raise ContractError(
            f"provider package {provider.name!r} is not used by Program {program['id']!r}"
        )

    cache_root = Path(cache_root)
    hits = 0
    misses = 0
    fingerprints = []
    for segment in selected:
        _, cache_hit, fingerprint = render_voice_clip(
            segment,
            provider,
            cache_root,
        )
        fingerprints.append(fingerprint)
        if cache_hit:
            hits += 1
        else:
            misses += 1

    return {
        "schema_version": 1,
        "status": "ready",
        "program_id": program["id"],
        "provider": provider.name,
        "provider_cache_identity": provider_cache_identity(provider),
        "segment_count": len(selected),
        "cache_hits": hits,
        "cache_misses": misses,
        "fingerprints": fingerprints,
    }
