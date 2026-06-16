"""Build a weakly supervised Stack Exchange NLP subset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.legacy_answer.weak_label_subset import (
    build_weak_labels,
    extract_weak_label_subset,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--posts", default="Posts.xml")
    parser.add_argument("--comments", default="Comments.xml")
    parser.add_argument("--output-dir", default="data/subsets/weak_label_subset")
    parser.add_argument("--target-questions", type=int, default=500)
    parser.add_argument("--post-row-limit", type=int, default=2_000_000)
    parser.add_argument("--comment-row-limit", type=int, default=2_000_000)
    parser.add_argument("--post-row-offset", type=int, default=0)
    parser.add_argument("--comment-row-offset", type=int, default=0)
    parser.add_argument("--min-answer-count", type=int, default=2)
    parser.add_argument("--min-gap-days", type=float, default=0.0)
    args = parser.parse_args()

    extraction = extract_weak_label_subset(
        posts_xml_path=args.posts,
        comments_xml_path=args.comments,
        output_dir=args.output_dir,
        target_questions=args.target_questions,
        post_row_limit=args.post_row_limit if args.post_row_limit > 0 else None,
        comment_row_limit=args.comment_row_limit if args.comment_row_limit > 0 else None,
        post_row_offset=args.post_row_offset,
        comment_row_offset=args.comment_row_offset,
        min_answer_count=args.min_answer_count,
    )
    labels = build_weak_labels(
        questions_csv_path=Path(args.output_dir) / "questions.csv",
        answers_csv_path=Path(args.output_dir) / "answers.csv",
        comments_csv_path=Path(args.output_dir) / "comments.csv",
        output_csv_path=Path(args.output_dir) / "weak_labeled_answers.csv",
        min_gap_days=args.min_gap_days,
    )

    print("Weak-label subset extraction complete")
    print(f"Output dir: {extraction['output_dir']}")
    print(f"Sampled questions: {extraction['sampled_questions']}")
    print(f"Sampled answers: {extraction['sampled_answers']}")
    print(f"Sampled comments: {extraction['sampled_comments']}")
    print(f"Labeled rows: {labels['labeled_rows']}")
    print(f"Positive labels: {labels['positive_labels']}")
    print(f"Negative labels: {labels['negative_labels']}")
    print(f"Skipped rows: {labels['skipped_rows']}")


if __name__ == "__main__":
    main()
