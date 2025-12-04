"""Utility modules for Rake Service

Provides common utilities for retry logic, text processing, and more.
"""

from utils.retry import (
    retry_with_backoff,
    retry_sync_with_backoff,
    RetryableOperation
)

from utils.text_processing import (
    clean_text,
    remove_html_tags,
    normalize_whitespace,
    get_text_stats,
    truncate_text,
    remove_duplicate_lines,
    extract_sentences,
    is_mostly_ascii,
    sanitize_filename
)

__all__ = [
    # Retry utilities
    "retry_with_backoff",
    "retry_sync_with_backoff",
    "RetryableOperation",

    # Text processing
    "clean_text",
    "remove_html_tags",
    "normalize_whitespace",
    "get_text_stats",
    "truncate_text",
    "remove_duplicate_lines",
    "extract_sentences",
    "is_mostly_ascii",
    "sanitize_filename",
]
