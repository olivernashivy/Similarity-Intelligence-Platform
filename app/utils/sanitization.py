"""Text sanitization and validation utilities.

Handles special characters, encoding issues, and text cleanup
to prevent processing failures.
"""
import re
import unicodedata
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def sanitize_text(
    text: str,
    max_length: Optional[int] = None,
    remove_control_chars: bool = True,
    normalize_unicode: bool = True,
    preserve_newlines: bool = True
) -> str:
    """
    Sanitize text input to handle special characters and encoding issues.

    Args:
        text: Input text to sanitize
        max_length: Optional maximum length (truncates if exceeded)
        remove_control_chars: Remove control characters (except newlines/tabs)
        normalize_unicode: Normalize unicode to NFC form
        preserve_newlines: Keep newline characters

    Returns:
        Sanitized text string

    Examples:
        >>> sanitize_text("Hello\\x00World")
        'HelloWorld'
        >>> sanitize_text("café")  # Returns normalized unicode
        'café'
    """
    if not text or not isinstance(text, str):
        return ""

    try:
        # Step 1: Handle encoding issues - ensure proper UTF-8
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        else:
            # Re-encode to catch any encoding issues
            text = text.encode('utf-8', errors='ignore').decode('utf-8')

        # Step 2: Normalize unicode (NFC = composed form)
        if normalize_unicode:
            text = unicodedata.normalize('NFC', text)

        # Step 3: Remove or replace problematic characters
        if remove_control_chars:
            # Remove control characters but optionally preserve newlines/tabs
            if preserve_newlines:
                # Keep \n, \r, \t but remove other control chars
                text = ''.join(
                    char for char in text
                    if unicodedata.category(char)[0] != 'C' or char in '\n\r\t'
                )
            else:
                # Remove all control characters
                text = ''.join(
                    char for char in text
                    if unicodedata.category(char)[0] != 'C'
                )

        # Step 4: Replace multiple whitespace with single space
        # But preserve paragraph breaks (double newlines)
        if preserve_newlines:
            # Normalize whitespace within lines
            lines = text.split('\n')
            text = '\n'.join(' '.join(line.split()) for line in lines)
            # Remove excessive newlines (more than 2)
            text = re.sub(r'\n{3,}', '\n\n', text)
        else:
            text = ' '.join(text.split())

        # Step 5: Remove leading/trailing whitespace
        text = text.strip()

        # Step 6: Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0]  # Break at word boundary
            logger.warning(f"Text truncated from {len(text)} to {max_length} characters")

        return text

    except Exception as e:
        logger.error(f"Error sanitizing text: {e}", exc_info=True)
        # Fallback: return basic cleaned version
        return str(text).strip() if text else ""


def remove_special_quotes(text: str) -> str:
    """
    Replace smart quotes and special quote characters with standard quotes.

    Args:
        text: Input text

    Returns:
        Text with normalized quotes
    """
    # Map of special characters to replacements
    replacements = {
        # Smart quotes
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201b': "'",  # Single high-reversed-9 quotation mark
        # Other quotes
        '\u00ab': '"',  # Left-pointing double angle quotation mark
        '\u00bb': '"',  # Right-pointing double angle quotation mark
        '\u2039': "'",  # Single left-pointing angle quotation mark
        '\u203a': "'",  # Single right-pointing angle quotation mark
        # Double prime/ditto
        '\u2033': '"',
        '\u2032': "'",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def remove_zero_width_chars(text: str) -> str:
    """
    Remove zero-width characters that can cause issues.

    Args:
        text: Input text

    Returns:
        Text without zero-width characters
    """
    zero_width_chars = [
        '\u200b',  # Zero width space
        '\u200c',  # Zero width non-joiner
        '\u200d',  # Zero width joiner
        '\ufeff',  # Zero width no-break space (BOM)
        '\u2060',  # Word joiner
    ]

    for char in zero_width_chars:
        text = text.replace(char, '')

    return text


def clean_article_text(text: str, max_length: int = 50000) -> str:
    """
    Clean article text for processing - handles all common issues.

    This is the main function to use for article input sanitization.

    Args:
        text: Raw article text from user
        max_length: Maximum allowed length

    Returns:
        Cleaned, safe text ready for processing

    Raises:
        ValueError: If text is empty after cleaning or exceeds max_length
    """
    if not text:
        raise ValueError("Article text cannot be empty")

    # Apply all sanitization steps
    text = sanitize_text(
        text,
        max_length=max_length,
        remove_control_chars=True,
        normalize_unicode=True,
        preserve_newlines=True
    )

    # Remove special quotes and zero-width characters
    text = remove_special_quotes(text)
    text = remove_zero_width_chars(text)

    # Final validation
    if not text or len(text.strip()) == 0:
        raise ValueError("Article text is empty after sanitization")

    if len(text.split()) < 10:
        raise ValueError("Article text too short (minimum 10 words required)")

    logger.info(f"Article text sanitized: {len(text)} chars, {len(text.split())} words")

    return text


def validate_metadata(metadata: dict) -> dict:
    """
    Validate and sanitize metadata dictionary.

    Args:
        metadata: User-provided metadata

    Returns:
        Sanitized metadata dictionary
    """
    if not metadata:
        return {}

    cleaned = {}
    for key, value in metadata.items():
        # Sanitize key
        if isinstance(key, str):
            clean_key = sanitize_text(key, max_length=100, preserve_newlines=False)
            if clean_key:
                # Sanitize value
                if isinstance(value, str):
                    clean_value = sanitize_text(value, max_length=500)
                    cleaned[clean_key] = clean_value
                elif isinstance(value, (int, float, bool)):
                    cleaned[clean_key] = value
                elif value is None:
                    cleaned[clean_key] = None
                # Skip complex types

    return cleaned


def safe_truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Safely truncate text at word boundary.

    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    # Account for suffix
    target_length = max_length - len(suffix)

    if target_length <= 0:
        return suffix

    # Find last space before target length
    truncated = text[:target_length].rsplit(' ', 1)[0]

    return truncated + suffix


def extract_printable_text(text: str) -> str:
    """
    Extract only printable characters from text.

    Useful for handling text with binary data or corrupted encoding.

    Args:
        text: Input text

    Returns:
        Text with only printable characters
    """
    import string

    printable = set(string.printable)
    return ''.join(filter(lambda x: x in printable or x.isprintable(), text))
