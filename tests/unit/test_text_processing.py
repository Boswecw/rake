"""Unit Tests for Text Processing Utilities

Tests for text cleaning, normalization, and statistics functions.

Run with:
    pytest tests/unit/test_text_processing.py -v
"""

import pytest
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


class TestCleanText:
    """Tests for clean_text function."""

    def test_remove_html_tags(self):
        """Test HTML tag removal."""
        html = "<p>Hello <strong>World</strong>!</p>"
        cleaned = clean_text(html, remove_html=True)
        assert "<" not in cleaned
        assert ">" not in cleaned
        assert "Hello" in cleaned
        assert "World" in cleaned

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "Hello    World\n\n\n\nTest"
        cleaned = clean_text(text, normalize_whitespace=True)
        assert "    " not in cleaned
        assert "\n\n\n" not in cleaned

    def test_remove_urls(self):
        """Test URL removal."""
        text = "Visit https://example.com for more info"
        cleaned = clean_text(text, remove_urls=True)
        assert "https://" not in cleaned
        assert "example.com" not in cleaned
        assert "Visit" in cleaned
        assert "for more info" in cleaned

    def test_remove_emails(self):
        """Test email removal."""
        text = "Contact us at test@example.com"
        cleaned = clean_text(text, remove_emails=True)
        assert "@" not in cleaned
        assert "test" not in cleaned
        assert "Contact us at" in cleaned

    def test_lowercase(self):
        """Test lowercase conversion."""
        text = "Hello World"
        cleaned = clean_text(text, lowercase=True)
        assert cleaned == "hello world"

    def test_empty_text(self):
        """Test handling of empty text."""
        assert clean_text("") == ""
        assert clean_text(None) == ""


class TestRemoveHtmlTags:
    """Tests for remove_html_tags function."""

    def test_simple_tags(self):
        """Test simple HTML tag removal."""
        html = "<p>Test</p>"
        result = remove_html_tags(html)
        assert result == "Test"

    def test_nested_tags(self):
        """Test nested HTML tag removal."""
        html = "<div><p><strong>Test</strong></p></div>"
        result = remove_html_tags(html)
        assert result == "Test"

    def test_preserve_text(self):
        """Test that text content is preserved."""
        html = "<p>Hello</p> <p>World</p>"
        result = remove_html_tags(html)
        assert "Hello" in result
        assert "World" in result


class TestNormalizeWhitespace:
    """Tests for normalize_whitespace function."""

    def test_collapse_spaces(self):
        """Test collapsing multiple spaces."""
        text = "Hello    World"
        result = normalize_whitespace(text)
        assert result == "Hello World"

    def test_normalize_newlines(self):
        """Test normalizing line endings."""
        text = "Line1\r\nLine2\rLine3\nLine4"
        result = normalize_whitespace(text)
        lines = result.split('\n')
        assert len(lines) == 4

    def test_remove_trailing_whitespace(self):
        """Test removing trailing whitespace."""
        text = "Line1   \nLine2   \n"
        result = normalize_whitespace(text)
        assert not result.endswith(' ')


class TestGetTextStats:
    """Tests for get_text_stats function."""

    def test_word_count(self):
        """Test word counting."""
        text = "Hello world test"
        stats = get_text_stats(text)
        assert stats['word_count'] == 3

    def test_char_count(self):
        """Test character counting."""
        text = "Hello"
        stats = get_text_stats(text)
        assert stats['char_count'] == 5
        assert stats['char_count_no_spaces'] == 5

    def test_paragraph_count(self):
        """Test paragraph counting."""
        text = "Para 1\n\nPara 2\n\nPara 3"
        stats = get_text_stats(text)
        assert stats['paragraph_count'] == 3

    def test_empty_text(self):
        """Test stats for empty text."""
        stats = get_text_stats("")
        assert stats['word_count'] == 0
        assert stats['char_count'] == 0


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_truncate_long_text(self):
        """Test truncating text that exceeds max length."""
        text = "This is a very long sentence that needs truncation"
        result = truncate_text(text, 20)
        assert len(result) <= 20
        assert result.endswith("...")

    def test_short_text_unchanged(self):
        """Test that short text is not truncated."""
        text = "Short"
        result = truncate_text(text, 20)
        assert result == "Short"

    def test_word_boundary(self):
        """Test truncation at word boundary."""
        text = "Hello world test"
        result = truncate_text(text, 12)
        assert "..." in result


class TestRemoveDuplicateLines:
    """Tests for remove_duplicate_lines function."""

    def test_remove_duplicates(self):
        """Test removing duplicate lines."""
        text = "Line 1\nLine 2\nLine 1\nLine 3"
        result = remove_duplicate_lines(text)
        lines = result.split('\n')
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[1] == "Line 2"
        assert lines[2] == "Line 3"

    def test_case_sensitive(self):
        """Test case-sensitive duplicate detection."""
        text = "Hello\nhello\nHELLO"
        result = remove_duplicate_lines(text, case_sensitive=True)
        assert result.count('\n') == 2  # All three are different

    def test_case_insensitive(self):
        """Test case-insensitive duplicate detection."""
        text = "Hello\nhello\nHELLO"
        result = remove_duplicate_lines(text, case_sensitive=False)
        assert result.count('\n') == 0  # Only one unique


class TestExtractSentences:
    """Tests for extract_sentences function."""

    def test_basic_extraction(self):
        """Test basic sentence extraction."""
        text = "Hello world! How are you? I'm fine."
        sentences = extract_sentences(text)
        assert len(sentences) == 3

    def test_empty_text(self):
        """Test extraction from empty text."""
        sentences = extract_sentences("")
        assert sentences == []


class TestIsMostlyAscii:
    """Tests for is_mostly_ascii function."""

    def test_ascii_text(self):
        """Test pure ASCII text."""
        assert is_mostly_ascii("Hello World 123!")

    def test_non_ascii_text(self):
        """Test non-ASCII text."""
        assert not is_mostly_ascii("你好世界")

    def test_mixed_text(self):
        """Test mixed ASCII and non-ASCII."""
        # Mostly ASCII
        assert is_mostly_ascii("Hello 世界", threshold=0.7)
        # Mostly non-ASCII
        assert not is_mostly_ascii("世界世界 Hello", threshold=0.7)


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_remove_invalid_chars(self):
        """Test removing invalid filename characters."""
        filename = "file:with/invalid\\chars?.txt"
        result = sanitize_filename(filename)
        assert ":" not in result
        assert "/" not in result
        assert "\\" not in result
        assert "?" not in result

    def test_preserve_extension(self):
        """Test preserving file extension."""
        filename = "document.pdf"
        result = sanitize_filename(filename)
        assert result.endswith(".pdf")

    def test_truncate_long_name(self):
        """Test truncating very long filenames."""
        filename = "a" * 300 + ".txt"
        result = sanitize_filename(filename, max_length=255)
        assert len(result) <= 255
        assert result.endswith(".txt")

    def test_empty_name(self):
        """Test handling empty filename."""
        result = sanitize_filename("")
        assert result == "unnamed"


# Run tests with: pytest tests/unit/test_text_processing.py -v
