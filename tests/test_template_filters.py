# tests/test_template_filters.py
import pytest
from unittest.mock import MagicMock
from datetime import datetime
import app  # Import the app module directly


class TestTemplateFilters:
    def test_markdown_filter(self):
        # Test with basic markdown
        result = app.markdown_filter("# Heading\n- Item 1\n- Item 2")
        assert "<h1>Heading</h1>" in result
        assert "<li>Item 1</li>" in result
        assert "<li>Item 2</li>" in result

        # Test with code blocks
        result = app.markdown_filter("```python\ndef hello():\n    print('Hello')\n```")
        assert '<pre><code class="language-python">' in result
        assert "def hello():" in result

        # Test with None
        result = app.markdown_filter(None)
        assert result == ""

    def test_datetime_format(self):
        # Test with ISO format string
        result = app.datetime_format("2025-04-01T10:00:00Z")
        assert result == "2025-04-01 10:00:00"

        # Test with datetime object
        dt = datetime(2025, 4, 1, 10, 0, 0)
        result = app.datetime_format(dt)
        assert result == dt  # Should return the object unchanged

        # Test with invalid string
        result = app.datetime_format("invalid-datetime")
        assert result == "invalid-datetime"  # Should return the string unchanged

    def test_chat_time_format(self):
        # Test with ISO format string
        result = app.chat_time_format("2025-04-01T10:00:00Z")
        assert result == "2025-04-01 10:00"  # Different format from datetime_format

        # Test with datetime object
        dt = datetime(2025, 4, 1, 10, 0, 0)
        result = app.chat_time_format(dt)
        assert result == dt  # Should return the object unchanged

        # Test with invalid string
        result = app.chat_time_format("invalid-datetime")
        assert result == "invalid-datetime"  # Should return the string unchanged
