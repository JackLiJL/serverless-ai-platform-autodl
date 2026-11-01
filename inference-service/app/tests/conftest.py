"""Shared fixtures for app unit tests.

MODEL_DIR must be set before app.model is first imported,
because model.py calls _get_model_dir() at module level.
This conftest creates a minimal fake model dir at collection time.
"""
import os
import json
import tempfile
from unittest.mock import patch, MagicMock

import pytest

# ── Create a fake model dir before any test module imports app.model ─────────
# _get_model_dir() checks for <MODEL_DIR>/config.json, so we provide one.
# Force-override (not setdefault) so a stale MODEL_DIR in the dev environment
# doesn't break the import of app.model.
_fake_model_dir = tempfile.mkdtemp(prefix="fake_model_")
os.makedirs(_fake_model_dir, exist_ok=True)
with open(os.path.join(_fake_model_dir, "config.json"), "w") as _f:
    json.dump(
        {"model_type": "qwen3", "architectures": ["Qwen3ForCausalLM"]},
        _f,
    )
os.environ["MODEL_DIR"] = _fake_model_dir


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_model_dir():
    """Return the fake model directory path (already set in MODEL_DIR env var)."""
    return _fake_model_dir


@pytest.fixture
def mock_hf():
    """
    Patch AutoTokenizer and AutoModelForCausalLM so no real model loading occurs.
    Resets module-level caches (_model, _tokenizer) before and after the test.

    Yields (mock_model, mock_tokenizer).
    """
    import app.model as model_mod
    import torch

    mock_model = MagicMock()
    mock_model.device = "cpu"
    mock_model.eval.return_value = None
    # load_model() does: _model = _model.to(device) when device == "cpu"
    # .to() must return the same mock so _model stays mock_model (with .device == "cpu")
    mock_model.to.return_value = mock_model
    # generate() returns a 2-D tensor [batch, seq]
    mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]])

    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = "mocked_prompt"
    # tokenizer(text, return_tensors="pt") is a call on the mock instance.
    # For MagicMock, the callable return value is set via .return_value (NOT __call__).
    mock_tokenizer.return_value = {
        "input_ids": torch.tensor([[1, 2, 3, 4]]),
        "attention_mask": torch.tensor([[1, 1, 1, 1]]),
    }
    mock_tokenizer.decode.return_value = "mocked answer"

    # Reset caches so load_model() actually executes in the test
    model_mod._model = None
    model_mod._tokenizer = None

    with patch.object(model_mod, "AutoTokenizer") as mock_tok_cls, \
         patch.object(model_mod, "AutoModelForCausalLM") as mock_clm_cls:
        mock_tok_cls.from_pretrained.return_value = mock_tokenizer
        mock_clm_cls.from_pretrained.return_value = mock_model
        yield mock_model, mock_tokenizer

    # Teardown: clear caches so subsequent tests start clean
    model_mod._model = None
    model_mod._tokenizer = None


@pytest.fixture
def test_client(mock_hf):
    """
    FastAPI TestClient with load_model / predict mocked at the app.main namespace.
    Using the context-manager form triggers the startup event (which calls
    the mocked load_model, so no real model is needed).
    """
    from fastapi.testclient import TestClient
    import app.main

    mock_model, mock_tokenizer = mock_hf

    # main.py does `from app.model import load_model, predict`
    # so patch the references in app.main's namespace
    with patch("app.main.load_model", return_value=(mock_model, mock_tokenizer)), \
         patch("app.main.predict", return_value="This is a mocked answer."):
        with TestClient(app.main.app) as client:
            yield client
