# Comment Obsolescence NLP Pipeline

This repository contains the final NLP workflow used to label Stack Overflow
comments for temporal answer obsolescence.

The active pipeline is intentionally simple:

1. parse a `Comments.sql` export
2. use high-recall keyword and pattern rules to extract candidate comments
3. optionally narrow the candidates further by category
4. verify candidate comments with a local Ollama model
5. write `0/1` labels back into a new SQL file through
   `hl_IndicatedDeprecation`

The pipeline targets temporal obsolescence only. A negative comment is not
automatically a positive label.

Database setup and XML ingress remain documented in
`docs/database_ingress_workflow.md`, but the NLP workflow itself can run
entirely from a SQL export.

## Project Layout

- `src/nlp_pipeline/comment_nlp.py`: SQL parsing and rule-based candidate extraction
- `src/nlp_pipeline/comment_ollama_labeling.py`: Ollama labeling for candidate comments
- `src/nlp_pipeline/ollama_utils.py`: shared local Ollama HTTP/CLI helpers
- `scripts/prepare_comment_nlp.py`: build candidate and annotation CSV files from a SQL dump
- `scripts/filter_comment_candidates.py`: keep only selected candidate categories or reasons
- `scripts/label_comment_annotations_with_ollama.py`: label candidate comments with Ollama
- `scripts/fill_comment_sql_heuristic_labels.py`: write a heuristic-only `0/1` SQL export
- `scripts/fill_comment_sql_from_ollama_labels.py`: write a `0/1` SQL export from Ollama labels
- `docs/comment_nlp_workflow.md`: end-to-end comment NLP workflow

## Recommended Workflow

Prepare candidate comments from a SQL export:

```powershell
venv\Scripts\python.exe scripts\prepare_comment_nlp.py --input-sql Comments.sql --output-dir data/processed/comment_nlp --skip-all-comments
```

This writes:

- `candidate_comments.csv`
- `annotation_sample.csv`
- `summary.json`

If you only want temporal candidates, filter them:

```powershell
venv\Scripts\python.exe scripts\filter_comment_candidates.py --input-csv data/processed/comment_nlp/candidate_comments.csv --output-csv data/processed/comment_nlp/candidate_comments_temporal_only.csv --candidate-category temporal_candidate
```

Label those candidates with Ollama:

```powershell
venv\Scripts\python.exe scripts\label_comment_annotations_with_ollama.py --model qwen3.5:9b --input-csv data/processed/comment_nlp/candidate_comments_temporal_only.csv --limit 2000 --ollama-host http://127.0.0.1:11434 --verbose --output-csv data/processed/comment_nlp/candidate_comments_temporal_only_ollama.csv
```

Write the final SQL labels from the Ollama output:

```powershell
venv\Scripts\python.exe scripts\fill_comment_sql_from_ollama_labels.py --input-sql Comments.sql --labels-csv data/processed/comment_nlp/candidate_comments_temporal_only_ollama.csv --output-sql data/processed/comment_nlp/Comments_ollama_labeled.sql
```

Rows labeled by Ollama as `temporal_obsolescence` are written as `1`. All other
rows are written as `0`.

## Heuristic-Only Fallback

If you want a pure rule-based output without Ollama verification:

```powershell
venv\Scripts\python.exe scripts\fill_comment_sql_heuristic_labels.py --input-sql Comments.sql --output-sql data/processed/comment_nlp/Comments_heuristic_labeled.sql
```

This writes `1` for comments whose rule-based category is
`temporal_candidate`, and `0` otherwise.
