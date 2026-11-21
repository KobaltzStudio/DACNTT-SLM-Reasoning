P1/P2 Unified Run Config Delivery — 2026-11-17

Files:
- config/p1p2_unified_run.yaml
- config/p1p2_method_registry.yaml (reference copy for standalone test package)
- tests/test_p1p2_unified_config.py

Install into the canonical manual repository by copying only:
- config/p1p2_unified_run.yaml -> <manual>/config/p1p2_unified_run.yaml
- tests/test_p1p2_unified_config.py -> <manual>/tests/test_p1p2_unified_config.py

Do not overwrite existing files. The test expects the already-installed
config/p1p2_method_registry.yaml and the protected config/experiment_config.json
to exist in the repository.

Run from <manual>:
python -m py_compile tests/test_p1p2_unified_config.py
python -m unittest discover -s tests -p "test_p1p2_unified_config.py" -v

This delivery does not create a controller, invoke training, modify frozen P2
configuration, or write run/model artifacts.
