"""Tests for webshocket.utils — parse_duration and generate_uuid."""

import pytest
from webshocket.utils import parse_duration, generate_uuid


def test_generate_uuid_uniqueness():
    ids = {generate_uuid() for _ in range(100)}
    assert len(ids) == 100


def test_parse_duration_valid():
    assert parse_duration("10s") == 10.0
    assert parse_duration("5m") == 300.0
    assert parse_duration("2h") == 7200.0
    assert parse_duration("1d") == 86400.0


def test_parse_duration_empty_string():
    with pytest.raises(ValueError, match="Duration cannot be empty"):
        parse_duration("")


def test_parse_duration_invalid_unit():
    with pytest.raises(ValueError, match="Invalid duration unit"):
        parse_duration("10x")
