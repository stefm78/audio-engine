import shutil
import subprocess
from pathlib import Path

from ..contract import ContractError, sha256_file


def verify_system_runtime(runtime, provider_label):
    evidence = []
    for item in runtime.get("system_dependencies", []):
        commands = []
        for command in item["commands"]:
            executable = shutil.which(command)
            if not executable:
                raise ContractError(
                    f"{provider_label} system runtime command is unavailable: {command!r}"
                )
            probe = subprocess.run(
                [executable, "-version"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            first_line = (probe.stdout or "").splitlines()[:1]
            if probe.returncode != 0 or not first_line:
                raise ContractError(
                    f"{provider_label} system runtime version probe failed: {command!r}"
                )
            commands.append({
                "command": command,
                "executable": executable,
                "version": first_line[0].strip(),
            })
        evidence.append({
            "name": item["name"],
            "reference_version": item.get("reference_version"),
            "commands": commands,
        })
    return evidence


def verify_model_assets(package, model_dir, provider_label):
    model_dir = Path(model_dir).resolve()
    if not model_dir.is_dir():
        raise ContractError(f"{provider_label} model directory not found: {model_dir}")
    verified = []
    for item in package["model"]["integrity"]:
        relative = Path(item["name"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ContractError(
                f"{provider_label} model integrity name must be safe relative path: "
                f"{item['name']!r}"
            )
        target = (model_dir / relative).resolve()
        try:
            target.relative_to(model_dir)
        except ValueError as exc:
            raise ContractError(
                f"{provider_label} model asset escapes model directory: {item['name']!r}"
            ) from exc
        if not target.is_file():
            raise ContractError(f"{provider_label} model asset missing: {item['name']}")
        actual = sha256_file(target)
        if actual != item["sha256"]:
            raise ContractError(
                f"{provider_label} model asset SHA-256 mismatch for {item['name']}: "
                f"{actual} != {item['sha256']}"
            )
        verified.append(target)
    return verified


def verify_references(package, workspace_root, provider_label):
    root = Path(workspace_root).resolve()
    references = {}
    for item in package.get("references", []):
        target = (root / item["path"]).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ContractError(
                f"{provider_label} reference escapes workspace: {item['path']}"
            ) from exc
        if not target.is_file():
            raise ContractError(f"{provider_label} reference missing: {item['path']}")
        actual = sha256_file(target)
        if actual != item["sha256"]:
            raise ContractError(
                f"{provider_label} reference SHA-256 mismatch for {item['id']}: "
                f"{actual} != {item['sha256']}"
            )
        references[item["id"]] = target
    return references
