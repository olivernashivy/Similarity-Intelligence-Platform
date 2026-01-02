#!/usr/bin/env python3
"""Test script to verify text sanitization handles special characters."""

from app.utils.sanitization import clean_article_text, sanitize_text, remove_special_quotes, remove_zero_width_chars

def test_special_characters():
    """Test various special character scenarios."""

    print("=" * 80)
    print("Testing Text Sanitization")
    print("=" * 80)

    # Test 1: Smart quotes and curly quotes
    print("\n1. Testing smart quotes:")
    text_with_smart_quotes = 'This is a \u201ctest\u201d with \u2018smart quotes\u2019 and \u2013 dashes.'
    cleaned = clean_article_text(text_with_smart_quotes)
    print(f"   Input:  {repr(text_with_smart_quotes)}")
    print(f"   Output: {repr(cleaned)}")
    print(f"   ✓ Smart quotes normalized" if '"test"' in cleaned else "   ✗ Failed")

    # Test 2: Zero-width characters
    print("\n2. Testing zero-width characters:")
    text_with_zwc = "This is a test article with Hello\u200bWorld\u200c\u200dTest and some more words to meet minimum"  # Contains zero-width spaces
    cleaned = clean_article_text(text_with_zwc)
    print(f"   Input:  {repr(text_with_zwc)}")
    print(f"   Output: {repr(cleaned)}")
    print(f"   ✓ Zero-width chars removed" if '\u200b' not in cleaned else "   ✗ Failed")

    # Test 3: Control characters
    print("\n3. Testing control characters:")
    text_with_control = "This is a test article with Hello\x00\x01\x02World control characters and some more words to test"
    cleaned = clean_article_text(text_with_control)
    print(f"   Input:  {repr(text_with_control)}")
    print(f"   Output: {repr(cleaned)}")
    print(f"   ✓ Control chars removed" if '\x00' not in cleaned else "   ✗ Failed")

    # Test 4: Mixed unicode and emoji
    print("\n4. Testing unicode and emoji:")
    text_with_emoji = "This article discusses AI 🤖 and machine learning 📊 with various technologies and approaches used"
    cleaned = clean_article_text(text_with_emoji)
    print(f"   Input:  {repr(text_with_emoji)}")
    print(f"   Output: {repr(cleaned)}")
    print(f"   ✓ Unicode preserved" if '🤖' in cleaned else "   ✗ Failed")

    # Test 5: Accented characters
    print("\n5. Testing accented characters:")
    text_with_accents = "This article about the Café résumé naïve Zürich restaurant has many interesting details to discuss"
    cleaned = clean_article_text(text_with_accents)
    print(f"   Input:  {repr(text_with_accents)}")
    print(f"   Output: {repr(cleaned)}")
    print(f"   ✓ Accents preserved" if 'é' in cleaned else "   ✗ Failed")

    # Test 6: Newlines and formatting
    print("\n6. Testing newlines and formatting:")
    text_with_formatting = "This is paragraph 1 with some text.\n\nThis is paragraph 2 with more information.\n\tThis is tabbed text with details."
    cleaned = clean_article_text(text_with_formatting)
    print(f"   Input:  {repr(text_with_formatting)}")
    print(f"   Output: {repr(cleaned)}")
    print(f"   ✓ Formatting preserved" if '\n' in cleaned else "   ✗ Failed")

    # Test 7: Malformed UTF-8
    print("\n7. Testing malformed UTF-8 recovery:")
    try:
        # Create bytes with invalid UTF-8 sequence
        malformed_bytes = b"This is a test article with malformed UTF-8 Hello \xff\xfe World and some more text to meet requirements"
        text_from_bytes = malformed_bytes.decode('utf-8', errors='ignore')
        cleaned = clean_article_text(text_from_bytes)
        print(f"   Input:  {repr(text_from_bytes)}")
        print(f"   Output: {repr(cleaned)}")
        print(f"   ✓ Malformed UTF-8 handled")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    # Test 8: Very long text with special characters
    print("\n8. Testing long text with mixed special characters:")
    long_text = ('This is a test article with \u201csmart quotes\u201d and \u2018apostrophes\u2019. ' * 100)
    cleaned = clean_article_text(long_text, max_length=5000)
    print(f"   Input length:  {len(long_text)} chars")
    print(f"   Output length: {len(cleaned)} chars")
    print(f"   ✓ Length limited correctly" if len(cleaned) <= 5000 else "   ✗ Failed")

    # Test 9: Empty and whitespace-only text
    print("\n9. Testing edge cases (validation errors):")
    empty_text = ""
    whitespace_text = "   \n\t  "
    try:
        cleaned_empty = clean_article_text(empty_text)
        print(f"   ✗ Empty text should raise error")
    except ValueError as e:
        print(f"   ✓ Empty text validation: {e}")

    try:
        cleaned_whitespace = clean_article_text(whitespace_text)
        print(f"   ✗ Whitespace-only text should raise error")
    except ValueError as e:
        print(f"   ✓ Whitespace validation: {e}")

    # Test 10: Real-world copy-paste scenario
    print("\n10. Testing real-world copy-paste from website:")
    copypasted_text = '''
    This article was copied from a website\u2122 and contains various special characters:
    \u2022 Bullet points
    \u2013 En dash
    \u2014 Em dash
    \u2026 Ellipsis
    \u00a9 Copyright symbol
    \u00ae Registered trademark
    \u201cQuotes\u201d and \u2018apostrophes\u2019
    '''
    cleaned = clean_article_text(copypasted_text)
    print(f"   Input:  {repr(copypasted_text[:100])}...")
    print(f"   Output: {repr(cleaned[:100])}...")
    print(f"   ✓ Real-world text handled" if cleaned else "   ✗ Failed")

    print("\n" + "=" * 80)
    print("Sanitization Tests Complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_special_characters()
