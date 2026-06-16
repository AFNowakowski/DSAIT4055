# Comment Survival Table (Ephemeral vs. Stable)

New: `scripts/build_comment_survival_table.py` builds a survival table from
the already-classified `Comments.hl_IndicatedDeprecation` column, then
compares half-lives between ephemeral tags (angular, react-native, angularjs,
webpack, npm) and stable tags (c, algorithm, math, regex, dynamic-programming).

Run it against the populated MySQL database:

```bash
python3 scripts/build_comment_survival_table.py
```

It prints an event-rate sanity check, then the per-bucket half-life and a
log-rank test p-value.

Also fixed a broken import in `comment_ollama_labeling.py` that was causing
all existing tests to fail.
