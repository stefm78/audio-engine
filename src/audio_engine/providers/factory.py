from pathlib import Path

from ..contract import ContractError, load_json
from ..provider_package import validate_provider_package
from .chatterbox_mtl_v3 import ChatterboxMultilingualV3Provider
from .voxcpm2 import VoxCPM2Provider


class CacheOnlyProvider:
    """Preserve promoted provider identity while forbidding runtime synthesis."""

    def __init__(self, provider):
        self._provider = provider
        self.name = provider.name
        self.processing = f"cache-only:{getattr(provider, 'processing', 'unknown')}"
        self.edge_silence_normalization = getattr(
            provider, "edge_silence_normalization", True
        )
        self.cache_compatible_identities = getattr(
            provider, "cache_compatible_identities", ()
        )

    def cache_identity(self):
        explicit = getattr(self._provider, "cache_identity", None)
        return explicit() if callable(explicit) else explicit

    def synthesize(self, segment, path):
        raise RuntimeError(
            f"Promoted provider {self.name!r} is cache-only in final render; "
            "prewarm the exact provider cache in its isolated runtime first"
        )


def build_promoted_providers(
    package_paths,
    workspace_root=".",
    model_cache_root=".provider-models",
    cache_only_ids=(),
):
    providers = {}
    cache_only_ids = set(cache_only_ids or ())
    cache_root = Path(model_cache_root).resolve()
    for package_path in package_paths or []:
        package_path = Path(package_path)
        package = validate_provider_package(
            load_json(package_path),
            package_path=package_path,
        )
        provider_id = package["provider"]["id"]
        if provider_id in providers:
            raise ContractError(f"duplicate provider package for {provider_id!r}")

        if provider_id == "chatterbox-multilingual-v3":
            model_dir = cache_root / provider_id / package["model"]["revision"]
            provider = ChatterboxMultilingualV3Provider(
                package_path,
                workspace_root=workspace_root,
                model_dir=model_dir,
            )
        elif provider_id == "voxcpm2":
            model_dir = cache_root / provider_id / package["model"]["revision"]
            provider = VoxCPM2Provider(
                package_path,
                workspace_root=workspace_root,
                model_dir=model_dir,
            )
        else:
            raise ContractError(
                f"provider package {provider_id!r} has no promoted Production adapter"
            )
        if provider_id in cache_only_ids:
            provider = CacheOnlyProvider(provider)
        providers[provider_id] = provider

    unknown = cache_only_ids - set(providers)
    if unknown:
        raise ContractError(
            "cache-only promoted provider ids have no matching package: "
            + ", ".join(sorted(unknown))
        )
    return providers
