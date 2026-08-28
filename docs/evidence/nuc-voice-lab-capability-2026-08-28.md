# NUC Voice Lab capability evidence — 2026-08-28

Status: **LAB EVIDENCE ONLY — CAPABILITY CHARACTERIZED**

Production Edge remains unchanged.

Baseline repository state used for this closeout:
`main@159fbebc34fd3797595eb1425fbf81c4f4801352`.

## Purpose

Record the verified execution envelope of the Intel NUC8i7HVK used as an optional Voice Lab machine.

This evidence does **not** promote any experimental model to Production and does not make the NUC a Production dependency.

## Host

- Windows 11 Professional, build `10.0.26200`
- Intel Core i7-8809G, 4 cores / 8 logical processors
- 31.92 GiB RAM
- Radeon RX Vega M GH, 4096 MiB HBM2
- Intel HD Graphics 630
- system Python 3.10.11 kept clean; experiments use isolated environments under `C:\voice-lab\envs`

WSL2 is available as a secondary Linux compatibility lane:

- Ubuntu 24.04.3 LTS
- kernel `6.6.87.2-microsoft-standard-WSL2`
- 23 GiB RAM exposed
- `/dev/dxg` present
- `/dev/dri` absent
- no ROCm/Vulkan/OpenCL runtime installed in WSL

Windows native remains the preferred Lab host.

## Proven execution backends

### PyTorch CPU

- CPU-only PyTorch build
- AVX2 / MKL / OpenMP active
- 2048x2048 FP32 MatMul median: ~48.1 ms
- verdict: **PASS**

### ONNX Runtime CPU

- ONNX Runtime 1.23.2
- 2048x2048 FP32 MatMul median: ~56.2 ms
- verdict: **PASS**

### ONNX Runtime DirectML

A strict no-CPU-fallback test was executed.

- `DmlExecutionProvider` executed the tested graph
- best observed MatMul medians: ~26.2 ms and ~29.1 ms on the two fast device IDs
- exact DirectML device-id-to-physical-GPU mapping was not treated as authoritative
- verdict: **PASS STRICT DIRECTML**

### OpenVINO

OpenVINO 2026.3.1:

- CPU: PASS, ~71.1 ms MatMul
- Intel HD Graphics 630: PASS, ~85.9 ms MatMul

Verdict: **PASS**

### Vulkan / llama.cpp / Radeon RX Vega M GH

Tested build:

- llama.cpp build 10516
- commit `b95502ba9`
- `Vulkan0 = Radeon RX Vega M GH Graphics`
- 4096 MiB total, ~3434 MiB free during tests

Real GGUF inference was proven, not only device enumeration.

#### ~1.78B Q4_K_M

- full offload: 29/29 layers
- ~935 MiB model buffer on Vega
- generation: ~30.9 tok/s Vulkan vs ~18.5 tok/s CPU
- Vulkan generation speedup: ~1.67x

#### ~3.40B Q4_K_M

- full offload: 37/37 layers
- ~1835 MiB model buffer
- ~1925 MiB total projected device use
- ~1505 MiB free after execution
- generation: ~23.54 tok/s Vulkan vs ~11.09 tok/s CPU
- prompt: ~68.54 tok/s Vulkan vs ~49.85 tok/s CPU
- Vulkan generation speedup: ~2.12x

Verdict: **VULKAN_VEGA_PASS_AND_USEFUL**

Very small models may remain faster on CPU because Vulkan overhead dominates.

## Non-applicable backend

### CUDA

Not applicable: no NVIDIA GPU.

### ROCm/HIP

Do not treat the Vega M GH as a supported ROCm target.

No ROCm installation is authorized merely because the GPU is AMD.

## Practical model envelope

These are resource envelopes, not TTS-quality claims:

- <=500M: comfortable CPU
- ~1-2B quantized: comfortable; Vega useful
- ~3-3.5B quantized: full Vega offload proven
- ~4B quantized: plausible, architecture-dependent
- 7-8B quantized: system-RAM/partial-offload only unless proven otherwise; test only for a scientifically justified candidate
- FP16/FP32 feasibility must be evaluated per architecture

TTS stacks may require several simultaneous submodels; LLM parameter count alone is not a TTS memory guarantee.

## Real TTS integration smoke

MOSS-TTS-Nano was used **only as a resource/integration smoke**, not as a scientific candidate.

Frozen upstream code:

`OpenMOSS/MOSS-TTS-Nano@cc7bdf19c7639c0870dab22045a33b442760f6be`

Path:

- ONNX Runtime CPU inference
- direct cloning from immutable `reference-claire.wav`
- French text
- WeText disabled because the shipped normalization lane is zh/en-oriented
- current upstream ONNX path still imports PyTorch/torchaudio for reference-audio loading/resampling

Result:

- verdict: **PASS_REAL_TTS**
- exit code: 0
- generated WAV: 48 kHz, stereo, PCM16
- duration: 5.04 s
- output SHA-256: `44e5a041a891995b9224fd332e21ae0fbc091f35b607b37cacfcdc0bae0a8e44`
- peak process-tree RSS: ~2029 MiB
- persistent model cache: ~727.8 MiB
- first-run wall time including model download: 32.46 s

This proves the NUC can execute a real French voice-cloning TTS pipeline with persistent model cache and disposable experiment environment.

It does **not** change the scientific classification of MOSS-TTS-Nano: it does not establish an independent fear/panic control.

## Immutable Voice Lab references on the NUC

Persistent read-mostly cache path:

`C:\voice-lab\references\voice-casting-protocol`

Verified exact bytes:

- `reference-claire.wav` — `3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe`
- `reference-lucie.wav` — `9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822`
- `clips/claire--panic.wav` — `ac92fd1f8346b981ac7518e1e698cf8b1c31a96dff069ad60a2d017a17ff9d7f`
- `clips/claire--sadness-contained.wav` — `d2091868592c3c8691c2c0c6a39adaa3613d4941d087c36e4be69e5395a19c84`

Source provenance:

- Actions run `32823632721`
- artifact id `9554047730`
- artifact name `voice-casting-qwen3-contrast-emotion-killer-recovery`

All four source and destination SHA-256 values matched after copy.

The NUC is a **persistent safety/cache copy only**. It is not the sole canonical archive.

Issue #174 remains the authority for creating a durable independent archive before the expiring Actions artifact disappears.

## Local layout

Recommended persistent structure:

```text
C:\voice-lab\
  cache\
  envs\
  logs\
  references\
  tools\
  work\
  tmp\
```

Rules:

- caches and references persist outside job workspaces
- experiment environments and workspaces are disposable/rebuildable
- immutable references are read-mostly and hash-verified
- no Lab cache/model/runtime becomes a Production dependency

## Runner security topology

### 1. Local/manual

**ACCEPTED SAFE BASELINE**

### 2. Private GitHub Lab control-plane -> NUC -> exact audio-engine SHA

**PREFERRED FUTURE TOPOLOGY**

Requirements:

- private control-plane
- exact immutable `audio-engine` commit SHA
- no Production secrets
- disposable job workspace
- persistent caches/references outside workspace
- Lab-only permissions

### 3. Persistent self-hosted runner directly attached to public audio-engine

**REJECTED BY DEFAULT**

The NUC must not execute untrusted public PR/fork code.

## Resource reopening rule

The completed NUC characterization changes only **resource feasibility**.

Scientific rejects remain closed.

A previous `RESOURCE_REJECT` may be reconsidered only when its actual upstream runtime maps to a backend proven on this NUC:

- PyTorch CPU
- ONNX Runtime CPU
- DirectML
- OpenVINO CPU/iGPU
- Vulkan/GGUF Vega

A model size that appears to fit is insufficient by itself.

A candidate still needs:

1. public executable code + weights;
2. compatible licensing;
3. French evidence;
4. arbitrary speaker reference;
5. independent emotion/fear control;
6. a concrete executable path on a proven NUC backend.

Only then may the cheap resource/API gate be reopened.

## Closeout

NUC capability status:

`NUC_VOICE_LAB_CAPABILITY_CHARACTERIZED`

Real TTS integration status:

`REAL_TTS_SMOKE=PASS`

Infrastructure exploration status:

`CLOSED`

Production status:

`EDGE_ACTIVE_UNAFFECTED`

The next Lab action is not another generic NUC benchmark. It is a read-only reassessment of prior resource rejects against the proven backend envelope, followed by at most one cheap preflight for the strongest newly admissible candidate.
