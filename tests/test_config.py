"""Tests for configuration management."""

import os
import pytest
from dbb.config import Config, load_config, ChannelConfig


def test_config_creation():
    """Test creating a config object."""
    config = Config()
    assert config.db_path == "./dbb.duckdb"
    assert len(config.channels) == 0


def test_config_with_channels():
    """Test config with channels."""
    channel = ChannelConfig(name="Test", channel_id="UC123")
    config = Config(channels=[channel])
    assert len(config.channels) == 1
    assert config.channels[0].name == "Test"


def test_env_var_interpolation():
    """Test environment variable interpolation."""
    os.environ["TEST_VAR"] = "test_value"

    config = Config(
        db_path="${TEST_VAR}.duckdb"
    )

    resolved = config.resolve_env_vars()
    assert "test_value" in resolved.db_path


def test_get_api_key():
    """Test getting API key from environment."""
    os.environ["TEST_API_KEY"] = "secret123"

    config = Config()
    key = config.get_api_key("TEST_API_KEY")
    assert key == "secret123"


def test_get_api_key_missing():
    """Test getting missing API key."""
    config = Config()
    key = config.get_api_key("NONEXISTENT_KEY")
    assert key == ""
