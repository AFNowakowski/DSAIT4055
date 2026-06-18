Shared retraining artifacts for the comment-obsolescence workflow.

Files:
- `candidate_comments_focus6000_ollama_qwen.csv`: the main weakly labeled training set used for the final classifier
- `annotation_sample_ollama_qwen_filtered.csv`: the cleaned 800-row evaluation/reference set
- `comment_classifier_focus6000_metadata.json`: metadata for the final trained logistic-regression model

These files are intended for reproducibility and retraining without requiring
the full local `data/processed/` workspace.
