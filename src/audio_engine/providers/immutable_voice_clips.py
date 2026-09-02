import hashlib
import json
from pathlib import Path

from ..audio import run_ffmpeg
from ..contract import ContractError, load_json, sha256_file
from ..provider_package import validate_provider_package
from .local_runtime import verify_references

_PROVIDER_ID = "immutable-voice-clips-v1"
_ALLOWED_PARAMETERS = {"reference"}


class ImmutableVoiceClipsProvider:
    """Promoted provider for already-authored immutable voice clips.

    The provider performs no speech synthesis and makes no selection decision.
    Each Program segment must explicitly name one hash-locked reference from
    the provider package. The only materialization step is deterministic audio
    transport into the engine's MP3 voice-cache format.
    """

    name = _PROVIDER_ID
    processing = "immutable-local-clip"
    edge_silence_normalization = False

    def __init__(self, package_path, workspace_root="."):
        self.package_path = Path(package_path)
        self.workspace_root = Path(workspace_root).resolve()
        self.package = validate_provider_package(
            load_json(self.package_path),
            package_path=self.package_path,
            workspace_root=self.workspace_root,
            verify_files=False,
        )
        provider = self.package["provider"]
        if provider["id"] != self.name:
            raise ContractError(
                f"Provider package id {provider['id']!r} does not match adapter {self.name!r}"
            )
        self.references = verify_references(
            self.package,
            self.workspace_root,
            "Immutable voice clips",
        )
        if not self.references:
            raise ContractError("Immutable voice clips provider requires at least one reference")
        self.package_sha256 = sha256_file(self.package_path)

    def cache_identity(self):
        payload = {
            "provider": self.name,
            "adapter_code_sha256": sha256_file(Path(__file__)),
            "implementation_version": self.package["provider"]["implementation_version"],
            "package_sha256": self.package_sha256,
            "references": [
                {"id": item["id"], "sha256": item["sha256"]}
                for item in self.package.get("references", [])
            ],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _resolved_reference(self, segment):
        defaults = dict(self.package["synthesis"].get("parameters") or {})
        overrides = segment.get("provider_parameters") or {}
        unknown = sorted((set(defaults) | set(overrides)) - _ALLOWED_PARAMETERS)
        if unknown:
            raise ContractError(
                "Unsupported immutable-voice-clips-v1 parameters: "
                + ", ".join(unknown)
            )
        controls = {**defaults, **overrides}
        reference_id = controls.get("reference")
        if not isinstance(reference_id, str) or not reference_id:
            raise ContractError(
                "immutable-voice-clips-v1 requires provider_parameters.reference "
                "on every routed segment"
            )
        try:
            return reference_id, self.references[reference_id]
        except KeyError as exc:
            raise ContractError(
                f"Unknown immutable voice clip reference: {reference_id!r}"
            ) from exc

    def synthesize(self, segment, path):
        _, source = self._resolved_reference(segment)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.unlink(missing_ok=True)
        run_ffmpeg([
            "-i", str(source),
            "-map_metadata", "-1",
            "-ac", "1",
            "-c:a", "libmp3lame",
            "-b:a", "96k",
            str(path),
        ])
        if not path.is_file() or path.stat().st_size <= 0:
            raise RuntimeError("Immutable voice clip transport produced no usable audio")
