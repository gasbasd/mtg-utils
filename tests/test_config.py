import json
from pathlib import Path
import pytest
from mtg_utils.utils.config import load_config


def test_load_config_valid(tmp_path):
    cfg = {"binder_id": "abc", "decks": {}, "purchased_file": "purchased.txt"}
    f = tmp_path / "config.json"
    f.write_text(json.dumps(cfg))
    assert load_config(str(f)) == cfg


def test_load_config_creates_default_when_missing(tmp_path):
    cfg_path = str(tmp_path / "new_config.json")
    result = load_config(cfg_path)
    assert "binder_id" in result
    assert "decks" in result
    assert Path(cfg_path).exists()


def test_load_config_default_has_expected_keys(tmp_path):
    cfg_path = str(tmp_path / "auto.json")
    result = load_config(cfg_path)
    assert "purchased_file" in result
    assert isinstance(result["decks"], dict)


def test_load_config_malformed_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{ not valid json }")
    with pytest.raises(json.JSONDecodeError):
        load_config(str(f))
