# Comment Obsolescence NLP Pipeline

This project detects Stack Overflow comments that indicate an answer has become
outdated over time.

The workflow is comment-level and focused on temporal obsolescence, such as
deprecation, removed APIs, version incompatibilities, outdated syntax, and
replaced practices.

In practice, the pipeline:

- extracts likely candidate comments with rule-based patterns
- verifies those candidates with a local Ollama model
- writes `0/1` obsolescence labels back into SQL or the database

More detail is documented in:

- `docs/comment_nlp_workflow.md`
- `docs/database_ingress_workflow.md`
