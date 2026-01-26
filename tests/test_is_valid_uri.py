"""Tests for validating graph parameter URIs"""

from cmem_plugin_pyshacl.plugin_pyshacl import is_valid_uri


def test_graph_parameter_url() -> None:
    """Test validation of URL"""
    assert is_valid_uri("https://example.org/graph")


def test_graph_parameter_url_fail() -> None:
    """Test validation of URL - fail"""
    assert not is_valid_uri("https:/example.org/graph")


def test_graph_parameter_urn() -> None:
    """Test validation of URN"""
    assert is_valid_uri("urn:isbn:9780134685991")


def test_graph_parameter_urn_invalid() -> None:
    """Test validation of URN - fail"""
    assert not is_valid_uri("urn:x:9780134685991")
