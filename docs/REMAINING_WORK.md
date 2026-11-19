# Remaining scientific work

| Item | Current state | Completion evidence |
|---|---|---|
| A P1-DEFICIT S1 | PASS, 416/500 strict D_dev | Reuse existing adapter and validated sidecar/state. |
| A S2 | PARTIAL, 26-step adapter and 75/500 predictions | Preserve those rows; evaluate remaining 425, publish summary/log/hook/capability state. |
| A S3 | NOT RUN | Start only after A S2 PASS and separate scope approval. |
| B P1P2 S1 | PASS, 406/500 strict D_dev | Reuse existing adapter and validated sidecar/state. |
| B S2/S3 | NOT RUN | Compute fresh NLL at S1/S2, train from those parents and validate each checkpoint before the next. |
| G6 | PARTIAL | Current 39 sidecars, 37 logical groups, 2 alternate provenance records. Validate new sidecars, 85 Gold IDs, 7 capabilities, preserve duplicate provenance and generate CSV/JSON/MD. |
| G7 | PARTIAL | Nine observations on exactly 415 D_dev_select IDs. Require all candidates, strict status valid, earliest tie-break, and a frozen FINAL manifest with independently recorded SHA. |
| G8 | PARTIAL | Seven PNGs and CSVs exist for observed data. Rebuild after the missing checkpoints, verify provenance and seed-13 labels, and report gaps. |
| G9 | NOT RUN / DELEGATED | Linux CPU and approved GPU operations pending. |
| D_test | NOT RUN | Separate approval after G7 FINAL, frozen selection SHA and checkpoint/evaluator SHA verification. |
| Original cleanup | PENDING APPROVAL | Keep originals, exact candidate list and a rollback plan pending. |

The copied analysis is an internal partial snapshot under `analysis/`. Regenerate outputs to a new destination after checkpoint validation. Commands assume the verified writable manual root and approved output paths.

```bash
python -B scripts/build_capability_learning_dynamics.py --manual "$MANUAL_ROOT" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" --output "$ANALYSIS_DIR/g6"
python -B scripts/select_checkpoint_on_dev.py --manual-root "$MANUAL_ROOT" --output "$ANALYSIS_DIR/g7"
python -B scripts/build_p1p2_analysis_figures.py --manual-root "$MANUAL_ROOT" --output "$ANALYSIS_DIR/g8"
sha256sum "$ANALYSIS_DIR/g7/checkpoint_selection_seed13.json"
```
