"""Tests for validating a graph IRI typed by the user"""

import pytest

from cmem_plugin_pyshacl.plugin_pyshacl import is_valid_uri


@pytest.mark.parametrize(
    "uri",
    [
        "https://example.org/graph",
        "https://example.org/graph#",
        "urn:uuid:6e8bc430-9c3a-11d9-9669-0800200c9a66",
        "URN:Example:data",
        "urn:graph",
    ],
)
def test_valid_uri(uri: str) -> None:
    """URLs and URNs are accepted"""
    assert is_valid_uri(uri)


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "https:/example.org/graph",
        "https://example.org/a b",
        "urn:",
        "urn:example:has space",
        "urn:example:a<b",
        "example.org/graph",
    ],
)
def test_invalid_uri(uri: str) -> None:
    """Malformed URLs, and URNs with characters an IRI cannot contain, are rejected"""
    assert not is_valid_uri(uri)
