import hashlib
import json
import re
from pathlib import Path

from .contract import ContractError, load_json

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_UNIT_STATES = ("ready", "hold")


def _non_empty(value):
    return isinstance(value, str) and bool(value.strip())


def _validate_relpath(value, label, errors):
    if not _non_empty(value):
        errors.append(f"{label} must be a non-empty relative path")
        return
    if "://" in value or Path(value).is_absolute():
        errors.append(f"{label} must be a local relative path")
        return
    if ".." in Path(value).parts:
        errors.append(f"{label} must not escape the manifest workspace")


def _validate_sha256(value, label, errors):
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        errors.append(f"{label} must be a lowercase SHA-256 hex digest")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_local(manifest_path, relative):
    base = Path(manifest_path).resolve().parent
    target = (base / relative).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ContractError(f"path escapes manifest workspace: {relative}") from exc
    return target


def validate_production_manifest(manifest, manifest_path=None, verify_files=False):
    errors = []
    if not isinstance(manifest, dict):
        raise ContractError("production manifest must be an object")
    if manifest.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if not _non_empty(manifest.get("id")):
        errors.append("id is required")
    engine_ref = manifest.get("engine_ref")
    if not isinstance(engine_ref, str) or not _GIT_SHA_RE.fullmatch(engine_ref):
        errors.append("engine_ref must be an exact 40-character lowercase Git commit SHA")

    units = manifest.get("units")
    if not isinstance(units, list) or not units:
        errors.append("units must be a non-empty array")
        units = []

    unit_ids = set()
    normalized_units = []
    for index, unit in enumerate(units, start=1):
        label = f"units[{index}]"
        if not isinstance(unit, dict):
            errors.append(f"{label} must be an object")
            continue
        unit_id = unit.get("id")
        if not _non_empty(unit_id):
            errors.append(f"{label}.id is required")
            continue
        if unit_id in unit_ids:
            errors.append(f"duplicate unit id: {unit_id}")
            continue
        unit_ids.add(unit_id)
        state = unit.get("state")
        if state not in _UNIT_STATES:
            errors.append(f"{label}.state must be one of {', '.join(_UNIT_STATES)}")
        provider = unit.get("provider")
        if not _non_empty(provider):
            errors.append(f"{label}.provider is required; fallback is never implicit")

        if state == "hold":
            if not _non_empty(unit.get("hold_reason")):
                errors.append(f"{label}.hold_reason is required when state=hold")
        elif state == "ready":
            for field in ("program", "voice_pack"):
                _validate_relpath(unit.get(field), f"{label}.{field}", errors)
            for field in ("program_sha256", "voice_pack_sha256"):
                _validate_sha256(unit.get(field), f"{label}.{field}", errors)

        normalized_units.append(unit)

    assemblies = manifest.get("assemblies")
    if not isinstance(assemblies, list) or not assemblies:
        errors.append("assemblies must be a non-empty array")
        assemblies = []

    assembly_ids = set()
    referenced_units = []
    for index, assembly in enumerate(assemblies, start=1):
        label = f"assemblies[{index}]"
        if not isinstance(assembly, dict):
            errors.append(f"{label} must be an object")
            continue
        assembly_id = assembly.get("id")
        if not _non_empty(assembly_id):
            errors.append(f"{label}.id is required")
            continue
        if assembly_id in assembly_ids:
            errors.append(f"duplicate assembly id: {assembly_id}")
            continue
        assembly_ids.add(assembly_id)
        inputs = assembly.get("units")
        if not isinstance(inputs, list) or not inputs or not all(_non_empty(v) for v in inputs):
            errors.append(f"{label}.units must be a non-empty array of unit ids")
            continue
        if len(inputs) != len(set(inputs)):
            errors.append(f"{label}.units contains duplicates")
        unknown = sorted(set(inputs) - unit_ids)
        if unknown:
            errors.append(f"{label}.units references unknown units: {unknown}")
        referenced_units.extend(inputs)

    if unit_ids and set(referenced_units) != unit_ids:
        missing = sorted(unit_ids - set(referenced_units))
        extra = sorted(set(referenced_units) - unit_ids)
        errors.append(f"assemblies must cover every unit exactly once; missing={missing}, extra={extra}")
    duplicates = sorted({u for u in referenced_units if referenced_units.count(u) > 1})
    if duplicates:
        errors.append(f"units may belong to only one assembly: {duplicates}")

    master = manifest.get("master")
    if not isinstance(master, dict):
        errors.append("master must be an object")
    else:
        inputs = master.get("assemblies")
        if not isinstance(inputs, list) or not inputs or not all(_non_empty(v) for v in inputs):
            errors.append("master.assemblies must be a non-empty ordered array")
        else:
            if len(inputs) != len(set(inputs)):
                errors.append("master.assemblies contains duplicates")
            unknown = sorted(set(inputs) - assembly_ids)
            if unknown:
                errors.append(f"master.assemblies references unknown assemblies: {unknown}")
            if set(inputs) != assembly_ids:
                missing = sorted(assembly_ids - set(inputs))
                errors.append(f"master.assemblies must include every assembly; missing={missing}")

    if verify_files and manifest_path:
        for index, unit in enumerate(normalized_units, start=1):
            if unit.get("state") != "ready":
                continue
            for field, hash_field in (("program", "program_sha256"), ("voice_pack", "voice_pack_sha256")):
                relative = unit.get(field)
                expected = unit.get(hash_field)
                if not (_non_empty(relative) and isinstance(expected, str) and _SHA256_RE.fullmatch(expected)):
                    continue
                try:
                    path = _resolve_local(manifest_path, relative)
                except ContractError as exc:
                    errors.append(f"units[{index}].{field}: {exc}")
                    continue
                if not path.is_file():
                    errors.append(f"units[{index}].{field} not found: {relative}")
                    continue
                actual = _sha256(path)
                if actual != expected:
                    errors.append(
                        f"units[{index}].{hash_field} mismatch for {relative}: expected {expected}, got {actual}"
                    )

    if errors:
        raise ContractError("; ".join(errors))
    return manifest


def production_plan(manifest_path, verify_files=True):
    manifest_path = Path(manifest_path)
    manifest = validate_production_manifest(
        load_json(manifest_path),
        manifest_path=manifest_path,
        verify_files=verify_files,
    )
    unit_to_assembly = {}
    for assembly in manifest["assemblies"]:
        for unit_id in assembly["units"]:
            unit_to_assembly[unit_id] = assembly["id"]

    ready_units = []
    held_units = []
    by_id = {unit["id"]: unit for unit in manifest["units"]}
    for unit in manifest["units"]:
        item = {
            "id": unit["id"],
            "assembly": unit_to_assembly[unit["id"]],
            "provider": unit["provider"],
        }
        if unit["state"] == "ready":
            item.update(
                program=unit["program"],
                program_sha256=unit["program_sha256"],
                voice_pack=unit["voice_pack"],
                voice_pack_sha256=unit["voice_pack_sha256"],
            )
            ready_units.append(item)
        else:
            item["hold_reason"] = unit["hold_reason"]
            held_units.append(item)

    assembly_plan = []
    for assembly in manifest["assemblies"]:
        held = [uid for uid in assembly["units"] if by_id[uid]["state"] != "ready"]
        assembly_plan.append({
            "id": assembly["id"],
            "units": assembly["units"],
            "state": "ready" if not held else "hold",
            "held_units": held,
        })

    held_assemblies = [a["id"] for a in assembly_plan if a["state"] != "ready"]
    return {
        "schema_version": 1,
        "manifest_id": manifest["id"],
        "manifest_sha256": _sha256(manifest_path),
        "engine_ref": manifest["engine_ref"],
        "ready_units": ready_units,
        "held_units": held_units,
        "assemblies": assembly_plan,
        "master": {
            "assemblies": manifest["master"]["assemblies"],
            "state": "ready" if not held_assemblies else "hold",
            "held_assemblies": held_assemblies,
        },
    }
