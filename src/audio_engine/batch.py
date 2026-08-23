import glob
import json
from pathlib import Path

from .render import render_program

def render_batch(pattern, output_root, voices_path=None):
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    sources = sorted(path for path in glob.glob(pattern, recursive=True) if Path(path).is_file())
    rendered = []
    failures = []
    for source in sources:
        try:
            manifest = render_program(source, output_root, voices_path)
            rendered.append({"source": source, "id": manifest["id"]})
        except Exception as exc:
            failures.append({"source": source, "error": str(exc)})
    status = "success"
    if not sources:
        status = "empty"
    elif failures and rendered:
        status = "partial"
    elif failures:
        status = "failed"
    report = {
        "schema_version": 1,
        "status": status,
        "source_count": len(sources),
        "rendered_count": len(rendered),
        "failure_count": len(failures),
        "rendered": rendered,
        "failures": failures,
    }
    (output_root / "render-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
