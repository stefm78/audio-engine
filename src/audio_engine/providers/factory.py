from pathlib import Path

from ..contract import ContractError, load_json
from ..provider_package import validate_provider_package
from .chatterbox_mtl_v3 import ChatterboxMultilingualV3Provider
from .voxcpm2 import VoxCPM2Provider


def build_promoted_providers(
    package_paths,
    workspace_root=".",
    model_cache_root=".provider-models",
):
    providers = {}
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
        providers[provider_id] = provider
    return providers
