# Comment NLP Workflow

## Immediate objective

Detect comments that provide evidence that a Stack Overflow answer became
outdated because the underlying technology changed.

This is narrower than general sentiment analysis. A negative comment is not
automatically evidence of temporal obsolescence.

## Database meaning

The `Comments.hl_IndicatedDeprecation` column has the following meaning:

- `NULL`: the comment has not been classified
- `0`: no temporal-obsolescence indication was predicted
- `1`: the comment was predicted to indicate temporal obsolescence

These must be classifier predictions, not direct keyword-rule results.

Install the runtime dependencies in the project environment before running the
database workflow:

```bash
venv/bin/pip install -r requirements.txt
```

## Bootstrap without human labels

When reviewed labels are not yet available, run:

```bash
venv/bin/python scripts/bootstrap_comment_nlp.py
```

This performs weak supervision:

- narrow, explicit version/deprecation phrases provide provisional positives
- explicit freshness and original-incorrectness phrases provide provisional
  negatives
- a random unlabeled sample is treated as low-weight background
- ambiguous phrases such as "doesn't work on my server" are left unlabeled

It creates:

- `bootstrap_training_seeds.csv`
- `bootstrap_comment_classifier.joblib`
- `bootstrap_scores.csv`
- `bootstrap_review_queue.csv`
- `bootstrap_metadata.json`

The review queue prioritizes high scores, uncertain examples, and comments that
the model ranked highly even though the rules abstained. These outputs are a
basis for later annotation and active learning.

Bootstrap scores are not evaluated probabilities or ground-truth labels. The
bootstrap model must not update `hl_IndicatedDeprecation`.

## Prepare data from MySQL

After database ingress, run:

```bash
python3 scripts/prepare_comment_nlp_from_db.py
```

This reads comments whose prediction value is still `NULL` and creates the
candidate and annotation files.

## Offline SQL fallback

Run:

```bash
python3 scripts/prepare_comment_nlp.py
```

This reads `Comments.sql` and writes:

- `data/processed/comment_nlp/comments.csv`: all parsed comments
- `data/processed/comment_nlp/candidate_comments.csv`: comments selected by
  high-recall review rules
- `data/processed/comment_nlp/annotation_sample.csv`: a balanced manual-review
  sample
- `data/processed/comment_nlp/summary.json`: parsing and candidate counts

The candidate rules are sampling aids, not training labels.

Use `--skip-all-comments` when only the smaller candidate and annotation files
are needed.

## Manual labels

Fill `human_label` in `annotation_sample.csv` with one of:

- `temporal_obsolescence`: the comment says the answer became outdated because
  an API, version, platform, syntax, or recommended practice changed
- `freshness_confirmation`: the comment explicitly says the answer still works
  or remains supported
- `incorrectness`: the answer was wrong independently of technological change
- `situational_failure`: it failed for one environment or user without enough
  evidence of temporal change
- `neutral`: none of the above

Examples:

- "This method was removed in version 4." -> `temporal_obsolescence`
- "Still works in Python 3.13." -> `freshness_confirmation`
- "This is incorrect; the result should be 5." -> `incorrectness`
- "It doesn't work on my server." -> `situational_failure`

Do not infer obsolescence from age, comment score, or negative tone alone.

## Evaluate the first baseline

After annotating enough rows, run:

```bash
python3 scripts/evaluate_comment_classifier.py
```

The baseline uses word and character TF-IDF with balanced logistic regression.
Cross-validation keeps comments attached to the same `post_id` in one fold.

For a meaningful first evaluation, aim for:

- at least 100 manually verified temporal-obsolescence comments
- at least 300 verified negative comments across the other categories
- preferably two annotators for a shared subset of 100 comments

## Train the classifier

After reviewing the evaluation results, train on all reviewed rows:

```bash
python3 scripts/train_comment_classifier.py
```

This writes the model and training metadata under
`data/processed/comment_nlp/`. Training cannot proceed while the annotation
labels are empty.

## Predict database values

First run a small database dry run:

```bash
python3 scripts/predict_comments_to_db.py --limit 1000
```

No values are written without `--apply`. After checking the evaluation and the
dry-run positive rate, classify all remaining comments with:

```bash
python3 scripts/predict_comments_to_db.py --apply
```

The update query includes `WHERE hl_IndicatedDeprecation IS NULL`, so existing
values are not overwritten. The default probability threshold is `0.5`; use
`--threshold` only after validating a different threshold.

## Later analysis

The complete paper analysis also uses:

- whether each `PostId` is an answer
- answer creation date
- answer-to-question `ParentId`
- question tags
- accepted-answer status or acceptance timestamp

The database ingress now provides these post and tag relationships. Historical
acceptance replacement may still not be fully reconstructable from the dump.
