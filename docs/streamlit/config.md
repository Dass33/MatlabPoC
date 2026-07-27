# Parameter Sidebar

The sidebar holds the algorithm parameters a job runs with. It has no built-in list of
parameters: the widgets, their labels, grouping and defaults all come from the selected
[preset](presets.md).

Users pick a preset at the top of the sidebar, adjust the fields it exposes, and submit. Everything
the preset does not expose is still sent to MATLAB, unchanged, from the preset's base settings.
**Load settings** re-applies the parameters of an existing settings JSON (a cloned job, a colleague's
export), and **Export current settings** downloads exactly what the next job would run with.

Presets themselves are authored in the [Preset editor](presets.md), not here.

---

## Code Reference

::: config
