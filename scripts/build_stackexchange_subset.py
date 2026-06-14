"""Build a small Stack Exchange subset for NLP debugging."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from nlp_pipeline.stackexchange_extract import extract_debug_subset
from nlp_pipeline.subset_labels import build_subset_labels


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--posts", default="Posts.xml")
    parser.add_argument("--votes", default="Votes.xml")
    parser.add_argument("--output-dir", default="data/subsets/debug_subset")
    parser.add_argument("--target-questions", type=int, default=250)
    parser.add_argument("--post-row-limit", type=int, default=300000)
    parser.add_argument("--vote-row-limit", type=int, default=300000)
    parser.add_argument("--post-row-offset", type=int, default=0)
    parser.add_argument("--vote-row-offset", type=int, default=0)
    parser.add_argument(
        "--sampling-strategy",
        choices=["repeated_acceptance", "accepted_snapshot"],
        default="repeated_acceptance",
    )
    args = parser.parse_args()

    extraction = extract_debug_subset(
        posts_xml_path=args.posts,
        votes_xml_path=args.votes,
        output_dir=args.output_dir,
        target_questions=args.target_questions,
        post_row_limit=args.post_row_limit if args.post_row_limit > 0 else None,
        vote_row_limit=args.vote_row_limit if args.vote_row_limit > 0 else None,
        sampling_strategy=args.sampling_strategy,
        post_row_offset=args.post_row_offset,
        vote_row_offset=args.vote_row_offset,
    )
    labels = build_subset_labels(
        answers_csv_path=Path(args.output_dir) / "answers.csv",
        acceptance_votes_csv_path=Path(args.output_dir) / "acceptance_votes.csv",
        output_csv_path=Path(args.output_dir) / "labeled_answers.csv",
    )

    print("Subset extraction complete")
    print(f"Output dir: {extraction['output_dir']}")
    print(f"Sampling strategy: {extraction['sampling_strategy']}")
    print(f"Post row offset: {extraction['post_row_offset']}")
    print(f"Vote row offset: {extraction['vote_row_offset']}")
    print(f"Sampled questions: {extraction['sampled_questions']}")
    print(f"Sampled answers: {extraction['sampled_answers']}")
    print(f"Acceptance votes: {extraction['acceptance_votes']}")
    print(f"Labeled rows: {labels['labeled_rows']}")


if __name__ == "__main__":
    main()
