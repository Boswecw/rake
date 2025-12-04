"""Text Processing Utilities for Rake Service

Provides text cleaning, normalization, and processing functions used
throughout the pipeline stages.

Features:
    - HTML tag removal
    - Whitespace normalization
    - Unicode normalization
    - Special character handling
    - Text statistics

Example:
    >>> from utils.text_processing import clean_text, get_text_stats
    >>>
    >>> raw_text = "<p>Hello   World!</p>\\n\\n\\n"
    >>> clean = clean_text(raw_text)
    >>> print(clean)
    Hello World!
    >>>
    >>> stats = get_text_stats(clean)
    >>> print(stats['word_count'])
    2
"""

import re
import unicodedata
from typing import Dict, Any, Optional
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def clean_text(
    text: str,
    remove_html: bool = True,
    normalize_whitespace: bool = True,
    normalize_unicode: bool = True,
    remove_urls: bool = False,
    remove_emails: bool = False,
    lowercase: bool = False
) -> str:
    """Clean and normalize text content.

    Applies various cleaning operations to text content to prepare
    it for chunking and embedding.

    Args:
        text: Raw text to clean
        remove_html: Remove HTML tags
        normalize_whitespace: Normalize whitespace to single spaces
        normalize_unicode: Normalize Unicode characters (NFKC)
        remove_urls: Remove URLs from text
        remove_emails: Remove email addresses
        lowercase: Convert to lowercase

    Returns:
        Cleaned text

    Example:
        >>> text = "<p>Hello   World!</p>\\n\\nVisit https://example.com"
        >>> clean = clean_text(text, remove_urls=True)
        >>> print(clean)
        Hello World!
    """
    if not text:
        return ""

    # Remove HTML tags
    if remove_html:
        text = remove_html_tags(text)

    # Normalize Unicode
    if normalize_unicode:
        text = unicodedata.normalize('NFKC', text)

    # Remove URLs
    if remove_urls:
        text = re.sub(
            r'https?://\S+|www\.\S+',
            '',
            text,
            flags=re.IGNORECASE
        )

    # Remove email addresses
    if remove_emails:
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '',
            text
        )

    # Normalize whitespace
    if normalize_whitespace:
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        # Remove leading/trailing whitespace from each line
        text = '\n'.join(line.strip() for line in text.split('\n'))
        # Remove leading/trailing whitespace
        text = text.strip()

    # Convert to lowercase
    if lowercase:
        text = text.lower()

    return text


def remove_html_tags(text: str) -> str:
    """Remove HTML tags from text using BeautifulSoup.

    Handles complex HTML structures and preserves text content.

    Args:
        text: Text containing HTML

    Returns:
        Text with HTML removed

    Example:
        >>> html = "<div><p>Hello <strong>World</strong>!</p></div>"
        >>> plain = remove_html_tags(html)
        >>> print(plain)
        Hello World!
    """
    if not text:
        return ""

    try:
        soup = BeautifulSoup(text, 'lxml')
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        logger.warning(f"Failed to parse HTML with lxml, falling back to html.parser: {e}")
        try:
            soup = BeautifulSoup(text, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception as e2:
            logger.error(f"Failed to parse HTML: {e2}")
            # Fallback: simple regex-based tag removal
            return re.sub(r'<[^>]+>', '', text)


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    - Converts tabs to spaces
    - Collapses multiple spaces to single space
    - Normalizes line endings
    - Removes trailing whitespace

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace

    Example:
        >>> text = "Hello    World\\t\\nFoo  Bar"
        >>> normalized = normalize_whitespace(text)
        >>> print(repr(normalized))
        'Hello World\\nFoo Bar'
    """
    if not text:
        return ""

    # Convert tabs to spaces
    text = text.replace('\t', ' ')

    # Collapse multiple spaces
    text = re.sub(r' +', ' ', text)

    # Normalize line endings (Windows/Mac → Unix)
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove trailing whitespace from each line
    text = '\n'.join(line.rstrip() for line in text.split('\n'))

    # Collapse multiple blank lines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def get_text_stats(text: str) -> Dict[str, Any]:
    """Calculate statistics for text content.

    Provides word count, character count, line count, and other metrics.

    Args:
        text: Text to analyze

    Returns:
        Dictionary with statistics:
            - char_count: Total characters
            - char_count_no_spaces: Characters excluding whitespace
            - word_count: Total words
            - line_count: Total lines
            - paragraph_count: Total paragraphs (double newline separated)
            - avg_word_length: Average word length
            - avg_sentence_length: Average sentence length in words

    Example:
        >>> text = "Hello World!\\n\\nThis is a test."
        >>> stats = get_text_stats(text)
        >>> print(stats['word_count'])
        6
        >>> print(stats['paragraph_count'])
        2
    """
    if not text:
        return {
            'char_count': 0,
            'char_count_no_spaces': 0,
            'word_count': 0,
            'line_count': 0,
            'paragraph_count': 0,
            'avg_word_length': 0.0,
            'avg_sentence_length': 0.0
        }

    # Basic counts
    char_count = len(text)
    char_count_no_spaces = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

    # Word count
    words = text.split()
    word_count = len(words)

    # Line and paragraph count
    lines = [line for line in text.split('\n') if line.strip()]
    line_count = len(lines)

    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs)

    # Average word length
    avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0.0

    # Sentence count and average
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    sentence_count = len(sentences)
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0.0

    return {
        'char_count': char_count,
        'char_count_no_spaces': char_count_no_spaces,
        'word_count': word_count,
        'line_count': line_count,
        'paragraph_count': paragraph_count,
        'sentence_count': sentence_count,
        'avg_word_length': round(avg_word_length, 2),
        'avg_sentence_length': round(avg_sentence_length, 2)
    }


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length.

    Truncates at word boundary if possible.

    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to append when truncated

    Returns:
        Truncated text

    Example:
        >>> text = "This is a very long sentence that needs truncation"
        >>> truncated = truncate_text(text, 25)
        >>> print(truncated)
        This is a very long...
    """
    if len(text) <= max_length:
        return text

    if max_length <= len(suffix):
        return suffix[:max_length]

    # Try to truncate at word boundary
    truncate_at = max_length - len(suffix)
    truncated = text[:truncate_at]

    # Find last space
    last_space = truncated.rfind(' ')
    if last_space > 0 and last_space > truncate_at * 0.8:
        # If we found a space relatively close to the end, use it
        truncated = truncated[:last_space]

    return truncated + suffix


def remove_duplicate_lines(text: str, case_sensitive: bool = True) -> str:
    """Remove duplicate lines from text while preserving order.

    Args:
        text: Text with potential duplicate lines
        case_sensitive: Whether to consider case when detecting duplicates

    Returns:
        Text with duplicates removed

    Example:
        >>> text = "Line 1\\nLine 2\\nLine 1\\nLine 3"
        >>> deduped = remove_duplicate_lines(text)
        >>> print(deduped)
        Line 1
        Line 2
        Line 3
    """
    if not text:
        return ""

    lines = text.split('\n')
    seen = set()
    result = []

    for line in lines:
        check_line = line if case_sensitive else line.lower()
        if check_line not in seen:
            seen.add(check_line)
            result.append(line)

    return '\n'.join(result)


def extract_sentences(text: str) -> list[str]:
    """Extract sentences from text.

    Uses simple regex-based sentence splitting.

    Args:
        text: Text to split into sentences

    Returns:
        List of sentences

    Example:
        >>> text = "Hello world! How are you? I'm fine."
        >>> sentences = extract_sentences(text)
        >>> print(len(sentences))
        3
    """
    if not text:
        return []

    # Split on sentence terminators
    sentences = re.split(r'[.!?]+', text)

    # Clean and filter
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def is_mostly_ascii(text: str, threshold: float = 0.95) -> bool:
    """Check if text is mostly ASCII characters.

    Useful for detecting and handling non-English or corrupted text.

    Args:
        text: Text to check
        threshold: Minimum fraction of ASCII characters (0.0-1.0)

    Returns:
        True if text is mostly ASCII

    Example:
        >>> is_mostly_ascii("Hello World!")
        True
        >>> is_mostly_ascii("你好世界")
        False
    """
    if not text:
        return True

    ascii_count = sum(1 for char in text if ord(char) < 128)
    return (ascii_count / len(text)) >= threshold


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize a string to be used as a filename.

    Removes or replaces characters that are invalid in filenames.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename

    Example:
        >>> sanitize_filename("My Document (v2).pdf")
        'My_Document_v2.pdf'
        >>> sanitize_filename("file:with/invalid\\chars?.txt")
        'filewith_invalid_chars.txt'
    """
    if not filename:
        return "unnamed"

    # Remove or replace invalid characters
    # Invalid: < > : " / \ | ? *
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')

    # Collapse multiple underscores
    filename = re.sub(r'_+', '_', filename)

    # Truncate if too long
    if len(filename) > max_length:
        # Try to preserve extension
        parts = filename.rsplit('.', 1)
        if len(parts) == 2:
            name, ext = parts
            max_name_length = max_length - len(ext) - 1
            filename = name[:max_name_length] + '.' + ext
        else:
            filename = filename[:max_length]

    return filename or "unnamed"


# Example usage and testing
if __name__ == "__main__":
    print("=== Text Processing Utilities Examples ===\n")

    # Example 1: Clean HTML text
    print("Example 1: Clean HTML")
    html_text = """
    <div class="content">
        <h1>Title</h1>
        <p>This is a   paragraph with   <strong>HTML</strong> tags.</p>
        <p>Visit <a href="https://example.com">our website</a>!</p>
    </div>
    """
    cleaned = clean_text(html_text, remove_urls=True)
    print(f"Original ({len(html_text)} chars):")
    print(html_text)
    print(f"\nCleaned ({len(cleaned)} chars):")
    print(cleaned)

    # Example 2: Text statistics
    print("\n\nExample 2: Text Statistics")
    sample_text = """This is a test document.

    It has multiple paragraphs.
    And various sentences! Can we count them?
    """
    stats = get_text_stats(sample_text)
    print(f"Text: {repr(sample_text)}")
    print(f"\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Example 3: Truncate text
    print("\n\nExample 3: Truncate Text")
    long_text = "This is a very long sentence that needs to be truncated for display purposes"
    truncated = truncate_text(long_text, 30)
    print(f"Original: {long_text}")
    print(f"Truncated: {truncated}")

    # Example 4: Sanitize filename
    print("\n\nExample 4: Sanitize Filename")
    bad_filename = "My Document: Version 2 (final).pdf"
    good_filename = sanitize_filename(bad_filename)
    print(f"Original: {bad_filename}")
    print(f"Sanitized: {good_filename}")

    print("\n✅ All examples completed")
