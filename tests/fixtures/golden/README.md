# Golden Reference Values

`reference.json` stores baseline outputs from a known-good run of the MATLAB pipeline against the synthetic test input. It is used to detect algorithmic regressions.

## Contents

```json
{
  "n_trajectories": <int>,
  "mean_iOC": <float>
}
```

## How to generate / update

1. Build the MATLAB container:
   ```bash
   scripts/build_matlab.sh
   ```

2. Run the integration test with the update flag:
   ```bash
   pytest tests/integration/ --run-integration --update-golden
   ```

3. Commit `reference.json` alongside any MATLAB source change that intentionally shifts the outputs.

## Tolerances

Comparisons use loose tolerances to catch crashes and wild regressions without flagging minor algorithmic improvements:

| Metric | Tolerance |
|--------|-----------|
| `n_trajectories` | ±20% relative |
| `mean_iOC` | ±15% relative |

## Synthetic input

The test input is `tests/fixtures/test_sample.tiff` + `test_sample.txt`.
Regenerate with:

```bash
pip install tifffile
python tests/fixtures/generate_synthetic.py
```

After regenerating, re-run `--update-golden` to refresh the reference.
