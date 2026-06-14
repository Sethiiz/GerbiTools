from __future__ import annotations

import gzip
import importlib.util
import os
import sys
import types

from models.deadisland import AreaResult, CollectableReport

_TOOL_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "tools", "DeadIslandCollectables")
)
_PKG = "di_src"

# Registra o pacote src do DeadIslandCollectables com nome único
_pkg_mod = types.ModuleType(_PKG)
_pkg_mod.__path__ = [os.path.join(_TOOL_ROOT, "src")]
_pkg_mod.__package__ = _PKG
sys.modules[_PKG] = _pkg_mod


def _load(module_name: str) -> types.ModuleType:
    full_name = f"{_PKG}.{module_name}"
    path = os.path.join(_TOOL_ROOT, "src", f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(full_name, path)
    mod  = importlib.util.module_from_spec(spec)
    mod.__package__ = _PKG
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod


_models = _load("models")
_parser = _load("save_parser")


def process_save_bytes(file_bytes: bytes) -> CollectableReport:
    data   = gzip.decompress(file_bytes)
    parsed = _parser.parse_save(data)
    return _to_api_model(parsed)


def _to_api_model(parsed) -> CollectableReport:
    return CollectableReport(
        collected_count=parsed.collected_count,
        missing_count=parsed.missing_count,
        total=parsed.total,
        areas=[
            AreaResult(
                name=a.name,
                total=a.total,
                collected=a.collected,
                missing=a.missing,
                complete=a.complete,
            )
            for a in parsed.areas
        ],
    )
