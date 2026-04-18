"""Smoke test: package is importable and the scaffold is in place."""
import importlib


def test_package_imports() -> None:
    mod = importlib.import_module("alc_crawler")
    assert mod is not None
