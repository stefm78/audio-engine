import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

from .contract import ContractError, load_json

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _non_empty(value):
    return isinstance(value, str) and bool(value.strip())


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_sha(value, label, errors):
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        errors.append(f"{label} must be a lowercase SHA-256 hex digest")


def _validate_relpath(value, label, errors):
    if not _non_empty(value):
        errors.append(f"{label} must be a non-empty relative path")
        return
    path = Path(value)
    if path.is_absolute() or "://" in value or ".." in path.parts:
        errors.append(f"{label} must be a workspace-relative local path")


def validate_provider_package(package, package_path=None, workspace_root=".", verify_files=False, voice_pack_path=None):
    errors = []
    if not isinstance(package, dict):
        raise ContractError("provider package must be an object")
    if package.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not _non_empty(package.get("id")):
        errors.append("id is required")
    if package.get("fallback") != "fail":
        errors.append("fallback must be exactly 'fail'; silent fallback is forbidden")

    provider = package.get("provider")
    if not isinstance(provider, dict):
        errors.append("provider must be an object")
    else:
        if not _non_empty(provider.get("id")):
            errors.append("provider.id is required")
        if not _non_empty(provider.get("implementation_version")):
            errors.append("provider.implementation_version is required")

    runtime = package.get("runtime")
    if not isinstance(runtime, dict):
        errors.append("runtime must be an object")
    else:
        if runtime.get("kind") != "python":
            errors.append("runtime.kind must be 'python'")
        if not _non_empty(runtime.get("python")):
            errors.append("runtime.python is required")
        dependencies = runtime.get("dependencies")
        if not isinstance(dependencies, list) or not dependencies:
            errors.append("runtime.dependencies must be a non-empty array")
        else:
            for i, dep in enumerate(dependencies, 1):
                if not isinstance(dep, dict) or not _non_empty(dep.get("name")):
                    errors.append(f"runtime.dependencies[{i}].name is required")
                    continue
                has_version = _non_empty(dep.get("version"))
                has_revision = _non_empty(dep.get("revision"))
                if has_version == has_revision:
                    errors.append(f"runtime.dependencies[{i}] needs exactly one of version or revision")
                if has_revision and not _GIT_SHA_RE.fullmatch(dep["revision"]):
                    errors.append(f"runtime.dependencies[{i}].revision must be an exact 40-char Git SHA")

    model = package.get("model")
    if not isinstance(model, dict):
        errors.append("model must be an object")
    else:
        if not _non_empty(model.get("id")):
            errors.append("model.id is required")
        if not _non_empty(model.get("revision")):
            errors.append("model.revision is required")
        source = model.get("source", "local")
        if source not in ("local", "huggingface"):
            errors.append("model.source must be 'local' or 'huggingface'")
        if source == "huggingface" and (
            not isinstance(model.get("revision"), str)
            or not _GIT_SHA_RE.fullmatch(model.get("revision", ""))
        ):
            errors.append("model.revision must be an exact 40-char commit SHA for huggingface")
        integrity = model.get("integrity")
        if not isinstance(integrity, list) or not integrity:
            errors.append("model.integrity must be a non-empty array")
        else:
            names = set()
            for i, item in enumerate(integrity, 1):
                if not isinstance(item, dict) or not _non_empty(item.get("name")):
                    errors.append(f"model.integrity[{i}].name is required")
                    continue
                if item["name"] in names:
                    errors.append(f"duplicate model integrity item: {item['name']}")
                names.add(item["name"])
                _validate_sha(item.get("sha256"), f"model.integrity[{i}].sha256", errors)
                if "path" in item:
                    _validate_relpath(item.get("path"), f"model.integrity[{i}].path", errors)

    _validate_sha(package.get("voice_pack_sha256"), "voice_pack_sha256", errors)

    synthesis = package.get("synthesis")
    if not isinstance(synthesis, dict):
        errors.append("synthesis must be an object")
    else:
        seed = synthesis.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
            errors.append("synthesis.seed must be a non-negative integer")
        if not isinstance(synthesis.get("parameters"), dict):
            errors.append("synthesis.parameters must be an object")

    references = package.get("references", [])
    if not isinstance(references, list):
        errors.append("references must be an array")
        references = []
    seen = set()
    for i, item in enumerate(references, 1):
        if not isinstance(item, dict) or not _non_empty(item.get("id")):
            errors.append(f"references[{i}].id is required")
            continue
        if item["id"] in seen:
            errors.append(f"duplicate reference id: {item['id']}")
        seen.add(item["id"])
        _validate_relpath(item.get("path"), f"references[{i}].path", errors)
        _validate_sha(item.get("sha256"), f"references[{i}].sha256", errors)
        source = item.get("source")
        if source is not None:
            if not isinstance(source, dict):
                errors.append(f"references[{i}].source must be an object")
            elif source.get("type") != "github_release":
                errors.append(f"references[{i}].source.type must be 'github_release'")
            else:
                for field in ("repository", "tag", "asset"):
                    if not _non_empty(source.get(field)):
                        errors.append(f"references[{i}].source.{field} is required")

    if verify_files:
        root = Path(workspace_root).resolve()
        if voice_pack_path is None:
            errors.append("voice_pack_path is required when verify_files=true")
        else:
            voice_pack = (root / voice_pack_path).resolve()
            try:
                voice_pack.relative_to(root)
            except ValueError:
                errors.append("voice_pack_path escapes workspace_root")
            else:
                if not voice_pack.is_file():
                    errors.append(f"voice pack not found: {voice_pack_path}")
                elif _sha256(voice_pack) != package.get("voice_pack_sha256"):
                    errors.append("voice_pack_sha256 mismatch")

        for i, item in enumerate(references, 1):
            if not isinstance(item, dict) or not _non_empty(item.get("path")):
                continue
            target = (root / item["path"]).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                errors.append(f"references[{i}].path escapes workspace_root")
                continue
            if not target.is_file():
                errors.append(f"reference not found: {item['path']}")
            elif _sha256(target) != item.get("sha256"):
                errors.append(f"references[{i}].sha256 mismatch")

        integrity = model.get("integrity", []) if isinstance(model, dict) else []
        for i, item in enumerate(integrity, 1):
            if not isinstance(item, dict) or not item.get("path"):
                continue
            target = (root / item["path"]).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                errors.append(f"model.integrity[{i}].path escapes workspace_root")
                continue
            if not target.is_file():
                errors.append(f"model integrity file not found: {item['path']}")
            elif _sha256(target) != item.get("sha256"):
                errors.append(f"model.integrity[{i}].sha256 mismatch")

    if errors:
        raise ContractError("; ".join(errors))
    return package


def provider_package_report(path, workspace_root=".", verify_files=False, voice_pack_path=None):
    path = Path(path)
    package = validate_provider_package(
        load_json(path),
        package_path=path,
        workspace_root=workspace_root,
        verify_files=verify_files,
        voice_pack_path=voice_pack_path,
    )
    return {
        "schema_version": 1,
        "status": "valid",
        "id": package["id"],
        "provider": package["provider"]["id"],
        "fallback": package["fallback"],
        "package_sha256": _sha256(path),
        "model_revision": package["model"]["revision"],
        "model_integrity_items": len(package["model"]["integrity"]),
        "reference_count": len(package.get("references", [])),
        "seed": package["synthesis"]["seed"],
        "files_verified": bool(verify_files),
    }


def hydrate_provider_model(path, cache_root=".provider-models"):
    """Hydrate an exact remote model snapshot, then verify declared SHA-256.

    Hydration is deliberately separate from synthesis. A provider adapter may
    consume the returned directory only after every declared file matches its
    immutable integrity record.
    """
    path = Path(path)
    package = validate_provider_package(load_json(path), package_path=path)
    model = package["model"]
    if model.get("source") != "huggingface":
        raise ContractError(
            "provider model hydration currently supports model.source='huggingface' only"
        )

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise ContractError(
            "huggingface-hub is required for model hydration; synthesis never installs it implicitly"
        ) from exc

    cache_root = Path(cache_root).resolve()
    destination = (
        cache_root
        / package["provider"]["id"]
        / model["revision"]
    )
    destination.mkdir(parents=True, exist_ok=True)
    filenames = [item["name"] for item in model["integrity"]]
    snapshot_download(
        repo_id=model["id"],
        revision=model["revision"],
        allow_patterns=filenames,
        local_dir=str(destination),
        token=os.getenv("HF_TOKEN"),
    )

    verified = []
    for item in model["integrity"]:
        target = destination / item["name"]
        if not target.is_file():
            raise ContractError(f"hydrated model asset missing: {item['name']}")
        actual = _sha256(target)
        if actual != item["sha256"]:
            raise ContractError(
                f"hydrated model SHA-256 mismatch for {item['name']}: "
                f"{actual} != {item['sha256']}"
            )
        verified.append({
            "name": item["name"],
            "sha256": actual,
            "bytes": target.stat().st_size,
        })

    return {
        "schema_version": 1,
        "status": "ready",
        "provider": package["provider"]["id"],
        "model_id": model["id"],
        "model_revision": model["revision"],
        "model_dir": str(destination),
        "verified": verified,
        "network_used": True,
        "fallback": package["fallback"],
    }


def hydrate_provider_references(path, workspace_root="."):
    """Materialize content-addressed reference assets from explicit sources."""
    path = Path(path)
    package = validate_provider_package(load_json(path), package_path=path)
    root = Path(workspace_root).resolve()
    hydrated = []
    for item in package.get("references", []):
        target = (root / item["path"]).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ContractError(f"reference path escapes workspace: {item['path']}") from exc

        if target.is_file() and _sha256(target) == item["sha256"]:
            hydrated.append({
                "id": item["id"],
                "path": item["path"],
                "sha256": item["sha256"],
                "cache_hit": True,
            })
            continue

        source = item.get("source")
        if not source:
            raise ContractError(
                f"reference {item['id']!r} is missing and has no explicit hydration source"
            )
        repository = source["repository"]
        tag = source["tag"]
        asset = source["asset"]
        url = f"https://github.com/{repository}/releases/download/{tag}/{asset}"
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(target.suffix + ".download")
        temp.unlink(missing_ok=True)
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "recit-audio-engine-provider-hydration/1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response, temp.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            actual = _sha256(temp)
            if actual != item["sha256"]:
                raise ContractError(
                    f"hydrated reference SHA-256 mismatch for {item['id']}: "
                    f"{actual} != {item['sha256']}"
                )
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)

        hydrated.append({
            "id": item["id"],
            "path": item["path"],
            "sha256": item["sha256"],
            "cache_hit": False,
            "source": url,
        })

    return {
        "schema_version": 1,
        "status": "ready",
        "provider": package["provider"]["id"],
        "references": hydrated,
        "fallback": package["fallback"],
    }
