#!/usr/bin/env bash
set -euo pipefail

# Voice Lab only. Usage:
#   scripts/voice_lab_rvc_gpu_train.sh QUALIFIED_DATASET_DIR WORK_DIR cu118|cu128
# The dataset directory must contain manifest.json and clips/*.wav from the
# machine-qualified Lucie corpus. No parameter auto-tuning is performed.

if [[ $# -ne 3 ]]; then
  echo "usage: $0 QUALIFIED_DATASET_DIR WORK_DIR cu118|cu128" >&2
  exit 2
fi

DATASET_DIR="$(realpath "$1")"
WORK_DIR="$(mkdir -p "$2" && realpath "$2")"
CUDA_FLAVOR="$3"
case "$CUDA_FLAVOR" in
  cu118|cu128) ;;
  *) echo "CUDA flavor must be cu118 or cu128" >&2; exit 2 ;;
esac

AUDIO_ENGINE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RVC_DIR="$WORK_DIR/RVC"
VENV="$WORK_DIR/.venv"
EXP="lucie_rvc_v2_32k"
RAW="$RVC_DIR/datasets/lucie-qualified"
OUT="$WORK_DIR/output"
RVC_REV="81eed5e8f68b6bed1789f682fe78cdd324495afc"
MODEL_REPO="lj1995/VoiceConversionWebUI"

mkdir -p "$OUT"

if [[ ! -f "$DATASET_DIR/manifest.json" ]]; then
  echo "missing $DATASET_DIR/manifest.json" >&2; exit 1
fi
if [[ ! -d "$DATASET_DIR/clips" ]]; then
  echo "missing $DATASET_DIR/clips" >&2; exit 1
fi

python3.12 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install --disable-pip-version-check -e "$AUDIO_ENGINE_ROOT"
python - <<PY
from pathlib import Path
from audio_engine.voice_lab_rvc_gpu_package import validate_dataset_manifest
m=validate_dataset_manifest(Path(r'''$DATASET_DIR/manifest.json'''))
print('DATASET_PASS', m['accepted_duration_seconds'], m['aggregate_wer'], m['expansion_acceptance_rate'])
PY

if [[ ! -d "$RVC_DIR/.git" ]]; then
  git clone --filter=blob:none https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git "$RVC_DIR"
fi
git -C "$RVC_DIR" fetch --depth=1 origin "$RVC_REV"
git -C "$RVC_DIR" checkout --detach FETCH_HEAD
test "$(git -C "$RVC_DIR" rev-parse HEAD)" = "$RVC_REV"
grep -qi "MIT License" "$RVC_DIR/LICENSE"

python - <<PY
import subprocess
from audio_engine.voice_lab_rvc_gpu_package import RVC_CONFIG_BLOB, RVC_SOURCE_BLOBS
root=r'''$RVC_DIR'''
def blob(path):
    return subprocess.check_output(['git','-C',root,'hash-object',path], text=True).strip()
assert blob('configs/v2/32k.json') == RVC_CONFIG_BLOB
for path, expected in RVC_SOURCE_BLOBS.items():
    got=blob(path)
    if got != expected: raise SystemExit(f'RVC source blob mismatch {path}: {got}')
print('RVC_SOURCE_PROVENANCE_PASS')
PY

if [[ "$CUDA_FLAVOR" == "cu118" ]]; then
  python -m pip install torch==2.7.1+cu118 torchaudio==2.7.1+cu118 \
    --index-url https://download.pytorch.org/whl/cu118 --extra-index-url https://pypi.org/simple
  REQ="$RVC_DIR/requirments_cu118_py312.txt"
else
  python -m pip install torch==2.7.1+cu128 torchaudio==2.7.1+cu128 \
    --index-url https://download.pytorch.org/whl/cu128 --extra-index-url https://pypi.org/simple
  REQ="$RVC_DIR/requirments_cu128_py312.txt"
fi
python -m pip install -r "$REQ"
python -m pip install --disable-pip-version-check huggingface_hub==0.36.0
python -m pip check

python - <<'PY'
import torch
if not torch.cuda.is_available(): raise SystemExit('CUDA GPU unavailable')
if torch.cuda.device_count() != 1: raise SystemExit(f'exactly one CUDA GPU required, got {torch.cuda.device_count()}')
p=torch.cuda.get_device_properties(0)
mem=p.total_memory/(1024**3)
print('GPU', p.name, 'VRAM_GiB', mem, 'torch_cuda', torch.version.cuda)
if mem < 10.0: raise SystemExit('GPU contract requires >=10 GiB VRAM for fixed batch 4; no auto-batch fallback')
PY

mkdir -p "$RVC_DIR/assets/hubert_base" "$RVC_DIR/assets/rmvpe" "$RVC_DIR/assets/pretrained_v2" "$RVC_DIR/.model-downloads" "$RVC_DIR/logs" "$RVC_DIR/assets/weights" "$RVC_DIR/assets/indices"
python - <<PY
import hashlib, json, shutil
from pathlib import Path
from huggingface_hub import hf_hub_download
from audio_engine.voice_lab_rvc_gpu_package import MODEL_ASSETS
repo='$MODEL_REPO'
root=Path(r'''$RVC_DIR''')
# Content hashes are authoritative. main is permitted only because every large
# executable/model asset is rejected if its bytes differ from this manifest.
items={
 'hubert_base/pytorch_model.bin': root/'assets/hubert_base/pytorch_model.bin',
 'hubert_base/config.json': root/'assets/hubert_base/config.json',
 'hubert_base/preprocessor_config.json': root/'assets/hubert_base/preprocessor_config.json',
 'rmvpe.pt': root/'assets/rmvpe/rmvpe.pt',
 'pretrained_v2/f0G32k.pth': root/'assets/pretrained_v2/f0G32k.pth',
 'pretrained_v2/f0D32k.pth': root/'assets/pretrained_v2/f0D32k.pth',
 'mute.zip': root/'.model-downloads/mute.zip',
}
for remote,dst in items.items():
    src=Path(hf_hub_download(repo_id=repo, filename=remote, revision='main'))
    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
large_map={
 'assets/hubert_base/pytorch_model.bin':'assets/hubert_base/pytorch_model.bin',
 'assets/rmvpe/rmvpe.pt':'assets/rmvpe/rmvpe.pt',
 'assets/pretrained_v2/f0G32k.pth':'assets/pretrained_v2/f0G32k.pth',
 'assets/pretrained_v2/f0D32k.pth':'assets/pretrained_v2/f0D32k.pth',
 'mute.zip':'.model-downloads/mute.zip',
}
for key,rel in large_map.items():
    p=root/rel; got=hashlib.sha256(p.read_bytes()).hexdigest(); expected=MODEL_ASSETS[key]
    if got!=expected: raise SystemExit(f'bootstrap SHA mismatch {key}: {got}')
cfg=json.loads((root/'assets/hubert_base/config.json').read_text())
pre=json.loads((root/'assets/hubert_base/preprocessor_config.json').read_text())
assert cfg.get('architectures')==['HubertModelWithFinalProj']
assert pre.get('sampling_rate')==16000 and pre.get('do_normalize') is False
print('BOOTSTRAP_MODEL_PROVENANCE_PASS')
PY
(cd "$RVC_DIR" && python -m zipfile -e .model-downloads/mute.zip logs)

rm -rf "$RAW"
mkdir -p "$RAW"
cp "$DATASET_DIR"/clips/*.wav "$RAW"/
CLIP_COUNT="$(find "$RAW" -maxdepth 1 -type f -name '*.wav' | wc -l)"
if [[ "$CLIP_COUNT" -lt 1 ]]; then echo "no dataset WAVs" >&2; exit 1; fi
printf 'staged_clips=%s\n' "$CLIP_COUNT"

cd "$RVC_DIR"
rm -rf "logs/$EXP"
mkdir -p "logs/$EXP"
cp configs/v2/32k.json "logs/$EXP/config.json"

python train/preprocess.py "$RAW" 32000 4 "logs/$EXP" False 3.7
python train/dataset/extract_f0.py cuda 1 0 0 "logs/$EXP" true
python train/dataset/extract_hubert_feature.py cuda:0 1 0 0 "logs/$EXP" v2 true

PYTHONPATH="$AUDIO_ENGINE_ROOT/src:$PYTHONPATH" python - <<PY
from pathlib import Path
from audio_engine.voice_lab_rvc_gpu_package import write_filelist
p=write_filelist(Path(r'''$RVC_DIR/logs/$EXP'''), Path(r'''$RVC_DIR'''))
rows=[x for x in p.read_text().splitlines() if x.strip()]
print('FILELIST_PASS rows=',len(rows),'real=',len(rows)-2,'mute=',2)
PY

test -s "logs/$EXP/filelist.txt"
python train/train.py \
  -e "$EXP" -sr 32k -f0 1 -bs 4 -g 0 -te 200 -se 25 \
  -pg assets/pretrained_v2/f0G32k.pth \
  -pd assets/pretrained_v2/f0D32k.pth \
  -l 1 -c 0 -sw 1 -v v2

test -s "assets/weights/$EXP.pth"
python train/train_index.py "$EXP" v2 assets/indices 4 single
INDEX="$(find "logs/$EXP" -maxdepth 1 -type f -name 'added_IVF*_Flat_nprobe_*_v2.index' | sort | tail -1)"
test -n "$INDEX" && test -s "$INDEX"

cp "assets/weights/$EXP.pth" "$OUT/$EXP.pth"
cp "$INDEX" "$OUT/$(basename "$INDEX")"
cp "$DATASET_DIR/manifest.json" "$OUT/dataset-manifest.json"
sha256sum "$OUT"/* > "$OUT/SHA256SUMS"

PYTHONPATH="$AUDIO_ENGINE_ROOT/src:$PYTHONPATH" python - <<PY
import hashlib, json, platform, subprocess
from pathlib import Path
import torch
from audio_engine.voice_lab_rvc_gpu_package import package_spec
out=Path(r'''$OUT''')
model=out/'$EXP.pth'
index=next(out.glob('added_IVF*.index'))
report=package_spec()
report.update({
 'status':'gpu-training-complete-unqualified',
 'model_file':model.name,
 'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
 'index_file':index.name,
 'index_sha256':hashlib.sha256(index.read_bytes()).hexdigest(),
 'gpu':torch.cuda.get_device_name(0),
 'gpu_vram_bytes':torch.cuda.get_device_properties(0).total_memory,
 'torch':torch.__version__,
 'torch_cuda':torch.version.cuda,
 'python':platform.python_version(),
 'training_complete':True,
 'machine_killer_evaluated':False,
 'human_gate':False,
 'production_qualified':False,
})
(out/'training-provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
PY

echo "RVC GPU TRAINING COMPLETE — model remains Lab-only and UNQUALIFIED until killer evaluation."
echo "Outputs: $OUT"
