# Submit Tab

The **Submit** tab provides the user interface for initiating new analysis jobs. It handles file uploads, validation, and launching the MATLAB backend binary.

---

## Workflow Details

1. **Upload Files**: Users upload `.tiff` raw kymograph files alongside paired `.txt` metadata files containing capture settings.
2. **Metadata Matching**: The frontend checks that each uploaded `.tiff` has a matching `.txt` file with the exact same stem name.
3. **Configure & Launch**:
   - Users can label their experiment.
   - They choose whether to wait synchronously for the processing to finish or submit it to the background (asynchronous processing).
   - Upon clicking "Submit", a unique UUID is generated for the job, and files are streamed to `data/jobs/<uuid>/input/`.
   - The job is registered, and a background thread is spawned to execute the compiled MATLAB analysis.

---

## Code Reference

::: tabs.submit
