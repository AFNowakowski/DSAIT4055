# DSAIT4055 Project

This repository contains the code and data workflow for the DSAIT4055 Web
Science and Engineering project based on Stack Overflow data.

The project combines:

- data ingestion from the Stack Exchange dump into a local MySQL database
- comment-level NLP for detecting answer obsolescence signals
- survival analysis on comment buckets

The current NLP workflow focuses on comments that indicate temporal
obsolescence, such as deprecation, removed APIs, outdated syntax, and version
incompatibilities.

Project documentation:

- `docs/database_ingress_workflow.md`
- `docs/comment_nlp_workflow.md`
- `docs/comment_survival_workflow.md`

## Database-first workflow

```bash
python3 scripts/prepare_comment_nlp_from_db.py
python3 scripts/train_comment_classifier.py
python3 scripts/predict_comments_to_db.py --apply
```

## Offline workflow (no MySQL)

```bash
python3 scripts/label_comment_annotations_with_ollama.py --model qwen3.5:9b --input-csv data/processed/comment_nlp/annotation_sample.csv --limit 800 --output-csv data/processed/comment_nlp/annotation_sample_ollama.csv
python3 scripts/train_comment_classifier.py --annotations data/processed/comment_nlp/annotation_sample_ollama.csv --label-column ollama_label
python3 scripts/predict_comments_offline.py --input-sql Comments.sql --output-csv data/processed/comment_nlp/comments_predictions.csv
```

## Survival analysis

```bash
python3 scripts/parquet_survival.py
python3 scripts/plot_survival.py
```
