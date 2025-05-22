import importlib.util
import sys

spec = importlib.util.spec_from_file_location(
    "drift_cli", __file__.replace("drift.py", "drift_cli.py")
)
drift_cli = importlib.util.module_from_spec(spec)
sys.modules["drift_cli"] = drift_cli
spec.loader.exec_module(drift_cli)
DriftCLI = drift_cli.DriftCLI
