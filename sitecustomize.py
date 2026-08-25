"""Narrow Lab-only import shim for the MeanVC killer workflow.

MeanVC's ``src.model`` package eagerly imports training-only modules (wandb,
accelerate, evaluation stacks) even when offline inference only needs submodules
such as ``src.model.prompt_vp`` and ``src.model.utils``.  During the dedicated
Lab workflow only, expose ``src.model`` as a normal namespace package rooted at
the pinned MeanVC checkout so Python can import those inference submodules
without executing the training-only package initializer.

This file is inert outside the exact MeanVC Lab workflow and is never intended
for Production/Edge use.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import types


if os.environ.get("GITHUB_WORKFLOW") == "Voice Casting MeanVC Identity Emotion Killer":
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", ""))
    meanvc_root = workspace / "MeanVC"
    model_root = meanvc_root / "src" / "model"
    if model_root.is_dir() and str(meanvc_root) in sys.path:
        import src  # type: ignore

        package = types.ModuleType("src.model")
        package.__file__ = str(model_root / "__init__.py")
        package.__package__ = "src.model"
        package.__path__ = [str(model_root)]
        sys.modules["src.model"] = package
        setattr(src, "model", package)
