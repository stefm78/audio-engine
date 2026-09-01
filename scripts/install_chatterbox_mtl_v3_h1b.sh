#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import sys
expected=(3,11,16)
if sys.version_info[:3] != expected:
    raise SystemExit(
        f"Chatterbox H1b runtime requires Python {'.'.join(map(str, expected))}; "
        f"got {sys.version.split()[0]}"
    )
PY

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python -m pip install --disable-pip-version-check \
  -r "$root/requirements/chatterbox-mtl-v3-h1b-runtime.txt"

python -m pip install --disable-pip-version-check --no-deps \
  "git+https://github.com/resemble-ai/Perth.git@ce86c49d029f42272c1902eccb675556b9ed2330"
python -m pip install --disable-pip-version-check --no-deps \
  "git+https://github.com/resemble-ai/chatterbox.git@5de7a54aa4e5e2baadb0182dde554908b48b85c2"

python - <<'PY'
import importlib.metadata as m
import sys
checks={
    "chatterbox-tts":"0.1.7",
    "resemble-perth":"1.0.1",
    "torch":"2.6.0",
    "torchaudio":"2.6.0",
    "transformers":"5.2.0",
    "huggingface-hub":"1.29.0",
}
bad=[]
for name,expected in checks.items():
    actual=m.version(name)
    if actual != expected:
        bad.append(f"{name}={actual} expected {expected}")
if bad:
    raise SystemExit("Runtime verification failed: "+"; ".join(bad))
print("CHATTERBOX_H1B_RUNTIME_READY")
PY
