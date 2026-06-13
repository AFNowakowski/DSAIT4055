# NLP Scaffold for Answer Deprecation Analysis

This repository now contains a starter scaffold for the NLP portion of the project.

## Recommended workflow

Use the notebook for exploration and visualization, but keep the core logic in Python modules inside `src/`. That gives you:

- reproducible preprocessing and feature extraction
- easier collaboration with teammates
- cleaner handoff from NLP detection to survival analysis

## Project layout

- `notebooks/01_nlp_exploration.ipynb`: starter notebook
- `src/nlp_pipeline/`: reusable NLP and survival-analysis code
- `data/`: raw and processed datasets
- `docs/implementation_notes.md`: project-specific implementation guidance

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
py -3 scripts/run_nlp_demo.py
```

This trains a simple TF-IDF + logistic regression classifier on a tiny demo dataset so the pipeline is callable before the real data arrives.
