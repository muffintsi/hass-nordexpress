"""Load standalone client/model without importing Home Assistant's entry point."""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "nordexpress"
if "nordexpress_test" not in sys.modules:
    package = types.ModuleType("nordexpress_test")
    package.__path__ = [str(PACKAGE)]
    sys.modules[package.__name__] = package
    for name in ("const", "model", "presentation", "api"):
        spec = importlib.util.spec_from_file_location(
            f"nordexpress_test.{name}", PACKAGE / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        setattr(package, name, module)
        spec.loader.exec_module(module)
