#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import sys
expected=(3,11,16)
if sys.version_info[:3] != expected:
    raise SystemExit(
        f"VoxCPM2 Production runtime requires Python {'.'.join(map(str, expected))}; "
        f"got {sys.version.split()[0]}"
    )
PY

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "ERROR: VoxCPM2 runtime requires ffmpeg + ffprobe; no supported provisioner is available." >&2
    exit 2
  fi
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends ffmpeg
fi

ffmpeg -version | head -n 1
ffprobe -version | head -n 1
if command -v dpkg-query >/dev/null 2>&1; then
  printf 'VOXCPM2_SYSTEM_FFMPEG_PACKAGE='
  dpkg-query -W -f='${Version}\n' ffmpeg
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python -m pip install --disable-pip-version-check \
  --index-url https://download.pytorch.org/whl/cpu \
  "torch==2.7.1+cpu" "torchaudio==2.7.1+cpu"

python -m pip install --disable-pip-version-check \
  -r "$root/requirements/voxcpm2-p4-runtime.txt"

python -m pip install --disable-pip-version-check --no-deps \
  "git+https://github.com/OpenBMB/VoxCPM.git@ee8161e9e1b7b082cb5721a3a9980da4204401e6"

python -m pip check
python - <<'PY'
import importlib.metadata as m
checks={
    "voxcpm":"2.0.3.post23+gee8161e9e",
    "torch":"2.7.1+cpu",
    "torchaudio":"2.7.1+cpu",
    "pydub":"0.25.1",
    "soundfile":"0.12.1",
    "huggingface-hub":"1.29.0",
    "transformers":"5.16.1",
}
bad=[]
for name,expected in checks.items():
    actual=m.version(name)
    if actual != expected:
        bad.append(f"{name}={actual} expected {expected}")
if bad:
    raise SystemExit("VoxCPM2 runtime verification failed: "+"; ".join(bad))
print("VOXCPM2_P4_RUNTIME_READY")
PY
