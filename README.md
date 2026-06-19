# DSAIT4055 Project

This repository contains the code and data workflow for the DSAIT4055 Web
Science and Engineering project based on Stack Overflow data.

The project combines:

- data ingestion from the Stack Exchange dump into a local MySQL database
- comment-level NLP for detecting answer obsolescence signals
- analysis code and supporting scripts for the downstream study

The current NLP workflow focuses on comments that indicate temporal
obsolescence, such as deprecation, removed APIs, outdated syntax, and version
incompatibilities.

Project documentation:

- `docs/database_ingress_workflow.md`
- `docs/comment_nlp_workflow.md`
