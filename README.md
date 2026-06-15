# NLP Scaffold for Answer Deprecation Analysis

This repository now contains a starter scaffold for the NLP portion of the project.

Database setup and XML ingress are documented in
`docs/database_ingress_workflow.md`.

## Recommended workflow

Use the notebook for exploration and visualization, but keep the core logic in Python modules inside `src/`. That gives you:

- reproducible preprocessing and feature extraction
- easier collaboration with teammates
- cleaner handoff from NLP detection to survival analysis

## Project layout

- `notebooks/01_nlp_exploration.ipynb`: starter notebook
- `src/nlp_pipeline/`: active comment-level NLP workflow
- `src/nlp_pipeline/legacy_answer/`: older answer-level experiments kept for reference
- `data/`: raw and processed datasets
- `docs/implementation_notes.md`: project-specific implementation guidance
- `docs/labeling_workflow.md`: explanation of accepted answers, weak labels, and Ollama labels

## Initial pipeline idea

1. Load question-answer history and accepted-answer events.
2. Build labels for "accepted answer became deprecated".
3. Extract text and metadata features from answers.
4. Train or tune a simple detector for likely deprecation.
5. Convert accepted answers into survival records.
6. Estimate half-life with Kaplan-Meier survival analysis.

## Suggested next step

Place the dataset in `data/raw/` and start by implementing the event-construction step carefully. The survival analysis quality will depend on how well "deprecation" is defined.

## Quick demo

You can smoke-test the NLP baseline on synthetic data with:

```powershell
py -3 scripts/legacy_answer_nlp/run_nlp_demo.py
```

This trains a simple TF-IDF + logistic regression classifier on a tiny demo dataset so the pipeline is callable before the real data arrives.

## Stack Exchange debug subset

To avoid debugging on the full XML dump, build a small subset first:

```powershell
py -3 scripts/legacy_answer_nlp/build_stackexchange_subset.py --target-questions 250 --post-row-limit 300000 --vote-row-limit 300000
```

A more practical debug run for this dataset is:

```powershell
py -3 scripts/legacy_answer_nlp/build_stackexchange_subset.py --target-questions 500 --post-row-limit 2000000 --vote-row-limit 2000000
```

This writes:

- `data/subsets/debug_subset/questions.csv`
- `data/subsets/debug_subset/answers.csv`
- `data/subsets/debug_subset/acceptance_votes.csv`
- `data/subsets/debug_subset/labeled_answers.csv`

The label rule is:

- `is_deprecated = 1` if an accepted answer is later replaced by another accepted answer on the same question
- `is_deprecated = 0` otherwise

The row limits are intentional for debugging. Once the logic looks correct on the subset, increase them gradually or remove them for a fuller extraction.

## Weak-label subset

The answer-level scripts below are now grouped under `scripts/legacy_answer_nlp/`
to keep the active comment workflow easier to navigate.

Because this dump does not appear to contain full accepted-answer replacement history, the practical NLP path is a weakly supervised subset based on:

- current accepted answers as negative examples
- older sibling answers as likely superseded positives
- stronger positive cues from comments like `deprecated` or `outdated`

Build it with:

```powershell
py -3 scripts/legacy_answer_nlp/build_weak_label_subset.py --target-questions 500 --post-row-limit 2000000 --comment-row-limit 2000000 --min-gap-days 0
```

This writes:

- `data/subsets/weak_label_subset/questions.csv`
- `data/subsets/weak_label_subset/answers.csv`
- `data/subsets/weak_label_subset/comments.csv`
- `data/subsets/weak_label_subset/weak_labeled_answers.csv`

See [docs/labeling_workflow.md](C:/Users/anton/Desktop/DELFT/Year-1-Q4/web_science/DSAIT4055/docs/labeling_workflow.md) for an explanation of what `is_accepted_snapshot`, `weak_label`, and `ollama_label` mean.

## Ollama Labels

If you have Ollama locally, you can add semantic labels on top of the weak-label subset:

```powershell
py -3 scripts/legacy_answer_nlp/label_with_ollama.py --model llama3.1:8b --limit 25
```

This reads `data/subsets/weak_label_subset/weak_labeled_answers.csv` and writes:

- `data/subsets/weak_label_subset/ollama_labels.csv`

Recommended use:

- start with `--limit 25`
- label mostly unaccepted answers first
- compare `ollama_label` against `heuristic_label`
- then decide whether to use Ollama labels as:
  - a review layer
  - additional training labels
  - or extra features for the baseline model

For larger runs, the script is resume-safe:

- it reuses existing rows already written to `ollama_labels.csv`
- it skips rows that are already labeled
- it appends new labels by rewriting the CSV with prior rows preserved

Example chunked workflow:

```powershell
py -3 scripts/legacy_answer_nlp/label_with_ollama.py --model qwen3.5:9b --limit 100 --ollama-host http://127.0.0.1:11434 --verbose --include-accepted
```

Run the same command again later to label the next chunk instead of starting over.

## Merge Labels

To create one training file with a single `final_label` column:

```powershell
py -3 scripts/legacy_answer_nlp/merge_training_labels.py
```

This writes:

- `data/subsets/weak_label_subset/training_labels.csv`

Current merge rule:

- use `ollama_label` when available
- otherwise fall back to `weak_label`

## Cross-Validation

To evaluate the merged dataset with cross-validation instead of a single split:

```powershell
py -3 scripts/legacy_answer_nlp/evaluate_training_labels_cv.py --folds 5
```

This reads:

- `data/subsets/weak_label_subset/training_labels.csv`

and reports fold-by-fold metrics plus mean accuracy, precision, recall, and F1.

## Error Analysis

To inspect example false positives and false negatives from cross-validation:

```powershell
py -3 scripts/legacy_answer_nlp/analyze_training_errors.py --folds 5 --show 5
```

## Comment-level NLP without Ollama

The current `Comments.sql` export has 410,621 comments but no populated human
labels. Prepare it for local NLP and manual annotation with:

```bash
python3 scripts/prepare_comment_nlp.py
```

The main review file is:

- `data/processed/comment_nlp/annotation_sample.csv`

Fill its `human_label` column using the categories documented in
`docs/comment_nlp_workflow.md`. Then evaluate a local TF-IDF + logistic
regression baseline:

```bash
python3 scripts/evaluate_comment_classifier.py
```

This comment classifier is the recommended primary NLP component for the
paper. The earlier answer-level weak-label and Ollama workflow remains
experimental and should not be treated as ground truth.

For the database-first workflow:

```bash
python3 scripts/prepare_comment_nlp_from_db.py
python3 scripts/evaluate_comment_classifier.py
python3 scripts/train_comment_classifier.py
python3 scripts/predict_comments_to_db.py --limit 1000
python3 scripts/predict_comments_to_db.py --apply
```

The final command updates only rows where
`hl_IndicatedDeprecation IS NULL`. Review
`docs/comment_nlp_workflow.md` before applying predictions.

For an offline workflow that does not require MySQL ingress:

```bash
python3 scripts/label_comment_annotations_with_ollama.py --model qwen3.5:9b --input-csv data/processed/comment_nlp/annotation_sample.csv --limit 800 --output-csv data/processed/comment_nlp/annotation_sample_ollama.csv
python3 scripts/evaluate_comment_classifier.py --annotations data/processed/comment_nlp/annotation_sample_ollama.csv --label-column ollama_label
python3 scripts/train_comment_classifier.py --annotations data/processed/comment_nlp/annotation_sample_ollama.csv --label-column ollama_label
python3 scripts/predict_comments_offline.py --input-sql Comments.sql --output-csv data/processed/comment_nlp/comments_predictions.csv
python3 scripts/fill_comment_sql_labels.py --input-sql Comments.sql --output-sql data/processed/comment_nlp/Comments_labeled.sql
```

This path is useful when you want to validate the NLP model locally and
produce a labeled `Comments.sql` export before the full dump is ingressed.

To compare multiple lightweight classifiers on the same labeled file:

```bash
python3 scripts/compare_comment_classifiers.py --annotations data/processed/comment_nlp/annotation_sample_ollama.csv --label-column ollama_label
```

While human labels are unavailable, build a provisional ranking model with:

```bash
venv/bin/python scripts/bootstrap_comment_nlp.py
```

This produces weak-supervision seeds, scores, and an active-learning review
queue. It intentionally does not update the database prediction column.
