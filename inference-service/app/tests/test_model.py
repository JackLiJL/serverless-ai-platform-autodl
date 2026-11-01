"""Unit tests for app.model — HuggingFace classes mocked, no GPU, no real model."""
import os
import json
import tempfile
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


# ── load_model() caching ───────────────────────────────────────────────────────

def test_load_model_returns_same_instance_on_second_call(mock_hf):
    """Calling load_model() twice returns the same cached objects."""
    import app.model as model_mod

    first = model_mod.load_model()
    second = model_mod.load_model()

    assert first[0] is second[0]   # same model object
    assert first[1] is second[1]   # same tokenizer object


def test_load_model_loads_once(mock_hf):
    """After the first load, subsequent calls return the cached mock_model directly."""
    mock_model, mock_tokenizer = mock_hf
    import app.model as model_mod

    first = model_mod.load_model()
    second = model_mod.load_model()

    # Both calls return the same cached objects
    assert first[0] is mock_model
    assert first[1] is mock_tokenizer
    assert second[0] is mock_model
    assert second[1] is mock_tokenizer


# ── predict() ──────────────────────────────────────────────────────────────────

def test_predict_returns_string(mock_hf):
    """predict() returns a non-empty string using the mocked model."""
    import app.model as model_mod

    result = model_mod.predict("What is Python?")
    assert isinstance(result, str)
    assert result == "mocked answer"


def test_predict_delegates_to_load_model(mock_hf):
    """predict() calls load_model() before generating."""
    mock_model, mock_tokenizer = mock_hf
    import app.model as model_mod

    with patch.object(model_mod, "load_model", return_value=(mock_model, mock_tokenizer)) as mock_load:
        model_mod.predict("Hello")
        mock_load.assert_called_once()


# ── _get_model_dir() ───────────────────────────────────────────────────────────

def test_get_model_dir_uses_env_var(tmp_path, monkeypatch):
    """_get_model_dir() returns the path from MODEL_DIR when valid."""
    import app.model as model_mod

    model_dir = tmp_path / "my_model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}")

    monkeypatch.setenv("MODEL_DIR", str(model_dir))
    result = model_mod._get_model_dir()
    assert result == str(model_dir.resolve())


def test_get_model_dir_raises_when_missing(monkeypatch):
    """_get_model_dir() raises RuntimeError when no model is found anywhere."""
    import app.model as model_mod

    monkeypatch.setenv("MODEL_DIR", "/nonexistent/model/path")

    # Patch os.path.isdir to return False for all paths,
    # simulating a system where no model directory exists.
    real_isdir = os.path.isdir

    def fake_isdir(path):
        return False if "nonexistent" in str(path) or "models" in str(path) else real_isdir(path)

    with patch("os.path.isdir", side_effect=fake_isdir):
        with pytest.raises(RuntimeError, match="No model found"):
            model_mod._get_model_dir()
