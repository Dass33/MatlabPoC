# Presets

A **preset** defines *which* pipeline settings the sidebar shows, how they are labelled and
grouped, and what they start at. It is not a saved snapshot of one user's parameter values --
that was the old meaning (format v1, see [Migration](#migration)).

An admin curates presets in the **Preset editor** (`?preset-editor=on`); everyone else just picks
one in the sidebar and fills in the handful of fields it exposes.

## Why

The v2 pipeline (`nsm_data_processing_v2`) loads its settings with
`jsondecode(fileread(settingFile))` and has ~80 leaf parameters. Exposing all of them is unusable,
and hardcoding a curated subset in Python means every pipeline change is a code change. A preset
moves that curation into data.

## File layout

One JSON file per preset, in `$DATA_DIR/_presets/<slug>.json`. The editor writes them at runtime,
so presets survive a redeploy (the data dir is the GCS bucket mount in Cloud Run) and do not
require one to change.

```json
{
  "version": 2,
  "name": "Basic",
  "description": "Everyday scan settings.",
  "updated_at": "2026-07-27T22:41:00+02:00",
  "base": {
    "Acquisition": { "Dx": 0.066, "fileExtension": ".tiff" },
    "Linking":     { "cut_off_distance": 20.0, "minTrackLength": 20.0 }
  },
  "groups": ["Acquisition", "Tracking"],
  "items": [
    {
      "key": "Acquisition.Dx",
      "schema": { "type": "number", "default": 0.066, "step": 0.001, "unit": "um" },
      "ui": { "label": "Pixel size", "group": "Acquisition", "visible": true }
    },
    {
      "key": "Linking.cut_off_distance",
      "schema": { "type": "number", "default": 20.0, "min": 0.0, "step": 1.0, "unit": "px" },
      "ui": { "label": "Cut-off distance", "group": "Tracking", "visible": true }
    }
  ]
}
```

### `base` -- the pass-through settings

A verbatim copy of a pipeline settings file (`Setting_default.json`). It is the starting point for
every job submitted under this preset: the emitted `config.json` is `base` with the preset's item
values written over it.

Anything in `base` that no item covers is passed to MATLAB **unchanged**. This is the fallback
rule that keeps the GUI from breaking when the pipeline grows a parameter: the failure mode is a
setting nobody can edit in the browser, never a job that runs with a missing key.

Copying rather than referencing is deliberate -- the MATLAB submodule is not in the container
image, and an embedded copy makes the preset self-contained and the job reproducible.

### `items` -- the curated parameters

Order in the array is render order. Each item names one leaf of `base` by dotted path.

`schema` holds *semantic* facts, `ui` holds *presentation*. They are separate blocks on purpose:
when the MATLAB team ships a settings schema of their own (the agreed long-term split -- they own
types/ranges/units, we own layout), the `schema` block gets read from there and deleted from this
file without touching anything else.

| `schema` | meaning |
| --- | --- |
| `type` | `number`, `integer`, `bool`, `enum`, or `text` |
| `default` | value the widget starts at, and the value written when `visible` is false |
| `options` | allowed values; required for `enum` |
| `min`, `max`, `step` | numeric bounds, all optional |
| `unit` | appended to the label, display only |

| `ui` | meaning |
| --- | --- |
| `label` | what the user sees; defaults to the last path segment |
| `group` | sidebar expander the item lives in |
| `visible` | false hides the widget but still writes `default` into the config |
| `help` | tooltip |

Only scalars are editable. Lists and any leaf whose type cannot be inferred stay in `base` and
pass through untouched.

A hidden item (`visible: false`) is how an admin pins a value: users cannot change it, but the
preset states it explicitly instead of relying on whatever `base` happened to hold.

### `groups`

Order of the sidebar expanders. Any group named by an item but missing here is appended at the
end, so a hand-edited file cannot lose parameters. Declared groups are kept even when empty --
that is how the editor offers an empty drop target -- and the sidebar skips any group with nothing
visible in it.

In the editor each group has a name box (renaming it moves every parameter in it; renaming onto an
existing name merges the two) and up/down buttons for its position. **Add group** appends an empty
one to drag parameters into.

Parameters derived from a settings file are grouped by the section they sit in. A leaf at the top
level has no section to name it and goes to `General`, so a flat settings file does not end up with
one expander per parameter.

### Identity

`id` is the filename stem and never changes; `name` is display-only and can be edited freely.
Renaming therefore updates a preset in place instead of orphaning the old file.

## Preview

The editor renders the draft into the real sidebar, so the effect of a change is visible while
making it. Its widgets are keyed on a revision counter that every edit bumps -- without that, a
parameter whose type just changed would land on a widget still holding the previous type's value.

## Widget state

Sidebar widget keys are namespaced `p:<id>:<updated_at>:<item key>`. The `id` keeps two presets
that expose the same parameter from bleeding into each other; `updated_at` means republishing a
preset invalidates the old keys, so a user with a live session picks up a changed default instead
of silently keeping the stale one.

## Bootstrap

An empty `_presets/` directory would leave the sidebar with nothing to render and no way to submit
a job, so first run seeds a preset from the bundled base settings in `streamlit/base_settings/`
(copies of the pipeline's `Setting_default*.json`, since the MATLAB submodule is not in the image).

## Emitting a job config

```
config = deepcopy(preset.base)
for item in preset.items:
    set_path(config, item.key, widget_value if item.ui.visible else item.schema.default)
```

The result is a full settings document in the pipeline's own vocabulary, written to the job dir as
`config.json` and persisted with the job for reproducibility.

## Authoring against the deployed pipeline

**New preset** can start from a bundled base settings file, another preset, or **a completed job's
`config.json`** -- the settings that job actually ran with. The last one matters while the pipeline
is mid-migration: the bundled base settings are `nsm_data_processing_v2`'s, but the compiled
`AnalyzeExperimentApp` in the image still reads the old parameter names (`kymographPreprocessing`,
`maxNegativeGab`), so a preset built on the bundled base will not drive it correctly. Seeding from
a job that ran successfully gives a preset in whatever vocabulary the deployed build speaks.

Nothing in the code assumes either vocabulary: an item names a dotted path into its own `base`, so
the same editor serves both pipelines, and swapping the bundled base settings is all the v2
cutover needs on this side.

## Migration

Format v1 was `{"name": ..., "config": {...}}` -- a value snapshot against the *old* pipeline's
parameter names (`kymographPreprocessing`, `maxNegativeGab`, ...). Such files are converted on
read: the old `config` becomes `base`, every leaf becomes a visible item with its type inferred
and its top-level section as the group. Nothing is written back until the preset is published from
the editor, so a v1 file stays readable until someone touches it.

A converted v1 preset still speaks the old pipeline's vocabulary. It keeps working with the old
compiled app; it will not carry over to `nsm_data_processing_v2`, which wants a preset built on a
v2 `base`.
