import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from mtg_utils.utils.config import AppConfig, DeckConfig, load_config


@pytest.mark.unit
def test_load_config_valid(tmp_path):
    cfg = {
        "binder_id": "abc123",
        "decks": {"my_deck": {"id": "deck-id-1", "file": "decks/my_deck.txt"}},
    }
    f = tmp_path / "config.json"
    f.write_text(json.dumps(cfg))
    result = load_config(str(f))
    assert isinstance(result, AppConfig)
    assert result.binder_id == "abc123"
    assert "my_deck" in result.decks
    deck = result.decks["my_deck"]
    assert isinstance(deck, DeckConfig)
    assert deck.id == "deck-id-1"
    assert deck.file == "decks/my_deck.txt"


@pytest.mark.unit
def test_load_config_defaults(tmp_path):
    cfg = {"binder_id": "xyz", "decks": {}}
    f = tmp_path / "config.json"
    f.write_text(json.dumps(cfg))
    result = load_config(str(f))
    assert result.purchased_file == "card_library/purchased.txt"
    assert result.purchased_formatted_file == "card_library/purchased_formatted.txt"


@pytest.mark.unit
def test_load_config_deck_shared_decks_default(tmp_path):
    cfg = {
        "binder_id": "xyz",
        "decks": {"solo": {"id": "s1", "file": "decks/solo.txt"}},
    }
    f = tmp_path / "config.json"
    f.write_text(json.dumps(cfg))
    result = load_config(str(f))
    assert result.decks["solo"].shared_decks == []


@pytest.mark.unit
def test_load_config_deck_shared_decks(tmp_path):
    cfg = {
        "binder_id": "xyz",
        "decks": {
            "main": {
                "id": "m1",
                "file": "decks/main.txt",
                "shared_decks": ["other"],
            }
        },
    }
    f = tmp_path / "config.json"
    f.write_text(json.dumps(cfg))
    result = load_config(str(f))
    assert result.decks["main"].shared_decks == ["other"]


@pytest.mark.unit
def test_load_config_creates_default_when_missing(tmp_path):
    cfg_path = str(tmp_path / "new_config.json")
    result = load_config(cfg_path)
    assert isinstance(result, AppConfig)
    assert hasattr(result, "binder_id")
    assert hasattr(result, "decks")
    assert Path(cfg_path).exists()


@pytest.mark.unit
def test_load_config_malformed_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{ not valid json }")
    with pytest.raises(json.JSONDecodeError):
        load_config(str(f))


@pytest.mark.unit
def test_load_config_invalid_schema(tmp_path):
    cfg = {"decks": {}}  # missing required binder_id
    f = tmp_path / "config.json"
    f.write_text(json.dumps(cfg))
    with pytest.raises(ValidationError):
        load_config(str(f))
