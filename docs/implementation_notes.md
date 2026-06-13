# Implementation Notes

## What the teammate message implies

The message suggests using one of the following as the event definition:

- another answer overtakes the current accepted answer
- another agreed replacement indicator defined by the team

Once that event is defined, the team wants to estimate the **half-life** of accepted answers using a Kaplan-Meier estimator. In practice:

- each accepted answer enters the study at the time it became accepted
- the event happens when it is considered deprecated
- if it is still accepted at the end of the observation window, it is right-censored

## Recommended scope for the NLP component

Keep the NLP detector simple at first. The goal is not a large language model pipeline. The goal is a reliable, explainable feature generator that helps identify answer replacement or obsolescence.

Good starting features:

- answer text length
- presence of version numbers, dates, or years
- code block count
- URLs and external references
- lexical overlap with newer competing answers
- semantic similarity between question and answer
- age of the answer at each observation point

## Practical implementation plan

### 1. Define the event label

Create a function that marks an accepted answer as deprecated when:

- a different answer becomes accepted later for the same question

This is the cleanest first definition because it is observable and low-ambiguity.

### 2. Build the survival table

For each accepted answer, store:

- `question_id`
- `answer_id`
- `accepted_at`
- `event_at`
- `duration_days`
- `event_observed`

### 3. Add NLP features

Compute features from the answer text and optionally relative features versus newer answers on the same question.

### 4. Run Kaplan-Meier

Fit a Kaplan-Meier curve on `duration_days` with `event_observed`.

The half-life is the first time where the survival probability drops to `<= 0.5`.

## Suggested team split

- You: event construction, text preprocessing, feature engineering, survival input table
- Others: broader analysis, visualization, reporting, or data acquisition

## Recommendation on notebooks

Yes, you should have a notebook, but only as a thin exploration layer. It is efficient for:

- inspecting distributions
- testing features
- plotting Kaplan-Meier curves

It is not efficient if the full pipeline lives only in notebook cells. Keep logic in `src/` and import it into the notebook.
