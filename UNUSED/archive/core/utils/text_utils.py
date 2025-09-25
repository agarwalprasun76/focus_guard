"""
Text utilities for handling encoding, Unicode, and display formatting issues.
"""
import re
import sys
import unicodedata
from typing import Optional, List, Dict, Any, Union


def sanitize_console_output(text: str) -> str:
    """
    Sanitize text for console output, removing or replacing problematic Unicode characters.
    
    Args:
        text: The text to sanitize
        
    Returns:
        Sanitized text safe for console output
    """
    if not text:
        return ""
    
    # Replace emoji and other non-BMP Unicode characters with placeholders
    sanitized = ''.join(c if ord(c) < 65536 else '?' for c in text)
    
    # Handle other potentially problematic characters
    sanitized = sanitized.replace('\u2713', '✓').replace('\u2717', '✗')
    
    # For Windows terminals that might have issues with even common Unicode symbols
    try:
        # Test if the string can be encoded in the current console encoding
        sanitized.encode(sys.stdout.encoding)
    except (UnicodeEncodeError, AttributeError):
        # If encoding fails, replace with ASCII-compatible versions
        sanitized = sanitized.replace('✓', 'Y').replace('✗', 'X')
        
    return sanitized


def truncate_text(text: str, max_length: int = 100, add_ellipsis: bool = True) -> str:
    """
    Truncate text to a maximum length and add ellipsis if requested.
    
    Args:
        text: Text to truncate
        max_length: Maximum allowed length
        add_ellipsis: Whether to add ellipsis to truncated text
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
        
    truncated = text[:max_length]
    if add_ellipsis:
        truncated += "..."
        
    return truncated


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text, replacing multiple spaces with single spaces.
    
    Args:
        text: Text to normalize
        
    Returns:
        Text with normalized whitespace
    """
    if not text:
        return ""
        
    # Replace all whitespace sequences with a single space
    return re.sub(r'\s+', ' ', text).strip()


def normalize_unicode(text: str) -> str:
    """
    Normalize Unicode characters to their canonical form.
    
    Args:
        text: Text to normalize
        
    Returns:
        Unicode-normalized text
    """
    if not text:
        return ""
        
    # Apply NFKC normalization (compatibility decomposition followed by canonical composition)
    return unicodedata.normalize('NFKC', text)


def safe_json_string(text: str) -> str:
    """
    Make a string safe for JSON serialization.
    
    Args:
        text: Text to make JSON-safe
        
    Returns:
        JSON-safe string
    """
    if not text:
        return ""
        
    # Replace control characters and other problematic chars
    return ''.join(c if ord(c) >= 32 and c != '\\' and c != '"' else ' ' for c in text)


def format_for_terminal_output(value: Any) -> str:
    """
    Format any value for safe terminal output, handling different data types.
    
    Args:
        value: Value to format for terminal output
        
    Returns:
        Terminal-safe string representation
    """
    if value is None:
        return "None"
    elif isinstance(value, bool):
        return "Yes" if value else "No"
    elif isinstance(value, (list, tuple)):
        items = [format_for_terminal_output(item) for item in value]
        return ', '.join(items)
    elif isinstance(value, dict):
        return '{' + ', '.join(f'{k}: {format_for_terminal_output(v)}' for k, v in value.items()) + '}'
    else:
        # Convert to string and sanitize
        return sanitize_console_output(str(value))
