"""Comment-level NLP helpers for rule-based candidate extraction and Ollama review."""

from .comment_ollama_labeling import label_comment_annotations_with_ollama

__all__ = ["label_comment_annotations_with_ollama"]
