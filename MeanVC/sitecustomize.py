"""Narrow Lab-only packaging compatibility for the MeanVC killer workflow.

The pinned MeanVC package eagerly imports training-only modules from
``src.model.__init__``. Offline inference only needs submodules such as
``src.model.prompt_vp`` and ``src.model.utils``. During the dedicated Lab
workflow, expose ``src.model`` as a namespace package without executing the
training-only initializer.

The Lab wrapper also uses ``pathlib.Path`` for immutable checkpoint paths while
the pinned upstream ``load_checkpoint`` helper expects a string and calls
``.split`` directly. The adapter below only converts ``os.PathLike`` arguments
to their filesystem string.

There is deliberately no model/runtime arithmetic patch here. In particular,
RoPE behavior is provided natively by the exact x-transformers version pinned
by the workflow. Model bytes, inference parameters, seeds, and gates are not
modified by this file.

It is inert outside the exact MeanVC Lab workflow. The upstream MeanVC checkout
does not contain a sitecustomize.py at the pinned revision, so the nested Git
checkout leaves this Lab-only untracked file in place.
"""

from __future__ import annotations

import importlib
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
