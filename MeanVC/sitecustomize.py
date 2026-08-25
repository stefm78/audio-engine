"""Narrow Lab-only import shim for the MeanVC killer workflow.

The pinned MeanVC package eagerly imports training-only modules from
``src.model.__init__``. Offline inference only needs submodules such as
``src.model.prompt_vp`` and ``src.model.utils``. Because this file lives in the
MeanVC directory already present on the workflow PYTHONPATH, Python loads it at
startup and exposes ``src.model`` as a namespace package without executing the
training-only initializer.

It is inert outside the exact MeanVC Lab workflow. The upstream MeanVC checkout
does not contain a sitecustomize.py at the pinned revision, so the nested Git
checkout leaves this Lab-only untracked shim in place.
"""

from __future__ import annotations

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
