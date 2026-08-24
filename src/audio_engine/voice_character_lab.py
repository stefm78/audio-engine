"""Minimal frozen-character contract for qualified Voice Casting Lab renderers.

Identity is fail-closed: the anchor file must match its declared SHA-256 before
any model is loaded and after rendering. Individual line synthesis is best-effort
so one residual generation failure does not erase successful lines.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from .providers.qwen3_xvector_lab import Qwen3XVectorLabProvider

SCHEMA = "audio-engine-character-lab-v1"
PROVIDER = "qwen3-xvector-lab"
IDENTITY_MODE = "x_vector_only"
DEFAULT_LANGUAGE = "French"


class CharacterLabError(ValueError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value)).strip("-")
    return value or "line"


def _seed(base_seed: int, character_id: str, line_id: str, text: str) -> int:
    payload = f"{base_seed}\0{character_id}\0{line_id}\0{text}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def freeze_character_identity(
    character_id,
    anchor_path,
    output_dir,
    *,
    base_seed=20260824,
    language=DEFAULT_LANGUAGE,
    source=None,
):
    """Copy an already-approved anchor into a self-contained immutable lab pack.

    This function never synthesizes or regenerates an anchor.
    """
    character_id = str(character_id or "").strip()
    if not character_id:
        raise CharacterLabError("character_id is required")
    anchor_path = Path(anchor_path)
    if not anchor_path.is_file():
        raise FileNotFoundError(anchor_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frozen_anchor = output_dir / "anchor.wav"
    spec_path = output_dir / "character.json"
    if frozen_anchor.exists() or spec_path.exists():
        raise CharacterLabError("character pack already exists; silent replacement is forbidden")
    shutil.copy2(anchor_path, frozen_anchor)
    digest = _sha256(frozen_anchor)
    spec = {
        "schema": SCHEMA,
        "character_id": character_id,
        "provider": PROVIDER,
        "identity_mode": IDENTITY_MODE,
        "language": language,
        "base_seed": int(base_seed),
        "anchor": {"file": "anchor.wav", "sha256": digest, "regeneration": False},
        "source": source or {},
        "claims": {
            "stable_character": True,
            "age_lineage": False,
            "production_promoted": False,
        },
    }
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "frozen", "spec": str(spec_path), "anchor_sha256": digest}


def load_character_identity(spec_path):
    spec_path = Path(spec_path)
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise CharacterLabError(f"unsupported character schema: {data.get('schema')!r}")
    if not str(data.get("character_id") or "").strip():
        raise CharacterLabError("character_id is required")
    if data.get("provider") != PROVIDER:
        raise CharacterLabError("qualified character pack requires qwen3-xvector-lab")
    if data.get("identity_mode") != IDENTITY_MODE:
        raise CharacterLabError("qualified character pack requires x_vector_only identity mode")
    claims = data.get("claims") or {}
    if claims.get("production_promoted") is True:
        raise CharacterLabError("lab character contract cannot claim production promotion")
    if claims.get("age_lineage") is True:
        raise CharacterLabError("age-lineage is not qualified for this character contract")
    anchor = data.get("anchor") or {}
    if anchor.get("regeneration") is not False:
        raise CharacterLabError("anchor regeneration must be explicitly forbidden")
    expected = str(anchor.get("sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise CharacterLabError("anchor.sha256 must be a lowercase SHA-256 digest")
    anchor_path = spec_path.parent / str(anchor.get("file") or "")
    if not anchor_path.is_file():
        raise FileNotFoundError(anchor_path)
    actual = _sha256(anchor_path)
    if actual != expected:
        raise CharacterLabError(
            f"frozen anchor hash mismatch for {data['character_id']}: expected {expected}, got {actual}"
        )
    return data, anchor_path


def render_character_lines(
    spec_path,
    lines,
    output_dir,
    *,
    provider=None,
    model_dir=None,
):
    """Render multiple lines from one verified frozen identity.

    A bad anchor aborts before provider/model initialization. A line-level synthesis
    error is recorded and the remaining lines continue. There is no provider fallback.
    """
    spec, anchor_path = load_character_identity(spec_path)
    expected_hash = spec["anchor"]["sha256"]
    if provider is None:
        if model_dir is None:
            raise CharacterLabError("model_dir is required when provider is not injected")
        provider = Qwen3XVectorLabProvider(model_dir=model_dir, device="cpu")
    if getattr(provider, "identity_mode", IDENTITY_MODE) != IDENTITY_MODE:
        raise CharacterLabError("provider must use x_vector_only identity mode")

    prompt = provider.build_identity_prompt(anchor_path)
    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    base_seed = int(spec.get("base_seed", 20260824))
    language = spec.get("language") or DEFAULT_LANGUAGE
    rendered, failures = [], []
    started = time.monotonic()

    for index, raw in enumerate(lines, 1):
        if not isinstance(raw, dict):
            raise CharacterLabError(f"line {index} must be an object")
        line_id = str(raw.get("id") or f"line-{index}").strip()
        text = str(raw.get("text") or "").strip()
        if not text:
            raise CharacterLabError(f"line {line_id!r} has empty text")
        seed = int(raw.get("seed", _seed(base_seed, spec["character_id"], line_id, text)))
        out = clips_dir / f"{index:03d}--{_slug(line_id)}.wav"
        clip_started = time.monotonic()
        try:
            provider.synthesize(
                {"text": text, "language": raw.get("language", language), "seed": seed},
                out,
                voice_clone_prompt=prompt,
            )
            rendered.append({
                "id": line_id,
                "text": text,
                "file": str(out.relative_to(output_dir)),
                "seed": seed,
                "render_seconds": round(time.monotonic() - clip_started, 2),
            })
        except Exception as exc:
            failures.append({"id": line_id, "text": text, "seed": seed, "error": str(exc)})

    final_hash = _sha256(anchor_path)
    if final_hash != expected_hash:
        raise CharacterLabError("frozen anchor changed during rendering; results are not trustworthy")

    result = {
        "schema": "audio-engine-character-lab-render-v1",
        "status": "success" if not failures else ("partial" if rendered else "failed"),
        "character_id": spec["character_id"],
        "provider": PROVIDER,
        "identity_mode": IDENTITY_MODE,
        "anchor_sha256": expected_hash,
        "anchor_verified_before_and_after": True,
        "production_promoted": False,
        "age_lineage": False,
        "rendered_count": len(rendered),
        "failure_count": len(failures),
        "rendered": rendered,
        "failures": failures,
        "render_total_seconds": round(time.monotonic() - started, 2),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
