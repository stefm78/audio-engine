"""Narrow Lab-only import/runtime shim for the MeanVC killer workflow.

The pinned MeanVC package eagerly imports training-only modules from
``src.model.__init__``. Offline inference only needs submodules such as
``src.model.prompt_vp`` and ``src.model.utils``. Because this file lives in the
MeanVC directory already present on the workflow PYTHONPATH, Python loads it at
startup and exposes ``src.model`` as a namespace package without executing the
training-only initializer.

The Lab wrapper also uses ``pathlib.Path`` for immutable checkpoint paths while
the pinned upstream ``load_checkpoint`` helper expects a string and calls
``.split`` directly. The compatibility adapter below only converts ``os.PathLike``
arguments to their filesystem string; it does not alter checkpoint content,
model state, inference parameters, seeds, or gates.

The Lab runtime originally pinned ``x-transformers==1.40.2`` for reproducibility.
That October-2024 release returns rotary frequencies as ``[seq, dim]``, while the
pinned MeanVC code (November 2025) explicitly indexes them as
``[batch, seq, dim]``. Contemporary x-transformers 2.11.x adds that singleton
batch axis without changing the rotary values. The narrow adapter below mirrors
only that shape contract (``[seq, dim] -> [1, seq, dim]``); it does not alter
frequencies, model weights, inference parameters, seeds, or evaluation gates.

It is inert outside the exact MeanVC Lab workflow. The upstream MeanVC checkout
does not contain a sitecustomize.py at the pinned revision, so the nested Git
checkout leaves this Lab-only untracked shim in place.
"""

from __future__ import annotations

import importlib
from importlib import metadata
import os
from pathlib import Path
import sys
import types


if os.environ.get("GITHUB_WORKFLOW") == "Voice Casting MeanVC Identity Emotion Killer":
    meanvc_root = Path(__file__).resolve().parent
    model_root = meanvc_root / "src" / "model"
    if model_root.is_dir():
        import src  # type: ignore

        package = types.ModuleType("src.model")
        package.__file__ = str(model_root / "__init__.py")
        package.__package__ = "src.model"
        package.__path__ = [str(model_root)]
        sys.modules["src.model"] = package
        setattr(src, "model", package)

        utils = importlib.import_module("src.model.utils")
        _upstream_load_checkpoint = utils.load_checkpoint

        def _load_checkpoint_path_compat(model, ckpt_path, *args, **kwargs):
            if isinstance(ckpt_path, os.PathLike):
                ckpt_path = os.fspath(ckpt_path)
            return _upstream_load_checkpoint(model, ckpt_path, *args, **kwargs)

        utils.load_checkpoint = _load_checkpoint_path_compat

        x_transformers_version = metadata.version("x-transformers")
        if x_transformers_version != "1.40.2":
            raise RuntimeError(
                f"Lab RoPE compatibility shim expected x-transformers 1.40.2, got {x_transformers_version}"
            )

        from x_transformers.x_transformers import RotaryEmbedding

        _upstream_forward_from_seq_len = RotaryEmbedding.forward_from_seq_len

        def _forward_from_seq_len_batched_compat(self, seq_len):
            freqs, scale = _upstream_forward_from_seq_len(self, seq_len)
            if getattr(freqs, "ndim", None) == 2:
                freqs = freqs.unsqueeze(0)
            if getattr(scale, "ndim", None) == 2:
                scale = scale.unsqueeze(0)
            return freqs, scale

        RotaryEmbedding.forward_from_seq_len = _forward_from_seq_len_batched_compat
