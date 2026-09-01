import hashlib
import json
import re
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
