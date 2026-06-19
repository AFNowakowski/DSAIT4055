# Comment NLP Workflow

## Objective

Detect comments that indicate a Stack Overflow answer became outdated because
the underlying technology changed over time.

This pipeline targets temporal obsolescence only. We do not treat generic
negativity, correctness disputes, or isolated user failures as positive labels
unless the comment explicitly ties the problem to a change in version, API,
syntax, platform, or recommended practice.

## Database Meaning

The `Comments.hl_IndicatedDeprecation` column has the following meaning:

- `0`: no temporal-obsolescence indication
- `1`: temporal-obsolescence indication

In the final workflow, these values are produced from the rule-based candidate
filter plus Ollama verification.

## Stage 1: Prepare Candidate Comments

Run:

```powershell
venv\Scripts\python.exe scripts\prepare_comment_nlp.py --input-sql Comments.sql --output-dir data/processed/comment_nlp --skip-all-comments
```

This parses `Comments.sql` and writes:

- `candidate_comments.csv`: comments selected by the high-recall rules
- `annotation_sample.csv`: a balanced review sample across candidate categories
- `summary.json`: parsing counts and category totals

The selection rules live in `src/nlp_pipeline/comment_nlp.py`. They include:

- explicit deprecation words such as `deprecated`, `outdated`, and `obsolete`
- `no longer works` patterns
- removed API phrases
- version replacement and version cutoff patterns
- syntax and best-practice replacement patterns

These rules are intentionally high recall. A candidate is not yet a final
positive label.

## Stage 2: Narrow to the Temporal Subset

If you want to review only the temporal candidates:

```powershell
venv\Scripts\python.exe scripts\filter_comment_candidates.py --input-csv data/processed/comment_nlp/candidate_comments.csv --output-csv data/processed/comment_nlp/candidate_comments_temporal_only.csv --candidate-category temporal_candidate
```

This keeps only rows where `candidate_category == temporal_candidate`.

## Stage 3: Verify Candidates with Ollama

Run a local Ollama model over the candidate CSV:

```powershell
venv\Scripts\python.exe scripts\label_comment_annotations_with_ollama.py --model qwen3.5:9b --input-csv data/processed/comment_nlp/candidate_comments_temporal_only.csv --limit 2000 --ollama-host http://127.0.0.1:11434 --verbose --output-csv data/processed/comment_nlp/candidate_comments_temporal_only_ollama.csv
```

The labeling prompt asks the model to assign one of:

- `temporal_obsolescence`
- `freshness_confirmation`
- `incorrectness`
- `situational_failure`
- `neutral`

The script is resume-safe:

- it reuses rows already written to the output CSV
- it skips rows already present in the output file
- rerunning the same command continues where the previous run stopped

## Stage 4: Write Final SQL Labels

To create a new SQL file where only Ollama-confirmed temporal comments receive
`1`:

```powershell
venv\Scripts\python.exe scripts\fill_comment_sql_from_ollama_labels.py --input-sql Comments.sql --labels-csv data/processed/comment_nlp/candidate_comments_temporal_only_ollama.csv --output-sql data/processed/comment_nlp/Comments_ollama_labeled.sql
```

This maps:

- `ollama_label == temporal_obsolescence` -> `1`
- every other row -> `0`

The output is a full SQL export with `hl_IndicatedDeprecation` populated for
every comment.

## Heuristic-Only SQL Output

If you want a quick baseline without Ollama verification:

```powershell
venv\Scripts\python.exe scripts\fill_comment_sql_heuristic_labels.py --input-sql Comments.sql --output-sql data/processed/comment_nlp/Comments_heuristic_labeled.sql
```

This writes:

- `1` when the rule-based candidate category is `temporal_candidate`
- `0` otherwise

## Notes

- `annotation_sample.csv` is useful for manual inspection, but the final paper
  workflow does not require a trained classifier.
- The final active NLP workflow is comment-level only.
- Older answer-level experiments and classifier-training utilities were removed
  to keep the repository aligned with the final paper methodology.
