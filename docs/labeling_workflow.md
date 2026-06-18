# Labeling Workflow

## The core problem

We want to detect answers that are likely outdated or superseded.

The Stack Exchange dump gives us:

- questions
- answers
- comments
- the **current** accepted answer snapshot

What it does **not** clearly give us is a full historical record of accepted-answer replacements that we can safely use as ground truth for deprecation.

Because of that, we use a staged labeling workflow.

## Accepted Answer

An **accepted answer** is the answer the question author marked as the current best answer.

In our extracted data:

- `is_accepted_snapshot = 1` means this answer is the currently accepted answer in the dump
- `is_accepted_snapshot = 0` means it is not the currently accepted answer

Why this matters:

- accepted answers are often a reasonable starting point for "probably still valid"
- non-accepted answers are candidates for "maybe outdated" or "maybe superseded"

This is only a heuristic. An accepted answer is not automatically correct forever.

## Heuristic Label

A **heuristic label** is a rough label made by simple rules, not by a human and not by a trained model.

In this project, the heuristic label is built from signals like:

- whether an answer is the current accepted answer
- whether it is an older sibling answer for the same question
- whether comments contain words like `deprecated`, `outdated`, or `obsolete`

Why this exists:

- we need labels before we can train anything
- the raw dataset does not directly contain a perfect `outdated = yes/no` field
- heuristics are fast and cheap

Weakness:

- heuristic labels are noisy
- they can be wrong

## Weak Label

A **weak label** is a label that is useful but not guaranteed to be true.

In our pipeline, the current `weak_label` column is a type of heuristic label.

Typical meaning:

- `weak_label = 0`: likely still valid
- `weak_label = 1`: likely outdated or superseded

Why it is called "weak":

- it is only a proxy for the real concept we care about
- it comes from rules, not from direct ground truth

## Ollama Label

An **Ollama label** is a label produced by a local LLM.

The model reads the question and answer text and returns:

- `ollama_label`
- `ollama_confidence`
- `ollama_reason`
- `ollama_explanation`

Why this helps:

- the LLM can understand meaning better than a simple rule
- it can notice old technologies, legacy advice, or obsolete APIs

Weakness:

- LLM labels are still not perfect ground truth
- they can be inconsistent or overly confident

## Why we have more than one label

We currently have multiple label types because they serve different purposes:

- `is_accepted_snapshot`: structural signal from the dataset
- `weak_label`: fast rule-based guess
- `ollama_label`: semantic judgment from the LLM

This is intentional.

We do not want to trust only one noisy source too early.

## Recommended interpretation

Think of the columns like this:

- `is_accepted_snapshot`
  Meaning: "Is this the currently accepted answer?"

- `weak_label`
  Meaning: "What do our simple rules think?"

- `ollama_label`
  Meaning: "What does the LLM think after reading the text?"

## Recommended next training label

For model training, we should eventually create one final column, for example:

- `final_label`

Simple rule for that column:

1. If an `ollama_label` exists, use it.
2. Otherwise, fall back to `weak_label`.

Why:

- the LLM is usually smarter than the rule
- the weak label is still useful when no LLM label is available

## Current pipeline

1. Extract a bounded subset from the large XML dump.
2. Build heuristic / weak labels.
3. Run Ollama on selected rows.
4. Merge labels into a final training dataset.
5. Train a smaller classifier on that dataset.

## Why we do not train directly on accepted answers

Because "accepted" and "not accepted" are not the same as "current" and "outdated".

Examples:

- an accepted answer can later become outdated
- a non-accepted answer can still be technically correct

So accepted status is only one signal, not the final truth.
