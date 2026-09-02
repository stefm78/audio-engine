#!/usr/bin/env bash
set -euo pipefail

python -m pip install --disable-pip-version-check   --index-url https://download.pytorch.org/whl/cpu   torch==2.6.0 torchaudio==2.6.0

python -m pip install --disable-pip-version-check   numpy==1.26.4   librosa==0.11.0   s3tokenizer==0.3.0   torchcrepe==0.0.24   transformers==4.46.3   diffusers==0.29.0   conformer==0.3.2   safetensors==0.5.3   huggingface_hub==0.33.1   scipy==1.15.3   tqdm==4.67.1   soundfile==0.13.1

python - <<'PY'
import numpy, librosa, torch, torchaudio, torchcrepe
import transformers, diffusers, safetensors, scipy, soundfile
print("BELTOUT_PRODUCTION_RUNTIME_READY")
print("torch", torch.__version__)
print("torchaudio", torchaudio.__version__)
print("numpy", numpy.__version__)
print("librosa", librosa.__version__)
print("transformers", transformers.__version__)
PY
