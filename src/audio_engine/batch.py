import glob
import json
from pathlib import Path

from .render import render_program


def render_batch(pattern, output_root, voices_path=None, sounds_path=None):
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    sources = sorted(path for path in glob.glob(pattern, recursive=True) if Path(path).is_file())
    completed = []
    failures = []
    rendered_count = 0
    cached_count = 0
    for source in sources:
        try:
            manifest = render_program(
                source,
                output_root,
                voices_path=voices_path,
                sounds_path=sounds_path,
            )
            cache_hit = bool(manifest.get("cache_hit"))
            if cache_hit:
                cached_count += 1
            else:
                rendered_count += 1
            completed.append({
                "source": source,
                "id": manifest["id"],
                "cache_hit": cache_hit,
            })
        except Exception as exc:
            failures.append({"source": source, "error": str(exc)})
    status = "success"
    if not sources:
        status = "empty"
    elif failures and completed:
        status = "partial"
    elif failures:
        status = "failed"
    report = {
        "schema_version": 1,
        "status": status,
        "source_count": len(sources),
        "success_count": len(completed),
        "rendered_count": rendered_count,
        "cached_count": cached_count,
        "failure_count": len(failures),
        "completed": completed,
        "failures": failures,
    }
    (output_root / "render-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
